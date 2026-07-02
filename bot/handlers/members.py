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
"""
import datetime
import logging

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.admin_panel import AdminBtn
from bot.keyboards.members import (
    PAGE_SIZE,
    MemberBtn,
    delete_card_kb,
    delete_list_kb,
    delete_search_result_kb,
    member_card_kb,
    members_list_kb,
    members_menu_kb,
    role_select_kb,
    season_confirm_kb,
)
from bot.keyboards.nav import CANCEL_KB
from bot.models.audit import AuditAction
from bot.models.user import User, UserRole
from bot.services.audit_service import AuditService
from bot.services.stats_service import StatsService
from bot.services.user_service import UserService
from bot.states.members import MemberDelete
from bot.utils.roles import ROLE_ORDER, assignable_roles, can_assign, role_label
from bot.utils.sync_title import ADMIN_TITLES, build_admin_title, sync_admin_title

router = Router()
logger = logging.getLogger(__name__)

_ICONS: dict[UserRole, str] = {
    UserRole.LEADER:     "👑",
    UserRole.ELDER:      "🛡",
    UserRole.CLAN_CHILD: "⭐",
    UserRole.MEMBER:     "👤",
}

_SUPERUSER_ID = 8490615925

_MENU_TEXT = (
    "👥 <b>Управление участниками</b>\n\n"
    "Выберите действие:"
)


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────────────────────────────────────

def _sort_users(users: list[User]) -> list[User]:
    order = {r: i for i, r in enumerate(ROLE_ORDER)}
    return sorted(
        users,
        key=lambda u: (order.get(u.role, 99), (u.game_nick or u.first_name).lower()),
    )


def _display_name(u: User) -> str:
    return u.game_nick or u.first_name


def _effective_role(actor_id: int, actor_role: UserRole) -> UserRole:
    return UserRole.LEADER if actor_id == _SUPERUSER_ID else actor_role


def _card_text(u: User) -> str:
    icon = _ICONS.get(u.role, "◇")
    username_line = f"@{u.username}" if u.username else "(без юзернейма)"
    return (
        f"👤 <b>{_display_name(u)}</b>\n\n"
        f"Текущая роль:\n{icon} {u.role.value}\n\n"
        f"Telegram:\n{username_line}\n\n"
        f"ID:\n<code>{u.telegram_id}</code>"
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


async def _show_list(cb: CallbackQuery, user_service: UserService, page: int) -> None:
    # Показываем только участников с установленным игровым ником
    all_users = _sort_users([u for u in await user_service.get_all_users() if u.game_nick])
    total = len(all_users)
    page_users = all_users[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    text = f"👥 <b>Участники клана</b>\n\nВсего: {total}\n\nВыберите участника:"
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
        f"Всего: {total}\n\n"
        "Выберите участника для удаления:"
    )
    kb = delete_list_kb(page_users, page, total)
    try:
        await cb.message.edit_text(text, reply_markup=kb)
    except Exception:
        await cb.message.answer(text, reply_markup=kb)


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
async def cb_mem_list(callback: CallbackQuery, user_service: UserService) -> None:
    if not await _check_admin(callback, user_service):
        return
    page = int(callback.data.split(":")[2])
    await callback.answer()
    await _show_list(callback, user_service, page)


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
async def cb_mem_card(callback: CallbackQuery, user_service: UserService) -> None:
    if not await _check_admin(callback, user_service):
        return
    user_id = int(callback.data.split(":")[2])
    u = await _find_user(user_service, user_id)
    if not u:
        await callback.answer("Участник не найден.", show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(_card_text(u), reply_markup=member_card_kb(user_id))


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
    elif confirmed in ADMIN_TITLES:
        actual_title = build_admin_title(confirmed, target_nick)
        tg_note = f"\n\n✅ Telegram-титул установлен: «{actual_title}»"
    else:
        tg_note = "\n\n✅ Telegram-титул снят."

    u = await _find_user(user_service, target_id)
    card = f"\n\n{_card_text(u)}" if u else ""

    await callback.answer(f"✅ {icon} {confirmed.value}", show_alert=False)
    await callback.message.edit_text(
        f"✅ <b>Роль успешно изменена.</b>\n\n"
        f"Новый тег:\n{icon} {confirmed.value}"
        f"{tg_note}"
        f"{card}",
        reply_markup=member_card_kb(target_id),
    )


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
    n_guide = stats["guides"]
    n_shot  = stats["screenshots"]
    n_event = stats["events"]

    lines = [
        f"📊 <b>Статистика — {nick}</b>",
        "",
        f"🏠 Дней в клане: <b>{days}</b>",
        f"⚡️ Очки активности: <b>{score}</b>",
        "",
        "Публикации:",
        f"  📰 Новостей: <b>{n_news}</b>",
        f"  📚 Гайдов: <b>{n_guide}</b>",
        f"  📅 Событий: <b>{n_event}</b>",
        f"  📸 Скриншотов: <b>{n_shot}</b>",
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
    icon = _ICONS.get(u.role, "◇")
    username_line = f"@{u.username}" if u.username else "(без юзернейма)"

    text = (
        f"🗑️ <b>Удалить участника?</b>\n\n"
        f"👤 <b>{name}</b>\n"
        f"{icon} {u.role.value}\n"
        f"{username_line}\n"
        f"ID: <code>{u.telegram_id}</code>\n\n"
        "После удаления будут стёрты:\n"
        "• запись участника\n"
        "• вся история активности\n"
        "• обращения в поддержку\n\n"
        "<b>Это действие необратимо.</b>"
    )

    # Проверяем ограничения заранее, чтобы сразу показать причину
    _SUPERUSER = 8490615925
    if target_id == _SUPERUSER:
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
