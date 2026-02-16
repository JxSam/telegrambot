import sqlite3
from pathlib import Path
from contextlib import contextmanager

@contextmanager
def get_db():
    conn = connect_db()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

DB_PATH = Path("../data/bot.db")

request_base_table = '''
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
    '''

request_post_table = '''
    CREATE TABLE IF NOT EXISTS posts (
    post_id INTEGER GENERATED ALWAYS PRIMARY KEY,
    text TEXT,
    old_text TEXT
);
CREATE TABLE IF NOT EXISTS post_media (
    id INTEGER GENERATED ALWAYS PRIMARY KEY,
    post_id INTEGER NOT NULL,
    file_id TEXT NOT NULL,
    CONSTRAINT fk_post
        FOREIGN KEY (post_id)
        REFERENCES posts(post_id)
        ON DELETE CASCADE
);
    '''

def connect_db():
    try:
        conn = sqlite3.connect(DB_PATH)

        return conn

    except Exception as e:
        print("❌ Ошибка подключения к SQLite:", e)
        return None

def create_table(execute):
    conn = connect_db()
    c = conn.cursor()

    c.executescript(execute)
    conn.commit()
    conn.close()

create_table(request_post_table)

# db = connect_db()
# cursor = db.cursor()
# cursor.execute("SELECT 1")
# print("🟢 Проверка запроса: OK")