# -*- coding: utf-8 -*-
"""Клавиатуры раздела «Новости»."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.models.news import NewsItem


def news_list_kb(items: list[NewsItem], is_manager: bool) -> InlineKeyboardMarkup:
    """Клавиатура списка новостей."""
    buttons: list[list[InlineKeyboardButton]] = []
    for item in items:
        prefix = "📌 " if item.pinned else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"{prefix}{item.title}",
                callback_data=f"news:view:{item.id}",
            )
        ])
    if is_manager:
        buttons.append([
            InlineKeyboardButton(text="➕ Создать новость", callback_data="news:create")
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def news_view_kb(news_id: int, pinned: bool, is_manager: bool) -> InlineKeyboardMarkup:
    """Клавиатура просмотра одной новости."""
    buttons: list[list[InlineKeyboardButton]] = []
    if is_manager:
        pin_text = "📍 Открепить" if pinned else "📌 Закрепить"
        buttons.append([
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"news:edit:{news_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"news:del_confirm:{news_id}"),
        ])
        buttons.append([
            InlineKeyboardButton(text=pin_text, callback_data=f"news:pin:{news_id}"),
        ])
    buttons.append([
        InlineKeyboardButton(text="◀️ К списку новостей", callback_data="news:list"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def news_edit_kb(news_id: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора поля для редактирования."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Заголовок", callback_data=f"news:edit_title:{news_id}"),
            InlineKeyboardButton(text="📝 Текст", callback_data=f"news:edit_content:{news_id}"),
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data=f"news:view:{news_id}"),
        ],
    ])


def news_delete_confirm_kb(news_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения удаления."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"news:delete:{news_id}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data=f"news:view:{news_id}"),
        ],
    ])
