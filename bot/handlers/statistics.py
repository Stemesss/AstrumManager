# -*- coding: utf-8 -*-
"""
Обработчик «📈 Центр статистики» (административная панель).

Доступ:
  👑 Лидер, ⭐ Дитя клана, 🛡️ Старейшина — полный доступ
  👤 Участник — доступа нет
"""
import asyncio
import logging

from aiogram import Bot, F, Router
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
from bot.utils.group_filter import filter_by_active_ids, filter_present_in_group, is_present_in_group

router = Router()
logger = logging.getLogger(__name__)

_WIP = "🚧 Раздел находится в разработке."

_DIVIDER = "━━━━━━━━━━━━━━━━"

_MENU_TEXT = (
    "📈 <b>Центр статистики</b>\n\n"
    f"{_DIVIDER}\n\n"
    "Выберите раздел:"
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


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные
# ─────────────────────────────────────────────────────────────────────────────

async def _is_active(
    user_id: int,
    group_chat_id: int,
    bot: "Bot",
    telethon_sync=None,
    db=None,
) -> bool:
    """Проверяет членство: сначала Telethon, при недоступности — Bot API."""
    if telethon_sync is not None and db is not None:
        ids = await telethon_sync.sync_and_get_ids(group_chat_id, db)
        if ids is not None:
            return user_id in ids
    return await is_present_in_group(bot, group_chat_id, user_id)


async def _filter_active(
    items: list,
    get_id,
    group_chat_id: int,
    bot: "Bot",
    telethon_sync=None,
    db=None,
) -> list:
    """Фильтрует список: сначала Telethon, при недоступности — Bot API."""
    if telethon_sync is not None and db is not None:
        ids = await telethon_sync.sync_and_get_ids(group_chat_id, db)
        if ids is not None:
            return filter_by_active_ids(items, get_id, ids)
    return await filter_present_in_group(bot, group_chat_id, items, get_id)


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
        f"{icon} <b>{title}</b>\n\n"
        f"👤 {u.game_nick}\n"
        f"⭐ {u.score} очков\n\n"
        f"{_DIVIDER}\n\n"
        f"📰 Новостей: {u.news_count}\n"
        f"📅 Событий: {u.events_count}"
    )


def _fmt_no_data(icon: str, title: str, period_hint: str) -> str:
    """Заглушка «нет данных» для карточек победителей."""
    return (
        f"{icon} <b>{title}</b>\n\n"
        f"🚧 Пока недостаточно данных для определения {period_hint}"
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
        return "📰 <b>Новости</b>\n\n🚧 Пока недостаточно данных."
    top_block = _fmt_top_authors(s.top_authors) if s.top_authors else "—"
    last_block = ""
    if s.latest_title or s.latest_date:
        last_block = "\n\n🕒 <b>Последняя публикация</b>\n"
        if s.latest_title:
            last_block += f"«{s.latest_title}»\n"
        if s.latest_date:
            last_block += _fmt_date(s.latest_date)
    return (
        f"📰 <b>Новости</b>\n\n"
        f"📄 Всего новостей: {s.total}\n\n"
        f"🥇 Топ авторов\n{top_block}"
        f"{last_block}"
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
        return f"{icon} <b>{title}</b>\n\n🚧 Пока недостаточно данных."
    top_block = _fmt_top_authors(s.top_authors) if s.top_authors else "—"
    last_block = ""
    if s.latest_date:
        last_block = f"\n\n🕒 {last_label}\n"
        if show_last_name and s.latest_description:
            last_block += f"{s.latest_description}\n"
        last_block += _fmt_date(s.latest_date)
    return (
        f"{icon} <b>{title}</b>\n\n"
        f"📄 {total_label}: {s.total}\n\n"
        f"🥇 {top_label}\n{top_block}"
        f"{last_block}"
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
    bot: Bot,
    group_chat_id: int,
    telethon_sync=None,
    db=None,
) -> None:
    """Показывает карточку лучшего участника текущего месяца."""
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()
    winner = await stats_service.best_of_month()
    if winner and not await _is_active(winner.user_id, group_chat_id, bot, telethon_sync, db):
        winner = None
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
    bot: Bot,
    group_chat_id: int,
    telethon_sync=None,
    db=None,
) -> None:
    """Показывает карточку самого активного участника за последние 7 дней."""
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()
    winner = await stats_service.best_of_week()
    if winner and not await _is_active(winner.user_id, group_chat_id, bot, telethon_sync, db):
        winner = None
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
# 🏆 Топ-10 участников
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_top10_card(users: list) -> str:
    if not users:
        return "🏆 <b>Топ-10 участников</b>\n\n🚧 Пока недостаточно данных."
    lines = "\n".join(
        f"{i + 1}. {u.game_nick} — {u.score} оч."
        for i, u in enumerate(users)
    )
    formula = (
        "📌 <i>Очки считаются по журналу:\n"
        "📰 Новость = 5  📅 Событие = 8\n"
        "📚 Гайд = 10  📸 Скриншот = 2</i>"
    )
    return f"🏆 <b>Топ-10 участников</b>\n\n{lines}\n\n{_DIVIDER}\n\n{formula}"


@router.callback_query(F.data == StatisticsBtn.TOP10)
async def cb_top10(
    callback: CallbackQuery,
    user_service: UserService,
    stats_service: StatsService,
    bot: Bot,
    group_chat_id: int,
    telethon_sync=None,
    db=None,
) -> None:
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()
    users = await stats_service.top_active_users(limit=10)
    users = await _filter_active(users, lambda u: u.user_id, group_chat_id, bot, telethon_sync, db)
    await callback.message.edit_text(_fmt_top10_card(users), reply_markup=STATISTICS_SECTION_KB)


# ─────────────────────────────────────────────────────────────────────────────
# 📈 Рост клана
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_growth_card(g) -> str:
    if not g.total:
        return "📈 <b>Рост клана</b>\n\n🚧 Пока недостаточно данных."
    bar = "".join("█" if cnt > 0 else "░" for _, cnt in g.by_day)
    days = len(g.by_day)
    return (
        f"📈 <b>Рост клана</b>\n\n"
        f"👥 Всего участников: {g.total}\n"
        f"📅 Сегодня: +{g.today}  •  За месяц: +{g.month}\n\n"
        f"{_DIVIDER}\n\n"
        f"Последние {days} дней\n"
        f"{bar}"
    )


@router.callback_query(F.data == StatisticsBtn.GROWTH)
async def cb_growth(
    callback: CallbackQuery,
    user_service: UserService,
    stats_service: StatsService,
) -> None:
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()
    growth = await stats_service.clan_growth(chart_days=14)
    await callback.message.edit_text(_fmt_growth_card(growth), reply_markup=STATISTICS_SECTION_KB)


# ─────────────────────────────────────────────────────────────────────────────
# 👑 Зал славы
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_hof_row(icon: str, label: str, name: str | None, extra: str = "") -> str:
    if not name:
        return f"{icon} <b>{label}</b>\n🚧 Нет данных"
    return f"{icon} <b>{label}</b>\n{name}" + (f"  •  {extra}" if extra else "")


def _fmt_hall_of_fame_card(
    month_winner, week_winner, news_s, guides_s, screenshots_s, events_s
) -> str:
    best_news   = news_s.top_authors[0].name        if news_s.top_authors        else None
    best_guides = guides_s.top_authors[0].name      if guides_s.top_authors      else None
    best_shots  = screenshots_s.top_authors[0].name if screenshots_s.top_authors else None
    best_events = events_s.top_authors[0].name      if events_s.top_authors      else None

    rows = [
        f"👑 <b>Зал славы</b>\n\n{_DIVIDER}",
        _fmt_hof_row("🥇", "Лучший участник месяца",
                     month_winner.game_nick if month_winner else None,
                     f"{month_winner.score} очков" if month_winner else ""),
        _fmt_hof_row("🔥", "Самый активный недели",
                     week_winner.game_nick if week_winner else None,
                     f"{week_winner.score} очков" if week_winner else ""),
        _fmt_hof_row("📰", "Лучший автор новостей",      best_news),
        _fmt_hof_row("📚", "Лучший автор гайдов",        best_guides),
        _fmt_hof_row("📸", "Лучший по скриншотам",       best_shots),
        _fmt_hof_row("📅", "Лучший организатор событий", best_events),
    ]
    return "\n\n".join(rows)


@router.callback_query(F.data == StatisticsBtn.HALL_OF_FAME)
async def cb_hall_of_fame(
    callback: CallbackQuery,
    user_service: UserService,
    stats_service: StatsService,
) -> None:
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()
    month_w, week_w, news_s, guides_s, shots_s, events_s = await asyncio.gather(
        stats_service.best_of_month(),
        stats_service.best_of_week(),
        stats_service.news(),
        stats_service.guides(),
        stats_service.screenshots(),
        stats_service.events(),
    )
    text = _fmt_hall_of_fame_card(month_w, week_w, news_s, guides_s, shots_s, events_s)
    await callback.message.edit_text(text, reply_markup=STATISTICS_SECTION_KB)
