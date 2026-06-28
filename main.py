import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import load_config
from bot.handlers import common, echo
from bot.middlewares.logging import LoggingMiddleware


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )


async def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)

    config = load_config()

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()

    dp.update.middleware(LoggingMiddleware())

    dp.include_router(common.router)
    dp.include_router(echo.router)

    me = await bot.get_me()
    logger.info("Starting bot @%s (id=%s)", me.username, me.id)

    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
