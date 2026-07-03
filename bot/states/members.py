# -*- coding: utf-8 -*-
"""FSM-состояния для раздела «👥 Участники»."""
from aiogram.fsm.state import State, StatesGroup


class MemberDelete(StatesGroup):
    waiting_search = State()


class MemberNickEdit(StatesGroup):
    """Смена игрового ника участника администратором из карточки."""
    waiting_name = State()


class MemberWarnAdd(StatesGroup):
    """FSM выдачи предупреждения участнику администратором."""
    waiting_reason = State()


class MemberNoteAdd(StatesGroup):
    """FSM добавления заметки администрации об участнике."""
    waiting_text = State()
