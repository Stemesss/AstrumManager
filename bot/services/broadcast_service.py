# -*- coding: utf-8 -*-
"""Сервис рассылок администрации."""
import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter

from bot.database.db import Database

logger = logging.getLogger(__name__)


class BroadcastService:
    """Бизнес-логика создания, хранения и отправки рассылок."""

    def __init__(self, db: Database) -> None:
        self._db = db

    async def create(self, author_id: int, author_name: str, text: str, audience: str) -> int:
        """Создаёт черновик рассылки, возвращает её ID."""
        return await self._db.create_broadcast(author_id, author_name, text, audience)

    async def get(self, broadcast_id: int):
        """Возвращает рассылку по ID или None."""
        return await self._db.get_broadcast(broadcast_id)

    async def list_recent(self, limit: int = 20):
        """Возвращает последние рассылки, от новых к старым."""
        return await self._db.list_broadcasts(limit)

    async def send(
        self, bot: Bot, broadcast_id: int, text: str, chat_ids: list[int]
    ) -> dict:
        """
        Рассылает текст по списку chat_id.
        Возвращает {'total', 'sent', 'failed'} и сохраняет результат в БД.
        """
        sent = 0
        failed = 0
        for chat_id in chat_ids:
            try:
                await bot.send_message(chat_id, text)
                sent += 1
            except TelegramRetryAfter as exc:
                await asyncio.sleep(exc.retry_after)
                try:
                    await bot.send_message(chat_id, text)
                    sent += 1
                except Exception:
                    failed += 1
            except (TelegramForbiddenError, TelegramBadRequest):
                failed += 1
            except Exception:
                logger.exception(
                    "Ошибка отправки рассылки #%s пользователю %s", broadcast_id, chat_id
                )
                failed += 1
            await asyncio.sleep(0.05)

        result = {"total": len(chat_ids), "sent": sent, "failed": failed}
        await self._db.update_broadcast_result(
            broadcast_id,
            total=result["total"],
            sent_count=result["sent"],
            failed_count=result["failed"],
            status="sent",
        )
        return result
