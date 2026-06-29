# -*- coding: utf-8 -*-
"""Пакет конфигурации — публичный API совместим со старым bot/config.py."""
from bot.config.settings import Config, load_config

__all__ = ["Config", "load_config"]
