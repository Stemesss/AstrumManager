# -*- coding: utf-8 -*-
"""Клавиатуры раздела «📈 Центр статистики» (административная панель)."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class StatisticsBtn:
    """Callback-данные кнопок центра статистики."""
    BEST_MONTH       = "statx:best_month"
    MOST_ACTIVE_WEEK = "statx:most_active_week"
    TOP10            = "statx:top10"
    NEWS             = "statx:news"
    GUIDES           = "statx:guides"
    SCREENSHOTS      = "statx:screenshots"
    EVENTS           = "statx:events"
    GROWTH           = "statx:growth"
    HALL_OF_FAME     = "statx:hall_of_fame"
    MENU             = "statx:menu"
    BACK             = "statx:back"


STATISTICS_MENU_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🏆 Лучший месяца",  callback_data=StatisticsBtn.BEST_MONTH),
            InlineKeyboardButton(text="🔥 Активный недели", callback_data=StatisticsBtn.MOST_ACTIVE_WEEK),
        ],
        [
            InlineKeyboardButton(text="📊 Топ-10",        callback_data=StatisticsBtn.TOP10),
            InlineKeyboardButton(text="👑 Зал славы",     callback_data=StatisticsBtn.HALL_OF_FAME),
        ],
        [
            InlineKeyboardButton(text="📰 Новости",   callback_data=StatisticsBtn.NEWS),
            InlineKeyboardButton(text="📅 События",   callback_data=StatisticsBtn.EVENTS),
        ],
        [InlineKeyboardButton(text="📈 Рост клана",   callback_data=StatisticsBtn.GROWTH)],
        [InlineKeyboardButton(text="⬅️ Назад",        callback_data=StatisticsBtn.BACK)],
    ]
)

STATISTICS_SECTION_KB = InlineKeyboardMarkup(
    inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ Назад", callback_data=StatisticsBtn.MENU),
    ]]
)
