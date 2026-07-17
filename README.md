# 🎓 Chatbot Tư vấn Học vụ Đại học Cần Thơ

> **Xây dựng Hệ thống Chatbot Tư vấn Học vụ Đại học Cần Thơ Sử dụng Retrieval-Augmented Generation và Hybrid Search**

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-lightgrey)](https://flask.palletsprojects.com)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_DB-orange)](https://www.trychroma.com)
[![Gemini](https://img.shields.io/badge/Google-Gemini_Flash-green)](https://ai.google.dev)

---

## 📖 Giới thiệu

Hệ thống chatbot AI giúp sinh viên **Đại học Cần Thơ** tra cứu thông tin về:
- 📚 Chương trình đào tạo các ngành học
- 📋 Quy chế học vụ, điều kiện tốt nghiệp
- 🎯 Số tín chỉ, thời gian đào tạo, mã ngành

### Công nghệ cốt lõi
| Thành phần | Công nghệ |
|---|---|
| **LLM** | Google Gemini (gemini-flash-lite) |
| **Embedding** | HuggingFace `Alibaba-NLP/gte-multilingual-base` |
| **Vector DB** | ChromaDB |
| **RAG** | Hybrid Search (Vector + BM25 + RRF Fusion) |
| **Web Server** | Flask |
| **Frontend** | HTML + CSS + JavaScript (Vanilla) |

---

## 🗂️ Cấu trúc dự án

```
chatbotCTU/
├── src/
│   ├── main.py              # Flask server - Entry point
│   ├── generator.py         # AI logic: RAG, match ngành, tạo câu trả lời
│   ├── retriever.py         # Xây dựng vector database từ file .md
│   ├── data_ingestion.py    # Parse PDF → Markdown bằng LlamaParse
│   ├── templates/
│   │   └── index.html       # Giao diện web
│   └── static/
│       ├── style.css        # Giao diện responsive, dark/light mode
│       └── script.js        # Frontend logic, LocalStorage history
├── data/
│   └── processed/           # File Markdown đã xử lý (cần chuẩn bị sẵn)
├── requirements.txt
├── .env.example             # Mẫu file .env (không chứa key thật)
└── architecture_diagram.drawio  # Sơ đồ kiến trúc hệ thống
```

---

## ⚙️ Cài đặt và Chạy

### 1. Clone repository
```bash
git clone https://github.com/<your-username>/chatbotCTU.git
cd chatbotCTU
```

### 2. Tạo môi trường ảo và cài thư viện
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Cài đặt PyTorch (GPU - CUDA 12.1)
```bash
# Nếu có GPU NVIDIA
pip install torch --index-url https://download.pytorch.org/whl/cu121

# Nếu chỉ dùng CPU
pip install torch
```

### 4. Cấu hình API Keys
Tạo file `.env` từ mẫu:
```bash
copy .env.example .env
```
Điền vào `.env`:
```env
LLAMA_CLOUD_API_KEY=your_llama_cloud_key_here
GOOGLE_API_KEY=your_google_api_key_here
```

### 5. Chuẩn bị dữ liệu

**Bước 5a — Parse PDF thành Markdown** (nếu có file PDF mới):
```bash
python src/data_ingestion.py
```
> Đặt file PDF vào `data/raw/` trước khi chạy

**Bước 5b — Xây dựng Vector Database:**
```bash
python src/retriever.py
```
> Chạy lần đầu sẽ mất vài phút để embedding toàn bộ dữ liệu

### 6. Chạy server
```bash
python src/main.py
```
Mở trình duyệt: **http://localhost:5000**

---

## 🔑 Lấy API Keys

| Key | Hướng dẫn |
|---|---|
| `GOOGLE_API_KEY` | [Google AI Studio](https://aistudio.google.com/app/apikey) → Create API Key |
| `LLAMA_CLOUD_API_KEY` | [LlamaCloud](https://cloud.llamaindex.ai) → API Keys (dùng để parse PDF) |

---

## 📐 Kiến trúc hệ thống

Xem file `architecture_diagram.drawio` bằng [draw.io](https://draw.io).

**Pipeline 1 — Xây dựng dữ liệu (offline):**
```
PDF → LlamaParse → Markdown → HuggingFace Embedding → ChromaDB
```

**Pipeline 2 — Phục vụ người dùng (online):**
```
Browser → Flask → match_nganh() → fetch context → Gemini LLM → Trả lời
                               ↘ Hybrid RAG (BM25 + Vector + RRF) ↗
```

---

## 🚀 Tính năng nổi bật

- ✅ **Hybrid Search**: Kết hợp Vector Search (ngữ nghĩa) + BM25 (từ khóa) + RRF Fusion
- ✅ **Nhận diện ngành thông minh**: Hiểu viết tắt (`ktpm`, `cntt clc`, `httt`...)
- ✅ **Nhớ lịch sử hội thoại**: LocalStorage — không mất khi tải lại trang
- ✅ **Incremental DB build**: Chỉ xử lý file mới, bỏ qua file không đổi
- ✅ **Dark/Light mode**: Responsive trên mọi thiết bị

---

"© 2026 Trang Minh Chánh. Đồ án Niên luận Đại học Cần Thơ."