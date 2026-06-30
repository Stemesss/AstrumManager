# -*- coding: utf-8 -*-
"""Сервис управления новостями и контентом клана."""
from bot.database.db import Database
from bot.database.repositories.news_repository import NewsRepository
from bot.models.news import NewsItem


class NewsService:
    """Бизнес-логика для работы с контентом (новости, события, гайды, скриншоты)."""

    def __init__(self, db: Database) -> None:
        self._news = NewsRepository(db)

    # ── Чтение ────────────────────────────────────────────────────────────

    async def get_list(self) -> list[NewsItem]:
        """Возвращает новости типа 'news': закреплённые первыми, затем по дате."""
        rows = await self._news.list_news()
        return [self._row_to_item(r) for r in rows]

    async def get_list_by_type(self, content_type: str) -> list[NewsItem]:
        """Возвращает записи указанного типа: закреплённые первыми, затем по дате."""
        rows = await self._news.list_by_type(content_type)
        return [self._row_to_item(r) for r in rows]

    async def get_by_id(self, news_id: int) -> NewsItem | None:
        """Возвращает запись по ID или None."""
        row = await self._news.get_by_id(news_id)
        return self._row_to_item(row) if row else None

    # ── Запись ────────────────────────────────────────────────────────────

    async def create(
        self,
        title: str,
        content: str,
        author_id: int,
        author_name: str,
        content_type: str = "news",
    ) -> NewsItem:
        """Создаёт запись контента и возвращает её."""
        news_id = await self._news.create(
            title, content, author_id, author_name, content_type
        )
        item = await self.get_by_id(news_id)
        assert item is not None
        return item

    async def update_title(self, news_id: int, title: str) -> None:
        """Обновляет заголовок записи."""
        await self._news.update(news_id, title=title)

    async def update_content(self, news_id: int, content: str) -> None:
        """Обновляет текст записи."""
        await self._news.update(news_id, content=content)

    async def delete(self, news_id: int) -> None:
        """Удаляет запись."""
        await self._news.delete(news_id)

    async def toggle_pin(self, news_id: int) -> bool:
        """Переключает закрепление. Возвращает новое состояние (True = закреплено)."""
        return await self._news.toggle_pin(news_id)

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
            content_type=row["content_type"] if "content_type" in row.keys() else "news",
        )
