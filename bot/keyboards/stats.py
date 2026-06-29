# -*- coding: utf-8 -*-
"""Клавиатуры раздела «📈 Центр статистики»."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class StatBtn:
    """Callback-данные кнопок центра статистики."""
    MENU        = "stats:menu"
    TOP1        = "stats:top1"
    TOP10       = "stats:top10"
    NEWS        = "stats:news"
    GUIDES      = "stats:guides"
    SCREENSHOTS = "stats:screenshots"
    EVENTS      = "stats:events"
    GROWTH      = "stats:growth"
    CLOSE       = "stats:close"


STATS_MENU_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Самый активный участник", callback_data=StatBtn.TOP1)],
        [InlineKeyboardButton(text="🏆 Топ-10 участников",       callback_data=StatBtn.TOP10)],
        [
            InlineKeyboardButton(text="📰 Новости",    callback_data=StatBtn.NEWS),
            InlineKeyboardButton(text="📚 Гайды",      callback_data=StatBtn.GUIDES),
        ],
        [
            InlineKeyboardButton(text="📸 Скриншоты",  callback_data=StatBtn.SCREENSHOTS),
            InlineKeyboardButton(text="📅 События",    callback_data=StatBtn.EVENTS),
        ],
        [InlineKeyboardButton(text="📊 Рост клана",   callback_data=StatBtn.GROWTH)],
        [InlineKeyboardButton(text="❌ Закрыть",       callback_data=StatBtn.CLOSE)],
    ]
)

STATS_BACK_KB = InlineKeyboardMarkup(
    inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ Назад", callback_data=StatBtn.MENU),
    ]]
)
