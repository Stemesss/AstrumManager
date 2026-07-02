# -*- coding: utf-8 -*-
"""
Обработчик «🎨 Иконки тем».

Позволяет администратору:
  - Просматривать текущие иконки всех системных тем.
  - Автоматически назначить иконки (getForumTopicIconStickers → матч по emoji).
  - Вручную выбрать иконку для каждой темы из доступных стикеров.

Доступ: 👑 Лидер, ⭐ Дитя клана, 🛡️ Старейшина.
"""
import logging

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery

from bot.keyboards.icons import TopicIconBtn, icons_panel_kb, sticker_picker_kb
from bot.models.topic import TOPIC_LABELS
from bot.models.user import UserRole
from bot.services.topic_service import TopicService
from bot.services.user_service import UserService

router = Router()
logger = logging.getLogger(__name__)

_PANEL_TITLE = "🎨 <b>Иконки тем</b>"


async def _check_admin(cb: CallbackQuery, user_service: UserService) -> bool:
    role = await user_service.get_role(cb.from_user.id)
    if role not in UserRole.admin_roles():
        await cb.answer("🔒 Недостаточно прав.", show_alert=True)
        return False
    return True


def _panel_text(topics) -> str:
    """Текст панели иконок."""
    lines = [
        f"{_PANEL_TITLE}\n",
        "✅ — иконка установлена    ❌ — не задана\n",
        "Нажмите на тему для выбора иконки вручную.",
    ]
    return "\n".join(lines)


def _format_icons_sync_report(report: dict) -> str:
    lines = ["🔄 <b>Результаты синхронизации иконок</b>\n"]

    if report.get("fetch_error"):
        lines.append(f"❌ Не удалось получить список иконок:\n<code>{report['fetch_error'][:120]}</code>")
        return "\n".join(lines)

    if report["applied"]:
        lines.append(f"✅ Установлены автоматически ({len(report['applied'])}):")
        for k in report["applied"]:
            lines.append(f"  • {TOPIC_LABELS.get(k, k)}")

    if report["already_set"]:
        lines.append(f"🔒 Уже установлены, пропущены ({len(report['already_set'])}): "
                     + ", ".join(TOPIC_LABELS.get(k, k) for k in report["already_set"]))

    if report["no_match"]:
        lines.append(f"⚠️ Подходящий стикер не найден ({len(report['no_match'])}):")
        for k in report["no_match"]:
            lines.append(f"  • {TOPIC_LABELS.get(k, k)} — выберите иконку вручную")

    if report["no_thread"]:
        lines.append(f"🚫 Тема не настроена ({len(report['no_thread'])}):")
        for k in report["no_thread"]:
            lines.append(f"  • {TOPIC_LABELS.get(k, k)}")

    if report["errors"]:
        lines.append(f"❌ Ошибки ({len(report['errors'])}):")
        for k, err in report["errors"].items():
            lines.append(f"  • {TOPIC_LABELS.get(k, k)}: {err[:80]}")

    total = (
        len(report["applied"]) + len(report["already_set"])
        + len(report["no_match"]) + len(report["no_thread"])
        + len(report["errors"])
    )
    lines.append(f"\n<i>Всего проверено: {total} тем</i>")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Открыть панель иконок
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == TopicIconBtn.PANEL)
async def cb_icons_panel(
    callback: CallbackQuery,
    user_service: UserService,
    topic_service: TopicService,
) -> None:
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()
    topics = await topic_service.list_topics()
    await callback.message.answer(
        _panel_text(topics),
        reply_markup=icons_panel_kb(topics),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Авто-синхронизация иконок
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == TopicIconBtn.SYNC)
async def cb_icons_sync(
    callback: CallbackQuery,
    user_service: UserService,
    topic_service: TopicService,
    bot: Bot,
) -> None:
    if not await _check_admin(callback, user_service):
        return
    await callback.answer()

    await callback.message.edit_text(
        "🔄 <b>Подбор иконок...</b>\n\n"
        "<i>Получаю список доступных стикеров и сопоставляю темам.</i>"
    )

    report = await topic_service.sync_all_icons(bot)
    result_text = _format_icons_sync_report(report)

    # Показываем отчёт, затем обновлённую панель
    topics = await topic_service.list_topics()
    try:
        await callback.message.edit_text(result_text)
    except Exception:
        pass

    await callback.message.answer(
        _panel_text(topics),
        reply_markup=icons_panel_kb(topics),
    )
    logger.info(
        "Синхронизация иконок: applied=%s no_match=%s no_thread=%s errors=%s",
        report["applied"], report["no_match"], report["no_thread"],
        list(report["errors"].keys()),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Выбор иконки для конкретной темы — показываем picker стикеров
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith(TopicIconBtn.PREFIX_EDIT))
async def cb_icon_edit(
    callback: CallbackQuery,
    user_service: UserService,
    topic_service: TopicService,
    bot: Bot,
) -> None:
    if not await _check_admin(callback, user_service):
        return

    topic_key = callback.data[len(TopicIconBtn.PREFIX_EDIT):]
    if topic_key not in TOPIC_LABELS:
        await callback.answer("Неизвестная тема.", show_alert=True)
        return

    label = TOPIC_LABELS[topic_key]
    await callback.answer()

    # Загружаем стикеры (из кэша при повторных запросах)
    try:
        stickers = await topic_service.get_icon_stickers(bot)
    except Exception as exc:
        await callback.message.edit_text(
            f"❌ Не удалось получить список иконок:\n<code>{exc}</code>",
            reply_markup=icons_panel_kb(await topic_service.list_topics()),
        )
        return

    # Фильтруем — нам нужны только стикеры с custom_emoji_id
    usable = [s for s in stickers if s.custom_emoji_id]
    if not usable:
        await callback.answer("Список иконок пуст.", show_alert=True)
        return

    # Отображаем пикер в том же сообщении
    await callback.message.edit_text(
        f"🎨 <b>Выбор иконки</b>\n\n"
        f"Тема: {label}\n\n"
        f"Нажмите на эмодзи, чтобы установить его как иконку темы:",
        reply_markup=sticker_picker_kb(topic_key, usable),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Применить выбранную иконку
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith(TopicIconBtn.PREFIX_SET))
async def cb_icon_set(
    callback: CallbackQuery,
    user_service: UserService,
    topic_service: TopicService,
    bot: Bot,
) -> None:
    if not await _check_admin(callback, user_service):
        return

    # Формат: "icons:set:{topic_key}:{emoji_id}"
    rest = callback.data[len(TopicIconBtn.PREFIX_SET):]
    # topic_key не содержит ":", emoji_id — только цифры, безопасный split с maxsplit=1
    parts = rest.split(":", 1)
    if len(parts) != 2:
        await callback.answer("Некорректные данные.", show_alert=True)
        return

    topic_key, emoji_id = parts
    if topic_key not in TOPIC_LABELS:
        await callback.answer("Неизвестная тема.", show_alert=True)
        return

    label = TOPIC_LABELS[topic_key]
    await callback.answer("⏳ Применяю иконку...")

    ok = await topic_service.apply_topic_icon(bot, topic_key, emoji_id)

    topics = await topic_service.list_topics()
    if ok:
        status = f"✅ Иконка для «{label}» установлена."
    else:
        status = f"⚠️ Не удалось применить иконку для «{label}».\n<i>Проверьте, что у бота есть права can_manage_topics.</i>"

    try:
        await callback.message.edit_text(status)
    except Exception:
        pass

    # Возвращаемся к обновлённой панели иконок
    await callback.message.answer(
        _panel_text(topics),
        reply_markup=icons_panel_kb(topics),
    )
    logger.info(
        "Администратор %s установил иконку '%s' для темы '%s': ok=%s",
        callback.from_user.id, emoji_id, topic_key, ok,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Назад — из пикера обратно к панели иконок (редактируем то же сообщение)
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == TopicIconBtn.BACK)
async def cb_icons_back(
    callback: CallbackQuery,
    topic_service: TopicService,
) -> None:
    await callback.answer()
    topics = await topic_service.list_topics()
    await callback.message.edit_text(
        _panel_text(topics),
        reply_markup=icons_panel_kb(topics),
    )
