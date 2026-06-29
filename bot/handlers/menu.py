# -*- coding: utf-8 -*-
"""Обработчики кнопок главного меню."""
import logging

from aiogram import F, Router
from aiogram.types import Message

from bot.keyboards.main_menu import BTN, MAIN_KEYBOARD
from bot.services.user_service import UserService
from bot.utils.profile import SETTINGS_KB, build_profile_card
from bot.utils.roles import role_label

router = Router()
logger = logging.getLogger(__name__)

_WIP = "🚧 Раздел находится в разработке."


# ------------------------------------------------------------------ #
# Разделы «в разработке»
# ------------------------------------------------------------------ #


@router.message(F.text == BTN.EVENTS)
async def handle_events(message: Message) -> None:
    """Раздел событий клана."""
    await message.answer(f"📅 <b>События</b>\n\n{_WIP}")


@router.message(F.text == BTN.GUIDES)
async def handle_guides(message: Message) -> None:
    """Раздел гайдов."""
    await message.answer(f"📚 <b>Гайды</b>\n\n{_WIP}")


@router.message(F.text == BTN.SCREENSHOTS)
async def handle_screenshots(message: Message) -> None:
    """Раздел скриншотов."""
    await message.answer(f"📸 <b>Скриншоты</b>\n\n{_WIP}")


@router.message(F.text == BTN.MEMBERS)
async def handle_members(message: Message, user_service: UserService) -> None:
    """Показывает список участников клана."""
    users = await user_service.get_all_users()
    if not users:
        await message.answer("👥 <b>Участники</b>\n\nСписок пока пуст.")
        return

    lines = [f"👥 <b>Участники клана Astrum</b> ({len(users)})\n"]
    for u in users:
        display = u.game_nick or u.first_name
        lines.append(f"• {display} — {role_label(u.role)}")
    await message.answer("\n".join(lines))


@router.message(F.text == BTN.SETTINGS)
async def handle_settings(message: Message, user_service: UserService) -> None:
    """Показывает карточку профиля пользователя."""
    if not message.from_user:
        return

    user = await user_service.get_or_create(message.from_user)
    role = await user_service.get_role(message.from_user.id)
    stats = await user_service.get_profile_stats(message.from_user.id)

    nick_str = user.game_nick or "<i>не задан</i>"
    await message.answer(
        build_profile_card(nick_str, role, stats),
        reply_markup=SETTINGS_KB,
    )


@router.message(F.text == BTN.HELP)
async def handle_help_button(message: Message) -> None:
    """Кнопка «Помощь» из главного меню."""
    await message.answer(
        "❓ <b>Помощь</b>\n\n"
        "Выберите раздел в главном меню:\n\n"
        "📰 <b>Новости</b> — последние новости клана\n"
        "📅 <b>События</b> — ближайшие мероприятия\n"
        "📚 <b>Гайды</b> — обучающие материалы\n"
        "📸 <b>Скриншоты</b> — галерея клана\n"
        "👥 <b>Участники</b> — состав клана\n"
        "🛡️ <b>Администрация</b> — для Лидеров, Дитя клана и Старейшин\n"
        "📈 <b>Статистика</b> — центр статистики клана\n"
        "⚙️ <b>Настройки</b> — ваш профиль\n\n"
        "По всем вопросам обращайтесь к администраторам клана.",
        reply_markup=MAIN_KEYBOARD,
    )
