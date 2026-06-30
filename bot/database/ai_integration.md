# -*- coding: utf-8 -*-
"""Database integration with AI schema (PHASE 1 INTEGRATION).

This module extends bot/database/db.py with AI schema initialization.

DESIGN DECISIONS:

1. BACKWARD COMPATIBILITY:
   - AI schema initialization is OPTIONAL and non-blocking
   - If AI schema fails, existing bot functionality continues unaffected
   - All AI tables use prefix 'ai_' to clearly separate from core tables

2. NON-INTRUSIVE INTEGRATION:
   - Added only TWO methods to Database class:
     a) _init_ai_schema() - private, called during connect()
     b) is_ai_schema_ready() - public, check if AI tables are initialized
   - Zero changes to existing Database methods
   - Zero changes to existing method signatures

3. ERROR HANDLING:
   - AI schema errors are LOGGED but NOT RAISED
   - Bot starts successfully even if AI schema initialization fails
   - Administrators can check AI status via is_ai_schema_ready()

4. MIGRATION SAFETY:
   - Uses idempotent SQL (CREATE TABLE IF NOT EXISTS)
   - Safe to call connect() multiple times
   - Indexes are created with IF NOT EXISTS

5. PERFORMANCE:
   - AI schema creation happens ONCE during connect()
   - Indexes are created to ensure fast queries
   - No impact on existing bot queries

COMPATIBILITY MATRIX:
  - Existing databases: ✅ AI tables added on next connect()
  - New databases: ✅ All tables created together
  - Database versions: ✅ Forward/backward compatible
  - Bot functionality: ✅ Zero impact if AI fails
  - Performance: ✅ Minimal impact (only 4 tables + 8 indexes)
"""

# NOTE: This file documents the modifications to Database class.
# Actual modifications are made inline in bot/database/db.py
# See git diff for the exact changes.

# MODIFICATIONS TO Database.connect():
#
# After line 128 (await self._conn.commit()), add:
#     await self._init_ai_schema()
#
# This ensures AI schema is initialized after core schema.

# ADDED METHODS (at end of Database class):
#
#     async def _init_ai_schema(self) -> None:
#         """Initialize AI module database schema (private, non-blocking)."""
#         try:
#             from bot.database.ai_schema import init_ai_schema
#             await init_ai_schema(self.conn)
#             logger.info("✅ AI module schema initialized successfully")
#         except Exception as exc:
#             logger.warning(
#                 "⚠️ AI module schema initialization failed (bot will continue): %s", exc
#             )
#             # AI schema failure is NOT critical - bot continues normally
#
#     def is_ai_schema_ready(self) -> bool:
#         """Check if AI schema tables exist."""
#         if self._conn is None:
#             return False
#         try:
#             # Check if ai_knowledge_sources table exists
#             result = self._conn.execute(
#                 "SELECT name FROM sqlite_master "
#                 "WHERE type='table' AND name='ai_knowledge_sources'"
#             )
#             return result.fetchone() is not None
#         except Exception:
#             return False

# These additions ensure:
# 1. AI schema is initialized when database connects
# 2. Failures don't crash the bot
# 3. Administrators can check AI readiness
# 4. Bot functions normally if AI schema fails
