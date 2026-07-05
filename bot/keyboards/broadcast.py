# -*- coding: utf-8 -*-
"""Клавиатуры подсистемы рассылок."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class BroadcastBtn:
    # Хаб
    NEW        = "broadcast:new"
    HISTORY    = "broadcast:history"
    TEMPLATES  = "broadcast:templates"
    SCHEDULED  = "broadcast:scheduled"
    BACK       = "broadcast:back"
    CLOSE      = "broadcast:close"

    # Предпросмотр
    SEND_ALL     = "broadcast:send_all"
    SEND_SELF    = "broadcast:send_self"
    EDIT_TEXT    = "broadcast:edit_text"
    SAVE_TPL     = "broadcast:save_tpl"
    SCHEDULE     = "broadcast:schedule"
    CANCEL       = "broadcast:cancel"

    # Шаблоны (динамические префиксы)
    TPL_USE_PREFIX = "broadcast:tpl_use:"
    TPL_DEL_PREFIX = "broadcast:tpl_del:"
    TPL_NEW        = "broadcast:tpl_new"

    # Запланированные (динамический префикс)
    SCHED_CANCEL_PREFIX = "broadcast:sched_cancel:"


HUB_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Новая рассылка", callback_data=BroadcastBtn.NEW)],
        [InlineKeyboardButton(text="🗂 Шаблоны",         callback_data=BroadcastBtn.TEMPLATES)],
        [InlineKeyboardButton(text="📊 История",         callback_data=BroadcastBtn.HISTORY)],
        [InlineKeyboardButton(text="⏰ Запланированные",  callback_data=BroadcastBtn.SCHEDULED)],
        [InlineKeyboardButton(text="❌ Закрыть",          callback_data=BroadcastBtn.CLOSE)],
    ]
)

PREVIEW_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📤 Отправить всем участникам", callback_data=BroadcastBtn.SEND_ALL)],
        [InlineKeyboardButton(text="🧪 Отправить себе (тест)",     callback_data=BroadcastBtn.SEND_SELF)],
        [InlineKeyboardButton(text="⏰ Запланировать",              callback_data=BroadcastBtn.SCHEDULE)],
        [InlineKeyboardButton(text="💾 Сохранить как шаблон",       callback_data=BroadcastBtn.SAVE_TPL)],
        [InlineKeyboardButton(text="✏️ Изменить текст",            callback_data=BroadcastBtn.EDIT_TEXT)],
        [InlineKeyboardButton(text="❌ Закрыть",                    callback_data=BroadcastBtn.CANCEL)],
    ]
)


def templates_kb(templates) -> InlineKeyboardMarkup:
    """Строит клавиатуру списка шаблонов: использовать / удалить для каждого."""
    rows = []
    for tpl in templates:
        rows.append([
            InlineKeyboardButton(
                text=f"📄 {tpl['name']}",
                callback_data=f"{BroadcastBtn.TPL_USE_PREFIX}{tpl['id']}",
            ),
            InlineKeyboardButton(
                text="🗑",
                callback_data=f"{BroadcastBtn.TPL_DEL_PREFIX}{tpl['id']}",
            ),
        ])
    rows.append([InlineKeyboardButton(text="➕ Новый шаблон", callback_data=BroadcastBtn.TPL_NEW)])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=BroadcastBtn.BACK)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def scheduled_kb(scheduled) -> InlineKeyboardMarkup:
    """Строит клавиатуру списка запланированных рассылок с кнопками отмены."""
    rows = []
    for row in scheduled:
        rows.append([
            InlineKeyboardButton(
                text=f"❌ Отменить #{row['id']} ({row['scheduled_at']} UTC)",
                callback_data=f"{BroadcastBtn.SCHED_CANCEL_PREFIX}{row['id']}",
            ),
        ])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=BroadcastBtn.BACK)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


BACK_ONLY_KB = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=BroadcastBtn.BACK)]]
)
