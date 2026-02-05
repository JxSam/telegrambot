import sqlite3
from pathlib import Path

DB_PATH = Path("../data/bot.db")


def connect_db():
    try:
        conn = sqlite3.connect(DB_PATH)

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
        (0, 'SIGNATURE', '@pnewsgg'),
        (1, 'MODE', 'REVIEW'),
        (2, 'OPENROUTER_API_KEY', 'YOUR_API_KEY'),
        (3, 'OPENROUTER_MODEL_NAME', 'openai/gpt-4o-mini'),
        (4, 'DESTINATION_CHANNEL', '@pnewsgg');
    INSERT OR IGNORE INTO Channels (id, name) VALUES
        (0, '@my_brak'),
        (1, '@whackdoor');
    ''')
    conn.commit()
    conn.close()


# db = connect_db()
# cursor = db.cursor()
# cursor.execute("SELECT 1")
# print("🟢 Проверка запроса: OK")