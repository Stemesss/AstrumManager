# -*- coding: utf-8 -*-
"""Единый FSM-мастер создания публикаций (новости, события, гайды, скриншоты)."""
from aiogram.fsm.state import State, StatesGroup


class PublishWizard(StatesGroup):
    waiting_title       = State()
    waiting_content     = State()
    waiting_attachments = State()  # Шаг 3: сбор вложений (необязательный)
    preview             = State()
