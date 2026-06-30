# -*- coding: utf-8 -*-
"""Репозиторий форумных тем."""
from __future__ import annotations

from bot.database.repositories.base import BaseRepository


class TopicRepository(BaseRepository):
    async def set(
        self,
        topic_name: str,
        thread_id: int | None,
        icon_custom_emoji_id: str | None = None,
    ) -> None:
        await self.execute(
            """
            INSERT INTO forum_topics (topic_name, message_thread_id, icon_custom_emoji_id)
            VALUES (?, ?, ?)
            ON CONFLICT(topic_name) DO UPDATE SET
                message_thread_id    = excluded.message_thread_id,
                icon_custom_emoji_id = COALESCE(excluded.icon_custom_emoji_id, forum_topics.icon_custom_emoji_id)
            """,
            (topic_name, thread_id, icon_custom_emoji_id),
        )

    async def get(self, topic_name: str):
        return await self.fetchone(
            "SELECT * FROM forum_topics WHERE topic_name = ?",
            (topic_name,),
        )

    async def list_all(self):
        return await self.fetchall("SELECT * FROM forum_topics ORDER BY id")
