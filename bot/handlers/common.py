# -*- coding: utf-8 -*-
"""Обработчики основных команд: /start, /help, /about."""
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.keyboards.main_menu import MAIN_KEYBOARD
from bot.services.user_service import UserService
from bot.states.nick import NickSetup
from bot.utils.nick_format import build_full_nick
from bot.utils.text import greeting_by_hour

router = Router()
logger = logging.getLogger(__name__)

_MSK = timezone(timedelta(hours=3))

# Приглашение к первичной настройке профиля
_SETUP_WELCOME = (
    "👋 <b>Добро пожаловать в Astrum!</b>\n\n"
    "Перед началом необходимо настроить ваш профиль.\n\n"
    "🎮 <b>Введите ваше игровое имя:</b>\n\n"
    "• от 3 до 20 символов\n"
    "• только буквы, цифры, пробел, дефис\n"
    "• без эмодзи и спецсимволов\n"
    "• только имя, без титулов\n\n"
    "Например: <code>Вадим</code>"
)

_SETUP_RETURN = (
    "⚜️ <b>AstrumManager</b>\n\n"
    "🎮 <b>Укажите игровое имя</b> для продолжения:\n\n"
    "• от 3 до 20 символов\n"
    "• только буквы, цифры, пробел, дефис\n"
    "• без эмодзи и спецсимволов\n"
    "• только имя, без титулов"
)


@router.message(CommandStart())
async def handle_start(
    message: Message,
    user_service: UserService,
    state: FSMContext,
    command: CommandObject,
) -> None:
    """
    Обрабатывает /start и deep-link /start join.

    Новый пользователь:
      → запуск мастера первичной настройки профиля (NickSetup).

    Существующий пользователь без ника:
      → повторный запуск мастера настройки.

    Существующий пользователь с ником:
      → приветствие по времени суток + главное меню.
    """
    if not message.from_user:
        return

    await state.clear()

    deep_join = (command.args or "").strip().lower() == "join"
    user, is_new = await user_service.register_if_new(message.from_user)

    # ── Новый пользователь → мастер первичной настройки ─────────────────────
    if is_new or deep_join:
        logger.info(
            "Новый участник %s (deep_join=%s) — запуск мастера настройки профиля",
            user.telegram_id, deep_join,
        )
        await state.set_state(NickSetup.waiting_name)
        await message.answer(_SETUP_WELCOME)
        return

    # ── Существующий пользователь без ника — повторный запуск мастера ───────
    if not user.game_nick:
        await state.set_state(NickSetup.waiting_name)
        logger.info(
            "Пользователь %s без ника — запуск мастера настройки профиля",
            user.telegram_id,
        )
        await message.answer(_SETUP_RETURN)
        return

    # ── Существующий пользователь с ником — приветствие ─────────────────────
    now = datetime.now(_MSK)
    header, greeting_word, emoji = greeting_by_hour(now.hour)
    role = await user_service.get_role(user.telegram_id)
    full_nick = build_full_nick(user.game_nick, role)

    logger.info(
        "Пользователь %s (%s) запустил бота — %s (МСК %02d:xx)",
        user.telegram_id, full_nick, greeting_word, now.hour,
    )
    await message.answer(
        f"⚜️ <b>AstrumManager</b>  •  {header}\n\n"
        f"{greeting_word}, <b>{full_nick}</b>! {emoji}\n\n"
        "Рады снова видеть тебя в сообществе Astrum.\n\n"
        "Выберите нужный раздел ниже.",
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
