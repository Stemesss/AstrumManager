# -*- coding: utf-8 -*-
"""Вспомогательные утилиты."""
from bot.utils.profile import SETTINGS_KB, build_profile_card
from bot.utils.roles import role_label
from bot.utils.text import greeting_by_hour, pluralize_days

__all__ = ["role_label", "pluralize_days", "greeting_by_hour",
           "build_profile_card", "SETTINGS_KB"]
