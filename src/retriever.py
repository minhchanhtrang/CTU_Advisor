import os

os.environ["HF_HOME"] = r"D:\AI_Models_Cache"
os.environ["LLAMA_INDEX_CACHE_DIR"] = r"D:\AI_Models_Cache"

import json
import time
import logging
import hashlib
import chromadb
import torch
from dotenv import load_dotenv

from llama_index.core import VectorStoreIndex, StorageContext, Settings, SimpleDirectoryReader
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.node_parser import MarkdownNodeParser

try:
    import frontmatter  # pip install python-frontmatter
except ImportError:
    frontmatter = None

# ============================================================
# CẤU HÌNH LOGGING
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("build_vector_db.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BATCH_SIZE = 20                 # Số nodes xử lý mỗi batch khi embedding
MAX_RETRIES = 5                 # Số lần thử lại khi gọi API lỗi
RETRY_BACKOFF_SECONDS = 5
STATE_FILE_DEFAULT = "processed_state.json"  # Lưu trạng thái các file đã xử lý (theo nội dung)

# Tự động phát hiện CUDA
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
EMBED_BATCH_SIZE = 16
EMBED_MODEL_NAME = "Alibaba-NLP/gte-multilingual-base"


# ============================================================
# 1. QUẢN LÝ TRẠNG THÁI FILE ĐÃ XỬ LÝ (để bỏ qua file không đổi)
# ============================================================
def compute_file_hash(file_path):
    """Tính SHA256 dựa trên nội dung file -> dùng để phát hiện file có thay đổi hay chưa."""
    try:
        with open(file_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception as e:
        logger.warning("Không thể đọc file để tính hash %s: %s", file_path, e)
        return None


def make_doc_id(file_path):
    """ID ổn định cho mỗi file, dùng làm ref_doc_id trong vector store."""
    return hashlib.md5(file_path.encode("utf-8")).hexdigest()


def load_state(state_file):
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Không đọc được state file %s (%s) -> coi như chạy lần đầu.", state_file, e)
    return {}


def save_state(state_file, state):
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def diff_files(processed_dir, old_state):
    """
    Quét toàn bộ file .md hiện có trong processed_dir, so với state cũ để phân loại:
      - unchanged: hash giống cũ -> bỏ qua, không xử lý lại
      - changed:   file mới hoặc nội dung đã đổi -> cần xử lý + embedding lại
      - deleted:   có trong state cũ nhưng không còn trên ổ cứng -> cần xóa khỏi vector DB
    Trả về (changed_paths, unchanged_paths, deleted_paths, new_state)
    """
    current_files = {}
    for root, _, files in os.walk(processed_dir):
        for fname in files:
            if fname.lower().endswith(".md"):
                full_path = os.path.abspath(os.path.join(root, fname))
                current_files[full_path] = compute_file_hash(full_path)

    changed, unchanged = [], []
    for path, file_hash in current_files.items():
        old_hash = old_state.get(path, {}).get("hash")
        if file_hash is not None and file_hash == old_hash:
            unchanged.append(path)
        else:
            changed.append(path)

    deleted = [path for path in old_state.keys() if path not in current_files]

    new_state = dict(old_state)
    for path, file_hash in current_files.items():
        new_state[path] = {"hash": file_hash, "doc_id": make_doc_id(path)}
    for path in deleted:
        new_state.pop(path, None)

    return changed, unchanged, deleted, new_state


# ============================================================
# 2. BÓC TÁCH FRONTMATTER
# ============================================================
def extract_frontmatter_metadata(doc):
    """Bóc tách YAML frontmatter bằng thư viện `python-frontmatter`."""
    try:
        if frontmatter is None:
            logger.warning(
                "Chưa cài 'python-frontmatter' -> bỏ qua bóc tách metadata cho %s. "
                "Cài bằng: pip install python-frontmatter",
                doc.metadata.get("file_path", "unknown")
            )
            return doc

        post = frontmatter.loads(doc.text)
        if post.metadata:
            for key, value in post.metadata.items():
                if isinstance(value, (list, tuple)):
                    doc.metadata[key] = ", ".join(str(v) for v in value)
                elif isinstance(value, (str, int, float, bool)):
                    doc.metadata[key] = value
                else:
                    doc.metadata[key] = str(value)
        doc.set_content(post.content.strip())

    except Exception as e:
        logger.warning(
            "Lỗi khi bóc tách frontmatter cho file %s: %s -> giữ nguyên nội dung gốc.",
            doc.metadata.get("file_path", "unknown"), e
        )
    return doc


def apply_default_metadata(doc):
    """Gắn metadata mặc định nếu thiếu, và gán doc_id ổn định theo đường dẫn file."""
    if "trinh_do" not in doc.metadata:
        doc.metadata["trinh_do"] = "Chung"
    if "nganh_hoc" not in doc.metadata:
        doc.metadata["nganh_hoc"] = "Chung"
    if "loai_tai_lieu" not in doc.metadata:
        doc.metadata["loai_tai_lieu"] = "Tài liệu khác"

    file_path = doc.metadata.get("file_path", "")
    if file_path:
        doc.doc_id = make_doc_id(os.path.abspath(file_path))

    doc.excluded_llm_metadata_keys = []
    doc.excluded_embed_metadata_keys = ["file_path", "file_size", "creation_date", "last_modified_date"]
    return doc


# ============================================================
# 3. EMBEDDING VỚI RETRY/BACKOFF
# ============================================================
def build_index_with_retry(nodes, storage_context, index=None, batch_size=BATCH_SIZE):
    """
    Build/insert vào VectorStoreIndex theo từng batch, có retry khi lỗi tạm thời.
    Nếu index=None thì tạo index mới; nếu đã có index (collection cũ) thì insert tiếp vào đó.

    Trả về (index, failed_doc_ids): failed_doc_ids là tập doc_id của các FILE có node
    embedding thất bại sau khi hết lượt retry -> để build_vector_database loại các file
    này khỏi state, đảm bảo chúng được xử lý lại ở lần chạy sau (không bị bỏ sót vĩnh viễn).
    """
    total = len(nodes)
    failed_doc_ids = set()
    if total == 0:
        return index, failed_doc_ids

    num_batches = (total + batch_size - 1) // batch_size

    for i in range(0, total, batch_size):
        batch = nodes[i:i + batch_size]
        batch_num = i // batch_size + 1
        logger.info("  -> Đang xử lý batch %d/%d (%d nodes)...", batch_num, num_batches, len(batch))

        success = False
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if index is None:
                    index = VectorStoreIndex(
                        batch,
                        storage_context=storage_context,
                        show_progress=True
                    )
                else:
                    for node in batch:
                        index.insert_nodes([node])
                success = True
                break
            except Exception as e:
                wait = RETRY_BACKOFF_SECONDS * attempt
                logger.warning(
                    "Lỗi khi embedding batch %d (lần thử %d/%d): %s. Thử lại sau %ds...",
                    batch_num, attempt, MAX_RETRIES, e, wait
                )
                if attempt == MAX_RETRIES:
                    logger.error(
                        "Batch %d thất bại sau %d lần thử. Các file liên quan sẽ được đánh dấu "
                        "'CHƯA xử lý' để tự động thử lại ở lần chạy sau.", batch_num, MAX_RETRIES
                    )
                else:
                    time.sleep(wait)

        if not success:
            for node in batch:
                ref_id = getattr(node, "ref_doc_id", None)
                if ref_id:
                    failed_doc_ids.add(ref_id)

    return index, failed_doc_ids


# ============================================================
# 4. HÀM CHÍNH
# ============================================================
def build_vector_database(
    processed_dir="data/processed",
    persist_dir="./vector_db",
    state_file=STATE_FILE_DEFAULT,
    reset_collection=False, #xóa toàn bộ collection cũ trước khi build (build lại từ đầu, mất hết incremental state).
    force_reprocess_all=False, #bỏ qua cơ chế skip-file-không-đổi, xử lý lại toàn bộ file (nhưng không xóa collection).
):
    load_dotenv(override=True)
    google_api_key = os.getenv("GOOGLE_API_KEY")

    if not google_api_key:
        logger.error("Chưa tìm thấy GOOGLE_API_KEY trong file .env")
        return None

    if not os.path.exists(processed_dir) or not os.listdir(processed_dir):
        logger.error("Thư mục %s trống hoặc không tồn tại. Hãy chuẩn bị các file .md trước!", processed_dir)
        return None

    # --- Kết nối ChromaDB trước, để có thể xóa node cũ khi cần ---
    db = chromadb.PersistentClient(path=persist_dir)
    if reset_collection:
        try:
            db.delete_collection("ctu_courses")
            logger.info("Đã xóa collection cũ 'ctu_courses' (reset_collection=True).")
        except Exception:
            pass
        old_state = {}  # reset toàn bộ -> coi như chưa xử lý file nào
    else:
        old_state = load_state(state_file)

    chroma_collection = db.get_or_create_collection("ctu_courses")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # So sánh trạng thái file: file nào mới/đổi, file nào giữ nguyên, file nào đã xóa 
    logger.info("1. Đang kiểm tra file nào đã xử lý, file nào mới/thay đổi...")
    if force_reprocess_all:
        changed_paths, unchanged_paths, deleted_paths, new_state = diff_files(processed_dir, {})
    else:
        changed_paths, unchanged_paths, deleted_paths, new_state = diff_files(processed_dir, old_state)

    logger.info("  -> File mới/thay đổi: %d | File giữ nguyên (bỏ qua): %d | File đã xóa: %d",
                len(changed_paths), len(unchanged_paths), len(deleted_paths))

    # Xóa vector của các file đã bị xóa khỏi ổ cứng hoặc sắp được xử lý lại 
    paths_to_clear = set(deleted_paths) | set(changed_paths)
    for path in paths_to_clear:
        doc_id = old_state.get(path, {}).get("doc_id") or make_doc_id(path)
        try:
            vector_store.delete(ref_doc_id=doc_id)
        except Exception:
            pass  # node chưa từng tồn tại (file mới hoàn toàn) -> không sao

    if not changed_paths:
        logger.info("✅ Không có file mới hoặc thay đổi.")
        save_state(state_file, new_state)
        return VectorStoreIndex.from_vector_store(vector_store=vector_store, storage_context=storage_context)

    # Chỉ đọc và xử lý các file MỚI/THAY ĐỔI
    logger.info("2. Đang đọc nội dung %d file cần xử lý...", len(changed_paths))
    reader = SimpleDirectoryReader(input_files=changed_paths)
    documents = reader.load_data()
    logger.info("  -> Đã tải %d trang tài liệu thô.", len(documents))

    logger.info("3. Đang bóc tách Frontmatter để cấu trúc hóa Metadata...")
    valid_documents = []
    skipped = []
    for doc in documents:
        try:
            doc = extract_frontmatter_metadata(doc)
            doc = apply_default_metadata(doc)
            valid_documents.append(doc)
        except Exception as e:
            file_path = doc.metadata.get("file_path", "unknown")
            logger.error("Bỏ qua file lỗi %s: %s", file_path, e)
            skipped.append(file_path)

    logger.info("  -> Xử lý thành công %d/%d file. Bỏ qua %d file lỗi.",
                len(valid_documents), len(documents), len(skipped))
    if skipped:
        logger.info("  -> Danh sách file bị bỏ qua: %s", skipped)
        for path in skipped:
            new_state.pop(os.path.abspath(path), None)  # không đánh dấu là "đã xử lý" nếu lỗi

    if not valid_documents:
        logger.warning("Không có tài liệu hợp lệ nào trong batch này.")
        save_state(state_file, new_state)
        return VectorStoreIndex.from_vector_store(vector_store=vector_store, storage_context=storage_context)
    
    logger.info("4. Đang khởi tạo mô hình Embedding...")
    Settings.embed_model = HuggingFaceEmbedding(
        model_name=EMBED_MODEL_NAME,
        trust_remote_code=True,
        device=DEVICE,
        embed_batch_size=EMBED_BATCH_SIZE,
    )

    logger.info("5. Đang băm nhỏ văn bản...")
    md_parser = MarkdownNodeParser()
    final_nodes = md_parser.get_nodes_from_documents(valid_documents)
    logger.info("  -> Đã băm thành công %d mảnh dữ liệu (Nodes).", len(final_nodes))

    logger.info("6. Đang tạo Embedding và lưu vào ChromaDB...")
    # Nếu collection đã có dữ liệu từ trước (không reset) thì load lại index hiện có để insert tiếp
    existing_index = None
    if chroma_collection.count() > 0:
        existing_index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store, storage_context=storage_context
        )

    index, failed_doc_ids = build_index_with_retry(final_nodes, storage_context, index=existing_index)

    if failed_doc_ids:
        logger.warning("⚠️  %d file có node embedding thất bại sau %d lần thử -> sẽ KHÔNG được đánh dấu "
                        "'đã xử lý', để tự động retry ở lần chạy kế tiếp.", len(failed_doc_ids), MAX_RETRIES)
        for path, info in list(new_state.items()):
            if info.get("doc_id") in failed_doc_ids:
                new_state.pop(path, None)
                logger.warning("   -> Sẽ xử lý lại: %s", path)

    if index is None:
        logger.error("Build index thất bại hoàn toàn.")
        return None

    # --- 4. Lưu lại trạng thái sau khi xử lý thành công ---
    save_state(state_file, new_state)

    logger.info("HOÀN TẤT THÀNH CÔNG! Cơ sở dữ liệu Vector tại '%s'.", persist_dir)
    logger.info("File xử lý lần này: %d | File bỏ qua (không đổi): %d | Tổng nodes mới: %d",
                len(changed_paths), len(unchanged_paths), len(final_nodes))
    return index

if __name__ == "__main__":
    build_vector_database(reset_collection=True)
    #True : xóa sạch vector cũ
    #False : Chỉ xử lý file mới thêm vào