# -*- coding: utf-8 -*-
"""Клавиатура панели администрации (для всех административных ролей)."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class AdminBtn:
    """Callback-данные кнопок панели администрации."""
    MEMBERS     = "admin:members"
    ROLES       = "admin:roles"
    NEWS        = "admin:news"
    EVENTS      = "admin:events"
    GUIDES      = "admin:guides"
    SCREENSHOTS = "admin:screenshots"
    AUDIT       = "admin:audit"
    SETTINGS    = "admin:settings"
    STATISTICS  = "admin:statistics"


ADMIN_PANEL_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="📰 Новости",             callback_data=AdminBtn.NEWS),
            InlineKeyboardButton(text="📅 События",             callback_data=AdminBtn.EVENTS),
        ],
        [
            InlineKeyboardButton(text="📚 Гайды",               callback_data=AdminBtn.GUIDES),
            InlineKeyboardButton(text="📸 Скриншоты",           callback_data=AdminBtn.SCREENSHOTS),
        ],
        [
            InlineKeyboardButton(text="👥 Участники",           callback_data=AdminBtn.MEMBERS),
        ],
        [
            InlineKeyboardButton(text="📋 Журнал действий",     callback_data=AdminBtn.AUDIT),
            InlineKeyboardButton(text="⚙️ Настройки",           callback_data=AdminBtn.SETTINGS),
        ],
        [
            InlineKeyboardButton(text="📈 Центр статистики",    callback_data=AdminBtn.STATISTICS),
        ],
    ]
)
