from telethon import events

from aiogram.enums import ParseMode

from utils import *


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