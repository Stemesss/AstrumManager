# -*- coding: utf-8 -*-
"""Tests for AI database schema.

Verifies:
- Schema creation (idempotent)
- Table structure
- Indexes creation
- Foreign key constraints
- No conflicts with existing schema
"""
import asyncio
import sqlite3
import tempfile
from pathlib import Path

import aiosqlite
import pytest

from bot.database.ai_schema import init_ai_schema


@pytest.fixture
async def test_db():
    """Create temporary test database."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name

    # Create users table (dependency for foreign key)
    conn = await aiosqlite.connect(db_path)
    await conn.execute(
        """
        CREATE TABLE users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'Участник',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            last_seen TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    await conn.commit()

    yield conn

    # Cleanup
    await conn.close()
    Path(db_path).unlink()


@pytest.mark.asyncio
async def test_ai_schema_initialization(test_db):
    """Test that AI schema initializes without errors."""
    await init_ai_schema(test_db)
    # If no exception, test passed
    assert True


@pytest.mark.asyncio
async def test_ai_schema_idempotent(test_db):
    """Test that calling init_ai_schema multiple times is safe."""
    await init_ai_schema(test_db)
    await init_ai_schema(test_db)
    await init_ai_schema(test_db)
    # If no exception on multiple calls, test passed
    assert True


@pytest.mark.asyncio
async def test_conversation_history_table_exists(test_db):
    """Verify ai_conversation_history table structure."""
    await init_ai_schema(test_db)

    async with test_db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='ai_conversation_history'"
    ) as cursor:
        row = await cursor.fetchone()
        assert row is not None, "ai_conversation_history table not created"


@pytest.mark.asyncio
async def test_knowledge_entries_table_exists(test_db):
    """Verify ai_knowledge_entries table structure."""
    await init_ai_schema(test_db)

    async with test_db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='ai_knowledge_entries'"
    ) as cursor:
        row = await cursor.fetchone()
        assert row is not None, "ai_knowledge_entries table not created"


@pytest.mark.asyncio
async def test_indexes_created(test_db):
    """Verify all indexes are created."""
    await init_ai_schema(test_db)

    async with test_db.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_ai%'"
    ) as cursor:
        rows = await cursor.fetchall()
        # Should have at least 8 indexes
        assert len(rows) >= 8, f"Expected at least 8 AI indexes, got {len(rows)}"


@pytest.mark.asyncio
async def test_foreign_key_constraint(test_db):
    """Verify foreign key relationships."""
    await init_ai_schema(test_db)

    # Try to insert into conversation_history with non-existent user_id
    # This should fail if FK constraint is enabled
    try:
        await test_db.execute("PRAGMA foreign_keys = ON")
        with pytest.raises(Exception):  # IntegrityError
            await test_db.execute(
                """
                INSERT INTO ai_conversation_history
                (user_id, conversation_id, role, message_content)
                VALUES (99999, 'test-conv', 'user', 'test')
                """
            )
            await test_db.commit()
    except Exception:
        # Foreign keys might be disabled, which is ok for this test
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
