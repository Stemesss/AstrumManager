# -*- coding: utf-8 -*-
"""Фоновый планировщик отложенной отправки рассылок."""
import asyncio
import logging

from aiogram import Bot

from bot.services.audit_service import AuditService
from bot.services.broadcast_service import BroadcastService
from bot.services.user_service import UserService

logger = logging.getLogger(__name__)

_CHECK_INTERVAL_SECONDS = 30


async def run_scheduler(
    bot: Bot,
    broadcast_service: BroadcastService,
    user_service: UserService,
    audit_service: AuditService,
) -> None:
    """
    Бесконечный цикл: раз в _CHECK_INTERVAL_SECONDS проверяет запланированные
    рассылки и отправляет те, чьё время (UTC) уже наступило.

    Останавливается через asyncio.CancelledError при остановке бота.
    """
    logger.info("Планировщик рассылок запущен (интервал проверки: %sс)", _CHECK_INTERVAL_SECONDS)
    try:
        while True:
            try:
                await broadcast_service.run_due(bot, user_service, audit_service)
            except Exception:
                logger.exception("Ошибка в цикле планировщика рассылок")
            await asyncio.sleep(_CHECK_INTERVAL_SECONDS)
    except asyncio.CancelledError:
        logger.info("Планировщик рассылок остановлен")
        raise
