# -*- coding: utf-8 -*-
"""
Обработчик раздела «👥 Участники».

Доступ: Лидер, Дитя клана, Старейшина.

Маршруты callback_data:
  admin:members / admin:roles  → список с пагинацией
  mem:list:{page}              → навигация по списку
  mem:card:{uid}               → карточка участника
  mem:role:{uid}               → выбор новой роли
  mem:set:{uid}:{role_value}   → применить роль + sync title + журнал
  mem:stats:{uid}              → статистика (WIP)
  mem:noop                     → индикатор страницы (без действия)
  mem:close                    → удалить сообщение
"""
import logging

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery

from bot.keyboards.admin_panel import AdminBtn
from bot.keyboards.members import PAGE_SIZE, member_card_kb, members_list_kb, role_select_kb
from bot.models.audit import AuditAction
from bot.models.user import User, UserRole
from bot.services.audit_service import AuditService
from bot.services.user_service import UserService
from bot.utils.roles import ROLE_ORDER, assignable_roles, can_assign, role_label
from bot.utils.sync_title import ADMIN_TITLES, sync_admin_title

router = Router()
logger = logging.getLogger(__name__)

_ICONS: dict[UserRole, str] = {
    UserRole.LEADER:     "✪",
    UserRole.CLAN_CHILD: "✦",
    UserRole.ELDER:      "✧",
    UserRole.MEMBER:     "◇",
}

_SUPERUSER_ID = 8490615925


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────────────────────────────────────

def _sort_users(users: list[User]) -> list[User]:
    """Сортировка: по убыванию роли, затем по нику/имени."""
    order = {r: i for i, r in enumerate(ROLE_ORDER)}
    return sorted(
        users,
        key=lambda u: (order.get(u.role, 99), (u.game_nick or u.first_name).lower()),
    )


def _display_name(u: User) -> str:
    return u.game_nick or u.first_name


def _effective_role(actor_id: int, actor_role: UserRole) -> UserRole:
    """Суперпользователь всегда получает права Лидера."""
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
    """Возвращает True, если пользователь — администратор клана."""
    role = await user_service.get_role(cb.from_user.id)
    if role not in UserRole.admin_roles():
        await cb.answer("🔒 Недостаточно прав.", show_alert=True)
        return False
    return True


async def _find_user(user_service: UserService, user_id: int) -> User | None:
    """Ищет участника среди всех зарегистрированных пользователей."""
    for u in await user_service.get_all_users():
        if u.telegram_id == user_id:
            return u
    return None


async def _show_list(cb: CallbackQuery, user_service: UserService, page: int) -> None:
    """Показывает страницу списка участников."""
    all_users = _sort_users(await user_service.get_all_users())
    total = len(all_users)
    page_users = all_users[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]

    text = f"👥 <b>Участники клана</b>\n\nВсего: {total}\n\nВыберите участника:"
    kb = members_list_kb(page_users, page, total)
    try:
        await cb.message.edit_text(text, reply_markup=kb)
    except Exception:
        await cb.message.answer(text, reply_markup=kb)


# ─────────────────────────────────────────────────────────────────────────────
# Вход из панели администрации
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == AdminBtn.MEMBERS)
async def cb_admin_members(callback: CallbackQuery, user_service: UserService) -> None:
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()
    await _show_list(callback, user_service, 0)


@router.callback_query(F.data == AdminBtn.ROLES)
async def cb_admin_roles(callback: CallbackQuery, user_service: UserService) -> None:
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()
    await _show_list(callback, user_service, 0)


# ─────────────────────────────────────────────────────────────────────────────
# Навигация по списку
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("mem:list:"))
async def cb_mem_list(callback: CallbackQuery, user_service: UserService) -> None:
    if not await _check_admin(callback, user_service):
        return
    page = int(callback.data.split(":")[2])
    await callback.answer()
    await _show_list(callback, user_service, page)


@router.callback_query(F.data == "mem:noop")
async def cb_mem_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data == "mem:close")
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

    # mem:set:{uid}:{role_value}  (role_value может содержать пробел — split с maxsplit)
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

    # Сохраняем роль и сразу читаем обратно
    await user_service.set_role(target_id, new_role)
    confirmed = await user_service.get_role(target_id)

    # Журнал аудита
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

    # Синхронизация Telegram Admin Title
    tg_error = await sync_admin_title(bot, group_chat_id, target_id, confirmed)

    icon = _ICONS.get(confirmed, "◇")
    if tg_error:
        tg_note = f"\n\n{tg_error}"
    elif confirmed in ADMIN_TITLES:
        tg_note = f"\n\n✅ Telegram-титул установлен: «{ADMIN_TITLES[confirmed]}»"
    else:
        tg_note = "\n\n✅ Telegram-титул снят."

    # Показываем результат + обновлённую карточку
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
# Статистика участника (WIP)
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("mem:stats:"))
async def cb_mem_stats(callback: CallbackQuery, user_service: UserService) -> None:
    if not await _check_admin(callback, user_service):
        return
    target_id = int(callback.data.split(":")[2])
    u = await _find_user(user_service, target_id)
    nick = _display_name(u) if u else str(target_id)
    await callback.answer()
    await callback.message.edit_text(
        f"📊 <b>Статистика — {nick}</b>\n\n🚧 Раздел в разработке.",
        reply_markup=member_card_kb(target_id),
    )
