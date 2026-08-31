# -*- coding: utf-8 -*-
"""
Chạy 100 câu hỏi qua chatbot (dùng lại generator.py hiện có của bạn), lấy về
answer + contexts cho từng câu, rồi ghi thẳng vào ragas_input_template.xlsx.

ĐẶT FILE NÀY CÙNG THƯ MỤC với generator.py (và vector_db/ đã build sẵn) rồi chạy:
    python run_batch_and_export.py

Yêu cầu: đã cài đủ dependency của generator.py (torch, chromadb, llama_index...)
và đã build vector_db từ trước (bằng retriever.py).
"""
import os
import time
import re
import pandas as pd

from generator import (
    setup_chatbot,
    match_nganh,
    fetch_full_context_for_nganh,
)
from llama_index.core import Settings

# Luôn phân giải theo thư mục chứa file .py này, để chạy từ bất kỳ đâu cũng đúng
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_XLSX = os.path.join(SCRIPT_DIR, "ragas_input_template.xlsx")
OUTPUT_XLSX = os.path.join(SCRIPT_DIR, "ragas_input_filled.xlsx")
CONTEXT_SEP = "|||"

# Gemini free tier: 15 request/phút -> tối thiểu ~4s/câu. Đặt dư ra cho an toàn.
SECONDS_BETWEEN_REQUESTS = 5
MAX_RETRIES = 6

# Để trống [] -> chạy bình thường (tiếp tục các câu chưa có answer).
# Điền id vào đây -> CHỈ hỏi lại đúng các câu này, kể cả khi đã có answer trước đó
# (sẽ tự động GHI ĐÈ answer/contexts cũ của các id này).
# Ví dụ: ONLY_IDS = ["Q003", "Q045", "Q078"]
ONLY_IDS = ["Q002", "Q006", "Q012", "Q015", "Q017", "Q023", "Q025", "Q026", "Q030", "Q032", "Q034", "Q040", "Q050", "Q051", "Q061", "Q064", "Q074", "Q076", "Q084", "Q090", "Q092", "Q093"]


def ask_with_context(chatbot_state, user_input):
    """
    Giống hệt logic của ask() trong generator.py (bản không có lịch sử chat),
    nhưng trả thêm 'contexts' để phục vụ RAGAS.
    Trả về: (answer: str, contexts: list[str])
    """
    matched = match_nganh(user_input, chatbot_state["nganh_values"])

    # Nhánh 1: khớp tên ngành -> lấy toàn bộ context của ngành đó
    if matched:
        context = fetch_full_context_for_nganh(chatbot_state["chroma_collection"], matched)
        if context.strip():
            prompt = chatbot_state["qa_template"].format(
                context_str=context, history_str="", query_str=user_input
            )
            response = Settings.llm.complete(prompt)
            return str(response), [context]

    # Nhánh 2: hybrid retriever (BM25 + vector)
    response = chatbot_state["query_engine"].query(user_input)
    contexts = [node.get_content() for node in response.source_nodes]
    return response.response, contexts


def ask_with_context_retry(chatbot_state, user_input):
    """
    Gọi ask_with_context() kèm retry khi gặp lỗi 429 (RESOURCE_EXHAUSTED).
    Ưu tiên đọc thời gian chờ ('retryDelay') mà Google trả về, nếu không có thì
    tăng dần thời gian chờ (exponential backoff).
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return ask_with_context(chatbot_state, user_input)
        except Exception as e:
            msg = str(e)
            is_rate_limit = "429" in msg or "RESOURCE_EXHAUSTED" in msg
            if not is_rate_limit or attempt == MAX_RETRIES:
                print(f"   Lỗi (không retry nữa): {e}")
                return "", []

            m = re.search(r"retryDelay['\"]?:\s*['\"]?(\d+)", msg)
            wait_s = int(m.group(1)) if m else min(60, 10 * attempt)
            wait_s += 2  # buffer an toàn
            print(f"   Bị giới hạn tốc độ (429). Chờ {wait_s}s rồi thử lại "
                  f"(lần {attempt}/{MAX_RETRIES})...")
            time.sleep(wait_s)


def main():
    df = pd.read_excel(INPUT_XLSX, sheet_name="ragas_data")

    # Nếu đã có file kết quả từ lần chạy trước -> tiếp tục từ đó, không hỏi lại
    # các câu đã có answer (giúp không mất tiến độ khi bị 429 giữa chừng).
    if os.path.exists(OUTPUT_XLSX):
        prev = pd.read_excel(OUTPUT_XLSX, sheet_name="ragas_data")
        if "answer" in prev.columns:
            df["answer"] = prev["answer"]
            df["contexts"] = prev["contexts"]
            print(f"Tìm thấy kết quả cũ: {OUTPUT_XLSX} -> sẽ bỏ qua các câu đã có answer.")
    if "answer" not in df.columns:
        df["answer"] = ""
        df["contexts"] = ""
    df["answer"] = df["answer"].fillna("")
    df["contexts"] = df["contexts"].fillna("")

    if ONLY_IDS:
        # Xóa answer/contexts cũ của các id được chọn -> ép hỏi lại đúng các câu này
        mask = df["id"].isin(ONLY_IDS)
        df.loc[mask, "answer"] = ""
        df.loc[mask, "contexts"] = ""
        print(f"Chế độ chọn câu: sẽ HỎI LẠI {mask.sum()} câu trong ONLY_IDS (ghi đè kết quả cũ).")

    print("Đang khởi tạo chatbot (load vector_db, embedding model)...")
    # vector_db nằm ở thư mục gốc dự án (ngang hàng với src/), không phải trong src/
    vector_db_dir = os.path.join(SCRIPT_DIR, "..", "vector_db")
    chatbot_state = setup_chatbot(persist_dir=vector_db_dir)

    for i, row in df.iterrows():
        if ONLY_IDS and row["id"] not in ONLY_IDS:
            continue  # đang ở chế độ chọn câu -> bỏ qua các câu không nằm trong ONLY_IDS
        if str(row["answer"]).strip():
            continue  # đã có kết quả từ lần chạy trước -> bỏ qua

        q = row["question"]
        print(f"[{i+1}/{len(df)}] {q[:70]}...")
        answer, contexts = ask_with_context_retry(chatbot_state, q)
        df.at[i, "answer"] = answer
        df.at[i, "contexts"] = CONTEXT_SEP.join(contexts)

        # Lưu ngay sau MỖI câu để không mất tiến độ nếu script bị dừng/lỗi
        with pd.ExcelWriter(OUTPUT_XLSX, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="ragas_data")

        time.sleep(SECONDS_BETWEEN_REQUESTS)  # tôn trọng rate limit 15 req/phút

    print(f"\nHoàn tất. Đã lưu: {OUTPUT_XLSX}")
    print("Đổi INPUT_FILE trong eval_ragas.py thành file này rồi chạy để chấm điểm.")


if __name__ == "__main__":
    main()