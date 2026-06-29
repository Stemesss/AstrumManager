# -*- coding: utf-8 -*-
"""
Обработчики установки и смены игрового ника.

Потоки:
  NickSetup  — срабатывает на /start у пользователя без ника
  NickChange — срабатывает по callback «nick:change» из профиля
"""
import logging

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.main_menu import MAIN_KEYBOARD
from bot.models.audit import AuditAction
from bot.models.user import UserRole
from bot.services.audit_service import AuditService
from bot.services.user_service import UserService
from bot.states.nick import NickChange, NickSetup
from bot.utils.profile import SETTINGS_KB, build_profile_card
from bot.utils.roles import role_label

router = Router()
logger = logging.getLogger(__name__)

_MIN_LEN = 2
_MAX_LEN = 24


def _validate_nick(text: str) -> str | None:
    """Возвращает очищенный ник или None, если не прошёл валидацию."""
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
    audit_service: AuditService,
) -> None:
    """Принимает игровой ник при первом запуске."""
    if not message.text or message.text.startswith("/"):
        await message.answer(
            f"⚠️ Напишите игровой ник одним сообщением "
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
    logger.info("Пользователь %s установил ник %r", message.from_user.id, nick)

    # Журнал: регистрация нового участника
    await audit_service.log(
        user_id=message.from_user.id,
        game_nick=nick,
        role=UserRole.MEMBER,
        action_type=AuditAction.MEMBER_REGISTER,
        description=f"👤 {nick} зарегистрировался в клане",
    )

    await message.answer(
        f"✅ <b>Ник успешно сохранён!</b>\n\n"
        f"Добро пожаловать в Astrum, <b>{nick}</b>!",
        reply_markup=MAIN_KEYBOARD,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Смена ника (NickChange)
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "nick:change")
async def cb_nick_change(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Запускает FSM смены ника из профиля."""
    await state.set_state(NickChange.waiting_nick)
    await callback.answer()
    await callback.message.answer("Введите новый игровой ник.")


@router.message(NickChange.waiting_nick)
async def fsm_nick_change(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    audit_service: AuditService,
) -> None:
    """Принимает новый ник, сохраняет и показывает обновлённый профиль."""
    if not message.text or message.text.startswith("/"):
        await message.answer(
            f"⚠️ Напишите новый ник одним сообщением "
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

    # Фиксируем старый ник ДО обновления (для журнала)
    old_nick = await user_service.get_game_nick(message.from_user.id) or "?"
    role = await user_service.get_role(message.from_user.id)

    await user_service.set_game_nick(message.from_user.id, nick)
    await state.clear()
    logger.info("Пользователь %s сменил ник на %r", message.from_user.id, nick)

    # Журнал: смена ника
    await audit_service.log(
        user_id=message.from_user.id,
        game_nick=old_nick,
        role=role,
        action_type=AuditAction.MEMBER_NICK_CHANGE,
        description=f"{role_label(role)} {old_nick} изменил ник: {old_nick} → {nick}",
    )

    stats = await user_service.get_profile_stats(message.from_user.id)
    await message.answer(
        f"✅ <b>Ник успешно изменён!</b>\n\n"
        + build_profile_card(nick, role, stats),
        reply_markup=SETTINGS_KB,
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
