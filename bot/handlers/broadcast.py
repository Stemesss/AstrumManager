# -*- coding: utf-8 -*-
"""
Подсистема рассылок администрации.

Сценарий:
  1. Админ нажимает «📣 Рассылки» в панели администрации → открывается хаб.
  2. Хаб: ✏️ Новая рассылка / 🗂 Шаблоны / 📊 История / ⏰ Запланированные / ❌ Закрыть.
  3. Новая рассылка: ввод текста → предпросмотр → отправить всем / себе (тест) /
     запланировать / сохранить как шаблон / изменить текст / закрыть.
"""
import logging
from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.admin_panel import AdminBtn
from bot.keyboards.broadcast import (
    BACK_ONLY_KB,
    HUB_KB,
    PREVIEW_KB,
    BroadcastBtn,
    scheduled_kb,
    templates_kb,
)
from bot.keyboards.nav import CANCEL_KB, reset_to_main_menu
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
_MAX_TPL_NAME = 60

_STATUS_LABELS = {
    "draft": "📝 Черновик",
    "sent": "✅ Отправлена",
    "scheduled": "⏰ Запланирована",
    "cancelled": "❌ Отменена",
}
_AUDIENCE_LABELS = {"all": "👥 Все участники", "self": "🧪 Себе (тест)"}


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


def _short_text(text: str, limit: int = 60) -> str:
    text = text.replace("\n", " ").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


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
async def cb_broadcasts(callback: CallbackQuery, user_service: UserService, state: FSMContext) -> None:
    role = await _check_admin(callback, user_service)
    if role is None:
        return
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        "📣 <b>Рассылки</b>\n\nВыберите действие:",
        reply_markup=HUB_KB,
    )


@router.callback_query(F.data == BroadcastBtn.BACK)
async def cb_hub_back(callback: CallbackQuery, user_service: UserService, state: FSMContext) -> None:
    role = await _check_admin(callback, user_service)
    if role is None:
        return
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        "📣 <b>Рассылки</b>\n\nВыберите действие:",
        reply_markup=HUB_KB,
    )


@router.callback_query(F.data == BroadcastBtn.CLOSE)
async def cb_hub_close(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()
    await reset_to_main_menu(callback.message, "❌ Раздел «Рассылки» закрыт.")


# ── Новая рассылка: шаг 0 — старт мастера ─────────────────────────────────────

@router.callback_query(F.data == BroadcastBtn.NEW)
async def cb_new(callback: CallbackQuery, user_service: UserService, state: FSMContext) -> None:
    role = await _check_admin(callback, user_service)
    if role is None:
        return
    await state.set_state(BroadcastWizard.waiting_text)
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
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

    data = await state.get_data()
    await state.update_data(text=text)

    if data.get("_tpl_new_flow"):
        await state.set_state(BroadcastWizard.waiting_template_name)
        await message.answer(
            f"💾 Введите название шаблона (до {_MAX_TPL_NAME} символов):",
            reply_markup=CANCEL_KB,
        )
        return

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


# ── Callback: ❌ Закрыть (из предпросмотра) ───────────────────────────────────

@router.callback_query(F.data == BroadcastBtn.CANCEL, BroadcastWizard.preview)
async def cb_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()
    await reset_to_main_menu(callback.message, "❌ Рассылка отменена.")


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

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()

    try:
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
    except Exception:
        logger.exception("Ошибка отправки тестовой рассылки")
        await state.clear()
        await reset_to_main_menu(callback.message, "⚠️ Не удалось отправить тестовую рассылку. Попробуйте ещё раз.")
        return

    await state.clear()
    await reset_to_main_menu(callback.message, f"✅ Тестовая рассылка отправлена вам (#{broadcast_id}).")


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

    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()

    try:
        users = await user_service.get_all_users()
        chat_ids = [u.telegram_id for u in users]
        broadcast_id = await broadcast_service.create(user.id, author_name, text, audience="all")

        await callback.message.answer(f"⏳ Рассылка запущена ({len(chat_ids)} получателей)…")

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
    except Exception:
        logger.exception("Ошибка при рассылке всем участникам")
        await reset_to_main_menu(callback.message, "⚠️ Рассылка прервана из-за ошибки. Проверьте историю рассылок.")
        return

    await reset_to_main_menu(
        callback.message,
        f"✅ <b>Рассылка #{broadcast_id} завершена</b>\n\n"
        f"📤 Доставлено: {result['sent']}\n"
        f"⚠️ Не доставлено: {result['failed']}\n"
        f"👥 Всего получателей: {result['total']}",
    )


# ── История рассылок ──────────────────────────────────────────────────────────

@router.callback_query(F.data == BroadcastBtn.HISTORY)
async def cb_history(callback: CallbackQuery, user_service: UserService, broadcast_service: BroadcastService) -> None:
    role = await _check_admin(callback, user_service)
    if role is None:
        return
    await callback.answer()

    items = await broadcast_service.list_recent(limit=10)
    if not items:
        await callback.message.edit_text("📊 <b>История рассылок</b>\n\nПока пусто.", reply_markup=BACK_ONLY_KB)
        return

    lines = ["📊 <b>История рассылок</b> (последние 10)\n"]
    for row in items:
        status = _STATUS_LABELS.get(row["status"], row["status"])
        audience = _AUDIENCE_LABELS.get(row["audience"], row["audience"])
        lines.append(
            f"#{row['id']} · {row['created_at']}\n"
            f"👤 {row['author_name']} · {audience} · {status}\n"
            f"«{_short_text(row['text'])}»\n"
            f"📤 {row['sent_count'] or 0}  ⚠️ {row['failed_count'] or 0}\n"
        )
    await callback.message.edit_text("\n".join(lines), reply_markup=BACK_ONLY_KB)


# ── Шаблоны ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == BroadcastBtn.TEMPLATES)
async def cb_templates(callback: CallbackQuery, user_service: UserService, broadcast_service: BroadcastService) -> None:
    role = await _check_admin(callback, user_service)
    if role is None:
        return
    await callback.answer()
    templates = await broadcast_service.list_templates()
    text = "🗂 <b>Шаблоны рассылок</b>\n\n" + (
        "Список пуст. Добавьте шаблон из предпросмотра рассылки или кнопкой ниже."
        if not templates else "Выберите шаблон, чтобы использовать его, или удалите ненужный."
    )
    await callback.message.edit_text(text, reply_markup=templates_kb(templates))


@router.callback_query(F.data.startswith(BroadcastBtn.TPL_USE_PREFIX))
async def cb_template_use(
    callback: CallbackQuery, user_service: UserService, broadcast_service: BroadcastService, state: FSMContext
) -> None:
    role = await _check_admin(callback, user_service)
    if role is None:
        return
    template_id = int(callback.data.removeprefix(BroadcastBtn.TPL_USE_PREFIX))
    template = await broadcast_service.get_template(template_id)
    if template is None:
        await callback.answer("⚠️ Шаблон не найден.", show_alert=True)
        return

    await state.update_data(text=template["text"])
    await state.set_state(BroadcastWizard.preview)
    await callback.answer()
    await callback.message.edit_text(_build_preview(template["text"]), reply_markup=PREVIEW_KB)


@router.callback_query(F.data.startswith(BroadcastBtn.TPL_DEL_PREFIX))
async def cb_template_delete(
    callback: CallbackQuery, user_service: UserService, broadcast_service: BroadcastService, audit_service: AuditService
) -> None:
    role = await _check_admin(callback, user_service)
    if role is None:
        return
    template_id = int(callback.data.removeprefix(BroadcastBtn.TPL_DEL_PREFIX))
    template = await broadcast_service.get_template(template_id)
    await broadcast_service.delete_template(template_id)
    await callback.answer("🗑 Шаблон удалён.")

    if template is not None:
        actor_nick = await user_service.get_game_nick(callback.from_user.id) or _author_name(callback.from_user)
        await audit_service.log(
            user_id=callback.from_user.id,
            game_nick=actor_nick,
            role=role,
            action_type=AuditAction.BROADCAST_TEMPLATE_DELETE,
            description=f"{role_label(role)} {actor_nick} удалил шаблон рассылки «{template['name']}»",
        )

    templates = await broadcast_service.list_templates()
    text = "🗂 <b>Шаблоны рассылок</b>\n\n" + (
        "Список пуст." if not templates else "Выберите шаблон, чтобы использовать его, или удалите ненужный."
    )
    await callback.message.edit_text(text, reply_markup=templates_kb(templates))


@router.callback_query(F.data == BroadcastBtn.TPL_NEW)
async def cb_template_new(callback: CallbackQuery, user_service: UserService, state: FSMContext) -> None:
    role = await _check_admin(callback, user_service)
    if role is None:
        return
    await state.set_state(BroadcastWizard.waiting_text)
    await state.update_data(_tpl_new_flow=True)
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"🗂 <b>Новый шаблон</b>\n\nВведите текст шаблона (до {_MAX_TEXT} символов):",
        reply_markup=CANCEL_KB,
    )


# ── Callback: 💾 Сохранить как шаблон (из предпросмотра) ──────────────────────

@router.callback_query(F.data == BroadcastBtn.SAVE_TPL, BroadcastWizard.preview)
async def cb_save_template_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BroadcastWizard.waiting_template_name)
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"💾 Введите название шаблона (до {_MAX_TPL_NAME} символов):",
        reply_markup=CANCEL_KB,
    )


@router.message(BroadcastWizard.waiting_template_name)
async def handle_template_name(
    message: Message, state: FSMContext, broadcast_service: BroadcastService, audit_service: AuditService, user_service: UserService
) -> None:
    if not message.text or message.text.startswith("/"):
        await message.answer("⚠️ Пожалуйста, введите название шаблона сообщением.")
        return
    name = message.text.strip()
    if len(name) > _MAX_TPL_NAME:
        await message.answer(f"⚠️ Название слишком длинное (максимум {_MAX_TPL_NAME} символов). Попробуйте ещё раз.")
        return

    data = await state.get_data()
    text = data.get("text", "")
    user = message.from_user
    author_name = _author_name(user)

    await broadcast_service.save_template(user.id, author_name, name, text)

    actor_nick = await user_service.get_game_nick(user.id) or author_name
    actor_role = await user_service.get_role(user.id)
    await audit_service.log(
        user_id=user.id,
        game_nick=actor_nick,
        role=actor_role,
        action_type=AuditAction.BROADCAST_TEMPLATE_SAVE,
        description=f"{role_label(actor_role)} {actor_nick} сохранил шаблон рассылки «{name}»",
    )

    await state.clear()
    await reset_to_main_menu(message, f"✅ Шаблон «{name}» сохранён.")


# ── Планировщик ────────────────────────────────────────────────────────────

@router.callback_query(F.data == BroadcastBtn.SCHEDULE, BroadcastWizard.preview)
async def cb_schedule_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BroadcastWizard.waiting_schedule_datetime)
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "⏰ <b>Планирование рассылки</b>\n\n"
        "Введите дату и время отправки в формате <code>ДД.ММ.ГГГГ ЧЧ:ММ</code> (время указывается по UTC).\n"
        "Рассылка уйдёт всем участникам.\n\nПример: <code>05.07.2026 18:30</code>",
        reply_markup=CANCEL_KB,
    )


@router.message(BroadcastWizard.waiting_schedule_datetime)
async def handle_schedule_datetime(
    message: Message, state: FSMContext, broadcast_service: BroadcastService, audit_service: AuditService, user_service: UserService
) -> None:
    if not message.text or message.text.startswith("/"):
        await message.answer("⚠️ Пожалуйста, введите дату и время сообщением.")
        return

    raw = message.text.strip()
    try:
        dt = datetime.strptime(raw, "%d.%m.%Y %H:%M")
    except ValueError:
        await message.answer(
            "⚠️ Неверный формат. Введите дату и время как <code>ДД.ММ.ГГГГ ЧЧ:ММ</code>, например "
            "<code>05.07.2026 18:30</code>."
        )
        return

    if dt <= datetime.utcnow():
        await message.answer("⚠️ Указанное время уже прошло (сравнение по UTC). Введите время в будущем.")
        return

    data = await state.get_data()
    text = data.get("text", "")
    user = message.from_user
    author_name = _author_name(user)

    scheduled_at = dt.strftime("%Y-%m-%d %H:%M:00")
    broadcast_id = await broadcast_service.create(user.id, author_name, text, audience="all")
    await broadcast_service.schedule(broadcast_id, scheduled_at)

    actor_nick = await user_service.get_game_nick(user.id) or author_name
    actor_role = await user_service.get_role(user.id)
    await audit_service.log(
        user_id=user.id,
        game_nick=actor_nick,
        role=actor_role,
        action_type=AuditAction.BROADCAST_SCHEDULE,
        description=f"{role_label(actor_role)} {actor_nick} запланировал рассылку #{broadcast_id} на {scheduled_at} UTC",
    )

    await state.clear()
    await reset_to_main_menu(
        message,
        f"✅ Рассылка #{broadcast_id} запланирована на {raw} (UTC).\nПолучатели: все участники.",
    )


@router.callback_query(F.data == BroadcastBtn.SCHEDULED)
async def cb_scheduled_list(callback: CallbackQuery, user_service: UserService, broadcast_service: BroadcastService) -> None:
    role = await _check_admin(callback, user_service)
    if role is None:
        return
    await callback.answer()
    scheduled = await broadcast_service.list_scheduled()
    if not scheduled:
        await callback.message.edit_text(
            "⏰ <b>Запланированные рассылки</b>\n\nСейчас ничего не запланировано.",
            reply_markup=BACK_ONLY_KB,
        )
        return

    lines = ["⏰ <b>Запланированные рассылки</b>\n"]
    for row in scheduled:
        lines.append(
            f"#{row['id']} · {row['scheduled_at']} UTC\n"
            f"👤 {row['author_name']}\n"
            f"«{_short_text(row['text'])}»\n"
        )
    await callback.message.edit_text("\n".join(lines), reply_markup=scheduled_kb(scheduled))


@router.callback_query(F.data.startswith(BroadcastBtn.SCHED_CANCEL_PREFIX))
async def cb_scheduled_cancel(
    callback: CallbackQuery, user_service: UserService, broadcast_service: BroadcastService, audit_service: AuditService
) -> None:
    role = await _check_admin(callback, user_service)
    if role is None:
        return
    broadcast_id = int(callback.data.removeprefix(BroadcastBtn.SCHED_CANCEL_PREFIX))
    ok = await broadcast_service.cancel_scheduled(broadcast_id)
    if ok:
        actor_nick = await user_service.get_game_nick(callback.from_user.id) or _author_name(callback.from_user)
        await audit_service.log(
            user_id=callback.from_user.id,
            game_nick=actor_nick,
            role=role,
            action_type=AuditAction.BROADCAST_SCHEDULE_CANCEL,
            description=f"{role_label(role)} {actor_nick} отменил запланированную рассылку #{broadcast_id}",
        )
        await callback.answer("❌ Рассылка отменена.")
    else:
        await callback.answer("⚠️ Рассылка уже отправлена или отменена.", show_alert=True)

    scheduled = await broadcast_service.list_scheduled()
    if not scheduled:
        await callback.message.edit_text(
            "⏰ <b>Запланированные рассылки</b>\n\nСейчас ничего не запланировано.",
            reply_markup=BACK_ONLY_KB,
        )
        return
    lines = ["⏰ <b>Запланированные рассылки</b>\n"]
    for row in scheduled:
        lines.append(
            f"#{row['id']} · {row['scheduled_at']} UTC\n"
            f"👤 {row['author_name']}\n"
            f"«{_short_text(row['text'])}»\n"
        )
    await callback.message.edit_text("\n".join(lines), reply_markup=scheduled_kb(scheduled))
