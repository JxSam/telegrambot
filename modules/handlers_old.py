import asyncio
import re
import os
from html import escape

from telethon import TelegramClient, events
from telethon.tl.types import *

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from .services import *

import config


class ReviewStorage:
    def __init__(self):
        self.review_posts = {}
        self.waiting_for_edit = {}

class AdminHandler:

    @staticmethod
    async def send_to_review(text, media_path, bot, storage):
        post_id = hash(text + str(asyncio.get_event_loop().time()))
        storage.review_posts[post_id] = {'text': text, 'media_path': media_path}

        kb = InlineKeyboardBuilder()
        kb.row(
            types.InlineKeyboardButton(text="✨ Уникализация (AI)", callback_data=f"ai_unique_{post_id}"),
            types.InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_{post_id}")
        )
        kb.row(
            types.InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"publish_{post_id}"),
            types.InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_{post_id}")
        )

        await bot.send_message(config.ADMIN_ID, text, reply_markup=kb.as_markup())

class ParserHandler:
    def __init__(self, client, bot, storage):
        self.client = client
        self.bot = bot
        self.storage = storage

        @client.on(events.NewMessage(chats=config.SOURCE_CHANNELS))
        async def handler(event):
            await self.handle_new_post(event)

    async def handle_new_post(self, event):
        if not event.message.text and not event.message.media:
            return

        text = TextService.get_html_text(event.message) + config.SIGNATURE
        media_path = None

        if event.message.media:
            MediaService.ensure_dir()
            media_path = await event.message.download_media(file=MediaService.DOWNLOAD_DIR)

        if config.MODE == "AUTO":
            await self.bot.send_message(config.DESTINATION_CHANNEL, text)
            if media_path:
                await MediaService.delete_temp_media(media_path)
        else:
            await AdminHandler.send_to_review(text, media_path, self.bot, self.storage)