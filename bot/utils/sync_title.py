# -*- coding: utf-8 -*-
"""
Синхронизация Telegram Admin Title с ролями Astrum.

─────────────────────────────────────────────────────────────────────────
ОГРАНИЧЕНИЕ TELEGRAM (важно для понимания архитектуры)
─────────────────────────────────────────────────────────────────────────
Telegram Bot API и MTProto не позволяют изменять отображаемое имя
(first_name / last_name / username) другого пользователя.

Что ДОСТУПНО через Bot API:
  • setChatAdministratorCustomTitle — кастомный «титул» рядом с именем
    для пользователей со статусом администратора в группе.
    Ограничения: только для админов; без эмодзи; максимум 16 символов.

Что НЕДОСТУПНО:
  • Изменить first_name / last_name / username любого пользователя.
  • Через MTProto/Userbot тоже нельзя — метода не существует.

Следствие для AstrumManager:
  • Все роли (включая Участника) — получают статус администратора
    с минимальными правами и кастомный титул.
─────────────────────────────────────────────────────────────────────────

Формат кастомного Telegram-титула:
  ✪ {game_nick} — Лидер
  ✦ {game_nick} — Дитя клана
  ✧ {game_nick} — Старейшина
  ◇ {game_nick} — Участник

  Если ник не помещается в 16 символов — усекается.
  Если даже 1 символ ника не помещается — {symbol} {label} (без ника).

Источник имени — ТОЛЬКО game_nick из БД. Telegram username,
first_name и другие поля Telegram никогда не используются.

Вызывается:
  • После смены роли участника (handlers/members.py, handlers/setrole.py).
  • После смены ника участника (handlers/nick.py, handlers/group_nick.py).
"""
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from bot.models.user import UserRole

logger = logging.getLogger(__name__)

# Символы для каждой роли (используются в Telegram Admin Title)
_ROLE_SYMBOLS: dict[UserRole, str] = {
    UserRole.LEADER:     "✪",
    UserRole.CLAN_CHILD: "✦",
    UserRole.ELDER:      "✧",
    UserRole.MEMBER:     "◇",
}

_SEP = " — "
_MAX_LEN = 16

# Кастомные титулы без ника (фоллбэк + источник истины для отображения в UI)
# Все 4 роли поддерживаются. Используется в handlers для показа установленного титула.
ADMIN_TITLES: dict[UserRole, str] = {
    UserRole.LEADER:     "✪ Лидер",
    UserRole.CLAN_CHILD: "✦ Дитя клана",
    UserRole.ELDER:      "✧ Старейшина",
    UserRole.MEMBER:     "◇ Участник",
}


def build_admin_title(role: UserRole, game_nick: str | None = None) -> str:
    """Строит строку кастомного Telegram-титула (≤ 16 символов).

    Формат: «{symbol} {game_nick} — {role_label}»
    Источник имени — только game_nick (Telegram username не используется).

    Примеры (game_nick="Вадим"):
      LEADER     → "✪ Вадим — Лидер"      (15 символов ✓)
      CLAN_CHILD → "✦ В — Дитя клана"     (16 символов, ник усечён до 1)
      ELDER      → "✧ В — Старейшина"     (16 символов, ник усечён до 1)
      MEMBER     → "◇ Вад — Участник"     (16 символов, ник усечён до 3)

    Если ник не помещается даже в 1 символ — «{symbol} {label}» без ника:
      CLAN_CHILD (без ника) → "✦ Дитя клана"   (12 символов ✓)
    """
    symbol = _ROLE_SYMBOLS.get(role)
    if not symbol:
        return ""

    label = role.value  # "Лидер" / "Дитя клана" / "Старейшина" / "Участник"

    if not game_nick:
        return f"{symbol} {label}"[:_MAX_LEN]

    prefix = f"{symbol} "
    suffix = f"{_SEP}{label}"
    full = f"{prefix}{game_nick}{suffix}"

    if len(full) <= _MAX_LEN:
        return full

    # Усекаем ник чтобы вписаться в 16 символов
    max_nick_len = _MAX_LEN - len(prefix) - len(suffix)
    if max_nick_len >= 1:
        return f"{prefix}{game_nick[:max_nick_len]}{suffix}"

    # Ник вообще не помещается — только symbol + label
    return f"{symbol} {label}"[:_MAX_LEN]


async def sync_admin_title(
    bot: Bot,
    chat_id: int,
    user_id: int,
    role: UserRole,
    game_nick: str | None = None,
) -> str | None:
    """Синхронизирует Telegram Admin Title пользователя с его ролью и ником.

    Все роли (LEADER / CLAN_CHILD / ELDER / MEMBER) получают статус
    администратора с минимальными правами и кастомный титул в формате:
      «{symbol} {game_nick} — {role_label}»

    Источник имени — только game_nick. Telegram username не используется.

    Возвращает None при успехе или строку предупреждения для вывода администратору.
    """
    title = build_admin_title(role, game_nick)

    try:
        await bot.promote_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            can_manage_chat=True,
            can_delete_messages=False,
            can_manage_video_chats=False,
            can_restrict_members=False,
            can_promote_members=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False,
            is_anonymous=False,
        )
        await bot.set_chat_administrator_custom_title(
            chat_id=chat_id,
            user_id=user_id,
            custom_title=title,
        )
        logger.info(
            "Telegram-титул установлен: user=%s title=%r chat=%s",
            user_id, title, chat_id,
        )

    except TelegramForbiddenError:
        logger.warning(
            "sync_admin_title: бот не имеет прав promote_members в чате %s", chat_id
        )
        return (
            "⚠️ <b>Telegram-титул не синхронизирован.</b>\n"
            "Бот не имеет права назначать администраторов в группе.\n"
            "Выдайте боту право «Добавление администраторов»."
        )

    except TelegramBadRequest as e:
        err = str(e).lower()
        if "user_not_participant" in err or "user not found" in err or "participant" in err:
            logger.info(
                "sync_admin_title: user %s не является участником чата %s", user_id, chat_id
            )
            return (
                "⚠️ <b>Telegram-титул не синхронизирован.</b>\n"
                "Пользователь не найден в группе."
            )
        if "not enough rights" in err or "rights" in err:
            return (
                "⚠️ <b>Telegram-титул не синхронизирован.</b>\n"
                "Недостаточно прав для изменения администраторов."
            )
        if "can't remove chat owner" in err or "owner" in err:
            return (
                "⚠️ <b>Telegram-титул не синхронизирован.</b>\n"
                "Нельзя изменить статус владельца группы через API."
            )
        if "emoji" in err or "special" in err:
            return (
                "⚠️ <b>Telegram-титул не синхронизирован.</b>\n"
                "Telegram запрещает эмодзи в кастомных титулах."
            )
        logger.warning("sync_admin_title: TelegramBadRequest для %s: %s", user_id, e)
        return f"⚠️ <b>Telegram-титул не синхронизирован:</b>\n{e}"

    except Exception as e:
        logger.warning("sync_admin_title: неожиданная ошибка для %s: %s", user_id, e)
        return f"⚠️ <b>Telegram-титул не синхронизирован:</b>\n{e}"

    return None


def tg_title_line(role: UserRole, game_nick: str | None = None) -> str:
    """Строка для отображения в профиле (Telegram Admin Title)."""
    title = build_admin_title(role, game_nick)
    if title:
        return f"🎖 <b>Telegram-титул в чате:</b> <code>{title}</code>"
    return ""
