# -*- coding: utf-8 -*-
"""Клавиатуры раздела «✅ Правила»."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def rules_view_kb(rules_id: int | None, is_manager: bool) -> InlineKeyboardMarkup | None:
    """Кнопки просмотра правил. None если менеджер — не нужна."""
    if not is_manager:
        return None
    rows: list[list[InlineKeyboardButton]] = []
    if rules_id is not None:
        rows.append([
            InlineKeyboardButton(text="✏️ Редактировать",       callback_data=f"rul:edit:{rules_id}"),
            InlineKeyboardButton(text="📌 Закрепить в теме",    callback_data=f"rul:pin:{rules_id}"),
        ])
    rows.append([
        InlineKeyboardButton(text="📤 Опубликовать новую редакцию", callback_data="rul:new"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def rules_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="rul:cancel")]
    ])
