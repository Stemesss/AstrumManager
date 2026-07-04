# -*- coding: utf-8 -*-
"""Клавиатура анонса обновления AstrumManager."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

UPDATE_BOT_URL = "https://t.me/AstrumManagerBot?start=update"

UPDATE_ANNOUNCEMENT_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Обновить AstrumManager", url=UPDATE_BOT_URL)],
    ]
)
