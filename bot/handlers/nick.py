# -*- coding: utf-8 -*-
"""
Обработчики установки и смены игрового ника.

Потоки:
  NickSetup  — срабатывает на /start у пользователя без ника
  NickChange — срабатывает по callback «nick:change» из настроек
"""
import logging

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.main_menu import MAIN_KEYBOARD
from bot.services.user_service import UserService
from bot.states.nick import NickChange, NickSetup
from bot.utils.roles import role_label

router = Router()
logger = logging.getLogger(__name__)

_MIN_LEN = 2
_MAX_LEN = 24


def _validate_nick(text: str) -> str | None:
    """
    Возвращает очищенный ник или None если он не прошёл валидацию.
    """
    nick = text.strip()
    if len(nick) < _MIN_LEN or len(nick) > _MAX_LEN:
        return None
    return nick


# ─────────────────────────────────────────────────────────────────────────────
# Первичная установка ника (NickSetup)
# ─────────────────────────────────────────────────────────────────────────────

@router.message(NickSetup.waiting_nick)
async def fsm_nick_setup(
    message: Message,
    state: FSMContext,
    user_service: UserService,
) -> None:
    """Принимает игровой ник при первом запуске."""
    if not message.text or message.text.startswith("/"):
        await message.answer(
            "⚠️ Пожалуйста, введи свой <b>игровой ник</b> текстом "
            f"(от {_MIN_LEN} до {_MAX_LEN} символов):"
        )
        return

    nick = _validate_nick(message.text)
    if nick is None:
        await message.answer(
            f"⚠️ Ник должен быть от <b>{_MIN_LEN}</b> до <b>{_MAX_LEN}</b> символов. "
            "Попробуй ещё раз:"
        )
        return

    await user_service.set_game_nick(message.from_user.id, nick)
    await state.clear()

    role = await user_service.get_role(message.from_user.id)
    logger.info("Пользователь %s установил ник %r", message.from_user.id, nick)

    await message.answer(
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚜️ <b>AstrumManager</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ Ник сохранён: <b>{nick}</b>\n\n"
        f"🌌 Добро пожаловать в клан <b>Astrum</b>!\n"
        f"🏅 Твоя роль: {role_label(role)}\n\n"
        "Выбери нужный раздел в меню.",
        reply_markup=MAIN_KEYBOARD,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Смена ника (NickChange)
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "nick:change")
async def cb_nick_change(
    callback: CallbackQuery,
    state: FSMContext,
    user_service: UserService,
) -> None:
    """Запускает FSM смены ника из профиля."""
    current = await user_service.get_game_nick(callback.from_user.id)
    await state.set_state(NickChange.waiting_nick)
    await callback.answer()

    current_line = f"Текущий ник: <b>{current}</b>\n\n" if current else ""
    await callback.message.answer(
        "✏️ <b>Смена игрового ника</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{current_line}"
        f"Введи новый игровой ник ({_MIN_LEN}–{_MAX_LEN} символов):\n\n"
        "<i>Отправь /cancel для отмены</i>",
    )


@router.message(NickChange.waiting_nick)
async def fsm_nick_change(
    message: Message,
    state: FSMContext,
    user_service: UserService,
) -> None:
    """Принимает и сохраняет новый ник."""
    if not message.text or message.text.startswith("/"):
        await message.answer(
            "⚠️ Пожалуйста, введи новый <b>игровой ник</b> текстом "
            f"(от {_MIN_LEN} до {_MAX_LEN} символов):"
        )
        return

    nick = _validate_nick(message.text)
    if nick is None:
        await message.answer(
            f"⚠️ Ник должен быть от <b>{_MIN_LEN}</b> до <b>{_MAX_LEN}</b> символов. "
            "Попробуй ещё раз:"
        )
        return

    await user_service.set_game_nick(message.from_user.id, nick)
    await state.clear()

    logger.info("Пользователь %s сменил ник на %r", message.from_user.id, nick)
    await message.answer(
        f"✅ <b>Ник успешно изменён!</b>\n\n"
        f"👤 Новый ник: <b>{nick}</b>",
        reply_markup=MAIN_KEYBOARD,
    )


@router.message(
    Command("cancel"),
    StateFilter(NickChange.waiting_nick),
)
async def handle_cancel_nick_change(message: Message, state: FSMContext) -> None:
    """Отменяет смену ника."""
    await state.clear()
    await message.answer(
        "❌ Смена ника отменена.",
        reply_markup=MAIN_KEYBOARD,
    )
