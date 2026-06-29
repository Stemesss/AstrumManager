# -*- coding: utf-8 -*-
"""FSM-состояния для управления новостями."""
from aiogram.fsm.state import State, StatesGroup


class NewsCreate(StatesGroup):
    """Состояния создания новости."""
    waiting_title = State()    # Ждём заголовок
    waiting_content = State()  # Ждём текст


class NewsEdit(StatesGroup):
    """Состояния редактирования новости."""
    waiting_title = State()    # Ждём новый заголовок (news_id в data)
    waiting_content = State()  # Ждём новый текст    (news_id в data)
