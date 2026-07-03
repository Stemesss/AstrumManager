# -*- coding: utf-8 -*-
"""Клавиатуры для раздела «📋 Журнал действий»."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.models.user import UserRole


def audit_menu_kb(role: UserRole) -> InlineKeyboardMarkup:
    """
    Главное меню журнала.
    Кнопка «Очистить» показывается всем административным ролям.
    """
    rows = [
        [InlineKeyboardButton(text="🕘 Последние действия", callback_data="alog:cat:recent:0")],
        [InlineKeyboardButton(text="👥 Участники",          callback_data="alog:cat:members:0")],
        [
            InlineKeyboardButton(text="📰 Новости",    callback_data="alog:cat:news:0"),
            InlineKeyboardButton(text="📅 События",    callback_data="alog:cat:events:0"),
        ],
        [
            InlineKeyboardButton(text="📚 Гайды",      callback_data="alog:cat:guides:0"),
            InlineKeyboardButton(text="📸 Скриншоты",  callback_data="alog:cat:screenshots:0"),
        ],
        [
            InlineKeyboardButton(text="🔍 Поиск",      callback_data="alog:search"),
            InlineKeyboardButton(text="📖 Все записи", callback_data="alog:cat:all:0"),
        ],
    ]
    if role in UserRole.admin_roles():
        rows.append([
            InlineKeyboardButton(text="🗑 Очистить журнал", callback_data="alog:clear"),
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def audit_page_kb(category: str, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Кнопки пагинации + возврат в меню."""
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text="⬅️ Назад", callback_data=f"alog:cat:{category}:{page - 1}"
        ))
    nav.append(InlineKeyboardButton(
        text=f"Стр {page + 1}/{total_pages}", callback_data="alog:noop"
    ))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(
            text="➡️ Далее", callback_data=f"alog:cat:{category}:{page + 1}"
        ))
    rows: list[list[InlineKeyboardButton]] = []
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="🔙 В меню", callback_data="alog:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def audit_search_result_kb() -> InlineKeyboardMarkup:
    """Кнопка возврата в меню после результатов поиска."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔙 В меню", callback_data="alog:menu"),
    ]])


def audit_clear_confirm_kb() -> InlineKeyboardMarkup:
    """Подтверждение очистки журнала."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Да, очистить", callback_data="alog:clear_yes"),
        InlineKeyboardButton(text="❌ Отмена",       callback_data="alog:menu"),
    ]])
