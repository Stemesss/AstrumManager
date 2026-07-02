# -*- coding: utf-8 -*-
"""Обработчики кнопок главного меню."""
import logging

from aiogram import F, Router
from aiogram.types import Message

from bot.keyboards.main_menu import BTN, MAIN_KEYBOARD
from bot.services.user_service import UserService
from bot.utils.profile import PROFILE_KB, build_profile_card

router = Router()
logger = logging.getLogger(__name__)

_WIP = "🚧 Раздел находится в разработке."


@router.message(F.text == BTN.PROFILE)
async def handle_profile(message: Message, user_service: UserService) -> None:
    """Показывает карточку профиля пользователя."""
    if not message.from_user:
        return

    user = await user_service.get_or_create(message.from_user)
    role = await user_service.get_role(message.from_user.id)
    stats = await user_service.get_profile_stats(message.from_user.id)

    name = user.game_nick or ""
    await message.answer(
        build_profile_card(name, role, stats),
        reply_markup=PROFILE_KB,
    )


@router.message(F.text == BTN.HELP)
async def handle_help_button(message: Message) -> None:
    """Кнопка «Помощь» из главного меню."""
    await message.answer(
        "❓ <b>Помощь</b>\n\n"
        "Выберите раздел в главном меню:\n\n"
        "📰 <b>Новости</b> — последние новости клана\n"
        "📅 <b>События</b> — ближайшие мероприятия\n"
        "✅ <b>Правила</b> — правила клана\n"
        "💡 <b>Жалобы и предложения</b> — обратная связь\n"
        "👥 <b>Участники</b> — состав клана\n"
        "🛡️ <b>Администрация</b> — для Лидеров, Дитя клана и Старейшин\n"
        "📈 <b>Статистика</b> — центр статистики клана\n"
        "👤 <b>Мой профиль</b> — ваш профиль и смена имени\n\n"
        "По всем вопросам обращайтесь к администраторам клана.",
        reply_markup=MAIN_KEYBOARD,
    )
