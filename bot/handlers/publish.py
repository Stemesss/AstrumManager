# -*- coding: utf-8 -*-
"""
Единый мастер создания публикаций.

Работает для: 📰 Новости, 📅 События, 📚 Гайды, 📸 Скриншоты.

Сценарий:
  1. Внешний обработчик устанавливает состояние PublishWizard.waiting_title
     и кладёт в FSM data: {"content_type": "<тип>"}
  2. Мастер собирает заголовок → текст → вложения (необязательно) → предпросмотр.
  3. Inline-кнопки предпросмотра:
       Опубликовать / Добавить ещё / Удалить вложения /
       Изменить заголовок / Изменить текст / Закрыть
"""
import datetime
import logging
import re

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.db import Database
from bot.keyboards.main_menu import MAIN_KEYBOARD
from bot.keyboards.publish import ATTACH_KB, PREVIEW_KB, PublishBtn
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
_URL_RE      = re.compile(r"https?://\S+")

# ── Конфигурация типов публикаций ─────────────────────────────────────────────

_TYPES: dict[str, dict] = {
    "news": {
        "icon":    "📰",
        "label":   "Новость",
        "topic":   "news",
        "audit":   AuditAction.NEWS_CREATE,
        "verb":    "создал новость",
        "uses_db": True,
    },
    "events": {
        "icon":    "📅",
        "label":   "Событие",
        "topic":   "events",
        "audit":   AuditAction.EVENT_CREATE,
        "verb":    "создал событие",
        "uses_db": False,
    },
    "guides": {
        "icon":    "📚",
        "label":   "Гайд",
        "topic":   "guides",
        "audit":   AuditAction.GUIDE_CREATE,
        "verb":    "создал гайд",
        "uses_db": False,
    },
    "screenshots": {
        "icon":    "📸",
        "label":   "Скриншот",
        "topic":   "screenshots",
        "audit":   AuditAction.SCREENSHOT_UPLOAD,
        "verb":    "загрузил скриншот",
        "uses_db": False,
    },
}

# ── Хелперы для вложений ──────────────────────────────────────────────────────

def _empty_attachments() -> dict:
    return {"photos": [], "videos": [], "documents": [], "links": []}


def _has_attachments(a: dict) -> bool:
    return bool(a.get("photos") or a.get("videos") or a.get("documents") or a.get("links"))


def _build_attach_prompt(attachments: dict) -> str:
    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        "📎 <b>Вложения</b>",
        "━━━━━━━━━━━━━━━━━━━━\n",
        "Прикрепите вложения к публикации:\n",
        "🖼 Отправьте фото (одно или несколько)",
        "🎥 Отправьте видео",
        "📄 Отправьте документ (PDF, DOCX, ZIP…)",
        "🔗 Вставьте ссылку текстом\n",
    ]
    if _has_attachments(attachments):
        lines.append("📦 <b>Добавлено:</b>")
        if p := len(attachments.get("photos", [])):
            lines.append(f"  🖼 Фото: {p}")
        if v := len(attachments.get("videos", [])):
            lines.append(f"  🎥 Видео: {v}")
        if d := len(attachments.get("documents", [])):
            lines.append(f"  📄 Документы: {d}")
        if lk := len(attachments.get("links", [])):
            lines.append(f"  🔗 Ссылки: {lk}")
        lines.append("")
    lines.append("Нажмите <b>✅ Готово</b> для перехода к предпросмотру.")
    lines.append("<i>Или /cancel для отмены.</i>")
    return "\n".join(lines)


def _build_attach_summary(attachments: dict) -> str:
    """Блок вложений для предпросмотра."""
    if not _has_attachments(attachments):
        return ""
    lines = ["━━━━━━━━━━━━━━━━━━━━\n\n📎 <b>Вложения</b>"]
    if p := len(attachments.get("photos", [])):
        lines.append(f"🖼 Фото: {p}")
    if v := len(attachments.get("videos", [])):
        lines.append(f"🎥 Видео: {v}")
    if d := len(attachments.get("documents", [])):
        lines.append(f"📄 Документы: {d}")
    if lk := len(attachments.get("links", [])):
        lines.append(f"🔗 Ссылки: {lk}")
    return "\n".join(lines)


# ── Хелперы форматирования ────────────────────────────────────────────────────

def _format_date(dt: datetime.datetime | None) -> str:
    if dt is None:
        return "—"
    return dt.strftime("%d.%m.%Y %H:%M")


def _build_preview(
    icon: str,
    label: str,
    title: str,
    content: str,
    attachments: dict | None = None,
) -> str:
    text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{icon} <b>Предпросмотр — {label}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📝 <b>Заголовок</b>\n"
        f"{title}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📄 <b>Текст</b>\n"
        f"{content}\n\n"
    )
    if attachments and _has_attachments(attachments):
        text += _build_attach_summary(attachments) + "\n\n"
    text += (
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Проверьте информацию перед публикацией.\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    return text


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


# ── Шаг 2: текст → шаг вложений ──────────────────────────────────────────────

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

    await state.update_data(content=content, attachments=_empty_attachments())
    await state.set_state(PublishWizard.waiting_attachments)

    sent = await message.answer(
        _build_attach_prompt(_empty_attachments()),
        reply_markup=ATTACH_KB,
    )
    await state.update_data(attach_msg_id=sent.message_id)


# ── Шаг 3: сбор вложений ─────────────────────────────────────────────────────

@router.message(PublishWizard.waiting_attachments)
async def handle_waiting_attachments(message: Message, state: FSMContext, bot: Bot) -> None:
    data        = await state.get_data()
    attachments = data.get("attachments") or _empty_attachments()
    added       = ""

    if message.photo:
        photo = message.photo[-1]
        attachments["photos"].append({
            "file_id":        photo.file_id,
            "file_unique_id": photo.file_unique_id,
        })
        added = f"🖼 Фото добавлено. Всего фото: {len(attachments['photos'])}"

    elif message.video:
        v = message.video
        attachments["videos"].append({
            "file_id":        v.file_id,
            "file_unique_id": v.file_unique_id,
        })
        added = f"🎥 Видео добавлено. Всего видео: {len(attachments['videos'])}"

    elif message.document:
        d = message.document
        attachments["documents"].append({
            "file_id":        d.file_id,
            "file_unique_id": d.file_unique_id,
            "file_name":      d.file_name or "",
        })
        added = f"📄 Документ добавлен. Всего: {len(attachments['documents'])}"

    elif message.text and not message.text.startswith("/"):
        urls = _URL_RE.findall(message.text)
        if urls:
            attachments["links"].extend(urls)
            added = f"🔗 Ссылок добавлено: {len(urls)}. Всего: {len(attachments['links'])}"
        else:
            await message.answer(
                "⚠️ Не распознан тип вложения.\n"
                "Отправьте фото, видео, документ или ссылку (http/https)."
            )
            return
    else:
        await message.answer(
            "⚠️ Не распознан тип вложения.\n"
            "Отправьте фото, видео, документ или ссылку (http/https)."
        )
        return

    await state.update_data(attachments=attachments)

    # Обновляем сообщение-приглашение с актуальным счётчиком
    attach_msg_id = data.get("attach_msg_id")
    if attach_msg_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=attach_msg_id,
                text=_build_attach_prompt(attachments),
                reply_markup=ATTACH_KB,
            )
        except Exception:
            pass  # Сообщение уже удалено или устарело — не страшно


# ── Callback: ✅ Готово (шаг вложений) ────────────────────────────────────────

@router.callback_query(F.data == PublishBtn.ATTACH_DONE, PublishWizard.waiting_attachments)
async def cb_attach_done(callback: CallbackQuery, state: FSMContext) -> None:
    data        = await state.get_data()
    attachments = data.get("attachments") or _empty_attachments()
    cfg         = _TYPES.get(data.get("content_type", "news"), _TYPES["news"])

    await state.set_state(PublishWizard.preview)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        _build_preview(cfg["icon"], cfg["label"], data.get("title", ""), data.get("content", ""), attachments),
        reply_markup=PREVIEW_KB,
    )
    await callback.answer()


# ── Callback: ⏩ Без вложений ─────────────────────────────────────────────────

@router.callback_query(F.data == PublishBtn.ATTACH_SKIP, PublishWizard.waiting_attachments)
async def cb_attach_skip(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    cfg  = _TYPES.get(data.get("content_type", "news"), _TYPES["news"])

    await state.update_data(attachments=_empty_attachments())
    await state.set_state(PublishWizard.preview)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        _build_preview(cfg["icon"], cfg["label"], data.get("title", ""), data.get("content", "")),
        reply_markup=PREVIEW_KB,
    )
    await callback.answer()


# ── Callback: 📎 Добавить ещё (из предпросмотра) ──────────────────────────────

@router.callback_query(F.data == PublishBtn.ADD_ATTACHMENTS, PublishWizard.preview)
async def cb_add_attachments(callback: CallbackQuery, state: FSMContext) -> None:
    data        = await state.get_data()
    attachments = data.get("attachments") or _empty_attachments()

    await state.set_state(PublishWizard.waiting_attachments)
    await callback.message.edit_reply_markup(reply_markup=None)

    sent = await callback.message.answer(
        _build_attach_prompt(attachments),
        reply_markup=ATTACH_KB,
    )
    await state.update_data(attach_msg_id=sent.message_id)
    await callback.answer()


# ── Callback: 🗑 Удалить вложения ─────────────────────────────────────────────

@router.callback_query(F.data == PublishBtn.CLEAR_ATTACHMENTS, PublishWizard.preview)
async def cb_clear_attachments(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    cfg  = _TYPES.get(data.get("content_type", "news"), _TYPES["news"])

    await state.update_data(attachments=_empty_attachments())
    await callback.message.edit_text(
        _build_preview(cfg["icon"], cfg["label"], data.get("title", ""), data.get("content", "")),
        reply_markup=PREVIEW_KB,
    )
    await callback.answer("🗑 Вложения удалены")


# ── Callback: ✅ Опубликовать ─────────────────────────────────────────────────

@router.callback_query(F.data == PublishBtn.CONFIRM, PublishWizard.preview)
async def cb_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    db: Database,
    news_service: NewsService,
    user_service: UserService,
    audit_service: AuditService,
    topic_service: TopicService,
) -> None:
    data         = await state.get_data()
    content_type = data.get("content_type", "news")
    title        = data.get("title", "")
    content      = data.get("content", "")
    attachments  = data.get("attachments") or _empty_attachments()
    cfg          = _TYPES.get(content_type, _TYPES["news"])

    user        = callback.from_user
    author_name = _author_name(user)
    author_id   = user.id

    actor_nick = await user_service.get_game_nick(author_id) or author_name
    actor_role = await user_service.get_role(author_id)

    await state.clear()
    now = datetime.datetime.now(datetime.timezone.utc)

    # ── Сохранение в БД (только новости) ─────────────────────────────────
    pub_id: int | None = None
    if cfg["uses_db"]:
        item   = await news_service.create(title, content, author_id, author_name)
        pub_id = item.id
        pub_date = item.created_at
        logger.info("Пользователь %s создал %s #%d: %r", author_id, content_type, item.id, title)
    else:
        pub_date = now
        logger.info("Пользователь %s создал %s: %r", author_id, content_type, title)

    # ── Журнал аудита ─────────────────────────────────────────────────────
    await audit_service.log(
        user_id=author_id,
        game_nick=actor_nick,
        role=actor_role,
        action_type=cfg["audit"],
        description=f"{role_label(actor_role)} {actor_nick} {cfg['verb']} «{title}»",
    )

    # ── Сохранение file_id вложений в БД ─────────────────────────────────
    if _has_attachments(attachments):
        for p in attachments.get("photos", []):
            await db.attachment_save(content_type, pub_id, p["file_id"], p["file_unique_id"], "photo")
        for v in attachments.get("videos", []):
            await db.attachment_save(content_type, pub_id, v["file_id"], v["file_unique_id"], "video")
        for d in attachments.get("documents", []):
            await db.attachment_save(
                content_type, pub_id, d["file_id"], d["file_unique_id"], "document", d.get("file_name")
            )

    # ── Текст публикации ──────────────────────────────────────────────────
    links = attachments.get("links", [])
    link_block = ("\n\n🔗 " + "\n🔗 ".join(links)) if links else ""
    group_text = (
        f"{cfg['icon']} <b>{title}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{content}"
        f"{link_block}\n\n"
        f"📅 {_format_date(pub_date)}  •  ✍️ {author_name}"
    )

    # ── Публикация в Telegram-ветку ───────────────────────────────────────
    ok = await topic_service.publish_with_attachments(
        bot, cfg["topic"], group_text, attachments
    )
    topic_note = "" if ok else "\n\n⚠️ <i>Не удалось опубликовать в группу.</i>"

    # ── Подтверждение администратору ──────────────────────────────────────
    attach_note = ""
    if _has_attachments(attachments):
        parts = []
        if n := len(attachments.get("photos", [])):
            parts.append(f"🖼 {n} фото")
        if n := len(attachments.get("videos", [])):
            parts.append(f"🎥 {n} видео")
        if n := len(attachments.get("documents", [])):
            parts.append(f"📄 {n} доку{'мент' if n == 1 else 'ментов'}")
        if n := len(attachments.get("links", [])):
            parts.append(f"🔗 {n} ссылок")
        attach_note = "\n📎 Вложения: " + ", ".join(parts)

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"✅ <b>{cfg['icon']} {cfg['label']} опубликован(а)!</b>\n\n"
        f"<b>{title}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{content[:200]}{'…' if len(content) > 200 else ''}\n\n"
        f"📅 {_format_date(pub_date)}"
        f"{attach_note}"
        f"{topic_note}",
        reply_markup=MAIN_KEYBOARD,
    )
    await callback.answer()


# ── Callback: ✏️ Изменить заголовок ──────────────────────────────────────────

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


# ── Callback: 📝 Изменить текст ───────────────────────────────────────────────

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


# ── Callback: ❌ Закрыть ─────────────────────────────────────────────────────

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
        PublishWizard.waiting_attachments,
        PublishWizard.preview,
    ),
)
async def handle_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "❌ Создание отменено.\n\nВыберите раздел в главном меню.",
        reply_markup=MAIN_KEYBOARD,
    )
