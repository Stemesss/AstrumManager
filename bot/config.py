# -*- coding: utf-8 -*-
import os
from dataclasses import dataclass


@dataclass
class Config:
    bot_token: str  # Токен Telegram-бота


def load_config() -> Config:
    """Загружает конфигурацию из переменных окружения."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError(
            "Переменная окружения TELEGRAM_BOT_TOKEN не задана. "
            "Получите токен у @BotFather и добавьте его в секреты проекта."
        )
    return Config(bot_token=token)
