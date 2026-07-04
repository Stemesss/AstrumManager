# -*- coding: utf-8 -*-
"""Сервис синхронизации участников группы через Telethon MTProto API.

Использование:
    service = TelethonSyncService()
    active_ids = await service.sync_and_get_ids(group_chat_id, db)
    # None → сервис недоступен, использовать Bot API как fallback
    # set[int] → telegram_id активных участников (кэш 30 сек)
"""
import logging
import os
import time

logger = logging.getLogger(__name__)

CACHE_TTL = 30  # секунды


class TelethonSyncService:
    """Синхронизация участников через Telethon.

    Подключается только при запросе, отключается сразу после.
    Кэширует set[telegram_id] на 30 секунд.
    При любой ошибке возвращает None → вызывающий код переходит на Bot API.
    """

    def __init__(self) -> None:
        self._cache_ids: set[int] | None = None
        self._cache_time: float = 0.0
        self._api_id: int | None = None
        self._api_hash: str | None = None
        self._session_str: str | None = None
        self._available: bool | None = None  # None = ещё не проверялось

    def _load_credentials(self) -> bool:
        """Загружает учётные данные из env. Возвращает True если все данные есть."""
        if self._available is not None:
            return self._available

        raw_id = os.getenv("TELEGRAM_API_ID", "").strip()
        api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()
        session = os.getenv("TELETHON_SESSION", "").strip()

        missing = [k for k, v in [
            ("TELEGRAM_API_ID", raw_id),
            ("TELEGRAM_API_HASH", api_hash),
            ("TELETHON_SESSION", session),
        ] if not v]

        if missing:
            logger.warning(
                "TelethonSync недоступен: отсутствуют секреты %s — "
                "используется Bot API fallback",
                missing,
            )
            self._available = False
            return False

        try:
            self._api_id = int(raw_id)
        except ValueError:
            logger.warning(
                "TelethonSync: TELEGRAM_API_ID не является числом: %r", raw_id
            )
            self._available = False
            return False

        self._api_hash = api_hash
        self._session_str = session
        self._available = True
        logger.info("TelethonSync: учётные данные загружены (api_id=%s)", self._api_id)
        return True

    def _is_cache_valid(self) -> bool:
        return (
            self._cache_ids is not None
            and (time.monotonic() - self._cache_time) < CACHE_TTL
        )

    async def fetch_members(self, group_chat_id: int) -> list[dict] | None:
        """Подключается через MTProto и возвращает список участников.

        Возвращает list[dict] или None при ошибке.
        Каждый dict содержит: telegram_id, username, first_name, last_name,
        is_bot, is_deleted.
        """
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        from telethon.tl.types import UserEmpty

        if not self._load_credentials():
            return None

        client = TelegramClient(
            StringSession(self._session_str),
            self._api_id,
            self._api_hash,
        )

        try:
            await client.connect()

            if not await client.is_user_authorized():
                logger.error(
                    "TelethonSync: сессия TELETHON_SESSION не авторизована — "
                    "сгенерируйте новую через tools/generate_telethon_session.py"
                )
                return None

            members: list[dict] = []
            async for user in client.iter_participants(group_chat_id):
                if isinstance(user, UserEmpty):
                    continue

                first = getattr(user, "first_name", None) or ""
                members.append({
                    "telegram_id": user.id,
                    "username": getattr(user, "username", None),
                    "first_name": first or "Пользователь",
                    "last_name": getattr(user, "last_name", None),
                    "is_bot": getattr(user, "bot", False),
                    "is_deleted": getattr(user, "deleted", False),
                })

            logger.info(
                "TelethonSync: получено %d участников из группы %d",
                len(members), group_chat_id,
            )
            return members

        except Exception as e:
            logger.error("TelethonSync: ошибка при получении участников: %s", e)
            return None

        finally:
            try:
                await client.disconnect()
            except Exception:
                pass

    async def sync_and_get_ids(self, group_chat_id: int, db) -> set[int] | None:
        """Основной метод: синхронизирует участников, возвращает set активных ID.

        Использует кэш CACHE_TTL секунд.
        Upsert обновляет только username/first_name — ники и роли не трогает.
        При любой ошибке возвращает None → вызывающий код использует Bot API.
        """
        if self._is_cache_valid():
            return self._cache_ids

        members = await self.fetch_members(group_chat_id)
        if members is None:
            return None

        active_ids: set[int] = set()
        added = 0
        updated = 0

        for m in members:
            if m["is_deleted"]:
                continue

            existing = await db.get_user(m["telegram_id"])
            await db.upsert_user(
                telegram_id=m["telegram_id"],
                username=m["username"],
                first_name=m["first_name"],
            )

            if existing is None:
                added += 1
            else:
                updated += 1

            active_ids.add(m["telegram_id"])

        logger.info(
            "TelethonSync: синхронизировано %d активных участников "
            "(новых: %d, обновлено: %d)",
            len(active_ids), added, updated,
        )

        self._cache_ids = active_ids
        self._cache_time = time.monotonic()
        return active_ids

    def invalidate_cache(self) -> None:
        """Сбрасывает кэш — следующий запрос выполнит полную синхронизацию."""
        self._cache_ids = None
        self._cache_time = 0.0
