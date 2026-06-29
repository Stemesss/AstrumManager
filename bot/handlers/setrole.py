# -*- coding: utf-8 -*-
"""Обработчик команды /setrole — назначение роли участнику клана."""
import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.models.user import UserRole
from bot.services.user_service import UserService
from bot.utils.roles import ROLE_ORDER, role_label

router = Router()
logger = logging.getLogger(__name__)

# Подсказка с ролями в порядке иерархии
_USAGE = (
    "Использование: /setrole &lt;telegram_id&gt; &lt;роль&gt;\n\n"
    "Доступные роли (по убыванию старшинства):\n"
    + "\n".join(f"• {role_label(r)}" for r in ROLE_ORDER)
)


@router.message(Command("setrole"))
async def handle_setrole(
    message: Message,
    user_service: UserService,
    owner_id: int | None,
) -> None:
    """Назначает роль пользователю. Доступно только владельцу бота."""
    if not message.from_user:
        return

    # Проверка прав владельца
    if owner_id is None or message.from_user.id != owner_id:
        logger.warning(
            "Пользователь %s попытался использовать /setrole без прав владельца",
            message.from_user.id,
        )
        await message.answer("🔒 Команда доступна только владельцу бота.")
        return

    # Разбор аргументов
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(_USAGE)
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
        await message.answer(f"❌ Неизвестная роль: <b>{raw_role}</b>\n\n{_USAGE}")
        return

    # Сохранение в БД
    await user_service.set_role(target_id, role)

    # Читаем обратно из БД — показываем именно то, что теперь хранится
    confirmed = await user_service.get_role(target_id)

    logger.info(
        "Владелец %s назначил роль %r пользователю %s (подтверждено: %r)",
        message.from_user.id, role.value, target_id, confirmed.value,
    )
    await message.answer(
        f"✅ Роль успешно изменена.\n\n"
        f"Пользователь: <code>{target_id}</code>\n"
        f"Новая роль: {role_label(confirmed)}"
    )
