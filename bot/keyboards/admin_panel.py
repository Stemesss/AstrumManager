# -*- coding: utf-8 -*-
"""Клавиатура панели администрации (для всех административных ролей)."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class AdminBtn:
    """Callback-данные кнопок панели администратора."""
    MEMBERS = "admin:members"
    NEWS = "admin:news"
    EVENTS = "admin:events"
    GUIDES = "admin:guides"
    SCREENSHOTS = "admin:screenshots"
    COMMUNITY = "admin:community"


ADMIN_PANEL_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="👥 Управление участниками", callback_data=AdminBtn.MEMBERS),
        ],
        [
            InlineKeyboardButton(text="📢 Управление новостями", callback_data=AdminBtn.NEWS),
        ],
        [
            InlineKeyboardButton(text="📅 Управление событиями", callback_data=AdminBtn.EVENTS),
        ],
        [
            InlineKeyboardButton(text="📚 Управление гайдами", callback_data=AdminBtn.GUIDES),
        ],
        [
            InlineKeyboardButton(text="📸 Управление скриншотами", callback_data=AdminBtn.SCREENSHOTS),
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки сообщества", callback_data=AdminBtn.COMMUNITY),
        ],
    ]
)
