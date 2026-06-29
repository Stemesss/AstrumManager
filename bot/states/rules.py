# -*- coding: utf-8 -*-
"""FSM-состояния для раздела «Правила»."""
from aiogram.fsm.state import State, StatesGroup


class RulesEdit(StatesGroup):
    waiting_content = State()
