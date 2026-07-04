# -*- coding: utf-8 -*-
"""Клавиатура анонса обновления AstrumManager.

Ссылка на бота формируется динамически из username, полученного через
bot.get_me() — при смене username бота код менять не придётся.
"""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def build_update_announcement_kb(bot_username: str) -> InlineKeyboardMarkup:
    """Строит клавиатуру анонса с одной inline-кнопкой на актуальный username бота."""
    url = f"https://t.me/{bot_username}?start=update"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Обновить AstrumManager", url=url)],
        ]
    )
