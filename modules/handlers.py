import asyncio
import os

from telethon import events

from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import ParseMode
from aiogram.types import BufferedInputFile

from utils import *

# --- Функции администрирования (Aiogram) ---

class AdminHandler():
    def __init__(self, bot, dispatcher):
        self.bot = bot
        self.dp = dispatcher

    async def send_to_review(self, text: str, media_info: str, media_path: str):
        """
        Отправляет пост на проверку админу с интерактивными кнопками.
        """
        # Уникальный ID поста
        post_id = hash(text + str(asyncio.get_event_loop().time()))

        review_data = {'text': text, 'media_path': media_path, 'caption': text}

        self.dp['review_posts'][post_id] = review_data

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
                await self.bot.send_photo(chat_id=config.ADMIN_ID, photo=file_input, caption=review_message,
                                     parse_mode=ParseMode.HTML, reply_markup=builder.as_markup())
            elif media_type in ('mp4', 'mov', 'avi', 'gif', 'webm'):
                await self.bot.send_video(chat_id=config.ADMIN_ID, video=file_input, caption=review_message,
                                     parse_mode=ParseMode.HTML, reply_markup=builder.as_markup())
            else:
                await self.bot.send_message(chat_id=config.ADMIN_ID, text=review_message, parse_mode=ParseMode.HTML,
                                       reply_markup=builder.as_markup())
                await delete_temp_media(media_path)
                review_data['media_path'] = None

        else:
            await self.bot.send_message(chat_id=config.ADMIN_ID, text=review_message, parse_mode=ParseMode.HTML,
                               reply_markup=builder.as_markup())

    async def process_callback_query(self, callback_query: types.CallbackQuery):
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

        if post_id not in self.dp['review_posts']:
            # Пост не найден, удаляем сообщение, чтобы не висело
            await callback_query.message.delete()
            await callback_query.answer()
            return

        data = self.dp['review_posts'][post_id]
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
                        await self.bot.send_photo(chat_id=config.DESTINATION_CHANNEL, photo=file_input, caption=current_text,
                                             parse_mode=ParseMode.HTML)
                    elif media_type in ('mp4', 'mov', 'avi', 'gif', 'webm'):
                        await self.bot.send_video(chat_id=config.DESTINATION_CHANNEL, video=file_input, caption=current_text,
                                             parse_mode=ParseMode.HTML)
                    else:
                        await self.bot.send_message(chat_id=config.DESTINATION_CHANNEL, text=current_text,
                                               parse_mode=ParseMode.HTML)
                else:
                    await self.bot.send_message(chat_id=config.DESTINATION_CHANNEL, text=current_text,
                                           parse_mode=ParseMode.HTML)

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
            del self.dp['review_posts'][post_id]

        elif action == "delete":
            # --- УДАЛИТЬ ---
            # 1. ОЧИСТКА ВРЕМЕННЫХ ФАЙЛОВ
            if media_path: await delete_temp_media(media_path)
            del self.dp['review_posts'][post_id]

            # 2. Удаляем сообщение
            await callback_query.message.delete()
            # 3. Отправляем подтверждение
            await self.bot.send_message(callback_query.from_user.id, f"🗑️ <b>Пост удален.</b> (ID: {post_id})",
                                   parse_mode=ParseMode.HTML)

        elif action == "ai_unique":
            clean_text = strip_signature(current_text)
            unique_body = await ai_unique_text(clean_text)
            final_unique_text = unique_body + config.SIGNATURE

            data['text'] = final_unique_text
            self.dp['review_posts'][post_id] = data

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
                            f"{final_unique_text}"

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
                await callback_query.answer("🤖 Уникализация текста…", show_alert=False)
            except Exception:
                pass

            # 2. Устанавливаем состояние (текст для запроса ответа)
            await callback_query.message.edit_text(
                f"✏️ <b>ОТПРАВЬТЕ НОВЫЙ ТЕКСТ</b> для поста с ID: {post_id_str}. "
                "Ответьте на это сообщение новым текстом.",
                parse_mode=ParseMode.HTML
            )
            self.dp['waiting_for_edit'][callback_query.message.chat.id] = post_id

        await callback_query.answer()

    async def handle_admin_reply(self, message: types.Message):
        """Обрабатывает ответ админа с новым текстом для редактирования."""

        if message.chat.id in self.dp['waiting_for_edit'] and message.reply_to_message:
            post_id = self.dp['waiting_for_edit'].pop(message.chat.id)

            if post_id not in self.dp['review_posts']:
                await message.reply("❌ Ошибка: Пост для редактирования не найден или уже обработан.")
                return

            new_text = message.text + config.SIGNATURE

            # Обновляем текст
            self.dp['review_posts'][post_id]['text'] = new_text

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

class ParsHandler():
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