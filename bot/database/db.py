# -*- coding: utf-8 -*-
"""Асинхронная работа с SQLite через aiosqlite."""
import logging
import os
import re

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

_CREATE_AUDIT = """
CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    game_nick   TEXT    NOT NULL,
    role        TEXT    NOT NULL,
    action_type TEXT    NOT NULL,
    description TEXT    NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
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
        await self._conn.execute(_CREATE_AUDIT)
        # Миграция: добавляем game_nick для существующих БД (игнорируем если уже есть)
        try:
            await self._conn.execute("ALTER TABLE users ADD COLUMN game_nick TEXT")
            logger.info("Миграция: столбец game_nick добавлен в таблицу users")
        except Exception:
            pass  # Столбец уже существует
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

    async def set_game_nick(self, telegram_id: int, game_nick: str) -> None:
        """Устанавливает или обновляет игровой ник пользователя."""
        await self.conn.execute(
            "UPDATE users SET game_nick = ? WHERE telegram_id = ?",
            (game_nick, telegram_id),
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

    # ------------------------------------------------------------------ #
    # Методы работы с журналом аудита
    # ------------------------------------------------------------------ #

    async def add_audit_log(
        self,
        user_id: int,
        game_nick: str,
        role: str,
        action_type: str,
        description: str,
    ) -> int:
        """Добавляет запись в журнал аудита, возвращает её ID."""
        async with self.conn.execute(
            """
            INSERT INTO audit_log (user_id, game_nick, role, action_type, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, game_nick, role, action_type, description),
        ) as cur:
            row_id = cur.lastrowid
        await self.conn.commit()
        return row_id  # type: ignore[return-value]

    async def get_audit_page(
        self,
        page: int,
        per_page: int,
        action_types: list[str] | None = None,
    ) -> list[aiosqlite.Row]:
        """Возвращает страницу записей журнала, отсортированных от новых к старым."""
        offset = page * per_page
        if action_types:
            placeholders = ",".join("?" * len(action_types))
            sql = (
                f"SELECT * FROM audit_log WHERE action_type IN ({placeholders})"
                " ORDER BY id DESC LIMIT ? OFFSET ?"
            )
            params: tuple = (*action_types, per_page, offset)
        else:
            sql = "SELECT * FROM audit_log ORDER BY id DESC LIMIT ? OFFSET ?"
            params = (per_page, offset)
        async with self.conn.execute(sql, params) as cur:
            return await cur.fetchall()

    async def count_audit(
        self, action_types: list[str] | None = None
    ) -> int:
        """Возвращает общее число записей (с учётом фильтра по типу)."""
        if action_types:
            placeholders = ",".join("?" * len(action_types))
            sql = f"SELECT COUNT(*) FROM audit_log WHERE action_type IN ({placeholders})"
            params: tuple = tuple(action_types)
        else:
            sql = "SELECT COUNT(*) FROM audit_log"
            params = ()
        async with self.conn.execute(sql, params) as cur:
            row = await cur.fetchone()
            return int(row[0]) if row else 0

    async def search_audit(
        self, query: str, per_page: int = 20
    ) -> list[aiosqlite.Row]:
        """
        Поиск записей:
        - формат дд.мм.гггг → ищем по created_at;
        - иначе             → по game_nick или action_type (LIKE).
        """
        date_match = re.match(r"(\d{2})\.(\d{2})\.(\d{4})", query.strip())
        if date_match:
            d, m, y = date_match.groups()
            date_str = f"{y}-{m}-{d}"
            sql = (
                "SELECT * FROM audit_log WHERE created_at LIKE ?"
                " ORDER BY id DESC LIMIT ?"
            )
            params: tuple = (f"{date_str}%", per_page)
        else:
            like_q = f"%{query}%"
            sql = (
                "SELECT * FROM audit_log"
                " WHERE game_nick LIKE ? OR action_type LIKE ?"
                " ORDER BY id DESC LIMIT ?"
            )
            params = (like_q, like_q, per_page)
        async with self.conn.execute(sql, params) as cur:
            return await cur.fetchall()

    async def clear_audit_log(self) -> int:
        """Удаляет все записи журнала, возвращает количество удалённых строк."""
        async with self.conn.execute("SELECT COUNT(*) FROM audit_log") as cur:
            row = await cur.fetchone()
            count = int(row[0]) if row else 0
        await self.conn.execute("DELETE FROM audit_log")
        await self.conn.commit()
        return count
