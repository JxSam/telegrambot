from aiogram import types
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def build_main_menu():
    """Клавиатура для действий с постом"""
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="📬 Показать посты")],
            [types.KeyboardButton(text="⚙️ Настройки")]
        ],
        resize_keyboard=True
    )

def build_actions_menu(post_id):
    actions_builder = InlineKeyboardBuilder()
    actions_builder.row(
        types.InlineKeyboardButton(text='Показать пост')
    )

def build_buttons_post(post_id):
    """Клавиатура для действий с постом"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        types.KeyboardButton(text="✨ Уникализация (AI)", callback_data=f"ai_unique_{post_id}"),
        types.KeyboardButton(text="✏️ Редактировать", callback_data=f"edit_{post_id}")
    )
    builder.row(
        types.KeyboardButton(text="✅ Опубликовать", callback_data=f"publish_{post_id}"),
        types.KeyboardButton(text="🗑️ Удалить", callback_data=f"delete_{post_id}")
    )
    return builder