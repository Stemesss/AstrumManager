# -*- coding: utf-8 -*-
import asyncio
import logging
import sys
from functools import partial

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from bot.config import Config, load_config
from bot.database.db import Database
from bot.handlers import admin, audit, cancel, common, complaints, content, debug, echo, group, group_nick, icons, members, menu, news, nick, publish, rules, setrole, stats, statistics, topics
from bot.middlewares.logging import LoggingMiddleware
from bot.middlewares.nick_gate import NickGateMiddleware
from bot.observability import HealthService, MetricsRegistry, ObservabilityServer, register_observability_routes
from bot.services.audit_service import AuditService
from bot.services.member_policy import MemberPolicy
from bot.services.membership_service import MembershipService
from bot.services.news_service import NewsService
from bot.services.nickname_service import NicknameService
from bot.services.role_service import RoleService
from bot.services.stats_service import StatsService
from bot.services.topic_service import TopicService
from bot.services.user_service import UserService

def setup_logging(level_name: str = "INFO") -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )


async def _check_topics_on_startup(dp: Dispatcher) -> None:
    """Быстрая проверка тем при старте (без API). Логирует предупреждения."""
    logger = logging.getLogger(__name__)
    topic_service = dp["topic_service"]
    missing = await topic_service.check_topics_startup()
    if missing:
        from bot.models.topic import TOPIC_LABELS
        names = ", ".join(TOPIC_LABELS.get(k, k) for k in missing)
        logger.warning(
            "Не настроены %d обязательных тем: %s — "
            "используйте ⚙️ Настройки → 🧵 Настройка веток → 🔄 Синхронизировать",
            len(missing), names,
        )
    else:
        logger.info("Проверка тем: все обязательные темы настроены")


async def on_startup(
    bot: Bot, db: Database, dp: Dispatcher, webhook_url: str, **_kwargs
) -> None:
    import datetime
    logger = logging.getLogger(__name__)
    dp["bot_start_time"] = datetime.datetime.now(datetime.timezone.utc)
    metrics: MetricsRegistry | None = dp["metrics"]
    if metrics:
        metrics.mark_startup("webhook")
    await db.connect()
    await dp["topic_service"].seed_default_topics()
    await _check_topics_on_startup(dp)
    me = await bot.get_me()
    dp["bot_username"] = me.username or ""
    allowed = dp.resolve_used_update_types()
    logger.info("Регистрация вебхука → %s  (allowed_updates=%s)", webhook_url, allowed)
    await bot.set_webhook(webhook_url, allowed_updates=allowed, drop_pending_updates=True)
    logger.info("Вебхук успешно зарегистрирован")


async def on_shutdown(bot: Bot, db: Database, **_kwargs) -> None:
    await bot.delete_webhook()
    metrics: MetricsRegistry | None = _kwargs.get("metrics")
    if metrics:
        metrics.mark_shutdown()
    await db.close()
    logging.getLogger(__name__).info("Вебхук удалён")


async def on_startup_polling(
    bot: Bot, db: Database, dp: Dispatcher, observability_server: ObservabilityServer | None = None
) -> None:
    import datetime
    dp["bot_start_time"] = datetime.datetime.now(datetime.timezone.utc)
    metrics: MetricsRegistry | None = dp["metrics"]
    if metrics:
        metrics.mark_startup("polling")
    await db.connect()
    await dp["topic_service"].seed_default_topics()
    await _check_topics_on_startup(dp)
    me = await bot.get_me()
    dp["bot_username"] = me.username or ""
    if observability_server:
        await observability_server.start()
    logging.getLogger(__name__).info(
        "Режим polling — @%s (id=%s)", me.username, me.id
    )


async def on_shutdown_polling(
    db: Database,
    observability_server: ObservabilityServer | None = None,
    metrics: MetricsRegistry | None = None,
) -> None:
    if observability_server:
        await observability_server.stop()
    if metrics:
        metrics.mark_shutdown()
    await db.close()


def build_dispatcher(
    db: Database,
    config: Config | None = None,
    owner_id: int | None = None,
    group_chat_id: int = -1004463841801,
    metrics: MetricsRegistry | None = None,
) -> Dispatcher:
    """Создаёт диспетчер с разделением приватных и групповых роутеров."""
    dp = Dispatcher()

    # ── Внедрение зависимостей ────────────────────────────────────────────
    audit_service = AuditService(db)
    stats_service = StatsService(db)
    policy_service = MemberPolicy(db, owner_id=owner_id)
    role_service = RoleService(db, audit_service, policy_service)
    nickname_service = NicknameService(db, audit_service, policy_service)
    membership_service = MembershipService(db, stats_service, policy_service)
    user_service  = UserService(
        db,
        owner_id=owner_id,
        stats_service=stats_service,
        audit_service=audit_service,
        policy=policy_service,
        role_service=role_service,
        nickname_service=nickname_service,
        membership_service=membership_service,
    )
    news_service  = NewsService(db)
    topic_service = TopicService(db, chat_id=group_chat_id or -1004463841801)
    dp["user_service"]  = user_service
    dp["news_service"]  = news_service
    dp["audit_service"] = audit_service
    dp["stats_service"] = stats_service
    dp["member_policy"] = policy_service
    dp["role_service"] = role_service
    dp["nickname_service"] = nickname_service
    dp["membership_service"] = membership_service
    dp["topic_service"]  = topic_service
    dp["group_chat_id"]  = group_chat_id or -1004463841801
    dp["db"]             = db
    dp["owner_id"]       = owner_id
    dp["config"]         = config
    dp["feature_flags"]  = config.features if config else None
    dp["metrics"]        = metrics
    # bot_username устанавливается в on_startup / on_startup_polling

    # ── Промежуточный слой (глобальный) ──────────────────────────────────
    dp.update.middleware(LoggingMiddleware(metrics=metrics))

    # ── Временный отладочный роутер (все типы чатов) — удалить после проверки веток
    dp.include_router(debug.router)

    # ── Групповой роутер (группы / супергруппы) ───────────────────────────
    dp.include_router(group.router)
    dp.include_router(group_nick.router)

    # ── Приватный роутер (только личные сообщения) ────────────────────────
    private = Router()
    private.message.filter(F.chat.type == "private")
    private.callback_query.filter(F.message.chat.type == "private")

    # NickGateMiddleware — перед обработчиками, после фильтрации приватных чатов
    # Блокирует сообщения от пользователей без установленного ника (кроме команд и NickSetup)
    private.message.middleware(NickGateMiddleware())

    # Порядок важен: cancel — первым, перехватывает «❌ Отмена» в любом FSM-состоянии
    private.include_router(cancel.router)
    private.include_router(common.router)
    private.include_router(setrole.router)
    private.include_router(nick.router)    # FSM ника — до menu/news
    private.include_router(audit.router)   # до menu — чтобы перехватить AuditSearch
    private.include_router(news.router)
    private.include_router(publish.router)  # мастер публикаций — после news, до admin
    private.include_router(topics.router)  # до admin — перекрывает admin:settings WIP-заглушку
    private.include_router(icons.router)   # управление иконками форумных тем
    private.include_router(members.router) # до admin — перехватывает admin:members и admin:roles
    private.include_router(content.router)     # события, гайды, скриншоты, мемы
    private.include_router(complaints.router)  # жалобы и предложения
    private.include_router(rules.router)       # правила клана
    private.include_router(admin.router)
    private.include_router(stats.router)
    private.include_router(statistics.router)
    private.include_router(menu.router)
    private.include_router(echo.router)

    dp.include_router(private)

    return dp


def _build_health_service(dp: Dispatcher, db: Database, metrics: MetricsRegistry) -> HealthService:
    return HealthService(
        db=db,
        metrics=metrics,
        started_at_provider=lambda: dp.workflow_data.get("bot_start_time"),
    )


def run_webhook(bot: Bot, dp: Dispatcher, db: Database, config: Config) -> None:
    logger = logging.getLogger(__name__)
    webhook_url = f"{config.runtime.public_host}{config.runtime.webhook_path}"

    dp.startup.register(
        partial(on_startup, bot=bot, db=db, dp=dp, webhook_url=webhook_url)
    )
    dp.shutdown.register(partial(on_shutdown, bot=bot, db=db, metrics=dp["metrics"]))

    app = web.Application()
    metrics: MetricsRegistry | None = dp["metrics"]
    if config.features.observability and metrics:
        paths = register_observability_routes(
            app=app,
            features=config.features,
            observability=config.observability,
            health_service=_build_health_service(dp, db, metrics),
            metrics=metrics,
        )
        if paths:
            logger.info("Observability endpoints включены: %s", ", ".join(paths))
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=config.runtime.webhook_path)
    setup_application(app, dp, bot=bot)

    logger.info(
        "Запуск вебхук-сервера на 0.0.0.0:%d, путь %s",
        config.runtime.port,
        config.runtime.webhook_path,
    )
    web.run_app(app, host="0.0.0.0", port=config.runtime.port)


async def run_polling(
    bot: Bot,
    dp: Dispatcher,
    db: Database,
    observability_server: ObservabilityServer | None = None,
) -> None:
    dp.startup.register(
        partial(
            on_startup_polling,
            bot=bot,
            db=db,
            dp=dp,
            observability_server=observability_server,
        )
    )
    dp.shutdown.register(
        partial(
            on_shutdown_polling,
            db=db,
            observability_server=observability_server,
            metrics=dp["metrics"],
        )
    )
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


def main() -> None:
    config = load_config()
    setup_logging(config.runtime.log_level)
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    db = Database(config.db_path)
    metrics = MetricsRegistry()
    dp = build_dispatcher(
        db,
        config=config,
        owner_id=config.owner_id,
        group_chat_id=config.group_chat_id,
        metrics=metrics,
    )
    observability_server = ObservabilityServer(
        features=config.features,
        observability=config.observability,
        health_service=_build_health_service(dp, db, metrics),
        metrics=metrics,
    )

    if config.runtime.public_host:
        run_webhook(bot, dp, db, config)
    else:
        logging.getLogger(__name__).info(
            "Публичный хост не найден — запуск в режиме polling (локальная разработка)"
        )
        asyncio.run(run_polling(bot, dp, db, observability_server=observability_server))


if __name__ == "__main__":
    main()
