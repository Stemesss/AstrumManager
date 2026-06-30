# -*- coding: utf-8 -*-
"""Сервис бизнес-операций для игровых ников."""
from aiogram.types import User as TgUser

from bot.database.db import Database
from bot.database.repositories.user_repository import UserRepository
from bot.models.audit import AuditAction
from bot.models.user import UserRole
from bot.services.audit_service import AuditService
from bot.services.member_policy import MemberPolicy
from bot.utils.nick_format import build_full_nick, validate_name
from bot.utils.sync_title import sync_admin_title


class NicknameService:
    """Единый use-case смены и удаления игровых ников."""

    def __init__(
        self,
        db: Database,
        audit_service: AuditService,
        policy: MemberPolicy,
    ) -> None:
        self._users = UserRepository(db)
        self._audit = audit_service
        self._policy = policy

    async def _ensure_user(self, telegram_user: TgUser | None, telegram_id: int) -> None:
        if await self._users.get_by_telegram_id(telegram_id):
            return
        if telegram_user is None:
            return
        await self._users.upsert(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name or "Пользователь",
        )

    async def change_nickname(
        self,
        *,
        actor_id: int,
        target_id: int,
        raw_nick: str,
        bot,
        group_chat_id: int,
        telegram_user: TgUser | None = None,
        audit_description: str | None = None,
    ) -> dict:
        if not await self._policy.can_change_nickname(actor_id, target_id):
            return {
                "ok": False,
                "error": "⛔ Назначать ник другим участникам могут только администраторы.",
            }

        name, error = validate_name(raw_nick)
        if error:
            return {"ok": False, "error": error}

        await self._ensure_user(telegram_user, target_id)
        target_row = await self._users.get_by_telegram_id(target_id)
        if target_row is None:
            return {"ok": False, "error": "Участник не найден."}

        conflict = await self._users.get_by_nickname(name, exclude_telegram_id=target_id)
        if conflict is not None:
            return {
                "ok": False,
                "error": (
                    f"❌ Ник «{name}» уже занят другим участником клана.\n"
                    "Выберите другой ник."
                ),
            }

        old_name = target_row["game_nick"] or None
        role = UserRole.from_str(target_row["role"])
        await self._users.set_game_nick(target_id, name)

        actor_row = await self._users.get_by_telegram_id(actor_id)
        actor_role = await self._policy.get_role(actor_id)
        actor_nick = actor_row["game_nick"] if actor_row and actor_row["game_nick"] else str(actor_id)

        new_full = build_full_nick(name, role)
        old_full = build_full_nick(old_name, role) if old_name else "?"
        description = audit_description or (
            f"{old_full} изменил имя → {new_full}"
            if actor_id == target_id
            else f"Администратор назначил ник: {old_full} → {new_full}"
        )
        await self._audit.log(
            user_id=actor_id,
            game_nick=actor_nick,
            role=actor_role,
            action_type=AuditAction.MEMBER_NICK_CHANGE,
            description=description,
        )

        tg_error = await sync_admin_title(
            bot, group_chat_id, target_id, role, game_nick=name
        )
        return {
            "ok": True,
            "error": None,
            "nick": name,
            "old_nick": old_name,
            "role": role,
            "full_nick": new_full,
            "tg_error": tg_error,
        }

    async def clear_nickname(
        self,
        *,
        actor_id: int,
        target_id: int,
        bot,
        group_chat_id: int,
    ) -> dict:
        if not await self._policy.can_change_nickname(actor_id, target_id):
            return {"ok": False, "error": "⛔ Удалять ники могут только администраторы."}

        target_row = await self._users.get_by_telegram_id(target_id)
        if target_row is None:
            return {"ok": False, "error": "Участник не найден."}

        old_name = target_row["game_nick"]
        if not old_name:
            return {"ok": False, "error": "⚠️ У этого участника ник не задан."}

        role = UserRole.from_str(target_row["role"])
        old_full = build_full_nick(old_name, role)
        await self._users.set_game_nick(target_id, "")

        actor_row = await self._users.get_by_telegram_id(actor_id)
        actor_role = await self._policy.get_role(actor_id)
        actor_nick = actor_row["game_nick"] if actor_row and actor_row["game_nick"] else str(actor_id)

        description = (
            f"{old_full} удалил свой игровой ник"
            if actor_id == target_id
            else f"Администратор удалил ник: {old_full}"
        )
        await self._audit.log(
            user_id=actor_id,
            game_nick=actor_nick,
            role=actor_role,
            action_type=AuditAction.MEMBER_NICK_CHANGE,
            description=description,
        )

        tg_error = await sync_admin_title(
            bot, group_chat_id, target_id, role, game_nick=None
        )
        return {
            "ok": True,
            "error": None,
            "old_nick": old_name,
            "old_full_nick": old_full,
            "role": role,
            "tg_error": tg_error,
        }
