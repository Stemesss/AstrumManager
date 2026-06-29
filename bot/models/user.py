# -*- coding: utf-8 -*-
"""Модель пользователя и перечисление ролей."""
from dataclasses import dataclass
from enum import Enum


class UserRole(str, Enum):
    """Роли участников клана Astrum."""
    LEADER = "Лидер"
    ELDER = "Старейшина"
    CLAN_CHILD = "Дитя клана"
    MEMBER = "Участник"

    @classmethod
    def admin_roles(cls) -> set["UserRole"]:
        """Роли с доступом к административному разделу."""
        return {cls.LEADER, cls.ELDER}

    @classmethod
    def from_str(cls, value: str) -> "UserRole":
        """Преобразует строку в роль, возвращая MEMBER при неизвестном значении."""
        for role in cls:
            if role.value == value:
                return role
        return cls.MEMBER


@dataclass
class User:
    """Пользователь бота."""
    telegram_id: int
    username: str | None
    first_name: str
    role: UserRole = UserRole.MEMBER
    game_nick: str | None = None
