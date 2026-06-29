# -*- coding: utf-8 -*-
"""Константы типов действий и категорий для журнала аудита."""


class AuditAction:
    """Все возможные типы действий, записываемых в журнал."""

    # ── Участники ──────────────────────────────────────────────────────────
    MEMBER_REGISTER   = "member_register"
    MEMBER_ROLE_SET   = "member_role_set"
    MEMBER_NICK_CHANGE = "member_nick_change"

    # ── Новости ────────────────────────────────────────────────────────────
    NEWS_CREATE = "news_create"
    NEWS_EDIT   = "news_edit"
    NEWS_PIN    = "news_pin"
    NEWS_UNPIN  = "news_unpin"
    NEWS_DELETE = "news_delete"

    # ── События ────────────────────────────────────────────────────────────
    EVENT_CREATE = "event_create"
    EVENT_EDIT   = "event_edit"
    EVENT_DELETE = "event_delete"

    # ── Гайды ─────────────────────────────────────────────────────────────
    GUIDE_CREATE = "guide_create"
    GUIDE_EDIT   = "guide_edit"
    GUIDE_DELETE = "guide_delete"

    # ── Скриншоты ─────────────────────────────────────────────────────────
    SCREENSHOT_UPLOAD = "screenshot_upload"
    SCREENSHOT_DELETE = "screenshot_delete"


# Фильтр action_type для каждой категории (None = без фильтра).
CATEGORY_ACTIONS: dict[str, list[str] | None] = {
    "recent": None,
    "members": [
        AuditAction.MEMBER_REGISTER,
        AuditAction.MEMBER_ROLE_SET,
        AuditAction.MEMBER_NICK_CHANGE,
    ],
    "news": [
        AuditAction.NEWS_CREATE,
        AuditAction.NEWS_EDIT,
        AuditAction.NEWS_PIN,
        AuditAction.NEWS_UNPIN,
        AuditAction.NEWS_DELETE,
    ],
    "events": [
        AuditAction.EVENT_CREATE,
        AuditAction.EVENT_EDIT,
        AuditAction.EVENT_DELETE,
    ],
    "guides": [
        AuditAction.GUIDE_CREATE,
        AuditAction.GUIDE_EDIT,
        AuditAction.GUIDE_DELETE,
    ],
    "screenshots": [
        AuditAction.SCREENSHOT_UPLOAD,
        AuditAction.SCREENSHOT_DELETE,
    ],
    "all": None,
}

CATEGORY_LABELS: dict[str, str] = {
    "recent":      "Последние действия",
    "members":     "👥 Участники",
    "news":        "📰 Новости",
    "events":      "📅 События",
    "guides":      "📚 Гайды",
    "screenshots": "📸 Скриншоты",
    "all":         "📖 Все записи",
}
