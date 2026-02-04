import sqlite3
from pathlib import Path

DB_PATH = Path("data/bot.db")


def connect_db():
    try:
        DB_PATH.parent.mkdir(exist_ok=True)

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # удобно потом

        print("✅ SQLite подключена:", DB_PATH.resolve())
        return conn

    except Exception as e:
        print("❌ Ошибка подключения к SQLite:", e)
        return None

db = connect_db()
cursor = db.cursor()
cursor.execute("SELECT 1")
print("🟢 Проверка запроса: OK")