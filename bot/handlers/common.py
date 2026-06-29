# -*- coding: utf-8 -*-
"""Обработчики основных команд: /start, /help, /about."""
import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.keyboards.main_menu import MAIN_KEYBOARD
from bot.services.user_service import UserService
from bot.states.nick import NickSetup
from bot.utils.roles import role_label

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def handle_start(
    message: Message,
    user_service: UserService,
    state: FSMContext,
) -> None:
    """Регистрирует пользователя. При первом запуске запрашивает игровой ник."""
    if not message.from_user:
        return

    await state.clear()
    user = await user_service.get_or_create(message.from_user)
    logger.info("Пользователь %s запустил бота (роль: %s)", user.telegram_id, user.role.value)

    if not user.game_nick:
        # Первый запуск — запрашиваем ник перед показом меню
        await state.set_state(NickSetup.waiting_nick)
        await message.answer(
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⚜️ <b>AstrumManager</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🌌 Добро пожаловать в клан <b>Astrum</b>!\n\n"
            "Перед началом работы введи свой <b>игровой ник</b> "
            "(от 2 до 24 символов):"
        )
        return

    await message.answer(
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚜️ <b>AstrumManager</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🌌 Добро пожаловать, <b>{user.game_nick}</b>!\n"
        f"🏅 Твоя роль: {role_label(user.role)}\n\n"
        "Выбери нужный раздел.",
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
