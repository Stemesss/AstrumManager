# -*- coding: utf-8 -*-
"""
Обработчики для групп и супергрупп.

Все личные функции бота работают только в личных сообщениях.
Группа получает лишь ограниченный набор команд сообщества:
  - /start → направить пользователя в личный чат;
  - приветствие новых участников (будущая функция);
  - публикация новостей / событий в чат (будущая функция);
  - модерация / уведомления (будущая функция).
"""
import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

router = Router()
logger = logging.getLogger(__name__)

# Все обработчики этого роутера работают ТОЛЬКО в группах и супергруппах.
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


# ─────────────────────────────────────────────────────────────────────────────
# /start в группе — перенаправление в личный чат
# ─────────────────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def group_start(message: Message, bot_username: str) -> None:
    """
    Отвечает на /start в группе: просит открыть личный чат с ботом.
    Кнопка-ссылка открывает личный чат с @bot_username.
    """
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="💬 Открыть AstrumManager",
            url=f"https://t.me/{bot_username}",
        )
    ]])
    await message.answer(
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚜️ <b>AstrumManager</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "👋 Для использования AstrumManager откройте личный чат с ботом.\n\n"
        "Все функции доступны только в личных сообщениях.\n\n"
        "Нажмите кнопку ниже.\n\n"
        "━━━━━━━━━━━━━━━━━━━━",
        reply_markup=kb,
    )
    logger.info(
        "Пользователь %s вызвал /start в группе %s — перенаправлен в ЛС",
        message.from_user.id if message.from_user else "?",
        message.chat.id,
    )
