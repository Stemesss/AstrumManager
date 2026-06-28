import logging
import os
import sys
from functools import partial

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from bot.config import load_config
from bot.handlers import common, echo
from bot.middlewares.logging import LoggingMiddleware

WEBHOOK_PATH = "/api/telegram/webhook"
WEBAPP_HOST = "0.0.0.0"


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )


async def on_startup(bot: Bot, base_url: str, **kwargs) -> None:
    webhook_url = f"https://{base_url}{WEBHOOK_PATH}"
    logger = logging.getLogger(__name__)
    logger.info("Setting webhook to %s", webhook_url)
    await bot.set_webhook(webhook_url, drop_pending_updates=True)
    logger.info("Webhook set successfully")


async def on_shutdown(bot: Bot, **kwargs) -> None:
    await bot.delete_webhook()
    logging.getLogger(__name__).info("Webhook deleted")


def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)

    config = load_config()

    replit_domains = os.getenv("REPLIT_DOMAINS", "")
    base_url = replit_domains.split(",")[0].strip()
    if not base_url:
        logger.error("REPLIT_DOMAINS is not set — cannot determine webhook URL")
        sys.exit(1)

    port = int(os.getenv("WEBHOOK_PORT", "6000"))

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()
    dp.update.middleware(LoggingMiddleware())
    dp.include_router(common.router)
    dp.include_router(echo.router)

    dp.startup.register(partial(on_startup, bot=bot, base_url=base_url))
    dp.shutdown.register(partial(on_shutdown, bot=bot))

    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    logger.info("Starting webhook server on port %d", port)
    web.run_app(app, host=WEBAPP_HOST, port=port)


if __name__ == "__main__":
    main()
