# -*- coding: utf-8 -*-
"""
Обработчик раздела «💡 Жалобы и предложения».

Callback-схема:
  cmp:create          — начать создание обращения
  cmp:list:{page}     — список всех обращений (менеджеры)
  cmp:mine:{page}     — мои обращения
  cmp:view:{id}       — просмотр обращения
  cmp:status:{id}:{s} — сменить статус (менеджеры)
  cmp:reply:{id}      — добавить ответ (менеджеры)
  cmp:delconf:{id}    — подтвердить удаление (менеджеры)
  cmp:del:{id}        — удалить (менеджеры)
  cmp:noop            — индикатор страниц
"""
import logging

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.db import Database
from bot.keyboards.complaints import (
    PAGE_SIZE,
    complaint_delete_confirm_kb,
    complaint_view_kb,
    complaints_list_kb,
    complaints_main_kb,
    complaints_manager_kb,
    status_label,
)
from bot.keyboards.main_menu import BTN, MAIN_KEYBOARD
from bot.models.audit import AuditAction
from bot.models.user import UserRole
from bot.services.audit_service import AuditService
from bot.services.user_service import UserService
from bot.states.complaints import ComplaintCreate, ComplaintReply
from bot.utils.roles import role_label

router = Router()
logger = logging.getLogger(__name__)

_MANAGER_ROLES = {UserRole.LEADER, UserRole.CLAN_CHILD, UserRole.ELDER}

_MAX_TITLE   = 100
_MAX_CONTENT = 2000
_MAX_REPLY   = 1000


def _fmt_date(dt_str: str) -> str:
    months = {1: "января", 2: "февраля", 3: "марта", 4: "апреля",
              5: "мая", 6: "июня", 7: "июля", 8: "августа",
              9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"}
    try:
        y, m, d = int(dt_str[:4]), int(dt_str[5:7]), int(dt_str[8:10])
        return f"{d} {months[m]} {y}"
    except Exception:
        return dt_str


def _fmt_complaint(row, show_author: bool = True) -> str:
    lines = [f"💡 <b>{row['title']}</b>", "", row["content"], ""]
    if show_author:
        lines.append(f"📅 {_fmt_date(row['created_at'])}  •  ✍️ {row['user_name']}")
    else:
        lines.append(f"📅 {_fmt_date(row['created_at'])}")
    lines.append(f"🏷 {status_label(row['status'])}")
    if row["admin_reply"]:
        lines += ["", f"💬 <b>Ответ администрации:</b>", row["admin_reply"]]
        if row["replied_by"]:
            lines.append(f"<i>— {row['replied_by']}</i>")
    return "\n".join(lines)


async def _is_manager(user_id: int, user_service: UserService) -> bool:
    role = await user_service.get_role(user_id)
    return role in _MANAGER_ROLES


# ── Главный экран раздела ─────────────────────────────────────────────────────

@router.message(F.text == BTN.COMPLAINTS, StateFilter(None))
async def handle_complaints(message: Message, user_service: UserService) -> None:
    manager = await _is_manager(message.from_user.id, user_service)
    text = (
        "💡 <b>Жалобы и предложения</b>\n\n"
        "Здесь вы можете создать обращение к администрации клана.\n"
        "Администрация рассмотрит его и даст ответ."
    )
    kb = complaints_manager_kb() if manager else complaints_main_kb()
    await message.answer(text, reply_markup=kb)


# ── Создание обращения (FSM) ──────────────────────────────────────────────────

@router.callback_query(F.data == "cmp:create")
async def cb_create(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ComplaintCreate.waiting_title)
    await callback.answer()
    await callback.message.answer(
        f"📝 <b>Создание обращения</b>\n\n"
        f"Введите <b>тему обращения</b> (до {_MAX_TITLE} символов):\n\n"
        "<i>Отправьте /cancel для отмены</i>",
    )


@router.message(ComplaintCreate.waiting_title)
async def fsm_complaint_title(message: Message, state: FSMContext) -> None:
    if not message.text or message.text.startswith("/"):
        await message.answer("⚠️ Введите тему обращения текстом.")
        return
    title = message.text.strip()
    if len(title) > _MAX_TITLE:
        await message.answer(f"⚠️ Тема слишком длинная (максимум {_MAX_TITLE} символов).")
        return
    await state.update_data(title=title)
    await state.set_state(ComplaintCreate.waiting_content)
    await message.answer(
        f"📝 Теперь введите <b>текст обращения</b> (до {_MAX_CONTENT} символов):\n\n"
        "<i>Отправьте /cancel для отмены</i>",
    )


@router.message(ComplaintCreate.waiting_content)
async def fsm_complaint_content(
    message: Message,
    state: FSMContext,
    db: Database,
    audit_service: AuditService,
    user_service: UserService,
) -> None:
    if not message.text or message.text.startswith("/"):
        await message.answer("⚠️ Введите текст обращения.")
        return
    content = message.text.strip()
    if len(content) > _MAX_CONTENT:
        await message.answer(f"⚠️ Текст слишком длинный (максимум {_MAX_CONTENT} символов).")
        return

    data = await state.get_data()
    title = data["title"]
    user_id = message.from_user.id
    user_name = (
        await user_service.get_game_nick(user_id)
        or message.from_user.full_name
    )

    complaint_id = await db.complaint_create(user_id, user_name, title, content)
    await state.clear()

    role = await user_service.get_role(user_id)
    await audit_service.log(
        user_id=user_id,
        game_nick=user_name,
        role=role,
        action_type=AuditAction.COMPLAINT_CREATE,
        description=f"{role_label(role)} {user_name} создал обращение #{complaint_id}: «{title}»",
    )
    logger.info("Пользователь %s создал обращение #%d", user_id, complaint_id)

    await message.answer(
        f"✅ <b>Обращение #{complaint_id} создано!</b>\n\n"
        f"Тема: <b>{title}</b>\n\n"
        "Администрация рассмотрит ваше обращение и даст ответ.",
        reply_markup=MAIN_KEYBOARD,
    )


# ── Список обращений ──────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cmp:list:"))
async def cb_list_all(callback: CallbackQuery, db: Database, user_service: UserService) -> None:
    if not await _is_manager(callback.from_user.id, user_service):
        await callback.answer("🔒 Недостаточно прав.", show_alert=True)
        return
    page = int(callback.data.split(":")[2])
    rows = await db.complaint_list()
    total = len(rows)
    page_rows = rows[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]

    text = (
        f"💡 <b>Все обращения</b>\n\nВсего: {total}"
        if total else
        "💡 <b>Все обращения</b>\n\nОбращений пока нет."
    )
    await callback.answer()
    await callback.message.edit_text(
        text,
        reply_markup=complaints_list_kb(page_rows, page, total, "list"),
    )


@router.callback_query(F.data.startswith("cmp:mine:"))
async def cb_list_mine(callback: CallbackQuery, db: Database) -> None:
    page = int(callback.data.split(":")[2])
    rows = await db.complaint_list_by_user(callback.from_user.id)
    total = len(rows)
    page_rows = rows[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]

    text = (
        f"💡 <b>Мои обращения</b>\n\nВсего: {total}"
        if total else
        "💡 <b>Мои обращения</b>\n\nВы ещё не создавали обращений."
    )
    await callback.answer()
    await callback.message.edit_text(
        text,
        reply_markup=complaints_list_kb(page_rows, page, total, "mine"),
    )


@router.callback_query(F.data == "cmp:noop")
async def cb_noop(callback: CallbackQuery) -> None:
    await callback.answer()


# ── Просмотр обращения ────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cmp:view:"))
async def cb_view(callback: CallbackQuery, db: Database, user_service: UserService) -> None:
    complaint_id = int(callback.data.split(":")[2])
    row = await db.complaint_get(complaint_id)
    if not row:
        await callback.answer("Обращение не найдено.", show_alert=True)
        return

    user_id = callback.from_user.id
    manager = await _is_manager(user_id, user_service)
    if not manager and row["user_id"] != user_id:
        await callback.answer("🔒 Нет доступа.", show_alert=True)
        return

    back_mode = "list" if manager else "mine"
    await callback.answer()
    await callback.message.edit_text(
        _fmt_complaint(row, show_author=manager),
        reply_markup=complaint_view_kb(complaint_id, row["status"], manager, back_mode),
    )


# ── Изменение статуса ─────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cmp:status:"))
async def cb_status(
    callback: CallbackQuery,
    db: Database,
    user_service: UserService,
    audit_service: AuditService,
) -> None:
    if not await _is_manager(callback.from_user.id, user_service):
        await callback.answer("🔒 Недостаточно прав.", show_alert=True)
        return
    parts = callback.data.split(":")
    complaint_id, new_status = int(parts[2]), parts[3]

    row = await db.complaint_get(complaint_id)
    if not row:
        await callback.answer("Обращение не найдено.", show_alert=True)
        return

    old_status = row["status"]
    await db.complaint_set_status(complaint_id, new_status)

    actor_nick = await user_service.get_game_nick(callback.from_user.id) or "?"
    role = await user_service.get_role(callback.from_user.id)
    await audit_service.log(
        user_id=callback.from_user.id,
        game_nick=actor_nick,
        role=role,
        action_type=AuditAction.COMPLAINT_STATUS,
        description=(
            f"{role_label(role)} {actor_nick} изменил статус обращения "
            f"#{complaint_id} «{row['title']}»: "
            f"{status_label(old_status)} → {status_label(new_status)}"
        ),
    )

    updated_row = await db.complaint_get(complaint_id)
    await callback.answer(f"Статус изменён: {status_label(new_status)}")
    await callback.message.edit_text(
        _fmt_complaint(updated_row, show_author=True),
        reply_markup=complaint_view_kb(complaint_id, new_status, True, "list"),
    )


# ── Ответ администрации (FSM) ─────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cmp:reply:"))
async def cb_reply(callback: CallbackQuery, user_service: UserService, state: FSMContext) -> None:
    if not await _is_manager(callback.from_user.id, user_service):
        await callback.answer("🔒 Недостаточно прав.", show_alert=True)
        return
    complaint_id = int(callback.data.split(":")[2])
    await state.set_state(ComplaintReply.waiting_reply)
    await state.update_data(complaint_id=complaint_id)
    await callback.answer()
    await callback.message.answer(
        f"💬 Введите <b>ответ администрации</b> для обращения #{complaint_id} "
        f"(до {_MAX_REPLY} символов):\n\n"
        "<i>Отправьте /cancel для отмены</i>",
    )


@router.message(ComplaintReply.waiting_reply)
async def fsm_reply(
    message: Message,
    state: FSMContext,
    db: Database,
    user_service: UserService,
    audit_service: AuditService,
) -> None:
    if not message.text or message.text.startswith("/"):
        await message.answer("⚠️ Введите ответ текстом.")
        return
    reply_text = message.text.strip()
    if len(reply_text) > _MAX_REPLY:
        await message.answer(f"⚠️ Ответ слишком длинный (максимум {_MAX_REPLY} символов).")
        return

    data = await state.get_data()
    complaint_id = data["complaint_id"]

    actor_nick = await user_service.get_game_nick(message.from_user.id) or "?"
    role = await user_service.get_role(message.from_user.id)

    row = await db.complaint_get(complaint_id)
    await db.complaint_set_reply(complaint_id, reply_text, actor_nick)
    await state.clear()

    await audit_service.log(
        user_id=message.from_user.id,
        game_nick=actor_nick,
        role=role,
        action_type=AuditAction.COMPLAINT_REPLY,
        description=f"{role_label(role)} {actor_nick} ответил на обращение #{complaint_id}",
    )

    title_log = row["title"] if row else f"#{complaint_id}"
    await message.answer(
        f"✅ <b>Ответ сохранён!</b>\n\nОбращение: <b>{title_log}</b>"
    )


# ── Удаление ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cmp:delconf:"))
async def cb_delete_confirm(callback: CallbackQuery, user_service: UserService) -> None:
    if not await _is_manager(callback.from_user.id, user_service):
        await callback.answer("🔒 Недостаточно прав.", show_alert=True)
        return
    complaint_id = int(callback.data.split(":")[2])
    await callback.answer()
    await callback.message.edit_text(
        "🗑 <b>Удаление обращения</b>\n\nВы уверены? Это действие нельзя отменить.",
        reply_markup=complaint_delete_confirm_kb(complaint_id),
    )


@router.callback_query(F.data.startswith("cmp:del:"))
async def cb_delete(
    callback: CallbackQuery,
    db: Database,
    user_service: UserService,
    audit_service: AuditService,
) -> None:
    if not await _is_manager(callback.from_user.id, user_service):
        await callback.answer("🔒 Недостаточно прав.", show_alert=True)
        return
    complaint_id = int(callback.data.split(":")[2])
    row = await db.complaint_get(complaint_id)
    title_log = row["title"] if row else f"#{complaint_id}"

    await db.complaint_delete(complaint_id)
    actor_nick = await user_service.get_game_nick(callback.from_user.id) or "?"
    role = await user_service.get_role(callback.from_user.id)
    await audit_service.log(
        user_id=callback.from_user.id,
        game_nick=actor_nick,
        role=role,
        action_type=AuditAction.COMPLAINT_DELETE,
        description=f"{role_label(role)} {actor_nick} удалил обращение «{title_log}»",
    )

    await callback.answer("🗑 Обращение удалено.")
    rows = await db.complaint_list()
    total = len(rows)
    page_rows = rows[:PAGE_SIZE]
    await callback.message.edit_text(
        f"💡 <b>Все обращения</b>\n\nВсего: {total}" if total else "💡 <b>Все обращения</b>\n\nОбращений нет.",
        reply_markup=complaints_list_kb(page_rows, 0, total, "list"),
    )


# ── Отмена FSM ────────────────────────────────────────────────────────────────

@router.message(
    Command("cancel"),
    StateFilter(ComplaintCreate.waiting_title, ComplaintCreate.waiting_content, ComplaintReply.waiting_reply),
)
async def handle_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Действие отменено.", reply_markup=MAIN_KEYBOARD)
