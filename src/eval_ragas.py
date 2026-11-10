# -*- coding: utf-8 -*-
"""
Chấm điểm chatbot bằng RAGAS, đọc dữ liệu từ file Excel (ragas_input_template.xlsx
đã được điền cột 'answer' và 'contexts').

Cài đặt:
    pip install ragas datasets langchain-google-genai langchain-huggingface sentence-transformers pandas openpyxl --break-system-packages

Cấu hình API key TRƯỚC khi chạy (LLM giám khảo vẫn cần API, dù embeddings dùng local):

A) Dùng Google Gemini (khớp với generator.py hiện tại của bạn):
    export GOOGLE_API_KEY="your_key_here"      # PowerShell: $env:GOOGLE_API_KEY="..."

B) Dùng OpenAI (mặc định của RAGAS, độ ổn định cao hơn với vài metric):
    export OPENAI_API_KEY="your_key_here"

Embeddings: mặc định USE_LOCAL_EMBEDDINGS=True sẽ tự tải model
"Alibaba-NLP/gte-multilingual-base" local (giống hệt generator.py), không cần API,
không tốn quota Google cho phần embedding.

Chạy:
    python eval_ragas.py
"""
import os
import re
import time
import pandas as pd
from datasets import Dataset

from ragas import evaluate
from ragas.metrics import (
    faithfulness,          # câu trả lời có bám sát ngữ cảnh (contexts) hay bịa đặt
    AnswerRelevancy,        # câu trả lời có đúng trọng tâm câu hỏi không
    context_precision,     # ngữ cảnh truy xuất có chứa nhiều thông tin thừa/nhiễu không
    context_recall,        # ngữ cảnh truy xuất có bao phủ đủ thông tin cần để trả lời không
    answer_correctness,    # so khớp answer với ground_truth (gần giống ROUGE nhưng thông minh hơn)
)

# answer_relevancy mặc định sinh 3 câu hỏi ứng viên cùng lúc (candidate_count=3) để
# tự đối chiếu -> nhiều model Gemini (vd: flash-lite) KHÔNG hỗ trợ multi-candidate,
# trả lỗi 400 INVALID_ARGUMENT "Multiple candidates is not enabled for this model".
# strictness=1 -> chỉ sinh 1 câu hỏi mỗi lần, tránh lỗi này (đổi lại kém ổn định hơn 1 chút).
answer_relevancy = AnswerRelevancy(strictness=1)

# Luôn phân giải theo thư mục chứa file .py này, để chạy từ bất kỳ đâu cũng đúng
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
EVALUATE_DIR = os.path.join(PROJECT_DIR, "data", "evaluate")
INPUT_FILE = os.path.join(EVALUATE_DIR, "ragas_input_filled.xlsx")
OUTPUT_FILE = os.path.join(EVALUATE_DIR, "ragas_ket_qua.csv")
CONTEXT_SEP = "|||"

USE_LLM_PROVIDER = "google"        # "google" hoặc "openai" -- LLM giám khảo (bắt buộc gọi API)
USE_LOCAL_EMBEDDINGS = True        # True: dùng model embedding local giống generator.py

# Phải khớp với EMBED_MODEL_NAME trong generator.py để nhất quán với retriever
LOCAL_EMBED_MODEL_NAME = "Alibaba-NLP/gte-multilingual-base"

# Chấm theo từng lô nhỏ + lưu tạm sau mỗi lô, để lỡ hết quota giữa chừng
# thì chạy lại không mất kết quả đã chấm, không tốn quota chấm lại từ đầu.
BATCH_SIZE = 5
MAX_RETRIES = 6
SECONDS_BETWEEN_BATCHES = 8

# Để trống [] -> chạy bình thường (tiếp tục các câu chưa chấm).
# Điền id vào đây -> CHỈ chấm lại đúng các câu này, kể cả khi đã có kết quả trước đó
# (sẽ tự động GHI ĐÈ kết quả cũ của các id này, không tạo dòng trùng).
# Ví dụ: ONLY_IDS = ["Q003", "Q045", "Q078"]
ONLY_IDS = ["Q002", "Q006", "Q012", "Q015", "Q017", "Q023", "Q025", "Q026", "Q030", "Q032", "Q034", "Q040", "Q050", "Q051", "Q061", "Q064", "Q074", "Q076", "Q084", "Q090", "Q092", "Q093"]

# RAGAS mặc định chạy nhiều job song song (nhiều metric x nhiều câu cùng lúc),
# rất dễ vượt rate-limit 15 req/phút của Gemini free tier -> job bị treo -> TimeoutError.
# Ép chạy TUẦN TỰ (max_workers=1) và nới timeout ra để job có đủ thời gian chờ tới lượt.
RUN_CONFIG_KWARGS = dict(
    max_workers=1,      # 1 job tại 1 thời điểm -> không làm quá tải quota
    timeout=300,         # 5 phút / job, đủ thời gian nếu phải chờ + retry
    max_retries=10,
    max_wait=90,
)


def build_llm_and_embeddings():
    from ragas.llms import LangchainLLMWrapper
    from ragas.embeddings import LangchainEmbeddingsWrapper

    # --- LLM giám khảo (vẫn cần gọi API, RAGAS cần LLM để suy luận) ---
    llm = None
    if USE_LLM_PROVIDER == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = LangchainLLMWrapper(ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", temperature=0))
    # nếu USE_LLM_PROVIDER == "openai" -> để None, RAGAS tự dùng OPENAI_API_KEY mặc định

    # --- Embeddings: local, dùng lại đúng model của generator.py ---
    embeddings = None
    if USE_LOCAL_EMBEDDINGS:
        import torch
        from langchain_huggingface import HuggingFaceEmbeddings

        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Đang nạp embedding model local ({LOCAL_EMBED_MODEL_NAME}, device={device})...")
        hf_embed = HuggingFaceEmbeddings(
            model_name=LOCAL_EMBED_MODEL_NAME,
            model_kwargs={"device": device, "trust_remote_code": True},
        )
        embeddings = LangchainEmbeddingsWrapper(hf_embed)
    else:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        embeddings = LangchainEmbeddingsWrapper(GoogleGenerativeAIEmbeddings(model="models/text-embedding-004"))

    return llm, embeddings


def evaluate_batch_with_retry(dataset_batch, metrics, llm, embeddings):
    """Chạy evaluate() cho 1 lô, tự retry khi gặp lỗi 429 (hết quota / rate limit)."""
    from ragas.run_config import RunConfig

    kwargs = {"run_config": RunConfig(**RUN_CONFIG_KWARGS)}
    if llm is not None:
        kwargs["llm"] = llm
    if embeddings is not None:
        kwargs["embeddings"] = embeddings

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return evaluate(dataset_batch, metrics=metrics, **kwargs)
        except Exception as e:
            msg = str(e)
            is_rate_limit = "429" in msg or "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower()
            if not is_rate_limit or attempt == MAX_RETRIES:
                raise
            m = re.search(r"retryDelay['\"]?:\s*['\"]?(\d+)", msg)
            wait_s = int(m.group(1)) if m else min(60, 15 * attempt)
            wait_s += 3
            print(f"   Hết quota / bị giới hạn tốc độ. Chờ {wait_s}s rồi thử lại lô này "
                  f"(lần {attempt}/{MAX_RETRIES})...")
            time.sleep(wait_s)


def main():
    df = pd.read_excel(INPUT_FILE, sheet_name="ragas_data")

    # Bỏ các dòng chưa điền answer/contexts
    df = df.dropna(subset=["answer", "contexts"])
    df = df[(df["answer"].str.strip() != "") & (df["contexts"].str.strip() != "")]
    df = df.reset_index(drop=True)

    if len(df) == 0:
        print("Chưa có dòng nào được điền đủ 'answer' và 'contexts'. Hãy điền file Excel trước.")
        return

    # Nếu đã có kết quả từ lần chạy trước -> chỉ chấm tiếp các id còn thiếu
    done_ids = set()
    if os.path.exists(OUTPUT_FILE):
        prev = pd.read_csv(OUTPUT_FILE)
        done_ids = set(prev["id"].tolist())
        print(f"Tìm thấy kết quả cũ: {OUTPUT_FILE} -> đã chấm {len(done_ids)} câu, sẽ bỏ qua.")

    if ONLY_IDS:
        todo = df[df["id"].isin(ONLY_IDS)]
        print(f"Chế độ chọn câu: sẽ CHẤM LẠI {len(todo)} câu trong ONLY_IDS "
              f"(ghi đè kết quả cũ nếu có).")
    else:
        todo = df[~df["id"].isin(done_ids)]
        print(f"Số câu cần chấm: {len(todo)} / {len(df)}")

    if len(todo) == 0:
        print("Không có câu nào cần chấm.")
        return

    metrics = [faithfulness, answer_relevancy, context_precision, context_recall, answer_correctness]
    llm, embeddings = build_llm_and_embeddings()

    num_batches = (len(todo) + BATCH_SIZE - 1) // BATCH_SIZE
    for b in range(num_batches):
        batch_df = todo.iloc[b * BATCH_SIZE:(b + 1) * BATCH_SIZE]
        print(f"\n--- Lô {b+1}/{num_batches} ({len(batch_df)} câu) ---")

        records = {
            "question": batch_df["question"].tolist(),
            "answer": batch_df["answer"].tolist(),
            "contexts": [str(c).split(CONTEXT_SEP) for c in batch_df["contexts"].tolist()],
            "ground_truth": batch_df["ground_truth"].tolist(),
        }
        dataset_batch = Dataset.from_dict(records)

        try:
            result = evaluate_batch_with_retry(dataset_batch, metrics, llm, embeddings)
        except Exception as e:
            print(f"   Lô này lỗi sau {MAX_RETRIES} lần thử, dừng lại tại đây: {e}")
            print(f"   Các lô trước đã lưu an toàn trong {OUTPUT_FILE}. "
                  f"Chạy lại script sau để tiếp tục từ lô này.")
            return

        result_df = result.to_pandas()
        result_df["id"] = batch_df["id"].values
        result_df["loai_cau_hoi"] = batch_df["loai_cau_hoi"].values
        result_df["nguon"] = batch_df["nguon"].values

        # Upsert theo id: nếu id đã có trong file kết quả -> ghi đè; chưa có -> thêm mới.
        # Nhờ vậy vừa hỗ trợ chạy tiếp (resume) vừa hỗ trợ chấm lại chọn lọc (ONLY_IDS)
        # mà không bao giờ tạo dòng trùng id.
        if os.path.exists(OUTPUT_FILE):
            existing = pd.read_csv(OUTPUT_FILE)
            existing = existing[~existing["id"].isin(result_df["id"])]
            combined = pd.concat([existing, result_df], ignore_index=True)
        else:
            combined = result_df
        combined.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
        print(f"   Đã lưu lô {b+1} vào {OUTPUT_FILE}.")

        if b < num_batches - 1:
            time.sleep(SECONDS_BETWEEN_BATCHES)

    final_df = pd.read_csv(OUTPUT_FILE)
    print("\n=== Điểm trung bình toàn bộ (tất cả các lô đã chấm) ===")
    print(final_df[["faithfulness", "answer_relevancy", "context_precision",
                     "context_recall", "answer_correctness"]].mean())

    print("\n=== Điểm trung bình theo loại câu hỏi ===")
    print(final_df.groupby("loai_cau_hoi")[
        ["faithfulness", "answer_relevancy", "context_precision",
         "context_recall", "answer_correctness"]
    ].mean())

    print(f"\nĐã lưu chi tiết vào: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
