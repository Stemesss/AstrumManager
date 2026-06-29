# -*- coding: utf-8 -*-
"""Утилиты для работы с ролями пользователей."""
from bot.models.user import UserRole

# Иконки в порядке иерархии: Лидер → Дитя клана → Старейшина → Участник
_ROLE_ICONS: dict[UserRole, str] = {
    UserRole.LEADER: "👑",
    UserRole.CLAN_CHILD: "🌟",
    UserRole.ELDER: "🛡️",
    UserRole.MEMBER: "👤",
}

# Порядок ролей по убыванию старшинства
ROLE_ORDER: list[UserRole] = [
    UserRole.LEADER,
    UserRole.CLAN_CHILD,
    UserRole.ELDER,
    UserRole.MEMBER,
]


def role_label(role: UserRole) -> str:
    """Возвращает иконку и название роли для отображения пользователю."""
    icon = _ROLE_ICONS.get(role, "❓")
    return f"{icon} {role.value}"
