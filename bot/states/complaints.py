# -*- coding: utf-8 -*-
"""FSM-состояния для раздела «Жалобы и предложения»."""
from aiogram.fsm.state import State, StatesGroup


class ComplaintCreate(StatesGroup):
    waiting_title   = State()
    waiting_content = State()


class ComplaintReply(StatesGroup):
    waiting_reply = State()
