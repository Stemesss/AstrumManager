# -*- coding: utf-8 -*-
"""Клавиатуры раздела «👥 Участники»."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.models.user import User, UserRole
from bot.utils.roles import ROLE_ORDER, assignable_roles

PAGE_SIZE = 10

_ICONS: dict[UserRole, str] = {
    UserRole.LEADER:     "✪",
    UserRole.CLAN_CHILD: "✦",
    UserRole.ELDER:      "✧",
    UserRole.MEMBER:     "◇",
}


def members_list_kb(users: list[User], page: int, total: int) -> InlineKeyboardMarkup:
    """Список участников с пагинацией."""
    rows: list[list[InlineKeyboardButton]] = []

    for u in users:
        icon = _ICONS.get(u.role, "◇")
        name = u.game_nick or u.first_name
        rows.append([
            InlineKeyboardButton(
                text=f"{icon} {name}",
                callback_data=f"mem:card:{u.telegram_id}",
            ),
            InlineKeyboardButton(
                text="⚙️",
                callback_data=f"mem:card:{u.telegram_id}",
            ),
        ])

    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"mem:list:{page - 1}"))
    if total_pages > 1:
        nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="mem:noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"mem:list:{page + 1}"))
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="mem:close")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def member_card_kb(user_id: int, page: int = 0) -> InlineKeyboardMarkup:
    """Кнопки карточки участника."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏷 Изменить роль", callback_data=f"mem:role:{user_id}")],
        [InlineKeyboardButton(text="📊 Статистика",    callback_data=f"mem:stats:{user_id}")],
        [InlineKeyboardButton(text="⬅️ Назад",         callback_data=f"mem:list:{page}")],
    ])


def role_select_kb(actor_role: UserRole, target_id: int) -> InlineKeyboardMarkup:
    """Список ролей, доступных для назначения актором."""
    rows: list[list[InlineKeyboardButton]] = []
    for role in assignable_roles(actor_role):
        icon = _ICONS.get(role, "◇")
        rows.append([InlineKeyboardButton(
            text=f"{icon} {role.value}",
            callback_data=f"mem:set:{target_id}:{role.value}",
        )])
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data=f"mem:card:{target_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
