# -*- coding: utf-8 -*-
"""Обработчики кнопок главного меню."""
import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.keyboards.main_menu import BTN, MAIN_KEYBOARD
from bot.services.user_service import UserService
from bot.utils.profile import PROFILE_KB, build_profile_card

router = Router()
logger = logging.getLogger(__name__)

_WIP = "🚧 Раздел находится в разработке."
_APP_VERSION = "1.2.8"


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


@router.callback_query(F.data == BTN.PROFILE)
async def cb_profile(callback: CallbackQuery, user_service: UserService) -> None:
    """Inline-точка входа в профиль (карточка обновления /start update).

    Переиспользует существующую логику построения карточки — без дублирования.
    """
    if not callback.from_user:
        return
    await callback.answer()

    user = await user_service.get_or_create(callback.from_user)
    role = await user_service.get_role(callback.from_user.id)
    stats = await user_service.get_profile_stats(callback.from_user.id)

    name = user.game_nick or ""
    await callback.message.answer(
        build_profile_card(name, role, stats),
        reply_markup=PROFILE_KB,
    )


@router.message(F.text == BTN.HANDBOOK)
async def handle_handbook_button(message: Message) -> None:
    """Кнопка «Справочник» из главного меню."""
    await message.answer(
        "📖 <b>Справочник AstrumManager</b>\n\n"
        "Добро пожаловать в справочный центр AstrumManager.\n\n"
        "Здесь собрана информация обо всех основных возможностях бота.\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "📰 <b>Новости</b> — последние новости клана.\n\n"
        "📅 <b>События</b> — ближайшие мероприятия.\n\n"
        "✅ <b>Правила</b> — правила клана.\n\n"
        "💡 <b>Жалобы и предложения</b> — связь с администрацией.\n\n"
        "👥 <b>Участники</b> — состав клана.\n\n"
        "🛡 <b>Администрация</b> — раздел для Лидера, Дитя клана и Старейшин.\n\n"
        "📊 <b>Статистика</b> — активность клана.\n\n"
        "👤 <b>Мой профиль</b> — просмотр и изменение игрового ника.\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"ℹ️ Версия AstrumManager: <b>{_APP_VERSION}</b>",
        reply_markup=MAIN_KEYBOARD,
    )
