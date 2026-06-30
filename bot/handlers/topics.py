# -*- coding: utf-8 -*-
"""
Обработчик «⚙️ Настройки → 🧵 Настройка веток».

Доступ: ✪ Лидер, ✧ Старейшина, ✦ Дитя клана.
"""
import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.admin_panel import AdminBtn, ADMIN_PANEL_KB
from bot.keyboards.topics import TOPICS_CANCEL_KB, TopicBtn, topics_menu_kb
from bot.models.topic import TOPIC_LABELS
from bot.models.user import UserRole
from bot.services.topic_service import TopicService
from bot.services.user_service import UserService
from bot.states.topics import TopicSetup

router = Router()
logger = logging.getLogger(__name__)

_MENU_TITLE = "🧵 <b>Настройка веток</b>"


async def _check_admin(cb: CallbackQuery, user_service: UserService) -> bool:
    role = await user_service.get_role(cb.from_user.id)
    if role not in UserRole.admin_roles():
        await cb.answer("🔒 Недостаточно прав.", show_alert=True)
        return False
    return True


def _format_sync_report(report: dict) -> str:
    """Форматирует отчёт синхронизации в текст для пользователя."""
    lines = ["🔄 <b>Результаты синхронизации</b>\n"]

    if report["created"]:
        lines.append(f"🆕 Созданы ({len(report['created'])}):")
        for k in report["created"]:
            lines.append(f"  • {TOPIC_LABELS.get(k, k)}")

    if report["name_fixed"]:
        lines.append(f"✏️ Исправлено название ({len(report['name_fixed'])}):")
        for k in report["name_fixed"]:
            lines.append(f"  • {TOPIC_LABELS.get(k, k)}")

    if report["ok"]:
        lines.append(f"✅ В порядке: {len(report['ok'])} тем")

    if report["missing"]:
        lines.append(f"⚠️ Тема удалена в Telegram ({len(report['missing'])}):")
        for k in report["missing"]:
            lines.append(f"  • {TOPIC_LABELS.get(k, k)} — thread_id сброшен, настройте заново")

    if report["no_permission"]:
        lines.append(f"🔒 Нет прав can_manage_topics ({len(report['no_permission'])}):")
        for k in report["no_permission"]:
            lines.append(f"  • {TOPIC_LABELS.get(k, k)}")
        lines.append("  <i>Назначьте боту роль администратора с правом управления темами.</i>")

    if report["errors"]:
        lines.append(f"❌ Ошибки ({len(report['errors'])}):")
        for k, err in report["errors"].items():
            lines.append(f"  • {TOPIC_LABELS.get(k, k)}: {err[:80]}")

    total = (
        len(report["created"]) + len(report["name_fixed"]) + len(report["ok"])
        + len(report["missing"]) + len(report["no_permission"]) + len(report["errors"])
    )
    lines.append(f"\n<i>Всего проверено: {total} тем</i>")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# ⚙️ Настройки → открывает меню веток
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == AdminBtn.SETTINGS)
async def cb_settings(
    callback: CallbackQuery,
    user_service: UserService,
    topic_service: TopicService,
) -> None:
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()
    topics = await topic_service.list_topics()
    await callback.message.answer(
        f"{_MENU_TITLE}\n\nВыберите ветку для настройки или нажмите «🔄 Синхронизировать»:",
        reply_markup=topics_menu_kb(topics),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 🔄 Синхронизировать темы
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == TopicBtn.SYNC)
async def cb_topics_sync(
    callback: CallbackQuery,
    user_service: UserService,
    topic_service: TopicService,
    bot: Bot,
) -> None:
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()

    progress = await callback.message.answer(
        "🔄 <b>Синхронизация тем...</b>\n\n<i>Это может занять несколько секунд.</i>"
    )

    report = await topic_service.sync_all_topics(bot)
    result_text = _format_sync_report(report)

    try:
        await progress.edit_text(result_text)
    except Exception:
        await callback.message.answer(result_text)

    # Обновляем меню с актуальными thread_id
    topics = await topic_service.list_topics()
    await callback.message.answer(
        f"{_MENU_TITLE}\n\nВыберите ветку для настройки:",
        reply_markup=topics_menu_kb(topics),
    )
    logger.info(
        "Синхронизация тем: created=%s fixed=%s ok=%s missing=%s no_perm=%s errors=%s",
        report["created"], report["name_fixed"], report["ok"],
        report["missing"], report["no_permission"], list(report["errors"].keys()),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Выбор конкретной ветки → запрос Thread ID
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith(TopicBtn.PREFIX))
async def cb_topic_select(
    callback: CallbackQuery,
    user_service: UserService,
    state: FSMContext,
) -> None:
    if not await _check_admin(callback, user_service):
        return
    topic_name = callback.data[len(TopicBtn.PREFIX):]
    if topic_name not in TOPIC_LABELS:
        await callback.answer("Неизвестная ветка.", show_alert=True)
        return
    label = TOPIC_LABELS[topic_name]
    await state.set_state(TopicSetup.waiting_thread_id)
    await state.update_data(topic_name=topic_name)
    await callback.answer()
    await callback.message.answer(
        f"🧵 <b>Настройка ветки</b>\n\n"
        f"Введите <b>Message Thread ID</b> для ветки «{label}»:\n\n"
        f"<i>Чтобы узнать ID, перешлите любое сообщение из нужной ветки боту "
        f"@RawDataBot или нажмите «Копировать ссылку» — ID указан после #.</i>\n\n"
        f"Введите <code>0</code> чтобы отключить ветку.",
        reply_markup=TOPICS_CANCEL_KB,
    )


# ─────────────────────────────────────────────────────────────────────────────
# FSM: получение Thread ID от администратора
# ─────────────────────────────────────────────────────────────────────────────

@router.message(TopicSetup.waiting_thread_id)
async def handle_thread_id(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    topic_service: TopicService,
) -> None:
    role = await user_service.get_role(message.from_user.id)
    if role not in UserRole.admin_roles():
        await state.clear()
        return

    data       = await state.get_data()
    topic_name = data.get("topic_name", "")
    raw        = (message.text or "").strip()

    if not raw.lstrip("-").isdigit():
        await message.answer(
            "⚠️ Введите числовой ID (например: <code>12345</code>) "
            "или <code>0</code> для отключения.",
            reply_markup=TOPICS_CANCEL_KB,
        )
        return

    thread_id: int | None = int(raw)
    if thread_id == 0:
        thread_id = None

    await topic_service.set_topic(topic_name, thread_id)
    await state.clear()

    label = TOPIC_LABELS.get(topic_name, topic_name)
    if thread_id is None:
        status = "отключена (сообщения идут в общий чат)"
    else:
        status = f"настроена → thread ID <code>{thread_id}</code>"

    topics = await topic_service.list_topics()
    await message.answer(f"✅ Ветка «{label}» {status}.")
    await message.answer(
        f"{_MENU_TITLE}\n\nВыберите ветку для настройки:",
        reply_markup=topics_menu_kb(topics),
    )
    logger.info(
        "Администратор %s задал thread_id=%s для ветки '%s'",
        message.from_user.id, thread_id, topic_name,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Навигация
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == TopicBtn.CANCEL)
async def cb_topics_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Отменено.")
    await callback.message.delete()


@router.callback_query(F.data == TopicBtn.BACK)
async def cb_topics_back(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.delete()
