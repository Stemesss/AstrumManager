# -*- coding: utf-8 -*-
"""
Обработчик раздела «👥 Участники».

Доступ: Лидер, Дитя клана, Старейшина.

Маршруты callback_data:
  admin:members / admin:roles  → меню раздела участников
  mem:menu                     → меню раздела участников
  mem:list:{page}              → список участников (просмотр)
  mem:card:{uid}               → карточка участника
  mem:role:{uid}               → выбор новой роли
  mem:set:{uid}:{role_value}   → применить роль + sync title + журнал
  mem:stats:{uid}              → статистика участника
  mem:del_list:{page}          → список участников (режим удаления)
  mem:del_search               → поиск для удаления (FSM)
  mem:del_card:{uid}           → карточка удаления с подтверждением
  mem:del_ok:{uid}             → выполнить удаление
  mem:season                   → подтверждение нового сезона
  mem:season_ok                → выполнить сброс сезона
  mem:noop                     → индикатор страницы (без действия)
  mem:close                    → удалить сообщение

  Раздел «Участники» в главном меню (только просмотр, без прав администратора):
  memv:list:{page}             → список участников (просмотр)
  memv:card:{uid}:{page}       → карточка участника (просмотр)
  memv:noop                    → индикатор страницы (без действия)
  memv:close                   → удалить сообщение
"""
import asyncio
import datetime
import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.admin_panel import AdminBtn
from bot.keyboards.main_menu import BTN, MAIN_KEYBOARD
from bot.database.db import Database
from bot.keyboards.members import (
    PAGE_SIZE,
    MemberBtn,
    MemberViewBtn,
    clean_absent_confirm_kb,
    delete_card_kb,
    delete_list_kb,
    delete_search_result_kb,
    history_kb,
    member_card_kb,
    members_list_kb,
    members_menu_kb,
    nick_report_kb,
    notes_kb,
    role_select_kb,
    season_confirm_kb,
    view_card_kb,
    view_list_kb,
    warnings_kb,
)
from bot.keyboards.nav import CANCEL_KB
from bot.models.audit import AuditAction
from bot.models.user import User, UserRole
from bot.services.audit_service import AuditService
from bot.services.stats_service import StatsService
from bot.services.topic_service import TopicService
from bot.services.user_service import UserService
from bot.handlers.synctitles import run_sync_titles
from bot.states.members import MemberDelete, MemberNickEdit, MemberNoteAdd, MemberWarnAdd
from bot.utils.nick_format import validate_name
from bot.utils.roles import ROLE_DISPLAY_ICONS, ROLE_ORDER, assignable_roles, can_assign, role_label
from bot.utils.sync_title import build_admin_title, sync_admin_title
from bot.utils.text import pluralize_days

router = Router()
logger = logging.getLogger(__name__)

_ICONS: dict[UserRole, str] = ROLE_DISPLAY_ICONS

_SUPERUSER_ID = 8490615925

_DIVIDER = "━━━━━━━━━━━━━━━━"

_MENU_TEXT = (
    "👥 <b>Управление участниками</b>\n\n"
    f"{_DIVIDER}\n\n"
    "Выберите действие:"
)


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────────────────────────────────────

def _sort_users(users: list[User]) -> list[User]:
    order = {r: i for i, r in enumerate(ROLE_ORDER)}
    return sorted(
        users,
        key=lambda u: (
            1 if not u.game_nick else 0,
            order.get(u.role, 99),
            (u.game_nick or u.first_name).lower(),
        ),
    )


def _display_name(u: User) -> str:
    return u.game_nick or u.first_name


def _effective_role(actor_id: int, actor_role: UserRole) -> UserRole:
    return UserRole.LEADER if actor_id == _SUPERUSER_ID else actor_role


async def _card_text(u: User, user_service: UserService, stats_service: StatsService) -> str:
    """Единая карточка участника — используется и в администрировании, и в просмотре."""
    username_line = f"@{u.username}" if u.username else u.first_name

    if not u.game_nick:
        return (
            "🆕 <b>Не зарегистрирован</b>\n"
            f"👤 <b>{u.first_name}</b>\n\n"
            f"{_DIVIDER}\n\n"
            "Участник состоит в группе, но ещё не запустил бота "
            "и не задал игровой ник.\n\n"
            f"{_DIVIDER}\n\n"
            f"📱 {username_line}\n"
            f"🆔 <code>{u.telegram_id}</code>"
        )

    days = await user_service.get_days_in_clan(u.telegram_id)
    score = (await stats_service.user_activity(u.telegram_id))["score"]
    title = build_admin_title(u.role, u.game_nick) if u.game_nick else ""

    return (
        f"{role_label(u.role)}\n"
        f"🎮 <b>{u.game_nick or u.first_name}</b>\n\n"
        f"{_DIVIDER}\n\n"
        f"🏷 <b>Telegram-титул:</b> {title or '—'}\n"
        f"🟢 <b>Статус:</b> Активен\n\n"
        f"{_DIVIDER}\n\n"
        f"🏆 <b>Очков активности:</b> {score}\n"
        f"📅 <b>В клане:</b> {pluralize_days(days)}\n\n"
        f"{_DIVIDER}\n\n"
        f"📱 {username_line}\n"
        f"🆔 <code>{u.telegram_id}</code>"
    )


async def _check_admin(cb: CallbackQuery, user_service: UserService) -> bool:
    role = await user_service.get_role(cb.from_user.id)
    if role not in UserRole.admin_roles():
        await cb.answer("🔒 Недостаточно прав.", show_alert=True)
        return False
    return True


async def _find_user(user_service: UserService, user_id: int) -> User | None:
    for u in await user_service.get_all_users():
        if u.telegram_id == user_id:
            return u
    return None


async def _show_menu(cb: CallbackQuery) -> None:
    try:
        await cb.message.edit_text(_MENU_TEXT, reply_markup=members_menu_kb())
    except Exception:
        await cb.message.answer(_MENU_TEXT, reply_markup=members_menu_kb())


async def _show_list(
    cb: CallbackQuery,
    user_service: UserService,
    page: int,
    telethon_sync=None,
    db=None,
    group_chat_id: int | None = None,
    bot: Bot | None = None,
) -> None:
    # Используем тот же источник данных, что и раздел «Главное меню → Участники»
    all_users = await _view_list_users(user_service, bot, group_chat_id, telethon_sync, db)
    total = len(all_users)
    page_users = all_users[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    text = (
        f"👥 <b>Участники клана</b>\n\n"
        f"👤 Всего участников: {total}\n\n"
        "Выберите участника:"
    )
    kb = members_list_kb(page_users, page, total)
    try:
        await cb.message.edit_text(text, reply_markup=kb)
    except Exception:
        await cb.message.answer(text, reply_markup=kb)


async def _show_delete_list(
    cb: CallbackQuery, user_service: UserService, page: int
) -> None:
    all_users = _sort_users(await user_service.get_all_users())
    total = len(all_users)
    page_users = all_users[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    text = (
        f"🗑️ <b>Удалить участника</b>\n\n"
        f"{_DIVIDER}\n\n"
        f"👤 Всего: {total}\n\n"
        "Выберите участника для удаления:"
    )
    kb = delete_list_kb(page_users, page, total)
    try:
        await cb.message.edit_text(text, reply_markup=kb)
    except Exception:
        await cb.message.answer(text, reply_markup=kb)


def _is_test_user(u: User) -> bool:
    """Возвращает True, если пользователь является тестовым (по суффиксам в нике)."""
    nick = (u.game_nick or "").strip()
    return "(Test)" in nick or "(T)" in nick


async def _view_list_users(
    user_service: UserService,
    bot: Bot | None = None,
    group_chat_id: int | None = None,
    telethon_sync=None,
    db=None,
) -> list[User]:
    """Список участников для обычного просмотра.

    Показывает всех актуальных участников Telegram-группы — включая тех, кто
    ещё не зарегистрирован (не задал игровой ник), с пометкой «🆕 Не
    зарегистрирован». Фильтрует:
    • пользователей с суффиксом (Test) или (T) в нике;
    • пользователей, отсутствующих в Telegram-группе.

    Сначала пробует Telethon (один запрос, быстро).
    Если Telethon недоступен — Bot API (по запросу на участника, медленно).
    При ошибке API пользователь включается в список (fail-open).
    """
    users = [
        u for u in await user_service.get_all_users()
        if not _is_test_user(u)
    ]

    if group_chat_id:
        # Приоритет: Telethon — один MTProto-запрос вместо N Bot API вызовов
        active_ids: set[int] | None = None
        if telethon_sync is not None and db is not None:
            active_ids = await telethon_sync.sync_and_get_ids(group_chat_id, db)

        if active_ids is not None:
            from bot.utils.group_filter import filter_by_active_ids
            users = filter_by_active_ids(users, lambda u: u.telegram_id, active_ids)
        elif bot:
            # Fallback: Bot API — по одному запросу на пользователя
            filtered: list[User] = []
            for u in users:
                try:
                    member = await bot.get_chat_member(group_chat_id, u.telegram_id)
                    if member.status not in ("left", "kicked"):
                        filtered.append(u)
                except TelegramBadRequest as e:
                    err = str(e).lower()
                    if any(k in err for k in ("user not found", "participant", "user_not_participant")):
                        pass  # подтверждено отсутствие — не показываем
                    else:
                        filtered.append(u)  # неизвестная ошибка — включаем
                except TelegramRetryAfter as e:
                    await asyncio.sleep(e.retry_after + 1)
                    filtered.append(u)  # после ожидания включаем без повторной проверки
                except Exception:
                    filtered.append(u)  # ошибка API — включаем (fail-open)
                await asyncio.sleep(0.05)
            users = filtered

    return _sort_users(users)


# ─────────────────────────────────────────────────────────────────────────────
# Главное меню → «Участники» (только просмотр, без прав администратора)
# ─────────────────────────────────────────────────────────────────────────────

@router.message(F.text == BTN.MEMBERS)
async def handle_members_view(
    message: Message,
    user_service: UserService,
    bot: Bot,
    group_chat_id: int,
    telethon_sync=None,
    db=None,
) -> None:
    """Красивый просмотр списка участников — без административных функций.

    Фильтрует тестовых пользователей (Test)/(T) и отсутствующих в группе.
    Использует Telethon как основной источник; Bot API — как fallback.
    """
    all_users = await _view_list_users(user_service, bot, group_chat_id, telethon_sync, db)
    total = len(all_users)
    if total == 0:
        await message.answer("👥 <b>Участники</b>\n\nСписок пока пуст.")
        return
    page_users = all_users[:PAGE_SIZE]
    text = (
        f"👥 <b>Участники клана</b>\n\n"
        f"👤 Всего участников: {total}\n\n"
        "Выберите участника:"
    )
    await message.answer(text, reply_markup=view_list_kb(page_users, 0, total))


@router.callback_query(F.data.startswith("memv:list:"))
async def cb_memv_list(
    callback: CallbackQuery,
    user_service: UserService,
    bot: Bot,
    group_chat_id: int,
    telethon_sync=None,
    db=None,
) -> None:
    page = int(callback.data.split(":")[2])
    all_users = await _view_list_users(user_service, bot, group_chat_id, telethon_sync, db)
    total = len(all_users)
    page_users = all_users[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    text = (
        f"👥 <b>Участники клана</b>\n\n"
        f"👤 Всего участников: {total}\n\n"
        "Выберите участника:"
    )
    kb = view_list_kb(page_users, page, total)
    await callback.answer()
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("memv:card:"))
async def cb_memv_card(
    callback: CallbackQuery, user_service: UserService, stats_service: StatsService
) -> None:
    parts = callback.data.split(":")
    user_id = int(parts[2])
    page = int(parts[3]) if len(parts) > 3 else 0
    u = await _find_user(user_service, user_id)
    if not u:
        await callback.answer("Участник не найден.", show_alert=True)
        return
    await callback.answer()
    text = await _card_text(u, user_service, stats_service)
    try:
        await callback.message.edit_text(text, reply_markup=view_card_kb(user_id, page))
    except Exception:
        await callback.message.answer(text, reply_markup=view_card_kb(user_id, page))


@router.callback_query(F.data == MemberViewBtn.NOOP)
async def cb_memv_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data == MemberViewBtn.CLOSE)
async def cb_memv_close(callback: CallbackQuery) -> None:
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Вход из панели администрации → меню участников
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == AdminBtn.MEMBERS)
async def cb_admin_members(callback: CallbackQuery, user_service: UserService) -> None:
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()
    await _show_menu(callback)


@router.callback_query(F.data == AdminBtn.ROLES)
async def cb_admin_roles(callback: CallbackQuery, user_service: UserService) -> None:
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()
    await _show_menu(callback)


@router.callback_query(F.data == MemberBtn.MENU)
async def cb_mem_menu(callback: CallbackQuery, user_service: UserService) -> None:
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()
    await _show_menu(callback)


# ─────────────────────────────────────────────────────────────────────────────
# Навигация по списку (просмотр)
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("mem:list:"))
async def cb_mem_list(
    callback: CallbackQuery,
    user_service: UserService,
    bot: Bot,
    group_chat_id: int,
    telethon_sync=None,
    db=None,
) -> None:
    if not await _check_admin(callback, user_service):
        return
    page = int(callback.data.split(":")[2])
    await callback.answer()
    await _show_list(callback, user_service, page, telethon_sync, db, group_chat_id, bot)


@router.callback_query(F.data == MemberBtn.NOOP)
async def cb_mem_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data == MemberBtn.CLOSE)
async def cb_mem_close(callback: CallbackQuery) -> None:
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Карточка участника
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("mem:card:"))
async def cb_mem_card(
    callback: CallbackQuery, user_service: UserService, stats_service: StatsService
) -> None:
    if not await _check_admin(callback, user_service):
        return
    user_id = int(callback.data.split(":")[2])
    u = await _find_user(user_service, user_id)
    if not u:
        await callback.answer("Участник не найден.", show_alert=True)
        return
    await callback.answer()
    text = await _card_text(u, user_service, stats_service)
    await callback.message.edit_text(text, reply_markup=member_card_kb(user_id))


# ─────────────────────────────────────────────────────────────────────────────
# Выбор новой роли
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("mem:role:"))
async def cb_mem_role(callback: CallbackQuery, user_service: UserService) -> None:
    if not await _check_admin(callback, user_service):
        return
    target_id = int(callback.data.split(":")[2])
    actor_id = callback.from_user.id
    actor_role = await user_service.get_role(actor_id)
    eff_role = _effective_role(actor_id, actor_role)

    if not assignable_roles(eff_role):
        await callback.answer("🔒 Вы не можете изменять роли.", show_alert=True)
        return

    u = await _find_user(user_service, target_id)
    if not u:
        await callback.answer("Участник не найден.", show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text(
        f"🏷 <b>Изменить роль</b>\n\nВыберите новую роль для <b>{_display_name(u)}</b>:",
        reply_markup=role_select_kb(eff_role, target_id),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Применение роли
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("mem:set:"))
async def cb_mem_set(
    callback: CallbackQuery,
    user_service: UserService,
    audit_service: AuditService,
    stats_service: StatsService,
    bot: Bot,
    group_chat_id: int,
) -> None:
    if not await _check_admin(callback, user_service):
        return

    parts = callback.data.split(":", 3)
    target_id = int(parts[2])
    role_value = parts[3]

    new_role = UserRole.from_str(role_value)
    actor_id = callback.from_user.id
    actor_role = await user_service.get_role(actor_id)
    eff_role = _effective_role(actor_id, actor_role)

    if not can_assign(eff_role, new_role):
        await callback.answer("⛔ Недостаточно прав.", show_alert=True)
        return

    await user_service.set_role(target_id, new_role)
    confirmed = await user_service.get_role(target_id)

    actor_nick  = await user_service.get_game_nick(actor_id) or str(actor_id)
    target_nick = await user_service.get_game_nick(target_id) or str(target_id)

    await audit_service.log(
        user_id=actor_id,
        game_nick=actor_nick,
        role=actor_role,
        action_type=AuditAction.MEMBER_ROLE_SET,
        description=(
            f"{role_label(actor_role)} {actor_nick} назначил роль "
            f"{role_label(confirmed)} участнику {target_nick}"
        ),
        target_id=target_id,
    )

    logger.info(
        "%s (роль: %s) назначил роль %r участнику %s",
        actor_id, actor_role.value, confirmed.value, target_id,
    )

    tg_error = await sync_admin_title(
        bot, group_chat_id, target_id, confirmed, game_nick=target_nick
    )

    icon = _ICONS.get(confirmed, "◇")
    if tg_error:
        tg_note = f"\n\n{tg_error}"
    else:
        actual_title = build_admin_title(confirmed, target_nick)
        tg_note = f"\n\n✅ Telegram-титул установлен: «{actual_title}»"

    u = await _find_user(user_service, target_id)
    card = f"\n\n{await _card_text(u, user_service, stats_service)}" if u else ""

    await callback.answer(f"✅ {icon} {confirmed.value}", show_alert=False)
    await callback.message.edit_text(
        f"✅ <b>Роль успешно изменена.</b>\n\n"
        f"Новый тег:\n{icon} {confirmed.value}"
        f"{tg_note}"
        f"{card}",
        reply_markup=member_card_kb(target_id),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Смена игрового ника (из карточки участника, административное действие)
# ─────────────────────────────────────────────────────────────────────────────

_NICK_EDIT_PROMPT = (
    "✏️ <b>Введите новый игровой ник участника:</b>\n\n"
    "• от 3 до 20 символов\n"
    "• только буквы, цифры, пробел, дефис\n"
    "• без эмодзи и спецсимволов\n"
    "• только имя, без титулов"
)


@router.callback_query(F.data.startswith("mem:nick:"))
async def cb_mem_nick_start(
    callback: CallbackQuery, user_service: UserService, state: FSMContext
) -> None:
    if not await _check_admin(callback, user_service):
        return
    target_id = int(callback.data.split(":")[2])
    u = await _find_user(user_service, target_id)
    if not u:
        await callback.answer("Участник не найден.", show_alert=True)
        return

    await state.set_state(MemberNickEdit.waiting_name)
    await state.update_data(target_id=target_id)
    await callback.answer()
    await callback.message.answer(_NICK_EDIT_PROMPT, reply_markup=CANCEL_KB)


@router.message(MemberNickEdit.waiting_name)
async def fsm_mem_nick_enter(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    audit_service: AuditService,
    stats_service: StatsService,
    bot: Bot,
    group_chat_id: int,
) -> None:
    data = await state.get_data()
    target_id = data.get("target_id")

    if not message.text or message.text.startswith("/"):
        await message.answer(_NICK_EDIT_PROMPT, reply_markup=CANCEL_KB)
        return

    new_name, error = validate_name(message.text)
    if error:
        await message.answer(error, reply_markup=CANCEL_KB)
        return

    await state.clear()

    u = await _find_user(user_service, target_id)
    if not u:
        await message.answer("Участник не найден.", reply_markup=MAIN_KEYBOARD)
        return

    old_name = u.game_nick or "?"
    role = u.role
    actor_id = message.from_user.id
    actor_role = await user_service.get_role(actor_id)
    actor_nick = await user_service.get_game_nick(actor_id) or str(actor_id)

    await user_service.set_game_nick(target_id, new_name)

    old_title = build_admin_title(role, old_name) if old_name != "?" else old_name
    new_title = build_admin_title(role, new_name)

    await audit_service.log(
        user_id=actor_id,
        game_nick=actor_nick,
        role=actor_role,
        action_type=AuditAction.MEMBER_NICK_CHANGE,
        description=(
            f"{role_label(actor_role)} {actor_nick} изменил ник участнику "
            f"{old_title} → {new_title}"
        ),
        target_id=target_id,
    )

    logger.info(
        "%s сменил ник участнику %s: %r → %r",
        actor_id, target_id, old_name, new_name,
    )

    tg_error = await sync_admin_title(bot, group_chat_id, target_id, role, game_nick=new_name)

    u = await _find_user(user_service, target_id)
    card = await _card_text(u, user_service, stats_service) if u else ""

    tg_note = f"\n\n{tg_error}" if tg_error else f"\n\n✅ Telegram-титул обновлён: «{new_title}»"

    await message.answer(
        f"✅ <b>Ник успешно изменён.</b>{tg_note}\n\n{card}",
        reply_markup=member_card_kb(target_id),
    )
    await message.answer("⚜️ <b>AstrumManager</b>  •  Главное меню", reply_markup=MAIN_KEYBOARD)


# ─────────────────────────────────────────────────────────────────────────────
# Статистика участника
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("mem:stats:"))
async def cb_mem_stats(
    callback: CallbackQuery,
    user_service: UserService,
    stats_service: StatsService,
) -> None:
    if not await _check_admin(callback, user_service):
        return
    target_id = int(callback.data.split(":")[2])
    u = await _find_user(user_service, target_id)
    nick = _display_name(u) if u else str(target_id)

    days  = await user_service.get_days_in_clan(target_id)
    stats = await stats_service.user_activity(target_id)

    score   = stats["score"]
    n_news  = stats["news"]
    n_event = stats["events"]

    lines = [
        f"📊 <b>Статистика — {nick}</b>",
        "",
        _DIVIDER,
        "",
        f"📅 Дней в клане: <b>{days}</b>",
        f"⭐ Очков активности: <b>{score}</b>",
        "",
        _DIVIDER,
        "",
        "📦 <b>Публикации</b>",
        f"📰 Новостей: <b>{n_news}</b>",
        f"📅 Событий: <b>{n_event}</b>",
    ]

    await callback.answer()
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=member_card_kb(target_id),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Удаление участника — список
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("mem:del_list:"))
async def cb_mem_del_list(callback: CallbackQuery, user_service: UserService) -> None:
    if not await _check_admin(callback, user_service):
        return
    page = int(callback.data.split(":")[2])
    await callback.answer()
    await _show_delete_list(callback, user_service, page)


# ─────────────────────────────────────────────────────────────────────────────
# Удаление участника — поиск (FSM)
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == MemberBtn.DEL_SEARCH)
async def cb_mem_del_search(
    callback: CallbackQuery, user_service: UserService, state: FSMContext
) -> None:
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()
    await state.set_state(MemberDelete.waiting_search)
    await callback.message.answer(
        "🔍 <b>Поиск участника</b>\n\n"
        "Введите <b>игровой ник</b>, <b>имя</b> или <b>Telegram ID</b>:",
        reply_markup=CANCEL_KB,
    )


@router.message(MemberDelete.waiting_search)
async def handle_mem_search(
    message: Message, user_service: UserService, state: FSMContext
) -> None:
    await state.clear()
    query = (message.text or "").strip()
    if not query:
        await message.answer("Поисковый запрос не может быть пустым.")
        return

    all_users = await user_service.get_all_users()
    query_lower = query.lower()

    matched: list[User] = []
    for u in all_users:
        if query.isdigit() and u.telegram_id == int(query):
            matched.append(u)
        elif query_lower in (u.game_nick or "").lower():
            matched.append(u)
        elif query_lower in u.first_name.lower():
            matched.append(u)

    if not matched:
        await message.answer(
            f"🔍 По запросу «{query}» ничего не найдено.\n\n"
            "Попробуйте другой ник или ID.",
            reply_markup=delete_search_result_kb([]),
        )
        return

    await message.answer(
        f"🔍 <b>Результаты поиска:</b> «{query}»\n\n"
        f"Найдено: {len(matched)}\n\n"
        "Выберите участника для удаления:",
        reply_markup=delete_search_result_kb(_sort_users(matched)),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Удаление участника — карточка с подтверждением
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("mem:del_card:"))
async def cb_mem_del_card(callback: CallbackQuery, user_service: UserService) -> None:
    if not await _check_admin(callback, user_service):
        return
    target_id = int(callback.data.split(":")[2])
    u = await _find_user(user_service, target_id)
    if not u:
        await callback.answer("Участник не найден.", show_alert=True)
        return

    actor_id = callback.from_user.id
    name = _display_name(u)
    username_line = f"@{u.username}" if u.username else u.first_name

    text = (
        f"🗑️ <b>Удалить участника?</b>\n\n"
        f"{role_label(u.role)}\n"
        f"🎮 <b>{name}</b>\n"
        f"📱 {username_line}\n"
        f"🆔 <code>{u.telegram_id}</code>\n\n"
        f"{_DIVIDER}\n\n"
        "После удаления будут стёрты:\n"
        "• запись участника\n"
        "• вся история активности\n"
        "• обращения в поддержку\n\n"
        "<b>Это действие необратимо.</b>"
    )

    # Проверяем ограничения заранее, чтобы сразу показать причину
    if target_id == _SUPERUSER_ID:
        text = "⛔ Невозможно удалить суперпользователя."
        await callback.answer()
        await callback.message.edit_text(
            text,
            reply_markup=delete_card_kb(target_id, name),
        )
        return
    if target_id == actor_id:
        await callback.answer("Нельзя удалить самого себя.", show_alert=True)
        return
    if u.role == UserRole.LEADER:
        await callback.answer("Невозможно удалить владельца проекта.", show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text(text, reply_markup=delete_card_kb(target_id, name))


# ─────────────────────────────────────────────────────────────────────────────
# Удаление участника — подтверждено
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("mem:del_ok:"))
async def cb_mem_del_ok(
    callback: CallbackQuery,
    user_service: UserService,
    audit_service: AuditService,
) -> None:
    if not await _check_admin(callback, user_service):
        return

    target_id = int(callback.data.split(":")[2])
    actor_id = callback.from_user.id

    u = await _find_user(user_service, target_id)
    target_name = _display_name(u) if u else str(target_id)

    result = await user_service.delete_member(actor_id, target_id)
    if not result["ok"]:
        await callback.answer(result["error"], show_alert=True)
        return

    actor_nick = await user_service.get_game_nick(actor_id) or str(actor_id)
    actor_role = await user_service.get_role(actor_id)

    await audit_service.log(
        user_id=actor_id,
        game_nick=actor_nick,
        role=actor_role,
        action_type=AuditAction.MEMBER_DELETE,
        description=f"{role_label(actor_role)} {actor_nick} удалил участника {target_name} (ID: {target_id})",
        target_id=target_id,
    )

    logger.info("Участник %s (%s) удалён администратором %s", target_id, target_name, actor_id)

    await callback.answer(f"✅ Участник «{target_name}» удалён.", show_alert=False)

    all_users = _sort_users(await user_service.get_all_users())
    total = len(all_users)
    page_users = all_users[:PAGE_SIZE]
    text = (
        f"✅ <b>Участник «{target_name}» удалён.</b>\n\n"
        f"🗑️ <b>Удалить участника</b>\n\nВсего: {total}\n\nВыберите участника для удаления:"
    )
    try:
        await callback.message.edit_text(text, reply_markup=delete_list_kb(page_users, 0, total))
    except Exception:
        await callback.message.answer(text, reply_markup=delete_list_kb(page_users, 0, total))


# ─────────────────────────────────────────────────────────────────────────────
# Новый сезон — подтверждение
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == MemberBtn.SEASON)
async def cb_mem_season(callback: CallbackQuery, user_service: UserService) -> None:
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()

    all_users = await user_service.get_all_users()
    total = len(all_users)

    text = (
        "🧹 <b>Новый сезон</b>\n\n"
        "⚠️ <b>Внимание! Это действие необратимо.</b>\n\n"
        "Будет выполнено:\n"
        "✅ Резервная копия базы данных\n"
        "✅ Сброс очков всех участников\n"
        "✅ Очистка журнала активности\n"
        "✅ Очистка истории начислений\n"
        "✅ Очистка сезонной статистики\n\n"
        "Будет сохранено:\n"
        "🔒 Все участники и роли\n"
        "🔒 Настройки и конфигурация\n"
        "🔒 Форумные темы\n"
        "🔒 Новости и контент\n\n"
        f"👥 Участников в базе: <b>{total}</b>\n\n"
        "Подтвердите запуск нового сезона:"
    )
    try:
        await callback.message.edit_text(text, reply_markup=season_confirm_kb())
    except Exception:
        await callback.message.answer(text, reply_markup=season_confirm_kb())


# ─────────────────────────────────────────────────────────────────────────────
# Новый сезон — выполнение
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == MemberBtn.SEASON_OK)
async def cb_mem_season_ok(
    callback: CallbackQuery,
    user_service: UserService,
    audit_service: AuditService,
) -> None:
    if not await _check_admin(callback, user_service):
        return

    actor_id = callback.from_user.id
    actor_role = await user_service.get_role(actor_id)

    # Только Лидер или суперпользователь могут запускать новый сезон
    if actor_role != UserRole.LEADER and actor_id != _SUPERUSER_ID:
        await callback.answer("⛔ Только Лидер клана может запустить новый сезон.", show_alert=True)
        return

    await callback.answer("⏳ Выполняется сброс сезона...")

    started_at = datetime.datetime.now()

    try:
        result = await user_service.new_season()
    except Exception as exc:
        logger.error("Ошибка при сбросе сезона: %s", exc)
        await callback.message.edit_text(
            f"❌ <b>Ошибка при запуске нового сезона:</b>\n\n<code>{exc}</code>",
            reply_markup=season_confirm_kb(),
        )
        return

    elapsed = (datetime.datetime.now() - started_at).total_seconds()

    actor_nick = await user_service.get_game_nick(actor_id) or str(actor_id)

    await audit_service.log(
        user_id=actor_id,
        game_nick=actor_nick,
        role=actor_role,
        action_type=AuditAction.SEASON_RESET,
        description=(
            f"{role_label(actor_role)} {actor_nick} запустил новый сезон: "
            f"сброшено {result['logs_deleted']} записей активности, "
            f"участников сохранено: {result['users_count']}"
        ),
    )

    logger.info(
        "Новый сезон запущен администратором %s: участников=%s, журналов удалено=%s, бэкап=%s",
        actor_id, result["users_count"], result["logs_deleted"], result["backup_path"],
    )

    backup_name = result["backup_path"].split("/")[-1]

    report = (
        "✅ <b>Новый сезон успешно запущен!</b>\n\n"
        "📊 <b>Отчёт:</b>\n"
        f"👥 Участников сохранено: <b>{result['users_count']}</b>\n"
        f"🗑️ Журналов активности очищено: <b>{result['logs_deleted']}</b>\n"
        f"⏱ Время выполнения: <b>{elapsed:.2f} сек.</b>\n"
        f"💾 Резервная копия: <code>{backup_name}</code>\n\n"
        "Все очки обнулены. Сезонная статистика сброшена.\n"
        "Участники, роли и контент сохранены."
    )

    try:
        await callback.message.edit_text(report, reply_markup=members_menu_kb())
    except Exception:
        await callback.message.answer(report, reply_markup=members_menu_kb())


# ─────────────────────────────────────────────────────────────────────────────
# Полная синхронизация Telegram-титулов (кнопка = логика команды /synctitles)
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == MemberBtn.SYNC_TITLES)
async def cb_mem_sync_titles(
    callback: CallbackQuery,
    user_service: UserService,
    audit_service: AuditService,
    bot: Bot,
    group_chat_id: int,
) -> None:
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()
    await run_sync_titles(
        actor_id=callback.from_user.id,
        reply=callback.message.answer,
        user_service=user_service,
        audit_service=audit_service,
        bot=bot,
        group_chat_id=group_chat_id,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Очистить отсутствующих — предварительный просмотр
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == MemberBtn.CLEAN_ABSENT)
async def cb_mem_clean_absent(
    callback: CallbackQuery,
    user_service: UserService,
    bot: Bot,
    group_chat_id: int,
) -> None:
    """Проверяет участников через getChatMember, показывает список отсутствующих."""
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()

    all_users = await user_service.get_all_users()
    actor_id = callback.from_user.id

    # Временное сообщение о прогрессе
    try:
        await callback.message.edit_text(
            f"⏳ <b>Проверка участников...</b>\n\nПроверяю {len(all_users)} записей..."
        )
    except Exception:
        pass

    absent: list[tuple[str, int, str]] = []  # (display_name, telegram_id, status_label)

    for u in all_users:
        # Защита — суперпользователь, сам себя, Лидер
        if u.telegram_id == _SUPERUSER_ID or u.telegram_id == actor_id:
            continue
        if u.role == UserRole.LEADER:
            continue

        display = u.game_nick or u.first_name
        try:
            member = await bot.get_chat_member(group_chat_id, u.telegram_id)
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)
            try:
                member = await bot.get_chat_member(group_chat_id, u.telegram_id)
            except Exception:
                absent.append((display, u.telegram_id, "не найден"))
                continue
        except TelegramBadRequest as e:
            err = str(e).lower()
            if any(k in err for k in ("user not found", "participant", "user_not_participant")):
                absent.append((display, u.telegram_id, "не в группе"))
            continue
        except Exception:
            continue

        if member.status == "creator":
            continue  # владелец группы — всегда защищён
        if member.status in ("left", "kicked"):
            status_label = "покинул группу" if member.status == "left" else "исключён"
            absent.append((display, u.telegram_id, status_label))

        await asyncio.sleep(0.1)

    if not absent:
        try:
            await callback.message.edit_text(
                "✅ <b>Все участники присутствуют в группе.</b>\n\n"
                "Отсутствующих не обнаружено.",
                reply_markup=members_menu_kb(),
            )
        except Exception:
            await callback.message.answer(
                "✅ Все участники присутствуют в группе.",
                reply_markup=members_menu_kb(),
            )
        return

    lines = [
        f"🧹 <b>Очистить отсутствующих</b>",
        "",
        f"Найдено {len(absent)} участников не в группе:",
        "",
    ]
    for name, uid, status in absent:
        lines.append(f"• <b>{name}</b> (ID: <code>{uid}</code>) — {status}")

    lines += [
        "",
        "⚠️ После подтверждения они будут удалены из базы данных.",
        "<b>Это действие необратимо.</b>",
    ]

    text = "\n".join(lines)
    kb = clean_absent_confirm_kb(len(absent))
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)


# ─────────────────────────────────────────────────────────────────────────────
# Очистить отсутствующих — выполнение
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == MemberBtn.CLEAN_ABSENT_OK)
async def cb_mem_clean_absent_ok(
    callback: CallbackQuery,
    user_service: UserService,
    audit_service: AuditService,
    bot: Bot,
    group_chat_id: int,
) -> None:
    """Удаляет из БД участников, отсутствующих в Telegram-группе."""
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()

    actor_id = callback.from_user.id
    actor_role = await user_service.get_role(actor_id)
    actor_nick = await user_service.get_game_nick(actor_id) or str(actor_id)
    all_users = await user_service.get_all_users()

    try:
        await callback.message.edit_text("⏳ <b>Выполняется очистка...</b>")
    except Exception:
        pass

    removed: list[str]  = []
    skipped: list[str]  = []
    errors:  list[str]  = []

    for u in all_users:
        # Защита
        if u.telegram_id == _SUPERUSER_ID or u.telegram_id == actor_id:
            continue
        if u.role == UserRole.LEADER:
            continue

        display = u.game_nick or u.first_name

        # Проверяем статус в группе.
        # ВАЖНО: удалять из БД только при ПОДТВЕРЖДЁННОМ отсутствии.
        # Сбой API (даже после retry) → пропускаем, не удаляем.
        is_absent = False

        try:
            member = await bot.get_chat_member(group_chat_id, u.telegram_id)
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)
            try:
                member = await bot.get_chat_member(group_chat_id, u.telegram_id)
            except TelegramBadRequest as e2:
                err2 = str(e2).lower()
                if any(k in err2 for k in ("user not found", "participant", "user_not_participant")):
                    is_absent = True  # подтверждено: не в группе
                else:
                    skipped.append(f"{display}: ошибка API после повторной попытки")
                    continue
            except Exception:
                # Не удалось проверить даже после retry — пропускаем, НЕ удаляем
                skipped.append(f"{display}: не удалось проверить (API недоступен)")
                continue
            else:
                if member.status == "creator":
                    continue
                if member.status not in ("left", "kicked"):
                    continue
                is_absent = True
        except TelegramBadRequest as e:
            err = str(e).lower()
            if any(k in err for k in ("user not found", "participant", "user_not_participant")):
                is_absent = True  # подтверждено: не является участником
            else:
                skipped.append(f"{display}: ошибка API")
                continue
        except Exception as exc:
            skipped.append(f"{display}: {exc}")
            continue
        else:
            # Успешно получили — проверяем статус
            if member.status == "creator":
                continue
            if member.status not in ("left", "kicked"):
                continue  # присутствует в группе — не трогаем
            is_absent = True

        if not is_absent:
            continue

        # ── Пытаемся снять права администратора ─────────────────────────
        try:
            await bot.promote_chat_member(
                chat_id=group_chat_id,
                user_id=u.telegram_id,
                can_manage_chat=False,
                can_delete_messages=False,
                can_manage_video_chats=False,
                can_restrict_members=False,
                can_promote_members=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False,
            )
        except Exception:
            pass  # уже нет прав или уже не в группе — OK

        # ── Удаляем из БД ───────────────────────────────────────────────
        result = await user_service.delete_member(actor_id, u.telegram_id)
        if result["ok"]:
            removed.append(display)
        else:
            errors.append(f"{display}: {result['error']}")

        await asyncio.sleep(0.1)

    # ── Журнал аудита ────────────────────────────────────────────────────
    await audit_service.log(
        user_id=actor_id,
        game_nick=actor_nick,
        role=actor_role,
        action_type=AuditAction.CLEAN_ABSENT,
        description=(
            f"{role_label(actor_role)} {actor_nick} очистил отсутствующих: "
            f"удалено {len(removed)}, пропущено {len(skipped)}, ошибок {len(errors)}. "
            f"Удалены: {', '.join(removed) or '—'}"
        ),
    )
    logger.info(
        "clean_absent: actor=%s removed=%d skipped=%d errors=%d",
        actor_id, len(removed), len(skipped), len(errors),
    )

    # ── Отчёт ────────────────────────────────────────────────────────────
    lines = [
        "✅ <b>Очистка завершена</b>",
        "",
        f"🗑️ Удалено из БД: <b>{len(removed)}</b>",
        f"⏭️ Пропущено: <b>{len(skipped)}</b>",
        f"❌ Ошибок: <b>{len(errors)}</b>",
    ]
    if removed:
        lines += ["", "🗑️ <b>Удалены:</b>"]
        lines += [f"  • {n}" for n in removed]
    if skipped:
        lines += ["", "⏭️ <b>Пропущено:</b>"]
        lines += [f"  • {s}" for s in skipped]
    if errors:
        lines += ["", "❌ <b>Ошибки:</b>"]
        lines += [f"  • {e}" for e in errors]

    report = "\n".join(lines)
    try:
        await callback.message.edit_text(report, reply_markup=members_menu_kb())
    except Exception:
        await callback.message.answer(report, reply_markup=members_menu_kb())


# ─────────────────────────────────────────────────────────────────────────────
# Детальный отчёт по игровым никам
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == MemberBtn.NICK_REPORT)
async def cb_mem_nick_report(
    callback: CallbackQuery,
    user_service: UserService,
    audit_service: AuditService,
) -> None:
    """Показывает детальный отчёт: кто имеет ник, а кто нет."""
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()

    all_users = await user_service.get_all_users()
    total = len(all_users)
    with_nick    = [u for u in all_users if u.game_nick]
    without_nick = [u for u in all_users if not u.game_nick]

    lines = [
        "📋 <b>Детальный отчёт по игровым никам</b>",
        "",
        f"👥 Всего участников: <b>{total}</b>",
        f"✅ Есть игровой ник: <b>{len(with_nick)}</b>",
        f"❌ Нет игрового ника: <b>{len(without_nick)}</b>",
    ]

    if with_nick:
        lines += ["", "✅ <b>Есть игровой ник:</b>"]
        for u in _sort_users(with_nick):
            icon = _ICONS.get(u.role, "◇")
            lines.append(f"  {icon} {u.game_nick}  <code>{u.telegram_id}</code>")

    if without_nick:
        lines += ["", "❌ <b>Нет игрового ника:</b>"]
        for u in _sort_users(without_nick):
            icon = _ICONS.get(u.role, "◇")
            if u.username:
                label = f"@{u.username}"
            else:
                label = u.first_name
            lines.append(f"  {icon} {label}  <code>{u.telegram_id}</code>")

    report = "\n".join(lines)
    if len(report) > 4000:
        report = report[:4000] + "\n…\n<i>(отчёт обрезан)</i>"

    # Журнал
    actor_id = callback.from_user.id
    actor_nick = await user_service.get_game_nick(actor_id) or str(actor_id)
    actor_role = await user_service.get_role(actor_id)
    await audit_service.log(
        user_id=actor_id,
        game_nick=actor_nick,
        role=actor_role,
        action_type=AuditAction.NICK_REPORT,
        description=(
            f"{role_label(actor_role)} {actor_nick} просмотрел отчёт по никам: "
            f"всего {total}, с ником {len(with_nick)}, без ника {len(without_nick)}"
        ),
    )

    try:
        await callback.message.edit_text(report, reply_markup=nick_report_kb())
    except Exception:
        await callback.message.answer(report, reply_markup=nick_report_kb())


# ─────────────────────────────────────────────────────────────────────────────
# Напомнить без ника — отправка в тему «📢 Объявления»
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == MemberBtn.NICK_REMIND)
async def cb_mem_nick_remind(
    callback: CallbackQuery,
    user_service: UserService,
    audit_service: AuditService,
    topic_service: TopicService,
    bot: Bot,
) -> None:
    """Публикует в тему «Объявления» напоминание для участников без игрового ника."""
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()

    all_users = await user_service.get_all_users()
    without_nick = [u for u in all_users if not u.game_nick]

    if not without_nick:
        try:
            await callback.message.edit_text(
                "✅ Все участники имеют игровой ник!\n\nНапоминание не требуется.",
                reply_markup=nick_report_kb(),
            )
        except Exception:
            await callback.message.answer(
                "✅ Все участники имеют игровой ник!",
                reply_markup=nick_report_kb(),
            )
        return

    # Разделяем: кому можно @упомянуть, у кого нет username
    can_mention: list[str] = []
    no_username:  list[str] = []

    for u in without_nick:
        if u.username:
            can_mention.append(f"@{u.username}")
        else:
            label = u.first_name
            no_username.append(f"{label} (ID: {u.telegram_id})")

    # Формируем текст публикации
    mention_block = "\n".join(can_mention) if can_mention else ""
    pub_text = (
        "⚠️ <b>Просьба заполнить игровой ник.</b>\n\n"
        f"{mention_block}\n\n"
        "Пожалуйста, откройте бота и заполните игровой ник."
    ).strip()

    published = await topic_service.publish(
        bot, "announcements", pub_text, parse_mode="HTML"
    )

    actor_id = callback.from_user.id
    actor_nick = await user_service.get_game_nick(actor_id) or str(actor_id)
    actor_role = await user_service.get_role(actor_id)

    await audit_service.log(
        user_id=actor_id,
        game_nick=actor_nick,
        role=actor_role,
        action_type=AuditAction.NICK_REMIND,
        description=(
            f"{role_label(actor_role)} {actor_nick} отправил напоминание о никах: "
            f"упомянуто {len(can_mention)}, без username {len(no_username)}, "
            f"публикация {'выполнена' if published else 'не удалась'}"
        ),
    )

    logger.info(
        "nick_remind: actor=%s mentioned=%d no_username=%d published=%s",
        actor_id, len(can_mention), len(no_username), published,
    )

    # ── Отчёт о результатах ─────────────────────────────────────────────
    lines = [
        "📢 <b>Напоминание отправлено</b>" if published else "❌ <b>Не удалось отправить напоминание</b>",
        "",
        f"✅ Упомянуто участников: <b>{len(can_mention)}</b>",
        f"⏭️ Без username (пропущены): <b>{len(no_username)}</b>",
    ]
    if no_username:
        lines += ["", "⚠️ <b>Не удалось отметить (нет username):</b>"]
        lines += [f"  • {n}" for n in no_username]

    result_text = "\n".join(lines)
    try:
        await callback.message.edit_text(result_text, reply_markup=nick_report_kb())
    except Exception:
        await callback.message.answer(result_text, reply_markup=nick_report_kb())


# ─────────────────────────────────────────────────────────────────────────────
# Предупреждения участника
# ─────────────────────────────────────────────────────────────────────────────

async def _show_warnings(
    callback: CallbackQuery,
    uid: int,
    db: Database,
    user_service: UserService,
) -> None:
    """Вспомогательная функция: показывает список предупреждений участника."""
    u = await _find_user(user_service, uid)
    name = _display_name(u) if u else str(uid)
    warn_list = await db.list_warnings(uid)
    count = len(warn_list)

    if count == 0:
        header = f"⚠️ <b>Предупреждения участника «{name}»</b>\n\nПредупреждений нет."
    else:
        header = (
            f"⚠️ <b>Предупреждения участника «{name}»</b>\n\n"
            f"Всего: <b>{count}</b>\n\n"
        )
        for w in warn_list:
            header += f"• <b>#{w['id']}</b> {w['reason']} <i>({w['created_at'][:10]})</i>\n"

    try:
        await callback.message.edit_text(header, reply_markup=warnings_kb(uid, warn_list))
    except Exception:
        await callback.message.answer(header, reply_markup=warnings_kb(uid, warn_list))


@router.callback_query(F.data.startswith("mem:warnings:"))
async def cb_mem_warnings(
    callback: CallbackQuery,
    user_service: UserService,
    db: Database,
) -> None:
    """Показывает список предупреждений участника."""
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()
    uid = int(callback.data.split(":")[2])
    await _show_warnings(callback, uid, db, user_service)


@router.callback_query(F.data.startswith("mem:warn_add:"))
async def cb_mem_warn_add_start(
    callback: CallbackQuery,
    user_service: UserService,
    state: FSMContext,
) -> None:
    """Начинает FSM выдачи предупреждения: запрашивает причину."""
    if not await _check_admin(callback, user_service):
        return
    uid = int(callback.data.split(":")[2])
    if uid == _SUPERUSER_ID:
        await callback.answer("🔒 Нельзя выдать предупреждение суперпользователю.", show_alert=True)
        return
    await callback.answer()
    await state.set_state(MemberWarnAdd.waiting_reason)
    await state.update_data(target_id=uid)
    u = await _find_user(user_service, uid)
    name = _display_name(u) if u else str(uid)
    try:
        await callback.message.edit_text(
            f"⚠️ <b>Выдача предупреждения</b>\n\n"
            f"Участник: <b>{name}</b>\n\n"
            f"Введите причину предупреждения:",
            reply_markup=CANCEL_KB,
        )
    except Exception:
        await callback.message.answer(
            f"⚠️ <b>Выдача предупреждения</b>\n\n"
            f"Участник: <b>{name}</b>\n\n"
            f"Введите причину предупреждения:",
            reply_markup=CANCEL_KB,
        )


@router.message(MemberWarnAdd.waiting_reason)
async def fsm_mem_warn_reason(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    audit_service: AuditService,
    db: Database,
) -> None:
    """Сохраняет предупреждение и показывает обновлённый список."""
    data = await state.get_data()
    target_id = data.get("target_id")

    actor_id = message.from_user.id
    actor_role = await user_service.get_role(actor_id)
    if actor_role not in UserRole.admin_roles():
        await state.clear()
        await message.answer("🔒 Недостаточно прав.", reply_markup=MAIN_KEYBOARD)
        return

    if not target_id:
        await state.clear()
        await message.answer("❌ Ошибка: участник не найден.")
        return

    reason = (message.text or "").strip()
    if not reason:
        await message.answer("❌ Причина не может быть пустой. Введите причину ещё раз:")
        return  # не очищаем state — пользователь может повторить ввод

    actor_nick = await user_service.get_game_nick(actor_id) or str(actor_id)

    u = await _find_user(user_service, target_id)
    target_name = _display_name(u) if u else str(target_id)

    await db.add_warning(user_id=target_id, issued_by=actor_id, reason=reason)

    await audit_service.log(
        user_id=actor_id,
        game_nick=actor_nick,
        role=actor_role,
        action_type=AuditAction.MEMBER_WARNING_ADD,
        description=(
            f"{role_label(actor_role)} {actor_nick} выдал предупреждение "
            f"участнику {target_name}: {reason}"
        ),
        target_id=target_id,
    )

    await state.clear()
    logger.info("warn_add: actor=%s target=%s reason=%r", actor_id, target_id, reason)

    warn_list = await db.list_warnings(target_id)
    count = len(warn_list)
    header = (
        f"✅ <b>Предупреждение выдано</b>\n\n"
        f"⚠️ <b>Предупреждения участника «{target_name}»</b>\n\n"
        f"Всего: <b>{count}</b>\n\n"
    )
    for w in warn_list:
        header += f"• <b>#{w['id']}</b> {w['reason']} <i>({w['created_at'][:10]})</i>\n"

    await message.answer(header, reply_markup=warnings_kb(target_id, warn_list))


@router.callback_query(F.data.startswith("mem:warn_del:"))
async def cb_mem_warn_del(
    callback: CallbackQuery,
    user_service: UserService,
    audit_service: AuditService,
    db: Database,
) -> None:
    """Снимает предупреждение и обновляет список."""
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()

    parts = callback.data.split(":")
    uid = int(parts[2])
    wid = int(parts[3])

    actor_id = callback.from_user.id
    actor_nick = await user_service.get_game_nick(actor_id) or str(actor_id)
    actor_role = await user_service.get_role(actor_id)

    u = await _find_user(user_service, uid)
    target_name = _display_name(u) if u else str(uid)

    w = await db.get_warning(wid)
    reason = w["reason"] if w else "?"

    await db.remove_warning(wid)

    await audit_service.log(
        user_id=actor_id,
        game_nick=actor_nick,
        role=actor_role,
        action_type=AuditAction.MEMBER_WARNING_REMOVE,
        description=(
            f"{role_label(actor_role)} {actor_nick} снял предупреждение #{wid} "
            f"у участника {target_name}: {reason}"
        ),
        target_id=uid,
    )

    logger.info("warn_del: actor=%s target=%s wid=%s", actor_id, uid, wid)

    await _show_warnings(callback, uid, db, user_service)


# ─────────────────────────────────────────────────────────────────────────────
# Заметки администрации об участнике
# ─────────────────────────────────────────────────────────────────────────────

async def _show_notes(
    callback: CallbackQuery,
    uid: int,
    db: Database,
    user_service: UserService,
) -> None:
    """Вспомогательная функция: показывает заметки администрации об участнике."""
    u = await _find_user(user_service, uid)
    name = _display_name(u) if u else str(uid)
    note_list = await db.list_notes(uid)
    count = len(note_list)

    if count == 0:
        header = f"📝 <b>Заметки об участнике «{name}»</b>\n\nЗаметок нет."
    else:
        header = (
            f"📝 <b>Заметки об участнике «{name}»</b>\n\n"
            f"Всего: <b>{count}</b>\n\n"
        )
        for n in note_list:
            header += f"• <b>#{n['id']}</b> {n['text']} <i>({n['created_at'][:10]})</i>\n"

    try:
        await callback.message.edit_text(header, reply_markup=notes_kb(uid, note_list))
    except Exception:
        await callback.message.answer(header, reply_markup=notes_kb(uid, note_list))


@router.callback_query(F.data.startswith("mem:notes:"))
async def cb_mem_notes(
    callback: CallbackQuery,
    user_service: UserService,
    db: Database,
) -> None:
    """Показывает заметки администрации об участнике."""
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()
    uid = int(callback.data.split(":")[2])
    await _show_notes(callback, uid, db, user_service)


@router.callback_query(F.data.startswith("mem:note_add:"))
async def cb_mem_note_add_start(
    callback: CallbackQuery,
    user_service: UserService,
    state: FSMContext,
) -> None:
    """Начинает FSM добавления заметки: запрашивает текст."""
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()
    uid = int(callback.data.split(":")[2])
    await state.set_state(MemberNoteAdd.waiting_text)
    await state.update_data(target_id=uid)
    u = await _find_user(user_service, uid)
    name = _display_name(u) if u else str(uid)
    try:
        await callback.message.edit_text(
            f"📝 <b>Добавление заметки</b>\n\n"
            f"Участник: <b>{name}</b>\n\n"
            f"Введите текст заметки:",
            reply_markup=CANCEL_KB,
        )
    except Exception:
        await callback.message.answer(
            f"📝 <b>Добавление заметки</b>\n\n"
            f"Участник: <b>{name}</b>\n\n"
            f"Введите текст заметки:",
            reply_markup=CANCEL_KB,
        )


@router.message(MemberNoteAdd.waiting_text)
async def fsm_mem_note_text(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    audit_service: AuditService,
    db: Database,
) -> None:
    """Сохраняет заметку и показывает обновлённый список."""
    data = await state.get_data()
    target_id = data.get("target_id")

    actor_id = message.from_user.id
    actor_role = await user_service.get_role(actor_id)
    if actor_role not in UserRole.admin_roles():
        await state.clear()
        await message.answer("🔒 Недостаточно прав.", reply_markup=MAIN_KEYBOARD)
        return

    if not target_id:
        await state.clear()
        await message.answer("❌ Ошибка: участник не найден.")
        return

    text = (message.text or "").strip()
    if not text:
        await message.answer("❌ Текст заметки не может быть пустым. Введите текст ещё раз:")
        return  # не очищаем state — пользователь может повторить ввод

    actor_nick = await user_service.get_game_nick(actor_id) or str(actor_id)

    u = await _find_user(user_service, target_id)
    target_name = _display_name(u) if u else str(target_id)

    await db.add_note(user_id=target_id, author_id=actor_id, text=text)

    await audit_service.log(
        user_id=actor_id,
        game_nick=actor_nick,
        role=actor_role,
        action_type=AuditAction.MEMBER_NOTE_ADD,
        description=(
            f"{role_label(actor_role)} {actor_nick} добавил заметку "
            f"об участнике {target_name}: {text[:80]}"
        ),
        target_id=target_id,
    )

    await state.clear()
    logger.info("note_add: actor=%s target=%s", actor_id, target_id)

    note_list = await db.list_notes(target_id)
    count = len(note_list)
    header = (
        f"✅ <b>Заметка добавлена</b>\n\n"
        f"📝 <b>Заметки об участнике «{target_name}»</b>\n\n"
        f"Всего: <b>{count}</b>\n\n"
    )
    for n in note_list:
        header += f"• <b>#{n['id']}</b> {n['text']} <i>({n['created_at'][:10]})</i>\n"

    await message.answer(header, reply_markup=notes_kb(target_id, note_list))


@router.callback_query(F.data.startswith("mem:note_del:"))
async def cb_mem_note_del(
    callback: CallbackQuery,
    user_service: UserService,
    audit_service: AuditService,
    db: Database,
) -> None:
    """Удаляет заметку и обновляет список."""
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()

    parts = callback.data.split(":")
    uid = int(parts[2])
    nid = int(parts[3])

    actor_id = callback.from_user.id
    actor_nick = await user_service.get_game_nick(actor_id) or str(actor_id)
    actor_role = await user_service.get_role(actor_id)

    u = await _find_user(user_service, uid)
    target_name = _display_name(u) if u else str(uid)

    n = await db.get_note(nid)
    note_text = n["text"] if n else "?"

    await db.remove_note(nid)

    await audit_service.log(
        user_id=actor_id,
        game_nick=actor_nick,
        role=actor_role,
        action_type=AuditAction.MEMBER_NOTE_REMOVE,
        description=(
            f"{role_label(actor_role)} {actor_nick} удалил заметку #{nid} "
            f"об участнике {target_name}: {note_text[:80]}"
        ),
        target_id=uid,
    )

    logger.info("note_del: actor=%s target=%s nid=%s", actor_id, uid, nid)

    await _show_notes(callback, uid, db, user_service)


# ─────────────────────────────────────────────────────────────────────────────
# История участника (audit_log)
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("mem:history:"))
async def cb_mem_history(
    callback: CallbackQuery,
    user_service: UserService,
    db: Database,
) -> None:
    """Показывает историю действий участника из audit_log."""
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()

    uid = int(callback.data.split(":")[2])
    u = await _find_user(user_service, uid)
    name = _display_name(u) if u else str(uid)

    records = await db.get_user_history(uid, limit=20)

    if not records:
        text = f"📋 <b>История участника «{name}»</b>\n\nЗаписей нет."
    else:
        lines = [f"📋 <b>История участника «{name}»</b>\n<i>(последние {len(records)} записей)</i>\n"]
        for r in records:
            date = r["created_at"][:10]
            lines.append(f"• <b>{date}</b> {r['description']}")
        text = "\n".join(lines)
        if len(text) > 4000:
            text = text[:4000] + "\n…\n<i>(история обрезана)</i>"

    try:
        await callback.message.edit_text(text, reply_markup=history_kb(uid))
    except Exception:
        await callback.message.answer(text, reply_markup=history_kb(uid))
