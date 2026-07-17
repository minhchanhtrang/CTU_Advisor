import os

import torch
import chromadb
from llama_index.core import VectorStoreIndex, Settings, PromptTemplate
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.google_genai import GoogleGenAI
from dotenv import load_dotenv

from llama_index.core.schema import TextNode
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core import get_response_synthesizer

EMBED_MODEL_NAME = "Alibaba-NLP/gte-multilingual-base"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

QA_PROMPT_STR = (
    "Bạn là trợ lý ảo tư vấn học vụ chính thức của Trường Đại học Cần Thơ (CTU).\n"
    "Thông tin ngữ cảnh từ CSDL được cung cấp bên dưới.\n"
    "---------------------\n"
    "{context_str}\n"
    "---------------------\n"
    "{history_str}"
    "Nhiệm vụ của bạn là giải đáp các thắc mắc của sinh viên dựa TẤT CẢ vào thông tin phía trên. "
    "Trình bày rõ ràng, thân thiện, sử dụng gạch đầu dòng nếu cần thiết.\n"
    "LUẬT 1: TUYỆT ĐỐI KHÔNG BỊA ĐẶT THÔNG TIN. Nếu thông tin không có trong ngữ cảnh, BẮT BUỘC bạn phải trả lời: "
    "'Hiện tại dữ liệu được cung cấp chưa có thông tin về vấn đề này...'\n"
    "LUẬT 2: Không được tóm tắt. Nếu sinh viên yêu cầu liệt kê, hãy liệt kê đầy đủ 100% các mục.\n"
    "LUẬT 3 (QUAN TRỌNG): KHÔNG ghi chú nguồn trong từng câu. Thay vào đó, sau khi trả lời xong, "
    "hãy thêm một dòng trống rồi in: '---\n📌 **Nguồn tham khảo:** [liệt kê các tên mục/ngành từ thẻ [Mục: ...] trong ngữ cảnh, "
    "phân cách bằng dấu \" · \"]'\n"
    "Câu hỏi của sinh viên: {query_str}\n"
    "Câu trả lời của Chatbot: "
)

MAX_HISTORY_TURNS = 5  # Số lượt hội thoại gần nhất được ghi nhớ


def build_history_str(chat_history: list) -> str:
    """
    Chuyển đổi danh sách lịch sử chat thành chuỗi văn bản để inject vào prompt.
    Chỉ lấy MAX_HISTORY_TURNS lượt gần nhất (mỗi lượt = 1 user + 1 assistant).
    """
    if not chat_history:
        return ""
    
    # Mỗi lượt hội thoại gồm 2 messages (user + assistant)
    # Lấy MAX_HISTORY_TURNS*2 messages gần nhất
    recent = chat_history[-(MAX_HISTORY_TURNS * 2):]
    
    lines = ["Lịch sử hội thoại trước đó (để hiểu ngữ cảnh):\n"]
    for msg in recent:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            lines.append(f"Sinh viên: {content}")
        elif role == "assistant":
            lines.append(f"Chatbot: {content}")
    lines.append("---------------------\n")
    return "\n".join(lines) + "\n"

def get_distinct_nganh(collection):
    """
    Lấy toàn bộ giá trị 'nganh_hoc' duy nhất đang có trong vector DB.
    Sắp xếp theo độ dài giảm dần -> khi match, ưu tiên tên ngành dài/cụ thể hơn.
    """
    try:
        result = collection.get(include=["metadatas"])
        metadatas = result.get("metadatas", []) or []
        values = {m.get("nganh_hoc") for m in metadatas if m.get("nganh_hoc") and m.get("nganh_hoc") != "Chung"}
        return sorted(values, key=len, reverse=True)
    except Exception as e:
        print(f"⚠️  Không lấy được danh sách ngành: {e}")
        return []


def _normalize_str(s: str) -> str:
    """Chuẩn hóa chuỗi: bỏ dấu ngoặc, gạch ngang, en-dash, gạch dưới và khoảng trắng thừa."""
    s = s.replace("(", "").replace(")", "")
    s = s.replace("-", " ").replace("–", " ").replace("_", " ")
    return " ".join(s.split())


# Bảng viết tắt tại module level — tạo 1 lần, dùng lại mỗi khi gọi _expand_abbreviations()
ABBREVIATIONS = {
    "clc":   "chất lượng cao",
    "ctclc": "chương trình chất lượng cao",
    "tt":    "tiên tiến",
    "cttt":  "chương trình tiên tiến",
    "cntt":  "công nghệ thông tin",
    "ktpm":  "kỹ thuật phần mềm",
    "ktmt":  "kỹ thuật máy tính",
    "httt":  "hệ thống thông tin",
    "khmt":  "khoa học máy tính",
    "attt":  "an toàn thông tin",
    "ktd":   "kỹ thuật điện",
    "ktxd":  "kỹ thuật xây dựng",
    "qtkd":  "quản trị kinh doanh",
    "tcnh":  "tài chính ngân hàng",
    "kdqt":  "kinh doanh quốc tế",
    "tmdt":  "thương mại điện tử",
}


def _expand_abbreviations(text: str) -> str:
    """
    Mở rộng toàn bộ viết tắt trong chuỗi bằng cách tokenize theo khoảng trắng.
    Ví dụ: 'ktpm clc' -> 'kỹ thuật phần mềm chất lượng cao'
    """
    # Tokenize, mở rộng từng token, ghép lại
    tokens = text.split()
    expanded = [ABBREVIATIONS.get(tok, tok) for tok in tokens]
    return " ".join(expanded)


def match_nganh(user_query, nganh_values):
    query_lower = user_query.lower().strip()

    # Bước 1: Mở rộng viết tắt theo token (xử lý đúng "ktpm clc", "cntt clc", v.v.)
    query_expanded = _expand_abbreviations(query_lower)

    # Chuẩn hóa query sau khi mở rộng
    query_norm = _normalize_str(query_expanded)

    # Từ khóa phân biệt chương trình đặc biệt — nếu có trong query, không được match nhầm ngành gốc
    SPECIAL_KEYWORDS = {"chất", "lượng", "cao", "tiên", "tiến"}
    query_words = set(query_norm.split())
    has_special = bool(query_words & SPECIAL_KEYWORDS)

    # Bước 2: Tìm khớp chính xác tên đầy đủ (ưu tiên ngành dài / cụ thể hơn).
    # Nếu query chứa từ khóa đặc biệt (clc/tt) nhưng tên ngành là ngành gốc -> bỏ qua.
    for value in nganh_values:
        val_lower = value.lower()
        val_norm = _normalize_str(val_lower)
        val_has_special = bool(set(val_norm.split()) & SPECIAL_KEYWORDS)
        if val_lower in query_norm or val_norm in query_norm:
            if has_special and not val_has_special:
                continue  # Query có clc/tt nhưng ngành này là ngành gốc -> bỏ qua
            return value  # Trúng tên đầy đủ -> chốt ngay!

    # Bước 3: Keyword scoring — tìm ngành có số từ khóa khớp với query cao nhất.
    # Giải quyết "ktpm clc" -> "kỹ thuật phần mềm chất lượng cao":
    # ngành CLC khớp thêm {chất, lượng, cao} so với ngành gốc -> score cao hơn.
    STOPWORDS = {"về", "của", "và", "là", "có", "cho", "với", "các", "ngành",
                 "hỏi", "xem", "tìm", "hiểu", "như", "thế", "nào", "gì",
                 "bao", "nhiêu", "tín", "chỉ", "môn", "học", "năm", "kỳ"}
    meaningful_keywords = query_words - STOPWORDS

    if len(meaningful_keywords) >= 2:
        best_match_kw = None
        best_score_kw = 0
        for value in nganh_values:
            val_norm = _normalize_str(value.lower())
            val_words = set(val_norm.split())
            # Đếm số từ khóa của query khớp với tên ngành
            matched_kw = meaningful_keywords & val_words
            score = len(matched_kw)
            # Chỉ chấp nhận nếu >= 80% từ khóa meaningful khớp
            if score >= len(meaningful_keywords) * 0.8 and score > best_score_kw:
                best_match_kw = value
                best_score_kw = score
        if best_match_kw:
            return best_match_kw

    # Bước 4: Tìm tên gốc (phần trước dấu ngoặc hoặc –), không bao gồm hậu tố CLC/TT
    best_match = None
    best_len = 0
    for value in nganh_values:
        core = value.split("(")[0].split("–")[0].split(" - ")[0].strip().lower()
        core_norm = _normalize_str(core)
        if core_norm and core_norm in query_norm and len(core_norm) > best_len:
            best_match = value
            best_len = len(core_norm)

    return best_match


def fetch_full_context_for_nganh(collection, nganh_value):
    #Lấy TOÀN BỘ chunk thuộc đúng 1 ngành, gắn kèm Header Path để AI hiểu cấu trúc.
    result = collection.get(where={"nganh_hoc": nganh_value}, include=["documents", "metadatas"])
    docs = result.get("documents", []) or []
    metas = result.get("metadatas", []) or []
    
    context_pieces = []
    for doc, meta in zip(docs, metas):
        header = meta.get("header_path", "Không rõ")
        # Gắn thêm đường dẫn tiêu đề vào trước nội dung để AI không bị lạc trôi
        context_pieces.append(f"--- [Mục: {header}] ---\n{doc}")
        
    return "\n\n".join(context_pieces)


def setup_chatbot(persist_dir="./vector_db"):
    load_dotenv(override=True)
    google_api_key = os.getenv("GOOGLE_API_KEY")

    if not google_api_key:
        print("❌ LỖI: Chưa tìm thấy GOOGLE_API_KEY trong file .env")
        return None

    if not os.path.exists(persist_dir):
        print(f"❌ LỖI: Thư mục CSDL {persist_dir} không tồn tại. Vui lòng chạy retriever.py trước.")
        return None

    print("Đang khởi động não bộ AI ...")
    Settings.llm = GoogleGenAI(
        model="gemini-3.1-flash-lite", 
        api_key=google_api_key, 
        temperature=0.0)
    
    print(f"Đang nạp embedding model ({EMBED_MODEL_NAME}, device={DEVICE})...")
    Settings.embed_model = HuggingFaceEmbedding(
        model_name=EMBED_MODEL_NAME,
        trust_remote_code=True,
        device=DEVICE,
    )

    print("Đang kết nối với Thư viện dữ liệu Đại học Cần Thơ...")
    db = chromadb.PersistentClient(path=persist_dir)
    try:
        chroma_collection = db.get_collection("ctu_courses")
    except Exception:
        print("❌ LỖI: Chưa tìm thấy collection 'ctu_courses'. Vui lòng chạy retriever.py trước.")
        return None

    if chroma_collection.count() == 0:
        print("❌ LỖI: Collection 'ctu_courses' đang TRỐNG (0 vector). Vui lòng chạy retriever.py để nạp dữ liệu.")
        return None

    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    index = VectorStoreIndex.from_vector_store(vector_store, embed_model=Settings.embed_model)

    print("Đang thiết lập hệ thống tư vấn...")
    qa_template = PromptTemplate(QA_PROMPT_STR)

    # Dùng cho câu hỏi KHÔNG nêu rõ 1 ngành cụ thể (ví dụ so sánh nhiều ngành, hỏi chung về trường)
    print("Đang thiết lập hệ thống Hybrid Search...")

    # Khởi tạo Vector Retriever (Tìm theo ngữ nghĩa)
    vector_retriever = index.as_retriever(similarity_top_k=20)
    
    # Khởi tạo BM25 Retriever (Tìm theo từ khóa chính xác)
    # Lấy toàn bộ dữ liệu từ ChromaDB để nạp vào thuật toán BM25
    all_data = chroma_collection.get(include=["documents", "metadatas"])
    nodes = []
    for doc, meta in zip(all_data.get("documents", []), all_data.get("metadatas", [])):
        nodes.append(TextNode(text=doc, metadata=meta))
    
    bm25_retriever = BM25Retriever.from_defaults(nodes=nodes, similarity_top_k=20)
    
    #Hợp nhất bằng thuật toán RRF (Reciprocal Rank Fusion)
    hybrid_retriever = QueryFusionRetriever(
        [vector_retriever, bm25_retriever],
        similarity_top_k=20,
        num_queries=1,  # Chỉ dùng nguyên bản câu hỏi của sinh viên
        mode="reciprocal_rerank",
    )
    
    # Đóng gói thành Query Engine
    query_engine = RetrieverQueryEngine.from_args(
        retriever=hybrid_retriever,
        response_synthesizer=get_response_synthesizer(
            response_mode="tree_summarize",
            text_qa_template=qa_template
        )
    )

    nganh_values = get_distinct_nganh(chroma_collection)
    print(f"   -> Đã nhận diện {len(nganh_values)} ngành trong CSDL ({chroma_collection.count()} vector tổng).")

    return {
        "query_engine": query_engine,
        "chroma_collection": chroma_collection,
        "nganh_values": nganh_values,
        "qa_template": qa_template,
    }


def ask(chatbot_state, user_input, chat_history: list = None):
    """
    Nếu câu hỏi nêu rõ tên 1 ngành đang có trong CSDL -> lấy TOÀN BỘ nội dung ngành đó.
    Nếu không rõ ngành -> tìm trong lịch sử chat xem trước đó đang nói về ngành nào.
    Nếu vẫn không rõ -> dùng Hybrid RAG thông thường.

    chat_history: Danh sách các dict {role: 'user'|'assistant', content: str}
                  đại diện cho lịch sử hội thoại trước đó (không bao gồm câu hỏi hiện tại).
    """
    history_str = build_history_str(chat_history or [])

    # BƯỚC 1: Tìm ngành trong câu hỏi hiện tại
    matched = match_nganh(user_input, chatbot_state["nganh_values"])

    # BƯỚC 2: Nếu không tìm thấy, duyệt lịch sử chat để tìm ngành được đề cập gần nhất
    if not matched and chat_history:
        for msg in reversed(chat_history):
            if msg.get("role") == "user":
                matched_in_history = match_nganh(msg["content"], chatbot_state["nganh_values"])
                if matched_in_history:
                    matched = matched_in_history
                    break  # Lấy ngành gần nhất trong lịch sử

    # BƯỚC 3: Nếu xác định được ngành -> lấy toàn bộ context của ngành đó
    if matched:
        context = fetch_full_context_for_nganh(chatbot_state["chroma_collection"], matched)
        if context.strip():
            prompt = chatbot_state["qa_template"].format(
                context_str=context,
                history_str=history_str,
                query_str=user_input
            )
            response = Settings.llm.complete(prompt)
            return str(response)

    # BƯỚC 4: Hybrid RAG — không xác định được ngành cụ thể
    # Mở rộng search_query bằng câu hỏi trước để retriever hiểu ngữ cảnh
    search_query = user_input
    if chat_history:
        recent_user_msgs = [m["content"] for m in chat_history[-4:] if m.get("role") == "user"]
        if recent_user_msgs:
            search_query = " ".join(recent_user_msgs) + " " + user_input

    response = chatbot_state["query_engine"].query(search_query)

    # Nếu có lịch sử, build lại response với context-aware prompt
    if history_str and response.source_nodes:
        context_str = "\n\n".join(
            f"--- [Mục: {node.metadata.get('header_path', 'Không rõ')}] ---\n{node.text}"
            for node in response.source_nodes
        )
        prompt = chatbot_state["qa_template"].format(
            context_str=context_str,
            history_str=history_str,
            query_str=user_input
        )
        final_response = Settings.llm.complete(prompt)
        return str(final_response)

    return response.response



def chat_loop():
    # Truyền persist_dir tương đối so với vị trí file generator.py
    _persist_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "vector_db")
    chatbot_state = setup_chatbot(persist_dir=_persist_dir)
    if not chatbot_state:
        return

    print("\n" + "=" * 60)
    print("🎓 CHATBOT TƯ VẤN CHƯƠNG TRÌNH ĐÀO TẠO ĐẠI HỌC CẦN THƠ ĐÃ SẴN SÀNG!")
    print("💡 Gõ câu hỏi của bạn (hoặc gõ 'thoát', 'quit' để dừng).")
    print("=" * 60 + "\n")

    chat_history = []

    while True:
        user_input = input("👤 Sinh viên: ")

        if user_input.lower() in ['thoát', 'thoat', 'quit', 'exit']:
            print("🤖 Chatbot: Cảm ơn bạn! Chúc bạn một ngày học tập hiệu quả. Tạm biệt!")
            break

        if not user_input.strip():
            continue

        try:
            answer = ask(chatbot_state, user_input, chat_history=chat_history)
            print(f"\n🤖 Chatbot:\n{answer}\n")
            print("-" * 60)
            # Cập nhật lịch sử sau mỗi lượt
            chat_history.append({"role": "user", "content": user_input})
            chat_history.append({"role": "assistant", "content": answer})
        except Exception as e:
            print(f"\n❌ Lỗi hệ thống: {e}\n")


if __name__ == "__main__":
    chat_loop()