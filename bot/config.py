import os
from dataclasses import dataclass


@dataclass
class Config:
    bot_token: str


def load_config() -> Config:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set")
    return Config(bot_token=token)
