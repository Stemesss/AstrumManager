# -*- coding: utf-8 -*-
"""Клавиатуры мастера публикаций."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class PublishBtn:
    CONFIRM           = "publish:confirm"
    EDIT_TITLE        = "publish:edit_title"
    EDIT_CONTENT      = "publish:edit_content"
    CANCEL            = "publish:cancel"
    ATTACH_DONE       = "publish:attach_done"
    ATTACH_SKIP       = "publish:attach_skip"
    ADD_ATTACHMENTS   = "publish:add_attach"
    CLEAR_ATTACHMENTS = "publish:clear_attach"


# ── Клавиатура шага вложений ───────────────────────────────────────────────────
ATTACH_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✅ Готово", callback_data=PublishBtn.ATTACH_DONE)],
        [InlineKeyboardButton(text="⏩ Без вложений", callback_data=PublishBtn.ATTACH_SKIP)],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=PublishBtn.CANCEL)],
    ]
)

# ── Клавиатура предпросмотра (6 кнопок) ───────────────────────────────────────
PREVIEW_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✅ Опубликовать", callback_data=PublishBtn.CONFIRM)],
        [
            InlineKeyboardButton(text="📎 Добавить ещё",      callback_data=PublishBtn.ADD_ATTACHMENTS),
            InlineKeyboardButton(text="🗑 Удалить вложения",  callback_data=PublishBtn.CLEAR_ATTACHMENTS),
        ],
        [
            InlineKeyboardButton(text="✏️ Изменить заголовок", callback_data=PublishBtn.EDIT_TITLE),
            InlineKeyboardButton(text="📝 Изменить текст",     callback_data=PublishBtn.EDIT_CONTENT),
        ],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data=PublishBtn.CANCEL)],
    ]
)
