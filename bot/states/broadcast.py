# -*- coding: utf-8 -*-
"""FSM-мастер создания и отправки рассылок администрации."""
from aiogram.fsm.state import State, StatesGroup


class BroadcastWizard(StatesGroup):
    waiting_text             = State()
    preview                  = State()
    waiting_template_name    = State()
    waiting_schedule_datetime = State()
