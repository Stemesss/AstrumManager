# -*- coding: utf-8 -*-
"""
Единый реестр системных форумных тем AstrumManager.

Для добавления новой системной темы достаточно добавить запись в TOPIC_REGISTRY.
Все остальные механизмы (синхронизация, публикация, UI) автоматически подхватят
новую тему без изменений в других файлах.

Ограничения Telegram Bot API:
  - icon_color нельзя менять после создания темы.
  - name и icon_custom_emoji_id можно менять через editForumTopic.
  - Список тем в чате через API получить нельзя (только create/edit/delete).
  - icon_custom_emoji_id — это ID кастомного стикера из Telegram-наборов
    (не стандартные Unicode-эмодзи; конкретные ID получаются через
    getForumTopicIconStickers или устанавливаются вручную).
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class TopicDefinition:
    """Метаданные одной системной форумной темы."""

    key:    str   # Внутренний ключ (e.g. "news")
    name:   str   # Полное название — используется как имя темы в Telegram
    emoji:  str   # Эмодзи-символ (только для отображения в UI)
    icon_color: int  # Цвет фона иконки при создании (менять нельзя после создания)
    required:   bool = True   # Обязательная ли системная тема?
    # icon_custom_emoji_id хранится в БД, здесь не задаётся —
    # устанавливается администратором или при синхронизации.


# ─── Единый реестр всех системных тем ─────────────────────────────────────────
# Порядок записей определяет порядок отображения в UI и очерёдность синхронизации.
#
# Допустимые значения icon_color (задаются Telegram):
#   7322096  — синий       16766590 — жёлтый     13338331 — фиолетовый
#   9367192  — зелёный     16749490 — красный     16478047 — оранжевый

TOPIC_REGISTRY: dict[str, TopicDefinition] = {
    "news":          TopicDefinition("news",          "📰 Новости",              "📰", 7322096),
    "guides":        TopicDefinition("guides",        "📚 Гайды",                "📚", 9367192),
    "screenshots":   TopicDefinition("screenshots",   "📸 Скриншоты",            "📸", 16478047),
    "events":        TopicDefinition("events",        "📅 События",              "📅", 16766590),
    "announcements": TopicDefinition("announcements", "📢 Объявления",           "📢", 13338331),
    "welcome":       TopicDefinition("welcome",       "👋 Приветствие",          "👋", 16749490),
    "complaints":    TopicDefinition("complaints",    "💡 Жалобы и предложения", "💡", 16766590),
    "memes":         TopicDefinition("memes",         "😂 Мемы",                 "😂", 16749490),
    "rules":         TopicDefinition("rules",         "✅ Правила",              "✅", 9367192),
}

# ── Обратная совместимость (старый код использует эти константы напрямую) ──────
TOPIC_LABELS:    dict[str, str] = {k: v.name for k, v in TOPIC_REGISTRY.items()}
ALL_TOPIC_NAMES: list[str]      = list(TOPIC_REGISTRY.keys())

DEFAULT_CHAT_ID: int = -1004463841801

# Предустановленные thread_id для группы Astrum.
# Используются только при первом запуске (seed_default_topics), если тема ещё
# не настроена вручную или автоматически.
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
    """Хранит настройки одной ветки форума (строка из БД forum_topics)."""

    topic_name:           str
    message_thread_id:    int | None
    enabled:              bool       = True
    icon_custom_emoji_id: str | None = None

    @property
    def definition(self) -> TopicDefinition | None:
        """Метаданные темы из централизованного реестра."""
        return TOPIC_REGISTRY.get(self.topic_name)

    @property
    def label(self) -> str:
        """Человекочитаемое название ветки."""
        defn = self.definition
        return defn.name if defn else TOPIC_LABELS.get(self.topic_name, self.topic_name)

    @property
    def is_configured(self) -> bool:
        """True если message_thread_id задан."""
        return self.message_thread_id is not None

    @property
    def status(self) -> str:
        """Краткий статус для отображения в UI."""
        return f"#{self.message_thread_id}" if self.is_configured else "не настроено"
