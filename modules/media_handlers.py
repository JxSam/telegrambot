import os
from config import DOWNLOAD_DIR

def ensure_download_dir():
    """Создает папку downloads, если она не существует."""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

async def delete_temp_media(file_path: str):
    """Безопасно удаляет временный медиафайл."""
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f"🗑️ Временный медиафайл удален: {file_path}")
        except Exception as e:
            print(f"❌ Ошибка при удалении файла {file_path}: {e}")