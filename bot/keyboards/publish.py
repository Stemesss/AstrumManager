# -*- coding: utf-8 -*-
"""Клавиатура предпросмотра единого мастера публикаций."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class PublishBtn:
    CONFIRM      = "publish:confirm"
    EDIT_TITLE   = "publish:edit_title"
    EDIT_CONTENT = "publish:edit_content"
    CANCEL       = "publish:cancel"


PREVIEW_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✅ Опубликовать",        callback_data=PublishBtn.CONFIRM)],
        [
            InlineKeyboardButton(text="✏️ Изменить заголовок", callback_data=PublishBtn.EDIT_TITLE),
            InlineKeyboardButton(text="📝 Изменить текст",     callback_data=PublishBtn.EDIT_CONTENT),
        ],
        [InlineKeyboardButton(text="❌ Закрыть",             callback_data=PublishBtn.CANCEL)],
    ]
)
