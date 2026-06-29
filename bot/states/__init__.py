# -*- coding: utf-8 -*-
"""Пакет FSM-состояний."""
from bot.states.news import NewsCreate, NewsEdit
from bot.states.nick import NickChange, NickSetup

__all__ = ["NewsCreate", "NewsEdit", "NickSetup", "NickChange"]
