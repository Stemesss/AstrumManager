# -*- coding: utf-8 -*-
"""
ВРЕМЕННЫЙ обработчик /testannounce — тестовая отправка анонса обновления
только администратору, который выполнил команду. Личный чат исполнителя,
клановая группа НЕ используется.
"""
import logging

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.services.announcements import send_update_announcement

router = Router()
logger = logging.getLogger(__name__)

# Суперпользователь — единственный, кому доступна тестовая команда
_SUPERUSER_ID = 8490615925


@router.message(Command("testannounce"))
async def cmd_testannounce(
    message: Message,
    bot: Bot,
    state: FSMContext,
    owner_id: int | None,
) -> None:
    """Отправляет анонс обновления исполнителю команды (тестовый режим)."""
    if not message.from_user:
        return

    actor_id = message.from_user.id
    is_authorized = actor_id == _SUPERUSER_ID or (owner_id is not None and actor_id == owner_id)

    if not is_authorized:
        await message.reply("🔒 Команда доступна только администратору.")
        return

    ok = await send_update_announcement(bot, actor_id, state=state)
    if ok:
        await message.reply("✅ Тестовый анонс отправлен вам в личные сообщения.")
    else:
        await message.reply("❌ Не удалось отправить анонс. Подробности — в логах.")
