import os, re
from html import escape

def escape_html_entities(text: str) -> str:
    """Экранирует специальные символы HTML: &, <, >."""
    return escape(text)

def ensure_download_dir(dir):
    """Создает папку downloads, если она не существует."""
    os.makedirs(dir, exist_ok=True)

def delete_temp_media(file_path: str):
    """Безопасно удаляет временный медиафайл."""
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f"🗑️ Временный медиафайл удален: {file_path}")
        except Exception as e:
            print(f"❌ Ошибка при удалении файла {file_path}: {e}")

def word_replace(words, text):
    word_list = [re.escape(word) for (word,) in words]

    pattern = r'(' + '|'.join(word_list) + r')'

    text = re.sub(pattern, '', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text