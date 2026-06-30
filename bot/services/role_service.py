# -*- coding: utf-8 -*-
"""Сервис бизнес-операций для ролей участников."""
from bot.database.db import Database
from bot.database.repositories.user_repository import UserRepository
from bot.models.audit import AuditAction
from bot.models.user import User, UserRole
from bot.services.audit_service import AuditService
from bot.services.member_policy import MemberPolicy
from bot.utils.roles import role_label
from bot.utils.sync_title import ADMIN_TITLES, build_admin_title, sync_admin_title


class RoleService:
    """Единая бизнес-операция назначения ролей."""

    def __init__(
        self,
        db: Database,
        audit_service: AuditService,
        policy: MemberPolicy,
    ) -> None:
        self._users = UserRepository(db)
        self._audit = audit_service
        self._policy = policy

    @staticmethod
    def _row_to_user(row) -> User | None:
        if row is None:
            return None
        return User(
            telegram_id=row["telegram_id"],
            username=row["username"],
            first_name=row["first_name"],
            role=UserRole.from_str(row["role"]),
            game_nick=row["game_nick"],
        )

    async def set_role(self, telegram_id: int, role: UserRole) -> None:
        await self._users.set_role(telegram_id, role.value)

    async def assign_role(
        self,
        *,
        actor_id: int,
        target_id: int,
        new_role: UserRole,
        bot,
        group_chat_id: int,
    ) -> dict:
        error = await self._policy.validate_role_assignment(actor_id, new_role)
        if error:
            return {"ok": False, "error": error}

        target_before = await self._users.get_by_telegram_id(target_id)
        if target_before is None:
            return {"ok": False, "error": "Участник не найден."}

        await self._users.set_role(target_id, new_role.value)
        target_row = await self._users.get_by_telegram_id(target_id)
        confirmed = UserRole.from_str(target_row["role"]) if target_row else new_role

        actor_role = await self._policy.get_role(actor_id)
        actor_nick = (await self._users.get_by_telegram_id(actor_id) or {}).get("game_nick") if False else None
        actor_row = await self._users.get_by_telegram_id(actor_id)
        actor_nick = actor_row["game_nick"] if actor_row and actor_row["game_nick"] else str(actor_id)
        target_game_nick = target_row["game_nick"] if target_row else None
        target_nick = target_game_nick or str(target_id)

        await self._audit.log(
            user_id=actor_id,
            game_nick=actor_nick,
            role=actor_role,
            action_type=AuditAction.MEMBER_ROLE_SET,
            description=(
                f"{role_label(actor_role)} {actor_nick} назначил роль "
                f"{role_label(confirmed)} участнику {target_nick}"
            ),
        )

        tg_error = await sync_admin_title(
            bot, group_chat_id, target_id, confirmed, game_nick=target_game_nick
        )

        tg_title = None
        if not tg_error and confirmed in ADMIN_TITLES:
            tg_title = build_admin_title(confirmed, target_game_nick)

        return {
            "ok": True,
            "error": None,
            "role": confirmed,
            "tg_error": tg_error,
            "tg_title": tg_title,
            "target_user": self._row_to_user(target_row),
            "actor_role": actor_role,
        }
