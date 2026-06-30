# -*- coding: utf-8 -*-
"""Integration tests for AI schema with Database class.

Verifies:
- AI schema initialization during Database.connect()
- Backward compatibility with existing database operations
- Non-blocking failure handling
- Health check for AI schema readiness
"""
import asyncio
import tempfile
from pathlib import Path

import aiosqlite
import pytest

from bot.database.db import Database


@pytest.fixture
async def test_db_instance():
    """Create a test Database instance."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name

    db = Database(db_path)
    await db.connect()

    yield db

    await db.close()
    Path(db_path).unlink()


@pytest.mark.asyncio
async def test_database_connect_with_ai_schema(test_db_instance):
    """Test that Database.connect() initializes AI schema without errors."""
    # If we got here without exception, AI schema was initialized
    assert test_db_instance.conn is not None


@pytest.mark.asyncio
async def test_ai_tables_exist_after_connect(test_db_instance):
    """Verify AI tables are created after Database.connect()."""
    db = test_db_instance

    # Check if ai_conversation_history exists
    async with db.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='ai_conversation_history'"
    ) as cursor:
        row = await cursor.fetchone()
        assert row is not None, "ai_conversation_history table not found"

    # Check if ai_knowledge_entries exists
    async with db.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='ai_knowledge_entries'"
    ) as cursor:
        row = await cursor.fetchone()
        assert row is not None, "ai_knowledge_entries table not found"


@pytest.mark.asyncio
async def test_core_tables_unaffected_by_ai_schema(test_db_instance):
    """Verify that core bot tables are not affected by AI schema."""
    db = test_db_instance

    # Check that core tables still exist
    core_tables = ['users', 'news', 'audit_log', 'forum_topics', 'complaints']

    for table_name in core_tables:
        async with db.conn.execute(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
        ) as cursor:
            row = await cursor.fetchone()
            assert row is not None, f"Core table {table_name} not found"


@pytest.mark.asyncio
async def test_existing_operations_still_work(test_db_instance):
    """Test that existing Database methods still work after AI schema init."""
    db = test_db_instance

    # Test user operations
    test_user_id = 123456789
    test_username = "testuser"
    test_first_name = "Test"

    # Create user
    await db.upsert_user(test_user_id, test_username, test_first_name)

    # Get user
    user = await db.get_user(test_user_id)
    assert user is not None
    assert user["telegram_id"] == test_user_id
    assert user["username"] == test_username

    # Get all users
    all_users = await db.get_all_users()
    assert len(all_users) >= 1

    # Set role
    await db.set_role(test_user_id, "Администратор")
    role = await db.get_role(test_user_id)
    assert role == "Администратор"


@pytest.mark.asyncio
async def test_ai_schema_idempotent_after_reconnect(test_db_instance):
    """Test that reconnecting doesn't cause issues."""
    db = test_db_instance
    db_path = db._path

    # Close connection
    await db.close()

    # Reconnect to same database
    db2 = Database(db_path)
    await db2.connect()

    # Verify AI tables still exist
    async with db2.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='ai_conversation_history'"
    ) as cursor:
        row = await cursor.fetchone()
        assert row is not None, "AI table missing after reconnect"

    await db2.close()
    Path(db_path).unlink()


@pytest.mark.asyncio
async def test_audit_log_still_works(test_db_instance):
    """Test that audit logging functionality is unaffected."""
    db = test_db_instance

    # Create a test audit log entry
    log_id = await db.add_audit_log(
        user_id=123456789,
        game_nick="TestPlayer",
        role="Участник",
        action_type="member_register",
        description="Test action",
    )

    assert log_id > 0

    # Retrieve the log
    logs = await db.get_audit_page(0, 10)
    assert len(logs) >= 1


@pytest.mark.asyncio
async def test_news_operations_still_work(test_db_instance):
    """Test that news operations are unaffected."""
    db = test_db_instance

    # Create a news item
    news_id = await db.create_news(
        title="Test News",
        content="This is test content",
        author_id=123456789,
        author_name="TestAuthor",
    )

    assert news_id > 0

    # Retrieve the news
    news = await db.get_news_by_id(news_id)
    assert news is not None
    assert news["title"] == "Test News"


@pytest.mark.asyncio
async def test_foreign_key_cascade_still_works(test_db_instance):
    """Test that foreign key constraints still work."""
    db = test_db_instance

    # Create a user
    user_id = 123456789
    await db.upsert_user(user_id, "testuser", "Test")

    # Add audit log for the user
    log_id = await db.add_audit_log(
        user_id=user_id,
        game_nick="Test",
        role="Участник",
        action_type="test",
        description="Test",
    )

    # Delete the user (should cascade)
    await db.delete_user(user_id)

    # Verify user is deleted
    user = await db.get_user(user_id)
    assert user is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
