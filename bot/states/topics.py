# -*- coding: utf-8 -*-
"""FSM-состояния для настройки веток форума."""
from aiogram.fsm.state import State, StatesGroup


class TopicSetup(StatesGroup):
    waiting_thread_id = State()
