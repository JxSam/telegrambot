from aiogram import types
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from modules.database import connect_db
from modules.functions import escape_html_entities

# --- Кнопки ---
main_menu_keyboard = [
            [types.KeyboardButton(text="💎 Администрирование")],
            [types.KeyboardButton(text="⚙️ Настройки")],
]

admin_kb = [
            [types.KeyboardButton(text="📤 Просмотр очереди")],
            [types.KeyboardButton(text="🌐 Главное меню"),
             types.KeyboardButton(text="⚙️ Настройки")]
]

settings_ai_kb = [
            [types.InlineKeyboardButton(text='API_KEY', callback_data='settings:API_KEY'),
              types.InlineKeyboardButton(text='MODEL_NAME', callback_data='settings:MODEL_NAME')],
            [types.InlineKeyboardButton(text='AI_PROMPT', callback_data='MODEL_NAME')],
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="settings:back")]
]

settings_menu_kb = [
            [types.InlineKeyboardButton(text="📋 Список каналов", callback_data="settings:list"),
             types.InlineKeyboardButton(text="🔗 Заменяющие теги", callback_data="settings:links_list")],
            [types.InlineKeyboardButton(text="📥 Канал куда выкладывать", callback_data="settings:channel"),
             types.InlineKeyboardButton(text="🧬 AI settings", callback_data="settings:ai_settings")]
]

channel_kb = [
    [types.InlineKeyboardButton(text="✏️ Изменить", callback_data="settings:channel_edit")],
    [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="settings:back")]
]

check_posts = [
    [types.InlineKeyboardButton(text="Смотреть пост", callback_data="post:round_check"),
     types.InlineKeyboardButton(text="Cмотреть все", callback_data="settings:back")],
]

next_posts = [
    [types.KeyboardButton(text="⬅️ Предыдущий"),
     types.KeyboardButton(text="➡️ Следующий")],
    [types.KeyboardButton(text="️️️⚡️ Действия"),
     types.KeyboardButton(text="❌ Удалить")],
    [types.KeyboardButton(text="🌐 Главное меню")]
]

back_button = [
    [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="settings:back")]
]

read_buttons = [
    [types.KeyboardButton(text="✨ Уникализация (AI)"),
         types.KeyboardButton(text="✏️ Изменить текст")],
    [types.KeyboardButton(text="✅ Опубликовать"),
         types.KeyboardButton(text="❌ Удалить")],
    [types.KeyboardButton(text='🌐 Главное меню')]
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

def build_links_list_kb():
    """Функция для списка каналов"""
    links = []
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM links_list')
    links_dict = cursor.fetchall()
    conn.close()
    for link in links_dict:
        link.append(link[1])
    keyboard = [
        [types.InlineKeyboardButton(
            text=f"📡 {ch}",
            callback_data=f"settings:link_actions?{ch}"
        )]
        for ch in link
    ]
    keyboard.append(
        [
         types.InlineKeyboardButton(text="⬅️ Назад", callback_data="settings:back"),
         types.InlineKeyboardButton(text="➕ Добавить", callback_data="settings:link_add")
        ]
    )

    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)

def build_variable_list(object, table):
    """Функция для списка каналов
    object - объект перебора в таблице
    table - таблица в БД
    """
    list = []
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(f'SELECT id, name FROM {table}')
    list_dict = cursor.fetchall()
    conn.close()
    for unit in list_dict:
        list.append(unit[1])
    keyboard = [
        [types.InlineKeyboardButton(
            text=f"{escape_html_entities(ch)}",
            callback_data=f"settings:{object}_actions?{ch}"
        )]
        for ch in list
    ]
    keyboard.append(
        [
         types.InlineKeyboardButton(text="⬅️ Назад", callback_data="settings:back"),
         types.InlineKeyboardButton(text="➕ Добавить", callback_data=f"settings:{object}_add")
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

def build_link_actions(name_link):
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
                [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="settings:link_list")],
                [types.InlineKeyboardButton(text="❌ Удалить", callback_data=f"settings:link_delete?{name_link}")]
        ],
        resize_keyboard=True
    )

def build_actions_menu(post_id, text):
    actions_builder = InlineKeyboardBuilder()
    actions_builder.row(
        types.InlineKeyboardButton(text='Показать пост', callback_data=f"post:check%${post_id}")
    )
    return actions_builder

def build_round_posts(post_id):
    actions_builder = InlineKeyboardBuilder()
    actions_builder.row(
        types.InlineKeyboardButton(text='Следующий пост', callback_data=f"post:check%${post_id}")
    )
    return actions_builder

def build_next_posts():
    keyboard = [
        [types.KeyboardButton(text='SQ')]
    ]
    return types.ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )