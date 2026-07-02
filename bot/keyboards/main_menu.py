# -*- coding: utf-8 -*-
"""Главная Reply-клавиатура меню управления кланом."""
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


class BTN:
    """Текст кнопок главного меню — единственный источник истины."""
    NEWS        = "📰 Новости"
    EVENTS      = "📅 События"
    RULES       = "✅ Правила"
    COMPLAINTS  = "💡 Жалобы и предложения"
    MEMBERS     = "👥 Участники"
    ADMIN       = "🛡️ Администрация"
    AUDIT       = "📋 Журнал действий"
    STATS       = "📈 Статистика"
    PROFILE     = "👤 Мой профиль"
    HELP        = "❓ Помощь"


MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BTN.NEWS),        KeyboardButton(text=BTN.EVENTS)],
        [KeyboardButton(text=BTN.RULES),       KeyboardButton(text=BTN.COMPLAINTS)],
        [KeyboardButton(text=BTN.MEMBERS),     KeyboardButton(text=BTN.ADMIN)],
        [KeyboardButton(text=BTN.AUDIT),       KeyboardButton(text=BTN.STATS)],
        [KeyboardButton(text=BTN.PROFILE),     KeyboardButton(text=BTN.HELP)],
    ],
    resize_keyboard=True,
)
