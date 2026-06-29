# -*- coding: utf-8 -*-
"""Загрузка конфигурации из переменных окружения."""
import os
from dataclasses import dataclass, field


@dataclass
class Config:
    bot_token: str                          # Токен Telegram-бота
    db_path: str = field(default="data/astrum.db")  # Путь к файлу SQLite


def load_config() -> Config:
    """Загружает конфигурацию из переменных окружения."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError(
            "Переменная окружения TELEGRAM_BOT_TOKEN не задана. "
            "Получите токен у @BotFather и добавьте его в секреты проекта."
        )
    db_path = os.getenv("DB_PATH", "data/astrum.db")
    return Config(bot_token=token, db_path=db_path)
