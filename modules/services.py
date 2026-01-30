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

import httpx
import config
from utils import strip_signature


class MediaService:
    DOWNLOAD_DIR = 'downloads'

    @classmethod
    def ensure_dir(cls):
        os.makedirs(cls.DOWNLOAD_DIR, exist_ok=True)

    @staticmethod
    async def delete_temp_media(file_path: str):
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"🗑️ Временный медиафайл удален: {file_path}")
            except Exception as e:
                print(f"❌ Ошибка при удалении файла {file_path}: {e}")


class TextService:
    @staticmethod
    def escape_html_entities(text: str) -> str:
        return escape(text)

    @staticmethod
    def get_html_text(message) -> str:
        text = message.text
        if not text:
            return ""

        entities = message.entities or []
        entities.sort(key=lambda x: x.offset)

        output = ""
        last_offset = 0

        for entity in entities:
            output += escape(text[last_offset:entity.offset])
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
                output += escape(entity_text)

            last_offset = entity.offset + entity.length

        output += escape(text[last_offset:])
        return output.replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')

    @staticmethod
    def convert_markdown_to_html(markdown_text: str) -> str:
        html_text = markdown_text
        html_text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', html_text)
        html_text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', html_text)
        html_text = re.sub(r'_(.+?)_', r'<i>\1</i>', html_text)
        html_text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', html_text)
        html_text = re.sub(r'~(.+?)~', r'<s>\1</s>', html_text)
        html_text = re.sub(r'`(.+?)`', r'<code>\1</code>', html_text)
        html_text = re.sub(r'```(?:\w+)?\n?(.+?)```', r'<pre>\1</pre>', html_text, flags=re.DOTALL)
        return html_text.replace('*', '').replace('_', '').replace('~', '').replace('`', '')

class AIService:

    @staticmethod
    async def ai_unique_text(text: str) -> str:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        prompt = config.AI_PROMPT.format(text=text)
        data = {
            "model": config.OPENROUTER_MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "text"}
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(url, headers=headers, json=data)
                response.raise_for_status()
                result = response.json()
                return TextService.convert_markdown_to_html(
                    result['choices'][0]['message']['content'].strip()
                )
            except Exception as e:
                return f"<b>❌ Ошибка уникализации</b>\n\n{text}"