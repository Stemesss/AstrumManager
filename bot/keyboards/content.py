# -*- coding: utf-8 -*-
"""Клавиатуры разделов «📅 События», «📚 Гайды», «📸 Скриншоты»."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.models.news import NewsItem

PAGE_SIZE = 10

# Иконки и подписи для каждого типа контента
_TYPE_ICON: dict[str, str] = {
    "events":      "📅",
    "guides":      "📚",
    "screenshots": "📸",
}

_TYPE_LABEL: dict[str, str] = {
    "events":      "События",
    "guides":      "Гайды",
    "screenshots": "Скриншоты",
}

_TYPE_CREATE: dict[str, str] = {
    "events":      "➕ Создать событие",
    "guides":      "➕ Создать гайд",
    "screenshots": "➕ Добавить скриншот",
}


def content_list_kb(
    items: list[NewsItem],
    page: int,
    total: int,
    content_type: str,
    is_manager: bool,
) -> InlineKeyboardMarkup:
    """Пагинированный список записей."""
    rows: list[list[InlineKeyboardButton]] = []

    for item in items:
        prefix = "📌 " if item.pinned else ""
        rows.append([
            InlineKeyboardButton(
                text=f"{prefix}{item.title}",
                callback_data=f"cnt:view:{content_type}:{item.id}",
            )
        ])

    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"cnt:list:{content_type}:{page - 1}"))
    if total_pages > 1:
        nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="cnt:noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"cnt:list:{content_type}:{page + 1}"))
    if nav:
        rows.append(nav)

    if is_manager:
        rows.append([
            InlineKeyboardButton(
                text=_TYPE_CREATE.get(content_type, "➕ Создать"),
                callback_data=f"cnt:create:{content_type}",
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def content_view_kb(
    content_type: str,
    item_id: int,
    pinned: bool,
    is_manager: bool,
    page: int = 0,
) -> InlineKeyboardMarkup:
    """Кнопки просмотра записи."""
    rows: list[list[InlineKeyboardButton]] = []
    if is_manager:
        pin_text = "📍 Открепить" if pinned else "📌 Закрепить"
        rows.append([
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"cnt:edit:{content_type}:{item_id}"),
            InlineKeyboardButton(text="🗑 Удалить",       callback_data=f"cnt:dconf:{content_type}:{item_id}"),
        ])
        rows.append([
            InlineKeyboardButton(text=pin_text, callback_data=f"cnt:pin:{content_type}:{item_id}"),
        ])
    icon = _TYPE_ICON.get(content_type, "📄")
    label = _TYPE_LABEL.get(content_type, "Записи")
    rows.append([
        InlineKeyboardButton(
            text=f"◀️ К списку: {icon} {label}",
            callback_data=f"cnt:list:{content_type}:{page}",
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def content_edit_kb(content_type: str, item_id: int) -> InlineKeyboardMarkup:
    """Выбор поля для редактирования."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Заголовок", callback_data=f"cnt:etitle:{content_type}:{item_id}"),
            InlineKeyboardButton(text="📝 Текст",     callback_data=f"cnt:econt:{content_type}:{item_id}"),
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data=f"cnt:view:{content_type}:{item_id}"),
        ],
    ])


def content_delete_confirm_kb(content_type: str, item_id: int) -> InlineKeyboardMarkup:
    """Подтверждение удаления."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"cnt:del:{content_type}:{item_id}"),
            InlineKeyboardButton(text="❌ Отмена",      callback_data=f"cnt:view:{content_type}:{item_id}"),
        ],
    ])
