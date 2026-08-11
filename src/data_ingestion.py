import os
import glob
import time
from pathlib import Path

from llama_cloud.client import LlamaCloud
from dotenv import load_dotenv

def load_environment():
    load_dotenv()
    api_key = os.getenv("LLAMA_CLOUD_API_KEY")
    if not api_key:
        raise ValueError("❌ LỖI: Chưa tìm thấy LLAMA_CLOUD_API_KEY trong file .env")
    return api_key

def parse_documents(raw_data_dir="data/raw", processed_dir="data/processed"):
    if not os.path.exists(raw_data_dir):
        print(f"Thư mục {raw_data_dir} chưa tồn tại.")
        return []

    os.makedirs(processed_dir, exist_ok=True)

    api_key = load_environment()
    pdf_files = glob.glob(os.path.join(raw_data_dir, "**", "*.pdf"), recursive=True)
    
    if not pdf_files:
        print("Không tìm thấy file PDF nào.")
        return []

    print(f"Tìm thấy {len(pdf_files)} file. Đang khởi tạo LlamaCloud client...")
    
    # Khởi tạo client
    client = LlamaCloud(token=api_key)

    all_documents = []
    
    for file_path in pdf_files:
        clean_path = os.path.abspath(file_path).replace("\\", "/")
        rel_path = os.path.relpath(file_path, raw_data_dir)
        
        out_rel_path = rel_path.replace(".pdf", ".md")
        out_path = os.path.join(processed_dir, out_rel_path)
        
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        
        if os.path.exists(out_path):
            print(f"\nBỏ qua (đã OCR): {rel_path}")
            continue

        print(f"\nĐang xử lý: {clean_path}")
        
        max_retries = 3
        success = False
        
        for attempt in range(1, max_retries + 1):
            print(f"  -> Lần tải {attempt}/{max_retries}...")
            try:
                # Upload the file
                file_obj = client.files.create(file=clean_path, purpose="parse")
                
                # Parse with agentic options
                result = client.parsing.parse(
                    file_id=file_obj.id,
                    tier="cost_effective",
                    version="latest",
                    agentic_options={
                        "custom_prompt": """You are an OCR and document-structure extraction system.

Your task is to extract the meaningful textual content from the document for
downstream RAG / semantic search.

IMPORTANT RULES:

1. OCR AND TEXT EXTRACTION
- Extract all meaningful textual content accurately.
- Preserve the original Vietnamese language, spelling, numbers, abbreviations,
  course codes, credit numbers, dates, and other factual information.
- Do NOT summarize, paraphrase, translate, infer, or invent information.
- If text is unclear, preserve the closest readable text rather than guessing.

2. REMOVE DOCUMENT HEADERS, FOOTERS, AND REPEATED TITLES
Remove content that is only document metadata or repeated page decoration,
including:
- University/institution headers repeated on every page.
- Repeated document titles.
- Page numbers such as "Trang 1", "Page 1", "1/10", etc.
- Repeated headers and footers.
- Running headers.
- Confidentiality labels, document codes, scan labels, or repeated page metadata
  when they are not part of the actual academic content.

IMPORTANT:
- Do NOT remove a title or heading if it introduces a meaningful section
  containing information.
- Keep meaningful section headings such as:
  "MỤC TIÊU ĐÀO TẠO",
  "CHUẨN ĐẦU RA",
  "KHUNG CHƯƠNG TRÌNH",
  "DANH MỤC HỌC PHẦN",
  etc.
- Remove only decorative/repeated document-level headers and footers.

3. REMOVE SIGNATURES
Do NOT extract signatures or handwritten signature marks.
Remove:
- Handwritten signatures.
- Signature images.
- Signature lines.
- Stamps/seals when they do not contain meaningful textual information.
- Names appearing only as part of a signature block.

However, preserve meaningful textual information surrounding the signature,
such as:
- Decision number.
- Date.
- Position/title of the signer.
- Official document information.

4. TABLE EXTRACTION AND TABLE FLATTENING
Tables are extremely important. Do NOT discard table content.

Convert every meaningful table into a flat, linear text representation.

DO NOT preserve the table as an HTML table.
DO NOT use complex nested Markdown tables.
DO NOT merge unrelated cells.

For each table:
- Identify the table title or section heading if available.
- Preserve all column names.
- Preserve all row values.
- Preserve the relationship between each value and its column.
- Repeat relevant contextual information for each row when necessary.

Preferred format:

TABLE: <table title>

Row 1:
Column A: value
Column B: value
Column C: value

Row 2:
Column A: value
Column B: value
Column C: value

Example:

TABLE: DANH MỤC HỌC PHẦN

Row 1:
Mã học phần: CT101
Tên học phần: Lập trình căn bản
Số tín chỉ: 3
Học kỳ: 1

Row 2:
Mã học phần: CT102
Tên học phần: Cấu trúc dữ liệu
Số tín chỉ: 3
Học kỳ: 2

5. MULTI-ROW / MULTI-COLUMN TABLES
For tables with merged cells, multi-level headers, or hierarchical rows:
- Resolve the structure into explicit key-value information.
- Repeat a parent category for child rows when necessary.
- Do not lose information contained in merged cells.

For example, if a table visually represents:

Nhóm kiến thức | Học phần | Số tín chỉ
Cơ sở ngành    | A         | 3
               | B         | 2

Output:

Row 1:
Nhóm kiến thức: Cơ sở ngành
Học phần: A
Số tín chỉ: 3

Row 2:
Nhóm kiến thức: Cơ sở ngành
Học phần: B
Số tín chỉ: 2

6. PRESERVE SEMANTIC RELATIONSHIPS
The output must remain understandable when a table row is retrieved
independently during RAG retrieval.

Every row should contain enough context to understand what the values mean.

For example, instead of:

"CT101 | Lập trình | 3"

prefer:

"Mã học phần: CT101
Tên học phần: Lập trình
Số tín chỉ: 3"

7. CHECKBOXES, SYMBOLS, AND MARKS
For checkboxes or visual marks:
- Convert meaningful checked/unchecked states into text when they convey
  information.
- Ignore purely decorative symbols.

8. DOCUMENT STRUCTURE
Preserve meaningful hierarchy using simple headings:

# Main Section
## Subsection
### Subsection

Do not create headings merely because text is visually large.

9. OUTPUT FORMAT
Produce clean plain text / Markdown suitable for:
- chunking
- embeddings
- vector databases
- RAG retrieval
- semantic search

Avoid:
- HTML
- XML
- CSS
- complex Markdown
- unnecessary formatting
- repeated headers/footers
- page numbers
- signature blocks

10. DO NOT MODIFY FACTUAL CONTENT
Do not:
- summarize
- rewrite
- translate
- correct factual information
- infer missing values
- invent table values
- combine information from unrelated sections

The final output should contain only meaningful document content,
with repeated headers/footers and signatures removed, and tables converted
into explicit flat key-value rows."""
                    },
                    output_options={
                        "markdown": {
                            "tables": {
                                "merge_continued_tables": True
                            }
                        }
                    },
                    processing_options={
                        "ocr_parameters": {
                            "languages": ["vi"]
                        }
                    },
                    expand=["markdown_full", "text_full"],
                )
                
                md_content = result.markdown_full or ""
                if md_content:
                    all_documents.append(md_content)
                    print(f"  -> ✅ HOÀN HẢO! Trích xuất thành công ({len(md_content)} ký tự).")
                    
                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write(md_content)
                    print(f"  -> 💾 Đã lưu file Markdown tại: {out_path}")
                    
                    success = True
                    break
                else:
                    print("  -> ❌ API trả về rỗng.")
                    break
                    
            except Exception as e:
                print(f"  -> Lỗi kết nối hoặc xử lý: {e}")
                if attempt < max_retries:
                    print("  -> Đang đợi 3 giây để thử lại...")
                    time.sleep(3)
                else:
                    print("  -> 3 lần thử thất bại.")
                    
        if not success:
            print(f"Vui lòng kiểm tra lại mạng hoặc dung lượng file {clean_path}.")

    return all_documents

if __name__ == "__main__":
    docs = parse_documents()
    
    if docs:
        print("\n" + "="*50)
        print(" BẢN XEM TRƯỚC NỘI DUNG (1000 ký tự đầu của file cuối cùng) ")
        print("="*50)
        print(docs[-1][:1000])