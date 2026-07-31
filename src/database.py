"""
database.py – Kết nối PostgreSQL và các hàm CRUD
cho hệ thống auth và lịch sử hội thoại CTU Advisor.
"""

import os
import psycopg2
import psycopg2.extras
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()


# ==========================================
# KẾT NỐI DATABASE
# ==========================================

def get_connection():
    """Tạo và trả về kết nối PostgreSQL mới."""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        dbname=os.getenv("POSTGRES_DB", "ctu_chatbot"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
    )


# ==========================================
# KHỞI TẠO BẢNG
# ==========================================

def init_db():
    """Tạo các bảng cần thiết nếu chưa tồn tại."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(80) UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name VARCHAR(150),
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    title VARCHAR(255) NOT NULL DEFAULT 'Cuộc hội thoại mới',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            # Index để tăng tốc truy vấn
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_conv_user_id
                ON conversations(user_id);
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_msg_conv_id
                ON messages(conversation_id);
            """)
        conn.commit()
        print("[DB] Tables initialized successfully.")
    except Exception as e:
        conn.rollback()
        print(f"[DB] Init error: {e}")
        raise
    finally:
        conn.close()


# ==========================================
# USER CRUD
# ==========================================

def create_user(username: str, password: str, full_name: str = "") -> dict | None:
    """
    Tạo user mới. Trả về dict user hoặc None nếu username đã tồn tại.
    """
    password_hash = generate_password_hash(password)
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO users (username, password_hash, full_name)
                VALUES (%s, %s, %s)
                RETURNING id, username, full_name, created_at
                """,
                (username.strip(), password_hash, full_name.strip()),
            )
            user = dict(cur.fetchone())
        conn.commit()
        return user
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return None
    except Exception as e:
        conn.rollback()
        print(f"[DB] create_user error: {e}")
        raise
    finally:
        conn.close()


def get_user_by_username(username: str) -> dict | None:
    """Lấy thông tin user theo username (bao gồm password_hash)."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, username, password_hash, full_name, created_at FROM users WHERE username = %s",
                (username.strip(),),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> dict | None:
    """Lấy thông tin user theo ID."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, username, full_name, created_at FROM users WHERE id = %s",
                (user_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def verify_password(user: dict, password: str) -> bool:
    """Kiểm tra mật khẩu với hash đã lưu."""
    return check_password_hash(user["password_hash"], password)


def update_user_info(user_id: int, full_name: str, password: str = None) -> bool:
    """Cập nhật thông tin user. Nếu có password mới thì hash và cập nhật."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if password:
                password_hash = generate_password_hash(password)
                cur.execute(
                    """
                    UPDATE users
                    SET full_name = %s, password_hash = %s
                    WHERE id = %s
                    """,
                    (full_name.strip(), password_hash, user_id),
                )
            else:
                cur.execute(
                    """
                    UPDATE users
                    SET full_name = %s
                    WHERE id = %s
                    """,
                    (full_name.strip(), user_id),
                )
            updated = cur.rowcount > 0
        conn.commit()
        return updated
    except Exception as e:
        conn.rollback()
        print(f"[DB] update_user_info error: {e}")
        return False
    finally:
        conn.close()


# ==========================================
# CONVERSATION CRUD
# ==========================================

def create_conversation(user_id: int, title: str = "Cuộc hội thoại mới") -> dict:
    """Tạo cuộc hội thoại mới cho user, trả về dict conversation."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO conversations (user_id, title)
                VALUES (%s, %s)
                RETURNING id, user_id, title, created_at, updated_at
                """,
                (user_id, title),
            )
            conv = dict(cur.fetchone())
        conn.commit()
        return conv
    except Exception as e:
        conn.rollback()
        print(f"[DB] create_conversation error: {e}")
        raise
    finally:
        conn.close()


def get_conversations(user_id: int) -> list[dict]:
    """
    Lấy danh sách tất cả cuộc hội thoại của user,
    sắp xếp mới nhất lên đầu.
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM conversations
                WHERE user_id = %s
                ORDER BY updated_at DESC
                """,
                (user_id,),
            )
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def update_conversation_title(conv_id: int, user_id: int, title: str) -> bool:
    """Cập nhật tiêu đề conversation. Trả về True nếu thành công."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE conversations
                SET title = %s, updated_at = NOW()
                WHERE id = %s AND user_id = %s
                """,
                (title, conv_id, user_id),
            )
            updated = cur.rowcount > 0
        conn.commit()
        return updated
    except Exception as e:
        conn.rollback()
        print(f"[DB] update_title error: {e}")
        return False
    finally:
        conn.close()


def delete_conversation(conv_id: int, user_id: int) -> bool:
    """Xóa conversation (và toàn bộ messages liên quan qua CASCADE)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM conversations WHERE id = %s AND user_id = %s",
                (conv_id, user_id),
            )
            deleted = cur.rowcount > 0
        conn.commit()
        return deleted
    except Exception as e:
        conn.rollback()
        print(f"[DB] delete_conversation error: {e}")
        return False
    finally:
        conn.close()


def delete_all_conversations(user_id: int) -> int:
    """Xóa toàn bộ conversation của user. Trả về số dòng đã xóa."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM conversations WHERE user_id = %s",
                (user_id,),
            )
            count = cur.rowcount
        conn.commit()
        return count
    except Exception as e:
        conn.rollback()
        print(f"[DB] delete_all_conversations error: {e}")
        return 0
    finally:
        conn.close()


# ==========================================
# MESSAGE CRUD
# ==========================================

def add_message(conv_id: int, role: str, content: str) -> dict:
    """
    Thêm một tin nhắn vào conversation.
    Đồng thời cập nhật updated_at của conversation.
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO messages (conversation_id, role, content)
                VALUES (%s, %s, %s)
                RETURNING id, conversation_id, role, content, created_at
                """,
                (conv_id, role, content),
            )
            msg = dict(cur.fetchone())
            # Cập nhật updated_at của conversation
            cur.execute(
                "UPDATE conversations SET updated_at = NOW() WHERE id = %s",
                (conv_id,),
            )
        conn.commit()
        return msg
    except Exception as e:
        conn.rollback()
        print(f"[DB] add_message error: {e}")
        raise
    finally:
        conn.close()


def get_messages(conv_id: int, user_id: int) -> list[dict]:
    """
    Lấy tất cả messages của một conversation.
    Kiểm tra quyền sở hữu qua user_id.
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Kiểm tra conv thuộc về user
            cur.execute(
                "SELECT id FROM conversations WHERE id = %s AND user_id = %s",
                (conv_id, user_id),
            )
            if not cur.fetchone():
                return []
            cur.execute(
                """
                SELECT id, role, content, created_at
                FROM messages
                WHERE conversation_id = %s
                ORDER BY created_at ASC
                """,
                (conv_id,),
            )
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
