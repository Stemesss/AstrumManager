# -*- coding: utf-8 -*-
"""Сервис управления пользователями."""
from aiogram.types import User as TgUser

from bot.database.db import Database
from bot.models.user import User, UserRole


class UserService:
    """Бизнес-логика для работы с пользователями."""

    def __init__(self, db: Database) -> None:
        self._db = db

    async def get_or_create(self, tg_user: TgUser) -> User:
        """Регистрирует пользователя при первом обращении, возвращает модель User."""
        await self._db.upsert_user(
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name or "Пользователь",
        )
        row = await self._db.get_user(tg_user.id)
        return User(
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name or "Пользователь",
            role=UserRole.from_str(row["role"]) if row else UserRole.MEMBER,
            game_nick=row["game_nick"] if row else None,
        )

    async def get_role(self, telegram_id: int) -> UserRole:
        """Возвращает роль пользователя по telegram_id."""
        role_str = await self._db.get_role(telegram_id)
        return UserRole.from_str(role_str)

    async def is_admin(self, telegram_id: int) -> bool:
        """True если пользователь — Лидер или Старейшина."""
        role = await self.get_role(telegram_id)
        return role in UserRole.admin_roles()

    async def set_role(self, telegram_id: int, role: UserRole) -> None:
        """Устанавливает роль пользователя."""
        await self._db.set_role(telegram_id, role.value)

    async def has_nick(self, telegram_id: int) -> bool:
        """True если пользователь уже установил игровой ник."""
        row = await self._db.get_user(telegram_id)
        return bool(row and row["game_nick"])

    async def set_game_nick(self, telegram_id: int, nick: str) -> None:
        """Устанавливает или обновляет игровой ник пользователя."""
        await self._db.set_game_nick(telegram_id, nick)

    async def get_game_nick(self, telegram_id: int) -> str | None:
        """Возвращает игровой ник или None."""
        row = await self._db.get_user(telegram_id)
        return row["game_nick"] if row else None

    async def get_profile_stats(self, telegram_id: int) -> dict:
        """Возвращает статистику профиля: дней в клане, гайдов, скриншотов."""
        days = await self._db.get_days_in_clan(telegram_id)
        return {
            "days_in_clan": days,
            "guides_count": 0,       # будет заполнено после реализации раздела гайдов
            "screenshots_count": 0,  # будет заполнено после реализации раздела скриншотов
        }

    async def get_all_users(self) -> list[User]:
        """Возвращает список всех зарегистрированных пользователей."""
        rows = await self._db.get_all_users()
        return [
            User(
                telegram_id=row["telegram_id"],
                username=row["username"],
                first_name=row["first_name"],
                role=UserRole.from_str(row["role"]),
                game_nick=row["game_nick"],
            )
            for row in rows
        ]
