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

    # ── Мемы ──────────────────────────────────────────────────────────────
    MEME_CREATE = "meme_create"
    MEME_EDIT   = "meme_edit"
    MEME_DELETE = "meme_delete"

    # ── Правила ───────────────────────────────────────────────────────────
    RULES_CREATE = "rules_create"
    RULES_EDIT   = "rules_edit"
    RULES_PIN    = "rules_pin"

    # ── Жалобы и предложения ──────────────────────────────────────────────
    COMPLAINT_CREATE = "complaint_create"
    COMPLAINT_STATUS = "complaint_status"
    COMPLAINT_REPLY  = "complaint_reply"
    COMPLAINT_DELETE = "complaint_delete"

    # ── Системные операции ────────────────────────────────────────────────
    MEMBER_DELETE  = "member_delete"
    SEASON_RESET   = "season_reset"
    SYNC_TITLES    = "sync_titles"
    CLEAN_ABSENT   = "clean_absent"
    NICK_REPORT    = "nick_report"
    NICK_REMIND    = "nick_remind"


# Фильтр action_type для каждой категории (None = без фильтра).
CATEGORY_ACTIONS: dict[str, list[str] | None] = {
    "recent": None,
    "members": [
        AuditAction.MEMBER_REGISTER,
        AuditAction.MEMBER_ROLE_SET,
        AuditAction.MEMBER_NICK_CHANGE,
        AuditAction.MEMBER_DELETE,
        AuditAction.SEASON_RESET,
        AuditAction.SYNC_TITLES,
        AuditAction.CLEAN_ABSENT,
        AuditAction.NICK_REPORT,
        AuditAction.NICK_REMIND,
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
    "memes": [
        AuditAction.MEME_CREATE,
        AuditAction.MEME_EDIT,
        AuditAction.MEME_DELETE,
    ],
    "rules": [
        AuditAction.RULES_CREATE,
        AuditAction.RULES_EDIT,
        AuditAction.RULES_PIN,
    ],
    "complaints": [
        AuditAction.COMPLAINT_CREATE,
        AuditAction.COMPLAINT_STATUS,
        AuditAction.COMPLAINT_REPLY,
        AuditAction.COMPLAINT_DELETE,
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
    "memes":       "😂 Мемы",
    "rules":       "✅ Правила",
    "complaints":  "💡 Жалобы и предложения",
    "all":         "📖 Все записи",
}
