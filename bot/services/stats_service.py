# -*- coding: utf-8 -*-
"""
Сервис статистики AstrumManager.

Формула активности:
  📰 news_create       = 5 очков
  📚 guide_create      = 10 очков
  📸 screenshot_upload = 2 очка
  📅 event_create      = 8 очков
"""
from datetime import date, timedelta

from bot.database.db import Database
from bot.models.audit import AuditAction
from bot.models.stats import AuthorStat, ClanGrowth, ContentStats, NewsStats, UserActivity


class StatsService:
    """Вычисляет всю статистику напрямую из БД."""

    def __init__(self, db: Database) -> None:
        self._db = db

    # ─────────────────────────────────────────────────────────────────────────
    # Активность участников
    # ─────────────────────────────────────────────────────────────────────────

    async def top_active_users(self, limit: int = 10) -> list[UserActivity]:
        """Возвращает список участников, отсортированных по очкам (убывание)."""
        rows = await self._db.stats_top_active_users(limit)
        return [
            UserActivity(
                user_id=r["user_id"],
                game_nick=r["game_nick"] or "—",
                role=r["role"],
                score=int(r["score"] or 0),
                news_count=int(r["news_count"] or 0),
                guides_count=int(r["guides_count"] or 0),
                screenshots_count=int(r["screenshots_count"] or 0),
                events_count=int(r["events_count"] or 0),
            )
            for r in rows
        ]

    async def most_active_user(self) -> UserActivity | None:
        """Возвращает участника с максимальной активностью или None."""
        result = await self.top_active_users(limit=1)
        return result[0] if result else None

    # ─────────────────────────────────────────────────────────────────────────
    # Новости
    # ─────────────────────────────────────────────────────────────────────────

    async def news_stats(self) -> NewsStats:
        """Статистика из таблицы news."""
        total_rows = await self._db.stats_count_news()
        author_rows = await self._db.stats_news_by_author(limit=5)
        latest = await self._db.stats_news_latest()

        return NewsStats(
            total=total_rows,
            top_authors=[AuthorStat(name=r["author_name"], count=r["count"]) for r in author_rows],
            latest_title=latest["title"] if latest else None,
            latest_date=latest["created_at"] if latest else None,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Контент из audit_log (гайды / скриншоты / события)
    # ─────────────────────────────────────────────────────────────────────────

    async def _content_stats(self, create_action: str) -> ContentStats:
        total = await self._db.stats_count_action(create_action)
        top_rows = await self._db.stats_content_by_user(create_action, limit=5)
        latest = await self._db.stats_content_latest(create_action)

        return ContentStats(
            total=total,
            top_authors=[AuthorStat(name=r["game_nick"] or "—", count=r["count"]) for r in top_rows],
            latest_author=latest["game_nick"] if latest else None,
            latest_date=latest["created_at"] if latest else None,
        )

    async def guides_stats(self) -> ContentStats:
        return await self._content_stats(AuditAction.GUIDE_CREATE)

    async def screenshots_stats(self) -> ContentStats:
        return await self._content_stats(AuditAction.SCREENSHOT_UPLOAD)

    async def events_stats(self) -> ContentStats:
        return await self._content_stats(AuditAction.EVENT_CREATE)

    # ─────────────────────────────────────────────────────────────────────────
    # Рост клана
    # ─────────────────────────────────────────────────────────────────────────

    async def clan_growth(self, chart_days: int = 7) -> ClanGrowth:
        """Динамика прироста участников."""
        total, today, week, month = await self._db.stats_users_joined()
        raw_rows = await self._db.stats_users_by_day(chart_days)

        # Заполняем пропущенные дни нулями
        db_map: dict[str, int] = {r["day"]: r["cnt"] for r in raw_rows}
        cur_date = date.today()
        by_day: list[tuple[str, int]] = []
        for i in range(chart_days - 1, -1, -1):
            d = cur_date - timedelta(days=i)
            key = d.strftime("%Y-%m-%d")
            by_day.append((key, db_map.get(key, 0)))

        return ClanGrowth(
            total=total,
            today=today,
            week=week,
            month=month,
            by_day=by_day,
        )
