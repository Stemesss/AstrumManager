# -*- coding: utf-8 -*-
"""
TopicService — управление Telegram Topics (ветками форума).

Использование в обработчиках:
    thread_id = await topic_service.get_thread_id("news")
    await bot.send_message(chat_id, text, message_thread_id=thread_id)
    # thread_id=None → обычный чат (не ветка)
"""
import logging

from aiogram import Bot

from bot.database.db import Database
from bot.models.topic import ALL_TOPIC_NAMES, ForumTopic

logger = logging.getLogger(__name__)


class TopicService:
    """CRUD для таблицы forum_topics + хелпер отправки в ветку."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def _to_model(self, row) -> ForumTopic:
        return ForumTopic(
            topic_name=row["topic_name"],
            message_thread_id=row["message_thread_id"],
            enabled=bool(row["enabled"]),
        )

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
        Возвращает message_thread_id для ветки или None.
        None означает «отправлять в обычный чат».
        """
        topic = await self.get_topic(topic_name)
        if topic is None or not topic.enabled:
            return None
        return topic.message_thread_id

    async def list_topics(self) -> list[ForumTopic]:
        """Список всех настроенных веток."""
        rows = await self._db.topic_list()
        configured = {r["topic_name"]: self._to_model(r) for r in rows}
        return [
            configured.get(name, ForumTopic(topic_name=name, message_thread_id=None))
            for name in ALL_TOPIC_NAMES
        ]

    async def safe_send(
        self,
        bot: Bot,
        chat_id: int,
        topic_name: str,
        text: str,
        **kwargs,
    ) -> bool:
        """
        Пробует отправить сообщение в ветку.
        Если бот не имеет доступа — логирует ошибку и возвращает False.
        Если ветка не настроена — отправляет в обычный чат.
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
                "safe_send: не удалось отправить в ветку '%s' (thread=%s): %s",
                topic_name, thread_id, exc,
            )
            return False
