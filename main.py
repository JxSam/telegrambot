import asyncio
from modules.handlers import *
import config


parser_client = TelegramClient(
    config.SESSION_NAME,
    config.API_ID,
    config.API_HASH
)

# Инициализация бота
bot = Bot(
    token=config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()
storage = ReviewStorage()
ParserHandler(parser_client, bot, storage)


async def run():
    MediaService.ensure_dir()
    await parser_client.start(password=config.TELEGRAM_PASSWORD)
    await asyncio.gather(
        parser_client.run_until_disconnected(),
        dp.start_polling(bot)
    )


if __name__ == '__main__':
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("Бот остановлен.")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
