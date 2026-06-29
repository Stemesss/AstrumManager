# -*- coding: utf-8 -*-
"""FSM-состояния для управления игровым ником."""
from aiogram.fsm.state import State, StatesGroup


class NickSetup(StatesGroup):
    """Первичная установка ника (при первом запуске)."""
    waiting_nick = State()


class NickChange(StatesGroup):
    """Смена ника через настройки профиля."""
    waiting_nick = State()
