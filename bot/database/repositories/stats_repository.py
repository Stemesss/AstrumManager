# -*- coding: utf-8 -*-
"""Репозиторий агрегированной статистики."""
from __future__ import annotations

from bot.database.repositories.base import BaseRepository


class StatsRepository(BaseRepository):
    async def top_active_users(self, limit: int = 10):
        return await self.fetchall(
            """
            SELECT
                al.user_id,
                COALESCE(u.game_nick, MAX(al.game_nick)) AS game_nick,
                MAX(al.role)                              AS role,
                SUM(CASE al.action_type
                    WHEN 'news_create'       THEN 5
                    WHEN 'guide_create'      THEN 10
                    WHEN 'screenshot_upload' THEN 2
                    WHEN 'event_create'      THEN 8
                    ELSE 0 END)                           AS score,
                SUM(CASE WHEN al.action_type = 'news_create'       THEN 1 ELSE 0 END) AS news_count,
                SUM(CASE WHEN al.action_type = 'guide_create'      THEN 1 ELSE 0 END) AS guides_count,
                SUM(CASE WHEN al.action_type = 'screenshot_upload' THEN 1 ELSE 0 END) AS screenshots_count,
                SUM(CASE WHEN al.action_type = 'event_create'      THEN 1 ELSE 0 END) AS events_count
            FROM audit_log al
            LEFT JOIN users u ON u.telegram_id = al.user_id
            WHERE al.action_type IN ('news_create','guide_create','screenshot_upload','event_create')
            GROUP BY al.user_id
            ORDER BY score DESC
            LIMIT ?
            """,
            (limit,),
        )

    async def content_by_user(self, action_type: str, limit: int = 5):
        return await self.fetchall(
            """
            SELECT al.user_id,
                   COALESCE(u.game_nick, MAX(al.game_nick)) AS game_nick,
                   COUNT(*)                                  AS count
            FROM audit_log al
            LEFT JOIN users u ON u.telegram_id = al.user_id
            WHERE al.action_type = ?
            GROUP BY al.user_id
            ORDER BY count DESC
            LIMIT ?
            """,
            (action_type, limit),
        )

    async def content_latest(self, action_type: str):
        return await self.fetchone(
            "SELECT game_nick, description, created_at"
            " FROM audit_log WHERE action_type = ?"
            " ORDER BY id DESC LIMIT 1",
            (action_type,),
        )

    async def count_action(self, action_type: str) -> int:
        row = await self.fetchone(
            "SELECT COUNT(*) FROM audit_log WHERE action_type = ?",
            (action_type,),
        )
        return int(row[0]) if row else 0

    async def user_activity(self, user_id: int):
        return await self.fetchone(
            """
            SELECT
                SUM(CASE action_type
                    WHEN 'news_create'       THEN 5
                    WHEN 'guide_create'      THEN 10
                    WHEN 'screenshot_upload' THEN 2
                    WHEN 'event_create'      THEN 8
                    ELSE 0 END)                                                         AS score,
                SUM(CASE WHEN action_type = 'news_create'       THEN 1 ELSE 0 END)     AS news_count,
                SUM(CASE WHEN action_type = 'guide_create'      THEN 1 ELSE 0 END)     AS guides_count,
                SUM(CASE WHEN action_type = 'screenshot_upload' THEN 1 ELSE 0 END)     AS screenshots_count,
                SUM(CASE WHEN action_type = 'event_create'      THEN 1 ELSE 0 END)     AS events_count
            FROM audit_log
            WHERE user_id = ?
            """,
            (user_id,),
        )

    async def best_since(self, since_expr: str):
        sql = f"""
        SELECT
            al.user_id,
            COALESCE(u.game_nick, MAX(al.game_nick)) AS game_nick,
            MAX(al.role)                              AS role,
            SUM(CASE al.action_type
                WHEN 'news_create'       THEN 5
                WHEN 'guide_create'      THEN 10
                WHEN 'screenshot_upload' THEN 2
                WHEN 'event_create'      THEN 8
                ELSE 0 END)                           AS score,
            SUM(CASE WHEN al.action_type = 'news_create'       THEN 1 ELSE 0 END) AS news_count,
            SUM(CASE WHEN al.action_type = 'guide_create'      THEN 1 ELSE 0 END) AS guides_count,
            SUM(CASE WHEN al.action_type = 'screenshot_upload' THEN 1 ELSE 0 END) AS screenshots_count,
            SUM(CASE WHEN al.action_type = 'event_create'      THEN 1 ELSE 0 END) AS events_count
        FROM audit_log al
        LEFT JOIN users u ON u.telegram_id = al.user_id
        WHERE al.action_type IN ('news_create','guide_create','screenshot_upload','event_create')
          AND al.created_at >= {since_expr}
        GROUP BY al.user_id
        ORDER BY score DESC
        LIMIT 1
        """
        return await self.fetchone(sql)
