# -*- coding: utf-8 -*-
"""Утилиты для работы с ролями пользователей."""
from bot.models.user import UserRole

# Иконки в порядке иерархии: Лидер → Старейшина → Дитя клана → Участник
_ROLE_ICONS: dict[UserRole, str] = {
    UserRole.LEADER: "✪",
    UserRole.ELDER: "✧",
    UserRole.CLAN_CHILD: "✦",
    UserRole.MEMBER: "◇",
}

# Иконки для Telegram Admin Title (отображаются в профиле и в группе)
ROLE_DISPLAY_ICONS: dict[UserRole, str] = {
    UserRole.LEADER:     "✪",
    UserRole.ELDER:      "✧",
    UserRole.CLAN_CHILD: "✦",
    UserRole.MEMBER:     "◇",
}

# Порядок ролей по убыванию старшинства
ROLE_ORDER: list[UserRole] = [
    UserRole.LEADER,
    UserRole.ELDER,
    UserRole.CLAN_CHILD,
    UserRole.MEMBER,
]


# Матрица прав: кто какие роли может назначать
# Ключ — роль того, кто назначает; значение — множество ролей, которые он может назначить.
ROLE_CAN_ASSIGN: dict[UserRole, frozenset[UserRole]] = {
    UserRole.LEADER:     frozenset({UserRole.LEADER, UserRole.ELDER, UserRole.CLAN_CHILD, UserRole.MEMBER}),
    UserRole.ELDER:      frozenset({UserRole.LEADER, UserRole.ELDER, UserRole.CLAN_CHILD, UserRole.MEMBER}),
    UserRole.CLAN_CHILD: frozenset({UserRole.LEADER, UserRole.ELDER, UserRole.CLAN_CHILD, UserRole.MEMBER}),
    UserRole.MEMBER:     frozenset(),
}


def can_assign(actor_role: UserRole, target_role: UserRole) -> bool:
    """Возвращает True, если actor_role имеет право назначить target_role."""
    return target_role in ROLE_CAN_ASSIGN.get(actor_role, frozenset())


def assignable_roles(actor_role: UserRole) -> list[UserRole]:
    """Список ролей, которые actor_role может назначать (в порядке иерархии)."""
    allowed = ROLE_CAN_ASSIGN.get(actor_role, frozenset())
    return [r for r in ROLE_ORDER if r in allowed]


def role_label(role: UserRole) -> str:
    """Возвращает иконку и название роли для отображения пользователю."""
    icon = _ROLE_ICONS.get(role, "❓")
    return f"{icon} {role.value}"


def role_display(role: UserRole) -> str:
    """Возвращает Telegram-стиль иконку + название роли (для профиля и титула)."""
    icon = ROLE_DISPLAY_ICONS.get(role, "◇")
    return f"{icon} {role.value}"
