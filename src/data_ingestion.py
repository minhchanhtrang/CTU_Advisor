import os
import glob
import asyncio
import nest_asyncio
import warnings
import time

from llama_parse import LlamaParse
from dotenv import load_dotenv

nest_asyncio.apply()
warnings.filterwarnings("ignore", category=DeprecationWarning)

def load_environment():
    load_dotenv()
    api_key = os.getenv("LLAMA_CLOUD_API_KEY")
    if not api_key:
        raise ValueError("❌ LỖI: Chưa tìm thấy LLAMA_CLOUD_API_KEY trong file .env")
    return api_key

async def parse_documents_async(raw_data_dir="data/raw", processed_dir="data/processed"):
    if not os.path.exists(raw_data_dir):
        print(f"Thư mục {raw_data_dir} chưa tồn tại.")
        return []

    # Tự động tạo thư mục chứa file markdown nếu chưa có
    os.makedirs(processed_dir, exist_ok=True)

    api_key = load_environment()
    pdf_files = glob.glob(os.path.join(raw_data_dir, "*.pdf"))
    
    if not pdf_files:
        print("Không tìm thấy file PDF nào.")
        return []

    print(f"Tìm thấy {len(pdf_files)} file. Đang khởi tạo LlamaParse...")
    
    parser = LlamaParse(
        api_key=api_key,
        result_type="markdown", 
        language="vi",
        verbose=False 
    )

    all_documents = []
    
    for file_path in pdf_files:
        clean_path = os.path.abspath(file_path).replace("\\", "/")
        print(f"\nĐang xử lý: {clean_path}")
        
        # Định nghĩa tên file .md đầu ra (thay thế đuôi .pdf thành .md)
        base_name = os.path.basename(clean_path)
        md_filename = base_name.replace(".pdf", ".md")
        out_path = os.path.join(processed_dir, md_filename)
        
        max_retries = 3
        success = False
        
        for attempt in range(1, max_retries + 1):
            print(f"  -> Lần tải {attempt}/{max_retries}...")
            try:
                # Sử dụng hàm bất đồng bộ aload_data để kết nối ổn định hơn
                docs = await parser.aload_data(clean_path)
                
                if docs and len(docs) > 0:
                    all_documents.extend(docs)
                    print(f"  -> ✅ HOÀN HẢO! Trích xuất thành công {len(docs)} phần tử.")
                    
                    with open(out_path, "w", encoding="utf-8") as f:
                        for doc in docs:
                            # doc.text chứa nội dung dạng Markdown của từng phần
                            f.write(doc.text + "\n\n")
                    print(f"  -> 💾 Đã lưu file Markdown tại: {out_path}")
                    
                    success = True
                    break # Thành công thì thoát vòng lặp Retry
                else:
                    print("  -> ❌ API trả về rỗng.")
                    break
                    
            except Exception as e:
                print(f"  -> Lỗi kết nối: {e}")
                if attempt < max_retries:
                    print("  -> Đang đợi 3 giây để thử lại...")
                    time.sleep(3)
                else:
                    print("  -> 3 lần thử thất bại.")
                    
        if not success:
            print(f"Vui lòng kiểm tra lại mạng hoặc dung lượng file {clean_path}.")

    return all_documents

if __name__ == "__main__":
    # Điểm neo chạy chương trình Async
    docs = asyncio.run(parse_documents_async())
    
    if docs:
        print("\n" + "="*50)
        print(" BẢN XEM TRƯỚC NỘI DUNG (1000 ký tự đầu) ")
        print("="*50)
        print(docs[0].text[:1000])