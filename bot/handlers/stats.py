# -*- coding: utf-8 -*-
"""
Обработчик раздела «📈 Центр статистики».

Доступ:
  👑 Лидер, ⭐ Дитя клана, 🛡️ Старейшина — полный доступ
  👤 Участник — доступа нет
"""
import logging

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message

from bot.keyboards.main_menu import BTN
from bot.keyboards.stats import STATS_BACK_KB, STATS_MENU_KB, StatBtn
from bot.models.stats import ClanGrowth, ContentStats, NewsStats, UserActivity
from bot.models.user import UserRole
from bot.services.stats_service import StatsService
from bot.services.user_service import UserService
from bot.utils.group_filter import filter_present_in_group, is_present_in_group
from bot.utils.roles import role_label

router = Router()
logger = logging.getLogger(__name__)

_NO_DATA = "Пока недостаточно данных."

_RANK_ICONS = {1: "🥇", 2: "🥈", 3: "🥉"}

_MENU_TEXT = "📈 <b>Центр статистики</b>"


# ─────────────────────────────────────────────────────────────────────────────
# Форматирование
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_dt(raw: str) -> str:
    """'2026-06-12 10:15:03' → '12.06.2026 • 10:15'."""
    try:
        date_part, time_part = raw[:16].split(" ")
        y, m, d = date_part.split("-")
        return f"{d}.{m}.{y} • {time_part}"
    except Exception:  # noqa: BLE001
        return raw


def _fmt_date(raw: str) -> str:
    """'2026-06-12' → '12.06'."""
    try:
        parts = raw[:10].split("-")
        return f"{parts[2]}.{parts[1]}"
    except Exception:  # noqa: BLE001
        return raw


def _bar(value: int, max_value: int, width: int = 12) -> str:
    if max_value == 0:
        return ""
    filled = max(1, round(value * width / max_value)) if value else 0
    return "█" * filled


def _fmt_top1(u: UserActivity) -> str:
    from bot.models.user import UserRole
    role_enum = UserRole.from_str(u.role)
    return (
        "🔥 <b>Самый активный участник</b>\n\n"
        f"🎮 <b>{u.game_nick}</b>\n"
        f"🎖 {role_label(role_enum)}\n\n"
        f"📰 Новостей: {u.news_count}  →  {u.news_count * 5} очков\n"
        f"📅 Событий: {u.events_count}  →  {u.events_count * 8} очков\n\n"
        f"📈 <b>Общая активность: {u.score} очков</b>"
    )


def _fmt_top10(users: list[UserActivity]) -> str:
    lines = ["🏆 <b>Топ-10 участников</b>\n"]
    for i, u in enumerate(users, start=1):
        icon = _RANK_ICONS.get(i, f"{i}.")
        lines.append(f"{icon} {u.game_nick} — {u.score} очков")
    return "\n".join(lines)


def _fmt_news(s: NewsStats) -> str:
    lines = [
        "📰 <b>Статистика новостей</b>\n",
        f"📊 Всего новостей: <b>{s.total}</b>",
    ]
    if s.top_authors:
        lines.append(f"\n👑 Лучший автор: {s.top_authors[0].name} ({s.top_authors[0].count} шт.)")
        lines.append("\n📋 <b>ТОП-5 авторов:</b>")
        for i, a in enumerate(s.top_authors, 1):
            lines.append(f"  {i}. {a.name} — {a.count}")
    else:
        lines.append(f"\n{_NO_DATA}")
    if s.latest_title:
        lines.append(f"\n📅 <b>Последняя новость:</b>\n  «{s.latest_title}»")
        if s.latest_date:
            lines.append(f"  {_fmt_dt(s.latest_date)}")
    return "\n".join(lines)


def _fmt_content(title: str, s: ContentStats) -> str:
    lines = [
        f"<b>{title}</b>\n",
        f"📊 Всего: <b>{s.total}</b>",
    ]
    if s.top_authors:
        lines.append(f"\n👑 Лучший: {s.top_authors[0].name} ({s.top_authors[0].count} шт.)")
        lines.append("\n📋 <b>ТОП-5:</b>")
        for i, a in enumerate(s.top_authors, 1):
            lines.append(f"  {i}. {a.name} — {a.count}")
    else:
        lines.append(f"\n{_NO_DATA}")
    if s.latest_author:
        lines.append("\n📅 <b>Последнее:</b>")
        lines.append(f"  {s.latest_author}")
        if s.latest_date:
            lines.append(f"  {_fmt_dt(s.latest_date)}")
    return "\n".join(lines)


def _fmt_growth(g: ClanGrowth) -> str:
    max_val = max((cnt for _, cnt in g.by_day), default=0)
    lines = [
        "📊 <b>Рост клана</b>\n",
        f"👥 Всего участников: <b>{g.total}</b>\n",
        f"📅 Вступило сегодня: {g.today}",
        f"📅 За неделю: {g.week}",
        f"📅 За месяц: {g.month}",
        "\n📈 <b>Последние 7 дней:</b>\n",
    ]
    if max_val == 0:
        lines.append(_NO_DATA)
    else:
        for day_str, cnt in g.by_day:
            bar = _bar(cnt, max_val)
            label = _fmt_date(day_str)
            lines.append(f"<code>{label} {bar:<12} {cnt}</code>")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные
# ─────────────────────────────────────────────────────────────────────────────

async def _check_access(
    callback: CallbackQuery, user_service: UserService
) -> bool:
    role = await user_service.get_role(callback.from_user.id)
    if role not in UserRole.admin_roles():
        await callback.answer("🔒 Недостаточно прав.", show_alert=True)
        return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Точка входа (reply-кнопка «📈 Статистика»)
# ─────────────────────────────────────────────────────────────────────────────

@router.message(F.text == BTN.STATS)
async def handle_stats_menu(message: Message, user_service: UserService) -> None:
    if not message.from_user:
        return
    role = await user_service.get_role(message.from_user.id)
    if role not in UserRole.admin_roles():
        await message.answer(
            "🔒 <b>Доступ запрещён</b>\n\n"
            "Раздел «Центр статистики» доступен только администраторам клана.\n"
            f"Ваша роль: {role_label(role)}"
        )
        return
    await message.answer(_MENU_TEXT, reply_markup=STATS_MENU_KB)


# ─────────────────────────────────────────────────────────────────────────────
# Навигация
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == StatBtn.MENU)
async def cb_stats_menu(callback: CallbackQuery, user_service: UserService) -> None:
    if not await _check_access(callback, user_service):
        return
    await callback.answer()
    await callback.message.edit_text(_MENU_TEXT, reply_markup=STATS_MENU_KB)


@router.callback_query(F.data == StatBtn.CLOSE)
async def cb_stats_close(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.delete()


# ─────────────────────────────────────────────────────────────────────────────
# Секции
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == StatBtn.TOP1)
async def cb_top1(
    callback: CallbackQuery,
    user_service: UserService,
    stats_service: StatsService,
    bot: Bot,
    group_chat_id: int,
    telethon_sync=None,
    db=None,
) -> None:
    if not await _check_access(callback, user_service):
        return
    await callback.answer()
    top = await stats_service.most_active_user()
    if top:
        present = False
        if telethon_sync is not None and db is not None:
            ids = await telethon_sync.sync_and_get_ids(group_chat_id, db)
            if ids is not None:
                present = top.user_id in ids
            else:
                present = await is_present_in_group(bot, group_chat_id, top.user_id)
        else:
            present = await is_present_in_group(bot, group_chat_id, top.user_id)
        if not present:
            top = None
    text = (
        _fmt_top1(top)
        if top
        else f"🔥 <b>Самый активный участник</b>\n\n{_NO_DATA}"
    )
    await callback.message.edit_text(text, reply_markup=STATS_BACK_KB)


@router.callback_query(F.data == StatBtn.TOP10)
async def cb_top10(
    callback: CallbackQuery,
    user_service: UserService,
    stats_service: StatsService,
    bot: Bot,
    group_chat_id: int,
    telethon_sync=None,
    db=None,
) -> None:
    if not await _check_access(callback, user_service):
        return
    await callback.answer()
    users = await stats_service.top_active_users(10)
    if telethon_sync is not None and db is not None:
        active_ids = await telethon_sync.sync_and_get_ids(group_chat_id, db)
        if active_ids is not None:
            from bot.utils.group_filter import filter_by_active_ids
            users = filter_by_active_ids(users, lambda u: u.user_id, active_ids)
        else:
            users = await filter_present_in_group(bot, group_chat_id, users, lambda u: u.user_id)
    else:
        users = await filter_present_in_group(bot, group_chat_id, users, lambda u: u.user_id)
    text = (
        _fmt_top10(users)
        if users
        else f"🏆 <b>Топ-10 участников</b>\n\n{_NO_DATA}"
    )
    await callback.message.edit_text(text, reply_markup=STATS_BACK_KB)


@router.callback_query(F.data == StatBtn.NEWS)
async def cb_stats_news(
    callback: CallbackQuery,
    user_service: UserService,
    stats_service: StatsService,
) -> None:
    if not await _check_access(callback, user_service):
        return
    await callback.answer()
    s = await stats_service.news_stats()
    await callback.message.edit_text(_fmt_news(s), reply_markup=STATS_BACK_KB)


@router.callback_query(F.data == StatBtn.GUIDES)
async def cb_stats_guides(
    callback: CallbackQuery,
    user_service: UserService,
    stats_service: StatsService,
) -> None:
    if not await _check_access(callback, user_service):
        return
    await callback.answer()
    s = await stats_service.guides_stats()
    await callback.message.edit_text(
        _fmt_content("📚 Статистика гайдов", s), reply_markup=STATS_BACK_KB
    )


@router.callback_query(F.data == StatBtn.SCREENSHOTS)
async def cb_stats_screenshots(
    callback: CallbackQuery,
    user_service: UserService,
    stats_service: StatsService,
) -> None:
    if not await _check_access(callback, user_service):
        return
    await callback.answer()
    s = await stats_service.screenshots_stats()
    await callback.message.edit_text(
        _fmt_content("📸 Статистика скриншотов", s), reply_markup=STATS_BACK_KB
    )


@router.callback_query(F.data == StatBtn.EVENTS)
async def cb_stats_events(
    callback: CallbackQuery,
    user_service: UserService,
    stats_service: StatsService,
) -> None:
    if not await _check_access(callback, user_service):
        return
    await callback.answer()
    s = await stats_service.events_stats()
    await callback.message.edit_text(
        _fmt_content("📅 Статистика событий", s), reply_markup=STATS_BACK_KB
    )


@router.callback_query(F.data == StatBtn.GROWTH)
async def cb_stats_growth(
    callback: CallbackQuery,
    user_service: UserService,
    stats_service: StatsService,
) -> None:
    if not await _check_access(callback, user_service):
        return
    await callback.answer()
    g = await stats_service.clan_growth()
    await callback.message.edit_text(_fmt_growth(g), reply_markup=STATS_BACK_KB)
