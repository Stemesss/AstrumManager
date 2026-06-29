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

_CREATE_TOPICS = """
CREATE TABLE IF NOT EXISTS forum_topics (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_name            TEXT    UNIQUE NOT NULL,
    message_thread_id     INTEGER,
    enabled               INTEGER NOT NULL DEFAULT 1,
    icon_custom_emoji_id  TEXT
)
"""

_CREATE_ATTACHMENTS = """
CREATE TABLE IF NOT EXISTS publication_attachments (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    publication_type TEXT    NOT NULL,
    publication_id   INTEGER,
    file_id          TEXT    NOT NULL,
    file_unique_id   TEXT,
    file_type        TEXT    NOT NULL,
    file_name        TEXT,
    created_at       TEXT    NOT NULL DEFAULT (datetime('now'))
)
"""

_CREATE_COMPLAINTS = """
CREATE TABLE IF NOT EXISTS complaints (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    user_name   TEXT    NOT NULL,
    title       TEXT    NOT NULL,
    content     TEXT    NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'new',
    admin_reply TEXT,
    replied_by  TEXT,
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
        await self._conn.execute(_CREATE_AUDIT)
        await self._conn.execute(_CREATE_TOPICS)
        await self._conn.execute(_CREATE_ATTACHMENTS)
        await self._conn.execute(_CREATE_COMPLAINTS)
        # Миграция: добавляем game_nick для существующих БД (игнорируем если уже есть)
        try:
            await self._conn.execute("ALTER TABLE users ADD COLUMN game_nick TEXT")
            logger.info("Миграция: столбец game_nick добавлен в таблицу users")
        except Exception:
            pass  # Столбец уже существует
        # Миграция: content_type для разграничения типов записей
        try:
            await self._conn.execute(
                "ALTER TABLE news ADD COLUMN content_type TEXT NOT NULL DEFAULT 'news'"
            )
            logger.info("Миграция: столбец content_type добавлен в таблицу news")
        except Exception:
            pass  # Столбец уже существует
        # Миграция: icon_custom_emoji_id для форумных тем
        try:
            await self._conn.execute(
                "ALTER TABLE forum_topics ADD COLUMN icon_custom_emoji_id TEXT"
            )
            logger.info("Миграция: столбец icon_custom_emoji_id добавлен в таблицу forum_topics")
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
        self,
        title: str,
        content: str,
        author_id: int,
        author_name: str,
        content_type: str = "news",
    ) -> int:
        """Создаёт запись контента и возвращает её ID."""
        async with self.conn.execute(
            """
            INSERT INTO news (title, content, author_id, author_name, content_type)
            VALUES (?, ?, ?, ?, ?)
            """,
            (title, content, author_id, author_name, content_type),
        ) as cur:
            news_id = cur.lastrowid
        await self.conn.commit()
        return news_id  # type: ignore[return-value]

    async def get_news_list(self) -> list[aiosqlite.Row]:
        """Возвращает новости типа 'news': закреплённые первыми, затем по дате."""
        async with self.conn.execute(
            "SELECT * FROM news WHERE content_type = 'news' ORDER BY pinned DESC, created_at DESC"
        ) as cur:
            return await cur.fetchall()

    async def get_news_list_by_type(self, content_type: str) -> list[aiosqlite.Row]:
        """Возвращает записи по типу контента: закреплённые первыми, затем по дате."""
        async with self.conn.execute(
            "SELECT * FROM news WHERE content_type = ? ORDER BY pinned DESC, created_at DESC",
            (content_type,),
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

    # ------------------------------------------------------------------ #
    # Методы статистики
    # ------------------------------------------------------------------ #

    async def stats_top_active_users(self, limit: int = 10) -> list[aiosqlite.Row]:
        """Топ участников по активности (формула очков из audit_log)."""
        sql = """
        SELECT
            al.user_id,
            COALESCE(u.game_nick, MAX(al.game_nick)) AS game_nick,
            MAX(al.role)                              AS role,
            SUM(CASE al.action_type
                WHEN 'news_create'       THEN 5
                WHEN 'guide_create'      THEN 10
                WHEN 'screenshot_upload' THEN 2
                WHEN 'event_create'      THEN 8
                ELSE 0 END)                           AS score,
            SUM(CASE WHEN al.action_type = 'news_create'       THEN 1 ELSE 0 END) AS news_count,
            SUM(CASE WHEN al.action_type = 'guide_create'      THEN 1 ELSE 0 END) AS guides_count,
            SUM(CASE WHEN al.action_type = 'screenshot_upload' THEN 1 ELSE 0 END) AS screenshots_count,
            SUM(CASE WHEN al.action_type = 'event_create'      THEN 1 ELSE 0 END) AS events_count
        FROM audit_log al
        LEFT JOIN users u ON u.telegram_id = al.user_id
        WHERE al.action_type IN ('news_create','guide_create','screenshot_upload','event_create')
        GROUP BY al.user_id
        ORDER BY score DESC
        LIMIT ?
        """
        async with self.conn.execute(sql, (limit,)) as cur:
            return await cur.fetchall()

    async def stats_count_news(self) -> int:
        """Общее количество новостей."""
        async with self.conn.execute("SELECT COUNT(*) FROM news") as cur:
            row = await cur.fetchone()
            return int(row[0]) if row else 0

    async def stats_news_by_author(self, limit: int = 5) -> list[aiosqlite.Row]:
        """Топ авторов новостей по количеству публикаций."""
        sql = """
        SELECT author_id, author_name, COUNT(*) AS count
        FROM news
        GROUP BY author_id
        ORDER BY count DESC
        LIMIT ?
        """
        async with self.conn.execute(sql, (limit,)) as cur:
            return await cur.fetchall()

    async def stats_news_latest(self) -> aiosqlite.Row | None:
        """Последняя опубликованная новость (заголовок + дата)."""
        async with self.conn.execute(
            "SELECT title, created_at FROM news ORDER BY created_at DESC LIMIT 1"
        ) as cur:
            return await cur.fetchone()

    async def stats_content_by_user(
        self, action_type: str, limit: int = 5
    ) -> list[aiosqlite.Row]:
        """Топ участников по заданному типу действий (guide_create, screenshot_upload, event_create)."""
        sql = """
        SELECT al.user_id,
               COALESCE(u.game_nick, MAX(al.game_nick)) AS game_nick,
               COUNT(*)                                  AS count
        FROM audit_log al
        LEFT JOIN users u ON u.telegram_id = al.user_id
        WHERE al.action_type = ?
        GROUP BY al.user_id
        ORDER BY count DESC
        LIMIT ?
        """
        async with self.conn.execute(sql, (action_type, limit)) as cur:
            return await cur.fetchall()

    async def stats_content_latest(self, action_type: str) -> aiosqlite.Row | None:
        """Последняя запись заданного типа из audit_log."""
        async with self.conn.execute(
            "SELECT game_nick, description, created_at"
            " FROM audit_log WHERE action_type = ?"
            " ORDER BY id DESC LIMIT 1",
            (action_type,),
        ) as cur:
            return await cur.fetchone()

    async def stats_count_action(self, action_type: str) -> int:
        """Количество записей конкретного action_type в audit_log."""
        async with self.conn.execute(
            "SELECT COUNT(*) FROM audit_log WHERE action_type = ?", (action_type,)
        ) as cur:
            row = await cur.fetchone()
            return int(row[0]) if row else 0

    async def stats_user_activity(self, user_id: int) -> "aiosqlite.Row | None":
        """Очки и счётчики публикаций одного участника из журнала аудита."""
        sql = """
        SELECT
            SUM(CASE action_type
                WHEN 'news_create'       THEN 5
                WHEN 'guide_create'      THEN 10
                WHEN 'screenshot_upload' THEN 2
                WHEN 'event_create'      THEN 8
                ELSE 0 END)                                                         AS score,
            SUM(CASE WHEN action_type = 'news_create'       THEN 1 ELSE 0 END)     AS news_count,
            SUM(CASE WHEN action_type = 'guide_create'      THEN 1 ELSE 0 END)     AS guides_count,
            SUM(CASE WHEN action_type = 'screenshot_upload' THEN 1 ELSE 0 END)     AS screenshots_count,
            SUM(CASE WHEN action_type = 'event_create'      THEN 1 ELSE 0 END)     AS events_count
        FROM audit_log
        WHERE user_id = ?
        """
        async with self.conn.execute(sql, (user_id,)) as cur:
            return await cur.fetchone()

    async def stats_users_joined(self) -> tuple[int, int, int, int]:
        """(total, today, week, month) — сколько пользователей вступило."""
        async with self.conn.execute("SELECT COUNT(*) FROM users") as cur:
            total = int((await cur.fetchone())[0])
        async with self.conn.execute(
            "SELECT COUNT(*) FROM users WHERE date(created_at) = date('now')"
        ) as cur:
            today = int((await cur.fetchone())[0])
        async with self.conn.execute(
            "SELECT COUNT(*) FROM users WHERE created_at >= datetime('now', '-7 days')"
        ) as cur:
            week = int((await cur.fetchone())[0])
        async with self.conn.execute(
            "SELECT COUNT(*) FROM users WHERE created_at >= datetime('now', '-30 days')"
        ) as cur:
            month = int((await cur.fetchone())[0])
        return total, today, week, month

    async def stats_users_by_day(self, days: int = 7) -> list[aiosqlite.Row]:
        """Количество новых пользователей за каждый из последних N дней."""
        sql = """
        SELECT date(created_at) AS day, COUNT(*) AS cnt
        FROM users
        WHERE created_at >= datetime('now', ? || ' days')
        GROUP BY day
        ORDER BY day
        """
        async with self.conn.execute(sql, (f"-{days - 1}",)) as cur:
            return await cur.fetchall()

    async def _stats_best_since(self, since_expr: str) -> aiosqlite.Row | None:
        """
        Участник с максимальными очками начиная с `since_expr` (SQLite-выражение).
        Формула: news_create=5, guide_create=10, screenshot_upload=2, event_create=8.
        since_expr встраивается напрямую — передавать только хардкоженные константы.
        """
        sql = f"""
        SELECT
            al.user_id,
            COALESCE(u.game_nick, MAX(al.game_nick)) AS game_nick,
            MAX(al.role)                              AS role,
            SUM(CASE al.action_type
                WHEN 'news_create'       THEN 5
                WHEN 'guide_create'      THEN 10
                WHEN 'screenshot_upload' THEN 2
                WHEN 'event_create'      THEN 8
                ELSE 0 END)                           AS score,
            SUM(CASE WHEN al.action_type = 'news_create'       THEN 1 ELSE 0 END) AS news_count,
            SUM(CASE WHEN al.action_type = 'guide_create'      THEN 1 ELSE 0 END) AS guides_count,
            SUM(CASE WHEN al.action_type = 'screenshot_upload' THEN 1 ELSE 0 END) AS screenshots_count,
            SUM(CASE WHEN al.action_type = 'event_create'      THEN 1 ELSE 0 END) AS events_count
        FROM audit_log al
        LEFT JOIN users u ON u.telegram_id = al.user_id
        WHERE al.action_type IN ('news_create','guide_create','screenshot_upload','event_create')
          AND al.created_at >= {since_expr}
        GROUP BY al.user_id
        ORDER BY score DESC
        LIMIT 1
        """
        async with self.conn.execute(sql) as cur:
            return await cur.fetchone()

    # ── Сводные методы для карточек контента ───────────────────────────────

    async def _stats_content_bundle(
        self, action_type: str, top_limit: int
    ) -> tuple[int, list, "aiosqlite.Row | None"]:
        """Сводка для одного типа контента: всего + топ + последняя запись."""
        total = await self.stats_count_action(action_type)
        top = await self.stats_content_by_user(action_type, top_limit)
        latest = await self.stats_content_latest(action_type)
        return total, top, latest

    async def stats_news(
        self, top_limit: int = 3
    ) -> tuple[int, list, "aiosqlite.Row | None"]:
        """Сводка новостей: всего + топ авторов + последняя новость."""
        total = await self.stats_count_news()
        top = await self.stats_news_by_author(top_limit)
        latest = await self.stats_news_latest()
        return total, top, latest

    async def stats_guides(
        self, top_limit: int = 3
    ) -> tuple[int, list, "aiosqlite.Row | None"]:
        """Сводка гайдов."""
        return await self._stats_content_bundle("guide_create", top_limit)

    async def stats_screenshots(
        self, top_limit: int = 3
    ) -> tuple[int, list, "aiosqlite.Row | None"]:
        """Сводка скриншотов."""
        return await self._stats_content_bundle("screenshot_upload", top_limit)

    async def stats_events(
        self, top_limit: int = 3
    ) -> tuple[int, list, "aiosqlite.Row | None"]:
        """Сводка событий."""
        return await self._stats_content_bundle("event_create", top_limit)

    # ── Победитель по периоду ───────────────────────────────────────────────

    async def stats_best_of_month(self) -> aiosqlite.Row | None:
        """Победитель текущего календарного месяца."""
        return await self._stats_best_since("strftime('%Y-%m-01', 'now')")

    async def stats_best_of_week(self) -> aiosqlite.Row | None:
        """Победитель последних 7 дней."""
        return await self._stats_best_since("datetime('now', '-6 days')")

    # ------------------------------------------------------------------ #
    # Методы работы с ветками форума (forum_topics)
    # ------------------------------------------------------------------ #

    async def topic_set(
        self,
        topic_name: str,
        thread_id: int | None,
        icon_custom_emoji_id: str | None = None,
    ) -> None:
        """Создаёт или обновляет запись ветки форума."""
        await self.conn.execute(
            """
            INSERT INTO forum_topics (topic_name, message_thread_id, icon_custom_emoji_id)
            VALUES (?, ?, ?)
            ON CONFLICT(topic_name) DO UPDATE SET
                message_thread_id    = excluded.message_thread_id,
                icon_custom_emoji_id = COALESCE(excluded.icon_custom_emoji_id, forum_topics.icon_custom_emoji_id)
            """,
            (topic_name, thread_id, icon_custom_emoji_id),
        )
        await self.conn.commit()

    async def topic_get(self, topic_name: str) -> "aiosqlite.Row | None":
        """Возвращает строку ветки или None."""
        async with self.conn.execute(
            "SELECT * FROM forum_topics WHERE topic_name = ?",
            (topic_name,),
        ) as cur:
            return await cur.fetchone()

    async def topic_list(self) -> list:
        """Список всех сохранённых веток."""
        async with self.conn.execute(
            "SELECT * FROM forum_topics ORDER BY id"
        ) as cur:
            return await cur.fetchall()

    # ------------------------------------------------------------------ #
    # Методы работы с вложениями публикаций (publication_attachments)
    # ------------------------------------------------------------------ #

    async def attachment_save(
        self,
        publication_type: str,
        publication_id: int | None,
        file_id: str,
        file_unique_id: str | None,
        file_type: str,
        file_name: str | None = None,
    ) -> None:
        """Сохраняет file_id вложения, привязанного к публикации."""
        await self.conn.execute(
            """
            INSERT INTO publication_attachments
                (publication_type, publication_id, file_id, file_unique_id, file_type, file_name)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (publication_type, publication_id, file_id, file_unique_id, file_type, file_name),
        )
        await self.conn.commit()

    async def attachments_by_publication(
        self,
        publication_type: str,
        publication_id: int | None,
    ) -> list:
        """Возвращает все вложения конкретной публикации."""
        async with self.conn.execute(
            """
            SELECT * FROM publication_attachments
            WHERE publication_type = ? AND publication_id IS ?
            ORDER BY id
            """,
            (publication_type, publication_id),
        ) as cur:
            return await cur.fetchall()

    # ------------------------------------------------------------------ #
    # Методы работы с жалобами и предложениями
    # ------------------------------------------------------------------ #

    async def complaint_create(
        self, user_id: int, user_name: str, title: str, content: str
    ) -> int:
        """Создаёт обращение и возвращает его ID."""
        async with self.conn.execute(
            """
            INSERT INTO complaints (user_id, user_name, title, content)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, user_name, title, content),
        ) as cur:
            row_id = cur.lastrowid
        await self.conn.commit()
        return row_id  # type: ignore[return-value]

    async def complaint_get(self, complaint_id: int) -> "aiosqlite.Row | None":
        """Возвращает обращение по ID или None."""
        async with self.conn.execute(
            "SELECT * FROM complaints WHERE id = ?", (complaint_id,)
        ) as cur:
            return await cur.fetchone()

    async def complaint_list(self, limit: int = 200) -> list:
        """Возвращает все обращения, новейшие первыми."""
        async with self.conn.execute(
            "SELECT * FROM complaints ORDER BY created_at DESC LIMIT ?", (limit,)
        ) as cur:
            return await cur.fetchall()

    async def complaint_list_by_user(self, user_id: int) -> list:
        """Возвращает обращения конкретного пользователя."""
        async with self.conn.execute(
            "SELECT * FROM complaints WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ) as cur:
            return await cur.fetchall()

    async def complaint_set_status(self, complaint_id: int, status: str) -> None:
        """Обновляет статус обращения."""
        await self.conn.execute(
            "UPDATE complaints SET status = ?, updated_at = datetime('now') WHERE id = ?",
            (status, complaint_id),
        )
        await self.conn.commit()

    async def complaint_set_reply(
        self, complaint_id: int, reply: str, replied_by: str
    ) -> None:
        """Сохраняет ответ администрации."""
        await self.conn.execute(
            """
            UPDATE complaints
            SET admin_reply = ?, replied_by = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (reply, replied_by, complaint_id),
        )
        await self.conn.commit()

    async def complaint_delete(self, complaint_id: int) -> None:
        """Удаляет обращение."""
        await self.conn.execute("DELETE FROM complaints WHERE id = ?", (complaint_id,))
        await self.conn.commit()
