# -*- coding: utf-8 -*-
"""Утилиты для работы с ролями пользователей."""
from bot.models.user import UserRole

_ROLE_ICONS: dict[UserRole, str] = {
    UserRole.LEADER: "👑",
    UserRole.ELDER: "🌟",
    UserRole.CLAN_CHILD: "🌱",
    UserRole.MEMBER: "⚔️",
}


def role_label(role: UserRole) -> str:
    """Возвращает иконку и название роли для отображения пользователю."""
    icon = _ROLE_ICONS.get(role, "❓")
    return f"{icon} {role.value}"
