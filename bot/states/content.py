# -*- coding: utf-8 -*-
"""FSM-состояния для редактирования контента (гайды, события, скриншоты)."""
from aiogram.fsm.state import State, StatesGroup


class ContentEdit(StatesGroup):
    """Состояния редактирования контента."""
    waiting_title   = State()
    waiting_content = State()
