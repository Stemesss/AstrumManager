# -*- coding: utf-8 -*-
"""Версионированные миграции SQLite."""
from __future__ import annotations

import logging
from dataclasses import dataclass

import aiosqlite

logger = logging.getLogger(__name__)

_CREATE_SCHEMA_MIGRATIONS = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL,
    applied_at  TEXT    NOT NULL DEFAULT (datetime('now'))
)
"""

_CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    telegram_id  INTEGER PRIMARY KEY,
    username     TEXT,
    first_name   TEXT    NOT NULL,
    role         TEXT    NOT NULL DEFAULT 'Участник',
    created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    last_seen    TEXT    NOT NULL DEFAULT (datetime('now')),
    game_nick    TEXT
)
"""

_CREATE_NEWS = """
CREATE TABLE IF NOT EXISTS news (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT    NOT NULL,
    content      TEXT    NOT NULL,
    author_id    INTEGER NOT NULL,
    author_name  TEXT    NOT NULL,
    pinned       INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    content_type TEXT    NOT NULL DEFAULT 'news'
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


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    name: str
    handler: "MigrationHandler"


class MigrationHandler:
    async def __call__(self, conn: aiosqlite.Connection) -> None: ...


async def _column_exists(
    conn: aiosqlite.Connection,
    table_name: str,
    column_name: str,
) -> bool:
    async with conn.execute(f"PRAGMA table_info({table_name})") as cur:
        rows = await cur.fetchall()
    return any(row[1] == column_name for row in rows)


async def _create_base_schema(conn: aiosqlite.Connection) -> None:
    await conn.execute(_CREATE_USERS)
    await conn.execute(_CREATE_NEWS)
    await conn.execute(_CREATE_AUDIT)
    await conn.execute(_CREATE_TOPICS)
    await conn.execute(_CREATE_ATTACHMENTS)
    await conn.execute(_CREATE_COMPLAINTS)


async def _add_users_game_nick(conn: aiosqlite.Connection) -> None:
    if await _column_exists(conn, "users", "game_nick"):
        return
    await conn.execute("ALTER TABLE users ADD COLUMN game_nick TEXT")


async def _add_news_content_type(conn: aiosqlite.Connection) -> None:
    if await _column_exists(conn, "news", "content_type"):
        return
    await conn.execute(
        "ALTER TABLE news ADD COLUMN content_type TEXT NOT NULL DEFAULT 'news'"
    )


async def _add_topics_icon_custom_emoji_id(conn: aiosqlite.Connection) -> None:
    if await _column_exists(conn, "forum_topics", "icon_custom_emoji_id"):
        return
    await conn.execute(
        "ALTER TABLE forum_topics ADD COLUMN icon_custom_emoji_id TEXT"
    )


MIGRATIONS: tuple[Migration, ...] = (
    Migration(1, "create_base_schema", _create_base_schema),
    Migration(2, "add_users_game_nick", _add_users_game_nick),
    Migration(3, "add_news_content_type", _add_news_content_type),
    Migration(4, "add_topics_icon_custom_emoji_id", _add_topics_icon_custom_emoji_id),
)


async def apply_pending_migrations(conn: aiosqlite.Connection) -> None:
    """Применяет все неприменённые миграции."""
    await conn.execute(_CREATE_SCHEMA_MIGRATIONS)
    async with conn.execute("SELECT version FROM schema_migrations") as cur:
        applied_rows = await cur.fetchall()
    applied_versions = {int(row[0]) for row in applied_rows}

    for migration in MIGRATIONS:
        if migration.version in applied_versions:
            continue
        await migration.handler(conn)
        await conn.execute(
            "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
            (migration.version, migration.name),
        )
        await conn.commit()
        logger.info(
            "Миграция применена: #%s %s",
            migration.version,
            migration.name,
        )
