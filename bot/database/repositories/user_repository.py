# -*- coding: utf-8 -*-
"""Репозиторий пользователей."""
from __future__ import annotations

from bot.database.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    async def get_by_id(self, user_id: int):
        return await self.get_by_telegram_id(user_id)

    async def get_by_telegram_id(self, telegram_id: int):
        return await self.fetchone(
            "SELECT * FROM users WHERE telegram_id = ?",
            (telegram_id,),
        )

    async def get_by_username(self, username: str):
        normalized = username.lstrip("@").strip()
        if not normalized:
            return None
        return await self.fetchone(
            "SELECT * FROM users WHERE lower(username) = lower(?)",
            (normalized,),
        )

    async def get_by_nickname(
        self,
        nickname: str,
        *,
        exclude_telegram_id: int | None = None,
    ):
        normalized = nickname.strip()
        if not normalized:
            return None
        sql = (
            "SELECT * FROM users "
            "WHERE trim(COALESCE(game_nick, '')) != '' "
            "AND lower(trim(game_nick)) = lower(trim(?))"
        )
        params: tuple = (normalized,)
        if exclude_telegram_id is not None:
            sql += " AND telegram_id != ?"
            params = (normalized, exclude_telegram_id)
        return await self.fetchone(sql, params)

    async def search_users(self, query: str, limit: int = 50):
        normalized = query.strip()
        if not normalized:
            return []
        like = f"%{normalized.lower()}%"
        if normalized.isdigit():
            return await self.fetchall(
                """
                SELECT *
                FROM users
                WHERE telegram_id = ?
                   OR lower(COALESCE(username, '')) LIKE ?
                   OR lower(first_name) LIKE ?
                   OR lower(COALESCE(game_nick, '')) LIKE ?
                ORDER BY role ASC, last_seen DESC
                LIMIT ?
                """,
                (int(normalized), like, like, like, limit),
            )
        return await self.fetchall(
            """
            SELECT *
            FROM users
            WHERE lower(COALESCE(username, '')) LIKE ?
               OR lower(first_name) LIKE ?
               OR lower(COALESCE(game_nick, '')) LIKE ?
            ORDER BY role ASC, last_seen DESC
            LIMIT ?
            """,
            (like, like, like, limit),
        )

    async def upsert(self, telegram_id: int, username: str | None, first_name: str) -> None:
        await self.execute(
            """
            INSERT INTO users (telegram_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username   = excluded.username,
                first_name = excluded.first_name,
                last_seen  = datetime('now')
            """,
            (telegram_id, username, first_name),
        )

    async def get_role(self, telegram_id: int) -> str:
        row = await self.get_by_telegram_id(telegram_id)
        return row["role"] if row else "Участник"

    async def set_role(self, telegram_id: int, role: str) -> None:
        await self.execute(
            "UPDATE users SET role = ? WHERE telegram_id = ?",
            (role, telegram_id),
        )

    async def set_game_nick(self, telegram_id: int, game_nick: str) -> None:
        await self.execute(
            "UPDATE users SET game_nick = ? WHERE telegram_id = ?",
            (game_nick, telegram_id),
        )

    async def get_days_in_clan(self, telegram_id: int) -> int:
        row = await self.fetchone(
            "SELECT CAST(julianday('now') - julianday(created_at) AS INTEGER) FROM users WHERE telegram_id = ?",
            (telegram_id,),
        )
        return int(row[0]) if row and row[0] is not None else 0

    async def list_all(self):
        return await self.fetchall("SELECT * FROM users ORDER BY last_seen DESC")

    async def delete(self, telegram_id: int) -> None:
        await self.conn.execute("DELETE FROM users WHERE telegram_id = ?", (telegram_id,))
        await self.conn.execute("DELETE FROM audit_log WHERE user_id = ?", (telegram_id,))
        await self.conn.execute("DELETE FROM complaints WHERE user_id = ?", (telegram_id,))
        await self.conn.commit()

    async def count_all(self) -> int:
        row = await self.fetchone("SELECT COUNT(*) FROM users")
        return int(row[0]) if row else 0

    async def count_joined_today(self) -> int:
        row = await self.fetchone(
            "SELECT COUNT(*) FROM users WHERE date(created_at) = date('now')"
        )
        return int(row[0]) if row else 0

    async def count_joined_since_days(self, days: int) -> int:
        row = await self.fetchone(
            "SELECT COUNT(*) FROM users WHERE created_at >= datetime('now', ? || ' days')",
            (f"-{days}",),
        )
        return int(row[0]) if row else 0

    async def count_by_day(self, days: int = 7):
        return await self.fetchall(
            """
            SELECT date(created_at) AS day, COUNT(*) AS cnt
            FROM users
            WHERE created_at >= datetime('now', ? || ' days')
            GROUP BY day
            ORDER BY day
            """,
            (f"-{days - 1}",),
        )
