import asyncio
import os
from multiprocessing import connection

from aiogram import Dispatcher, Router
from aiogram.fsm.context import FSMContext
from telethon import events
from modules.database import *
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from aiogram.types import BufferedInputFile
from modules.functions import *
from modules.ai.service import ai_unique_text
from modules.keyboards import *
from utils import *

# --- Главное меню ---
class MenuHandler:
    def __init__(self, dp: Dispatcher):
        self.dp = dp
        self.execute = ""
        self.chats = []

    async def start(self, message: types.Message):
        await message.answer(
            "👋 Привет!\n\n"
            "Я бот для модерации постов.\n"
            "Выберите действие:",
            reply_markup=build_reply_menu(main_menu_keyboard)
        )

    async def admin(self, message: types.Message):
        await message.answer(
            "📦 Очередь постов: 0\n"
            "⌛️ Запланировано: 0\n"
            "✅ Бот слушает каналы и присылает уведомления\n"
            "👉 Выберите действие\n",
            reply_markup=build_reply_menu(admin_kb)
        )

    async def show_posts(self, message: types.Message):
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Posts ORDER BY post_id DESC")
        posts = cursor.fetchall()

        if len(posts) == 0:
            await message.answer(
                "📦 В очереди пока нет постов."
            )
        else:
            await message.answer(
                f"📦 В очереди: {len(posts)} постов\n\n"
                f"👉 Выберите действие:",
                reply_markup=build_inline_menu(check_posts)
            )

    def register(self):
        self.dp.message.register(self.start, CommandStart())
        self.dp.message.register(self.admin, lambda m: m.text == "🌐 Главное меню")
        self.dp.message.register(self.admin, lambda m: m.text == "💎 Администрирование")
        self.dp.message.register(self.show_posts, lambda m: m.text == "📤 Просмотр очереди")

# --- Парсер ---
class ParsHandler:
    def __init__(self, bot, dp, dir, client):
        self.bot = bot
        self.dp = dp
        self.DOWNLOAD_DIR = dir
        self.client = client
        self.chats = []

    def load_channels(self):
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM Channels")
        self.chats = [row[0] for row in cursor.fetchall()]
        conn.close()

    async def send_to_review(self, text: str, media_info: str, media_path: str):
        """
        Отправляет пост на проверку админу с интерактивными кнопками.
        """
        # Уникальный ID поста
        post_id = hash(text + str(asyncio.get_event_loop().time()))

        review_data = {'text': text, 'media_path': media_path, 'caption': text}

        self.dp['review_posts'][post_id] = review_data

        builder = build_actions_menu(post_id, text)

        review_message = f"<b>🔥 Новый пост на проверку!</b> {media_info}\n\n" \
                     f"<i>ID: {post_id}</i>\n" \
                     "------------------------\n"

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(f"INSERT INTO Posts (post_id, text) VALUES ('{post_id}', '{text}')")
        conn.commit()
        conn.close()

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

    # --- Обработчик парсинга (Telethon) ---
    async def handler_new_post(self, event):
        """Обрабатывает новое сообщение в любом из исходных каналов."""
        if not event.message.text and not event.message.media: return
        post_text = get_html_text(event.message)
        final_text = post_text + config.SIGNATURE
        media_path = None
        media_info = ""

        if event.message.media:
            ensure_download_dir(self.DOWNLOAD_DIR)
            media_info = " (с медиа-вложением)"
            try:
                media_path = await event.message.download_media(file=self.DOWNLOAD_DIR)
                print(f"📥 Медиа загружено: {media_path}")
            except Exception as e:
                print(f"❌ Ошибка при загрузке медиа: {e}")
                media_path = None

        print(f"Получен новый пост{media_info} из {event.chat_id}. Режим: {config.MODE}")

        if config.MODE == "AUTO":
            await self.bot.send_message(chat_id=config.DESTINATION_CHANNEL, text=final_text, parse_mode=ParseMode.HTML)
            print(f"✅ Пост автоматически опубликован в {config.DESTINATION_CHANNEL}.")
            if media_path: await delete_temp_media(media_path)
        elif config.MODE == "REVIEW":
            await self.send_to_review(final_text, media_info, media_path)

    def register(self):
        # регистрация обработчика Telethon
        self.client.add_event_handler(self.handler_new_post, events.NewMessage(chats=self.chats))

# --- Настройки ---
class SettingsState(StatesGroup):
    waiting_channel = State()

class SettingsHandler(MenuHandler, ParsHandler):
    def __init__(self, dp: Dispatcher, pars_handler: ParsHandler):
        super().__init__(dp)
        self.pars_handler = pars_handler

    async def open_settings(self, message: types.Message):
        await message.answer(
            "⚙️ <b>Настройки</b>\n\nВыберите пункт:",
            parse_mode="HTML",
            reply_markup=build_inline_menu(settings_menu_kb)
        )

    async def get_channel(self, message: types.Message, state: FSMContext):
        channel = message.text.strip()

        if not channel.startswith("@"):
            await message.answer("❌ Канал должен быть в формате @channel_name")
            return

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(self.execute.format(channel))

        await message.answer(f"✅ Канал {channel} сохранён")
        await state.clear()

    async def callback(self, callback: types.CallbackQuery, state: FSMContext):
        data = callback.data.split("?")
        action = data[0]

        if action == "settings:channel_actions":
            channel = data[1]
            await callback.message.edit_text(
                f"📡 <b>Канал:</b> {channel}\n\n"
                "Вы хотите удалить канал?",
                parse_mode="HTML",
                reply_markup=build_channel_actions(channel)
            )

        elif action == "settings:channel_delete":
            channel = data[1]
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM Channels WHERE name = ?", (channel,))

            await callback.message.edit_text(
                f"❌ Канал {channel} удалён"
            )

        elif action == "settings:list":
            await callback.message.edit_text(
                "📋 <b>Подключeнные каналы</b>",
                parse_mode="HTML",
                reply_markup=build_variable_list()
            )

        elif action == "settings:channel_add":
            await callback.message.edit_text(
                "Пришлите ссылку на канал @channel_name"
            )
            self.execute = "INSERT OR IGNORE INTO Channels (name) VALUES ('{}')"
            await state.set_state(SettingsState.waiting_channel)

        elif action == "settings:channel_edit":
            await callback.message.edit_text(
                "Пришлите ссылку на канал @channel_name"
            )
            self.execute = "UPDATE Settings SET value = '{}' WHERE name = 'DESTINATION_CHANNEL'"
            await state.set_state(SettingsState.waiting_channel)

        elif action == "settings:channel":
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT value FROM Settings WHERE name = "DESTINATION_CHANNEL"')
                channel = cursor.fetchall()[0][0]
            await callback.message.edit_text(
                f"Текущий канал {channel}\n"
                "Сюда выкладываются посты.",
                parse_mode="HTML",
                reply_markup=build_inline_menu(channel_kb)
            )

        elif action == "settings:back":
            await callback.message.edit_text(
                "⚙️ <b>Настройки</b>\n\nВыберите пункт:",
                parse_mode="HTML",
                reply_markup=build_inline_menu(settings_menu_kb)
            )

        await callback.answer()

    def register(self):
        self.dp.message.register(self.open_settings, lambda m: m.text == "⚙️ Настройки")
        self.dp.callback_query.register(self.callback, lambda c: c.data.startswith("settings:"))
        self.dp.message.register(
            self.get_channel,
            SettingsState.waiting_channel
        )

class AdminHandler(MenuHandler):
    def __init__(self, dp: Dispatcher, bot):
        super().__init__(dp)
        self.post_id = 0
        self.waiting_edit_message_id = None
        self.bot = bot
        self.text = str

    async def callback_post(self, callback: types.CallbackQuery, state: FSMContext):
        data = callback.data.split("%$")
        print(data)
        action = data[0]

        if action == "post:check":
            self.post_id = data[1]
            self.text = data[2]
            await callback.message.answer(
                f"<b>Post = {self.post_id}</b>\n"
                f"Text = {self.text}",
                reply_markup=build_reply_menu(read_buttons)
            )

        elif action == "post:round_check":
            conn = connect_db()
            cursor = conn.cursor()

            cursor.execute("""
                    SELECT * FROM Posts
                    ORDER BY post_id ASC
                    LIMIT 1
                """)
            data = cursor.fetchone()

            conn.close()

            if not data:
                await callback.message.answer("🚫 Постов нет")
                await callback.answer()
                return

            self.post_id = data[1]
            self.text = data[2]

            await callback.message.answer(
                f"<b>Post = {self.post_id}</b>\n"
                f"Text = {self.text}",
                reply_markup=build_reply_menu(next_posts)
            )

            await callback.answer()

    async def round_next_post(self, message: types.Message):
        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM Posts
            WHERE post_id > ?
            ORDER BY post_id
            LIMIT 1
        """, (self.post_id,))

        data = cursor.fetchone()
        conn.close()

        if not data:
            await message.answer("🚫 Нет следующих постов")
            return

        self.post_id = data[1]
        self.text = data[2]

        await message.answer(
            f"<b>Post = {self.post_id}</b>\n"
            f"Text = {self.text}",
            reply_markup=build_reply_menu(next_posts)
        )

    async def round_prev_post(self, message: types.Message):
        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM Posts
            WHERE post_id < ?
            ORDER BY post_id DESC
            LIMIT 1
        """, (self.post_id,))

        data = cursor.fetchone()
        conn.close()

        if not data:
            await message.answer("🚫 Нет предыдущих постов")
            return

        self.post_id = data[1]
        self.text = data[2]

        await message.answer(
            f"<b>Post = {self.post_id}</b>\n"
            f"Text = {self.text}",
            reply_markup=build_reply_menu(next_posts)
        )

    async def publish_post(self, message: types.Message):    # 2. Публикация в целевой канал
            sent_message = await self.bot.send_message(
                chat_id=config.DESTINATION_CHANNEL,
                text=self.text,
                parse_mode=ParseMode.HTML
            )
            if sent_message.chat.username:
                post_link = f"https://t.me/{sent_message.chat.username}/{sent_message.message_id}"
            else:
                # приватный канал
                chat_id = str(sent_message.chat.id).replace("-100", "")
                post_link = f"https://t.me/c/{chat_id}/{sent_message.message_id}"
            await message.answer(
                f'<b>✅ Опубликовано\n</b>'
                f'Link = {post_link}',
                parse_mode=ParseMode.HTML
            )
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Posts WHERE post_id = ?", (self.post_id,))
            conn.commit()
            conn.close()

    async def delete_post(self, message: types.Message):
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Posts WHERE post_id = ?", (self.post_id,))
        conn.commit()
        conn.close()
        await message.answer(
            f'🗑️ <b>Пост удален.</b> (ID: {self.post_id})',
            reply_markup=build_reply_menu(next_posts)
        )

    async def read_post(self, message: types.Message):
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
                    SELECT * FROM Posts
                    WHERE post_id = ?
                    ORDER BY post_id DESC
                """, (self.post_id,))

        data = cursor.fetchone()
        conn.close()
        if not data:
            await message.answer("🚫 Ошибка, отсутствует")
            return

        self.post_id = data[1]
        self.text = data[2]

        await message.answer(
            f"<b>️️️⚡️️ Редактирование. Текст:</b>\n"
            "------------------------\n"
            f"{self.text}",
            reply_markup=build_reply_menu(read_buttons)
        )

    async def read_post_text(self, message: types.Message):

        msg = await message.answer(
            "✏️ Пришлите новый текст ответом на это сообщение"
        )

        self.waiting_edit_message_id = msg.message_id

    async def handle_edit_reply(self, message: types.Message):

        if not message.reply_to_message:
            return

        if message.reply_to_message.message_id != self.waiting_edit_message_id:
            return

        self.text = message.text
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE Posts SET text = ? WHERE post_id = ?",
            (self.text, self.post_id)
        )
        print(cursor)
        conn.commit()
        conn.close()

        await message.answer(f"✅ <b>ТЕКСТ ОБНОВЛЕН!</b>\n\n"
                "------------------------\n"
                f"{self.text}",
                parse_mode=ParseMode.HTML,)

        self.waiting_edit_message_id = None


    def register(self):
        self.dp.callback_query.register(self.callback_post, lambda c: c.data.startswith("post:"))
        self.dp.message.register(self.round_next_post, lambda m: m.text == "➡️ Следующий")
        self.dp.message.register(self.round_prev_post, lambda m: m.text == "⬅️ Предыдущий")
        self.dp.message.register(self.delete_post, lambda m: m.text == "❌ Удалить")
        self.dp.message.register(self.read_post, lambda m: m.text == "️️️⚡️ Действия")
        self.dp.message.register(self.read_post_text, lambda m: m.text == "✏️ Изменить текст")
        self.dp.message.register(self.publish_post, lambda m: m.text == "✅ Опубликовать")
        self.dp.message.register(self.handle_edit_reply)

class DeleteStates(StatesGroup):
    waiting_reason = State()

class DeleteHandler:
    def __init__(self):
        self.router = Router()
        self.register_handlers()

    def register_handlers(self):
        self.router.message.register(self.get_reason, DeleteStates.waiting_reason)

    async def ask_reason(self, message: types.Message, state: FSMContext):
        await state.set_state(DeleteStates.waiting_reason)
        await message.answer("Напиши причину удаления:")

    async def get_reason(self, message: types.Message, state: FSMContext):
        reason = message.text
        await message.answer(f"Причина: {reason}")
        await state.clear()

# --- Функции администрирования ---
# class AdminHandler():
#     def __init__(self, bot, dispatcher):
#         self.bot = bot
#         self.dp = dispatcher
#
#     async def process_callback_query(self, callback_query: types.CallbackQuery):
#         """Обработка нажатий на кнопки администрирования."""
#
#         data_parts = callback_query.data.split('_')
#         post_id_str = data_parts[-1]
#
#         if len(data_parts) == 3 and data_parts[0] == 'ai' and data_parts[1] == 'unique':
#             action = 'ai_unique'
#         elif len(data_parts) == 2:
#             action = data_parts[0]
#         else:
#             await callback_query.answer("❌ Неизвестный формат данных.")
#             return
#
#         try:
#             post_id = int(post_id_str)
#         except ValueError:
#             await callback_query.answer("❌ Некорректный ID поста.")
#             return
#
#         if post_id not in self.dp['review_posts']:
#             # Пост не найден, удаляем сообщение, чтобы не висело
#             await callback_query.message.delete()
#             await callback_query.answer()
#             return
#
#         data = self.dp['review_posts'][post_id]
#         current_text = data['text']
#         media_path = data.get('media_path')
#
#         is_media_message = callback_query.message.caption is not None
#
#         if action == "publish":
#             # --- ОПУБЛИКОВАТЬ ---
#             try:
#                 if is_media_message:
#                     await callback_query.message.edit_caption(caption=callback_query.message.caption, reply_markup=None,
#                                                               parse_mode=ParseMode.HTML)
#                 else:
#                     await callback_query.message.edit_reply_markup(reply_markup=None)
#             except Exception:
#                 pass
#
#             try:
#                 await callback_query.message.edit_caption(caption="⏳ Публикация…", parse_mode=ParseMode.HTML)
#                 # 2. Публикация в целевой канал
#                 if media_path and os.path.exists(media_path):
#                     media_type = media_path.lower().split('.')[-1]
#
#                     with open(media_path, 'rb') as media_file:
#                         media_data = media_file.read()
#
#                     file_input = BufferedInputFile(media_data, filename=os.path.basename(media_path))
#
#                     if media_type in ('png', 'jpg', 'jpeg', 'webp'):
#                         sent_message = await self.bot.send_photo(
#                             chat_id=config.DESTINATION_CHANNEL,
#                             photo=file_input,
#                             caption=current_text,
#                             parse_mode=ParseMode.HTML
#                         )
#                     elif media_type in ('mp4', 'mov', 'avi', 'gif', 'webm'):
#                         sent_message = await self.bot.send_video(
#                             chat_id=config.DESTINATION_CHANNEL,
#                             video=file_input,
#                             caption=current_text,
#                             parse_mode=ParseMode.HTML
#                         )
#                     else:
#                         sent_message = await self.bot.send_message(
#                             chat_id=config.DESTINATION_CHANNEL,
#                             text=current_text,
#                             parse_mode=ParseMode.HTML
#                         )
#                 else:
#                     sent_message = await self.bot.send_message(
#                         chat_id=config.DESTINATION_CHANNEL,
#                         text=current_text,
#                         parse_mode=ParseMode.HTML
#                     )
#                 if sent_message.chat.username:
#                     post_link = f"https://t.me/{sent_message.chat.username}/{sent_message.message_id}"
#                 else:
#                     # приватный канал
#                     chat_id = str(sent_message.chat.id).replace("-100", "")
#                     post_link = f"https://t.me/c/{chat_id}/{sent_message.message_id}"
#
#                 # 3. Отправляем сообщение об успешности
#                 await self.bot.send_message(
#                     callback_query.from_user.id,
#                     f"✅ <b>Пост опубликован.</b>\n🔗 <a href=\"{post_link}\">Открыть пост</a>",
#                     parse_mode=ParseMode.HTML,
#                     disable_web_page_preview=True
#                 )
#                 await callback_query.message.delete()
#
#             except Exception as e:
#                 # 4. Обработка ошибки публикации
#                 unique_suffix = f'&#x200B; (Error ID:{post_id})'
#                 error_msg = f"❌ Ошибка публикации: {escape_html_entities(str(e))}\n\nОригинал: {current_text}{unique_suffix}"
#
#                 if is_media_message:
#                     await callback_query.message.edit_caption(error_msg, parse_mode=ParseMode.HTML)
#                 else:
#                     await callback_query.message.edit_text(error_msg, parse_mode=ParseMode.HTML)
#
#             if media_path: await delete_temp_media(media_path)
#             del self.dp['review_posts'][post_id]
#
#         elif action == "delete":
#             # --- УДАЛИТЬ ---
#             if media_path: await delete_temp_media(media_path)
#             del self.dp['review_posts'][post_id]
#
#             await callback_query.message.delete()
#             await self.bot.send_message(callback_query.from_user.id, f"🗑️ <b>Пост удален.</b> (ID: {post_id})",
#                                    parse_mode=ParseMode.HTML)
#
#         elif action == "ai_unique":
#             clean_text = strip_signature(current_text)
#             unique_body = await ai_unique_text(clean_text)
#             final_unique_text = unique_body + config.SIGNATURE
#
#             data['text'] = final_unique_text
#             self.dp['review_posts'][post_id] = data
#
#             # 4. Пересобираем клавиатуру
#             builder = build_buttons_post(post_id)
#
#             # 5. Редактируем сообщение (медиа остается, текст обновляется)
#             final_message = f"🤖 <b>УНИКАЛИЗАЦИЯ ЗАВЕРШЕНА!</b>\n\n" \
#                             f"<i>ID: {post_id}</i>\n" \
#                             "------------------------\n" \
#                             f"{final_unique_text}"
#
#             if is_media_message:
#                 await callback_query.message.edit_caption(caption=final_message, parse_mode=ParseMode.HTML,
#                                                           reply_markup=builder.as_markup())
#             else:
#                 await callback_query.message.edit_text(text=final_message, parse_mode=ParseMode.HTML,
#                                                        reply_markup=builder.as_markup())
#
#         elif action == "edit":
#             # --- РЕДАКТИРОВАНИЕ ---
#             builder = InlineKeyboardBuilder()
#             builder.row(
#                 types.InlineKeyboardButton(
#                     text="⬅️ Вернуться",
#                     callback_data=f"back_{post_id}"
#                 )
#             )
#
#             # 2. Устанавливаем состояние (текст для запроса ответа)
#             await callback_query.message.edit_text(
#                 f"✏️ <b>ОТПРАВЬТЕ НОВЫЙ ТЕКСТ</b> для поста с ID: {post_id_str}. "
#                 "Ответьте на это сообщение новым текстом.",
#                 parse_mode=ParseMode.HTML
#                 , reply_markup=builder.as_markup()
#             )
#             self.dp['waiting_for_edit'][callback_query.message.chat.id] = post_id
#         elif action == "back":
#             # Сбрасываем режим редактирования
#             self.dp['waiting_for_edit'].pop(callback_query.message.chat.id, None)
#
#             builder = build_buttons_post(post_id)
#
#             final_message = (
#                 f"<i>ID: {post_id}</i>\n"
#                 "------------------------\n"
#                 f"{current_text}"
#             )
#
#             if is_media_message:
#                 await callback_query.message.edit_caption(
#                     caption=final_message,
#                     parse_mode=ParseMode.HTML,
#                     reply_markup=builder.as_markup()
#                 )
#             else:
#                 await callback_query.message.edit_text(
#                     final_message,
#                     parse_mode=ParseMode.HTML,
#                     reply_markup=builder.as_markup()
#                 )
#
#         await callback_query.answer()
#
#     async def handle_admin_reply(self, message: types.Message):
#         """Обрабатывает ответ админа с новым текстом для редактирования."""
#
#         if message.chat.id in self.dp['waiting_for_edit'] and message.reply_to_message:
#             post_id = self.dp['waiting_for_edit'].pop(message.chat.id)
#
#             if post_id not in self.dp['review_posts']:
#                 await message.reply("❌ Ошибка: Пост для редактирования не найден или уже обработан.")
#                 return
#
#             new_text = message.text + config.SIGNATURE
#
#             # Обновляем текст
#             self.dp['review_posts'][post_id]['text'] = new_text
#
#             # Пересобираем клавиатуру
#             builder = build_buttons_post(post_id)
#
#             await message.reply(
#                 f"✅ <b>ТЕКСТ ОБНОВЛЕН!</b>\n\n"
#                 f"<i>ID: {post_id}</i>\n"
#                 "------------------------\n"
#                 f"{new_text}",
#                 parse_mode=ParseMode.HTML,
#                 reply_markup=builder.as_markup()
#             )
