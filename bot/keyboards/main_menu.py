# -*- coding: utf-8 -*-
"""Главная Reply-клавиатура меню управления кланом."""
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


class BTN:
    """Текст кнопок главного меню — единственный источник истины."""
    NEWS        = "📰 Новости"
    EVENTS      = "📅 События"
    GUIDES      = "📚 Гайды"
    SCREENSHOTS = "📸 Скриншоты"
    MEMBERS     = "👥 Участники"
    ADMIN       = "🛡️ Администрация"
    AUDIT       = "📋 Журнал действий"
    SETTINGS    = "⚙️ Настройки"
    HELP        = "❓ Помощь"


MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BTN.NEWS),    KeyboardButton(text=BTN.EVENTS)],
        [KeyboardButton(text=BTN.GUIDES),  KeyboardButton(text=BTN.SCREENSHOTS)],
        [KeyboardButton(text=BTN.MEMBERS), KeyboardButton(text=BTN.ADMIN)],
        [KeyboardButton(text=BTN.AUDIT),   KeyboardButton(text=BTN.SETTINGS)],
        [KeyboardButton(text=BTN.HELP)],
    ],
    resize_keyboard=True,
)
