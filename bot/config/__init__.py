# -*- coding: utf-8 -*-
"""Пакет конфигурации — публичный API совместим со старым bot/config.py."""
from bot.config.settings import (
    DEFAULT_GROUP_CHAT_ID,
    DEFAULT_WEBHOOK_PATH,
    Config,
    FeatureFlags,
    ObservabilityConfig,
    RuntimeConfig,
    load_config,
)

__all__ = [
    "Config",
    "DEFAULT_GROUP_CHAT_ID",
    "DEFAULT_WEBHOOK_PATH",
    "FeatureFlags",
    "ObservabilityConfig",
    "RuntimeConfig",
    "load_config",
]
