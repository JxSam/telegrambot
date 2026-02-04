import os
from dotenv import load_dotenv

load_dotenv()

################################################
# Папка для временных файлов с парсинга постов #
################################################
DOWNLOAD_DIR = 'downloads'

# Telegram API (от my.telegram.org)
API_ID = 24445592
API_HASH = "eae79b2a0476a5af0aaa4e55d7615efe"

# Бот-админ (от BotFather)
BOT_TOKEN = "8566777029:AAE7uEGvY5aVzKHHcXbsVpK7dEXvCiwpIKk"

# Добавьте ваш облачный пароль (2FA) сюда!
# Если у вас НЕТ 2FA, оставьте эту переменную пустой строкой: TELEGRAM_PASSWORD = ""
TELEGRAM_PASSWORD = "JohnyX2003"

# Каналы
SOURCE_CHANNELS = ["@my_brak"]
DESTINATION_CHANNEL = "@pnewsgg"  # Куда постить
ADMIN_ID = 1112309604  # Твой ID

# Подпись
SIGNATURE = "\n\n@pnewsgg"

# Режимы работы
MODE = "REVIEW"  # "REVIEW" (ручная проверка) или "AUTO" (автоматическая публикация)

# Имя сессии для Telethon
SESSION_NAME = "parser_session"