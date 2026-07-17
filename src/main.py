import os
import sys

# Fix encoding cho Windows console
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Đảm bảo có thể import từ thư mục src
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ["HF_HOME"] = r"D:\AI_Models_Cache"
os.environ["LLAMA_INDEX_CACHE_DIR"] = r"D:\AI_Models_Cache"

# pyrefly: ignore [missing-import]
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from generator import setup_chatbot, ask

# ==========================================
# CẤU HÌNH FLASK APP
# ==========================================
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
CORS(app)

# ==========================================
# KHỞI TẠO CHATBOT MỘT LẦN DUY NHẤT
# ==========================================
print("=" * 60)
print("[*] Dang khoi dong CTU Chatbot Server...")
print("=" * 60)
chatbot_state = setup_chatbot(persist_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "vector_db"))

if chatbot_state is None:
    print("[LỖI] NGHIÊM TRỌNG: Không thể khởi tạo chatbot! Kiểm tra vector DB.")
else:
    print("\n[OK] Server đã sẵn sàng!")
    print("[WEB] Truy cập: http://localhost:5000")
    print("=" * 60)


# ==========================================
# ROUTES
# ==========================================
@app.route("/")
def index():
    """Trang chủ - trả về giao diện chat."""
    return render_template("index.html")


@app.route("/api/status", methods=["GET"])
def status():
    """Kiểm tra trạng thái hệ thống."""
    if chatbot_state is None:
        return jsonify({"status": "error", "message": "Chatbot chưa được khởi tạo."}), 503
    return jsonify({
        "status": "ok",
        "message": "Hệ thống đang hoạt động bình thường.",
        "nganh_count": len(chatbot_state.get("nganh_values", [])),
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Endpoint xử lý câu hỏi của người dùng.
    Request body (JSON):
        {
            "message": "Câu hỏi của người dùng",
            "history": [
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."},
                ...
            ]
        }
    Response:
        {"answer": "Câu trả lời của chatbot"}
    """
    if chatbot_state is None:
        return jsonify({"error": "Hệ thống chatbot chưa sẵn sàng. Vui lòng thử lại sau."}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "Yêu cầu không hợp lệ."}), 400

    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "Tin nhắn không được để trống."}), 400

    # Lấy lịch sử hội thoại từ client (tối đa 10 messages = 5 lượt)
    history = data.get("history", [])
    if not isinstance(history, list):
        history = []

    try:
        answer = ask(chatbot_state, user_message, chat_history=history)
        return jsonify({"answer": answer})
    except Exception as e:
        print(f"❌ Lỗi khi xử lý câu hỏi: {e}")
        return jsonify({"error": f"Đã xảy ra lỗi khi xử lý: {str(e)}"}), 500


# ==========================================
# KHỞI CHẠY SERVER
# ==========================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
