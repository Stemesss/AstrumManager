# -*- coding: utf-8 -*-
"""Обработчик команды /setrole — назначение роли с учётом иерархии прав."""
import logging

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.models.user import UserRole
from bot.services.member_policy import MemberPolicy
from bot.services.role_service import RoleService
from bot.services.user_service import UserService
from bot.utils.roles import assignable_roles, role_label

router = Router()
logger = logging.getLogger(__name__)

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
    member_policy: MemberPolicy,
    role_service: RoleService,
    group_chat_id: int,
) -> None:
    """Назначает роль пользователю с проверкой иерархии прав."""
    if not message.from_user:
        return

    actor_id = message.from_user.id
    actor_role = await user_service.get_role(actor_id)
    effective_role = await member_policy.get_effective_role(actor_id)

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
    result = await role_service.assign_role(
        actor_id=actor_id,
        target_id=target_id,
        new_role=role,
        bot=bot,
        group_chat_id=group_chat_id,
    )
    if not result["ok"]:
        await message.answer(f"{result['error']}\n\n{_usage_for(effective_role)}")
        return

    confirmed = result["role"]
    tg_error = result["tg_error"]
    tg_title = result["tg_title"]

    logger.info(
        "%s (роль: %s) назначил роль %r пользователю %s (подтверждено: %r)",
        actor_id, effective_role.value, role.value, target_id, confirmed.value,
    )

    if tg_error:
        tg_note = f"\n\n{tg_error}"
    elif tg_title:
        tg_note = (
            f"\n\n✅ Telegram-титул установлен: "
            f"«{tg_title}»"
        )
    else:
        tg_note = "\n\n✅ Telegram-титул снят (роль Участник)."

    await message.answer(
        f"✅ Роль успешно изменена.\n\n"
        f"Пользователь: <code>{target_id}</code>\n"
        f"Новая роль: {role_label(confirmed)}"
        f"{tg_note}"
    )
