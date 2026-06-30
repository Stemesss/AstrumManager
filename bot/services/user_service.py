# -*- coding: utf-8 -*-
"""Фасад совместимости для работы с пользователями."""
from aiogram.types import User as TgUser

from bot.database.db import Database
from bot.database.repositories.user_repository import UserRepository
from bot.models.audit import AuditAction
from bot.models.user import User, UserRole
from bot.services.audit_service import AuditService
from bot.services.member_policy import MemberPolicy
from bot.services.membership_service import MembershipService
from bot.services.nickname_service import NicknameService
from bot.services.role_service import RoleService
from bot.services.stats_service import StatsService


class UserService:
    """Бизнес-логика и совместимый фасад для legacy handlers."""

    def __init__(
        self,
        db: Database,
        *,
        owner_id: int | None = None,
        stats_service: StatsService | None = None,
        audit_service: AuditService | None = None,
        policy: MemberPolicy | None = None,
        role_service: RoleService | None = None,
        nickname_service: NicknameService | None = None,
        membership_service: MembershipService | None = None,
    ) -> None:
        self._db = db
        self._users = UserRepository(db)
        self._stats_service = stats_service or StatsService(db)
        self._audit_service = audit_service or AuditService(db)
        self._policy = policy or MemberPolicy(db, owner_id=owner_id)
        self._role_service = role_service or RoleService(
            db, self._audit_service, self._policy
        )
        self._nickname_service = nickname_service or NicknameService(
            db, self._audit_service, self._policy
        )
        self._membership_service = membership_service or MembershipService(
            db, self._stats_service, self._policy
        )

    @staticmethod
    def _row_to_user(tg_user: TgUser, row) -> User:
        return User(
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name or "Пользователь",
            role=UserRole.from_str(row["role"]) if row else UserRole.MEMBER,
            game_nick=row["game_nick"] if row else None,
        )

    @staticmethod
    def _db_row_to_user(row) -> User:
        return User(
            telegram_id=row["telegram_id"],
            username=row["username"],
            first_name=row["first_name"],
            role=UserRole.from_str(row["role"]),
            game_nick=row["game_nick"],
        )

    async def get_or_create(self, tg_user: TgUser) -> User:
        await self._users.upsert(
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name or "Пользователь",
        )
        row = await self._users.get_by_telegram_id(tg_user.id)
        return self._row_to_user(tg_user, row)

    async def register_if_new(self, tg_user: TgUser) -> tuple["User", bool]:
        existing = await self._users.get_by_telegram_id(tg_user.id)
        is_new = existing is None
        await self._users.upsert(
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name or "Пользователь",
        )
        row = await self._users.get_by_telegram_id(tg_user.id)
        return self._row_to_user(tg_user, row), is_new

    async def log_registration(self, user: "User") -> None:
        await self._db.add_audit_log(
            user_id=user.telegram_id,
            game_nick=user.first_name,
            role=user.role.value,
            action_type=AuditAction.MEMBER_REGISTER,
            description="👤 Пользователь вступил в клан",
        )

    async def get_role(self, telegram_id: int) -> UserRole:
        return await self._policy.get_role(telegram_id)

    async def get_effective_role(self, telegram_id: int) -> UserRole:
        return await self._policy.get_effective_role(telegram_id)

    async def is_admin(self, telegram_id: int) -> bool:
        return await self._policy.can_view_admin_sections(telegram_id)

    async def set_role(self, telegram_id: int, role: UserRole) -> None:
        await self._role_service.set_role(telegram_id, role)

    async def assign_role(
        self,
        *,
        actor_id: int,
        target_id: int,
        new_role: UserRole,
        bot,
        group_chat_id: int,
    ) -> dict:
        return await self._role_service.assign_role(
            actor_id=actor_id,
            target_id=target_id,
            new_role=new_role,
            bot=bot,
            group_chat_id=group_chat_id,
        )

    async def has_nick(self, telegram_id: int) -> bool:
        row = await self._users.get_by_telegram_id(telegram_id)
        return bool(row and row["game_nick"])

    async def set_game_nick(self, telegram_id: int, nick: str) -> None:
        await self._users.set_game_nick(telegram_id, nick)

    async def change_nickname(self, **kwargs) -> dict:
        return await self._nickname_service.change_nickname(**kwargs)

    async def clear_nickname(self, **kwargs) -> dict:
        return await self._nickname_service.clear_nickname(**kwargs)

    async def get_game_nick(self, telegram_id: int) -> str | None:
        row = await self._users.get_by_telegram_id(telegram_id)
        return row["game_nick"] if row else None

    async def is_nick_taken(self, nick: str, exclude_id: int | None = None) -> bool:
        row = await self._users.get_by_nickname(nick, exclude_telegram_id=exclude_id)
        return row is not None

    async def list_nicks(self) -> list[tuple[int, str, "UserRole"]]:
        users = await self.get_all_users()
        items = [
            (u.telegram_id, u.game_nick, u.role)
            for u in users
            if u.game_nick
        ]
        items.sort(key=lambda x: x[1].casefold())
        return items

    async def get_profile_stats(self, telegram_id: int) -> dict:
        return await self._membership_service.get_profile_stats(telegram_id)

    async def get_days_in_clan(self, telegram_id: int) -> int:
        return await self._users.get_days_in_clan(telegram_id)

    async def get_user_by_id(self, user_id: int) -> User | None:
        return await self._membership_service.get_user_by_id(user_id)

    async def get_user_by_telegram_id(self, telegram_id: int) -> User | None:
        return await self._membership_service.get_user_by_telegram_id(telegram_id)

    async def get_user_by_username(self, username: str) -> User | None:
        return await self._membership_service.get_user_by_username(username)

    async def get_user_by_nickname(self, nickname: str) -> User | None:
        return await self._membership_service.get_user_by_nickname(nickname)

    async def search_users(self, query: str, limit: int = 50) -> list[User]:
        return await self._membership_service.search_users(query, limit=limit)

    async def get_all_users(self) -> list[User]:
        rows = await self._users.list_all()
        return [self._db_row_to_user(row) for row in rows]

    async def delete_member(self, actor_id: int, target_id: int) -> dict:
        return await self._membership_service.delete_member(actor_id, target_id)

    async def new_season(self) -> dict:
        return await self._membership_service.new_season()
