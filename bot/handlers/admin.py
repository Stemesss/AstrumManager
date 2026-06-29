# -*- coding: utf-8 -*-
"""
Обработчик раздела «🛡️ Администрация».

Доступ:
  👑 Лидер, ⭐ Дитя клана, 🛡️ Старейшина → полная панель управления
  👤 Участник → отказ
"""
import datetime
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.admin_panel import ADMIN_PANEL_KB, AdminBtn
from bot.keyboards.audit import audit_menu_kb
from bot.keyboards.main_menu import BTN, MAIN_KEYBOARD
from bot.models.user import UserRole
from bot.services.news_service import NewsService
from bot.services.user_service import UserService
from bot.states.publish import PublishWizard
from bot.utils.roles import ROLE_ORDER, role_label

router = Router()
logger = logging.getLogger(__name__)

_WIP     = "🚧 Раздел находится в разработке."
_VERSION = "v1.0.0"

_ROLE_ICONS = {
    UserRole.LEADER:     "👑",
    UserRole.CLAN_CHILD: "⭐",
    UserRole.ELDER:      "🛡️",
    UserRole.MEMBER:     "👤",
}


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────────────────────────────────────

def _format_uptime(start: datetime.datetime) -> str:
    now   = datetime.datetime.now(datetime.timezone.utc)
    delta = now - start
    total = int(delta.total_seconds())
    days  = total // 86400
    hours = (total % 86400) // 3600
    mins  = (total % 3600) // 60
    if days:
        return f"{days} д. {hours} ч."
    if hours:
        return f"{hours} ч. {mins} мин."
    return f"{mins} мин."


def _role_stats(users: list) -> dict[UserRole, int]:
    counts: dict[UserRole, int] = {r: 0 for r in UserRole}
    for u in users:
        counts[u.role] = counts.get(u.role, 0) + 1
    return counts


async def _build_panel(
    users: list,
    news_count: int,
    start_time: datetime.datetime | None,
    role: UserRole,
) -> str:
    counts = _role_stats(users)
    total  = len(users)
    uptime = _format_uptime(start_time) if start_time else "—"

    members_block = ""
    for r in ROLE_ORDER:
        icon  = _ROLE_ICONS[r]
        label = role_label(r)
        cnt   = counts.get(r, 0)
        members_block += f"{icon} {label}: {cnt}\n"

    return (
        "🛡️ <b>Панель управления</b>\n\n"
        f"🟢 Онлайн  •  ⏳ {uptime}  •  🤖 {_VERSION}\n\n"
        f"👥 Всего участников: {total}\n"
        f"{members_block}\n"
        f"📰 Новостей: {news_count}\n"
        f"📅 Событий: 0\n"
        f"📚 Гайдов: 0\n"
        f"📸 Скриншотов: 0\n\n"
        "Выберите раздел:"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Главный обработчик кнопки «🛡️ Администрация»
# ─────────────────────────────────────────────────────────────────────────────

@router.message(F.text == BTN.ADMIN)
async def handle_admin(
    message: Message,
    user_service: UserService,
    news_service: NewsService,
    bot_start_time: datetime.datetime | None = None,
) -> None:
    if not message.from_user:
        return

    role = await user_service.get_role(message.from_user.id)

    if role not in UserRole.admin_roles():
        logger.info(
            "Пользователь %s (роль: %s) попытался войти в раздел администрации",
            message.from_user.id, role.value,
        )
        await message.answer(
            "🔒 <b>Доступ запрещён</b>\n\n"
            "Раздел «Администрация» доступен только администраторам клана.\n"
            f"Ваша роль: {role_label(role)}"
        )
        return

    users, news_list = (
        await user_service.get_all_users(),
        await news_service.get_list(),
    )

    logger.info(
        "Администратор %s (роль: %s) открыл панель управления",
        message.from_user.id, role.value,
    )
    text = await _build_panel(users, len(news_list), bot_start_time, role)
    await message.answer(text, reply_markup=ADMIN_PANEL_KB)


# ─────────────────────────────────────────────────────────────────────────────
# Обработчики инлайн-кнопок панели администрации
# ─────────────────────────────────────────────────────────────────────────────

async def _check_admin(callback: CallbackQuery, user_service: UserService) -> UserRole | None:
    if not callback.from_user:
        await callback.answer()
        return None
    role = await user_service.get_role(callback.from_user.id)
    if role not in UserRole.admin_roles():
        await callback.answer("🔒 Недостаточно прав.", show_alert=True)
        return None
    return role


async def _wip_callback(
    callback: CallbackQuery,
    user_service: UserService,
    section_name: str,
) -> None:
    role = await _check_admin(callback, user_service)
    if role is None:
        return
    await callback.answer()
    await callback.message.answer(f"<b>{section_name}</b>\n\n{_WIP}")


@router.callback_query(F.data == AdminBtn.NEWS)
async def cb_news(
    callback: CallbackQuery, user_service: UserService, state: FSMContext
) -> None:
    role = await _check_admin(callback, user_service)
    if role is None:
        return
    await state.set_state(PublishWizard.waiting_title)
    await state.update_data(content_type="news")
    await callback.answer()
    await callback.message.answer(
        "📰 <b>Создание новости</b>\n\n"
        "Введите <b>заголовок</b> новости (до 100 символов):\n\n"
        "<i>Отправьте /cancel для отмены</i>",
        reply_markup=MAIN_KEYBOARD,
    )


@router.callback_query(F.data == AdminBtn.EVENTS)
async def cb_events(
    callback: CallbackQuery, user_service: UserService, state: FSMContext
) -> None:
    role = await _check_admin(callback, user_service)
    if role is None:
        return
    await state.set_state(PublishWizard.waiting_title)
    await state.update_data(content_type="events")
    await callback.answer()
    await callback.message.answer(
        "📅 <b>Создание события</b>\n\n"
        "Введите <b>заголовок</b> события (до 100 символов):\n\n"
        "<i>Отправьте /cancel для отмены</i>",
        reply_markup=MAIN_KEYBOARD,
    )


@router.callback_query(F.data == AdminBtn.GUIDES)
async def cb_guides(
    callback: CallbackQuery, user_service: UserService, state: FSMContext
) -> None:
    role = await _check_admin(callback, user_service)
    if role is None:
        return
    await state.set_state(PublishWizard.waiting_title)
    await state.update_data(content_type="guides")
    await callback.answer()
    await callback.message.answer(
        "📚 <b>Создание гайда</b>\n\n"
        "Введите <b>заголовок</b> гайда (до 100 символов):\n\n"
        "<i>Отправьте /cancel для отмены</i>",
        reply_markup=MAIN_KEYBOARD,
    )


@router.callback_query(F.data == AdminBtn.SCREENSHOTS)
async def cb_screenshots(
    callback: CallbackQuery, user_service: UserService, state: FSMContext
) -> None:
    role = await _check_admin(callback, user_service)
    if role is None:
        return
    await state.set_state(PublishWizard.waiting_title)
    await state.update_data(content_type="screenshots")
    await callback.answer()
    await callback.message.answer(
        "📸 <b>Создание скриншота</b>\n\n"
        "Введите <b>заголовок</b> скриншота (до 100 символов):\n\n"
        "<i>Отправьте /cancel для отмены</i>",
        reply_markup=MAIN_KEYBOARD,
    )



@router.callback_query(F.data == AdminBtn.AUDIT)
async def cb_audit(callback: CallbackQuery, user_service: UserService) -> None:
    role = await _check_admin(callback, user_service)
    if role is None:
        return
    await callback.answer()
    await callback.message.answer(
        "📋 <b>Журнал действий</b>\n\n"
        "Выберите категорию для просмотра:",
        reply_markup=audit_menu_kb(role),
    )


@router.callback_query(F.data == AdminBtn.SETTINGS)
async def cb_settings(callback: CallbackQuery, user_service: UserService) -> None:
    await _wip_callback(callback, user_service, "⚙️ Настройки")
