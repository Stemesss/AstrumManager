# -*- coding: utf-8 -*-
"""Клавиатуры раздела «💡 Жалобы и предложения»."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

PAGE_SIZE = 8

_STATUS_LABELS: dict[str, str] = {
    "new":       "🆕 Новая",
    "reviewing": "🔍 Рассматривается",
    "accepted":  "✅ Принята",
    "rejected":  "❌ Отклонена",
}

_NEXT_STATUSES: dict[str, list[str]] = {
    "new":       ["reviewing", "accepted", "rejected"],
    "reviewing": ["accepted", "rejected"],
    "accepted":  ["rejected"],
    "rejected":  ["accepted"],
}


def status_label(status: str) -> str:
    return _STATUS_LABELS.get(status, status)


def complaints_main_kb() -> InlineKeyboardMarkup:
    """Кнопки главного экрана раздела жалоб."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Создать обращение", callback_data="cmp:create")],
        [InlineKeyboardButton(text="📋 Мои обращения", callback_data="cmp:mine:0")],
    ])


def complaints_manager_kb() -> InlineKeyboardMarkup:
    """Кнопки для менеджера: создать + список всех."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Создать обращение", callback_data="cmp:create")],
        [InlineKeyboardButton(text="📋 Все обращения",    callback_data="cmp:list:0")],
        [InlineKeyboardButton(text="📋 Мои обращения",    callback_data="cmp:mine:0")],
    ])


def complaints_list_kb(
    complaints: list,
    page: int,
    total: int,
    mode: str = "list",
) -> InlineKeyboardMarkup:
    """Пагинированный список обращений. mode='list'|'mine'."""
    rows: list[list[InlineKeyboardButton]] = []

    for c in complaints:
        s_icon = _STATUS_LABELS.get(c["status"], "")[:2]
        title  = c["title"][:40]
        rows.append([
            InlineKeyboardButton(
                text=f"{s_icon} {title}",
                callback_data=f"cmp:view:{c['id']}",
            )
        ])

    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"cmp:{mode}:{page - 1}"))
    if total_pages > 1:
        nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="cmp:noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"cmp:{mode}:{page + 1}"))
    if nav:
        rows.append(nav)

    back_cb = "cmp:list:0" if mode == "list" else "cmp:mine:0"
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def complaint_view_kb(
    complaint_id: int,
    status: str,
    is_manager: bool,
    back_mode: str = "mine",
) -> InlineKeyboardMarkup:
    """Кнопки просмотра одного обращения."""
    rows: list[list[InlineKeyboardButton]] = []
    if is_manager:
        next_st = _NEXT_STATUSES.get(status, [])
        for s in next_st:
            rows.append([
                InlineKeyboardButton(
                    text=f"→ {status_label(s)}",
                    callback_data=f"cmp:status:{complaint_id}:{s}",
                )
            ])
        rows.append([
            InlineKeyboardButton(
                text="💬 Ответить",
                callback_data=f"cmp:reply:{complaint_id}",
            )
        ])
        rows.append([
            InlineKeyboardButton(
                text="🗑 Удалить",
                callback_data=f"cmp:delconf:{complaint_id}",
            )
        ])
    back_mode_cb = "list" if back_mode == "list" else "mine"
    rows.append([
        InlineKeyboardButton(
            text="◀️ К списку",
            callback_data=f"cmp:{back_mode_cb}:0",
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def complaint_delete_confirm_kb(complaint_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Удалить", callback_data=f"cmp:del:{complaint_id}"),
            InlineKeyboardButton(text="❌ Отмена",  callback_data=f"cmp:view:{complaint_id}"),
        ]
    ])
