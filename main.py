# -*- coding: utf-8 -*-
import asyncio
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


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )


def resolve_public_host() -> str | None:
    """Возвращает публичный хост для регистрации вебхука или None для режима polling."""
    # Явное переопределение через переменную окружения имеет наивысший приоритет
    override = os.getenv("WEBHOOK_BASE_URL", "").strip()
    if override:
        return override.rstrip("/")

    # Replit: REPLIT_DOMAINS — список доменов через запятую
    replit = os.getenv("REPLIT_DOMAINS", "").split(",")[0].strip()
    if replit:
        return f"https://{replit}"

    # Railway: RAILWAY_PUBLIC_DOMAIN — публичный домен сервиса
    railway = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()
    if railway:
        return f"https://{railway}"

    return None


async def on_startup(bot: Bot, webhook_url: str, **_kwargs) -> None:
    logger = logging.getLogger(__name__)
    logger.info("Регистрация вебхука → %s", webhook_url)
    await bot.set_webhook(webhook_url, drop_pending_updates=True)
    logger.info("Вебхук успешно зарегистрирован")


async def on_shutdown(bot: Bot, **_kwargs) -> None:
    await bot.delete_webhook()
    logging.getLogger(__name__).info("Вебхук удалён")


def build_dispatcher(bot: Bot) -> Dispatcher:
    dp = Dispatcher()
    dp.update.middleware(LoggingMiddleware())
    dp.include_router(common.router)
    dp.include_router(echo.router)
    return dp


async def run_polling(bot: Bot, dp: Dispatcher) -> None:
    logger = logging.getLogger(__name__)
    me = await bot.get_me()
    logger.info("Режим polling — @%s (id=%s)", me.username, me.id)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


def run_webhook(bot: Bot, dp: Dispatcher, public_host: str) -> None:
    logger = logging.getLogger(__name__)
    webhook_url = f"{public_host}{WEBHOOK_PATH}"

    # На Railway используется $PORT; на Replit — порт 6000 (за Node-прокси)
    port = int(os.getenv("PORT", os.getenv("WEBHOOK_PORT", "6000")))

    dp.startup.register(partial(on_startup, bot=bot, webhook_url=webhook_url))
    dp.shutdown.register(partial(on_shutdown, bot=bot))

    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    logger.info("Запуск вебхук-сервера на 0.0.0.0:%d, путь %s", port, WEBHOOK_PATH)
    web.run_app(app, host="0.0.0.0", port=port)


def main() -> None:
    setup_logging()

    config = load_config()
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = build_dispatcher(bot)

    public_host = resolve_public_host()

    if public_host:
        run_webhook(bot, dp, public_host)
    else:
        logging.getLogger(__name__).info(
            "Публичный хост не найден — запуск в режиме polling (локальная разработка)"
        )
        asyncio.run(run_polling(bot, dp))


if __name__ == "__main__":
    main()
