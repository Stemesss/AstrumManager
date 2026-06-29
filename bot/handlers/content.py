# -*- coding: utf-8 -*-
"""
Единый обработчик разделов «📅 События», «📚 Гайды», «📸 Скриншоты».

Callback-схема: cnt:{action}:{type}:{id_or_page}
  cnt:list:{type}:{page}   — пагинированный список
  cnt:view:{type}:{id}     — просмотр записи
  cnt:create:{type}        — создание (запускает PublishWizard)
  cnt:edit:{type}:{id}     — выбор поля для редактирования
  cnt:etitle:{type}:{id}   — изменить заголовок (FSM)
  cnt:econt:{type}:{id}    — изменить текст (FSM)
  cnt:dconf:{type}:{id}    — подтверждение удаления
  cnt:del:{type}:{id}      — удалить
  cnt:pin:{type}:{id}      — переключить закрепление
  cnt:noop                 — индикатор страниц (без действия)
"""
import logging

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.nav import CANCEL_KB
from bot.keyboards.content import (
    PAGE_SIZE,
    content_delete_confirm_kb,
    content_edit_kb,
    content_list_kb,
    content_view_kb,
)
from bot.keyboards.main_menu import BTN, MAIN_KEYBOARD
from bot.models.audit import AuditAction
from bot.models.news import NewsItem
from bot.models.user import UserRole
from bot.services.audit_service import AuditService
from bot.services.news_service import NewsService
from bot.services.user_service import UserService
from bot.states.content import ContentEdit
from bot.states.publish import PublishWizard
from bot.utils.roles import role_label

router = Router()
logger = logging.getLogger(__name__)

_MANAGER_ROLES = {UserRole.LEADER, UserRole.CLAN_CHILD, UserRole.ELDER}

_MAX_TITLE   = 100
_MAX_CONTENT = 4000

# ── Конфиг типов контента ─────────────────────────────────────────────────────

_TYPES: dict[str, dict] = {
    "events": {
        "icon":      "📅",
        "label":     "Событие",
        "label_pl":  "События",
        "label_gen": "события",
        "btn":       BTN.EVENTS,
        "audit_edit": AuditAction.EVENT_EDIT,
        "audit_del":  AuditAction.EVENT_DELETE,
    },
    "guides": {
        "icon":      "📚",
        "label":     "Гайд",
        "label_pl":  "Гайды",
        "label_gen": "гайда",
        "btn":       BTN.GUIDES,
        "audit_edit": AuditAction.GUIDE_EDIT,
        "audit_del":  AuditAction.GUIDE_DELETE,
    },
    "screenshots": {
        "icon":      "📸",
        "label":     "Скриншот",
        "label_pl":  "Скриншоты",
        "label_gen": "скриншота",
        "btn":       BTN.SCREENSHOTS,
        "audit_edit": AuditAction.SCREENSHOT_UPLOAD,
        "audit_del":  AuditAction.SCREENSHOT_DELETE,
    },
    "memes": {
        "icon":      "😂",
        "label":     "Мем",
        "label_pl":  "Мемы",
        "label_gen": "мема",
        "btn":       BTN.MEMES,
        "audit_edit": AuditAction.MEME_EDIT,
        "audit_del":  AuditAction.MEME_DELETE,
    },
}


# ── Утилиты ───────────────────────────────────────────────────────────────────

def _fmt_date(dt_str: str) -> str:
    months = {
        1: "января", 2: "февраля", 3: "марта", 4: "апреля",
        5: "мая", 6: "июня", 7: "июля", 8: "августа",
        9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
    }
    try:
        y, m, d = int(dt_str[:4]), int(dt_str[5:7]), int(dt_str[8:10])
        return f"{d} {months[m]} {y}"
    except Exception:
        return dt_str


def _item_card(item: NewsItem, cfg: dict) -> str:
    pin = "📌 " if item.pinned else ""
    return (
        f"{pin}{cfg['icon']} <b>{item.title}</b>\n\n"
        f"{item.content}\n\n"
        f"📅 {_fmt_date(item.created_at)}  •  ✍️ {item.author_name}"
    )


def _list_text(cfg: dict, total: int) -> str:
    if total == 0:
        return f"{cfg['icon']} <b>{cfg['label_pl']}</b>\n\nЗаписей пока нет."
    return (
        f"{cfg['icon']} <b>{cfg['label_pl']}</b>\n\n"
        f"Всего: {total}\n\n"
        "Выберите запись:"
    )


async def _show_list(
    target: Message | CallbackQuery,
    news_service: NewsService,
    user_service: UserService,
    content_type: str,
    page: int = 0,
    edit: bool = False,
) -> None:
    cfg = _TYPES[content_type]
    user_id = target.from_user.id if target.from_user else 0
    role = await user_service.get_role(user_id)
    is_manager = role in _MANAGER_ROLES

    items = await news_service.get_list_by_type(content_type)
    total = len(items)
    page_items = items[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]

    text = _list_text(cfg, total)
    kb = content_list_kb(page_items, page, total, content_type, is_manager)

    msg = target if isinstance(target, Message) else target.message
    if edit and isinstance(target, CallbackQuery):
        try:
            await msg.edit_text(text, reply_markup=kb)
        except Exception:
            await msg.answer(text, reply_markup=kb)
    else:
        await msg.answer(text, reply_markup=kb)


# ── Кнопки главного меню → список ─────────────────────────────────────────────

@router.message(F.text == BTN.EVENTS, StateFilter(None))
async def handle_events(message: Message, news_service: NewsService, user_service: UserService) -> None:
    await _show_list(message, news_service, user_service, "events")


@router.message(F.text == BTN.GUIDES, StateFilter(None))
async def handle_guides(message: Message, news_service: NewsService, user_service: UserService) -> None:
    await _show_list(message, news_service, user_service, "guides")


@router.message(F.text == BTN.SCREENSHOTS, StateFilter(None))
async def handle_screenshots(message: Message, news_service: NewsService, user_service: UserService) -> None:
    await _show_list(message, news_service, user_service, "screenshots")


@router.message(F.text == BTN.MEMES, StateFilter(None))
async def handle_memes(message: Message, news_service: NewsService, user_service: UserService) -> None:
    await _show_list(message, news_service, user_service, "memes")


# ── Список (пагинация) ────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cnt:list:"))
async def cb_list(
    callback: CallbackQuery, news_service: NewsService, user_service: UserService, state: FSMContext
) -> None:
    await state.clear()
    parts = callback.data.split(":")
    content_type, page = parts[2], int(parts[3])
    if content_type not in _TYPES:
        await callback.answer()
        return
    await callback.answer()
    await _show_list(callback, news_service, user_service, content_type, page, edit=True)


@router.callback_query(F.data == "cnt:noop")
async def cb_noop(callback: CallbackQuery) -> None:
    await callback.answer()


# ── Просмотр записи ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cnt:view:"))
async def cb_view(
    callback: CallbackQuery, news_service: NewsService, user_service: UserService
) -> None:
    parts = callback.data.split(":")
    content_type, item_id = parts[2], int(parts[3])
    if content_type not in _TYPES:
        await callback.answer()
        return

    item = await news_service.get_by_id(item_id)
    if not item:
        await callback.answer("Запись не найдена.", show_alert=True)
        return

    cfg = _TYPES[content_type]
    role = await user_service.get_role(callback.from_user.id)
    is_manager = role in _MANAGER_ROLES

    await callback.answer()
    await callback.message.edit_text(
        _item_card(item, cfg),
        reply_markup=content_view_kb(content_type, item_id, item.pinned, is_manager),
    )


# ── Создание (запуск PublishWizard) ───────────────────────────────────────────

@router.callback_query(F.data.startswith("cnt:create:"))
async def cb_create(
    callback: CallbackQuery, user_service: UserService, state: FSMContext
) -> None:
    role = await user_service.get_role(callback.from_user.id)
    if role not in _MANAGER_ROLES:
        await callback.answer("🔒 Недостаточно прав.", show_alert=True)
        return

    content_type = callback.data.split(":")[2]
    if content_type not in _TYPES:
        await callback.answer()
        return

    cfg = _TYPES[content_type]
    await state.set_state(PublishWizard.waiting_title)
    await state.update_data(content_type=content_type)
    await callback.answer()
    await callback.message.answer(
        f"{cfg['icon']} <b>Создание — {cfg['label']}</b>\n\n"
        f"Введите <b>заголовок</b> {cfg['label_gen']} (до {_MAX_TITLE} символов):",
        reply_markup=CANCEL_KB,
    )


# ── Редактирование — выбор поля ───────────────────────────────────────────────

@router.callback_query(F.data.startswith("cnt:edit:"))
async def cb_edit(callback: CallbackQuery, user_service: UserService) -> None:
    role = await user_service.get_role(callback.from_user.id)
    if role not in _MANAGER_ROLES:
        await callback.answer("🔒 Недостаточно прав.", show_alert=True)
        return
    parts = callback.data.split(":")
    content_type, item_id = parts[2], int(parts[3])
    cfg = _TYPES.get(content_type, {})
    label = cfg.get("label", "записи")
    await callback.answer()
    await callback.message.edit_text(
        f"✏️ <b>Редактирование — {label}</b>\n\nЧто вы хотите изменить?",
        reply_markup=content_edit_kb(content_type, item_id),
    )


# ── Редактирование заголовка (FSM) ────────────────────────────────────────────

@router.callback_query(F.data.startswith("cnt:etitle:"))
async def cb_edit_title(callback: CallbackQuery, user_service: UserService, state: FSMContext) -> None:
    role = await user_service.get_role(callback.from_user.id)
    if role not in _MANAGER_ROLES:
        await callback.answer("🔒 Недостаточно прав.", show_alert=True)
        return
    parts = callback.data.split(":")
    content_type, item_id = parts[2], int(parts[3])
    await state.set_state(ContentEdit.waiting_title)
    await state.update_data(content_id=item_id, content_type=content_type)
    await callback.answer()
    await callback.message.answer(
        f"✏️ Введите <b>новый заголовок</b> (до {_MAX_TITLE} символов):",
        reply_markup=CANCEL_KB,
    )


@router.message(ContentEdit.waiting_title)
async def fsm_edit_title(
    message: Message,
    state: FSMContext,
    news_service: NewsService,
    user_service: UserService,
    audit_service: AuditService,
) -> None:
    if not message.text or message.text.startswith("/"):
        await message.answer("⚠️ Введите новый заголовок текстом.")
        return
    title = message.text.strip()
    if len(title) > _MAX_TITLE:
        await message.answer(f"⚠️ Заголовок слишком длинный (максимум {_MAX_TITLE} символов).")
        return

    data = await state.get_data()
    item_id = data["content_id"]
    content_type = data["content_type"]
    cfg = _TYPES.get(content_type, {})

    await news_service.update_title(item_id, title)
    await state.clear()

    actor_nick = await user_service.get_game_nick(message.from_user.id) or "?"
    actor_role = await user_service.get_role(message.from_user.id)
    await audit_service.log(
        user_id=message.from_user.id,
        game_nick=actor_nick,
        role=actor_role,
        action_type=cfg.get("audit_edit", AuditAction.NEWS_EDIT),
        description=f"{role_label(actor_role)} {actor_nick} изменил заголовок {cfg.get('label_gen','записи')} #{item_id}: «{title}»",
    )
    await message.answer(f"✅ <b>Заголовок обновлён!</b>\n\nНовый заголовок: <b>{title}</b>")


# ── Редактирование текста (FSM) ───────────────────────────────────────────────

@router.callback_query(F.data.startswith("cnt:econt:"))
async def cb_edit_content(callback: CallbackQuery, user_service: UserService, state: FSMContext) -> None:
    role = await user_service.get_role(callback.from_user.id)
    if role not in _MANAGER_ROLES:
        await callback.answer("🔒 Недостаточно прав.", show_alert=True)
        return
    parts = callback.data.split(":")
    content_type, item_id = parts[2], int(parts[3])
    await state.set_state(ContentEdit.waiting_content)
    await state.update_data(content_id=item_id, content_type=content_type)
    await callback.answer()
    await callback.message.answer(
        f"📝 Введите <b>новый текст</b> (до {_MAX_CONTENT} символов):",
        reply_markup=CANCEL_KB,
    )


@router.message(ContentEdit.waiting_content)
async def fsm_edit_content(
    message: Message,
    state: FSMContext,
    news_service: NewsService,
    user_service: UserService,
    audit_service: AuditService,
) -> None:
    if not message.text or message.text.startswith("/"):
        await message.answer("⚠️ Введите новый текст сообщением.")
        return
    content = message.text.strip()
    if len(content) > _MAX_CONTENT:
        await message.answer(f"⚠️ Текст слишком длинный (максимум {_MAX_CONTENT} символов).")
        return

    data = await state.get_data()
    item_id = data["content_id"]
    content_type = data["content_type"]
    cfg = _TYPES.get(content_type, {})

    await news_service.update_content(item_id, content)
    await state.clear()

    actor_nick = await user_service.get_game_nick(message.from_user.id) or "?"
    actor_role = await user_service.get_role(message.from_user.id)
    await audit_service.log(
        user_id=message.from_user.id,
        game_nick=actor_nick,
        role=actor_role,
        action_type=cfg.get("audit_edit", AuditAction.NEWS_EDIT),
        description=f"{role_label(actor_role)} {actor_nick} изменил текст {cfg.get('label_gen','записи')} #{item_id}",
    )
    await message.answer(f"✅ <b>Текст обновлён!</b>")


# ── Удаление ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cnt:dconf:"))
async def cb_delete_confirm(callback: CallbackQuery, user_service: UserService) -> None:
    role = await user_service.get_role(callback.from_user.id)
    if role not in _MANAGER_ROLES:
        await callback.answer("🔒 Недостаточно прав.", show_alert=True)
        return
    parts = callback.data.split(":")
    content_type, item_id = parts[2], int(parts[3])
    cfg = _TYPES.get(content_type, {})
    await callback.answer()
    await callback.message.edit_text(
        f"🗑 <b>Удаление {cfg.get('label_gen', 'записи')}</b>\n\nВы уверены? Это действие нельзя отменить.",
        reply_markup=content_delete_confirm_kb(content_type, item_id),
    )


@router.callback_query(F.data.startswith("cnt:del:"))
async def cb_delete(
    callback: CallbackQuery,
    news_service: NewsService,
    user_service: UserService,
    audit_service: AuditService,
) -> None:
    role = await user_service.get_role(callback.from_user.id)
    if role not in _MANAGER_ROLES:
        await callback.answer("🔒 Недостаточно прав.", show_alert=True)
        return
    parts = callback.data.split(":")
    content_type, item_id = parts[2], int(parts[3])
    cfg = _TYPES.get(content_type, {})

    item = await news_service.get_by_id(item_id)
    title_log = item.title if item else f"#{item_id}"

    await news_service.delete(item_id)
    logger.info("Пользователь %s удалил %s #%d", callback.from_user.id, content_type, item_id)

    actor_nick = await user_service.get_game_nick(callback.from_user.id) or "?"
    await audit_service.log(
        user_id=callback.from_user.id,
        game_nick=actor_nick,
        role=role,
        action_type=cfg.get("audit_del", AuditAction.NEWS_DELETE),
        description=f"{role_label(role)} {actor_nick} удалил {cfg.get('label_gen','запись')} «{title_log}»",
    )

    await callback.answer("🗑 Запись удалена.")
    await _show_list(callback, news_service, user_service, content_type, edit=True)


# ── Закрепление ───────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cnt:pin:"))
async def cb_pin(
    callback: CallbackQuery,
    news_service: NewsService,
    user_service: UserService,
    audit_service: AuditService,
) -> None:
    role = await user_service.get_role(callback.from_user.id)
    if role not in _MANAGER_ROLES:
        await callback.answer("🔒 Недостаточно прав.", show_alert=True)
        return
    parts = callback.data.split(":")
    content_type, item_id = parts[2], int(parts[3])
    cfg = _TYPES.get(content_type, {})

    new_state = await news_service.toggle_pin(item_id)
    action_word = "закреплена" if new_state else "откреплена"

    item = await news_service.get_by_id(item_id)
    title_log = item.title if item else f"#{item_id}"
    actor_nick = await user_service.get_game_nick(callback.from_user.id) or "?"
    action_ru = "закрепил" if new_state else "открепил"
    await audit_service.log(
        user_id=callback.from_user.id,
        game_nick=actor_nick,
        role=role,
        action_type=cfg.get("audit_edit", AuditAction.NEWS_EDIT),
        description=f"{role_label(role)} {actor_nick} {action_ru} {cfg.get('label_gen','запись')} «{title_log}»",
    )

    await callback.answer(f"{'📌' if new_state else '📍'} {action_word.capitalize()}.")
    if not item:
        await _show_list(callback, news_service, user_service, content_type, edit=True)
        return

    is_manager = role in _MANAGER_ROLES
    await callback.message.edit_text(
        _item_card(item, cfg),
        reply_markup=content_view_kb(content_type, item_id, item.pinned, is_manager),
    )


