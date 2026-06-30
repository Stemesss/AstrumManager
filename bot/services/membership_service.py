# -*- coding: utf-8 -*-
"""Сервис профиля, поиска и удаления участников."""
from bot.database.db import Database
from bot.database.repositories.user_repository import UserRepository
from bot.models.user import User, UserRole
from bot.services.member_policy import MemberPolicy
from bot.services.stats_service import StatsService


class MembershipService:
    """Операции профиля, поиска, удаления и сезонного сброса."""

    def __init__(
        self,
        db: Database,
        stats_service: StatsService,
        policy: MemberPolicy,
    ) -> None:
        self._db = db
        self._users = UserRepository(db)
        self._stats = stats_service
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

    async def get_profile_stats(self, telegram_id: int) -> dict:
        days = await self._users.get_days_in_clan(telegram_id)
        activity = await self._stats.user_activity(telegram_id)
        return {
            "days_in_clan": days,
            "score": activity["score"],
            "news_count": activity["news"],
            "guides_count": activity["guides"],
            "screenshots_count": activity["screenshots"],
            "events_count": activity["events"],
        }

    async def get_user_by_id(self, user_id: int) -> User | None:
        return self._row_to_user(await self._users.get_by_id(user_id))

    async def get_user_by_telegram_id(self, telegram_id: int) -> User | None:
        return self._row_to_user(await self._users.get_by_telegram_id(telegram_id))

    async def get_user_by_username(self, username: str) -> User | None:
        return self._row_to_user(await self._users.get_by_username(username))

    async def get_user_by_nickname(self, nickname: str) -> User | None:
        return self._row_to_user(await self._users.get_by_nickname(nickname))

    async def search_users(self, query: str, limit: int = 50) -> list[User]:
        rows = await self._users.search_users(query, limit=limit)
        return [user for row in rows if (user := self._row_to_user(row)) is not None]

    async def delete_member(self, actor_id: int, target_id: int) -> dict:
        error = await self._policy.validate_member_deletion(actor_id, target_id)
        if error:
            return {"ok": False, "error": error}

        target = await self._users.get_by_telegram_id(target_id)
        target_name = (
            target["game_nick"] or target["first_name"] if target else str(target_id)
        )
        await self._users.delete(target_id)
        return {"ok": True, "error": None, "target_name": target_name}

    async def new_season(self) -> dict:
        backup_path = await self._db.create_backup()
        users_count, logs_deleted = await self._db.season_reset()
        return {
            "backup_path": backup_path,
            "users_count": users_count,
            "logs_deleted": logs_deleted,
        }
