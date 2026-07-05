# -*- coding: utf-8 -*-
"""Клавиатуры мастера рассылок."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class BroadcastBtn:
    SEND_ALL  = "broadcast:send_all"
    SEND_SELF = "broadcast:send_self"
    EDIT_TEXT = "broadcast:edit_text"
    CANCEL    = "broadcast:cancel"


PREVIEW_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📤 Отправить всем участникам", callback_data=BroadcastBtn.SEND_ALL)],
        [InlineKeyboardButton(text="🧪 Отправить себе (тест)",     callback_data=BroadcastBtn.SEND_SELF)],
        [InlineKeyboardButton(text="✏️ Изменить текст",            callback_data=BroadcastBtn.EDIT_TEXT)],
        [InlineKeyboardButton(text="❌ Закрыть",                    callback_data=BroadcastBtn.CANCEL)],
    ]
)
