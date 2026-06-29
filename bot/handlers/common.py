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
from bot.utils.text import greeting_by_hour

router = Router()
logger = logging.getLogger(__name__)

_MSK = timezone(timedelta(hours=3))

_WELCOME_NEW = (
    "━━━━━━━━━━━━━━━━━━━━\n"
    "🌌 <b>Добро пожаловать в Astrum!</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "Твой профиль успешно создан.\n\n"
    "🎖 <b>Роль:</b>\n"
    "👤 Участник\n\n"
    "Теперь тебе доступны:\n\n"
    "📖 Просмотр новостей\n"
    "📚 Просмотр гайдов\n"
    "📸 Просмотр скриншотов\n"
    "📅 Просмотр событий\n"
    "👤 Личный профиль\n\n"
    "Приятной игры!\n\n"
    "━━━━━━━━━━━━━━━━━━━━"
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
      - создать профиль → записать в audit_log → показать welcome → главное меню.

    Существующий пользователь с ником:
      - приветствие по времени суток + главное меню.

    Существующий пользователь без ника:
      - FSM NickSetup (запрос игрового ника).
    """
    if not message.from_user:
        return

    await state.clear()

    deep_join = (command.args or "").strip().lower() == "join"
    user, is_new = await user_service.register_if_new(message.from_user)

    # ── Новый пользователь (или deep-link ?start=join) ──────────────────────
    if is_new or deep_join:
        logger.info(
            "Новый участник %s (deep_join=%s) — регистрация",
            user.telegram_id, deep_join,
        )
        await user_service.log_registration(user)
        await message.answer(_WELCOME_NEW)
        await message.answer(
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⚜️ <b>AstrumManager</b>\n"
            "Главное меню\n"
            "━━━━━━━━━━━━━━━━━━━━",
            reply_markup=MAIN_KEYBOARD,
        )
        return

    # ── Существующий пользователь без ника — запрос ника (FSM) ─────────────
    if not user.game_nick:
        await state.set_state(NickSetup.waiting_nick)
        logger.info("Пользователь %s без ника — запрос игрового ника", user.telegram_id)
        await message.answer(
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⚜️ <b>AstrumManager</b>\n"
            "👋 Добро пожаловать!\n\n"
            "Для использования бота необходимо указать свой игровой ник.\n\n"
            "Напишите ваш игровой ник одним сообщением.\n\n"
            "Например:\n"
            "<code>Stemess</code>\n\n"
            "<b>Введите ник:</b>\n"
            "━━━━━━━━━━━━━━━━━━━━",
        )
        return

    # ── Существующий пользователь с ником — приветствие ────────────────────
    now = datetime.now(_MSK)
    header, greeting_word, emoji = greeting_by_hour(now.hour)

    logger.info(
        "Пользователь %s (%s) запустил бота — %s (МСК %02d:xx)",
        user.telegram_id, user.game_nick, greeting_word, now.hour,
    )
    await message.answer(
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚜️ <b>AstrumManager</b>\n"
        f"{header}\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{greeting_word}, <b>{user.game_nick}</b>! {emoji}\n\n"
        "Рады снова видеть тебя в сообществе Astrum.\n\n"
        "Желаем удачной игры и хорошего настроения!\n\n"
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
