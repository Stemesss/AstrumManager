# -*- coding: utf-8 -*-
"""Репозиторий контента."""
from __future__ import annotations

from bot.database.repositories.base import BaseRepository


class NewsRepository(BaseRepository):
    async def create(
        self,
        title: str,
        content: str,
        author_id: int,
        author_name: str,
        content_type: str = "news",
    ) -> int:
        return await self.insert(
            """
            INSERT INTO news (title, content, author_id, author_name, content_type)
            VALUES (?, ?, ?, ?, ?)
            """,
            (title, content, author_id, author_name, content_type),
        )

    async def list_news(self):
        return await self.fetchall(
            "SELECT * FROM news WHERE content_type = 'news' ORDER BY pinned DESC, created_at DESC"
        )

    async def list_by_type(self, content_type: str):
        return await self.fetchall(
            "SELECT * FROM news WHERE content_type = ? ORDER BY pinned DESC, created_at DESC",
            (content_type,),
        )

    async def get_by_id(self, news_id: int):
        return await self.fetchone("SELECT * FROM news WHERE id = ?", (news_id,))

    async def update(
        self,
        news_id: int,
        *,
        title: str | None = None,
        content: str | None = None,
    ) -> None:
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

    async def delete(self, news_id: int) -> None:
        await self.execute("DELETE FROM news WHERE id = ?", (news_id,))

    async def toggle_pin(self, news_id: int) -> bool:
        await self.execute(
            "UPDATE news SET pinned = NOT pinned, updated_at = datetime('now') WHERE id = ?",
            (news_id,),
        )
        row = await self.get_by_id(news_id)
        return bool(row["pinned"]) if row else False

    async def count_all(self) -> int:
        row = await self.fetchone("SELECT COUNT(*) FROM news")
        return int(row[0]) if row else 0

    async def top_authors(self, limit: int = 5):
        return await self.fetchall(
            """
            SELECT author_id, author_name, COUNT(*) AS count
            FROM news
            GROUP BY author_id
            ORDER BY count DESC
            LIMIT ?
            """,
            (limit,),
        )

    async def latest(self):
        return await self.fetchone(
            "SELECT title, created_at FROM news ORDER BY created_at DESC LIMIT 1"
        )
