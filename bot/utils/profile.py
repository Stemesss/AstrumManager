# -*- coding: utf-8 -*-
"""
Единый рендерер карточки профиля и клавиатура настроек.

Импортируется и в menu.py, и в nick.py, чтобы профиль
выглядел одинаково при открытии и после смены ника.
"""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.models.user import UserRole
from bot.utils.roles import role_display
from bot.utils.text import pluralize_days

SETTINGS_KB = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(text="✏️ Изменить ник", callback_data="nick:change"),
]])


def build_profile_card(nick_str: str, role: UserRole, stats: dict) -> str:
    """Возвращает отформатированный HTML-текст карточки профиля."""
    return (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚜️ <b>AstrumManager</b>\n"
        "👤 <b>Профиль пользователя</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎮 <b>Ник:</b> {nick_str}\n\n"
        f"🎖 <b>Роль Astrum:</b> {role_display(role)}\n\n"
        f"📅 <b>В клане:</b> {pluralize_days(stats['days_in_clan'])}\n"
        f"📚 <b>Создано гайдов:</b> {stats['guides_count']}\n"
        f"📸 <b>Загружено скриншотов:</b> {stats['screenshots_count']}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🟢 Онлайн\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
