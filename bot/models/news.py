# -*- coding: utf-8 -*-
"""Модель новости клана."""
from dataclasses import dataclass


@dataclass
class NewsItem:
    """Новость клана Astrum."""
    id: int
    title: str
    content: str
    author_id: int
    author_name: str
    pinned: bool
    created_at: str
    updated_at: str
