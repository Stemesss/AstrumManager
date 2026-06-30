# -*- coding: utf-8 -*-
"""
Обработчики настройки и смены игрового имени.

Потоки:
  NickSetup  — первичная настройка профиля (новый пользователь)
  NickChange — смена имени через «👤 Мой профиль»

Шаги каждого потока:
  1. waiting_name    — пользователь вводит имя
  2. waiting_confirm — предпросмотр ника, ждём ✅/✏️

После подтверждения:
  • Имя сохраняется в БД (game_nick).
  • Для администраторов (Лидер/Старейшина/Дитя клана) автоматически
    обновляется Telegram Admin Title в групповом чате.
  • Всем пользователям отправляется подсказка с форматированным
    ником для самостоятельной установки в Telegram Профиль.

ВАЖНО: Telegram Bot API не позволяет изменять отображаемое имя
обычного пользователя (first_name/username). Для участников со статусом
Участник (◇ Участник) бот не может автоматически изменить имя в чате.
"""
import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot.keyboards.main_menu import MAIN_KEYBOARD
from bot.models.audit import AuditAction
from bot.services.audit_service import AuditService
from bot.services.nickname_service import NicknameService
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

# ─── Подсказка по копированию ника ───────────────────────────────────────────

_HOW_TO_RENAME = (
    "Telegram → Настройки → Изменить профиль → Имя"
)


def _copy_hint_kb(full_nick: str) -> InlineKeyboardMarkup:
    """Кнопка-инструкция для самостоятельной смены имени в Telegram."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="📖 Как изменить имя в Telegram",
            callback_data="nick:how_to_rename",
        ),
    ]])


def _copy_hint_text(full_nick: str) -> str:
    return (
        f"📋 <b>Ваш игровой ник:</b>\n\n"
        f"<code>{full_nick}</code>\n\n"
        f"<i>Нажмите на ник выше, чтобы скопировать.</i>"
    )


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
    nickname_service: NicknameService,
    audit_service: AuditService,
    bot: Bot,
    group_chat_id: int,
) -> None:
    """Сохраняет имя, обновляет Telegram-титул, завершает настройку."""
    data = await state.get_data()
    name = data.get("pending_name", "")
    await state.clear()

    result = await nickname_service.change_nickname(
        actor_id=callback.from_user.id,
        target_id=callback.from_user.id,
        raw_nick=name,
        bot=bot,
        group_chat_id=group_chat_id,
        telegram_user=callback.from_user,
    )
    if not result["ok"]:
        await callback.message.answer(result["error"])
        return

    role = result["role"]
    full_nick = result["full_nick"]

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

    # Обновить Telegram Admin Title (только для администраторов)
    tg_error = result["tg_error"]

    await callback.message.edit_text(
        f"✅ <b>Профиль настроен!</b>\n\n"
        f"Добро пожаловать в Astrum, <b>{full_nick}</b>! 🎉"
    )
    await callback.message.answer(
        "⚜️ <b>AstrumManager</b>  •  Главное меню",
        reply_markup=MAIN_KEYBOARD,
    )

    # Отправить скопируемый ник
    await callback.message.answer(
        _copy_hint_text(full_nick),
        reply_markup=_copy_hint_kb(full_nick),
    )

    if tg_error:
        await callback.message.answer(tg_error)

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
    nickname_service: NicknameService,
    bot: Bot,
    group_chat_id: int,
) -> None:
    """Сохраняет новое имя, обновляет Telegram-титул, показывает профиль."""
    data = await state.get_data()
    new_name = data.get("pending_name", "")

    result = await nickname_service.change_nickname(
        actor_id=callback.from_user.id,
        target_id=callback.from_user.id,
        raw_nick=new_name,
        bot=bot,
        group_chat_id=group_chat_id,
        telegram_user=callback.from_user,
    )
    if not result["ok"]:
        await callback.message.answer(result["error"])
        return
    await state.clear()

    role = result["role"]
    new_full = result["full_nick"]
    old_name = result["old_nick"] or "?"

    logger.info(
        "Пользователь %s сменил имя: %r → %r",
        callback.from_user.id, old_name, new_name,
    )

    tg_error = result["tg_error"]

    stats = await user_service.get_profile_stats(callback.from_user.id)
    await callback.message.edit_text(
        f"✅ <b>Имя успешно изменено!</b>\n\n"
        + build_profile_card(new_name, role, stats),
        reply_markup=PROFILE_KB,
    )

    # Отправить скопируемый ник
    await callback.message.answer(
        _copy_hint_text(new_full),
        reply_markup=_copy_hint_kb(new_full),
    )

    if tg_error:
        await callback.message.answer(tg_error)

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


# ─────────────────────────────────────────────────────────────────────────────
# Информационный callback: как изменить имя в Telegram
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "nick:how_to_rename")
async def cb_how_to_rename(callback: CallbackQuery) -> None:
    """Объясняет, как вручную установить игровой ник в Telegram."""
    await callback.answer()
    await callback.message.answer(
        "📖 <b>Как изменить отображаемое имя в Telegram</b>\n\n"
        "Telegram не позволяет боту изменять ваше имя автоматически.\n"
        "Вы можете сделать это самостоятельно:\n\n"
        "<b>В приложении Telegram:</b>\n"
        "Настройки → Изменить профиль → Имя\n\n"
        "<b>Для администраторов клана</b> (Лидер / Старейшина / Дитя клана):\n"
        "Ваш Telegram-титул в чате группы обновляется автоматически "
        "при смене роли или имени. Пример: «✪ | Вадим».\n\n"
        "<b>Для Участников (◇ Участник):</b>\n"
        "Telegram не позволяет добавлять титул к обычным участникам — "
        "только администраторы получают кастомный титул рядом с именем.\n\n"
        "💡 Скопируйте ник из сообщения выше и вставьте его в поле «Имя» "
        "в настройках Telegram.",
    )
