# -*- coding: utf-8 -*-
"""
Форматирование игрового ника участника клана.

Формат: <Символ роли> <Имя>
Пример: ✪ Stemes, ✦ Dragon, ✧ Shadow, ◇ Player

Символы соответствуют единой схеме ролей всего проекта
(см. bot.utils.roles.ROLE_DISPLAY_ICONS):
  ✪ — Лидер
  ✦ — Дитя клана
  ✧ — Старейшина
  ◇ — Участник

Публичный API:
  build_full_nick(name, role) → "✪ Stemes"
  validate_name(text)        → (cleaned_name | None, error_msg | None)
"""
import re
import unicodedata

from bot.models.user import UserRole
from bot.utils.roles import ROLE_DISPLAY_ICONS

NAME_MIN = 3
NAME_MAX = 20

_ALLOWED_RE = re.compile(r"^[\w\s\-]+$", re.UNICODE)


def build_full_nick(name: str, role: UserRole) -> str:
    """Строит отображаемый ник по имени и роли.

    Пример: build_full_nick("Stemes", UserRole.LEADER) → "✪ Stemes"
    """
    symbol = ROLE_DISPLAY_ICONS.get(role, "◇")
    return f"{symbol} {name}"


def _has_emoji(text: str) -> bool:
    """True если строка содержит эмодзи или декоративные спецсимволы."""
    for char in text:
        cp = ord(char)
        cat = unicodedata.category(char)
        if (
            cat in ("So", "Sm", "Sk")
            or 0x1F000 <= cp <= 0x1FFFF
            or 0x2600 <= cp <= 0x27BF
            or 0xFE00 <= cp <= 0xFE0F
        ):
            return True
    return False


def validate_name(text: str) -> tuple[str | None, str | None]:
    """Валидирует введённое пользователем имя.

    Возвращает (cleaned_name, None) при успехе
    или (None, error_message) при ошибке.

    Правила:
      • от 3 до 20 символов (после strip)
      • только буквы, цифры, пробел, дефис
      • без эмодзи и декоративных спецсимволов
    """
    name = text.strip()
    if len(name) < NAME_MIN or len(name) > NAME_MAX:
        return None, (
            f"⚠️ Имя должно содержать от <b>{NAME_MIN}</b> до <b>{NAME_MAX}</b> символов.\n"
            "Попробуй ещё раз:"
        )
    if _has_emoji(name):
        return None, "⚠️ Имя не должно содержать эмодзи.\nПопробуй ещё раз:"
    if not _ALLOWED_RE.match(name):
        return None, (
            "⚠️ Имя может содержать только буквы, цифры, пробел и дефис.\n"
            "Попробуй ещё раз:"
        )
    return name, None
