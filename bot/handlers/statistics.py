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
from bot.models.stats import ContentStats, NewsStats, UserActivity
from bot.models.user import UserRole
from bot.services.stats_service import StatsService
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

_HEADER = "━━━━━━━━━━━━━━━━━━━━"


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные
# ─────────────────────────────────────────────────────────────────────────────

async def _check_admin(callback: CallbackQuery, user_service: UserService) -> bool:
    """Проверяет административные права; отвечает alert и возвращает False при отказе."""
    role = await user_service.get_role(callback.from_user.id)
    if role not in UserRole.admin_roles():
        await callback.answer("🔒 Недостаточно прав.", show_alert=True)
        return False
    return True


def _fmt_winner_card(icon: str, title: str, u: UserActivity) -> str:
    """Универсальная карточка победителя (используется в разных периодах)."""
    return (
        f"{_HEADER}\n"
        f"{icon} <b>{title}</b>\n"
        f"{_HEADER}\n\n"
        f"👤 Ник:\n{u.game_nick}\n\n"
        f"⭐ Очков:\n{u.score}\n\n"
        f"📰 Новостей:\n{u.news_count}\n\n"
        f"📚 Гайдов:\n{u.guides_count}\n\n"
        f"📸 Скриншотов:\n{u.screenshots_count}\n\n"
        f"📅 Событий:\n{u.events_count}\n\n"
        f"{_HEADER}"
    )


def _fmt_no_data(icon: str, title: str, period_hint: str) -> str:
    """Заглушка «нет данных» для карточек победителей."""
    return (
        f"{_HEADER}\n"
        f"{icon} <b>{title}</b>\n"
        f"{_HEADER}\n\n"
        f"🚧 Пока недостаточно данных для определения\n"
        f"{period_hint}\n\n"
        f"{_HEADER}"
    )


def _fmt_date(dt_str: str) -> str:
    """'2026-06-29 12:34:56' → '29.06.2026'. Возвращает исходную строку при ошибке."""
    try:
        return dt_str[:10].split("-")[2] + "." + dt_str[5:7] + "." + dt_str[:4]
    except Exception:
        return dt_str


def _fmt_top_authors(authors: list) -> str:
    """Нумерованный список топ-авторов. Пустая строка если список пуст."""
    medals = ["1.", "2.", "3.", "4.", "5."]
    lines = [
        f"{medals[i]} {a.name} — {a.count}"
        for i, a in enumerate(authors)
    ]
    return "\n".join(lines)


def _fmt_news_card(s: "NewsStats") -> str:
    """Карточка раздела «Новости»."""
    if not s.total:
        return f"{_HEADER}\n📰 <b>Новости</b>\n{_HEADER}\n\n🚧 Пока недостаточно данных.\n\n{_HEADER}"
    top_block = _fmt_top_authors(s.top_authors) if s.top_authors else "—"
    last_block = ""
    if s.latest_title or s.latest_date:
        last_block = (
            f"\n{_HEADER}\n🕒 Последняя публикация\n"
            + (f"\"{s.latest_title}\"\n" if s.latest_title else "")
            + (_fmt_date(s.latest_date) if s.latest_date else "")
        )
    return (
        f"{_HEADER}\n📰 <b>Новости</b>\n{_HEADER}\n\n"
        f"📄 Всего новостей: {s.total}\n\n"
        f"🥇 Топ авторов\n{top_block}"
        f"{last_block}\n\n{_HEADER}"
    )


def _fmt_content_card(
    icon: str,
    title: str,
    total_label: str,
    top_label: str,
    last_label: str,
    s: "ContentStats",
    show_last_name: bool = True,
) -> str:
    """Универсальная карточка контентного раздела (гайды / скриншоты / события)."""
    if not s.total:
        return f"{_HEADER}\n{icon} <b>{title}</b>\n{_HEADER}\n\n🚧 Пока недостаточно данных.\n\n{_HEADER}"
    top_block = _fmt_top_authors(s.top_authors) if s.top_authors else "—"
    last_block = ""
    if s.latest_date:
        last_block = f"\n{_HEADER}\n🕒 {last_label}\n"
        if show_last_name and s.latest_description:
            last_block += f"{s.latest_description}\n"
        last_block += _fmt_date(s.latest_date)
    return (
        f"{_HEADER}\n{icon} <b>{title}</b>\n{_HEADER}\n\n"
        f"📄 {total_label}: {s.total}\n\n"
        f"🥇 {top_label}\n{top_block}"
        f"{last_block}\n\n{_HEADER}"
    )


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
    logger.info("Пользователь %s открыл центр статистики", callback.from_user.id)
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
# 🏆 Лучший участник месяца
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == StatisticsBtn.BEST_MONTH)
async def cb_best_month(
    callback: CallbackQuery,
    user_service: UserService,
    stats_service: StatsService,
) -> None:
    """Показывает карточку лучшего участника текущего месяца."""
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()
    winner = await stats_service.best_of_month()
    text = (
        _fmt_winner_card("🏆", "Лучший участник месяца", winner)
        if winner
        else _fmt_no_data("🏆", "Лучший участник месяца", "лучшего участника месяца.")
    )
    await callback.message.edit_text(text, reply_markup=STATISTICS_SECTION_KB)


@router.callback_query(F.data == StatisticsBtn.MOST_ACTIVE_WEEK)
async def cb_most_active_week(
    callback: CallbackQuery,
    user_service: UserService,
    stats_service: StatsService,
) -> None:
    """Показывает карточку самого активного участника за последние 7 дней."""
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()
    winner = await stats_service.best_of_week()
    text = (
        _fmt_winner_card("🔥", "Самый активный участник недели", winner)
        if winner
        else _fmt_no_data("🔥", "Самый активный участник недели",
                          "самого активного участника недели.")
    )
    await callback.message.edit_text(text, reply_markup=STATISTICS_SECTION_KB)


# ─────────────────────────────────────────────────────────────────────────────
# 📰 Новости / 📚 Гайды / 📸 Скриншоты / 📅 События
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == StatisticsBtn.NEWS)
async def cb_news(
    callback: CallbackQuery,
    user_service: UserService,
    stats_service: StatsService,
) -> None:
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()
    data = await stats_service.news()
    await callback.message.edit_text(_fmt_news_card(data), reply_markup=STATISTICS_SECTION_KB)


@router.callback_query(F.data == StatisticsBtn.GUIDES)
async def cb_guides(
    callback: CallbackQuery,
    user_service: UserService,
    stats_service: StatsService,
) -> None:
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()
    data = await stats_service.guides()
    text = _fmt_content_card(
        "📚", "Гайды", "Всего гайдов", "Топ авторов", "Последний гайд", data
    )
    await callback.message.edit_text(text, reply_markup=STATISTICS_SECTION_KB)


@router.callback_query(F.data == StatisticsBtn.SCREENSHOTS)
async def cb_screenshots(
    callback: CallbackQuery,
    user_service: UserService,
    stats_service: StatsService,
) -> None:
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()
    data = await stats_service.screenshots()
    text = _fmt_content_card(
        "📸", "Скриншоты", "Всего скриншотов", "Самые активные", "Последняя загрузка",
        data, show_last_name=False,
    )
    await callback.message.edit_text(text, reply_markup=STATISTICS_SECTION_KB)


@router.callback_query(F.data == StatisticsBtn.EVENTS)
async def cb_events(
    callback: CallbackQuery,
    user_service: UserService,
    stats_service: StatsService,
) -> None:
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()
    data = await stats_service.events()
    text = _fmt_content_card(
        "📅", "События", "Всего событий", "Лучшие организаторы", "Последнее событие", data
    )
    await callback.message.edit_text(text, reply_markup=STATISTICS_SECTION_KB)


# ─────────────────────────────────────────────────────────────────────────────
# Заглушки для оставшихся WIP-секций
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.in_({
    StatisticsBtn.TOP10,
    StatisticsBtn.GROWTH,
    StatisticsBtn.HALL_OF_FAME,
}))
async def cb_statistics_section(
    callback: CallbackQuery,
    user_service: UserService,
) -> None:
    """Общий обработчик WIP-секций центра статистики."""
    if not await _check_admin(callback, user_service):
        return
    section = _SECTION_NAMES.get(callback.data, "Раздел")
    await callback.answer()
    await callback.message.edit_text(
        f"{_HEADER}\n"
        f"<b>{section}</b>\n"
        f"{_HEADER}\n\n"
        f"{_WIP}",
        reply_markup=STATISTICS_SECTION_KB,
    )
