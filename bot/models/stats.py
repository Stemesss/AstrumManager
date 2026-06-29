# -*- coding: utf-8 -*-
"""Датаклассы для результатов статистики."""
from dataclasses import dataclass, field


@dataclass
class UserActivity:
    """Активность участника с итоговыми баллами."""
    user_id: int
    game_nick: str
    role: str
    score: int
    news_count: int
    guides_count: int
    screenshots_count: int
    events_count: int


@dataclass
class AuthorStat:
    """Имя автора и количество его материалов."""
    name: str
    count: int


@dataclass
class NewsStats:
    """Статистика раздела «Новости»."""
    total: int
    top_authors: list[AuthorStat] = field(default_factory=list)
    latest_title: str | None = None
    latest_date: str | None = None


@dataclass
class ContentStats:
    """Статистика контентного раздела из audit_log (гайды / скриншоты / события)."""
    total: int
    top_authors: list[AuthorStat] = field(default_factory=list)
    latest_author: str | None = None
    latest_date: str | None = None


@dataclass
class ClanGrowth:
    """Статистика прироста участников."""
    total: int
    today: int
    week: int
    month: int
    by_day: list[tuple[str, int]] = field(default_factory=list)
