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

    # ── Шаблоны ───────────────────────────────────────────────────────────

    async def save_template(self, author_id: int, author_name: str, name: str, text: str) -> int:
        """Сохраняет текст рассылки как шаблон, возвращает его ID."""
        return await self._db.create_broadcast_template(author_id, author_name, name, text)

    async def list_templates(self):
        """Возвращает все сохранённые шаблоны."""
        return await self._db.list_broadcast_templates()

    async def get_template(self, template_id: int):
        """Возвращает шаблон по ID или None."""
        return await self._db.get_broadcast_template(template_id)

    async def delete_template(self, template_id: int) -> None:
        """Удаляет шаблон по ID."""
        await self._db.delete_broadcast_template(template_id)

    # ── Планировщик ───────────────────────────────────────────────────────

    async def schedule(self, broadcast_id: int, scheduled_at: str) -> None:
        """Помечает рассылку как запланированную на указанное время (UTC)."""
        await self._db.schedule_broadcast(broadcast_id, scheduled_at)

    async def list_scheduled(self):
        """Возвращает все ещё не отправленные запланированные рассылки."""
        return await self._db.list_scheduled_broadcasts()

    async def cancel_scheduled(self, broadcast_id: int) -> bool:
        """Отменяет запланированную рассылку. True, если запись была найдена."""
        return await self._db.cancel_scheduled_broadcast(broadcast_id)

    async def get_due(self):
        """Возвращает запланированные рассылки, время которых уже наступило."""
        return await self._db.get_due_scheduled_broadcasts()

    async def run_due(self, bot: Bot, user_service, audit_service) -> None:
        """
        Отправляет все запланированные рассылки, время которых наступило.

        Вызывается периодически фоновым планировщиком (см. broadcast_scheduler.py).
        """
        from bot.models.audit import AuditAction
        from bot.utils.roles import role_label

        due = await self.get_due()
        for row in due:
            broadcast_id = row["id"]
            text = row["text"]
            author_id = row["author_id"]
            author_name = row["author_name"]
            audience = row["audience"]

            if audience == "self":
                chat_ids = [author_id]
            else:
                users = await user_service.get_all_users()
                chat_ids = [u.telegram_id for u in users]

            try:
                result = await self.send(bot, broadcast_id, text, chat_ids)
            except Exception:
                logger.exception("Ошибка при отправке запланированной рассылки #%s", broadcast_id)
                continue

            actor_nick = await user_service.get_game_nick(author_id) or author_name
            actor_role = await user_service.get_role(author_id)
            await audit_service.log(
                user_id=author_id,
                game_nick=actor_nick,
                role=actor_role,
                action_type=AuditAction.BROADCAST_SEND,
                description=(
                    f"{role_label(actor_role)} {actor_nick}: запланированная рассылка #{broadcast_id} "
                    f"отправлена (доставлено {result['sent']} из {result['total']})"
                ),
            )

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
