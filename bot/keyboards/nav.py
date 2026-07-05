# -*- coding: utf-8 -*-
"""Единый набор навигационных кнопок и клавиатур."""
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove

from bot.keyboards.main_menu import MAIN_KEYBOARD

CANCEL_TEXT = "❌ Отмена"

CANCEL_KB = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=CANCEL_TEXT)]],
    resize_keyboard=True,
)


async def reset_to_main_menu(message: Message, text: str) -> None:
    """
    Гарантированно убирает текущую Reply-клавиатуру и показывает главное меню.

    Используется при любом выходе из FSM: отмена, успех, ошибка, закрытие мастера.
    Отправляет два сообщения — сначала с ReplyKeyboardRemove(), затем с главным меню,
    т.к. одно сообщение может нести только одну reply-клавиатуру.
    """
    await message.answer(text, reply_markup=ReplyKeyboardRemove())
    await message.answer("⚜️ Главное меню", reply_markup=MAIN_KEYBOARD)
