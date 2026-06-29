# -*- coding: utf-8 -*-
"""Клавиатуры раздела «🎨 Иконки тем»."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.models.topic import ALL_TOPIC_NAMES, TOPIC_LABELS, ForumTopic


class TopicIconBtn:
    """Callback-данные кнопок раздела иконок."""
    PANEL        = "icons:panel"
    SYNC         = "icons:sync"
    BACK         = "icons:back"
    PREFIX_EDIT  = "icons:edit:"
    PREFIX_SET   = "icons:set:"

    @staticmethod
    def edit(topic_key: str) -> str:
        return f"icons:edit:{topic_key}"

    @staticmethod
    def set_icon(topic_key: str, emoji_id: str) -> str:
        # Максимум: "icons:set:" (10) + "announcements" (13) + ":" (1) + emoji_id (≤19) = 43 < 64
        return f"icons:set:{topic_key}:{emoji_id}"


def icons_panel_kb(topics: list[ForumTopic]) -> InlineKeyboardMarkup:
    """Клавиатура панели иконок: одна строка на тему + Авто-синхронизировать + Назад."""
    configured = {t.topic_name: t for t in topics}
    rows = []
    for name in ALL_TOPIC_NAMES:
        topic    = configured.get(name)
        label    = TOPIC_LABELS[name]
        has_icon = bool(topic and topic.icon_custom_emoji_id)
        badge    = "✅" if has_icon else "❌"
        rows.append([
            InlineKeyboardButton(
                text=f"{badge} {label}",
                callback_data=TopicIconBtn.edit(name),
            )
        ])
    rows.append([
        InlineKeyboardButton(text="🔄 Авто-синхронизировать", callback_data=TopicIconBtn.SYNC),
    ])
    rows.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data=TopicIconBtn.BACK),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def sticker_picker_kb(topic_key: str, stickers: list) -> InlineKeyboardMarkup:
    """
    Показывает все доступные стикеры-иконки в виде кнопок с эмодзи (5 в ряд).
    Администратор выбирает подходящую иконку для темы.
    """
    ROW_SIZE = 5
    buttons = []
    for sticker in stickers:
        if not sticker.custom_emoji_id:
            continue
        buttons.append(
            InlineKeyboardButton(
                text=sticker.emoji or "?",
                callback_data=TopicIconBtn.set_icon(topic_key, sticker.custom_emoji_id),
            )
        )
    rows = [buttons[i : i + ROW_SIZE] for i in range(0, len(buttons), ROW_SIZE)]
    rows.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data=TopicIconBtn.BACK),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
