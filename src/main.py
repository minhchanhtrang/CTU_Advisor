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
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, send_from_directory
from flask_cors import CORS
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from dotenv import load_dotenv
from generator import setup_chatbot, ask
import database as db

load_dotenv()

# ==========================================
# CẤU HÌNH FLASK APP
# ==========================================
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.secret_key = os.getenv("SECRET_KEY", "ctu-advisor-secret-2024-change-me")
CORS(app)

# ==========================================
# FLASK-LOGIN SETUP
# ==========================================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth_login"
login_manager.login_message = "Vui lòng đăng nhập để tiếp tục."
login_manager.login_message_category = "info"


class User(UserMixin):
    """User model tương thích với Flask-Login."""
    def __init__(self, user_dict: dict):
        self.id = user_dict["id"]
        self.username = user_dict["username"]
        self.full_name = user_dict.get("full_name", "")

    def get_id(self):
        return str(self.id)


@login_manager.user_loader
def load_user(user_id):
    user_dict = db.get_user_by_id(int(user_id))
    if user_dict:
        return User(user_dict)
    return None


# ==========================================
# KHỞI TẠO DATABASE & CHATBOT
# ==========================================
print("=" * 60)
print("[*] Dang khoi dong CTU Chatbot Server...")
print("=" * 60)

# Khởi tạo database (tạo bảng nếu chưa có)
try:
    db.init_db()
except Exception as e:
    print(f"[LỖI] Không thể kết nối PostgreSQL: {e}")
    print("[!] Server vẫn khởi động, nhưng tính năng auth/lịch sử sẽ không hoạt động.")

# Khởi tạo chatbot
chatbot_state = setup_chatbot(
    persist_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "vector_db")
)

if chatbot_state is None:
    print("[LỖI] NGHIÊM TRỌNG: Không thể khởi tạo chatbot! Kiểm tra vector DB.")
else:
    print("\n[OK] Server đã sẵn sàng!")
    print("[WEB] Truy cập: http://localhost:5000")
    print("=" * 60)


# ==========================================
# AUTH ROUTES
# ==========================================

@app.route("/auth/login", methods=["GET", "POST"])
def auth_login():
    """Trang đăng nhập."""
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            error = "Vui lòng điền đầy đủ thông tin."
        else:
            user_dict = db.get_user_by_username(username)
            if user_dict and db.verify_password(user_dict, password):
                user_obj = User(user_dict)
                login_user(user_obj, remember=True)
                next_page = request.args.get("next")
                return redirect(next_page or url_for("index"))
            else:
                error = "Tên đăng nhập hoặc mật khẩu không đúng."

    return render_template("login.html", error=error)


@app.route("/auth/register", methods=["GET", "POST"])
def auth_register():
    """Trang đăng ký tài khoản mới."""
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")
        full_name = request.form.get("full_name", "").strip()

        if not username or not password:
            error = "Vui lòng điền đầy đủ tên đăng nhập và mật khẩu."
        elif len(username) < 3:
            error = "Tên đăng nhập phải có ít nhất 3 ký tự."
        elif len(password) < 6:
            error = "Mật khẩu phải có ít nhất 6 ký tự."
        elif password != confirm:
            error = "Mật khẩu xác nhận không khớp."
        else:
            user_dict = db.create_user(username, password, full_name)
            if user_dict is None:
                error = "Tên đăng nhập đã tồn tại. Vui lòng chọn tên khác."
            else:
                # Tự động đăng nhập sau khi đăng ký
                user_obj = User(user_dict)
                login_user(user_obj, remember=True)
                return redirect(url_for("index"))

    return render_template("register.html", error=error)


@app.route("/auth/logout")
@login_required
def auth_logout():
    """Đăng xuất."""
    logout_user()
    return redirect(url_for("auth_login"))


# ==========================================
# MAIN ROUTES
# ==========================================

@app.route("/")
@login_required
def index():
    """Trang chủ - trả về giao diện chat."""
    return render_template("index.html", user=current_user)


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


# ==========================================
# CONVERSATION API
# ==========================================

@app.route("/api/conversations", methods=["GET"])
@login_required
def get_conversations():
    """Lấy danh sách tất cả cuộc hội thoại của user hiện tại."""
    convs = db.get_conversations(current_user.id)
    # Serialize datetime thành chuỗi ISO
    result = []
    for c in convs:
        result.append({
            "id": c["id"],
            "title": c["title"],
            "created_at": c["created_at"].isoformat() if c["created_at"] else None,
            "updated_at": c["updated_at"].isoformat() if c["updated_at"] else None,
        })
    return jsonify(result)


@app.route("/api/conversations", methods=["POST"])
@login_required
def create_conversation():
    """Tạo cuộc hội thoại mới."""
    data = request.get_json() or {}
    title = data.get("title", "Cuộc hội thoại mới")
    conv = db.create_conversation(current_user.id, title)
    return jsonify({
        "id": conv["id"],
        "title": conv["title"],
        "created_at": conv["created_at"].isoformat(),
        "updated_at": conv["updated_at"].isoformat(),
    }), 201


@app.route("/api/conversations/<int:conv_id>", methods=["DELETE"])
@login_required
def delete_conversation(conv_id):
    """Xóa một cuộc hội thoại."""
    success = db.delete_conversation(conv_id, current_user.id)
    if success:
        return jsonify({"message": "Đã xóa thành công."}), 200
    return jsonify({"error": "Không tìm thấy hội thoại."}), 404


@app.route("/api/conversations/all", methods=["DELETE"])
@login_required
def delete_all_conversations():
    """Xóa toàn bộ cuộc hội thoại của user."""
    count = db.delete_all_conversations(current_user.id)
    return jsonify({"message": f"Đã xóa {count} hội thoại."}), 200


@app.route("/api/conversations/<int:conv_id>/messages", methods=["GET"])
@login_required
def get_messages(conv_id):
    """Lấy tất cả messages của một cuộc hội thoại."""
    msgs = db.get_messages(conv_id, current_user.id)
    result = []
    for m in msgs:
        result.append({
            "id": m["id"],
            "role": m["role"],
            "content": m["content"],
            "created_at": m["created_at"].isoformat() if m["created_at"] else None,
        })
    return jsonify(result)


@app.route("/api/conversations/<int:conv_id>/title", methods=["PATCH"])
@login_required
def update_title(conv_id):
    """Cập nhật tiêu đề cuộc hội thoại."""
    data = request.get_json() or {}
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "Tiêu đề không được để trống."}), 400
    success = db.update_conversation_title(conv_id, current_user.id, title)
    if success:
        return jsonify({"message": "Đã cập nhật tiêu đề."}), 200
    return jsonify({"error": "Không tìm thấy hội thoại."}), 404


# ==========================================
# CHAT API
# ==========================================

@app.route("/api/chat", methods=["POST"])
@login_required
def chat():
    """
    Endpoint xử lý câu hỏi của người dùng.
    Request body (JSON):
        {
            "message": "Câu hỏi của người dùng",
            "conversation_id": 123,   // optional
            "history": [...]          // optional fallback nếu không có conv_id
        }
    Response:
        {"answer": "...", "conversation_id": 123}
    """
    if chatbot_state is None:
        return jsonify({"error": "Hệ thống chatbot chưa sẵn sàng. Vui lòng thử lại sau."}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "Yêu cầu không hợp lệ."}), 400

    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "Tin nhắn không được để trống."}), 400

    conv_id = data.get("conversation_id")

    # Nếu không có conversation_id → tạo mới
    if not conv_id:
        # Tự động tạo conversation, title sẽ cập nhật sau
        short_title = user_message[:60] + ("…" if len(user_message) > 60 else "")
        conv = db.create_conversation(current_user.id, short_title)
        conv_id = conv["id"]
        is_new_conv = True
    else:
        is_new_conv = False

    # Lấy lịch sử từ DB để làm context cho AI
    msgs_from_db = db.get_messages(conv_id, current_user.id)
    history_for_ai = [{"role": m["role"], "content": m["content"]} for m in msgs_from_db]

    # Lưu message của user vào DB
    db.add_message(conv_id, "user", user_message)

    # Cập nhật title nếu đây là tin nhắn đầu tiên trong conv cũ
    if not is_new_conv and len(msgs_from_db) == 0:
        short_title = user_message[:60] + ("…" if len(user_message) > 60 else "")
        db.update_conversation_title(conv_id, current_user.id, short_title)

    try:
        answer = ask(chatbot_state, user_message, chat_history=history_for_ai)
        # Lưu câu trả lời của AI vào DB
        db.add_message(conv_id, "assistant", answer)
        return jsonify({"answer": answer, "conversation_id": conv_id})
    except Exception as e:
        print(f"❌ Lỗi khi xử lý câu hỏi: {e}")
        return jsonify({"error": f"Đã xảy ra lỗi khi xử lý: {str(e)}"}), 500


# ==========================================
# USER INFO API
# ==========================================

@app.route("/api/me", methods=["GET"])
@login_required
def me():
    """Trả về thông tin user hiện tại."""
    return jsonify({
        "id": current_user.id,
        "username": current_user.username,
        "full_name": current_user.full_name,
    })


@app.route("/api/me/update", methods=["POST"])
@login_required
def update_me():
    """Cập nhật thông tin user hiện tại."""
    data = request.get_json() or {}
    full_name = data.get("full_name", current_user.full_name)
    password = data.get("password")

    success = db.update_user_info(current_user.id, full_name, password)
    if success:
        current_user.full_name = full_name
        return jsonify({"message": "Cập nhật thành công.", "full_name": full_name}), 200
    return jsonify({"error": "Không thể cập nhật thông tin."}), 500


# ==========================================
# FILE SERVING API
# ==========================================

@app.route("/api/pdfs/<path:filename>", methods=["GET"])
@login_required
def serve_pdf(filename):
    """Serve PDF files from data/raw/DaiHoc for references."""
    pdf_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "raw", "DaiHoc")
    return send_from_directory(pdf_dir, filename)


# ==========================================
# KHỞI CHẠY SERVER
# ==========================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
