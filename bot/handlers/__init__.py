# -*- coding: utf-8 -*-
"""Пакет обработчиков команд и сообщений."""
from bot.handlers import admin, audit, common, echo, group, menu, news, nick, setrole

__all__ = ["common", "echo", "menu", "admin", "setrole", "news", "nick", "group", "audit"]
