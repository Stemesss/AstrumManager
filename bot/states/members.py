# -*- coding: utf-8 -*-
"""FSM-состояния для раздела «👥 Участники»."""
from aiogram.fsm.state import State, StatesGroup


class MemberDelete(StatesGroup):
    waiting_search = State()


class MemberNickEdit(StatesGroup):
    """Смена игрового ника участника администратором из карточки."""
    waiting_name = State()
