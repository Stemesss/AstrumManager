# -*- coding: utf-8 -*-
import asyncio
import logging
import os
import sys
from functools import partial

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from bot.config import load_config
from bot.database.db import Database
from bot.handlers import admin, audit, common, content, debug, echo, group, members, menu, news, nick, publish, setrole, stats, statistics, topics
from bot.middlewares.logging import LoggingMiddleware
from bot.services.audit_service import AuditService
from bot.services.news_service import NewsService
from bot.services.stats_service import StatsService
from bot.services.topic_service import TopicService
from bot.services.user_service import UserService

WEBHOOK_PATH = "/api/telegram/webhook"


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )


def resolve_public_host() -> str | None:
    """Возвращает публичный хост для регистрации вебхука или None для режима polling."""
    override = os.getenv("WEBHOOK_BASE_URL", "").strip()
    if override:
        return override.rstrip("/")

    replit = os.getenv("REPLIT_DOMAINS", "").split(",")[0].strip()
    if replit:
        return f"https://{replit}"

    railway = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()
    if railway:
        return f"https://{railway}"

    return None


async def on_startup(
    bot: Bot, db: Database, dp: Dispatcher, webhook_url: str, **_kwargs
) -> None:
    import datetime
    logger = logging.getLogger(__name__)
    dp["bot_start_time"] = datetime.datetime.now(datetime.timezone.utc)
    await db.connect()
    await dp["topic_service"].seed_default_topics()
    me = await bot.get_me()
    dp["bot_username"] = me.username or ""
    allowed = dp.resolve_used_update_types()
    logger.info("Регистрация вебхука → %s  (allowed_updates=%s)", webhook_url, allowed)
    await bot.set_webhook(webhook_url, allowed_updates=allowed, drop_pending_updates=True)
    logger.info("Вебхук успешно зарегистрирован")


async def on_shutdown(bot: Bot, db: Database, **_kwargs) -> None:
    await bot.delete_webhook()
    await db.close()
    logging.getLogger(__name__).info("Вебхук удалён")


async def on_startup_polling(
    bot: Bot, db: Database, dp: Dispatcher, **_kwargs
) -> None:
    import datetime
    dp["bot_start_time"] = datetime.datetime.now(datetime.timezone.utc)
    await db.connect()
    await dp["topic_service"].seed_default_topics()
    me = await bot.get_me()
    dp["bot_username"] = me.username or ""
    logging.getLogger(__name__).info(
        "Режим polling — @%s (id=%s)", me.username, me.id
    )


async def on_shutdown_polling(db: Database, **_kwargs) -> None:
    await db.close()


def build_dispatcher(
    db: Database,
    owner_id: int | None = None,
    group_chat_id: int = -1004463841801,
) -> Dispatcher:
    """Создаёт диспетчер с разделением приватных и групповых роутеров."""
    dp = Dispatcher()

    # ── Внедрение зависимостей ────────────────────────────────────────────
    user_service  = UserService(db)
    news_service  = NewsService(db)
    audit_service = AuditService(db)
    stats_service = StatsService(db)
    topic_service = TopicService(db, chat_id=group_chat_id or -1004463841801)
    dp["user_service"]  = user_service
    dp["news_service"]  = news_service
    dp["audit_service"] = audit_service
    dp["stats_service"] = stats_service
    dp["topic_service"]  = topic_service
    dp["group_chat_id"]  = group_chat_id or -1004463841801
    dp["db"]             = db
    dp["owner_id"]       = owner_id
    # bot_username устанавливается в on_startup / on_startup_polling

    # ── Промежуточный слой ────────────────────────────────────────────────
    dp.update.middleware(LoggingMiddleware())

    # ── Временный отладочный роутер (все типы чатов) — удалить после проверки веток
    dp.include_router(debug.router)

    # ── Групповой роутер (группы / супергруппы) ───────────────────────────
    dp.include_router(group.router)

    # ── Приватный роутер (только личные сообщения) ────────────────────────
    private = Router()
    private.message.filter(F.chat.type == "private")
    private.callback_query.filter(F.message.chat.type == "private")

    # Порядок важен: специализированные роутеры до универсального echo
    private.include_router(common.router)
    private.include_router(setrole.router)
    private.include_router(nick.router)    # FSM ника — до menu/news
    private.include_router(audit.router)   # до menu — чтобы перехватить AuditSearch
    private.include_router(news.router)
    private.include_router(publish.router)  # мастер публикаций — после news, до admin
    private.include_router(topics.router)  # до admin — перекрывает admin:settings WIP-заглушку
    private.include_router(members.router) # до admin — перехватывает admin:members и admin:roles
    private.include_router(content.router) # события, гайды, скриншоты
    private.include_router(admin.router)
    private.include_router(stats.router)
    private.include_router(statistics.router)
    private.include_router(menu.router)
    private.include_router(echo.router)

    dp.include_router(private)

    return dp


def run_webhook(bot: Bot, dp: Dispatcher, db: Database, public_host: str) -> None:
    logger = logging.getLogger(__name__)
    webhook_url = f"{public_host}{WEBHOOK_PATH}"

    port = int(os.getenv("PORT", os.getenv("WEBHOOK_PORT", "6000")))

    dp.startup.register(
        partial(on_startup, bot=bot, db=db, dp=dp, webhook_url=webhook_url)
    )
    dp.shutdown.register(partial(on_shutdown, bot=bot, db=db))

    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    logger.info("Запуск вебхук-сервера на 0.0.0.0:%d, путь %s", port, WEBHOOK_PATH)
    web.run_app(app, host="0.0.0.0", port=port)


async def run_polling(bot: Bot, dp: Dispatcher, db: Database) -> None:
    dp.startup.register(partial(on_startup_polling, bot=bot, db=db, dp=dp))
    dp.shutdown.register(partial(on_shutdown_polling, db=db))
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


def main() -> None:
    setup_logging()

    config = load_config()
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    db = Database(config.db_path)
    dp = build_dispatcher(db, owner_id=config.owner_id, group_chat_id=config.group_chat_id)

    public_host = resolve_public_host()

    if public_host:
        run_webhook(bot, dp, db, public_host)
    else:
        logging.getLogger(__name__).info(
            "Публичный хост не найден — запуск в режиме polling (локальная разработка)"
        )
        asyncio.run(run_polling(bot, dp, db))


if __name__ == "__main__":
    main()
