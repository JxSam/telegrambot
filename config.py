import os
from dotenv import load_dotenv

load_dotenv()

################################################
# Папка для временных файлов с парсинга постов #
################################################
DOWNLOAD_DIR = 'downloads'

# Telegram API (от my.telegram.org)
API_ID =
API_HASH = ""

# Бот-админ (от BotFather)
BOT_TOKEN = ""

# Добавьте ваш облачный пароль (2FA) сюда!
TELEGRAM_PASSWORD = ""

# Каналы
ADMIN_ID =   # Твой ID

# Режимы работы
MODE = "REVIEW"  # "REVIEW" (ручная проверка) или "AUTO" (автоматическая публикация)

# Имя сессии для Telethon
SESSION_NAME = "parser_session"
