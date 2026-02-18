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

        review_message = f"<b>🔥 Новый пост на проверку!</b>\n\n" \
                     f"<i>ID: {post_id}</i>\n" \
                     "------------------------\n"
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(f"INSERT INTO Posts (post_id, text) VALUES ('{post_id}', '{text}')")
        if media_path is not None:
            cursor.execute(f"INSERT INTO post_media (post_id, file_id) VALUES ('{post_id}', '{media_path}')")
        cursor.execute("SELECT name FROM Channels")
        self.chats = [row[0] for row in cursor.fetchall()]
        conn.commit()
        conn.close()

        await self.bot.send_message(chat_id=config.ADMIN_ID, text=review_message, parse_mode=ParseMode.HTML,
                               reply_markup=builder.as_markup())

    # --- Обработчик парсинга (Telethon) ---
    async def handler_new_post(self, event):
        """Обрабатывает новое сообщение в любом из исходных каналов."""
        if not event.message.text and not event.message.media: return
        post_text = event.message.text
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

# --- Администрирование ---
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
            conn = connect_db()
            cursor = conn.cursor()

            cursor.execute("""
                                SELECT text FROM Posts
                                WHERE post_id = ?
                                ORDER BY post_id ASC
                                LIMIT 1
                            """, (self.post_id,))
            data = cursor.fetchone()
            self.text = data[0]
            conn.close()
            await callback.message.answer(
                f"<b>️️️⚡️️ Редактирование {self.post_id}. \nТекст:</b>\n"
                "------------------------\n"
                f"{self.text}",
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
                parse_mode=ParseMode.HTML,
                reply_markup=build_reply_menu(admin_kb)
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