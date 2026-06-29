# -*- coding: utf-8 -*-
"""
TopicService — единая точка управления системными форумными темами.

Публичный API:
    # Получение данных (без обращения к Telegram API)
    await topic_service.get_topic(key)        → ForumTopic | None
    await topic_service.get_thread_id(key)    → int | None
    await topic_service.list_topics()         → list[ForumTopic]

    # Создание / синхронизация (обращается к Telegram API)
    await topic_service.create_system_topic(bot, key)  → int | None
    await topic_service.sync_all_topics(bot)           → SyncReport (dict)

    # Быстрая проверка при запуске (без API)
    await topic_service.check_topics_startup()  → list[str]  # ключи отсутствующих тем

    # Публикация контента
    await topic_service.publish(bot, key, text)
    await topic_service.publish_with_attachments(bot, key, text, attachments)
"""
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import InputMediaPhoto, InputMediaVideo

from bot.database.db import Database
from bot.models.topic import (
    ALL_TOPIC_NAMES,
    DEFAULT_THREAD_IDS,
    TOPIC_LABELS,
    TOPIC_REGISTRY,
    ForumTopic,
)

logger = logging.getLogger(__name__)


class TopicService:
    """Единый менеджер системных форумных тем."""

    def __init__(self, db: Database, chat_id: int) -> None:
        self._db = db
        self._chat_id = chat_id

    @property
    def chat_id(self) -> int:
        return self._chat_id

    # ── Внутренние вспомогательные методы ─────────────────────────────────────

    def _to_model(self, row) -> ForumTopic:
        """Конвертирует строку БД в объект ForumTopic."""
        row_dict = dict(row)
        return ForumTopic(
            topic_name=row_dict["topic_name"],
            message_thread_id=row_dict["message_thread_id"],
            enabled=bool(row_dict["enabled"]),
            icon_custom_emoji_id=row_dict.get("icon_custom_emoji_id"),
        )

    # ── CRUD ──────────────────────────────────────────────────────────────────

    async def set_topic(
        self,
        topic_name: str,
        thread_id: int | None,
        icon_custom_emoji_id: str | None = None,
    ) -> None:
        """Сохраняет (или обновляет) параметры ветки в БД."""
        await self._db.topic_set(topic_name, thread_id, icon_custom_emoji_id)
        logger.info("Ветка '%s' → thread_id=%s emoji=%s", topic_name, thread_id, icon_custom_emoji_id)

    async def get_topic(self, topic_name: str) -> ForumTopic | None:
        """Возвращает ForumTopic из БД или None."""
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
        """Список всех тем в порядке реестра (из БД + заглушки для ненастроенных)."""
        rows = await self._db.topic_list()
        configured = {r["topic_name"]: self._to_model(r) for r in rows}
        return [
            configured.get(name, ForumTopic(topic_name=name, message_thread_id=None))
            for name in ALL_TOPIC_NAMES
        ]

    # ── Начальный посев данных ────────────────────────────────────────────────

    async def seed_default_topics(self) -> None:
        """
        Заполняет forum_topics предустановленными значениями при первом запуске.
        Пропускает темы, уже настроенные администратором.
        """
        for name, thread_id in DEFAULT_THREAD_IDS.items():
            existing = await self._db.topic_get(name)
            if existing is None:
                await self._db.topic_set(name, thread_id)
                logger.info("Посев: ветка '%s' → thread_id=%d", name, thread_id)

    # ── Управление темами через Telegram API ───────────────────────────────────

    async def create_system_topic(self, bot: Bot, topic_key: str) -> int | None:
        """
        Создаёт форумную тему в Telegram и сохраняет thread_id в БД.

        Требует, чтобы бот имел права can_manage_topics в группе.
        Возвращает thread_id созданной темы или None при ошибке.

        Ограничение Telegram: icon_color нельзя изменить после создания.
        """
        defn = TOPIC_REGISTRY.get(topic_key)
        if not defn:
            logger.error("create_system_topic: неизвестный ключ '%s'", topic_key)
            return None
        try:
            tg_topic = await bot.create_forum_topic(
                chat_id=self._chat_id,
                name=defn.name,
                icon_color=defn.icon_color,
            )
            thread_id = tg_topic.message_thread_id
            await self.set_topic(topic_key, thread_id)
            logger.info("Создана тема '%s' → thread_id=%d", topic_key, thread_id)
            return thread_id
        except TelegramForbiddenError as exc:
            logger.warning("create_system_topic '%s': нет прав → %s", topic_key, exc)
            return None
        except TelegramBadRequest as exc:
            logger.error("create_system_topic '%s': ошибка API → %s", topic_key, exc)
            return None
        except Exception as exc:
            logger.error("create_system_topic '%s': неожиданная ошибка → %s", topic_key, exc)
            return None

    async def sync_all_topics(self, bot: Bot) -> dict:
        """
        Синхронизирует все системные темы с Telegram.

        Алгоритм для каждой темы из реестра:
        - Если thread_id настроен → вызывает editForumTopic для проверки/исправления имени.
          Ограничение Telegram: editForumTopic меняет name и icon_custom_emoji_id,
          но НЕ icon_color (цвет задаётся только при создании).
        - Если thread_id не настроен → вызывает create_system_topic.

        Возвращает словарь-отчёт:
        {
          "created":      [keys],   # созданы новые темы
          "name_fixed":   [keys],   # исправлены названия
          "ok":           [keys],   # всё в порядке
          "missing":      [keys],   # тема удалена из Telegram (thread не найден)
          "no_permission":[keys],   # нет прав (can_manage_topics)
          "errors":       {key: msg},
        }

        Синхронизация безопасна: не удаляет и не пересоздаёт темы.
        """
        report: dict = {
            "created":       [],
            "name_fixed":    [],
            "ok":            [],
            "missing":       [],
            "no_permission": [],
            "errors":        {},
        }

        for topic_key, defn in TOPIC_REGISTRY.items():
            topic     = await self.get_topic(topic_key)
            thread_id = topic.message_thread_id if (topic and topic.enabled) else None

            if thread_id is None:
                # Тема не настроена — создаём
                new_id = await self.create_system_topic(bot, topic_key)
                if new_id is not None:
                    report["created"].append(topic_key)
                else:
                    report["no_permission"].append(topic_key)
            else:
                # Тема настроена — проверяем/исправляем через editForumTopic
                try:
                    await bot.edit_forum_topic(
                        chat_id=self._chat_id,
                        message_thread_id=thread_id,
                        name=defn.name,
                    )
                    # Успешный edit означает, что имя было другим и теперь исправлено
                    report["name_fixed"].append(topic_key)
                    logger.info("Исправлено имя темы '%s' #%d", topic_key, thread_id)
                except TelegramBadRequest as exc:
                    msg = str(exc)
                    if "TOPIC_NOT_MODIFIED" in msg:
                        # Имя и так совпадает — всё в порядке
                        report["ok"].append(topic_key)
                    elif "MESSAGE_THREAD_NOT_FOUND" in msg or "THREAD_NOT_FOUND" in msg:
                        # Тема удалена из Telegram; сбрасываем thread_id в БД
                        await self.set_topic(topic_key, None)
                        report["missing"].append(topic_key)
                        logger.warning(
                            "Тема '%s' #%d не найдена в Telegram — thread_id сброшен",
                            topic_key, thread_id,
                        )
                    else:
                        report["errors"][topic_key] = msg
                        logger.error("Ошибка синхронизации темы '%s': %s", topic_key, exc)
                except TelegramForbiddenError as exc:
                    report["no_permission"].append(topic_key)
                    logger.warning("Нет прав для темы '%s': %s", topic_key, exc)
                except Exception as exc:
                    report["errors"][topic_key] = str(exc)
                    logger.error("Ошибка синхронизации темы '%s': %s", topic_key, exc)

        return report

    async def check_topics_startup(self) -> list[str]:
        """
        Быстрая проверка при запуске (без обращения к Telegram API).
        Возвращает список ключей обязательных тем, у которых не настроен thread_id.
        """
        missing = []
        for topic_key, defn in TOPIC_REGISTRY.items():
            if not defn.required:
                continue
            topic = await self.get_topic(topic_key)
            if not topic or topic.message_thread_id is None:
                missing.append(topic_key)
        return missing

    # ── Публикация ────────────────────────────────────────────────────────────

    async def publish(
        self,
        bot: Bot,
        topic_name: str,
        text: str,
        **kwargs,
    ) -> bool:
        """Публикует текстовое сообщение в нужную ветку (или основной чат)."""
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

    async def publish_with_attachments(
        self,
        bot: Bot,
        topic_name: str,
        text: str,
        attachments: dict | None = None,
    ) -> bool:
        """
        Публикует текст + вложения (фото, видео, документы) в нужную ветку.

        Логика:
        - Фото + видео → медиагруппа (или одиночное сообщение), caption = text.
        - Документы → отдельные send_document после медиагруппы.
        - Только документы (без медиа) → сначала текст, потом документы.
        - Нет вложений → обычный publish().
        """
        if not attachments or not any(attachments.get(k) for k in ("photos", "videos", "documents")):
            return await self.publish(bot, topic_name, text)

        thread_id = await self.get_thread_id(topic_name)
        label = TOPIC_LABELS.get(topic_name, topic_name)

        photos = attachments.get("photos", [])
        videos = attachments.get("videos", [])
        docs   = attachments.get("documents", [])

        try:
            # ── Медиагруппа (фото и видео) ───────────────────────────────────
            all_media: list = []
            for i, p in enumerate(photos):
                caption = text if i == 0 else None
                pm = "HTML" if caption else None
                all_media.append(InputMediaPhoto(media=p["file_id"], caption=caption, parse_mode=pm))
            for i, v in enumerate(videos):
                idx     = len(photos) + i
                caption = text if idx == 0 else None
                pm = "HTML" if caption else None
                all_media.append(InputMediaVideo(media=v["file_id"], caption=caption, parse_mode=pm))

            if all_media:
                if len(all_media) == 1:
                    if photos:
                        await bot.send_photo(
                            chat_id=self._chat_id,
                            photo=photos[0]["file_id"],
                            caption=text,
                            message_thread_id=thread_id,
                            parse_mode="HTML",
                        )
                    else:
                        await bot.send_video(
                            chat_id=self._chat_id,
                            video=videos[0]["file_id"],
                            caption=text,
                            message_thread_id=thread_id,
                            parse_mode="HTML",
                        )
                else:
                    await bot.send_media_group(
                        chat_id=self._chat_id,
                        media=all_media,
                        message_thread_id=thread_id,
                    )
                for d in docs:
                    await bot.send_document(
                        chat_id=self._chat_id,
                        document=d["file_id"],
                        message_thread_id=thread_id,
                    )
            else:
                # Только документы: сначала текст, потом файлы
                await bot.send_message(
                    chat_id=self._chat_id,
                    text=text,
                    message_thread_id=thread_id,
                    parse_mode="HTML",
                )
                for d in docs:
                    await bot.send_document(
                        chat_id=self._chat_id,
                        document=d["file_id"],
                        message_thread_id=thread_id,
                    )

            logger.info(
                "publish_with_attachments '%s' (thread=%s): photos=%d videos=%d docs=%d",
                label, thread_id, len(photos), len(videos), len(docs),
            )
            return True

        except Exception as exc:
            logger.warning(
                "publish_with_attachments: не удалось опубликовать в ветку '%s': %s",
                label, exc,
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
