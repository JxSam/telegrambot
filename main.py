import asyncio
import logging

from aiogram import Dispatcher, Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from telethon import TelegramClient, events
import config
from config import DOWNLOAD_DIR
from modules.handlers import MenuHandler, SettingsHandler, ParsHandler, AdminHandler, DeleteHandler
from modules.functions import *

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    """Основная функция запуска"""
    parser_client = TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH)
    default_properties = DefaultBotProperties(parse_mode=ParseMode.HTML)
    bot = Bot(token=config.BOT_TOKEN, default=default_properties)
    dp = Dispatcher()
    dp['review_posts'] = {}
    dp['waiting_for_edit'] = {}

    menu = MenuHandler(dp)
    menu.register()
    pars_handler = ParsHandler(bot, dp, DOWNLOAD_DIR, parser_client)
    pars_handler.load_channels()
    pars_handler.register()
    settings = SettingsHandler(dp, pars_handler)
    settings.register()
    admin = AdminHandler(dp)
    admin.register()
    #Создание и проверка наличия папки для скачивания медиа
    ensure_download_dir(DOWNLOAD_DIR)
    reply_handler = DeleteHandler()
    dp.include_router(reply_handler.router)

    await parser_client.start(password=config.TELEGRAM_PASSWORD)
    print("Telethon Client запущен.")

    await asyncio.gather(
        parser_client.run_until_disconnected(),
        dp.start_polling(bot)
    )

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")