# -*- coding: utf-8 -*-
"""
Мастер создания и отправки рассылок администрации.

Сценарий:
  1. Админ нажимает «📣 Рассылки» в панели администрации.
  2. Вводит текст рассылки.
  3. Предпросмотр: отправить всем участникам / отправить себе (тест) /
     изменить текст / закрыть.
"""
import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.admin_panel import AdminBtn
from bot.keyboards.broadcast import PREVIEW_KB, BroadcastBtn
from bot.keyboards.main_menu import MAIN_KEYBOARD
from bot.keyboards.nav import CANCEL_KB
from bot.models.audit import AuditAction
from bot.models.user import UserRole
from bot.services.audit_service import AuditService
from bot.services.broadcast_service import BroadcastService
from bot.services.user_service import UserService
from bot.states.broadcast import BroadcastWizard
from bot.utils.roles import role_label

router = Router()
logger = logging.getLogger(__name__)

_MAX_TEXT = 4000


def _author_name(user) -> str:
    if user.username:
        return f"@{user.username}"
    return user.first_name or "Автор"


def _build_preview(text: str) -> str:
    return (
        "📣 <b>Предпросмотр рассылки</b>\n\n"
        f"{text}\n\n"
        "Проверьте текст перед отправкой."
    )


async def _check_admin(callback: CallbackQuery, user_service: UserService) -> UserRole | None:
    if not callback.from_user:
        await callback.answer()
        return None
    role = await user_service.get_role(callback.from_user.id)
    if role not in UserRole.admin_roles():
        await callback.answer("🔒 Недостаточно прав.", show_alert=True)
        return None
    return role


# ── Вход: кнопка «📣 Рассылки» в панели администрации ─────────────────────────

@router.callback_query(F.data == AdminBtn.BROADCASTS)
async def cb_broadcasts(
    callback: CallbackQuery, user_service: UserService, state: FSMContext
) -> None:
    role = await _check_admin(callback, user_service)
    if role is None:
        return
    await state.set_state(BroadcastWizard.waiting_text)
    await callback.answer()
    await callback.message.answer(
        "📣 <b>Создание рассылки</b>\n\n"
        f"Введите текст сообщения (до {_MAX_TEXT} символов):",
        reply_markup=CANCEL_KB,
    )


# ── Шаг 1: текст рассылки ─────────────────────────────────────────────────────

@router.message(BroadcastWizard.waiting_text)
async def handle_waiting_text(message: Message, state: FSMContext) -> None:
    if not message.text or message.text.startswith("/"):
        await message.answer("⚠️ Пожалуйста, введите текст рассылки сообщением.")
        return
    text = message.text.strip()
    if len(text) > _MAX_TEXT:
        await message.answer(
            f"⚠️ Текст слишком длинный (максимум {_MAX_TEXT} символов). Попробуйте ещё раз."
        )
        return

    await state.update_data(text=text)
    await state.set_state(BroadcastWizard.preview)
    await message.answer(_build_preview(text), reply_markup=PREVIEW_KB)


# ── Callback: ✏️ Изменить текст ───────────────────────────────────────────────

@router.callback_query(F.data == BroadcastBtn.EDIT_TEXT, BroadcastWizard.preview)
async def cb_edit_text(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BroadcastWizard.waiting_text)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"✏️ Введите новый текст рассылки (до {_MAX_TEXT} символов):",
        reply_markup=CANCEL_KB,
    )
    await callback.answer()


# ── Callback: ❌ Закрыть ──────────────────────────────────────────────────────

@router.callback_query(F.data == BroadcastBtn.CANCEL, BroadcastWizard.preview)
async def cb_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "❌ Рассылка отменена.\n\nВыберите раздел в главном меню.",
        reply_markup=MAIN_KEYBOARD,
    )
    await callback.answer()


# ── Callback: 🧪 Отправить себе (тест) ────────────────────────────────────────

@router.callback_query(F.data == BroadcastBtn.SEND_SELF, BroadcastWizard.preview)
async def cb_send_self(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    broadcast_service: BroadcastService,
    user_service: UserService,
    audit_service: AuditService,
) -> None:
    data = await state.get_data()
    text = data.get("text", "")
    user = callback.from_user
    author_name = _author_name(user)

    broadcast_id = await broadcast_service.create(user.id, author_name, text, audience="self")
    await broadcast_service.send(bot, broadcast_id, text, [user.id])

    actor_nick = await user_service.get_game_nick(user.id) or author_name
    actor_role = await user_service.get_role(user.id)
    await audit_service.log(
        user_id=user.id,
        game_nick=actor_nick,
        role=actor_role,
        action_type=AuditAction.BROADCAST_SEND,
        description=f"{role_label(actor_role)} {actor_nick} отправил тестовую рассылку самому себе",
    )

    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"✅ Тестовая рассылка отправлена вам (#{broadcast_id}).",
        reply_markup=MAIN_KEYBOARD,
    )
    await callback.answer()


# ── Callback: 📤 Отправить всем участникам ────────────────────────────────────

@router.callback_query(F.data == BroadcastBtn.SEND_ALL, BroadcastWizard.preview)
async def cb_send_all(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    broadcast_service: BroadcastService,
    user_service: UserService,
    audit_service: AuditService,
) -> None:
    data = await state.get_data()
    text = data.get("text", "")
    user = callback.from_user
    author_name = _author_name(user)

    users = await user_service.get_all_users()
    chat_ids = [u.telegram_id for u in users]

    broadcast_id = await broadcast_service.create(user.id, author_name, text, audience="all")

    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"⏳ Рассылка запущена ({len(chat_ids)} получателей)…",
        reply_markup=MAIN_KEYBOARD,
    )
    await callback.answer()

    result = await broadcast_service.send(bot, broadcast_id, text, chat_ids)

    actor_nick = await user_service.get_game_nick(user.id) or author_name
    actor_role = await user_service.get_role(user.id)
    await audit_service.log(
        user_id=user.id,
        game_nick=actor_nick,
        role=actor_role,
        action_type=AuditAction.BROADCAST_SEND,
        description=(
            f"{role_label(actor_role)} {actor_nick} разослал сообщение всем участникам "
            f"(доставлено {result['sent']} из {result['total']})"
        ),
    )

    await callback.message.answer(
        f"✅ <b>Рассылка #{broadcast_id} завершена</b>\n\n"
        f"📤 Доставлено: {result['sent']}\n"
        f"⚠️ Не доставлено: {result['failed']}\n"
        f"👥 Всего получателей: {result['total']}",
    )
