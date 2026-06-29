# -*- coding: utf-8 -*-
"""FSM-состояния для раздела «👥 Участники»."""
from aiogram.fsm.state import State, StatesGroup


class MemberDelete(StatesGroup):
    waiting_search = State()
