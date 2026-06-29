# -*- coding: utf-8 -*-
"""Сервис управления новостями клана."""
from bot.database.db import Database
from bot.models.news import NewsItem


class NewsService:
    """Бизнес-логика для работы с новостями."""

    def __init__(self, db: Database) -> None:
        self._db = db

    # ── Чтение ────────────────────────────────────────────────────────────

    async def get_list(self) -> list[NewsItem]:
        """Возвращает все новости: закреплённые первыми, затем по дате."""
        rows = await self._db.get_news_list()
        return [self._row_to_item(r) for r in rows]

    async def get_by_id(self, news_id: int) -> NewsItem | None:
        """Возвращает новость по ID или None."""
        row = await self._db.get_news_by_id(news_id)
        return self._row_to_item(row) if row else None

    # ── Запись ────────────────────────────────────────────────────────────

    async def create(
        self, title: str, content: str, author_id: int, author_name: str
    ) -> NewsItem:
        """Создаёт новость и возвращает её."""
        news_id = await self._db.create_news(title, content, author_id, author_name)
        item = await self.get_by_id(news_id)
        assert item is not None
        return item

    async def update_title(self, news_id: int, title: str) -> None:
        """Обновляет заголовок новости."""
        await self._db.update_news(news_id, title=title)

    async def update_content(self, news_id: int, content: str) -> None:
        """Обновляет текст новости."""
        await self._db.update_news(news_id, content=content)

    async def delete(self, news_id: int) -> None:
        """Удаляет новость."""
        await self._db.delete_news(news_id)

    async def toggle_pin(self, news_id: int) -> bool:
        """Переключает закрепление. Возвращает новое состояние (True = закреплено)."""
        return await self._db.toggle_news_pin(news_id)

    # ── Утилиты ───────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_item(row) -> NewsItem:
        return NewsItem(
            id=row["id"],
            title=row["title"],
            content=row["content"],
            author_id=row["author_id"],
            author_name=row["author_name"],
            pinned=bool(row["pinned"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
