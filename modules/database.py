import sqlite3
from pathlib import Path

DB_PATH = Path("../data/bot.db")


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

def create_table():
    conn = connect_db()
    c = conn.cursor()

    c.executescript('''
    CREATE TABLE IF NOT EXISTS Channels (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS Settings (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    value TEXT
    );
    INSERT OR IGNORE INTO Settings (id, name, value) VALUES
        (0, 'SOURCE_CHANNEL', '@my_brak'),
        (1, 'SIGNATURE', '@pnewsgg'),
        (2, 'MODE', 'REVIEW'),
        (3, 'OPENROUTER_API_KEY', 'YOUR_API_KEY'),
        (4, 'OPENROUTER_MODEL_NAME', 'openai/gpt-4o-mini');
    ''')
    conn.commit()
    conn.close()

create_table()
# db = connect_db()
# cursor = db.cursor()
# cursor.execute("SELECT 1")
# print("🟢 Проверка запроса: OK")