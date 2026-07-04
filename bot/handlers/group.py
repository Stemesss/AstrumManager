# -*- coding: utf-8 -*-
"""
Обработчики для групп и супергрупп.

Все личные функции бота работают только в личных сообщениях.
Группа получает лишь ограниченный набор команд сообщества:
  - /start → направить пользователя в личный чат;
  - приветствие новых участников;
  - публикация новостей / событий в чат (через PublishWizard);
  - начисление очков активности за сообщения (текст +1, медиа +2).
"""
import logging

from aiogram import Bot, F, Router
from aiogram.enums import ContentType
from aiogram.filters import CommandStart
from aiogram.types import ChatMemberUpdated, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.models.audit import AuditAction
from bot.services.audit_service import AuditService
from bot.services.topic_service import TopicService
from bot.services.user_service import UserService

router = Router()
logger = logging.getLogger(__name__)

# Все обработчики этого роутера работают ТОЛЬКО в группах и супергруппах.
router.message.filter(F.chat.type.in_({"group", "supergroup"}))
router.chat_member.filter(F.chat.type.in_({"group", "supergroup"}))


# ─────────────────────────────────────────────────────────────────────────────
# /start в группе — перенаправление в личный чат
# ─────────────────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def group_start(message: Message, bot_username: str) -> None:
    """
    Отвечает на /start в группе: просит открыть личный чат с ботом.
    Кнопка-ссылка открывает личный чат с @bot_username.
    """
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="💬 Открыть AstrumManager",
            url=f"https://t.me/{bot_username}",
        )
    ]])
    await message.answer(
        "⚜️ <b>AstrumManager</b>\n\n"
        "👋 Для использования откройте личный чат с ботом.\n\n"
        "Все функции доступны только в личных сообщениях.",
        reply_markup=kb,
    )
    logger.info(
        "Пользователь %s вызвал /start в группе %s — перенаправлен в ЛС",
        message.from_user.id if message.from_user else "?",
        message.chat.id,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Приветствие новых участников → ветка 👋 Приветствие
# ─────────────────────────────────────────────────────────────────────────────

@router.chat_member()
async def handle_new_member(
    event: ChatMemberUpdated,
    bot: Bot,
    topic_service: TopicService,
    user_service: UserService,
    bot_username: str,
) -> None:
    """
    Публикует приветствие в ветку «👋 Приветствие» при вступлении участника.
    Если ветка не настроена — отправляет в основной чат.
    Игнорирует выходы и другие изменения статуса.
    """
    logger.info(
        "NEW MEMBER EVENT RECEIVED — chat=%s old=%s new=%s",
        event.chat.id,
        event.old_chat_member.status,
        event.new_chat_member.status,
    )
    old = event.old_chat_member.status
    new = event.new_chat_member.status

    # Только вступление: left/kicked → member/restricted/administrator/creator
    joined = old in ("left", "kicked") and new in (
        "member", "restricted", "administrator", "creator"
    )
    if not joined:
        return

    # Публикуем только в нашей группе (chat_id из конфига)
    if event.chat.id != topic_service.chat_id:
        return

    user = event.new_chat_member.user
    if user.is_bot:
        return

    # Заводим минимальную запись в БД сразу при вступлении в группу, чтобы
    # раздел «Участники» мог показать пользователя как «🆕 Не зарегистрирован»
    # ещё до того, как он запустит бота и задаст игровой ник.
    try:
        await user_service.get_or_create(user)
    except Exception:
        logger.exception("Не удалось создать запись участника %s при вступлении в группу", user.id)

    mention = f'<a href="tg://user?id={user.id}">{user.full_name}</a>'
    text = (
        f"👋 <b>Добро пожаловать в Astrum!</b> {mention}\n\n"
        "🌟 Рады видеть тебя в нашем сообществе!\n\n"
        "🚀 <b>Первый шаг</b>\n\n"
        "Нажми кнопку <b>«🤖 Запустить AstrumManager»</b> под этим сообщением.\n\n"
        "После запуска бот поможет:\n"
        "✅ зарегистрировать игровой ник\n"
        "✅ получить доступ ко всем функциям\n"
        "✅ отслеживать свою статистику\n"
        "✅ пользоваться сервисами клана\n\n"
        "📌 <b>После регистрации</b>\n\n"
        "📖 Ознакомься с разделом «✅ Правила».\n"
        "💬 Представься участникам в общем чате.\n"
        "🎮 Принимай участие в событиях клана.\n\n"
        "📚 <b>Разделы сообщества</b>\n\n"
        "📰 Новости — важные объявления клана\n"
        "📅 События — мероприятия и активности\n"
        "👥 Участники — список членов клана\n"
        "📊 Статистика — активность и рейтинг"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🤖 Запустить AstrumManager",
            url=f"https://t.me/{bot_username}?start=welcome",
        )
    ]])
    ok = await topic_service.publish(bot, "welcome", text, reply_markup=kb)
    if ok:
        logger.info(
            "Приветствие для %s (%s) опубликовано в группе %s",
            user.full_name, user.id, event.chat.id,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Начисление очков активности за сообщения в группе
# ─────────────────────────────────────────────────────────────────────────────

_MEDIA_TYPES = frozenset({
    ContentType.PHOTO,
    ContentType.VIDEO,
    ContentType.VOICE,
    ContentType.VIDEO_NOTE,
    ContentType.DOCUMENT,
    ContentType.ANIMATION,
})

_IGNORED_TYPES = frozenset({
    ContentType.STICKER,
    ContentType.NEW_CHAT_MEMBERS,
    ContentType.LEFT_CHAT_MEMBER,
    ContentType.NEW_CHAT_TITLE,
    ContentType.NEW_CHAT_PHOTO,
    ContentType.DELETE_CHAT_PHOTO,
    ContentType.GROUP_CHAT_CREATED,
    ContentType.PINNED_MESSAGE,
    ContentType.FORUM_TOPIC_CREATED,
    ContentType.FORUM_TOPIC_CLOSED,
    ContentType.FORUM_TOPIC_REOPENED,
    ContentType.FORUM_TOPIC_EDITED,
})


@router.message()
async def handle_group_message_activity(
    message: Message,
    user_service: UserService,
    audit_service: AuditService,
    group_chat_id: int,
) -> None:
    """Начисляет очки активности за сообщения участников в клановой группе.

    💬 Текст      → +1 очко  (msg_text)
    🖼 Медиа       → +2 очка  (msg_media)
    🚫 Игнорирует: стикеры, реакции, системные сообщения, ботов.
    """
    if message.chat.id != group_chat_id:
        return

    if not message.from_user or message.from_user.is_bot:
        return

    ct = message.content_type
    if ct in _IGNORED_TYPES:
        return

    if ct in _MEDIA_TYPES:
        action_type = AuditAction.MSG_MEDIA
        desc = "медиа-сообщение в группе (+2)"
    elif ct == ContentType.TEXT:
        action_type = AuditAction.MSG_TEXT
        desc = "текстовое сообщение в группе (+1)"
    else:
        return

    user_id = message.from_user.id

    try:
        from bot.models.user import UserRole
        game_nick = await user_service.get_game_nick(user_id)
        if not game_nick:
            return
        role = await user_service.get_role(user_id)
        await audit_service.log(
            user_id=user_id,
            game_nick=game_nick,
            role=role,
            action_type=action_type,
            description=desc,
        )
    except Exception:
        logger.debug("Не удалось начислить очки активности для %s", user_id)
