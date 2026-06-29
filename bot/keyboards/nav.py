# -*- coding: utf-8 -*-
"""Единый набор навигационных кнопок и клавиатур."""
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

CANCEL_TEXT = "❌ Отмена"

CANCEL_KB = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=CANCEL_TEXT)]],
    resize_keyboard=True,
)
