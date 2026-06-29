# -*- coding: utf-8 -*-
"""Обработчик команды /setrole — назначение роли с учётом иерархии прав."""
import logging

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.models.audit import AuditAction
from bot.models.user import UserRole
from bot.services.audit_service import AuditService
from bot.services.user_service import UserService
from bot.utils.roles import assignable_roles, can_assign, role_label
from bot.utils.sync_title import ADMIN_TITLES, sync_admin_title

router = Router()
logger = logging.getLogger(__name__)

# Суперпользователь — полный доступ независимо от роли в БД
_SUPERUSER_ID = 8490615925


def _usage_for(actor_role: UserRole) -> str:
    """Возвращает подсказку /setrole с ролями, доступными данному актору."""
    allowed = assignable_roles(actor_role)
    roles_list = "\n".join(f"• {role_label(r)}" for r in allowed) if allowed else "  (нет доступных ролей)"
    return (
        "Использование: /setrole &lt;telegram_id&gt; &lt;роль&gt;\n\n"
        f"Роли, которые вы можете назначать ({role_label(actor_role)}):\n"
        f"{roles_list}"
    )


@router.message(Command("setrole"))
async def handle_setrole(
    message: Message,
    bot: Bot,
    user_service: UserService,
    audit_service: AuditService,
    owner_id: int | None,
    group_chat_id: int,
) -> None:
    """Назначает роль пользователю с проверкой иерархии прав."""
    if not message.from_user:
        return

    actor_id   = message.from_user.id
    is_superuser = actor_id == _SUPERUSER_ID or (owner_id is not None and actor_id == owner_id)

    # Получаем роль актора
    actor_role = await user_service.get_role(actor_id)

    # Суперпользователь и владелец бота всегда получают права Лидера
    effective_role = UserRole.LEADER if is_superuser else actor_role

    # Проверка: есть ли у актора право назначать хоть кому-то что-то
    if not assignable_roles(effective_role):
        await message.answer("🔒 У вас нет прав для управления ролями.")
        return

    # Разбор аргументов
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(_usage_for(effective_role))
        return

    raw_id, raw_role = parts[1], parts[2].strip()

    # Валидация telegram_id
    try:
        target_id = int(raw_id)
    except ValueError:
        await message.answer(f"❌ Некорректный Telegram ID: <code>{raw_id}</code>")
        return

    # Валидация роли (регистронезависимо)
    role: UserRole | None = None
    for r in UserRole:
        if r.value.lower() == raw_role.lower():
            role = r
            break

    if role is None:
        await message.answer(
            f"❌ Неизвестная роль: <b>{raw_role}</b>\n\n{_usage_for(effective_role)}"
        )
        return

    # Проверка иерархии прав
    if not can_assign(effective_role, role):
        await message.answer(
            f"⛔ Недостаточно прав для назначения роли {role_label(role)}.\n\n"
            f"{_usage_for(effective_role)}"
        )
        return

    # Сохранение в БД
    await user_service.set_role(target_id, role)

    # Читаем обратно из БД — показываем именно то, что теперь хранится
    confirmed = await user_service.get_role(target_id)

    logger.info(
        "%s (роль: %s) назначил роль %r пользователю %s (подтверждено: %r)",
        actor_id, effective_role.value, role.value, target_id, confirmed.value,
    )

    # Журнал аудита
    actor_nick  = await user_service.get_game_nick(actor_id) or str(actor_id)
    target_nick = await user_service.get_game_nick(target_id) or str(target_id)

    await audit_service.log(
        user_id=actor_id,
        game_nick=actor_nick,
        role=actor_role,
        action_type=AuditAction.MEMBER_ROLE_SET,
        description=(
            f"{role_label(actor_role)} {actor_nick} назначил роль "
            f"{role_label(confirmed)} пользователю {target_nick}"
        ),
    )

    # Синхронизация Telegram Admin Title
    tg_error = await sync_admin_title(bot, group_chat_id, target_id, confirmed)

    if tg_error:
        tg_note = f"\n\n{tg_error}"
    elif confirmed in ADMIN_TITLES:
        tg_note = f"\n\n✅ Telegram-титул установлен: «{ADMIN_TITLES[confirmed]}»"
    else:
        tg_note = "\n\n✅ Telegram-титул снят (роль Участник)."

    await message.answer(
        f"✅ Роль успешно изменена.\n\n"
        f"Пользователь: <code>{target_id}</code>\n"
        f"Новая роль: {role_label(confirmed)}"
        f"{tg_note}"
    )
