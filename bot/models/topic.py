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
}

ALL_TOPIC_NAMES: list[str] = list(TOPIC_LABELS.keys())


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
