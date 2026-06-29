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

from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.types import ChatMemberUpdated, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.services.topic_service import TopicService

router = Router()
logger = logging.getLogger(__name__)

# Все обработчики этого роутера работают ТОЛЬКО в группах и супергруппах.
router.message.filter(F.chat.type.in_({"group", "supergroup"}))
router.chat_member.filter(F.chat.type.in_({"group", "supergroup"}))


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


# ─────────────────────────────────────────────────────────────────────────────
# Приветствие новых участников → ветка 👋 Приветствие
# ─────────────────────────────────────────────────────────────────────────────

@router.chat_member()
async def handle_new_member(
    event: ChatMemberUpdated,
    bot: Bot,
    topic_service: TopicService,
    bot_username: str,
) -> None:
    """
    Публикует приветствие в ветку «👋 Приветствие» при вступлении участника.
    Если ветка не настроена — отправляет в основной чат.
    Игнорирует выходы и другие изменения статуса.
    """
    old = event.old_chat_member.status
    new = event.new_chat_member.status

    # Только вступление: left/kicked → member/restricted/administrator/creator
    joined = old in ("left", "kicked") and new in (
        "member", "restricted", "administrator", "creator"
    )
    if not joined:
        return

    # Публикуем только в нашей группе (chat_id из конфига)
    if event.chat.id != topic_service.chat_id:
        return

    user = event.new_chat_member.user
    if user.is_bot:
        return

    mention = f'<a href="tg://user?id={user.id}">{user.full_name}</a>'
    text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👋 <b>Новый участник!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Добро пожаловать в клан Astrum, {mention}! 🌌\n\n"
        "Рады видеть тебя в нашем сообществе.\n"
        "Ознакомься с правилами и приятной игры!\n\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🤖 Запустить AstrumManager",
            url=f"https://t.me/{bot_username}?start=welcome",
        )
    ]])
    ok = await topic_service.publish(bot, "welcome", text, reply_markup=kb)
    if ok:
        logger.info(
            "Приветствие для %s (%s) опубликовано в группе %s",
            user.full_name, user.id, event.chat.id,
        )
