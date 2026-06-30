# -*- coding: utf-8 -*-
import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from bot.observability.metrics import MetricsRegistry

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Промежуточный слой для логирования входящих обновлений от пользователей."""

    def __init__(self, metrics: MetricsRegistry | None = None) -> None:
        super().__init__()
        self._metrics = metrics

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Update):
            user = None
            if event.message and event.message.from_user:
                user = event.message.from_user
            elif event.callback_query and event.callback_query.from_user:
                user = event.callback_query.from_user

            if user:
                logger.info(
                    "Обновление от пользователя %s (@%s): %s",
                    user.id,
                    user.username or "нет_username",
                    event.event_type,
                )
            if self._metrics:
                try:
                    self._metrics.record_update(event.event_type)
                except Exception:
                    self._metrics.record_error()
                    logger.exception("Не удалось записать in-memory метрику обновления")

        return await handler(event, data)
