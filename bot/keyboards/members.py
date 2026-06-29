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


class MemberBtn:
    """Callback-данные кнопок раздела участников."""
    MENU         = "mem:menu"
    NOOP         = "mem:noop"
    CLOSE        = "mem:close"

    DEL_SEARCH   = "mem:del_search"
    SEASON       = "mem:season"
    SEASON_OK    = "mem:season_ok"

    @staticmethod
    def list(page: int) -> str:
        return f"mem:list:{page}"

    @staticmethod
    def card(uid: int) -> str:
        return f"mem:card:{uid}"

    @staticmethod
    def role(uid: int) -> str:
        return f"mem:role:{uid}"

    @staticmethod
    def stats(uid: int) -> str:
        return f"mem:stats:{uid}"

    @staticmethod
    def del_list(page: int) -> str:
        return f"mem:del_list:{page}"

    @staticmethod
    def del_card(uid: int) -> str:
        return f"mem:del_card:{uid}"

    @staticmethod
    def del_ok(uid: int) -> str:
        return f"mem:del_ok:{uid}"


def members_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню раздела «Участники»."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Просмотреть участников", callback_data=MemberBtn.list(0))],
        [InlineKeyboardButton(text="🗑️ Удалить участника",      callback_data=MemberBtn.del_list(0))],
        [InlineKeyboardButton(text="🧹 Новый сезон",             callback_data=MemberBtn.SEASON)],
        [InlineKeyboardButton(text="❌ Закрыть",                 callback_data=MemberBtn.CLOSE)],
    ])


def members_list_kb(users: list[User], page: int, total: int) -> InlineKeyboardMarkup:
    """Список участников с пагинацией (режим просмотра)."""
    rows: list[list[InlineKeyboardButton]] = []

    for u in users:
        icon = _ICONS.get(u.role, "◇")
        name = u.game_nick or u.first_name
        rows.append([
            InlineKeyboardButton(
                text=f"{icon} {name}",
                callback_data=MemberBtn.card(u.telegram_id),
            ),
            InlineKeyboardButton(
                text="⚙️",
                callback_data=MemberBtn.card(u.telegram_id),
            ),
        ])

    rows.extend(_pagination_rows(page, total, prefix="mem:list"))
    rows.append([InlineKeyboardButton(text="⬅️ Меню участников", callback_data=MemberBtn.MENU)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def delete_list_kb(users: list[User], page: int, total: int) -> InlineKeyboardMarkup:
    """Список участников с пагинацией (режим удаления)."""
    rows: list[list[InlineKeyboardButton]] = []

    for u in users:
        icon = _ICONS.get(u.role, "◇")
        name = u.game_nick or u.first_name
        rows.append([InlineKeyboardButton(
            text=f"🗑️ {icon} {name}",
            callback_data=MemberBtn.del_card(u.telegram_id),
        )])

    rows.extend(_pagination_rows(page, total, prefix="mem:del_list"))
    rows.append([InlineKeyboardButton(text="🔍 Поиск по нику / ID", callback_data=MemberBtn.DEL_SEARCH)])
    rows.append([InlineKeyboardButton(text="⬅️ Меню участников",    callback_data=MemberBtn.MENU)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def delete_card_kb(uid: int, name: str, page: int = 0) -> InlineKeyboardMarkup:
    """Карточка участника в режиме удаления — подтверждение."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"✅ Удалить «{name}»",
            callback_data=MemberBtn.del_ok(uid),
        )],
        [InlineKeyboardButton(text="⬅️ Назад к списку", callback_data=MemberBtn.del_list(page))],
    ])


def delete_search_result_kb(users: list[User]) -> InlineKeyboardMarkup:
    """Результаты поиска для удаления."""
    rows: list[list[InlineKeyboardButton]] = []
    for u in users:
        icon = _ICONS.get(u.role, "◇")
        name = u.game_nick or u.first_name
        rows.append([InlineKeyboardButton(
            text=f"🗑️ {icon} {name}",
            callback_data=MemberBtn.del_card(u.telegram_id),
        )])
    rows.append([InlineKeyboardButton(text="⬅️ К списку участников", callback_data=MemberBtn.del_list(0))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def season_confirm_kb() -> InlineKeyboardMarkup:
    """Подтверждение запуска нового сезона."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, начать новый сезон", callback_data=MemberBtn.SEASON_OK)],
        [InlineKeyboardButton(text="❌ Отмена",                 callback_data=MemberBtn.MENU)],
    ])


def member_card_kb(user_id: int, page: int = 0) -> InlineKeyboardMarkup:
    """Кнопки карточки участника."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏷 Изменить роль", callback_data=MemberBtn.role(user_id))],
        [InlineKeyboardButton(text="📊 Статистика",    callback_data=MemberBtn.stats(user_id))],
        [InlineKeyboardButton(text="⬅️ Назад",         callback_data=MemberBtn.list(page))],
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
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data=MemberBtn.card(target_id))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _pagination_rows(
    page: int, total: int, prefix: str
) -> list[list[InlineKeyboardButton]]:
    """Строки навигации: ◀️ | N/M | ▶️."""
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"{prefix}:{page - 1}"))
    if total_pages > 1:
        nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data=MemberBtn.NOOP))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"{prefix}:{page + 1}"))
    return [nav] if nav else []
