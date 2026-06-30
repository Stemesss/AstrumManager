# -*- coding: utf-8 -*-
"""AI module database schema extension.

This module defines additional database tables for the AI system:
- Conversation history (per-user memory)
- Knowledge base entries (searchable, indexed)
- Knowledge sources (file tracking for hot-reload)
- Memory metadata (TTL, lifecycle)

All tables are created with IF NOT EXISTS for safe migrations.
Designed to be completely independent from core bot tables.
"""
import logging

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# TABLE DEFINITIONS
# ──────────────────────────────────────────────────────────────────────────────

_CREATE_AI_CONVERSATION_HISTORY = """
CREATE TABLE IF NOT EXISTS ai_conversation_history (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL,
    conversation_id     TEXT    NOT NULL,
    role                TEXT    NOT NULL,
    message_content     TEXT    NOT NULL,
    tokens_used         INTEGER,
    model_name          TEXT,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    expires_at          TEXT,
    FOREIGN KEY (user_id) REFERENCES users(telegram_id) ON DELETE CASCADE
)
"""

_CREATE_AI_MEMORY_METADATA = """
CREATE TABLE IF NOT EXISTS ai_memory_metadata (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL UNIQUE,
    conversation_id     TEXT    NOT NULL,
    total_messages      INTEGER NOT NULL DEFAULT 0,
    total_tokens        INTEGER NOT NULL DEFAULT 0,
    context_window_size INTEGER NOT NULL DEFAULT 4096,
    last_active_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    ttl_days            INTEGER NOT NULL DEFAULT 30,
    FOREIGN KEY (user_id) REFERENCES users(telegram_id) ON DELETE CASCADE
)
"""

_CREATE_AI_KNOWLEDGE_ENTRIES = """
CREATE TABLE IF NOT EXISTS ai_knowledge_entries (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id           INTEGER NOT NULL,
    title               TEXT    NOT NULL,
    content             TEXT    NOT NULL,
    category            TEXT    NOT NULL,
    subcategory         TEXT,
    keywords            TEXT,
    embedding_vector    BLOB,
    chunk_index         INTEGER,
    priority            INTEGER NOT NULL DEFAULT 0,
    enabled             INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (source_id) REFERENCES ai_knowledge_sources(id) ON DELETE CASCADE
)
"""

_CREATE_AI_KNOWLEDGE_SOURCES = """
CREATE TABLE IF NOT EXISTS ai_knowledge_sources (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type         TEXT    NOT NULL,
    source_path         TEXT    NOT NULL UNIQUE,
    category            TEXT    NOT NULL,
    file_hash           TEXT,
    total_entries       INTEGER NOT NULL DEFAULT 0,
    enabled             INTEGER NOT NULL DEFAULT 1,
    last_loaded_at      TEXT,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now'))
)
"""

# ──────────────────────────────────────────────────────────────────────────────
# INDEXES FOR PERFORMANCE
# ──────────────────────────────────────────────────────────────────────────────

_CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_ai_conv_user_time ON ai_conversation_history(user_id, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_ai_conv_conv_id ON ai_conversation_history(conversation_id)",
    "CREATE INDEX IF NOT EXISTS idx_ai_mem_user ON ai_memory_metadata(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_ai_kb_category ON ai_knowledge_entries(category, enabled)",
    "CREATE INDEX IF NOT EXISTS idx_ai_kb_keywords ON ai_knowledge_entries(keywords)",
    "CREATE INDEX IF NOT EXISTS idx_ai_kb_source ON ai_knowledge_entries(source_id, enabled)",
    "CREATE INDEX IF NOT EXISTS idx_ai_src_path ON ai_knowledge_sources(source_path)",
    "CREATE INDEX IF NOT EXISTS idx_ai_src_category ON ai_knowledge_sources(category)",
]

# ──────────────────────────────────────────────────────────────────────────────
# SCHEMA INITIALIZATION
# ──────────────────────────────────────────────────────────────────────────────


async def init_ai_schema(conn) -> None:
    """
    Initialize AI module database schema.

    Creates all necessary tables and indexes for the AI system.
    Safe to call multiple times (uses IF NOT EXISTS).

    Args:
        conn: aiosqlite.Connection instance

    Raises:
        Exception: If schema creation fails
    """
    logger.info("Initializing AI module database schema...")

    try:
        await conn.execute(_CREATE_AI_CONVERSATION_HISTORY)
        logger.debug("Created/verified ai_conversation_history table")

        await conn.execute(_CREATE_AI_MEMORY_METADATA)
        logger.debug("Created/verified ai_memory_metadata table")

        await conn.execute(_CREATE_AI_KNOWLEDGE_ENTRIES)
        logger.debug("Created/verified ai_knowledge_entries table")

        await conn.execute(_CREATE_AI_KNOWLEDGE_SOURCES)
        logger.debug("Created/verified ai_knowledge_sources table")

        # Create all indexes
        for index_sql in _CREATE_INDEXES:
            await conn.execute(index_sql)

        await conn.commit()
        logger.info("✅ AI module schema successfully initialized")

    except Exception as exc:
        logger.error("❌ Failed to initialize AI schema: %s", exc)
        raise
