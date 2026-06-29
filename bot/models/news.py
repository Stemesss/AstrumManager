# -*- coding: utf-8 -*-
"""Модель новости и контент-записи клана."""
from dataclasses import dataclass, field


@dataclass
class NewsItem:
    """Запись любого типа контента (новость, событие, гайд, скриншот)."""
    id: int
    title: str
    content: str
    author_id: int
    author_name: str
    pinned: bool
    created_at: str
    updated_at: str
    content_type: str = field(default="news")
