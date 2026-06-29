# -*- coding: utf-8 -*-
"""
Обработчики настройки и смены игрового имени.

Потоки:
  NickSetup  — первичная настройка профиля (новый пользователь)
  NickChange — смена имени через «👤 Мой профиль»

Шаги каждого потока:
  1. waiting_name    — пользователь вводит имя
  2. waiting_confirm — предпросмотр ника, ждём ✅/✏️
"""
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot.keyboards.main_menu import MAIN_KEYBOARD
from bot.models.audit import AuditAction
from bot.models.user import UserRole
from bot.services.audit_service import AuditService
from bot.services.user_service import UserService
from bot.states.nick import NickChange, NickSetup
from bot.utils.nick_format import build_full_nick, validate_name
from bot.utils.profile import PROFILE_KB, build_profile_card

router = Router()
logger = logging.getLogger(__name__)

# ─── Клавиатура предпросмотра ─────────────────────────────────────────────────

_PREVIEW_KB = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(text="✅ Подтвердить", callback_data="nick:confirm"),
    InlineKeyboardButton(text="✏️ Изменить",    callback_data="nick:edit"),
]])

# ─── Общий промпт для ввода имени ────────────────────────────────────────────

_NAME_PROMPT = (
    "🎮 <b>Введите ваше игровое имя:</b>\n\n"
    "• от 3 до 20 символов\n"
    "• только буквы, цифры, пробел, дефис\n"
    "• без эмодзи и спецсимволов\n"
    "• только имя, без титулов\n\n"
    "Например: <code>Вадим</code>"
)

_CHANGE_PROMPT = (
    "🎮 <b>Введите новое игровое имя:</b>\n\n"
    "• от 3 до 20 символов\n"
    "• только буквы, цифры, пробел, дефис\n"
    "• без эмодзи и спецсимволов\n"
    "• только имя, без титулов"
)


def _preview_text(full_nick: str) -> str:
    return (
        "👤 <b>Предпросмотр профиля</b>\n\n"
        "Ваш ник будет выглядеть так:\n\n"
        f"<b>{full_nick}</b>\n\n"
        "Всё верно?"
    )


# ─────────────────────────────────────────────────────────────────────────────
# ПОТОК 1: Первичная настройка (NickSetup)
# ─────────────────────────────────────────────────────────────────────────────

@router.message(NickSetup.waiting_name)
async def fsm_setup_enter_name(
    message: Message,
    state: FSMContext,
    user_service: UserService,
) -> None:
    """Принимает введённое имя, валидирует, показывает предпросмотр."""
    if not message.text or message.text.startswith("/"):
        await message.answer(_NAME_PROMPT)
        return

    name, error = validate_name(message.text)
    if error:
        await message.answer(error)
        return

    role = await user_service.get_role(message.from_user.id)
    full_nick = build_full_nick(name, role)

    await state.update_data(pending_name=name)
    await state.set_state(NickSetup.waiting_confirm)

    await message.answer(_preview_text(full_nick), reply_markup=_PREVIEW_KB)


@router.callback_query(F.data == "nick:confirm", NickSetup.waiting_confirm)
async def cb_setup_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    user_service: UserService,
    audit_service: AuditService,
) -> None:
    """Сохраняет имя, завершает настройку, открывает главное меню."""
    data = await state.get_data()
    name = data.get("pending_name", "")
    await state.clear()

    await user_service.set_game_nick(callback.from_user.id, name)

    role = await user_service.get_role(callback.from_user.id)
    full_nick = build_full_nick(name, role)

    await audit_service.log(
        user_id=callback.from_user.id,
        game_nick=name,
        role=role,
        action_type=AuditAction.MEMBER_REGISTER,
        description=f"👤 {full_nick} зарегистрировался в клане",
    )

    logger.info(
        "Пользователь %s завершил первичную настройку: ник %r",
        callback.from_user.id, full_nick,
    )

    await callback.message.edit_text(
        f"✅ <b>Профиль настроен!</b>\n\n"
        f"Добро пожаловать в Astrum, <b>{full_nick}</b>! 🎉"
    )
    await callback.message.answer(
        "⚜️ <b>AstrumManager</b>  •  Главное меню",
        reply_markup=MAIN_KEYBOARD,
    )
    await callback.answer()


@router.callback_query(F.data == "nick:edit", NickSetup.waiting_confirm)
async def cb_setup_edit(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Возвращает к вводу имени."""
    await state.set_state(NickSetup.waiting_name)
    await callback.message.edit_text(_NAME_PROMPT)
    await callback.answer()


# ─────────────────────────────────────────────────────────────────────────────
# ПОТОК 2: Смена имени (NickChange) — из раздела «👤 Мой профиль»
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "nick:change")
async def cb_nick_change_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Запускает FSM смены имени из профиля."""
    await state.set_state(NickChange.waiting_name)
    await callback.answer()
    await callback.message.answer(_CHANGE_PROMPT)


@router.message(NickChange.waiting_name)
async def fsm_change_enter_name(
    message: Message,
    state: FSMContext,
    user_service: UserService,
) -> None:
    """Принимает новое имя, валидирует, показывает предпросмотр."""
    if not message.text or message.text.startswith("/"):
        await message.answer(_CHANGE_PROMPT)
        return

    name, error = validate_name(message.text)
    if error:
        await message.answer(error)
        return

    role = await user_service.get_role(message.from_user.id)
    full_nick = build_full_nick(name, role)

    await state.update_data(pending_name=name)
    await state.set_state(NickChange.waiting_confirm)

    await message.answer(_preview_text(full_nick), reply_markup=_PREVIEW_KB)


@router.callback_query(F.data == "nick:confirm", NickChange.waiting_confirm)
async def cb_change_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    user_service: UserService,
    audit_service: AuditService,
) -> None:
    """Сохраняет новое имя, показывает обновлённый профиль."""
    data = await state.get_data()
    new_name = data.get("pending_name", "")

    old_name = await user_service.get_game_nick(callback.from_user.id) or "?"
    role = await user_service.get_role(callback.from_user.id)

    await user_service.set_game_nick(callback.from_user.id, new_name)
    await state.clear()

    new_full = build_full_nick(new_name, role)
    old_full  = build_full_nick(old_name, role) if old_name != "?" else old_name

    await audit_service.log(
        user_id=callback.from_user.id,
        game_nick=old_name,
        role=role,
        action_type=AuditAction.MEMBER_NICK_CHANGE,
        description=f"{old_full} изменил имя → {new_full}",
    )

    logger.info(
        "Пользователь %s сменил имя: %r → %r",
        callback.from_user.id, old_name, new_name,
    )

    stats = await user_service.get_profile_stats(callback.from_user.id)
    await callback.message.edit_text(
        f"✅ <b>Имя успешно изменено!</b>\n\n"
        + build_profile_card(new_name, role, stats),
        reply_markup=PROFILE_KB,
    )
    await callback.answer()


@router.callback_query(F.data == "nick:edit", NickChange.waiting_confirm)
async def cb_change_edit(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Возвращает к вводу нового имени."""
    await state.set_state(NickChange.waiting_name)
    await callback.message.edit_text(_CHANGE_PROMPT)
    await callback.answer()
