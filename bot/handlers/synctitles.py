# -*- coding: utf-8 -*-
"""
Команда /synctitles — массовая синхронизация Telegram Admin Title.

Доступ: только администраторы (Лидер, Дитя клана, Старейшина).

Алгоритм:
  1. Получить всех участников с game_nick.
  2. Для каждого — getChatMember: пропустить creator и left/kicked.
  3. Выполнить sync_admin_title с RetryAfter / flood-control.
  4. Вывести подробный отчёт.
  5. Записать в журнал AuditAction.SYNC_TITLES.
"""
import asyncio
import logging

from aiogram import Bot, Router
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.filters import Command
from aiogram.types import Message

from bot.models.audit import AuditAction
from bot.models.user import UserRole
from bot.services.audit_service import AuditService
from bot.services.user_service import UserService
from bot.utils.roles import role_label
from bot.utils.sync_title import build_admin_title, sync_admin_title

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("synctitles"))
async def cmd_sync_titles(
    message: Message,
    user_service: UserService,
    audit_service: AuditService,
    bot: Bot,
    group_chat_id: int,
) -> None:
    """Массовая синхронизация Telegram Admin Title для всех участников клана."""
    if not message.from_user:
        return

    actor_id = message.from_user.id
    actor_role = await user_service.get_role(actor_id)

    if actor_role not in UserRole.admin_roles():
        await message.answer(
            "🔒 <b>Доступ запрещён.</b>\n"
            "Команда доступна только администраторам клана."
        )
        return

    all_users = await user_service.get_all_users()
    users_with_nick = [u for u in all_users if u.game_nick]

    if not users_with_nick:
        await message.answer("👥 Нет участников с игровым ником для синхронизации.")
        return

    progress_msg = await message.answer(
        f"⏳ <b>Синхронизация Telegram-титулов...</b>\n\n"
        f"Обрабатываю {len(users_with_nick)} участников, подождите..."
    )

    synced: list[str]            = []
    skipped_creator: list[str]   = []
    skipped_no_member: list[str] = []
    errors: list[str]            = []

    for u in users_with_nick:
        nick_label = u.game_nick or str(u.telegram_id)

        # ── Проверяем статус участника в группе ─────────────────────────
        try:
            member = await bot.get_chat_member(group_chat_id, u.telegram_id)
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)
            try:
                member = await bot.get_chat_member(group_chat_id, u.telegram_id)
            except Exception as exc:
                errors.append(f"{nick_label}: {exc}")
                continue
        except TelegramBadRequest as e:
            err = str(e).lower()
            if any(k in err for k in ("user not found", "participant", "chat not found", "user_not_participant")):
                skipped_no_member.append(nick_label)
            else:
                errors.append(f"{nick_label}: {e}")
            continue
        except Exception as exc:
            errors.append(f"{nick_label}: {exc}")
            continue

        # ── Пропускаем владельца группы ─────────────────────────────────
        if member.status == "creator":
            skipped_creator.append(nick_label)
            continue

        # ── Пропускаем тех, кто не в группе ─────────────────────────────
        if member.status in ("left", "kicked"):
            skipped_no_member.append(nick_label)
            continue

        # ── Синхронизируем Telegram-титул ───────────────────────────────
        try:
            err_msg = await sync_admin_title(
                bot, group_chat_id, u.telegram_id, u.role, u.game_nick
            )
            if err_msg:
                errors.append(f"{nick_label}: (без прав API)")
            else:
                synced.append(f"{build_admin_title(u.role, u.game_nick)}  [{nick_label}]")
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)
            try:
                err_msg = await sync_admin_title(
                    bot, group_chat_id, u.telegram_id, u.role, u.game_nick
                )
                if err_msg:
                    errors.append(f"{nick_label}: (без прав API)")
                else:
                    synced.append(f"{build_admin_title(u.role, u.game_nick)}  [{nick_label}]")
            except Exception as exc:
                errors.append(f"{nick_label}: {exc}")
        except Exception as exc:
            errors.append(f"{nick_label}: {exc}")

        # Пауза между запросами — flood-control
        await asyncio.sleep(0.15)

    # ── Запись в аудит ───────────────────────────────────────────────────
    actor_nick = await user_service.get_game_nick(actor_id) or str(actor_id)
    await audit_service.log(
        user_id=actor_id,
        game_nick=actor_nick,
        role=actor_role,
        action_type=AuditAction.SYNC_TITLES,
        description=(
            f"{role_label(actor_role)} {actor_nick} синхронизировал Telegram-титулы: "
            f"обновлено {len(synced)}, "
            f"пропущено (владелец) {len(skipped_creator)}, "
            f"пропущено (не в группе) {len(skipped_no_member)}, "
            f"ошибок {len(errors)}"
        ),
    )
    logger.info(
        "/synctitles: actor=%s synced=%d skipped_creator=%d skipped_absent=%d errors=%d",
        actor_id, len(synced), len(skipped_creator), len(skipped_no_member), len(errors),
    )

    # ── Итоговый отчёт ───────────────────────────────────────────────────
    lines = [
        "✅ <b>Синхронизация Telegram-титулов завершена</b>",
        "",
        "📊 <b>Итог:</b>",
        f"  ✅ Синхронизировано: <b>{len(synced)}</b>",
        f"  👑 Пропущено (владелец группы): <b>{len(skipped_creator)}</b>",
        f"  🚪 Пропущено (не в группе): <b>{len(skipped_no_member)}</b>",
        f"  ❌ Ошибок: <b>{len(errors)}</b>",
    ]

    if synced:
        lines += ["", "✅ <b>Синхронизировано:</b>"]
        lines += [f"  • {t}" for t in synced]

    if skipped_creator:
        lines += ["", "👑 <b>Пропущено (владелец группы):</b>"]
        lines += [f"  • {n}" for n in skipped_creator]

    if skipped_no_member:
        lines += ["", "🚪 <b>Не в группе (пропущены):</b>"]
        lines += [f"  • {n}" for n in skipped_no_member]

    if errors:
        lines += ["", "❌ <b>Ошибки:</b>"]
        lines += [f"  • {e}" for e in errors]

    report = "\n".join(lines)
    # Telegram ограничивает сообщение 4096 символами
    if len(report) > 4000:
        report = report[:4000] + "\n…\n<i>(отчёт обрезан)</i>"

    try:
        await progress_msg.edit_text(report)
    except Exception:
        await message.answer(report)
