# -*- coding: utf-8 -*-
"""Обработчики основных команд: /start, /help, /about."""
import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot.keyboards.main_menu import MAIN_KEYBOARD
from bot.services.user_service import UserService
from bot.utils.roles import role_label

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def handle_start(message: Message, user_service: UserService) -> None:
    """Регистрирует пользователя и показывает главное меню."""
    if not message.from_user:
        return
    user = await user_service.get_or_create(message.from_user)
    logger.info("Пользователь %s запустил бота (роль: %s)", user.telegram_id, user.role.value)
    await message.answer(
        f"🌌 <b>Добро пожаловать в Astrum!</b>\n\n"
        f"Рады видеть тебя в системе управления кланом.\n"
        f"Твоя роль: {role_label(user.role)}\n\n"
        "Выберите нужный раздел.",
        reply_markup=MAIN_KEYBOARD,
    )


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    """Показывает список доступных команд."""
    await message.answer(
        "📖 <b>Доступные команды</b>\n\n"
        "/start — главное меню\n"
        "/help — показать эту справку\n"
        "/echo &lt;текст&gt; — повторить ваш текст\n"
        "/about — о боте",
    )


@router.message(Command("about"))
async def handle_about(message: Message) -> None:
    """Информация о боте и используемых технологиях."""
    await message.answer(
        "🤖 <b>О боте Astrum Manager</b>\n\n"
        "Система управления кланом <b>Astrum</b>.\n\n"
        "Фреймворк: <b>aiogram 3</b>\n"
        "База данных: <b>SQLite</b> (aiosqlite)\n"
        "Язык: <b>Python 3.11</b>",
    )
