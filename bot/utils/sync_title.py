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
    Ограничения: только для админов; максимум 16 символов.

Что НЕДОСТУПНО:
  • Изменить first_name / last_name / username любого пользователя.
  • Через MTProto/Userbot тоже нельзя — метода не существует.

Следствие для AstrumManager:
  • Участники со статусом «Участник» (UserRole.MEMBER) — отображаемое
    имя в чате изменить нельзя. Бот присылает им форматированный ник
    для самостоятельной установки в настройках Telegram.
  • Администраторы (Лидер / Старейшина / Дитя клана) — кастомный титул
    устанавливается автоматически и виден рядом с именем в чате.
─────────────────────────────────────────────────────────────────────────

Вызывается:
  • После смены роли участника (handlers/members.py cb_mem_set).
  • После смены ника участника (handlers/nick.py cb_*_confirm).
"""
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from bot.models.user import UserRole

logger = logging.getLogger(__name__)

# Символы роли для кастомного титула и внутреннего отображения
ADMIN_TITLES: dict[UserRole, str] = {
    UserRole.LEADER:     "✪",
    UserRole.ELDER:      "✧",
    UserRole.CLAN_CHILD: "✦",
}

_SEP = " | "
_MAX_LEN = 16


def build_admin_title(role: UserRole, game_nick: str | None = None) -> str:
    """Строит строку кастомного Telegram-титула (≤ 16 символов).

    Если game_nick указан и помещается — включает имя: «✪ | Вадим».
    Иначе возвращает базовый титул: «✪».
    """
    base = ADMIN_TITLES.get(role)
    if not base:
        return ""  # MEMBER — без титула

    if not game_nick:
        return base

    candidate = f"{base}{_SEP}{game_nick}"
    if len(candidate) <= _MAX_LEN:
        return candidate

    # Обрезаем имя, чтобы вписаться в 16 символов
    max_nick = _MAX_LEN - len(base) - len(_SEP)
    if max_nick >= 2:
        return f"{base}{_SEP}{game_nick[:max_nick]}"

    return base


async def sync_admin_title(
    bot: Bot,
    chat_id: int,
    user_id: int,
    role: UserRole,
    game_nick: str | None = None,
) -> str | None:
    """Синхронизирует Telegram Admin Title пользователя с его ролью и ником.

    • LEADER / ELDER / CLAN_CHILD → промоут + кастомный титул с именем.
    • MEMBER → снять административный статус.

    Возвращает None при успехе или строку предупреждения для вывода администратору.

    Пример кастомного титула:
      role=LEADER, game_nick="Вадим" → «✪ | Вадим» (видно рядом с именем в чате)
    """
    title = build_admin_title(role, game_nick)

    try:
        if title:
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
        else:
            await bot.promote_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                can_manage_chat=False,
                can_delete_messages=False,
                can_manage_video_chats=False,
                can_restrict_members=False,
                can_promote_members=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False,
                is_anonymous=False,
            )
            logger.info(
                "Telegram-титул снят (понижен до участника): user=%s chat=%s",
                user_id, chat_id,
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
    """Строка для отображения в профиле (Telegram Admin Title или пусто)."""
    title = build_admin_title(role, game_nick)
    if title:
        return f"🎖 <b>Telegram-титул в чате:</b> <code>{title}</code>"
    return ""
