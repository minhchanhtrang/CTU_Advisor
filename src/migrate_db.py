"""
migrate_db.py - Drop schema cu, tao lai schema moi cho CTU Advisor.
Chay 1 lan duy nhat: python src/migrate_db.py
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv(r'd:\NienLuan\chatbotCTU\.env')

conn = psycopg2.connect(
    host=os.getenv('POSTGRES_HOST', 'localhost'),
    port=int(os.getenv('POSTGRES_PORT', 5432)),
    dbname=os.getenv('POSTGRES_DB', 'ctu_chatbot'),
    user=os.getenv('POSTGRES_USER', 'postgres'),
    password=os.getenv('POSTGRES_PASSWORD', '')
)

try:
    with conn.cursor() as cur:
        print("[*] Xoa bang cu (sessions, messages)...")
        cur.execute("DROP TABLE IF EXISTS messages CASCADE;")
        cur.execute("DROP TABLE IF EXISTS sessions CASCADE;")

        print("[*] Tao bang users...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(80) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name VARCHAR(150),
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        print("[*] Tao bang conversations...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title VARCHAR(255) NOT NULL DEFAULT 'Cuoc hoi thoai moi',
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
        """)

        print("[*] Tao bang messages...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        print("[*] Tao indexes...")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_conv_user_id ON conversations(user_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_msg_conv_id ON messages(conversation_id);")

    conn.commit()
    print("[OK] Migration hoan tat!")

except Exception as e:
    conn.rollback()
    print(f"[LOI] {e}")
    raise
finally:
    conn.close()
