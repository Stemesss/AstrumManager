# -*- coding: utf-8 -*-
"""FSM-состояния для раздела «Журнал действий»."""
from aiogram.fsm.state import State, StatesGroup


class AuditSearch(StatesGroup):
    waiting_query = State()
