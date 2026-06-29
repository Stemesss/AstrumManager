# -*- coding: utf-8 -*-
"""
Рендерер карточки профиля и клавиатура «👤 Мой профиль».

Импортируется и в menu.py, и в nick.py, чтобы профиль
выглядел одинаково при открытии и после смены имени.
"""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.models.user import UserRole
from bot.utils.nick_format import build_full_nick
from bot.utils.roles import role_display
from bot.utils.text import pluralize_days

PROFILE_KB = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(text="✏️ Изменить имя", callback_data="nick:change"),
]])


def build_profile_card(name: str, role: UserRole, stats: dict) -> str:
    """Возвращает отформатированный HTML-текст карточки профиля.

    Args:
        name:  игровое имя участника (только имя без титула, из game_nick в БД)
        role:  текущая роль (для отображения титула и роли)
        stats: словарь со статистикой (days_in_clan, guides_count, screenshots_count)
    """
    full_nick = build_full_nick(name, role) if name else "<i>не задан</i>"
    return (
        "⚜️ <b>AstrumManager</b>  •  👤 Профиль\n\n"
        f"🎮 <b>Ник:</b> {full_nick}\n"
        f"🎖 <b>Роль:</b> {role_display(role)}\n\n"
        f"📅 <b>В клане:</b> {pluralize_days(stats['days_in_clan'])}\n"
        f"📚 <b>Гайдов:</b> {stats['guides_count']}\n"
        f"📸 <b>Скриншотов:</b> {stats['screenshots_count']}\n\n"
        "🟢 Онлайн"
    )
