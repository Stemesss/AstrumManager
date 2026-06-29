# -*- coding: utf-8 -*-
"""Сервис журнала действий (Audit Log)."""
import logging
import math

from bot.database.db import Database
from bot.models.audit import CATEGORY_ACTIONS
from bot.models.user import UserRole

logger = logging.getLogger(__name__)

PAGE_SIZE = 10


class AuditService:
    """Единый сервис для записи и чтения журнала аудита."""

    def __init__(self, db: Database) -> None:
        self._db = db

    # ── Запись ────────────────────────────────────────────────────────────

    async def log(
        self,
        user_id: int,
        game_nick: str,
        role: UserRole,
        action_type: str,
        description: str,
    ) -> None:
        """
        Добавляет запись в журнал.
        Ошибки логируются, но не пробрасываются — не должны ломать основной поток.
        """
        try:
            await self._db.add_audit_log(
                user_id, game_nick, role.value, action_type, description
            )
            logger.debug("Audit [%s] %s: %s", action_type, game_nick, description)
        except Exception as exc:  # noqa: BLE001
            logger.error("Ошибка записи в журнал аудита: %s", exc)

    # ── Чтение ────────────────────────────────────────────────────────────

    async def get_page(
        self, page: int, category: str = "recent"
    ) -> tuple[list, int, int]:
        """Возвращает (записи, всего_записей, всего_страниц)."""
        action_types = CATEGORY_ACTIONS.get(category)
        rows = await self._db.get_audit_page(page, PAGE_SIZE, action_types)
        total = await self._db.count_audit(action_types)
        total_pages = max(1, math.ceil(total / PAGE_SIZE))
        return rows, total, total_pages

    async def search(self, query: str) -> list:
        """Поиск по нику, типу действия или дате (дд.мм.гггг)."""
        return await self._db.search_audit(query, per_page=20)

    async def clear(self) -> int:
        """Очищает журнал, возвращает количество удалённых записей."""
        return await self._db.clear_audit_log()
