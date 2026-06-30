# -*- coding: utf-8 -*-
"""Репозиторий вложений публикаций."""
from __future__ import annotations

from bot.database.repositories.base import BaseRepository


class AttachmentRepository(BaseRepository):
    async def save(
        self,
        publication_type: str,
        publication_id: int | None,
        file_id: str,
        file_unique_id: str | None,
        file_type: str,
        file_name: str | None = None,
    ) -> None:
        await self.execute(
            """
            INSERT INTO publication_attachments
                (publication_type, publication_id, file_id, file_unique_id, file_type, file_name)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (publication_type, publication_id, file_id, file_unique_id, file_type, file_name),
        )

    async def list_by_publication(
        self,
        publication_type: str,
        publication_id: int | None,
    ):
        return await self.fetchall(
            """
            SELECT * FROM publication_attachments
            WHERE publication_type = ? AND publication_id IS ?
            ORDER BY id
            """,
            (publication_type, publication_id),
        )
