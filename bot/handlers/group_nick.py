# -*- coding: utf-8 -*-
"""
Команды управления никами прямо в групповом чате.

────────────────────────────────────────────────────────────────────────
ТЕХНИЧЕСКОЕ ПРИМЕЧАНИЕ (честный ответ на вопрос)
────────────────────────────────────────────────────────────────────────
Команды вида «+Ник», «!Ник», «!Назначить ник» в Telegram реализуются
через MTProto-юзерботы (Pyrogram / Telethon) — обычный пользовательский
аккаунт, запущенный как скрипт.

НО: ни Bot API, ни MTProto НЕ позволяют изменить first_name / username
другого пользователя. Такого API-метода в Telegram не существует.

Что эти команды делают в реальных юзерботах:
  1. Сохраняют ник в собственную БД (user_id → "Вадим").
  2. Используют ник при выводе списков и статистики.
  3. Для администраторов — устанавливают Admin Custom Title.
     (Это же умеет Bot API — setChatAdministratorCustomTitle.)

Вывод: юзербот добавляет только «слушать все сообщения без /команды»
и «отвечать на паттерн +Текст». Это реализуемо и через обычный Bot API,
если бот является администратором группы (тогда он видит все сообщения).

Данный файл реализует те же команды через aiogram (Bot API):
  +Имя            — назначить ник (ответ на сообщение → цель, иначе себе)
  !ник Имя        — то же самое (явная форма)
  !назначить ник  — назначить ник (только в ответ на сообщение)
  !удалить ник    — удалить ник участника (только для администраторов)
  -ник            — удалить собственный ник
  Ники            — список ников клана

Префикс «+» закреплён за никами (как у Iris). Префикс «!» используется
только для явных команд, чтобы обычные «!текст» сообщения в чате не
распознавались как попытка установить ник.
────────────────────────────────────────────────────────────────────────

Требования:
  • Бот должен быть администратором группы — иначе не получает
    обычные текстовые сообщения (privacy mode).
  • Или: отключить privacy mode через BotFather → /setprivacy → Disable.
"""
import logging
import re

from aiogram import Bot, F, Router
from aiogram.types import Message

from bot.models.audit import AuditAction
from bot.services.audit_service import AuditService
from bot.services.user_service import UserService
from bot.utils.nick_format import build_full_nick, validate_name
from bot.utils.sync_title import ADMIN_TITLES, sync_admin_title

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

logger = logging.getLogger(__name__)

# ─── Паттерны команд ─────────────────────────────────────────────────────────

# +Вадим  — краткая форма (префикс «+» закреплён за никами, как у Iris).
# Префикс «!» намеренно НЕ входит сюда, иначе любой «!текст» в чате
# распознавался бы как ник. Для «!» используются явные команды (!ник …).
_SHORT_NICK_RE = re.compile(r"^\+(\S.+)$", re.UNICODE)

# !ник Вадим  (с пробелом)
_NICK_CMD_RE = re.compile(r"^[!/]ник\s+(.+)$", re.IGNORECASE | re.UNICODE)

# !назначить ник Вадим  (только в ответ на сообщение)
_ASSIGN_CMD_RE = re.compile(r"^[!/]назначить\s+ник\s+(.+)$", re.IGNORECASE | re.UNICODE)

_ADMIN_BADGE = "🔰"   # значок в ответе при назначении ником другому


async def _is_group_admin(user_id: int, user_service: UserService) -> bool:
    """True если пользователь является администратором клана в системе бота."""
    return await user_service.is_admin(user_id)


async def _set_nick(
    bot: Bot,
    message: Message,
    target_id: int,
    target_name_tg: str,
    new_name: str,
    actor_id: int,
    user_service: UserService,
    audit_service: AuditService,
    group_chat_id: int,
    *,
    is_self: bool,
) -> None:
    """Общая логика сохранения нового ника + синхронизация Telegram-титула."""
    old_name = await user_service.get_game_nick(target_id) or "?"
    role = await user_service.get_role(target_id)
    actor_nick = await user_service.get_game_nick(actor_id) or str(actor_id)

    await user_service.set_game_nick(target_id, new_name)

    new_full = build_full_nick(new_name, role)
    old_full  = build_full_nick(old_name, role) if old_name != "?" else old_name

    await audit_service.log(
        user_id=actor_id,
        game_nick=actor_nick,
        role=await user_service.get_role(actor_id),
        action_type=AuditAction.MEMBER_NICK_CHANGE,
        description=(
            f"{old_full} → {new_full}"
            if is_self
            else f"Администратор назначил ник: {old_full} → {new_full}"
        ),
    )

    logger.info(
        "Ник изменён в группе: target=%s %r → %r (actor=%s)",
        target_id, old_name, new_name, actor_id,
    )

    # Обновить Telegram Admin Title для администраторов
    tg_error = None
    if role in ADMIN_TITLES:
        tg_error = await sync_admin_title(
            bot, group_chat_id, target_id, role, game_nick=new_name
        )

    mention = f'<a href="tg://user?id={target_id}">{target_name_tg}</a>'
    tg_note = f"\n<i>Telegram-титул: {old_full} → {new_full}</i>" if not tg_error else ""

    if is_self:
        text = (
            f"✅ Игровой ник обновлён!\n\n"
            f"👤 {mention}: <b>{new_full}</b>{tg_note}"
        )
    else:
        text = (
            f"{_ADMIN_BADGE} Ник назначен!\n\n"
            f"👤 {mention}: <b>{new_full}</b>{tg_note}"
        )

    await message.reply(text)
    if tg_error:
        await message.reply(tg_error)


async def _delete_nick(
    bot: Bot,
    message: Message,
    target_id: int,
    target_name_tg: str,
    actor_id: int,
    user_service: UserService,
    audit_service: AuditService,
    group_chat_id: int,
) -> None:
    """Удаляет ник участника (только для администраторов)."""
    old_name = await user_service.get_game_nick(target_id)
    role = await user_service.get_role(target_id)
    actor_nick = await user_service.get_game_nick(actor_id) or str(actor_id)

    if not old_name:
        await message.reply("⚠️ У этого участника ник не задан.")
        return

    old_full = build_full_nick(old_name, role)

    await user_service.set_game_nick(target_id, "")

    await audit_service.log(
        user_id=actor_id,
        game_nick=actor_nick,
        role=await user_service.get_role(actor_id),
        action_type=AuditAction.MEMBER_NICK_CHANGE,
        description=f"Администратор удалил ник: {old_full}",
    )

    logger.info(
        "Ник удалён в группе: target=%s ник=%r (actor=%s)",
        target_id, old_name, actor_id,
    )

    mention = f'<a href="tg://user?id={target_id}">{target_name_tg}</a>'
    await message.reply(
        f"🗑 Ник удалён.\n\n"
        f"👤 {mention}: <i>ник удалён</i>\n"
        f"<i>Был: {old_full}</i>"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Обработчики
# ─────────────────────────────────────────────────────────────────────────────

async def _handle_nick_assign(
    message: Message,
    raw_name: str,
    user_service: UserService,
    audit_service: AuditService,
    bot: Bot,
    group_chat_id: int,
) -> None:
    """Общий обработчик назначения ника (краткие и явные команды)."""
    if not message.from_user:
        return

    actor_id = message.from_user.id

    name, error = validate_name(raw_name)
    if error:
        await message.reply(error)
        return

    # Определяем цель: ответ на сообщение → автор ответа, иначе → сам
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user = message.reply_to_message.from_user
        # Назначать чужой ник — только администраторам
        if target_user.id != actor_id and not await _is_group_admin(actor_id, user_service):
            await message.reply(
                "⛔ Назначать ник другим участникам могут только администраторы."
            )
            return
        is_self = (target_user.id == actor_id)
    else:
        target_user = message.from_user
        is_self = True

    if target_user.is_bot:
        await message.reply("⚠️ Нельзя назначить игровой ник боту.")
        return

    # Гарантируем, что цель есть в БД — иначе set_game_nick (UPDATE) не сохранит ник
    await user_service.get_or_create(target_user)

    # Уникальность ника в клане (как у Iris: нет повторяющихся ников)
    if await user_service.is_nick_taken(name, exclude_id=target_user.id):
        await message.reply(
            f"❌ Ник «{name}» уже занят другим участником клана.\n"
            "Выберите другой ник."
        )
        return

    await _set_nick(
        bot, message,
        target_id=target_user.id,
        target_name_tg=target_user.full_name,
        new_name=name,
        actor_id=actor_id,
        user_service=user_service,
        audit_service=audit_service,
        group_chat_id=group_chat_id,
        is_self=is_self,
    )


@router.message(F.text.regexp(r"^\+\S.+"))
async def handle_short_nick(
    message: Message,
    user_service: UserService,
    audit_service: AuditService,
    bot: Bot,
    group_chat_id: int,
) -> None:
    """Обработчик краткой формы: «+Вадим» (префикс «+» закреплён за никами)."""
    if not message.text:
        return

    m = _SHORT_NICK_RE.match(message.text)
    if not m:
        return

    raw_name = m.group(1).strip()
    await _handle_nick_assign(
        message, raw_name, user_service, audit_service, bot, group_chat_id
    )


@router.message(F.text.regexp(r"(?i)^[!/]ник\s+\S"))
async def handle_nick_cmd(
    message: Message,
    user_service: UserService,
    audit_service: AuditService,
    bot: Bot,
    group_chat_id: int,
) -> None:
    """Обработчик: «!ник Вадим» или «/ник Вадим»."""
    if not message.text:
        return
    m = _NICK_CMD_RE.match(message.text)
    if not m:
        return
    raw_name = m.group(1).strip()
    await _handle_nick_assign(
        message, raw_name, user_service, audit_service, bot, group_chat_id
    )


@router.message(F.text.regexp(r"(?i)^[!/]назначить\s+ник\s+\S"))
async def handle_assign_nick_cmd(
    message: Message,
    user_service: UserService,
    audit_service: AuditService,
    bot: Bot,
    group_chat_id: int,
) -> None:
    """Обработчик: «!назначить ник Вадим» — строго в ответ на сообщение."""
    if not message.text:
        return
    m = _ASSIGN_CMD_RE.match(message.text)
    if not m:
        return
    if not message.reply_to_message:
        await message.reply(
            "⚠️ Команда «!назначить ник» должна использоваться\n"
            "в ответ на сообщение участника."
        )
        return
    raw_name = m.group(1).strip()
    await _handle_nick_assign(
        message, raw_name, user_service, audit_service, bot, group_chat_id
    )


@router.message(F.text.regexp(r"(?i)^[!/]удалить\s+ник$"))
async def handle_delete_nick_cmd(
    message: Message,
    user_service: UserService,
    audit_service: AuditService,
    bot: Bot,
    group_chat_id: int,
) -> None:
    """Обработчик: «!удалить ник» — только для администраторов, в ответ."""
    if not message.from_user:
        return

    if not await _is_group_admin(message.from_user.id, user_service):
        await message.reply("⛔ Удалять ники могут только администраторы.")
        return

    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.reply(
            "⚠️ Используйте команду в ответ на сообщение участника."
        )
        return

    target = message.reply_to_message.from_user

    await _delete_nick(
        bot, message,
        target_id=target.id,
        target_name_tg=target.full_name,
        actor_id=message.from_user.id,
        user_service=user_service,
        audit_service=audit_service,
        group_chat_id=group_chat_id,
    )


@router.message(F.text.regexp(r"^-ник$") | F.text.regexp(r"(?i)^[!/]удалить\s+свой\s+ник$"))
async def handle_remove_own_nick(
    message: Message,
    user_service: UserService,
    audit_service: AuditService,
    bot: Bot,
    group_chat_id: int,
) -> None:
    """Обработчик: «-ник» — удалить собственный ник (краткая форма, как у Iris)."""
    if not message.from_user:
        return
    await _delete_nick(
        bot, message,
        target_id=message.from_user.id,
        target_name_tg=message.from_user.full_name,
        actor_id=message.from_user.id,
        user_service=user_service,
        audit_service=audit_service,
        group_chat_id=group_chat_id,
    )


@router.message(F.text.regexp(r"(?i)^(ники|[!/]ники)$"))
async def handle_list_nicks(
    message: Message,
    user_service: UserService,
) -> None:
    """Обработчик: «Ники» — список ников участников клана (как у Iris)."""
    items = await user_service.list_nicks()
    if not items:
        await message.reply("📭 В клане пока нет установленных ников.")
        return

    lines = []
    for tg_id, nick, role in items[:50]:
        full = build_full_nick(nick, role)
        lines.append(
            f'• <a href="tg://user?id={tg_id}">{full}</a>'
        )

    total = len(items)
    header = f"🏷 <b>Ники клана</b> ({total})\n\n"
    footer = "" if total <= 50 else f"\n\n<i>Показаны первые 50 из {total}.</i>"
    await message.reply(header + "\n".join(lines) + footer)


@router.message(F.text.regexp(r"(?i)^[!/](?:ник|назначить\s+ник|удалить\s+ник)$"))
async def handle_nick_help(message: Message) -> None:
    """Показывает подсказку при неправильном использовании команд."""
    await message.reply(
        "📋 <b>Команды никнеймов в группе</b>\n\n"
        "<b>Установить свой ник:</b>\n"
        "<code>+Вадим</code>  или  <code>!ник Вадим</code>\n\n"
        "<b>Удалить свой ник:</b>\n"
        "<code>-ник</code>\n\n"
        "<b>Список ников клана:</b>\n"
        "<code>Ники</code>\n\n"
        "<b>Назначить ник участнику</b> (ответ на сообщение, только администратор):\n"
        "<code>+Вадим</code>  или  <code>!назначить ник Вадим</code>\n\n"
        "<b>Удалить ник участника</b> (ответ на сообщение, только администратор):\n"
        "<code>!удалить ник</code>\n\n"
        "<i>Правила имени: от 3 до 20 символов, без эмодзи и спецсимволов.\n"
        "Повторяющиеся ники в клане запрещены.\n"
        "Префикс «+» — для ников; «!» — для команд.</i>"
    )
