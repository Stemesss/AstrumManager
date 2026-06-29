# -*- coding: utf-8 -*-
"""
Обработчик раздела «📰 Новости».

Права доступа:
  👑 Лидер, ⭐ Дитя клана, 🛡️ Старейшина → просмотр + управление
  👤 Участник → только просмотр
"""
import logging

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.main_menu import BTN, MAIN_KEYBOARD
from bot.keyboards.news import (
    news_delete_confirm_kb,
    news_edit_kb,
    news_list_kb,
    news_view_kb,
)
from bot.models.audit import AuditAction
from bot.models.user import UserRole
from bot.services.audit_service import AuditService
from bot.services.news_service import NewsService
from bot.services.user_service import UserService
from bot.states.news import NewsEdit
from bot.states.publish import PublishWizard
from bot.utils.roles import role_label

router = Router()
logger = logging.getLogger(__name__)

# Роли, которым разрешено управлять новостями
NEWS_MANAGER_ROLES = {UserRole.LEADER, UserRole.CLAN_CHILD, UserRole.ELDER}

_MAX_TITLE_LEN = 100
_MAX_CONTENT_LEN = 4000


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────────────────────────────────────

def _format_date(dt_str: str) -> str:
    """Преобразует 'YYYY-MM-DD HH:MM:SS' в '29 июня 2026'."""
    months = {
        1: "января", 2: "февраля", 3: "марта", 4: "апреля",
        5: "мая", 6: "июня", 7: "июля", 8: "августа",
        9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
    }
    try:
        parts = dt_str[:10].split("-")
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
        return f"{d} {months[m]} {y}"
    except Exception:
        return dt_str


def _news_card(item) -> str:
    """Форматирует карточку новости без разделителей."""
    pin_badge = "📌 " if item.pinned else ""
    return (
        f"{pin_badge}<b>{item.title}</b>\n\n"
        f"{item.content}\n\n"
        f"📅 {_format_date(item.created_at)}  •  ✍️ {item.author_name}"
    )


async def _show_news_list(
    target: Message | CallbackQuery,
    news_service: NewsService,
    user_service: UserService,
    edit: bool = False,
) -> None:
    """Отображает список новостей с клавиатурой."""
    user_id = target.from_user.id if target.from_user else 0
    role = await user_service.get_role(user_id)
    is_manager = role in NEWS_MANAGER_ROLES
    items = await news_service.get_list()

    if not items:
        text = "📰 <b>Новости клана Astrum</b>\n\nНовостей пока нет."
        kb = news_list_kb([], is_manager)
    else:
        pinned = [i for i in items if i.pinned]
        regular = [i for i in items if not i.pinned]
        count_line = f"Всего: {len(items)}"
        if pinned:
            count_line += f"  •  📌 закреплено: {len(pinned)}"
        text = (
            "📰 <b>Новости клана Astrum</b>\n\n"
            f"{count_line}\n\n"
            "Выберите новость:"
        )
        kb = news_list_kb(pinned + regular, is_manager)

    msg = target if isinstance(target, Message) else target.message
    if edit and isinstance(target, CallbackQuery):
        await msg.edit_text(text, reply_markup=kb)
    else:
        await msg.answer(text, reply_markup=kb)


# ─────────────────────────────────────────────────────────────────────────────
# Показ списка новостей (кнопка меню)
# ─────────────────────────────────────────────────────────────────────────────

@router.message(F.text == BTN.NEWS, StateFilter(None))
async def handle_news_menu(
    message: Message,
    news_service: NewsService,
    user_service: UserService,
) -> None:
    """Открывает раздел новостей."""
    await _show_news_list(message, news_service, user_service)


@router.callback_query(F.data == "news:list")
async def cb_news_list(
    callback: CallbackQuery,
    news_service: NewsService,
    user_service: UserService,
    state: FSMContext,
) -> None:
    """Возвращает к списку новостей из просмотра или управления."""
    await state.clear()
    await callback.answer()
    await _show_news_list(callback, news_service, user_service, edit=True)


# ─────────────────────────────────────────────────────────────────────────────
# Просмотр одной новости
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("news:view:"))
async def cb_news_view(
    callback: CallbackQuery,
    news_service: NewsService,
    user_service: UserService,
) -> None:
    """Показывает полный текст новости."""
    news_id = int(callback.data.split(":")[2])
    item = await news_service.get_by_id(news_id)
    if not item:
        await callback.answer("Новость не найдена.", show_alert=True)
        return

    role = await user_service.get_role(callback.from_user.id)
    is_manager = role in NEWS_MANAGER_ROLES

    await callback.answer()
    await callback.message.edit_text(
        _news_card(item),
        reply_markup=news_view_kb(item.id, item.pinned, is_manager),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Создание новости (FSM)
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "news:create")
async def cb_news_create(
    callback: CallbackQuery,
    user_service: UserService,
    state: FSMContext,
) -> None:
    """Начинает создание новости."""
    role = await user_service.get_role(callback.from_user.id)
    if role not in NEWS_MANAGER_ROLES:
        await callback.answer("🔒 Недостаточно прав.", show_alert=True)
        return

    await state.set_state(PublishWizard.waiting_title)
    await state.update_data(content_type="news")
    await callback.answer()
    await callback.message.answer(
        "📰 <b>Создание новости</b>\n\n"
        f"Введите <b>заголовок</b> новости (до {_MAX_TITLE_LEN} символов):\n\n"
        "<i>Отправьте /cancel для отмены</i>",
        reply_markup=MAIN_KEYBOARD,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Редактирование новости (FSM)
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("news:edit:"))
async def cb_news_edit(
    callback: CallbackQuery,
    user_service: UserService,
) -> None:
    """Показывает выбор поля для редактирования."""
    role = await user_service.get_role(callback.from_user.id)
    if role not in NEWS_MANAGER_ROLES:
        await callback.answer("🔒 Недостаточно прав.", show_alert=True)
        return
    news_id = int(callback.data.split(":")[2])
    await callback.answer()
    await callback.message.edit_text(
        "✏️ <b>Редактирование новости</b>\n\nЧто вы хотите изменить?",
        reply_markup=news_edit_kb(news_id),
    )


@router.callback_query(F.data.startswith("news:edit_title:"))
async def cb_edit_title(
    callback: CallbackQuery,
    user_service: UserService,
    state: FSMContext,
) -> None:
    """Начинает редактирование заголовка."""
    role = await user_service.get_role(callback.from_user.id)
    if role not in NEWS_MANAGER_ROLES:
        await callback.answer("🔒 Недостаточно прав.", show_alert=True)
        return
    news_id = int(callback.data.split(":")[2])
    await state.set_state(NewsEdit.waiting_title)
    await state.update_data(news_id=news_id)
    await callback.answer()
    await callback.message.answer(
        f"✏️ Введите <b>новый заголовок</b> (до {_MAX_TITLE_LEN} символов):\n\n"
        "<i>Отправьте /cancel для отмены</i>",
    )


@router.callback_query(F.data.startswith("news:edit_content:"))
async def cb_edit_content(
    callback: CallbackQuery,
    user_service: UserService,
    state: FSMContext,
) -> None:
    """Начинает редактирование текста."""
    role = await user_service.get_role(callback.from_user.id)
    if role not in NEWS_MANAGER_ROLES:
        await callback.answer("🔒 Недостаточно прав.", show_alert=True)
        return
    news_id = int(callback.data.split(":")[2])
    await state.set_state(NewsEdit.waiting_content)
    await state.update_data(news_id=news_id)
    await callback.answer()
    await callback.message.answer(
        f"📝 Введите <b>новый текст</b> новости (до {_MAX_CONTENT_LEN} символов):\n\n"
        "<i>Отправьте /cancel для отмены</i>",
    )


@router.message(NewsEdit.waiting_title)
async def fsm_edit_title(
    message: Message,
    state: FSMContext,
    news_service: NewsService,
    user_service: UserService,
    audit_service: AuditService,
) -> None:
    """Сохраняет новый заголовок."""
    if not message.text or message.text.startswith("/"):
        await message.answer("⚠️ Пожалуйста, введите новый заголовок текстом.")
        return
    title = message.text.strip()
    if len(title) > _MAX_TITLE_LEN:
        await message.answer(
            f"⚠️ Заголовок слишком длинный (максимум {_MAX_TITLE_LEN} символов)."
        )
        return

    data = await state.get_data()
    news_id = data["news_id"]
    await news_service.update_title(news_id, title)
    await state.clear()

    logger.info(
        "Пользователь %s обновил заголовок новости #%d", message.from_user.id, news_id
    )

    actor_nick = await user_service.get_game_nick(message.from_user.id) or "?"
    actor_role = await user_service.get_role(message.from_user.id)
    await audit_service.log(
        user_id=message.from_user.id,
        game_nick=actor_nick,
        role=actor_role,
        action_type=AuditAction.NEWS_EDIT,
        description=(
            f"{role_label(actor_role)} {actor_nick} "
            f"изменил заголовок новости #{news_id}: «{title}»"
        ),
    )

    await message.answer(
        f"✅ <b>Заголовок обновлён!</b>\n\nНовый заголовок: <b>{title}</b>"
    )


@router.message(NewsEdit.waiting_content)
async def fsm_edit_content(
    message: Message,
    state: FSMContext,
    news_service: NewsService,
    user_service: UserService,
    audit_service: AuditService,
) -> None:
    """Сохраняет новый текст новости."""
    if not message.text or message.text.startswith("/"):
        await message.answer("⚠️ Пожалуйста, введите новый текст новости.")
        return
    content = message.text.strip()
    if len(content) > _MAX_CONTENT_LEN:
        await message.answer(
            f"⚠️ Текст слишком длинный (максимум {_MAX_CONTENT_LEN} символов)."
        )
        return

    data = await state.get_data()
    news_id = data["news_id"]
    await news_service.update_content(news_id, content)
    await state.clear()

    logger.info(
        "Пользователь %s обновил текст новости #%d", message.from_user.id, news_id
    )

    actor_nick = await user_service.get_game_nick(message.from_user.id) or "?"
    actor_role = await user_service.get_role(message.from_user.id)
    await audit_service.log(
        user_id=message.from_user.id,
        game_nick=actor_nick,
        role=actor_role,
        action_type=AuditAction.NEWS_EDIT,
        description=(
            f"{role_label(actor_role)} {actor_nick} "
            f"изменил текст новости #{news_id}"
        ),
    )

    await message.answer("✅ <b>Текст новости обновлён!</b>")


# ─────────────────────────────────────────────────────────────────────────────
# Удаление новости
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("news:del_confirm:"))
async def cb_delete_confirm(
    callback: CallbackQuery,
    user_service: UserService,
) -> None:
    """Запрашивает подтверждение удаления."""
    role = await user_service.get_role(callback.from_user.id)
    if role not in NEWS_MANAGER_ROLES:
        await callback.answer("🔒 Недостаточно прав.", show_alert=True)
        return
    news_id = int(callback.data.split(":")[2])
    await callback.answer()
    await callback.message.edit_text(
        "🗑 <b>Удаление новости</b>\n\nВы уверены? Это действие нельзя отменить.",
        reply_markup=news_delete_confirm_kb(news_id),
    )


@router.callback_query(F.data.startswith("news:delete:"))
async def cb_delete(
    callback: CallbackQuery,
    user_service: UserService,
    news_service: NewsService,
    audit_service: AuditService,
) -> None:
    """Удаляет новость после подтверждения."""
    role = await user_service.get_role(callback.from_user.id)
    if role not in NEWS_MANAGER_ROLES:
        await callback.answer("🔒 Недостаточно прав.", show_alert=True)
        return
    news_id = int(callback.data.split(":")[2])

    item = await news_service.get_by_id(news_id)
    title_for_log = item.title if item else f"#{news_id}"

    await news_service.delete(news_id)
    logger.info("Пользователь %s удалил новость #%d", callback.from_user.id, news_id)

    actor_nick = await user_service.get_game_nick(callback.from_user.id) or "?"
    await audit_service.log(
        user_id=callback.from_user.id,
        game_nick=actor_nick,
        role=role,
        action_type=AuditAction.NEWS_DELETE,
        description=f"{role_label(role)} {actor_nick} удалил новость «{title_for_log}»",
    )

    await callback.answer("🗑 Новость удалена.")
    await _show_news_list(callback, news_service, user_service, edit=True)


# ─────────────────────────────────────────────────────────────────────────────
# Закрепление новости
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("news:pin:"))
async def cb_pin(
    callback: CallbackQuery,
    user_service: UserService,
    news_service: NewsService,
    audit_service: AuditService,
) -> None:
    """Переключает закрепление новости."""
    role = await user_service.get_role(callback.from_user.id)
    if role not in NEWS_MANAGER_ROLES:
        await callback.answer("🔒 Недостаточно прав.", show_alert=True)
        return
    news_id = int(callback.data.split(":")[2])
    new_state = await news_service.toggle_pin(news_id)
    action_word = "закреплена" if new_state else "откреплена"
    logger.info(
        "Пользователь %s %s новость #%d", callback.from_user.id, action_word, news_id
    )

    item = await news_service.get_by_id(news_id)
    title_for_log = item.title if item else f"#{news_id}"
    actor_nick = await user_service.get_game_nick(callback.from_user.id) or "?"
    action_type = AuditAction.NEWS_PIN if new_state else AuditAction.NEWS_UNPIN
    action_ru = "закрепил" if new_state else "открепил"
    await audit_service.log(
        user_id=callback.from_user.id,
        game_nick=actor_nick,
        role=role,
        action_type=action_type,
        description=(
            f"{role_label(role)} {actor_nick} {action_ru} новость «{title_for_log}»"
        ),
    )

    await callback.answer(f"{'📌' if new_state else '📍'} Новость {action_word}.")

    if not item:
        await _show_news_list(callback, news_service, user_service, edit=True)
        return
    is_manager = role in NEWS_MANAGER_ROLES
    await callback.message.edit_text(
        _news_card(item),
        reply_markup=news_view_kb(item.id, item.pinned, is_manager),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Отмена FSM через /cancel
# ─────────────────────────────────────────────────────────────────────────────

@router.message(
    Command("cancel"),
    StateFilter(NewsEdit.waiting_title, NewsEdit.waiting_content),
)
async def handle_cancel(message: Message, state: FSMContext) -> None:
    """Отменяет текущий процесс редактирования новости."""
    await state.clear()
    await message.answer(
        "❌ Действие отменено.\n\nВыберите раздел в главном меню.",
        reply_markup=MAIN_KEYBOARD,
    )
