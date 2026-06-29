# -*- coding: utf-8 -*-
"""Сервис управления пользователями."""
from aiogram.types import User as TgUser

from bot.database.db import Database
from bot.models.audit import AuditAction
from bot.models.user import User, UserRole


class UserService:
    """Бизнес-логика для работы с пользователями."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def _row_to_user(self, tg_user: TgUser, row) -> User:
        """Конвертирует строку БД + TgUser в модель User."""
        return User(
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name or "Пользователь",
            role=UserRole.from_str(row["role"]) if row else UserRole.MEMBER,
            game_nick=row["game_nick"] if row else None,
        )

    async def get_or_create(self, tg_user: TgUser) -> User:
        """Регистрирует пользователя при первом обращении, возвращает модель User."""
        await self._db.upsert_user(
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name or "Пользователь",
        )
        row = await self._db.get_user(tg_user.id)
        return self._row_to_user(tg_user, row)

    async def register_if_new(self, tg_user: TgUser) -> tuple["User", bool]:
        """
        Проверяет наличие пользователя в БД.
        Если новый — создаёт профиль и возвращает (User, True).
        Если существующий — обновляет last_seen и возвращает (User, False).
        """
        existing = await self._db.get_user(tg_user.id)
        is_new = existing is None
        await self._db.upsert_user(
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name or "Пользователь",
        )
        row = await self._db.get_user(tg_user.id)
        return self._row_to_user(tg_user, row), is_new

    async def log_registration(self, user: "User") -> None:
        """Записывает в журнал действий: «Пользователь вступил в клан»."""
        await self._db.add_audit_log(
            user_id=user.telegram_id,
            game_nick=user.first_name,
            role=user.role.value,
            action_type=AuditAction.MEMBER_REGISTER,
            description="👤 Пользователь вступил в клан",
        )

    async def get_role(self, telegram_id: int) -> UserRole:
        """Возвращает роль пользователя по telegram_id."""
        role_str = await self._db.get_role(telegram_id)
        return UserRole.from_str(role_str)

    async def is_admin(self, telegram_id: int) -> bool:
        """True если пользователь имеет административную роль (Лидер, Дитя клана или Старейшина)."""
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
