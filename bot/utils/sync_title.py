# -*- coding: utf-8 -*-
"""
Синхронизация Telegram Admin Title с ролями Astrum.

Вызывается после смены роли в UserService.
Не выбрасывает исключения — при ошибке возвращает строку для показа администратору.
"""
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from bot.models.user import UserRole
from bot.utils.roles import ROLE_DISPLAY_ICONS

logger = logging.getLogger(__name__)

# Telegram Admin Title для каждой управляющей роли
ADMIN_TITLES: dict[UserRole, str] = {
    UserRole.LEADER:     "✪ Лидер",
    UserRole.CLAN_CHILD: "✦ Дитя клана",
    UserRole.ELDER:      "✧ Старейшина",
}


async def sync_admin_title(
    bot: Bot,
    chat_id: int,
    user_id: int,
    role: UserRole,
) -> str | None:
    """
    Синхронизирует Telegram Admin Title пользователя с его ролью Astrum.

    • LEADER / CLAN_CHILD / ELDER → промоут + установка кастомного титула.
    • MEMBER → снять административный статус (все права False).

    Возвращает None при успехе или строку с предупреждением для вывода администратору.
    """
    title = ADMIN_TITLES.get(role)  # None для MEMBER

    try:
        if title:
            # Минимальный промоут, необходимый для задания кастомного титула
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
            # Снимаем административный статус
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
        logger.warning("sync_admin_title: TelegramBadRequest для %s: %s", user_id, e)
        return f"⚠️ <b>Telegram-титул не синхронизирован:</b>\n{e}"

    except Exception as e:
        logger.warning("sync_admin_title: неожиданная ошибка для %s: %s", user_id, e)
        return f"⚠️ <b>Telegram-титул не синхронизирован:</b>\n{e}"

    return None


def tg_title_line(role: UserRole) -> str:
    """Возвращает строку для отображения в профиле (Telegram Admin Title или пусто)."""
    title = ADMIN_TITLES.get(role)
    if title:
        return f"🎖 <b>Telegram-титул:</b> {title}"
    return ""
