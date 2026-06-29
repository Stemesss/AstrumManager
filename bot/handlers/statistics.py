# -*- coding: utf-8 -*-
"""
Обработчик «📈 Центр статистики» (административная панель).

Доступ:
  👑 Лидер, ⭐ Дитя клана, 🛡️ Старейшина — полный доступ
  👤 Участник — доступа нет
"""
import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.keyboards.admin_panel import AdminBtn
from bot.keyboards.statistics import (
    STATISTICS_MENU_KB,
    STATISTICS_SECTION_KB,
    StatisticsBtn,
)
from bot.models.user import UserRole
from bot.services.user_service import UserService

router = Router()
logger = logging.getLogger(__name__)

_WIP = "🚧 Раздел находится в разработке."

_MENU_TEXT = (
    "━━━━━━━━━━━━━━━━━━━━\n"
    "📈 <b>Центр статистики</b>\n"
    "━━━━━━━━━━━━━━━━━━━━"
)

_SECTION_NAMES: dict[str, str] = {
    StatisticsBtn.BEST_MONTH:       "🏆 Лучший участник месяца",
    StatisticsBtn.MOST_ACTIVE_WEEK: "🔥 Самый активный недели",
    StatisticsBtn.TOP10:            "📊 Топ-10 участников",
    StatisticsBtn.NEWS:             "📰 Новости",
    StatisticsBtn.GUIDES:           "📚 Гайды",
    StatisticsBtn.SCREENSHOTS:      "📸 Скриншоты",
    StatisticsBtn.EVENTS:           "📅 События",
    StatisticsBtn.GROWTH:           "📈 Рост клана",
    StatisticsBtn.HALL_OF_FAME:     "👑 Зал славы",
}


async def _check_admin(callback: CallbackQuery, user_service: UserService) -> bool:
    """Проверяет административные права; отвечает alert и возвращает False при отказе."""
    role = await user_service.get_role(callback.from_user.id)
    if role not in UserRole.admin_roles():
        await callback.answer("🔒 Недостаточно прав.", show_alert=True)
        return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Вход: кнопка «📈 Центр статистики» из административной панели
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == AdminBtn.STATISTICS)
async def cb_open_statistics(
    callback: CallbackQuery,
    user_service: UserService,
) -> None:
    """Открывает меню центра статистики (новое сообщение)."""
    if not await _check_admin(callback, user_service):
        return
    logger.info(
        "Пользователь %s открыл центр статистики", callback.from_user.id
    )
    await callback.answer()
    await callback.message.answer(_MENU_TEXT, reply_markup=STATISTICS_MENU_KB)


# ─────────────────────────────────────────────────────────────────────────────
# Навигация внутри центра статистики
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == StatisticsBtn.MENU)
async def cb_statistics_menu(
    callback: CallbackQuery,
    user_service: UserService,
) -> None:
    """Возвращает в главное меню центра статистики (редактирует сообщение)."""
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()
    await callback.message.edit_text(_MENU_TEXT, reply_markup=STATISTICS_MENU_KB)


@router.callback_query(F.data == StatisticsBtn.BACK)
async def cb_statistics_back(callback: CallbackQuery) -> None:
    """Закрывает центр статистики (удаляет сообщение)."""
    await callback.answer()
    await callback.message.delete()


# ─────────────────────────────────────────────────────────────────────────────
# Заглушки для всех секций
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.in_({
    StatisticsBtn.BEST_MONTH,
    StatisticsBtn.MOST_ACTIVE_WEEK,
    StatisticsBtn.TOP10,
    StatisticsBtn.NEWS,
    StatisticsBtn.GUIDES,
    StatisticsBtn.SCREENSHOTS,
    StatisticsBtn.EVENTS,
    StatisticsBtn.GROWTH,
    StatisticsBtn.HALL_OF_FAME,
}))
async def cb_statistics_section(
    callback: CallbackQuery,
    user_service: UserService,
) -> None:
    """Общий обработчик всех WIP-секций центра статистики."""
    if not await _check_admin(callback, user_service):
        return
    section = _SECTION_NAMES.get(callback.data, "Раздел")
    await callback.answer()
    await callback.message.edit_text(
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>{section}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{_WIP}",
        reply_markup=STATISTICS_SECTION_KB,
    )
