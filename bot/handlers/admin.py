# -*- coding: utf-8 -*-
"""
Обработчик раздела «🛡️ Администрация».

Доступ:
  Лидер     → красивая панель управления с инлайн-кнопками
  Старейшина → статистика клана (только просмотр)
  Остальные  → сообщение об отказе
"""
import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.keyboards.admin_panel import ADMIN_PANEL_KB, AdminBtn
from bot.keyboards.main_menu import BTN
from bot.models.user import UserRole
from bot.services.user_service import UserService
from bot.utils.roles import role_label

router = Router()
logger = logging.getLogger(__name__)

_WIP = "🚧 Раздел находится в разработке."

# ───────────────────────────────────────────────────────────────────────────
# Вспомогательные функции
# ───────────────────────────────────────────────────────────────────────────

def _role_stats(users: list) -> str:
    """Формирует строку статистики по ролям в порядке иерархии."""
    from bot.utils.roles import ROLE_ORDER
    by_role: dict[UserRole, int] = {}
    for u in users:
        by_role[u.role] = by_role.get(u.role, 0) + 1

    lines = []
    for role in ROLE_ORDER:          # 👑 Лидер → 🌟 Дитя клана → 🛡️ Старейшина → 👤 Участник
        count = by_role.get(role, 0)
        if count:
            lines.append(f"  {role_label(role)}: {count}")
    return "\n".join(lines)


# ───────────────────────────────────────────────────────────────────────────
# Главный обработчик кнопки «🛡️ Администрация»
# ───────────────────────────────────────────────────────────────────────────

@router.message(F.text == BTN.ADMIN)
async def handle_admin(message: Message, user_service: UserService) -> None:
    """Открывает панель в зависимости от роли пользователя."""
    if not message.from_user:
        return

    role = await user_service.get_role(message.from_user.id)

    # ── Доступ запрещён ──────────────────────────────────────────────────
    if role not in UserRole.admin_roles():
        logger.info(
            "Пользователь %s (роль: %s) попытался войти в раздел администрации",
            message.from_user.id, role.value,
        )
        await message.answer(
            "🔒 <b>Доступ запрещён</b>\n\n"
            "Раздел «Администрация» доступен только Лидерам и Старейшинам.\n"
            f"Ваша роль: {role_label(role)}"
        )
        return

    users = await user_service.get_all_users()
    total = len(users)
    stats = _role_stats(users)

    # ── Панель Лидера (полный доступ + инлайн-кнопки) ───────────────────
    if role == UserRole.LEADER:
        logger.info("Лидер %s открыл панель управления", message.from_user.id)
        await message.answer(
            "👑 <b>Панель управления Astrum</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🌌 Добро пожаловать, Лидер!\n\n"
            f"<b>📊 Состав клана:</b>\n"
            f"{stats}\n"
            f"  <b>Итого:</b> {total}\n\n"
            "Выберите раздел для управления:",
            reply_markup=ADMIN_PANEL_KB,
        )
        return

    # ── Панель Старейшины (статистика, без кнопок управления) ───────────
    logger.info("Старейшина %s открыл панель администрации", message.from_user.id)
    await message.answer(
        "🌟 <b>Панель администрации Astrum</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Ваш уровень доступа: {role_label(role)}\n\n"
        f"<b>📊 Состав клана:</b>\n"
        f"{stats}\n"
        f"  <b>Итого:</b> {total}\n\n"
        "🚧 Инструменты управления доступны только Лидеру."
    )


# ───────────────────────────────────────────────────────────────────────────
# Обработчики инлайн-кнопок панели Лидера
# ───────────────────────────────────────────────────────────────────────────

async def _admin_callback(
    callback: CallbackQuery,
    user_service: UserService,
    section_name: str,
) -> None:
    """Общий обработчик: проверяет права и отвечает на нажатие кнопки."""
    if not callback.from_user:
        await callback.answer()
        return

    role = await user_service.get_role(callback.from_user.id)
    if role != UserRole.LEADER:
        await callback.answer("🔒 Только для Лидера.", show_alert=True)
        return

    await callback.answer()
    await callback.message.answer(
        f"<b>{section_name}</b>\n\n{_WIP}"
    )


@router.callback_query(F.data == AdminBtn.MEMBERS)
async def cb_members(callback: CallbackQuery, user_service: UserService) -> None:
    """Управление участниками."""
    await _admin_callback(callback, user_service, "👥 Управление участниками")


@router.callback_query(F.data == AdminBtn.NEWS)
async def cb_news(callback: CallbackQuery, user_service: UserService) -> None:
    """Управление новостями."""
    await _admin_callback(callback, user_service, "📢 Управление новостями")


@router.callback_query(F.data == AdminBtn.EVENTS)
async def cb_events(callback: CallbackQuery, user_service: UserService) -> None:
    """Управление событиями."""
    await _admin_callback(callback, user_service, "📅 Управление событиями")


@router.callback_query(F.data == AdminBtn.GUIDES)
async def cb_guides(callback: CallbackQuery, user_service: UserService) -> None:
    """Управление гайдами."""
    await _admin_callback(callback, user_service, "📚 Управление гайдами")


@router.callback_query(F.data == AdminBtn.SCREENSHOTS)
async def cb_screenshots(callback: CallbackQuery, user_service: UserService) -> None:
    """Управление скриншотами."""
    await _admin_callback(callback, user_service, "📸 Управление скриншотами")


@router.callback_query(F.data == AdminBtn.COMMUNITY)
async def cb_community(callback: CallbackQuery, user_service: UserService) -> None:
    """Настройки сообщества."""
    await _admin_callback(callback, user_service, "⚙️ Настройки сообщества")
