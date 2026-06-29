# -*- coding: utf-8 -*-
"""Обработчики кнопок главного меню."""
import logging

from aiogram import F, Router
from aiogram.types import Message

from bot.keyboards.main_menu import BTN, MAIN_KEYBOARD
from bot.services.user_service import UserService
from bot.utils.roles import role_label

router = Router()
logger = logging.getLogger(__name__)

_WIP = "🚧 Раздел находится в разработке."


# ------------------------------------------------------------------ #
# Разделы «в разработке»
# ------------------------------------------------------------------ #

@router.message(F.text == BTN.NEWS)
async def handle_news(message: Message) -> None:
    """Раздел новостей клана."""
    await message.answer(f"📰 <b>Новости</b>\n\n{_WIP}")


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
        name = f"@{u.username}" if u.username else u.first_name
        lines.append(f"• {name} — {role_label(u.role)}")
    await message.answer("\n".join(lines))


@router.message(F.text == BTN.SETTINGS)
async def handle_settings(message: Message, user_service: UserService) -> None:
    """Показывает текущие настройки пользователя."""
    if not message.from_user:
        return
    user = await user_service.get_or_create(message.from_user)
    await message.answer(
        f"⚙️ <b>Настройки</b>\n\n"
        f"Твой ID: <code>{user.telegram_id}</code>\n"
        f"Имя: {user.first_name}\n"
        f"Username: {'@' + user.username if user.username else 'не задан'}\n"
        f"Роль: {role_label(user.role)}\n\n"
        f"{_WIP}",
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
        "🛡️ <b>Администрация</b> — только для Лидеров и Старейшин\n"
        "⚙️ <b>Настройки</b> — ваш профиль\n\n"
        "По всем вопросам обращайтесь к администраторам клана.",
        reply_markup=MAIN_KEYBOARD,
    )
