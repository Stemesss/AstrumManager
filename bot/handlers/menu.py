# -*- coding: utf-8 -*-
"""Обработчики кнопок главного меню."""
import logging

from aiogram import F, Router
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.keyboards.main_menu import BTN, MAIN_KEYBOARD
from bot.services.user_service import UserService
from bot.utils.roles import role_label
from bot.utils.text import pluralize_days

router = Router()
logger = logging.getLogger(__name__)

_WIP = "🚧 Раздел находится в разработке."

_SETTINGS_KB = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(text="✏️ Изменить ник", callback_data="nick:change"),
]])


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
    """Показывает профиль пользователя с актуальными данными из БД."""
    if not message.from_user:
        return

    user = await user_service.get_or_create(message.from_user)
    role = await user_service.get_role(message.from_user.id)
    stats = await user_service.get_profile_stats(message.from_user.id)

    nick_str = user.game_nick or "<i>не задан</i>"

    await message.answer(
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚜️ <b>AstrumManager</b>\n"
        "👤 <b>Личный профиль</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>Ник:</b> {nick_str}\n\n"
        f"🏅 <b>Роль:</b> {role_label(role)}\n\n"
        f"📅 <b>В клане:</b> {pluralize_days(stats['days_in_clan'])}\n"
        f"📚 <b>Создано гайдов:</b> {stats['guides_count']}\n"
        f"📸 <b>Загружено скриншотов:</b> {stats['screenshots_count']}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🟢 <b>Статус:</b> Онлайн\n\n"
        "✏️ Изменить ник\n\n"
        "━━━━━━━━━━━━━━━━━━━━",
        reply_markup=_SETTINGS_KB,
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
