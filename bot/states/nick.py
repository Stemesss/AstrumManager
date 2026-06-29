# -*- coding: utf-8 -*-
"""FSM-состояния для управления игровым ником."""
from aiogram.fsm.state import State, StatesGroup


class NickSetup(StatesGroup):
    """Первичная настройка профиля (при первом запуске)."""
    waiting_name    = State()   # ввод имени
    waiting_confirm = State()   # предпросмотр — ожидание подтверждения


class NickChange(StatesGroup):
    """Смена имени через раздел «👤 Мой профиль»."""
    waiting_name    = State()   # ввод нового имени
    waiting_confirm = State()   # предпросмотр — ожидание подтверждения
