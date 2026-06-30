# -*- coding: utf-8 -*-
"""Repository Layer для доступа к SQLite."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bot.database.repositories.attachment_repository import AttachmentRepository
from bot.database.repositories.audit_repository import AuditRepository
from bot.database.repositories.complaint_repository import ComplaintRepository
from bot.database.repositories.news_repository import NewsRepository
from bot.database.repositories.stats_repository import StatsRepository
from bot.database.repositories.topic_repository import TopicRepository
from bot.database.repositories.user_repository import UserRepository

if TYPE_CHECKING:
    from bot.database.db import Database


@dataclass(slots=True)
class RepositoryRegistry:
    users: UserRepository
    news: NewsRepository
    audit: AuditRepository
    stats: StatsRepository
    topics: TopicRepository
    attachments: AttachmentRepository
    complaints: ComplaintRepository

    @classmethod
    def build(cls, db: "Database") -> "RepositoryRegistry":
        return cls(
            users=UserRepository(db),
            news=NewsRepository(db),
            audit=AuditRepository(db),
            stats=StatsRepository(db),
            topics=TopicRepository(db),
            attachments=AttachmentRepository(db),
            complaints=ComplaintRepository(db),
        )


__all__ = [
    "AttachmentRepository",
    "AuditRepository",
    "ComplaintRepository",
    "NewsRepository",
    "RepositoryRegistry",
    "StatsRepository",
    "TopicRepository",
    "UserRepository",
]
