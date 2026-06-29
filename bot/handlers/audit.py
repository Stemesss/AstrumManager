# -*- coding: utf-8 -*-
"""
Обработчик раздела «📋 Журнал действий» (Audit Log).

Доступ:
  👑 Лидер, ⭐ Дитя клана, 🛡️ Старейшина — полный доступ (просмотр + поиск + очистка)
  👤 Участник — доступа нет
"""
import logging

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.audit import (
    audit_clear_confirm_kb,
    audit_menu_kb,
    audit_page_kb,
    audit_search_result_kb,
)
from bot.keyboards.main_menu import BTN, MAIN_KEYBOARD
from bot.models.audit import CATEGORY_LABELS
from bot.models.user import UserRole
from bot.services.audit_service import AuditService
from bot.services.user_service import UserService
from bot.states.audit import AuditSearch

router = Router()
logger = logging.getLogger(__name__)

# Все три административные роли имеют одинаковые права в журнале
_ADMIN_ROLES = UserRole.admin_roles()

_MENU_TEXT = (
    "━━━━━━━━━━━━━━━━━━━━\n"
    "📋 <b>Журнал действий</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "Выберите категорию для просмотра:"
)


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_dt(dt_str: str) -> str:
    """'2026-06-12 10:15:03' → '12.06.2026 • 10:15'."""
    try:
        date_part, time_part = dt_str[:16].split(" ")
        y, m, d = date_part.split("-")
        return f"{d}.{m}.{y} • {time_part}"
    except Exception:  # noqa: BLE001
        return dt_str


def _format_entry(row) -> str:
    """Форматирует одну запись журнала в виде карточки."""
    return (
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>#{row['id']:06d}</b>\n\n"
        f"{row['description']}\n\n"
        f"🕘 {_fmt_dt(row['created_at'])}\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )


def _page_text(category: str, records: list, total: int) -> str:
    label = CATEGORY_LABELS.get(category, category)
    header = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 <b>Журнал — {label}</b>\n"
        f"Всего записей: {total}\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    return header + "\n\n".join(_format_entry(r) for r in records)


# ─────────────────────────────────────────────────────────────────────────────
# Главный экран
# ─────────────────────────────────────────────────────────────────────────────

@router.message(F.text == BTN.AUDIT, StateFilter(None))
async def handle_audit_menu(
    message: Message,
    user_service: UserService,
) -> None:
    if not message.from_user:
        return
    role = await user_service.get_role(message.from_user.id)
    if role not in _ADMIN_ROLES:
        await message.answer(
            "🔒 <b>Доступ запрещён</b>\n\n"
            "Раздел «Журнал действий» доступен только администраторам клана."
        )
        return
    await message.answer(_MENU_TEXT, reply_markup=audit_menu_kb(role))


@router.callback_query(F.data == "alog:menu")
async def cb_audit_menu(
    callback: CallbackQuery,
    user_service: UserService,
) -> None:
    role = await user_service.get_role(callback.from_user.id)
    await callback.answer()
    await callback.message.edit_text(_MENU_TEXT, reply_markup=audit_menu_kb(role))


# ─────────────────────────────────────────────────────────────────────────────
# Просмотр категории с пагинацией     alog:cat:{category}:{page}
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("alog:cat:"))
async def cb_audit_view(
    callback: CallbackQuery,
    user_service: UserService,
    audit_service: AuditService,
) -> None:
    parts = callback.data.split(":")
    category = parts[2]
    page = int(parts[3])

    role = await user_service.get_role(callback.from_user.id)
    if role not in _ADMIN_ROLES:
        await callback.answer("🔒 Доступ запрещён.", show_alert=True)
        return

    records, total, total_pages = await audit_service.get_page(page, category)
    await callback.answer()

    if not records:
        label = CATEGORY_LABELS.get(category, category)
        await callback.message.edit_text(
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 <b>Журнал — {label}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Записей пока нет.",
            reply_markup=audit_page_kb(category, 0, 1),
        )
        return

    await callback.message.edit_text(
        _page_text(category, records, total),
        reply_markup=audit_page_kb(category, page, total_pages),
    )


@router.callback_query(F.data == "alog:noop")
async def cb_noop(callback: CallbackQuery) -> None:
    await callback.answer()


# ─────────────────────────────────────────────────────────────────────────────
# Поиск
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "alog:search")
async def cb_audit_search_start(
    callback: CallbackQuery,
    user_service: UserService,
    state: FSMContext,
) -> None:
    role = await user_service.get_role(callback.from_user.id)
    if role not in _ADMIN_ROLES:
        await callback.answer("🔒 Недостаточно прав.", show_alert=True)
        return
    await state.set_state(AuditSearch.waiting_query)
    await callback.answer()
    await callback.message.answer(
        "🔍 <b>Поиск в журнале</b>\n\n"
        "Введите один из вариантов:\n"
        "• Игровой ник — например: <code>ProGamer</code>\n"
        "• Тип действия — например: <code>news_create</code>\n"
        "• Дата — например: <code>12.06.2026</code>\n\n"
        "<i>/cancel для отмены</i>",
    )


@router.message(AuditSearch.waiting_query)
async def fsm_audit_search(
    message: Message,
    state: FSMContext,
    audit_service: AuditService,
) -> None:
    if not message.text or message.text.startswith("/"):
        await message.answer("⚠️ Введите поисковый запрос текстом.")
        return

    query = message.text.strip()
    results = await audit_service.search(query)
    await state.clear()

    if not results:
        await message.answer(
            f"🔍 <b>Поиск: «{query}»</b>\n\nНичего не найдено.",
            reply_markup=audit_search_result_kb(),
        )
        return

    entries = "\n\n".join(_format_entry(r) for r in results)
    await message.answer(
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🔍 <b>Результаты: «{query}»</b>\n"
        f"Найдено: {len(results)}\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        + entries,
        reply_markup=audit_search_result_kb(),
    )


@router.message(Command("cancel"), StateFilter(AuditSearch.waiting_query))
async def handle_cancel_search(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Поиск отменён.", reply_markup=MAIN_KEYBOARD)


# ─────────────────────────────────────────────────────────────────────────────
# Очистка журнала  (все административные роли)
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "alog:clear")
async def cb_audit_clear_confirm(
    callback: CallbackQuery,
    user_service: UserService,
) -> None:
    role = await user_service.get_role(callback.from_user.id)
    if role not in _ADMIN_ROLES:
        await callback.answer("🔒 Недостаточно прав.", show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(
        "🗑 <b>Очистка журнала</b>\n\n"
        "Все записи журнала будут безвозвратно удалены.\n\n"
        "Вы уверены?",
        reply_markup=audit_clear_confirm_kb(),
    )


@router.callback_query(F.data == "alog:clear_yes")
async def cb_audit_clear_execute(
    callback: CallbackQuery,
    user_service: UserService,
    audit_service: AuditService,
) -> None:
    role = await user_service.get_role(callback.from_user.id)
    if role not in _ADMIN_ROLES:
        await callback.answer("🔒 Недостаточно прав.", show_alert=True)
        return
    deleted = await audit_service.clear()
    logger.info(
        "%s %s очистил журнал аудита (%d записей)",
        role.value, callback.from_user.id, deleted,
    )
    await callback.answer(f"🗑 Удалено записей: {deleted}", show_alert=True)
    await callback.message.edit_text(
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📋 <b>Журнал действий</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ Журнал очищен. Удалено записей: <b>{deleted}</b>.\n\n"
        "Выберите категорию для просмотра:",
        reply_markup=audit_menu_kb(role),
    )
