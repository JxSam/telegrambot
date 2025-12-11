import asyncio
import re
from telethon import TelegramClient, events
from telethon.tl.types import MessageEntityBold, MessageEntityItalic, MessageEntityTextUrl, MessageEntityCode, \
    MessageEntityPre, MessageEntityStrike, MessageEntityUnderline, MessageEntitySpoiler, MessageEntityUrl, \
    MessageEntityCustomEmoji, MessageEntityMentionName, MessageEntityBlockquote
from html import escape
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import ParseMode

import httpx  # Для запросов к OpenRouter
import config  # В config.py должен быть определен TELEGRAM_PASSWORD

# --- Инициализация клиентов ---
# Telethon Client (для парсинга аккаунтом)
parser_client = TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH)

# Aiogram Bot (для администрирования)
default_properties = DefaultBotProperties(parse_mode=ParseMode.HTML)
bot = Bot(token=config.BOT_TOKEN, default=default_properties)
dp = Dispatcher()
# Инициализация хранилищ для состояний
dp['review_posts'] = {}
dp['waiting_for_edit'] = {}


# --- Вспомогательные функции (Минимальное экранирование) ---

def escape_html_entities(text: str) -> str:
    """Экранирует специальные символы HTML: &, <, >."""
    return escape(text)


def get_markdown_text(message) -> str:
    """
    Получает сырой текст сообщения, минимально экранируя HTML-конфликтующие символы
    для безопасной передачи через Aiogram. Сохраняет Markdown символы (**, >, ```).
    """
    text = message.text
    if not text:
        return ""

    # Получаем сырой текст сообщения
    raw_content = message.text

    # Экранируем, чтобы избежать ошибок парсинга HTML в Aiogram
    final_text = escape_html_entities(raw_content)

    return final_text


def convert_markdown_to_html(markdown_text: str) -> str:
    """
    Конвертирует наиболее распространенные MarkdownV2 символы в HTML.
    ИИ должен возвращать цитаты уже в тегах <blockquote>.
    """
    html_text = markdown_text

    # 1. Markdown в HTML
    # Жирный шрифт: **текст**
    html_text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', html_text)

    # Курсив: _текст_ или *текст*
    html_text = re.sub(r'_(.+?)_', r'<i>\1</i>', html_text)
    html_text = re.sub(r'\*(.+?)_*', r'<i>\1</i>', html_text)

    # Зачеркнутый: ~текст~
    html_text = re.sub(r'~(.+?)~', r'<s>\1</s>', html_text)

    # Инлайн-код: `код`
    html_text = re.sub(r'`(.+?)`', r'<code>\1</code>', html_text)

    # Блочный код: ```код```
    # re.DOTALL нужен, чтобы захватывать переносы строк внутри блочного кода.
    html_text = re.sub(r'```(?:\w+)?\n?(.+?)```', r'<pre>\1</pre>', html_text, flags=re.DOTALL)

    # 2. Очистка от одиночных/разорванных символов Markdown (безопасно после конвертации)
    html_text = html_text.replace('*', '').replace('_', '').replace('~', '').replace('`', '')

    return html_text

async def ai_unique_text(text: str) -> str:
    """Отправляет текст в OpenRouter API для уникализации, а затем преобразует Markdown в HTML."""

    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = config.AI_PROMPT.format(text=text)

    data = {
        "model": config.OPENROUTER_MODEL_NAME,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "text"}
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()

            ai_markdown_text = result['choices'][0]['message']['content'].strip()

            # 🌟 ГЛАВНОЕ ИЗМЕНЕНИЕ: Конвертируем Markdown в HTML
            final_html_text = convert_markdown_to_html(ai_markdown_text)

            return final_html_text

        except Exception as e:
            print(f"❌ Ошибка при запросе к AI: {e}")
            error_message = f"❌ Ошибка уникализации. {escape_html_entities(str(e))}"
            # Вставляем оригинальный текст, чтобы не потерять его
            return f"<b>{error_message}</b>\n\nОригинал:\n{text}"

# --- Обработчик парсинга (Telethon) ---

@parser_client.on(events.NewMessage(chats=config.SOURCE_CHANNELS))
async def handler_new_post(event):
    """Обрабатывает новое сообщение в любом из исходных каналов."""

    if not event.message.text and not event.message.media:
        return

    # 1. Извлечение текста с минимальным экранированием (сохраняем Markdown символы)
    post_text = get_markdown_text(event.message)

    # 2. Добавление подписи
    final_text = post_text + config.SIGNATURE

    # 3. Обработка медиа (если есть)
    media_info = " (с медиа-вложением)" if event.message.media else ""

    print(f"Получен новый пост{media_info} из {event.chat_id}. Режим: {config.MODE}")

    if config.MODE == "AUTO":
        # АВТОМАТИЧЕСКАЯ ПУБЛИКАЦИЯ
        try:
            # Текст отправляется как есть (включая сырой Markdown).
            # Это может вызвать ошибки, если Aiogram увидит непарные HTML-теги.
            # Для АВТО-режима лучше использовать ИИ или принудительно очистить текст,
            # но пока оставляем сырой текст.
            await bot.send_message(
                chat_id=config.DESTINATION_CHANNEL,
                text=final_text,
                parse_mode=ParseMode.HTML  # Aiogram попытается интерпретировать экранированные символы
            )
            print(f"✅ Пост автоматически опубликован в {config.DESTINATION_CHANNEL}.")
        except Exception as e:
            print(f"❌ Ошибка при автоматической публикации: {e}")

    elif config.MODE == "REVIEW":
        # РУЧНАЯ ПРОВЕРКА
        await send_to_review(final_text, media_info, event.message)


# --- Функции администрирования (Aiogram) ---

async def send_to_review(text: str, media_info: str, original_message):
    """Отправляет пост на проверку админу с интерактивными кнопками."""

    # Сохраняем данные для кнопок
    review_data = {
        'text': text,
        'media': original_message.media,
        'caption': text
    }

    # Генерируем уникальный ID
    post_id = hash(text + str(asyncio.get_event_loop().time()))
    dp['review_posts'][post_id] = review_data

    builder = InlineKeyboardBuilder()

    builder.row(
        types.InlineKeyboardButton(text="✨ Уникализация (AI)", callback_data=f"ai_unique_{post_id}"),
        types.InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_{post_id}")
    )
    builder.row(
        types.InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"publish_{post_id}"),
        types.InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_{post_id}")
    )

    # ВАЖНОЕ ИСПРАВЛЕНИЕ: Используем <b> для заголовка, чтобы не было **
    await bot.send_message(
        chat_id=config.ADMIN_ID,
        text=f"<b>🔥 Новый пост на проверку!</b> {media_info}\n\n"
             f"<i>ID: {post_id}</i>\n"
             "------------------------\n"
             f"{text}",  # В теле поста будут видны ** и > (т.к. они экранированы)
        parse_mode=ParseMode.HTML,
        reply_markup=builder.as_markup()
    )


@dp.callback_query(lambda c: c.data and c.data.startswith(('ai_unique_', 'publish_', 'delete_', 'edit_')))
async def process_callback_query(callback_query: types.CallbackQuery):
    """Обработка нажатий на кнопки администрирования."""

    data_parts = callback_query.data.split('_')
    post_id_str = data_parts[-1]

    if len(data_parts) == 3 and data_parts[0] == 'ai' and data_parts[1] == 'unique':
        action = 'ai_unique'
    elif len(data_parts) == 2:
        action = data_parts[0]
    else:
        await callback_query.answer("❌ Неизвестный формат данных.")
        return

    try:
        post_id = int(post_id_str)
    except ValueError:
        await callback_query.answer("❌ Некорректный ID поста.")
        await callback_query.message.edit_text(f"❌ Ошибка ID: Пост для {action} не найден.", parse_mode=ParseMode.HTML)
        return

    if post_id not in dp['review_posts']:
        await callback_query.message.edit_text("❌ Ошибка: Пост не найден или уже обработан.", parse_mode=ParseMode.HTML)
        await callback_query.answer()
        return

    data = dp['review_posts'][post_id]
    current_text = data['text']

    await callback_query.message.edit_reply_markup()  # Убираем кнопки

    if action == "publish":
        # --- ОПУБЛИКОВАТЬ ---
        try:
            # Публикуем HTML-текст. Если он был уникализирован ИИ, он будет чистым HTML.
            # Если он не был обработан ИИ, он будет содержать экранированный Markdown.
            await bot.send_message(
                chat_id=config.DESTINATION_CHANNEL,
                text=current_text,
                parse_mode=ParseMode.HTML
            )
            # ИСПРАВЛЕНИЕ: Используем <b>
            await callback_query.message.edit_text(
                f"✅ <b>ОПУБЛИКОВАНО!</b>\n\n{current_text}",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            await callback_query.message.edit_text(
                f"❌ Ошибка публикации: {escape_html_entities(str(e))}\n\nОригинал: {current_text}",
                parse_mode=ParseMode.HTML
            )
        del dp['review_posts'][post_id]

    elif action == "delete":
        # --- УДАЛИТЬ ---
        # ИСПРАВЛЕНИЕ: Используем <b>
        await callback_query.message.edit_text(
            f"🗑️ <b>УДАЛЕНО.</b> (ID: {post_id})",
            parse_mode=ParseMode.HTML
        )
        del dp['review_posts'][post_id]

    elif action == "ai_unique":
        # --- УНИКАЛИЗАЦИЯ (AI) ---
        # ИСПРАВЛЕНИЕ: Используем <b>
        await callback_query.message.edit_text(
            f"🤖 <b>УНИКАЛИЗАЦИЯ...</b> Пожалуйста, подождите.\n\n"
            f"Оригинал: \n{current_text}",
            parse_mode=ParseMode.HTML
        )

        # 1. Получаем уникализированный и HTML-отформатированный текст от ИИ
        unique_text = await ai_unique_text(current_text)

        # 2. Обновляем данные и отправляем обратно на проверку
        data['text'] = unique_text
        dp['review_posts'][post_id] = data

        # Пересобираем клавиатуру
        builder = InlineKeyboardBuilder()
        builder.row(
            types.InlineKeyboardButton(text="✨ Уникализация (AI)", callback_data=f"ai_unique_{post_id}"),
            types.InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_{post_id}")
        )
        builder.row(
            types.InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"publish_{post_id}"),
            types.InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_{post_id}")
        )

        # ИСПРАВЛЕНИЕ: Используем <b>
        await callback_query.message.edit_text(
            f"🤖 <b>УНИКАЛИЗАЦИЯ ЗАВЕРШЕНА!</b>\n\n"
            f"<i>ID: {post_id}</i>\n"
            "------------------------\n"
            f"{unique_text}",  # Здесь ожидается чистый HTML от ИИ
            parse_mode=ParseMode.HTML,
            reply_markup=builder.as_markup()
        )

    elif action == "edit":
        # --- РЕДАКТИРОВАНИЕ ---
        # ИСПРАВЛЕНИЕ: Используем <b>
        await callback_query.message.edit_text(
            f"✏️ <b>ОТПРАВЬТЕ НОВЫЙ ТЕКСТ</b> для поста с ID: {post_id_str}. "
            "Ответьте на это сообщение новым текстом.",
            parse_mode=ParseMode.HTML
        )
        # Устанавливаем состояние для ожидания нового текста
        dp['waiting_for_edit'][callback_query.message.chat.id] = post_id

    await callback_query.answer()


@dp.message()
async def handle_admin_reply(message: types.Message):
    """Обрабатывает ответ админа с новым текстом для редактирования."""

    if message.chat.id in dp['waiting_for_edit'] and message.reply_to_message:
        post_id = dp['waiting_for_edit'].pop(message.chat.id)

        if post_id not in dp['review_posts']:
            await message.reply("❌ Ошибка: Пост для редактирования не найден или уже обработан.")
            return

        # Если новый текст не был уникализирован ИИ, он может содержать сырой Markdown
        new_text = message.text + config.SIGNATURE

        # Обновляем текст
        dp['review_posts'][post_id]['text'] = new_text

        # Пересобираем клавиатуру
        builder = InlineKeyboardBuilder()
        builder.row(
            types.InlineKeyboardButton(text="✨ Уникализация (AI)", callback_data=f"ai_unique_{post_id}"),
            types.InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_{post_id}")
        )
        builder.row(
            types.InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"publish_{post_id}"),
            types.InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_{post_id}")
        )

        # ИСПРАВЛЕНИЕ: Используем <b>
        await message.reply(
            f"✅ <b>ТЕКСТ ОБНОВЛЕН!</b>\n\n"
            f"<i>ID: {post_id}</i>\n"
            "------------------------\n"
            f"{new_text}",
            parse_mode=ParseMode.HTML,
            reply_markup=builder.as_markup()
        )


# --- Запуск ---

async def main():
    """Основная функция запуска клиента и бота."""

    # ВАЖНО: Хранилища уже инициализированы в глобальной области видимости,
    # но можно оставить их здесь для ясности (хотя это дублирование)
    # dp['review_posts'] = {}
    # dp['waiting_for_edit'] = {}

    await parser_client.start(password=config.TELEGRAM_PASSWORD)
    print("Telethon Client запущен.")

    await asyncio.gather(
        parser_client.run_until_disconnected(),
        dp.start_polling(bot)
    )


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")