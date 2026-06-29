# -*- coding: utf-8 -*-
"""
Единый мастер создания публикаций.

Работает для: 📰 Новости, 📅 События, 📚 Гайды, 📸 Скриншоты.

Сценарий:
  1. Внешний обработчик устанавливает состояние PublishWizard.waiting_title
     и кладёт в FSM data: {"content_type": "<тип>"}
  2. Мастер собирает заголовок → текст → показывает предпросмотр.
  3. Inline-кнопки: Опубликовать / Изменить заголовок / Изменить текст / Закрыть.
"""
import datetime
import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.main_menu import MAIN_KEYBOARD
from bot.keyboards.publish import PREVIEW_KB, PublishBtn
from bot.models.audit import AuditAction
from bot.models.user import UserRole
from bot.services.audit_service import AuditService
from bot.services.news_service import NewsService
from bot.services.topic_service import TopicService
from bot.services.user_service import UserService
from bot.states.publish import PublishWizard
from bot.utils.roles import role_label

router = Router()
logger = logging.getLogger(__name__)

_MAX_TITLE   = 100
_MAX_CONTENT = 4000

# ── Конфигурация типов публикаций ─────────────────────────────────────────────

_TYPES: dict[str, dict] = {
    "news": {
        "icon":       "📰",
        "label":      "Новость",
        "topic":      "news",
        "audit":      AuditAction.NEWS_CREATE,
        "verb":       "создал новость",
        "uses_db":    True,
    },
    "events": {
        "icon":       "📅",
        "label":      "Событие",
        "topic":      "events",
        "audit":      AuditAction.EVENT_CREATE,
        "verb":       "создал событие",
        "uses_db":    False,
    },
    "guides": {
        "icon":       "📚",
        "label":      "Гайд",
        "topic":      "guides",
        "audit":      AuditAction.GUIDE_CREATE,
        "verb":       "создал гайд",
        "uses_db":    False,
    },
    "screenshots": {
        "icon":       "📸",
        "label":      "Скриншот",
        "topic":      "screenshots",
        "audit":      AuditAction.SCREENSHOT_UPLOAD,
        "verb":       "загрузил скриншот",
        "uses_db":    False,
    },
}

# ── Вспомогательные функции ───────────────────────────────────────────────────

def _format_date(dt: datetime.datetime | None) -> str:
    if dt is None:
        return "—"
    return dt.strftime("%d.%m.%Y %H:%M")


def _build_preview(icon: str, label: str, title: str, content: str) -> str:
    return (
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{icon} <b>Предпросмотр — {label}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📝 <b>Заголовок</b>\n"
        f"{title}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📄 <b>Текст</b>\n"
        f"{content}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Проверьте информацию перед публикацией.\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )


def _author_name(user) -> str:
    if user.username:
        return f"@{user.username}"
    return user.first_name or "Автор"


# ── Шаг 1: заголовок ─────────────────────────────────────────────────────────

@router.message(PublishWizard.waiting_title)
async def handle_waiting_title(message: Message, state: FSMContext) -> None:
    if not message.text or message.text.startswith("/"):
        await message.answer("⚠️ Пожалуйста, введите заголовок текстом.")
        return
    title = message.text.strip()
    if len(title) > _MAX_TITLE:
        await message.answer(
            f"⚠️ Заголовок слишком длинный (максимум {_MAX_TITLE} символов). "
            "Попробуйте ещё раз."
        )
        return

    data = await state.get_data()
    await state.update_data(title=title)
    await state.set_state(PublishWizard.waiting_content)

    cfg = _TYPES.get(data.get("content_type", "news"), _TYPES["news"])
    await message.answer(
        f"📝 Заголовок сохранён: <b>{title}</b>\n\n"
        f"Теперь введите <b>текст</b> {cfg['label'].lower()}а "
        f"(до {_MAX_CONTENT} символов):\n\n"
        "<i>Отправьте /cancel для отмены</i>",
    )


# ── Шаг 2: текст → предпросмотр ──────────────────────────────────────────────

@router.message(PublishWizard.waiting_content)
async def handle_waiting_content(message: Message, state: FSMContext) -> None:
    if not message.text or message.text.startswith("/"):
        await message.answer("⚠️ Пожалуйста, введите текст сообщением.")
        return
    content = message.text.strip()
    if len(content) > _MAX_CONTENT:
        await message.answer(
            f"⚠️ Текст слишком длинный (максимум {_MAX_CONTENT} символов). "
            "Попробуйте ещё раз."
        )
        return

    data = await state.get_data()
    await state.update_data(content=content)
    await state.set_state(PublishWizard.preview)

    cfg   = _TYPES.get(data.get("content_type", "news"), _TYPES["news"])
    title = data.get("title", "")
    await message.answer(
        _build_preview(cfg["icon"], cfg["label"], title, content),
        reply_markup=PREVIEW_KB,
    )


# ── Кнопка: ✅ Опубликовать ───────────────────────────────────────────────────

@router.callback_query(F.data == PublishBtn.CONFIRM, PublishWizard.preview)
async def cb_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    news_service: NewsService,
    user_service: UserService,
    audit_service: AuditService,
    topic_service: TopicService,
) -> None:
    data         = await state.get_data()
    content_type = data.get("content_type", "news")
    title        = data.get("title", "")
    content      = data.get("content", "")
    cfg          = _TYPES.get(content_type, _TYPES["news"])

    user        = callback.from_user
    author_name = _author_name(user)
    author_id   = user.id

    actor_nick = await user_service.get_game_nick(author_id) or author_name
    actor_role = await user_service.get_role(author_id)

    await state.clear()
    now = datetime.datetime.now(datetime.timezone.utc)

    # ── Публикация в БД (только для новостей) ────────────────────────────
    if cfg["uses_db"]:
        item = await news_service.create(title, content, author_id, author_name)
        pub_date = item.created_at
        logger.info(
            "Пользователь %s создал %s #%d: %r",
            author_id, content_type, item.id, title,
        )
    else:
        pub_date = now
        logger.info(
            "Пользователь %s создал %s: %r",
            author_id, content_type, title,
        )

    # ── Журнал аудита ─────────────────────────────────────────────────────
    await audit_service.log(
        user_id=author_id,
        game_nick=actor_nick,
        role=actor_role,
        action_type=cfg["audit"],
        description=f"{role_label(actor_role)} {actor_nick} {cfg['verb']} «{title}»",
    )

    # ── Публикация в ветку Telegram ───────────────────────────────────────
    group_text = (
        f"{cfg['icon']} <b>{title}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{content}\n\n"
        f"📅 {_format_date(pub_date)}  •  ✍️ {author_name}"
    )
    ok = await topic_service.publish(bot, cfg["topic"], group_text)
    topic_note = "" if ok else "\n\n⚠️ <i>Не удалось опубликовать в группу.</i>"

    # ── Подтверждение администратору ─────────────────────────────────────
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"✅ <b>{cfg['icon']} {cfg['label']} опубликован(а)!</b>\n\n"
        f"<b>{title}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{content[:200]}{'…' if len(content) > 200 else ''}\n\n"
        f"📅 {_format_date(pub_date)}{topic_note}",
        reply_markup=MAIN_KEYBOARD,
    )
    await callback.answer()


# ── Кнопка: ✏️ Изменить заголовок ────────────────────────────────────────────

@router.callback_query(F.data == PublishBtn.EDIT_TITLE)
async def cb_edit_title(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    cfg  = _TYPES.get(data.get("content_type", "news"), _TYPES["news"])
    await state.set_state(PublishWizard.waiting_title)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"✏️ Введите новый <b>заголовок</b> {cfg['label'].lower()}а "
        f"(до {_MAX_TITLE} символов):\n\n"
        "<i>Отправьте /cancel для отмены</i>",
    )
    await callback.answer()


# ── Кнопка: 📝 Изменить текст ────────────────────────────────────────────────

@router.callback_query(F.data == PublishBtn.EDIT_CONTENT)
async def cb_edit_content(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    cfg  = _TYPES.get(data.get("content_type", "news"), _TYPES["news"])
    await state.set_state(PublishWizard.waiting_content)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"📝 Введите новый <b>текст</b> {cfg['label'].lower()}а "
        f"(до {_MAX_CONTENT} символов):\n\n"
        "<i>Отправьте /cancel для отмены</i>",
    )
    await callback.answer()


# ── Кнопка: ❌ Закрыть ────────────────────────────────────────────────────────

@router.callback_query(F.data == PublishBtn.CANCEL)
async def cb_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "❌ Создание отменено.\n\nВыберите раздел в главном меню.",
        reply_markup=MAIN_KEYBOARD,
    )
    await callback.answer()


# ── /cancel через команду ─────────────────────────────────────────────────────

@router.message(
    Command("cancel"),
    StateFilter(
        PublishWizard.waiting_title,
        PublishWizard.waiting_content,
        PublishWizard.preview,
    ),
)
async def handle_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "❌ Создание отменено.\n\nВыберите раздел в главном меню.",
        reply_markup=MAIN_KEYBOARD,
    )
