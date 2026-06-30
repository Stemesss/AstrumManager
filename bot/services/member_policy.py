# -*- coding: utf-8 -*-
"""Единый policy layer для прав участников."""
from bot.database.db import Database
from bot.database.repositories.user_repository import UserRepository
from bot.models.user import UserRole


class MemberPolicy:
    """Централизованная проверка прав и ограничений модуля участников."""

    def __init__(self, db: Database, owner_id: int | None = None) -> None:
        self._users = UserRepository(db)
        self._owner_id = owner_id

    async def get_role(self, telegram_id: int) -> UserRole:
        row = await self._users.get_by_telegram_id(telegram_id)
        return UserRole.from_str(row["role"]) if row else UserRole.MEMBER

    def is_owner(self, telegram_id: int) -> bool:
        return self._owner_id is not None and telegram_id == self._owner_id

    async def get_effective_role(self, telegram_id: int) -> UserRole:
        role = await self.get_role(telegram_id)
        return UserRole.LEADER if self.is_owner(telegram_id) else role

    async def can_view_admin_sections(self, telegram_id: int) -> bool:
        return await self.get_effective_role(telegram_id) in UserRole.admin_roles()

    async def can_use_admin_functions(self, telegram_id: int) -> bool:
        return await self.can_view_admin_sections(telegram_id)

    async def can_manage_roles(self, telegram_id: int) -> bool:
        return await self.can_use_admin_functions(telegram_id)

    async def can_change_nickname(self, actor_id: int, target_id: int) -> bool:
        return actor_id == target_id or await self.can_use_admin_functions(actor_id)

    async def can_start_new_season(self, telegram_id: int) -> bool:
        return await self.can_use_admin_functions(telegram_id)

    async def validate_member_deletion(self, actor_id: int, target_id: int) -> str | None:
        if target_id == actor_id:
            return "Нельзя удалить самого себя."
        if self.is_owner(target_id):
            return "Невозможно удалить владельца проекта."

        target = await self._users.get_by_telegram_id(target_id)
        if target is None:
            return "Участник не найден."

        target_role = UserRole.from_str(target["role"])
        if target_role == UserRole.LEADER:
            return "Невозможно удалить владельца проекта (Лидера)."
        return None

    async def validate_role_assignment(self, actor_id: int, target_role: UserRole) -> str | None:
        from bot.utils.roles import can_assign

        effective_role = await self.get_effective_role(actor_id)
        if not can_assign(effective_role, target_role):
            return "⛔ Недостаточно прав."
        return None
