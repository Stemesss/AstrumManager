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

_CREATE_NEWS = """
CREATE TABLE IF NOT EXISTS news (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    content     TEXT    NOT NULL,
    author_id   INTEGER NOT NULL,
    author_name TEXT    NOT NULL,
    pinned      INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
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
        await self._conn.execute(_CREATE_NEWS)
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

    async def get_days_in_clan(self, telegram_id: int) -> int:
        """Возвращает количество дней пользователя в клане (с момента регистрации)."""
        async with self.conn.execute(
            "SELECT CAST(julianday('now') - julianday(created_at) AS INTEGER) FROM users WHERE telegram_id = ?",
            (telegram_id,),
        ) as cur:
            row = await cur.fetchone()
            return int(row[0]) if row and row[0] is not None else 0

    async def get_all_users(self) -> list[aiosqlite.Row]:
        """Возвращает всех пользователей."""
        async with self.conn.execute(
            "SELECT * FROM users ORDER BY last_seen DESC"
        ) as cur:
            return await cur.fetchall()

    # ------------------------------------------------------------------ #
    # Методы работы с новостями
    # ------------------------------------------------------------------ #

    async def create_news(
        self, title: str, content: str, author_id: int, author_name: str
    ) -> int:
        """Создаёт новость и возвращает её ID."""
        async with self.conn.execute(
            """
            INSERT INTO news (title, content, author_id, author_name)
            VALUES (?, ?, ?, ?)
            """,
            (title, content, author_id, author_name),
        ) as cur:
            news_id = cur.lastrowid
        await self.conn.commit()
        return news_id  # type: ignore[return-value]

    async def get_news_list(self) -> list[aiosqlite.Row]:
        """Возвращает все новости: закреплённые первыми, затем по дате."""
        async with self.conn.execute(
            "SELECT * FROM news ORDER BY pinned DESC, created_at DESC"
        ) as cur:
            return await cur.fetchall()

    async def get_news_by_id(self, news_id: int) -> aiosqlite.Row | None:
        """Возвращает новость по ID или None."""
        async with self.conn.execute(
            "SELECT * FROM news WHERE id = ?", (news_id,)
        ) as cur:
            return await cur.fetchone()

    async def update_news(
        self,
        news_id: int,
        *,
        title: str | None = None,
        content: str | None = None,
    ) -> None:
        """Обновляет заголовок и/или текст новости."""
        if title is not None:
            await self.conn.execute(
                "UPDATE news SET title = ?, updated_at = datetime('now') WHERE id = ?",
                (title, news_id),
            )
        if content is not None:
            await self.conn.execute(
                "UPDATE news SET content = ?, updated_at = datetime('now') WHERE id = ?",
                (content, news_id),
            )
        await self.conn.commit()

    async def delete_news(self, news_id: int) -> None:
        """Удаляет новость по ID."""
        await self.conn.execute("DELETE FROM news WHERE id = ?", (news_id,))
        await self.conn.commit()

    async def toggle_news_pin(self, news_id: int) -> bool:
        """Переключает закрепление новости. Возвращает новое состояние (True = закреплено)."""
        await self.conn.execute(
            "UPDATE news SET pinned = NOT pinned, updated_at = datetime('now') WHERE id = ?",
            (news_id,),
        )
        await self.conn.commit()
        row = await self.get_news_by_id(news_id)
        return bool(row["pinned"]) if row else False
