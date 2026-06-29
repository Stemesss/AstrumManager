# -*- coding: utf-8 -*-
"""
Обработчик раздела «✅ Правила».

Показывает последнюю версию правил клана.
Менеджеры могут редактировать текст и публиковать новые редакции.

Callback-схема:
  rul:edit:{id}  — редактировать текст текущих правил (FSM)
  rul:pin:{id}   — закрепить правила в теме форума
  rul:new        — опубликовать новую редакцию (PublishWizard)
  rul:cancel     — отмена редактирования
"""
import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.main_menu import BTN, MAIN_KEYBOARD
from bot.keyboards.rules import rules_cancel_kb, rules_view_kb
from bot.models.audit import AuditAction
from bot.models.user import UserRole
from bot.services.audit_service import AuditService
from bot.services.news_service import NewsService
from bot.services.topic_service import TopicService
from bot.services.user_service import UserService
from bot.states.publish import PublishWizard
from bot.states.rules import RulesEdit
from bot.utils.roles import role_label

router = Router()
logger = logging.getLogger(__name__)

_MANAGER_ROLES = {UserRole.LEADER, UserRole.CLAN_CHILD, UserRole.ELDER}
_MAX_CONTENT   = 4000


def _fmt_date(dt_str: str) -> str:
    months = {1: "января", 2: "февраля", 3: "марта", 4: "апреля",
              5: "мая", 6: "июня", 7: "июля", 8: "августа",
              9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"}
    try:
        y, m, d = int(dt_str[:4]), int(dt_str[5:7]), int(dt_str[8:10])
        return f"{d} {months[m]} {y}"
    except Exception:
        return dt_str


async def _is_manager(user_id: int, user_service: UserService) -> bool:
    role = await user_service.get_role(user_id)
    return role in _MANAGER_ROLES


async def _show_rules(
    target: Message | CallbackQuery,
    news_service: NewsService,
    user_service: UserService,
    edit: bool = False,
) -> None:
    user_id = target.from_user.id if target.from_user else 0
    manager = await _is_manager(user_id, user_service)

    items = await news_service.get_list_by_type("rules")
    if not items:
        text = (
            "✅ <b>Правила клана</b>\n\n"
            "Правила ещё не опубликованы."
        )
        kb = rules_view_kb(None, manager)
        msg = target if isinstance(target, Message) else target.message
        if edit:
            await msg.edit_text(text, reply_markup=kb)
        else:
            await msg.answer(text, reply_markup=kb)
        return

    rule = items[0]
    updated = rule.updated_at if rule.updated_at != rule.created_at else rule.created_at
    text = (
        f"✅ <b>{rule.title}</b>\n\n"
        f"{rule.content}\n\n"
        f"📅 Редакция от {_fmt_date(updated)}  •  ✍️ {rule.author_name}"
    )
    kb = rules_view_kb(rule.id, manager)

    msg = target if isinstance(target, Message) else target.message
    if edit:
        try:
            await msg.edit_text(text, reply_markup=kb)
        except Exception:
            await msg.answer(text, reply_markup=kb)
    else:
        await msg.answer(text, reply_markup=kb)


# ── Главный экран ─────────────────────────────────────────────────────────────

@router.message(F.text == BTN.RULES, StateFilter(None))
async def handle_rules(message: Message, news_service: NewsService, user_service: UserService) -> None:
    await _show_rules(message, news_service, user_service)


# ── Редактирование правил (FSM) ───────────────────────────────────────────────

@router.callback_query(F.data.startswith("rul:edit:"))
async def cb_edit(callback: CallbackQuery, user_service: UserService, state: FSMContext) -> None:
    if not await _is_manager(callback.from_user.id, user_service):
        await callback.answer("🔒 Недостаточно прав.", show_alert=True)
        return
    rules_id = int(callback.data.split(":")[2])
    await state.set_state(RulesEdit.waiting_content)
    await state.update_data(rules_id=rules_id)
    await callback.answer()
    await callback.message.answer(
        f"✏️ Введите <b>новый текст правил</b> (до {_MAX_CONTENT} символов):\n\n"
        "<i>Текущие правила будут обновлены. Отправьте /cancel для отмены.</i>",
        reply_markup=rules_cancel_kb(),
    )


@router.message(RulesEdit.waiting_content)
async def fsm_rules_content(
    message: Message,
    state: FSMContext,
    news_service: NewsService,
    user_service: UserService,
    audit_service: AuditService,
) -> None:
    if not message.text or message.text.startswith("/"):
        await message.answer("⚠️ Введите текст правил.")
        return
    content = message.text.strip()
    if len(content) > _MAX_CONTENT:
        await message.answer(f"⚠️ Текст слишком длинный (максимум {_MAX_CONTENT} символов).")
        return

    data = await state.get_data()
    rules_id = data["rules_id"]
    await news_service.update_content(rules_id, content)
    await state.clear()

    actor_nick = await user_service.get_game_nick(message.from_user.id) or "?"
    role = await user_service.get_role(message.from_user.id)
    await audit_service.log(
        user_id=message.from_user.id,
        game_nick=actor_nick,
        role=role,
        action_type=AuditAction.RULES_EDIT,
        description=f"{role_label(role)} {actor_nick} обновил текст правил клана",
    )
    await message.answer("✅ <b>Правила обновлены!</b>")
    await _show_rules(message, news_service, user_service)


@router.callback_query(F.data == "rul:cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Отменено.")
    await callback.message.delete()


# ── Публикация новой редакции (PublishWizard) ─────────────────────────────────

@router.callback_query(F.data == "rul:new")
async def cb_new(callback: CallbackQuery, user_service: UserService, state: FSMContext) -> None:
    if not await _is_manager(callback.from_user.id, user_service):
        await callback.answer("🔒 Недостаточно прав.", show_alert=True)
        return
    await state.set_state(PublishWizard.waiting_title)
    await state.update_data(content_type="rules")
    await callback.answer()
    await callback.message.answer(
        "✅ <b>Новая редакция правил</b>\n\n"
        "Введите <b>заголовок</b> (например: «Правила клана Astrum»):\n\n"
        "<i>Отправьте /cancel для отмены</i>",
        reply_markup=MAIN_KEYBOARD,
    )


# ── Закрепление в теме ────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("rul:pin:"))
async def cb_pin(
    callback: CallbackQuery,
    bot: Bot,
    news_service: NewsService,
    user_service: UserService,
    topic_service: TopicService,
    audit_service: AuditService,
) -> None:
    if not await _is_manager(callback.from_user.id, user_service):
        await callback.answer("🔒 Недостаточно прав.", show_alert=True)
        return
    rules_id = int(callback.data.split(":")[2])
    rule = await news_service.get_by_id(rules_id)
    if not rule:
        await callback.answer("Правила не найдены.", show_alert=True)
        return

    text = f"✅ <b>{rule.title}</b>\n\n{rule.content}"
    thread_id = await topic_service.get_thread_id("rules")
    sent = False
    try:
        msg = await bot.send_message(
            chat_id=topic_service.chat_id,
            text=text,
            message_thread_id=thread_id,
            parse_mode="HTML",
        )
        try:
            await bot.pin_chat_message(
                chat_id=topic_service.chat_id,
                message_id=msg.message_id,
            )
        except Exception:
            pass
        sent = True
    except Exception as exc:
        logger.warning("Не удалось опубликовать правила в тему: %s", exc)

    if sent:
        actor_nick = await user_service.get_game_nick(callback.from_user.id) or "?"
        role = await user_service.get_role(callback.from_user.id)
        await audit_service.log(
            user_id=callback.from_user.id,
            game_nick=actor_nick,
            role=role,
            action_type=AuditAction.RULES_PIN,
            description=f"{role_label(role)} {actor_nick} закрепил правила клана в теме форума",
        )
        await callback.answer("📌 Правила опубликованы и закреплены в теме!")
    else:
        await callback.answer("⚠️ Не удалось опубликовать в тему. Проверьте настройки.", show_alert=True)


# ── Отмена FSM ────────────────────────────────────────────────────────────────

@router.message(Command("cancel"), StateFilter(RulesEdit.waiting_content))
async def handle_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Редактирование отменено.", reply_markup=MAIN_KEYBOARD)
