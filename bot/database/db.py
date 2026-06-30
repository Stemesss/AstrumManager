# -*- coding: utf-8 -*-
"""Асинхронная работа с SQLite через aiosqlite."""
import logging
import os

import aiosqlite

from bot.database.migrations import apply_pending_migrations
from bot.database.repositories import RepositoryRegistry

logger = logging.getLogger(__name__)


class Database:
    """Обёртка над aiosqlite для хранения данных пользователей."""

    def __init__(self, path: str) -> None:
        self._path = path
        self._conn: aiosqlite.Connection | None = None
        self.repositories = RepositoryRegistry.build(self)

    async def connect(self) -> None:
        """Открывает соединение и применяет все ожидающие миграции."""
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        self._conn = await aiosqlite.connect(self._path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await apply_pending_migrations(self._conn)
        await self._conn.commit()
        logger.info("База данных подключена: %s", self._path)

    async def close(self) -> None:
        """Закрывает соединение с базой данных."""
        if self._conn:
            await self._conn.close()
            logger.info("Соединение с базой данных закрыто")

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("База данных не подключена — вызовите connect() сначала")
        return self._conn

    async def ping(self) -> bool:
        """Проверяет доступность активного соединения с БД."""
        if self._conn is None:
            return False
        try:
            async with self.conn.execute("SELECT 1") as cur:
                row = await cur.fetchone()
            return bool(row and row[0] == 1)
        except Exception:
            logger.exception("Проверка доступности БД завершилась ошибкой")
            return False

    # ------------------------------------------------------------------ #
    # Методы работы с пользователями
    # ------------------------------------------------------------------ #

    async def get_user(self, telegram_id: int) -> aiosqlite.Row | None:
        """Возвращает запись пользователя по telegram_id или None."""
        return await self.repositories.users.get_by_telegram_id(telegram_id)

    async def upsert_user(
        self, telegram_id: int, username: str | None, first_name: str
    ) -> None:
        """Создаёт нового пользователя или обновляет его данные (last_seen)."""
        await self.repositories.users.upsert(telegram_id, username, first_name)

    async def get_role(self, telegram_id: int) -> str:
        """Возвращает роль пользователя. Участник по умолчанию."""
        return await self.repositories.users.get_role(telegram_id)

    async def set_role(self, telegram_id: int, role: str) -> None:
        """Устанавливает роль пользователя."""
        await self.repositories.users.set_role(telegram_id, role)

    async def set_game_nick(self, telegram_id: int, game_nick: str) -> None:
        """Устанавливает или обновляет игровой ник пользователя."""
        await self.repositories.users.set_game_nick(telegram_id, game_nick)

    async def get_days_in_clan(self, telegram_id: int) -> int:
        """Возвращает количество дней пользователя в клане (с момента регистрации)."""
        return await self.repositories.users.get_days_in_clan(telegram_id)

    async def get_all_users(self) -> list[aiosqlite.Row]:
        """Возвращает всех пользователей."""
        return await self.repositories.users.list_all()

    async def delete_user(self, telegram_id: int) -> None:
        """Удаляет пользователя и все связанные с ним данные."""
        await self.repositories.users.delete(telegram_id)

    async def season_reset(self) -> tuple[int, int]:
        """
        Создаёт резервную копию и сбрасывает сезонные данные:
        очищает журнал аудита, сохраняет пользователей, темы, новости, жалобы.
        Возвращает (users_count, logs_deleted).
        """
        async with self.conn.execute("SELECT COUNT(*) FROM users") as cur:
            users_count = int((await cur.fetchone())[0])
        logs_count = await self.repositories.audit.count_all()
        await self.repositories.audit.delete_all()
        return users_count, logs_count

    async def create_backup(self) -> str:
        """Копирует файл БД в data/backups/. Возвращает путь к резервной копии."""
        import datetime
        import shutil
        backup_dir = os.path.join(os.path.dirname(self._path), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"astrum_{ts}.db")
        shutil.copy2(self._path, backup_path)
        logger.info("Резервная копия БД создана: %s", backup_path)
        return backup_path

    # ------------------------------------------------------------------ #
    # Методы работы с новостями
    # ------------------------------------------------------------------ #

    async def create_news(
        self,
        title: str,
        content: str,
        author_id: int,
        author_name: str,
        content_type: str = "news",
    ) -> int:
        """Создаёт запись контента и возвращает её ID."""
        return await self.repositories.news.create(
            title, content, author_id, author_name, content_type
        )

    async def get_news_list(self) -> list[aiosqlite.Row]:
        """Возвращает новости типа 'news': закреплённые первыми, затем по дате."""
        return await self.repositories.news.list_news()

    async def get_news_list_by_type(self, content_type: str) -> list[aiosqlite.Row]:
        """Возвращает записи по типу контента: закреплённые первыми, затем по дате."""
        return await self.repositories.news.list_by_type(content_type)

    async def get_news_by_id(self, news_id: int) -> aiosqlite.Row | None:
        """Возвращает новость по ID или None."""
        return await self.repositories.news.get_by_id(news_id)

    async def update_news(
        self,
        news_id: int,
        *,
        title: str | None = None,
        content: str | None = None,
    ) -> None:
        """Обновляет заголовок и/или текст новости."""
        await self.repositories.news.update(news_id, title=title, content=content)

    async def delete_news(self, news_id: int) -> None:
        """Удаляет новость по ID."""
        await self.repositories.news.delete(news_id)

    async def toggle_news_pin(self, news_id: int) -> bool:
        """Переключает закрепление новости. Возвращает новое состояние (True = закреплено)."""
        return await self.repositories.news.toggle_pin(news_id)

    # ------------------------------------------------------------------ #
    # Методы работы с журналом аудита
    # ------------------------------------------------------------------ #

    async def add_audit_log(
        self,
        user_id: int,
        game_nick: str,
        role: str,
        action_type: str,
        description: str,
    ) -> int:
        """Добавляет запись в журнал аудита, возвращает её ID."""
        return await self.repositories.audit.add_log(
            user_id, game_nick, role, action_type, description
        )

    async def get_audit_page(
        self,
        page: int,
        per_page: int,
        action_types: list[str] | None = None,
    ) -> list[aiosqlite.Row]:
        """Возвращает страницу записей журнала, отсортированных от новых к старым."""
        return await self.repositories.audit.get_page(page, per_page, action_types)

    async def count_audit(
        self, action_types: list[str] | None = None
    ) -> int:
        """Возвращает общее число записей (с учётом фильтра по типу)."""
        return await self.repositories.audit.count(action_types)

    async def search_audit(
        self, query: str, per_page: int = 20
    ) -> list[aiosqlite.Row]:
        """
        Поиск записей:
        - формат дд.мм.гггг → ищем по created_at;
        - иначе             → по game_nick или action_type (LIKE).
        """
        return await self.repositories.audit.search(query, per_page)

    async def clear_audit_log(self) -> int:
        """Удаляет все записи журнала, возвращает количество удалённых строк."""
        return await self.repositories.audit.clear()

    # ------------------------------------------------------------------ #
    # Методы статистики
    # ------------------------------------------------------------------ #

    async def stats_top_active_users(self, limit: int = 10) -> list[aiosqlite.Row]:
        """Топ участников по активности (формула очков из audit_log)."""
        return await self.repositories.stats.top_active_users(limit)

    async def stats_count_news(self) -> int:
        """Общее количество новостей."""
        return await self.repositories.news.count_all()

    async def stats_news_by_author(self, limit: int = 5) -> list[aiosqlite.Row]:
        """Топ авторов новостей по количеству публикаций."""
        return await self.repositories.news.top_authors(limit)

    async def stats_news_latest(self) -> aiosqlite.Row | None:
        """Последняя опубликованная новость (заголовок + дата)."""
        return await self.repositories.news.latest()

    async def stats_content_by_user(
        self, action_type: str, limit: int = 5
    ) -> list[aiosqlite.Row]:
        """Топ участников по заданному типу действий (guide_create, screenshot_upload, event_create)."""
        return await self.repositories.stats.content_by_user(action_type, limit)

    async def stats_content_latest(self, action_type: str) -> aiosqlite.Row | None:
        """Последняя запись заданного типа из audit_log."""
        return await self.repositories.stats.content_latest(action_type)

    async def stats_count_action(self, action_type: str) -> int:
        """Количество записей конкретного action_type в audit_log."""
        return await self.repositories.stats.count_action(action_type)

    async def stats_user_activity(self, user_id: int) -> "aiosqlite.Row | None":
        """Очки и счётчики публикаций одного участника из журнала аудита."""
        return await self.repositories.stats.user_activity(user_id)

    async def stats_users_joined(self) -> tuple[int, int, int, int]:
        """(total, today, week, month) — сколько пользователей вступило."""
        total = await self.repositories.users.count_all()
        today = await self.repositories.users.count_joined_today()
        week = await self.repositories.users.count_joined_since_days(7)
        month = await self.repositories.users.count_joined_since_days(30)
        return total, today, week, month

    async def stats_users_by_day(self, days: int = 7) -> list[aiosqlite.Row]:
        """Количество новых пользователей за каждый из последних N дней."""
        return await self.repositories.users.count_by_day(days)

    async def _stats_best_since(self, period: str) -> aiosqlite.Row | None:
        """
        Участник с максимальными очками начиная с заданного периода.
        Формула: news_create=5, guide_create=10, screenshot_upload=2, event_create=8.
        """
        return await self.repositories.stats.best_since(period)

    # ── Сводные методы для карточек контента ───────────────────────────────

    async def _stats_content_bundle(
        self, action_type: str, top_limit: int
    ) -> tuple[int, list, "aiosqlite.Row | None"]:
        """Сводка для одного типа контента: всего + топ + последняя запись."""
        total = await self.stats_count_action(action_type)
        top = await self.stats_content_by_user(action_type, top_limit)
        latest = await self.stats_content_latest(action_type)
        return total, top, latest

    async def stats_news(
        self, top_limit: int = 3
    ) -> tuple[int, list, "aiosqlite.Row | None"]:
        """Сводка новостей: всего + топ авторов + последняя новость."""
        total = await self.stats_count_news()
        top = await self.stats_news_by_author(top_limit)
        latest = await self.stats_news_latest()
        return total, top, latest

    async def stats_guides(
        self, top_limit: int = 3
    ) -> tuple[int, list, "aiosqlite.Row | None"]:
        """Сводка гайдов."""
        return await self._stats_content_bundle("guide_create", top_limit)

    async def stats_screenshots(
        self, top_limit: int = 3
    ) -> tuple[int, list, "aiosqlite.Row | None"]:
        """Сводка скриншотов."""
        return await self._stats_content_bundle("screenshot_upload", top_limit)

    async def stats_events(
        self, top_limit: int = 3
    ) -> tuple[int, list, "aiosqlite.Row | None"]:
        """Сводка событий."""
        return await self._stats_content_bundle("event_create", top_limit)

    # ── Победитель по периоду ───────────────────────────────────────────────

    async def stats_best_of_month(self) -> aiosqlite.Row | None:
        """Победитель текущего календарного месяца."""
        return await self._stats_best_since("month")

    async def stats_best_of_week(self) -> aiosqlite.Row | None:
        """Победитель последних 7 дней."""
        return await self._stats_best_since("week")

    # ------------------------------------------------------------------ #
    # Методы работы с ветками форума (forum_topics)
    # ------------------------------------------------------------------ #

    async def topic_set(
        self,
        topic_name: str,
        thread_id: int | None,
        icon_custom_emoji_id: str | None = None,
    ) -> None:
        """Создаёт или обновляет запись ветки форума."""
        await self.repositories.topics.set(topic_name, thread_id, icon_custom_emoji_id)

    async def topic_get(self, topic_name: str) -> "aiosqlite.Row | None":
        """Возвращает строку ветки или None."""
        return await self.repositories.topics.get(topic_name)

    async def topic_list(self) -> list:
        """Список всех сохранённых веток."""
        return await self.repositories.topics.list_all()

    # ------------------------------------------------------------------ #
    # Методы работы с вложениями публикаций (publication_attachments)
    # ------------------------------------------------------------------ #

    async def attachment_save(
        self,
        publication_type: str,
        publication_id: int | None,
        file_id: str,
        file_unique_id: str | None,
        file_type: str,
        file_name: str | None = None,
    ) -> None:
        """Сохраняет file_id вложения, привязанного к публикации."""
        await self.repositories.attachments.save(
            publication_type,
            publication_id,
            file_id,
            file_unique_id,
            file_type,
            file_name,
        )

    async def attachments_by_publication(
        self,
        publication_type: str,
        publication_id: int | None,
    ) -> list:
        """Возвращает все вложения конкретной публикации."""
        return await self.repositories.attachments.list_by_publication(
            publication_type,
            publication_id,
        )

    # ------------------------------------------------------------------ #
    # Методы работы с жалобами и предложениями
    # ------------------------------------------------------------------ #

    async def complaint_create(
        self, user_id: int, user_name: str, title: str, content: str
    ) -> int:
        """Создаёт обращение и возвращает его ID."""
        return await self.repositories.complaints.create(
            user_id,
            user_name,
            title,
            content,
        )

    async def complaint_get(self, complaint_id: int) -> "aiosqlite.Row | None":
        """Возвращает обращение по ID или None."""
        return await self.repositories.complaints.get(complaint_id)

    async def complaint_list(self, limit: int = 200) -> list:
        """Возвращает все обращения, новейшие первыми."""
        return await self.repositories.complaints.list_all(limit)

    async def complaint_list_by_user(self, user_id: int) -> list:
        """Возвращает обращения конкретного пользователя."""
        return await self.repositories.complaints.list_by_user(user_id)

    async def complaint_set_status(self, complaint_id: int, status: str) -> None:
        """Обновляет статус обращения."""
        await self.repositories.complaints.set_status(complaint_id, status)

    async def complaint_set_reply(
        self, complaint_id: int, reply: str, replied_by: str
    ) -> None:
        """Сохраняет ответ администрации."""
        await self.repositories.complaints.set_reply(complaint_id, reply, replied_by)

    async def complaint_delete(self, complaint_id: int) -> None:
        """Удаляет обращение."""
        await self.repositories.complaints.delete(complaint_id)
