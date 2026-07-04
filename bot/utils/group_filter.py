# -*- coding: utf-8 -*-
"""Фильтрация списков по фактическому составу Telegram-группы.

Общая утилита для пользовательских разделов (статистика, участники), чтобы
не показывать людей, покинувших группу. При ошибке API запись остаётся в
списке (fail-open) — временный сбой Telegram не должен обнулять раздел.
"""
import asyncio
from typing import Callable, TypeVar

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter

T = TypeVar("T")

_ABSENT_MARKERS = ("user not found", "participant", "user_not_participant")


async def filter_present_in_group(
    bot: Bot,
    group_chat_id: int,
    items: list[T],
    get_user_id: Callable[[T], int],
) -> list[T]:
    """Возвращает только те элементы, чей telegram_id всё ещё состоит в группе."""
    result: list[T] = []
    for item in items:
        try:
            member = await bot.get_chat_member(group_chat_id, get_user_id(item))
            if member.status not in ("left", "kicked"):
                result.append(item)
        except TelegramBadRequest as e:
            err = str(e).lower()
            if any(marker in err for marker in _ABSENT_MARKERS):
                pass  # подтверждено отсутствие — не показываем
            else:
                result.append(item)  # неизвестная ошибка — включаем
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)
            result.append(item)
        except Exception:
            result.append(item)  # ошибка API — включаем (fail-open)
        await asyncio.sleep(0.05)
    return result


async def is_present_in_group(bot: Bot, group_chat_id: int, telegram_id: int) -> bool:
    """True, если пользователь всё ещё состоит в Telegram-группе (fail-open)."""
    try:
        member = await bot.get_chat_member(group_chat_id, telegram_id)
        return member.status not in ("left", "kicked")
    except TelegramBadRequest as e:
        err = str(e).lower()
        if any(marker in err for marker in _ABSENT_MARKERS):
            return False
        return True
    except Exception:
        return True


def filter_by_active_ids(
    items: list[T],
    get_user_id: Callable[[T], int],
    active_ids: set[int],
) -> list[T]:
    """Фильтрует список по готовому набору активных telegram_id (без обращений к API)."""
    return [item for item in items if get_user_id(item) in active_ids]
