# -*- coding: utf-8 -*-
"""Репозиторий журнала аудита."""
from __future__ import annotations

import re

from bot.database.repositories.base import BaseRepository


class AuditRepository(BaseRepository):
    async def add_log(
        self,
        user_id: int,
        game_nick: str,
        role: str,
        action_type: str,
        description: str,
    ) -> int:
        return await self.insert(
            """
            INSERT INTO audit_log (user_id, game_nick, role, action_type, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, game_nick, role, action_type, description),
        )

    async def get_page(
        self,
        page: int,
        per_page: int,
        action_types: list[str] | None = None,
    ):
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
        return await self.fetchall(sql, params)

    async def count(self, action_types: list[str] | None = None) -> int:
        if action_types:
            placeholders = ",".join("?" * len(action_types))
            sql = f"SELECT COUNT(*) FROM audit_log WHERE action_type IN ({placeholders})"
            params: tuple = tuple(action_types)
        else:
            sql = "SELECT COUNT(*) FROM audit_log"
            params = ()
        row = await self.fetchone(sql, params)
        return int(row[0]) if row else 0

    async def search(self, query: str, per_page: int = 20):
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
        return await self.fetchall(sql, params)

    async def clear(self) -> int:
        row = await self.fetchone("SELECT COUNT(*) FROM audit_log")
        count = int(row[0]) if row else 0
        await self.execute("DELETE FROM audit_log")
        return count

    async def count_all(self) -> int:
        row = await self.fetchone("SELECT COUNT(*) FROM audit_log")
        return int(row[0]) if row else 0

    async def delete_all(self) -> None:
        await self.execute("DELETE FROM audit_log")
