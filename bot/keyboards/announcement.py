# -*- coding: utf-8 -*-
"""Клавиатура анонса обновления AstrumManager.

Ссылка на бота формируется динамически из username, полученного через
bot.get_me() — при смене username бота код менять не придётся.
"""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.main_menu import BTN
from bot.keyboards.stats import StatBtn


def build_update_announcement_kb(bot_username: str) -> InlineKeyboardMarkup:
    """Строит клавиатуру анонса с одной inline-кнопкой на актуальный username бота."""
    url = f"https://t.me/{bot_username}?start=update"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Обновить AstrumManager", url=url)],
        ]
    )


def build_update_menu_kb() -> InlineKeyboardMarkup:
    """Клавиатура карточки обновления (после deep-link /start update).

    Переиспользует существующие callback_data проекта — не вводит новых схем:
      • BTN.PROFILE      — существующий текстовый идентификатор раздела профиля
      • BTN.COMPLAINTS   — существующий текстовый идентификатор раздела жалоб
      • StatBtn.MENU      — существующий callback_data центра статистики
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN.PROFILE, callback_data=BTN.PROFILE)],
            [InlineKeyboardButton(text=BTN.COMPLAINTS, callback_data=BTN.COMPLAINTS)],
            [InlineKeyboardButton(text="📊 Статистика", callback_data=StatBtn.MENU)],
        ]
    )
