from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from modules.database import connect_db

# --- Кнопки ---
main_menu_keyboard = [
            [types.KeyboardButton(text="💎 Администрирование")],
            [types.KeyboardButton(text="⚙️ Настройки")],
]

admin_kb = [
            [types.KeyboardButton(text="📤 Просмотр очереди"),
             types.KeyboardButton(text="🕓 Запланированные")],
            [types.KeyboardButton(text="👑 Главное меню")]
]

settings_menu_kb = [
            [types.InlineKeyboardButton(text="📋 Список каналов", callback_data="settings:list")],
            [types.InlineKeyboardButton(text="📥 Канал куда выкладывать", callback_data="settings:channel")]
]

channel_kb = [
    [types.InlineKeyboardButton(text="✏️ Изменить", callback_data="settings:channel_edit")],
    [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="settings:back")]
]

back_button = [
    [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="settings:back")]
]


# --- Функции для меню ---
def build_reply_menu(keyboard):
    """Клавиатура для кнопок под полем ввода"""
    return types.ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )

def build_inline_menu(keyboard):
    """Клавиатура для кнопок под сообщением"""
    return types.InlineKeyboardMarkup(
        inline_keyboard=keyboard,
        resize_keyboard=True
    )

def build_variable_list():
    """Функция для списка каналов"""
    channels = []
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM Channels')
    channels_dict = cursor.fetchall()
    conn.close()
    for channel in channels_dict:
        channels.append(channel[1])
    keyboard = [
        [types.InlineKeyboardButton(
            text=f"📡 {ch}",
            callback_data=f"settings:channel_actions?{ch}"
        )]
        for ch in channels
    ]
    keyboard.append(
        [
         types.InlineKeyboardButton(text="⬅️ Назад", callback_data="settings:back"),
         types.InlineKeyboardButton(text="➕ Добавить", callback_data="settings:channel_add")
        ]
    )

    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)

def build_channel_actions(name_channel):
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
                [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="settings:list")],
                [types.InlineKeyboardButton(text="❌ Удалить", callback_data=f"settings:channel_delete?{name_channel}")]
        ],
        resize_keyboard=True
    )


def build_actions_menu(post_id):
    actions_builder = InlineKeyboardBuilder()
    actions_builder.row(
        types.InlineKeyboardButton(text='Показать пост')
    )

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