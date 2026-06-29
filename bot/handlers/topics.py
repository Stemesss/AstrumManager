# -*- coding: utf-8 -*-
"""
Обработчик «⚙️ Настройки → 🧵 Настройка веток».

Доступ: 👑 Лидер, ⭐ Дитя клана, 🛡️ Старейшина.
"""
import logging

from aiogram import F, Router
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

_HEADER = "━━━━━━━━━━━━━━━━━━━━"
_MENU_TITLE = f"{_HEADER}\n🧵 <b>Настройка веток</b>\n{_HEADER}"


async def _check_admin(cb: CallbackQuery, user_service: UserService) -> bool:
    role = await user_service.get_role(cb.from_user.id)
    if role not in UserRole.admin_roles():
        await cb.answer("🔒 Недостаточно прав.", show_alert=True)
        return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# ⚙️ Настройки → открывает меню веток
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == AdminBtn.SETTINGS)
async def cb_settings(
    callback: CallbackQuery,
    user_service: UserService,
    topic_service: TopicService,
) -> None:
    """Открывает раздел «⚙️ Настройки» → список веток."""
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()
    topics = await topic_service.list_topics()
    await callback.message.answer(
        f"{_MENU_TITLE}\n\nВыберите ветку для настройки:",
        reply_markup=topics_menu_kb(topics),
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
    """Пользователь выбрал ветку — запрашиваем Message Thread ID."""
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
        f"{_HEADER}\n"
        f"🧵 <b>Настройка ветки</b>\n"
        f"{_HEADER}\n\n"
        f"Введите <b>Message Thread ID</b>\n"
        f"для ветки «{label}»:\n\n"
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
    """Сохраняет введённый Message Thread ID."""
    role = await user_service.get_role(message.from_user.id)
    if role not in UserRole.admin_roles():
        await state.clear()
        return

    data = await state.get_data()
    topic_name: str = data.get("topic_name", "")
    raw = (message.text or "").strip()

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
    await message.answer(
        f"{_HEADER}\n"
        f"✅ Ветка «{label}» {status}.\n"
        f"{_HEADER}",
    )
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
    """Отмена ввода Thread ID."""
    await state.clear()
    await callback.answer("Отменено.")
    await callback.message.delete()


@router.callback_query(F.data == TopicBtn.BACK)
async def cb_topics_back(callback: CallbackQuery) -> None:
    """Возврат к панели администрации."""
    await callback.answer()
    await callback.message.delete()
