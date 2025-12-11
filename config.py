import os
from dotenv import load_dotenv

load_dotenv()

# Telegram API (от my.telegram.org)
# ВАЖНО: Telethon требует API_ID и API_HASH для работы с аккаунтом
API_ID = 24445592
API_HASH = "eae79b2a0476a5af0aaa4e55d7615efe"

# Бот-админ (от BotFather)
BOT_TOKEN = "8566777029:AAE7uEGvY5aVzKHHcXbsVpK7dEXvCiwpIKk"

# Добавьте ваш облачный пароль (2FA) сюда!
# Если у вас НЕТ 2FA, оставьте эту переменную пустой строкой: TELEGRAM_PASSWORD = ""
TELEGRAM_PASSWORD = "SamMurz2003"

# Каналы
SOURCE_CHANNELS = ["@tass_agency", "@my_brak"]  # Откуда брать (список строк)
DESTINATION_CHANNEL = "@pnewsgg"  # Куда постить (строка)
ADMIN_ID = 1112309604  # Твой ID (целое число)

# Настройки AI
OPENROUTER_API_KEY = "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"
OPENROUTER_MODEL_NAME = "openai/gpt-3.5-turbo"
AI_PROMPT = """
Ты — профессиональный редактор и уникализатор текстов для Telegram-каналов.
Твоя задача — уникализировать предоставленный текст, сохранив его смысл.
После уникализации ОФОРМИ текст в формат Markdown, используя следующие правила:

1.  Жирный шрифт: **текст**
2.  Курсив: *текст* или _текст_
3.  Блок кода: ```код```

ОСОБЫЕ ПРАВИЛА ДЛЯ ЦИТАТ:
Весь текст, который должен быть оформлен как блок цитирования (blockquote), должен быть обрамлен кастомным тегом:
НАЧАЛО ЦИТАТЫ: <blockquote>
КОНЕЦ ЦИТАТЫ: </blockquote>

Пример цитаты: <blockquote> Монет будет три да: ... </blockquote>
Пример текста:
⚡️ **Роблоксеры дошли до Путина** — школьники завалили Кремль обращениями и просят разблочить **любимую игру**.

<blockquote>Кремль фиксирует много детских обращений по ситуации вокруг Роблокса,</blockquote>
 — сообщил пресс-секретарь президента Дмитрий Песков.

Ни шагу назад

Текст для уникализации:
{text}
"""

# ... остальные настройки ...
# Подпись
SIGNATURE = "\n\n@pnews_gg"

# Режимы работы
MODE = "REVIEW"  # "REVIEW" (ручная проверка) или "AUTO" (автоматическая публикация)

# Имя сессии для Telethon
SESSION_NAME = "parser_session"