# -*- coding: utf-8 -*-
"""
TopicService — управление Telegram Topics (ветками форума).

Использование в обработчиках:
    await topic_service.publish(bot, "news", text)
    # thread_id=None → обычный чат (не ветка), без ошибки
"""
import logging

from aiogram import Bot
from aiogram.types import InputMediaPhoto

from bot.database.db import Database
from bot.models.topic import ALL_TOPIC_NAMES, DEFAULT_THREAD_IDS, TOPIC_LABELS, ForumTopic

logger = logging.getLogger(__name__)


class TopicService:
    """CRUD для таблицы forum_topics + публикация в нужную ветку."""

    def __init__(self, db: Database, chat_id: int) -> None:
        self._db = db
        self._chat_id = chat_id

    @property
    def chat_id(self) -> int:
        return self._chat_id

    # ── Конвертер ─────────────────────────────────────────────────────────────

    def _to_model(self, row) -> ForumTopic:
        return ForumTopic(
            topic_name=row["topic_name"],
            message_thread_id=row["message_thread_id"],
            enabled=bool(row["enabled"]),
        )

    # ── CRUD ──────────────────────────────────────────────────────────────────

    async def set_topic(self, topic_name: str, thread_id: int | None) -> None:
        """Сохраняет (или обновляет) message_thread_id для ветки."""
        await self._db.topic_set(topic_name, thread_id)
        logger.info("Ветка '%s' → thread_id=%s", topic_name, thread_id)

    async def get_topic(self, topic_name: str) -> ForumTopic | None:
        """Возвращает ForumTopic или None если ветка не настроена."""
        row = await self._db.topic_get(topic_name)
        return self._to_model(row) if row else None

    async def get_thread_id(self, topic_name: str) -> int | None:
        """
        Возвращает message_thread_id или None.
        None → публиковать в основной чат (без ошибки).
        """
        topic = await self.get_topic(topic_name)
        if topic is None or not topic.enabled:
            return None
        return topic.message_thread_id

    async def list_topics(self) -> list[ForumTopic]:
        """Список всех тем (из БД + заглушки для ненастроенных)."""
        rows = await self._db.topic_list()
        configured = {r["topic_name"]: self._to_model(r) for r in rows}
        return [
            configured.get(name, ForumTopic(topic_name=name, message_thread_id=None))
            for name in ALL_TOPIC_NAMES
        ]

    # ── Начальный посев данных ────────────────────────────────────────────────

    async def seed_default_topics(self) -> None:
        """
        Заполняет forum_topics значениями по умолчанию.
        Пропускает темы, уже настроенные администратором через панель.
        """
        for name, thread_id in DEFAULT_THREAD_IDS.items():
            existing = await self._db.topic_get(name)
            if existing is None:
                await self._db.topic_set(name, thread_id)
                logger.info("Посев: ветка '%s' → thread_id=%d", name, thread_id)

    # ── Публикация ────────────────────────────────────────────────────────────

    async def publish(
        self,
        bot: Bot,
        topic_name: str,
        text: str,
        **kwargs,
    ) -> bool:
        """
        Публикует текстовое сообщение в нужную ветку (или основной чат).
        Возвращает True при успехе, False при ошибке доступа.
        """
        thread_id = await self.get_thread_id(topic_name)
        label = TOPIC_LABELS.get(topic_name, topic_name)
        try:
            await bot.send_message(
                chat_id=self._chat_id,
                text=text,
                message_thread_id=thread_id,
                **kwargs,
            )
            logger.info(
                "Публикация '%s' (thread=%s) → chat %s", label, thread_id, self._chat_id
            )
            return True
        except Exception as exc:
            logger.warning(
                "Не удалось опубликовать в ветку '%s' (thread=%s, chat=%s): %s",
                label, thread_id, self._chat_id, exc,
            )
            return False

    async def publish_photo(
        self,
        bot: Bot,
        topic_name: str,
        photo: str,
        caption: str | None = None,
        **kwargs,
    ) -> bool:
        """Публикует фото в нужную ветку."""
        thread_id = await self.get_thread_id(topic_name)
        label = TOPIC_LABELS.get(topic_name, topic_name)
        try:
            await bot.send_photo(
                chat_id=self._chat_id,
                photo=photo,
                caption=caption,
                message_thread_id=thread_id,
                **kwargs,
            )
            return True
        except Exception as exc:
            logger.warning(
                "Не удалось опубликовать фото в ветку '%s': %s", label, exc
            )
            return False

    async def publish_media_group(
        self,
        bot: Bot,
        topic_name: str,
        media: list[InputMediaPhoto],
        **kwargs,
    ) -> bool:
        """Публикует медиагруппу в нужную ветку."""
        thread_id = await self.get_thread_id(topic_name)
        label = TOPIC_LABELS.get(topic_name, topic_name)
        try:
            await bot.send_media_group(
                chat_id=self._chat_id,
                media=media,
                message_thread_id=thread_id,
                **kwargs,
            )
            return True
        except Exception as exc:
            logger.warning(
                "Не удалось опубликовать медиагруппу в ветку '%s': %s", label, exc
            )
            return False

    async def safe_send(
        self,
        bot: Bot,
        chat_id: int,
        topic_name: str,
        text: str,
        **kwargs,
    ) -> bool:
        """
        Отправка в произвольный chat_id (не в self._chat_id).
        Используется для тестов / специальных сценариев.
        """
        thread_id = await self.get_thread_id(topic_name)
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                message_thread_id=thread_id,
                **kwargs,
            )
            return True
        except Exception as exc:
            logger.warning(
                "safe_send: ветка '%s' (thread=%s, chat=%s): %s",
                topic_name, thread_id, chat_id, exc,
            )
            return False
