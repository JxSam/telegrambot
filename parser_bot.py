import asyncio
import re
import os
import shutil
from html import escape

from telethon import TelegramClient, events
from telethon.tl.types import (
    MessageEntityBold, MessageEntityItalic, MessageEntityTextUrl, MessageEntityCode,
    MessageEntityPre, MessageEntityStrike, MessageEntityUnderline, MessageEntitySpoiler,
    MessageEntityUrl, MessageEntityCustomEmoji, MessageEntityMentionName, MessageEntityBlockquote
)
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import ParseMode
from aiogram.types import BufferedInputFile

import httpx
import config

# --- Настройки ---
DOWNLOAD_DIR = 'downloads'


def ensure_download_dir():
    """Создает папку downloads, если она не существует."""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# --- Инициализация клиентов ---
parser_client = TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH)
default_properties = DefaultBotProperties(parse_mode=ParseMode.HTML)
bot = Bot(token=config.BOT_TOKEN, default=default_properties)
dp = Dispatcher()
dp['review_posts'] = {}
dp['waiting_for_edit'] = {}


# --- Вспомогательные функции (HTML, Markdown, Медиа) ---

def escape_html_entities(text: str) -> str:
    """Экранирует специальные символы HTML: &, <, >."""
    return escape(text)


async def delete_temp_media(file_path: str):
    """Безопасно удаляет временный медиафайл."""
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f"🗑️ Временный медиафайл удален: {file_path}")
        except Exception as e:
            print(f"❌ Ошибка при удалении файла {file_path}: {e}")


def get_html_text(message) -> str:
    """Конвертирует объект Message из Telethon в HTML-разметку."""
    text = message.text
    if not text: return ""

    entities = message.entities if message.entities else []
    entities.sort(key=lambda x: x.offset)

    output = ""
    last_offset = 0

    for entity in entities:
        raw_text = text[last_offset:entity.offset]
        output += escape_html_entities(raw_text)

        entity_text = text[entity.offset:entity.offset + entity.length]

        if isinstance(entity, MessageEntityBold):
            output += f"<b>{entity_text}</b>"
        elif isinstance(entity, MessageEntityItalic):
            output += f"<i>{entity_text}</i>"
        elif isinstance(entity, MessageEntityStrike):
            output += f"<s>{entity_text}</s>"
        elif isinstance(entity, MessageEntityUnderline):
            output += f"<u>{entity_text}</u>"
        elif isinstance(entity, MessageEntitySpoiler):
            output += f"<tg-spoiler>{entity_text}</tg-spoiler>"
        elif isinstance(entity, MessageEntityCode):
            output += f"<code>{entity_text}</code>"
        elif isinstance(entity, MessageEntityPre):
            output += f"<pre>{entity_text}</pre>"
        elif isinstance(entity, MessageEntityTextUrl):
            output += f'<a href="{entity.url}">{entity_text}</a>'
        elif isinstance(entity, MessageEntityUrl):
            output += f'<a href="{entity_text}">{entity_text}</a>'
        elif isinstance(entity, MessageEntityMentionName):
            output += f'<a href="tg://user?id={entity.user_id}">{entity_text}</a>'
        elif isinstance(entity, MessageEntityCustomEmoji):
            output += f'<tg-emoji emoji-id="{entity.document_id}">{entity_text}</tg-emoji>'
        elif isinstance(entity, MessageEntityBlockquote):
            output += f"<blockquote>{entity_text}</blockquote>"
        else:
            output += escape_html_entities(entity_text)

        last_offset = entity.offset + entity.length

    remaining_text = text[last_offset:]
    output += escape_html_entities(remaining_text)

    # ФИНАЛЬНАЯ ЧИСТКА
    output = output.replace('&lt;', '<').replace('&gt;', '>').replace('&ast;', '').replace('&amp;ast;', '').replace(
        '&quot;', '"')
    return output


def convert_markdown_to_html(markdown_text: str) -> str:
    """Конвертирует MarkdownV2 символы в HTML."""
    html_text = markdown_text

    # 1. Markdown в HTML
    html_text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', html_text)
    html_text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', html_text)
    html_text = re.sub(r'_(.+?)_', r'<i>\1</i>', html_text)
    html_text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', html_text)
    html_text = re.sub(r'~(.+?)~', r'<s>\1</s>', html_text)
    html_text = re.sub(r'`(.+?)`', r'<code>\1</code>', html_text)
    html_text = re.sub(r'```(?:\w+)?\n?(.+?)```', r'<pre>\1</pre>', html_text, flags=re.DOTALL)

    # 2. Очистка от одиночных/разорванных символов Markdown
    html_text = html_text.replace('*', '').replace('_', '').replace('~', '').replace('`', '')
    return html_text


async def ai_unique_text(text: str) -> str:
    """Отправляет текст в OpenRouter API для уникализации."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {config.OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    prompt = config.AI_PROMPT.format(text=text)
    data = {"model": config.OPENROUTER_MODEL_NAME, "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "text"}}

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            ai_markdown_text = result['choices'][0]['message']['content'].strip()
            return convert_markdown_to_html(ai_markdown_text)
        except Exception as e:
            print(f"❌ Ошибка при запросе к AI: {e}")
            error_message = f"❌ Ошибка уникализации. {escape_html_entities(str(e))}"
            return f"<b>{error_message}</b>\n\nОригинал:\n{text}"


# --- Обработчик парсинга (Telethon) ---

@parser_client.on(events.NewMessage(chats=config.SOURCE_CHANNELS))
async def handler_new_post(event):
    """Обрабатывает новое сообщение в любом из исходных каналов."""

    if not event.message.text and not event.message.media: return

    post_text = get_html_text(event.message)
    final_text = post_text + config.SIGNATURE
    media_path = None
    media_info = ""

    if event.message.media:
        ensure_download_dir()
        media_info = " (с медиа-вложением)"
        try:
            media_path = await event.message.download_media(file=DOWNLOAD_DIR)
            print(f"📥 Медиа загружено: {media_path}")
        except Exception as e:
            print(f"❌ Ошибка при загрузке медиа: {e}")
            media_path = None

    print(f"Получен новый пост{media_info} из {event.chat_id}. Режим: {config.MODE}")

    if config.MODE == "AUTO":
        await bot.send_message(chat_id=config.DESTINATION_CHANNEL, text=final_text, parse_mode=ParseMode.HTML)
        print(f"✅ Пост автоматически опубликован в {config.DESTINATION_CHANNEL}.")
        if media_path: await delete_temp_media(media_path)
    elif config.MODE == "REVIEW":
        await send_to_review(final_text, media_info, media_path)


# --- Функции администрирования (Aiogram) ---

async def send_to_review(text: str, media_info: str, media_path: str | None):
    """Отправляет пост на проверку админу с интерактивными кнопками."""
    # Уникальный ID поста
    post_id = hash(text + str(asyncio.get_event_loop().time()))

    review_data = {'text': text, 'media_path': media_path, 'caption': text}
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

    review_message = f"<b>🔥 Новый пост на проверку!</b> {media_info}\n\n" \
                     f"<i>ID: {post_id}</i>\n" \
                     "------------------------\n" \
                     f"{text}"

    if media_path:
        media_type = media_path.lower().split('.')[-1]

        with open(media_path, 'rb') as media_file:
            media_data = media_file.read()

        file_input = BufferedInputFile(media_data, filename=os.path.basename(media_path))

        if media_type in ('png', 'jpg', 'jpeg', 'webp'):
            await bot.send_photo(chat_id=config.ADMIN_ID, photo=file_input, caption=review_message,
                                 parse_mode=ParseMode.HTML, reply_markup=builder.as_markup())
        elif media_type in ('mp4', 'mov', 'avi', 'gif', 'webm'):
            await bot.send_video(chat_id=config.ADMIN_ID, video=file_input, caption=review_message,
                                 parse_mode=ParseMode.HTML, reply_markup=builder.as_markup())
        else:
            await bot.send_message(chat_id=config.ADMIN_ID, text=review_message, parse_mode=ParseMode.HTML,
                                   reply_markup=builder.as_markup())
            await delete_temp_media(media_path)
            review_data['media_path'] = None
    else:
        await bot.send_message(chat_id=config.ADMIN_ID, text=review_message, parse_mode=ParseMode.HTML,
                               reply_markup=builder.as_markup())


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
        return

    if post_id not in dp['review_posts']:
        # Пост не найден, удаляем сообщение, чтобы не висело
        await callback_query.message.delete()
        await callback_query.answer()
        return

    data = dp['review_posts'][post_id]
    current_text = data['text']
    media_path = data.get('media_path')

    is_media_message = callback_query.message.caption is not None

    if action == "publish":
        # --- ОПУБЛИКОВАТЬ ---

        # 1. Убираем кнопки (пытаемся, но игнорируем ошибку "not modified")
        try:
            if is_media_message:
                await callback_query.message.edit_caption(caption=callback_query.message.caption, reply_markup=None,
                                                          parse_mode=ParseMode.HTML)
            else:
                await callback_query.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

        try:
            # 2. Публикация в целевой канал
            if media_path and os.path.exists(media_path):
                media_type = media_path.lower().split('.')[-1]

                with open(media_path, 'rb') as media_file:
                    media_data = media_file.read()

                file_input = BufferedInputFile(media_data, filename=os.path.basename(media_path))

                if media_type in ('png', 'jpg', 'jpeg', 'webp'):
                    await bot.send_photo(chat_id=config.DESTINATION_CHANNEL, photo=file_input, caption=current_text,
                                         parse_mode=ParseMode.HTML)
                elif media_type in ('mp4', 'mov', 'avi', 'gif', 'webm'):
                    await bot.send_video(chat_id=config.DESTINATION_CHANNEL, video=file_input, caption=current_text,
                                         parse_mode=ParseMode.HTML)
                else:
                    await bot.send_message(chat_id=config.DESTINATION_CHANNEL, text=current_text,
                                           parse_mode=ParseMode.HTML)
            else:
                await bot.send_message(chat_id=config.DESTINATION_CHANNEL, text=current_text, parse_mode=ParseMode.HTML)

            # 3. Редактируем сообщение админу (ГАРАНТИРУЕМ УНИКАЛЬНОСТЬ ФИНАЛЬНОГО ТЕКСТА)
            unique_suffix = f'&#x200B; (ID:{post_id})'
            final_admin_msg = f"✅ <b>ОПУБЛИКОВАНО!</b>\n\n{current_text}{unique_suffix}"

            if is_media_message:
                await callback_query.message.edit_caption(final_admin_msg, parse_mode=ParseMode.HTML)
            else:
                await callback_query.message.edit_text(final_admin_msg, parse_mode=ParseMode.HTML)

        except Exception as e:
            # 4. Обработка ошибки публикации (ГАРАНТИРУЕМ УНИКАЛЬНОСТЬ СООБЩЕНИЯ)
            unique_suffix = f'&#x200B; (Error ID:{post_id})'
            error_msg = f"❌ Ошибка публикации: {escape_html_entities(str(e))}\n\nОригинал: {current_text}{unique_suffix}"

            if is_media_message:
                await callback_query.message.edit_caption(error_msg, parse_mode=ParseMode.HTML)
            else:
                await callback_query.message.edit_text(error_msg, parse_mode=ParseMode.HTML)

        # 5. ОЧИСТКА ВРЕМЕННЫХ ФАЙЛОВ
        if media_path: await delete_temp_media(media_path)

        # 6. Удаление данных о посте
        del dp['review_posts'][post_id]

    elif action == "delete":
        # --- УДАЛИТЬ ---
        # 1. ОЧИСТКА ВРЕМЕННЫХ ФАЙЛОВ
        if media_path: await delete_temp_media(media_path)
        del dp['review_posts'][post_id]

        # 2. Удаляем сообщение
        await callback_query.message.delete()
        # 3. Отправляем подтверждение
        await bot.send_message(callback_query.from_user.id, f"🗑️ <b>Пост удален.</b> (ID: {post_id})",
                               parse_mode=ParseMode.HTML)

    elif action == "ai_unique":
        # --- ГАРАНТИРОВАННАЯ УНИКАЛИЗАЦИЯ С СОХРАНЕНИЕМ ТЕКСТА ---

        # 1. Уведомляем о начале обработки, не удаляя старый текст
        unique_prefix = f'&#8203;'  # Невидимый символ для гарантии модификации

        # Создаем временный текст, добавляя статус в начало *текущего* текста:
        status_message = f"🤖 <b>{unique_prefix}УНИКАЛИЗАЦИЯ (ИДЁТ)...</b>\n"
        temp_processing_text = f"{status_message}\n------------------------\n{current_text}"

        reply_markup = None

        try:
            # Пытаемся обновить статус и убрать кнопки
            if is_media_message:
                await callback_query.message.edit_caption(temp_processing_text, reply_markup=reply_markup,
                                                          parse_mode=ParseMode.HTML)
            else:
                await callback_query.message.edit_text(temp_processing_text, reply_markup=reply_markup,
                                                       parse_mode=ParseMode.HTML)
        except Exception as e:
            # Если тут ошибка "not modified", это значит, что кто-то кликнул слишком быстро. Продолжаем обработку.
            print(f"❌ Ошибка редактирования при начале уникализации: {e}")

        # 2. Главное: ВЫЗЫВАЕМ УНИКАЛИЗАЦИЮ ВСЕГДА!
        unique_text = await ai_unique_text(current_text)

        # 3. Обновляем данные
        data['text'] = unique_text
        dp['review_posts'][post_id] = data

        # 4. Пересобираем клавиатуру
        builder = InlineKeyboardBuilder()
        builder.row(
            types.InlineKeyboardButton(text="✨ Уникализация (AI)", callback_data=f"ai_unique_{post_id}"),
            types.InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_{post_id}")
        )
        builder.row(
            types.InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"publish_{post_id}"),
            types.InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_{post_id}")
        )

        # 5. Редактируем сообщение (медиа остается, текст обновляется)
        final_message = f"🤖 <b>УНИКАЛИЗАЦИЯ ЗАВЕРШЕНА!</b>\n\n" \
                        f"<i>ID: {post_id}</i>\n" \
                        "------------------------\n" \
                        f"{unique_text}"

        if is_media_message:
            await callback_query.message.edit_caption(caption=final_message, parse_mode=ParseMode.HTML,
                                                      reply_markup=builder.as_markup())
        else:
            await callback_query.message.edit_text(text=final_message, parse_mode=ParseMode.HTML,
                                                   reply_markup=builder.as_markup())

    elif action == "edit":
        # --- РЕДАКТИРОВАНИЕ ---
        # 1. Убираем кнопки
        try:
            if is_media_message:
                await callback_query.message.edit_caption(callback_query.message.caption, reply_markup=None,
                                                          parse_mode=ParseMode.HTML)
            else:
                await callback_query.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

        # 2. Устанавливаем состояние (текст для запроса ответа)
        await callback_query.message.edit_text(
            f"✏️ <b>ОТПРАВЬТЕ НОВЫЙ ТЕКСТ</b> для поста с ID: {post_id_str}. "
            "Ответьте на это сообщение новым текстом.",
            parse_mode=ParseMode.HTML
        )
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

    ensure_download_dir()

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