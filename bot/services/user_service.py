# -*- coding: utf-8 -*-
"""Сервис управления пользователями."""
from aiogram.types import User as TgUser

from bot.database.db import Database
from bot.database.repositories.user_repository import UserRepository
from bot.models.audit import AuditAction
from bot.models.user import User, UserRole


class UserService:
    """Бизнес-логика для работы с пользователями."""

    def __init__(self, db: Database) -> None:
        self._db = db
        self._users = UserRepository(db)

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
        row = await self._users.get_by_telegram_id(tg_user.id)
        return self._row_to_user(tg_user, row)

    async def register_if_new(self, tg_user: TgUser) -> tuple["User", bool]:
        """
        Проверяет наличие пользователя в БД.
        Если новый — создаёт профиль и возвращает (User, True).
        Если существующий — обновляет last_seen и возвращает (User, False).
        """
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
        role_str = await self._users.get_role(telegram_id)
        return UserRole.from_str(role_str)

    async def is_admin(self, telegram_id: int) -> bool:
        """True если пользователь имеет административную роль (Лидер, Старейшина или Дитя клана)."""
        role = await self.get_role(telegram_id)
        return role in UserRole.admin_roles()

    async def set_role(self, telegram_id: int, role: UserRole) -> None:
        """Устанавливает роль пользователя."""
        await self._users.set_role(telegram_id, role.value)

    async def has_nick(self, telegram_id: int) -> bool:
        """True если пользователь уже установил игровой ник."""
        row = await self._users.get_by_telegram_id(telegram_id)
        return bool(row and row["game_nick"])

    async def set_game_nick(self, telegram_id: int, nick: str) -> None:
        """Устанавливает или обновляет игровой ник пользователя."""
        await self._users.set_game_nick(telegram_id, nick)

    async def get_game_nick(self, telegram_id: int) -> str | None:
        """Возвращает игровой ник или None."""
        row = await self._users.get_by_telegram_id(telegram_id)
        return row["game_nick"] if row else None

    async def is_nick_taken(self, nick: str, exclude_id: int | None = None) -> bool:
        """
        True если игровой ник уже занят другим участником (без учёта регистра).

        Как у Iris: в клане не может быть двух одинаковых ников.
        exclude_id — пользователь, которого нужно пропустить (например, сам себя
        при смене ника на тот же).
        """
        target = nick.casefold()
        for u in await self.get_all_users():
            if not u.game_nick:
                continue
            if u.game_nick.casefold() == target and u.telegram_id != exclude_id:
                return True
        return False

    async def list_nicks(self) -> list[tuple[int, str, "UserRole"]]:
        """Возвращает список (telegram_id, game_nick, role) участников с ником."""
        users = await self.get_all_users()
        items = [
            (u.telegram_id, u.game_nick, u.role)
            for u in users
            if u.game_nick
        ]
        items.sort(key=lambda x: x[1].casefold())
        return items

    async def get_profile_stats(self, telegram_id: int) -> dict:
        """Возвращает статистику профиля: дней в клане, гайдов, скриншотов."""
        days = await self._users.get_days_in_clan(telegram_id)
        return {
            "days_in_clan": days,
            "guides_count": 0,       # будет заполнено после реализации раздела гайдов
            "screenshots_count": 0,  # будет заполнено после реализации раздела скриншотов
        }

    async def get_days_in_clan(self, telegram_id: int) -> int:
        """Возвращает количество дней пользователя в клане."""
        return await self._users.get_days_in_clan(telegram_id)

    async def get_all_users(self) -> list[User]:
        """Возвращает список всех зарегистрированных пользователей."""
        rows = await self._users.list_all()
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

    async def delete_member(self, actor_id: int, target_id: int) -> dict:
        """
        Удаляет участника из базы данных.
        Возвращает {'ok': bool, 'error': str | None}.
        Запрещено удалять: суперпользователя, самого себя, Лидера.
        """
        _SUPERUSER_ID = 8490615925
        if target_id == _SUPERUSER_ID:
            return {"ok": False, "error": "Невозможно удалить суперпользователя."}
        if target_id == actor_id:
            return {"ok": False, "error": "Нельзя удалить самого себя."}
        target_role = await self.get_role(target_id)
        if target_role == UserRole.LEADER:
            return {"ok": False, "error": "Невозможно удалить владельца проекта (Лидера)."}
        await self._users.delete(target_id)
        return {"ok": True, "error": None}

    async def new_season(self) -> dict:
        """
        Создаёт резервную копию БД, затем сбрасывает сезонные данные:
        полностью очищает журнал аудита, сохраняя пользователей, роли, темы, новости.
        Возвращает dict с параметрами отчёта.
        """
        backup_path = await self._db.create_backup()
        users_count, logs_deleted = await self._db.season_reset()
        return {
            "backup_path": backup_path,
            "users_count": users_count,
            "logs_deleted": logs_deleted,
        }
