from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

channels = [

]
# --- Кнопки ---
main_menu_keyboard = [
            [types.KeyboardButton(text="📬 Показать посты")],
            [types.KeyboardButton(text="⚙️ Настройки")]
]

settings_menu_kb = [
            [types.InlineKeyboardButton(text="📋 Список каналов", callback_data="settings:list")],
            [types.InlineKeyboardButton(text="📥 Канал куда выкладывать", callback_data="settings:add")]
]

channel_kb = [
    [types.InlineKeyboardButton(text="✏️ Изменить", callback_data="settings:list")],
    [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="settings:back")]
]

def build_reply_menu(keyboard):
    """Клавиатура для кнопок под полем ввода"""
    return types.ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )

# --- Функции для меню ---
def build_inline_menu(keyboard):
    """Клавиатура для кнопок под сообщением"""
    return types.InlineKeyboardMarkup(
        inline_keyboard=keyboard,
        resize_keyboard=True
    )


def build_variable_list(channels: list[str]):
    keyboard = [
        [types.InlineKeyboardButton(text=f"📡 {ch}", callback_data=f"settings:channel{ch}")]
        for ch in channels
    ]
    keyboard.append(
        [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="settings:back")]
    )

    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)

# def build_actions_menu(post_id):
#     actions_builder = InlineKeyboardBuilder()
#     actions_builder.row(
#         types.InlineKeyboardButton(text='Показать пост')
#     )
#
# def build_buttons_post(post_id):
#     """Клавиатура для действий с постом"""
#     builder = ReplyKeyboardBuilder()
#     builder.row(
#         types.KeyboardButton(text="✨ Уникализация (AI)", callback_data=f"ai_unique_{post_id}"),
#         types.KeyboardButton(text="✏️ Редактировать", callback_data=f"edit_{post_id}")
#     )
#     builder.row(
#         types.KeyboardButton(text="✅ Опубликовать", callback_data=f"publish_{post_id}"),
#         types.KeyboardButton(text="🗑️ Удалить", callback_data=f"delete_{post_id}")
#     )
#     return builder