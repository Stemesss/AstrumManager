# -*- coding: utf-8 -*-
"""Обработчик раздела «Администрация» (только для Лидеров и Старейшин)."""
import logging

from aiogram import F, Router
from aiogram.types import Message

from bot.keyboards.main_menu import BTN
from bot.models.user import UserRole
from bot.services.user_service import UserService
from bot.utils.roles import role_label

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == BTN.ADMIN)
async def handle_admin(message: Message, user_service: UserService) -> None:
    """Панель администрации. Доступна только Лидерам и Старейшинам."""
    if not message.from_user:
        return

    is_admin = await user_service.is_admin(message.from_user.id)

    if not is_admin:
        role = await user_service.get_role(message.from_user.id)
        logger.info(
            "Пользователь %s (роль: %s) попытался войти в раздел администрации",
            message.from_user.id,
            role.value,
        )
        await message.answer(
            "🔒 <b>Доступ запрещён</b>\n\n"
            f"Раздел «Администрация» доступен только Лидерам и Старейшинам.\n"
            f"Ваша роль: {role_label(role)}"
        )
        return

    # Только для администраторов
    users = await user_service.get_all_users()
    total = len(users)
    by_role: dict[UserRole, int] = {}
    for u in users:
        by_role[u.role] = by_role.get(u.role, 0) + 1

    role_lines = "\n".join(
        f"  • {role_label(role)}: {count}"
        for role, count in sorted(by_role.items(), key=lambda x: x[0].value)
    )

    admin_role = await user_service.get_role(message.from_user.id)
    await message.answer(
        f"🛡️ <b>Панель администрации</b>\n\n"
        f"Ваш уровень доступа: {role_label(admin_role)}\n\n"
        f"<b>Статистика клана:</b>\n"
        f"  Всего участников: {total}\n"
        f"{role_lines}\n\n"
        "🚧 Расширенные инструменты управления находятся в разработке."
    )
    logger.info(
        "Администратор %s открыл панель управления (роль: %s)",
        message.from_user.id,
        admin_role.value,
    )
