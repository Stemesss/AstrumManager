# -*- coding: utf-8 -*-
"""
Глобальный обработчик отмены FSM.

Перехватывает нажатие кнопки «❌ Отмена» в любом активном состоянии.

  • Смена игрового ника (NickChange) — возвращает пользователя в раздел
    «👤 Мой профиль» без изменения ника.
  • Все остальные FSM-состояния — возвращает в главное меню.

Должен регистрироваться ПЕРВЫМ среди приватных роутеров, чтобы опережать
FSM-обработчики других модулей.
"""
from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message, ReplyKeyboardRemove

from bot.keyboards.main_menu import MAIN_KEYBOARD
from bot.keyboards.nav import CANCEL_TEXT, reset_to_main_menu
from bot.services.user_service import UserService
from bot.states.nick import NickChange
from bot.utils.profile import PROFILE_KB, build_profile_card

router = Router()


@router.message(
    F.text == CANCEL_TEXT,
    StateFilter(NickChange.waiting_name, NickChange.waiting_confirm),
)
async def handle_nick_change_cancel(
    message: Message,
    state: FSMContext,
    user_service: UserService,
) -> None:
    """Отменяет смену игрового ника и возвращает в раздел «👤 Мой профиль»."""
    await state.clear()

    user  = await user_service.get_or_create(message.from_user)
    role  = await user_service.get_role(message.from_user.id)
    stats = await user_service.get_profile_stats(message.from_user.id)
    name  = user.game_nick or ""

    # Гарантированно убираем текущую Reply-клавиатуру перед восстановлением главного меню
    await message.answer("❌ Смена ника отменена.", reply_markup=ReplyKeyboardRemove())
    await message.answer(
        "⚜️ <b>AstrumManager</b>  •  Главное меню",
        reply_markup=MAIN_KEYBOARD,
    )
    await message.answer(
        build_profile_card(name, role, stats),
        reply_markup=PROFILE_KB,
    )


@router.message(F.text == CANCEL_TEXT, ~StateFilter(default_state))
async def handle_global_cancel(message: Message, state: FSMContext) -> None:
    """Отменяет любой активный FSM-сценарий и возвращает в главное меню."""
    await state.clear()
    await reset_to_main_menu(message, "❌ Действие отменено.")


@router.message(F.text == CANCEL_TEXT, StateFilter(default_state))
async def handle_cancel_outside_fsm(message: Message) -> None:
    """
    «❌ Отмена» нажата вне активного FSM-сценария.

    Просто убирает клавиатуру и показывает главное меню — без сообщения
    «Я не понял это сообщение», которое выдал бы echo.router по умолчанию.
    """
    await reset_to_main_menu(message, "❌ Нет активного действия для отмены.")
