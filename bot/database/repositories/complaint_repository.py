# -*- coding: utf-8 -*-
"""Репозиторий жалоб и предложений."""
from __future__ import annotations

from bot.database.repositories.base import BaseRepository


class ComplaintRepository(BaseRepository):
    async def create(self, user_id: int, user_name: str, title: str, content: str) -> int:
        return await self.insert(
            """
            INSERT INTO complaints (user_id, user_name, title, content)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, user_name, title, content),
        )

    async def get(self, complaint_id: int):
        return await self.fetchone(
            "SELECT * FROM complaints WHERE id = ?",
            (complaint_id,),
        )

    async def list_all(self, limit: int = 200):
        return await self.fetchall(
            "SELECT * FROM complaints ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )

    async def list_by_user(self, user_id: int):
        return await self.fetchall(
            "SELECT * FROM complaints WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )

    async def set_status(self, complaint_id: int, status: str) -> None:
        await self.execute(
            "UPDATE complaints SET status = ?, updated_at = datetime('now') WHERE id = ?",
            (status, complaint_id),
        )

    async def set_reply(self, complaint_id: int, reply: str, replied_by: str) -> None:
        await self.execute(
            """
            UPDATE complaints
            SET admin_reply = ?, replied_by = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (reply, replied_by, complaint_id),
        )

    async def delete(self, complaint_id: int) -> None:
        await self.execute("DELETE FROM complaints WHERE id = ?", (complaint_id,))
