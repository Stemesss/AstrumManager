# -*- coding: utf-8 -*-
"""
Глобальный обработчик отмены FSM.

Перехватывает нажатие кнопки «❌ Отмена» в любом активном состоянии
и возвращает пользователя в главное меню. Должен регистрироваться
ПЕРВЫМ среди приватных роутеров, чтобы опережать FSM-обработчики.
"""
from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message

from bot.keyboards.main_menu import MAIN_KEYBOARD
from bot.keyboards.nav import CANCEL_TEXT

router = Router()


@router.message(F.text == CANCEL_TEXT, ~StateFilter(default_state))
async def handle_global_cancel(message: Message, state: FSMContext) -> None:
    """Отменяет любой активный FSM-сценарий и возвращает в главное меню."""
    await state.clear()
    await message.answer("❌ Действие отменено.", reply_markup=MAIN_KEYBOARD)
