# -*- coding: utf-8 -*-
"""Модель и константы для Telegram Topics (веток форума)."""
from dataclasses import dataclass

TOPIC_LABELS: dict[str, str] = {
    "news":          "📰 Новости",
    "guides":        "📚 Гайды",
    "screenshots":   "📸 Скриншоты",
    "events":        "📅 События",
    "announcements": "📢 Объявления",
    "welcome":       "👋 Приветствие",
    "complaints":    "💡 Жалобы и предложения",
    "memes":         "😂 Мемы",
    "rules":         "✅ Правила",
}

ALL_TOPIC_NAMES: list[str] = list(TOPIC_LABELS.keys())

# Значения по умолчанию (chat_id и thread_id из конфига группы Astrum).
# Используются только при первом запуске; настройки из БД имеют приоритет.
DEFAULT_CHAT_ID: int = -1004463841801
DEFAULT_THREAD_IDS: dict[str, int] = {
    "guides":      2,
    "complaints":  5,
    "events":      6,
    "news":        32,
    "screenshots": 34,
    "memes":       35,
    "rules":       58,
    "welcome":     309,
}


@dataclass
class ForumTopic:
    """Хранит настройки одной ветки форума."""
    topic_name: str
    message_thread_id: int | None
    enabled: bool = True

    @property
    def label(self) -> str:
        """Человекочитаемое название ветки."""
        return TOPIC_LABELS.get(self.topic_name, self.topic_name)

    @property
    def is_configured(self) -> bool:
        """True если message_thread_id уже задан."""
        return self.message_thread_id is not None

    @property
    def status(self) -> str:
        """Показывает текущий ID или «не настроено»."""
        return f"#{self.message_thread_id}" if self.is_configured else "не настроено"
