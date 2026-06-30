# -*- coding: utf-8 -*-
"""Базовые инструменты Repository Layer."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import aiosqlite
    from bot.database.db import Database


class BaseRepository:
    """Базовый репозиторий с доступом к активному соединению."""

    def __init__(self, db: "Database") -> None:
        self._db = db

    @property
    def conn(self) -> "aiosqlite.Connection":
        return self._db.conn

    async def fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> Any:
        async with self.conn.execute(sql, params) as cur:
            return await cur.fetchone()

    async def fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[Any]:
        async with self.conn.execute(sql, params) as cur:
            return await cur.fetchall()

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        await self.conn.execute(sql, params)
        await self.conn.commit()

    async def insert(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        async with self.conn.execute(sql, params) as cur:
            row_id = cur.lastrowid
        await self.conn.commit()
        return int(row_id)
