# -*- coding: utf-8 -*-
"""Асинхронная работа с SQLite через aiosqlite."""
import logging
import os

import aiosqlite

logger = logging.getLogger(__name__)

_CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    telegram_id  INTEGER PRIMARY KEY,
    username     TEXT,
    first_name   TEXT    NOT NULL,
    role         TEXT    NOT NULL DEFAULT 'Участник',
    created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    last_seen    TEXT    NOT NULL DEFAULT (datetime('now'))
)
"""


class Database:
    """Обёртка над aiosqlite для хранения данных пользователей."""

    def __init__(self, path: str) -> None:
        self._path = path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Открывает соединение и создаёт схему, если её нет."""
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        self._conn = await aiosqlite.connect(self._path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute(_CREATE_USERS)
        await self._conn.commit()
        logger.info("База данных подключена: %s", self._path)

    async def close(self) -> None:
        """Закрывает соединение с базой данных."""
        if self._conn:
            await self._conn.close()
            logger.info("Соединение с базой данных закрыто")

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("База данных не подключена — вызовите connect() сначала")
        return self._conn

    # ------------------------------------------------------------------ #
    # Методы работы с пользователями
    # ------------------------------------------------------------------ #

    async def get_user(self, telegram_id: int) -> aiosqlite.Row | None:
        """Возвращает запись пользователя по telegram_id или None."""
        async with self.conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cur:
            return await cur.fetchone()

    async def upsert_user(
        self, telegram_id: int, username: str | None, first_name: str
    ) -> None:
        """Создаёт нового пользователя или обновляет его данные (last_seen)."""
        await self.conn.execute(
            """
            INSERT INTO users (telegram_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username   = excluded.username,
                first_name = excluded.first_name,
                last_seen  = datetime('now')
            """,
            (telegram_id, username, first_name),
        )
        await self.conn.commit()

    async def get_role(self, telegram_id: int) -> str:
        """Возвращает роль пользователя. Участник по умолчанию."""
        row = await self.get_user(telegram_id)
        return row["role"] if row else "Участник"

    async def set_role(self, telegram_id: int, role: str) -> None:
        """Устанавливает роль пользователя."""
        await self.conn.execute(
            "UPDATE users SET role = ? WHERE telegram_id = ?", (role, telegram_id)
        )
        await self.conn.commit()

    async def get_all_users(self) -> list[aiosqlite.Row]:
        """Возвращает всех пользователей."""
        async with self.conn.execute(
            "SELECT * FROM users ORDER BY last_seen DESC"
        ) as cur:
            return await cur.fetchall()
