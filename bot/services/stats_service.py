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
from bot.database.repositories.news_repository import NewsRepository
from bot.database.repositories.stats_repository import StatsRepository
from bot.database.repositories.user_repository import UserRepository
from bot.models.audit import AuditAction
from bot.models.stats import AuthorStat, ClanGrowth, ContentStats, NewsStats, UserActivity


class StatsService:
    """Вычисляет всю статистику напрямую из БД."""

    def __init__(self, db: Database) -> None:
        self._stats = StatsRepository(db)
        self._news = NewsRepository(db)
        self._users = UserRepository(db)

    # ─────────────────────────────────────────────────────────────────────────
    # Активность участников
    # ─────────────────────────────────────────────────────────────────────────

    async def top_active_users(self, limit: int = 10) -> list[UserActivity]:
        """Возвращает список участников, отсортированных по очкам (убывание)."""
        rows = await self._stats.top_active_users(limit)
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
        """Возвращает участника с максимальной активностью за всё время или None."""
        result = await self.top_active_users(limit=1)
        return result[0] if result else None

    @staticmethod
    def _row_to_activity(row) -> UserActivity:
        """Преобразует строку БД (stats_best_since) в UserActivity."""
        return UserActivity(
            user_id=int(row["user_id"]),
            game_nick=row["game_nick"] or "—",
            role=row["role"],
            score=int(row["score"] or 0),
            news_count=int(row["news_count"] or 0),
            guides_count=int(row["guides_count"] or 0),
            screenshots_count=int(row["screenshots_count"] or 0),
            events_count=int(row["events_count"] or 0),
        )

    async def best_of_month(self) -> UserActivity | None:
        """Участник с максимальными очками за текущий календарный месяц."""
        row = await self._stats.best_since("strftime('%Y-%m-01', 'now')")
        return self._row_to_activity(row) if row else None

    async def best_of_week(self) -> UserActivity | None:
        """Участник с максимальными очками за последние 7 дней."""
        row = await self._stats.best_since("datetime('now', '-6 days')")
        return self._row_to_activity(row) if row else None

    # ─────────────────────────────────────────────────────────────────────────
    # Новости
    # ─────────────────────────────────────────────────────────────────────────

    async def news_stats(self) -> NewsStats:
        """Статистика из таблицы news."""
        total_rows = await self._news.count_all()
        author_rows = await self._news.top_authors(limit=5)
        latest = await self._news.latest()

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
        total = await self._stats.count_action(create_action)
        top_rows = await self._stats.content_by_user(create_action, limit=5)
        latest = await self._stats.content_latest(create_action)

        return ContentStats(
            total=total,
            top_authors=[AuthorStat(name=r["game_nick"] or "—", count=r["count"]) for r in top_rows],
            latest_author=latest["game_nick"] if latest else None,
            latest_description=latest["description"] if latest else None,
            latest_date=latest["created_at"] if latest else None,
        )

    async def guides_stats(self) -> ContentStats:
        return await self._content_stats(AuditAction.GUIDE_CREATE)

    async def screenshots_stats(self) -> ContentStats:
        return await self._content_stats(AuditAction.SCREENSHOT_UPLOAD)

    async def events_stats(self) -> ContentStats:
        return await self._content_stats(AuditAction.EVENT_CREATE)

    # Публичные псевдонимы с коротким именем (для handlers/statistics.py)
    async def news(self) -> NewsStats:
        """Статистика новостей (псевдоним news_stats, top=3)."""
        total = await self._news.count_all()
        top_rows = await self._news.top_authors(limit=3)
        latest = await self._news.latest()
        return NewsStats(
            total=total,
            top_authors=[AuthorStat(name=r["author_name"], count=r["count"]) for r in top_rows],
            latest_title=latest["title"] if latest else None,
            latest_date=latest["created_at"] if latest else None,
        )

    async def guides(self) -> ContentStats:
        """Статистика гайдов (top=3)."""
        total = await self._stats.count_action(AuditAction.GUIDE_CREATE)
        top_rows = await self._stats.content_by_user(AuditAction.GUIDE_CREATE, limit=3)
        latest = await self._stats.content_latest(AuditAction.GUIDE_CREATE)
        return ContentStats(
            total=total,
            top_authors=[AuthorStat(name=r["game_nick"] or "—", count=r["count"]) for r in top_rows],
            latest_description=latest["description"] if latest else None,
            latest_date=latest["created_at"] if latest else None,
        )

    async def screenshots(self) -> ContentStats:
        """Статистика скриншотов (top=3)."""
        total = await self._stats.count_action(AuditAction.SCREENSHOT_UPLOAD)
        top_rows = await self._stats.content_by_user(AuditAction.SCREENSHOT_UPLOAD, limit=3)
        latest = await self._stats.content_latest(AuditAction.SCREENSHOT_UPLOAD)
        return ContentStats(
            total=total,
            top_authors=[AuthorStat(name=r["game_nick"] or "—", count=r["count"]) for r in top_rows],
            latest_date=latest["created_at"] if latest else None,
        )

    async def events(self) -> ContentStats:
        """Статистика событий (top=3)."""
        total = await self._stats.count_action(AuditAction.EVENT_CREATE)
        top_rows = await self._stats.content_by_user(AuditAction.EVENT_CREATE, limit=3)
        latest = await self._stats.content_latest(AuditAction.EVENT_CREATE)
        return ContentStats(
            total=total,
            top_authors=[AuthorStat(name=r["game_nick"] or "—", count=r["count"]) for r in top_rows],
            latest_description=latest["description"] if latest else None,
            latest_date=latest["created_at"] if latest else None,
        )

    async def user_activity(self, user_id: int) -> dict:
        """Статистика публикаций и очки активности одного участника."""
        row = await self._stats.user_activity(user_id)
        if not row:
            return {"score": 0, "news": 0, "guides": 0, "screenshots": 0, "events": 0}
        return {
            "score":       int(row["score"] or 0),
            "news":        int(row["news_count"] or 0),
            "guides":      int(row["guides_count"] or 0),
            "screenshots": int(row["screenshots_count"] or 0),
            "events":      int(row["events_count"] or 0),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Рост клана
    # ─────────────────────────────────────────────────────────────────────────

    async def clan_growth(self, chart_days: int = 7) -> ClanGrowth:
        """Динамика прироста участников."""
        total = await self._users.count_all()
        today = await self._users.count_joined_today()
        week = await self._users.count_joined_since_days(7)
        month = await self._users.count_joined_since_days(30)
        raw_rows = await self._users.count_by_day(chart_days)

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
