# -*- coding: utf-8 -*-
"""Клавиатуры раздела «🧵 Настройка веток»."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.models.topic import ALL_TOPIC_NAMES, TOPIC_LABELS, ForumTopic


class TopicBtn:
    """Callback-данные кнопок настройки веток."""
    PREFIX = "topic:"
    BACK   = "topics:back"
    CANCEL = "topics:cancel"
    SYNC   = "topics:sync"

    @staticmethod
    def select(name: str) -> str:
        return f"topic:{name}"


def topics_menu_kb(topics: list[ForumTopic]) -> InlineKeyboardMarkup:
    """Меню со всеми ветками и их статусом."""
    configured = {t.topic_name: t for t in topics}
    rows = []
    for name in ALL_TOPIC_NAMES:
        topic  = configured.get(name)
        label  = TOPIC_LABELS[name]
        status = f" [{topic.status}]" if topic else " [не настроено]"
        rows.append([
            InlineKeyboardButton(
                text=f"{label}{status}",
                callback_data=TopicBtn.select(name),
            )
        ])
    rows.append([
        InlineKeyboardButton(text="🔄 Синхронизировать", callback_data=TopicBtn.SYNC),
        InlineKeyboardButton(text="🎨 Иконки тем",       callback_data="icons:panel"),
    ])
    rows.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data=TopicBtn.BACK),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


TOPICS_CANCEL_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data=TopicBtn.CANCEL)]
    ]
)
