# -*- coding: utf-8 -*-
"""
TopicService — единая точка управления системными форумными темами.

Публичный API:
    # Получение данных (без обращения к Telegram API)
    await topic_service.get_topic(key)        → ForumTopic | None
    await topic_service.get_thread_id(key)    → int | None
    await topic_service.list_topics()         → list[ForumTopic]

    # Иконки — работает с Telegram API
    await topic_service.get_icon_stickers(bot)           → list[Sticker]
    await topic_service.find_matching_icon(bot, key)     → str | None
    await topic_service.apply_topic_icon(bot, key, id)   → bool
    await topic_service.sync_all_icons(bot)              → dict (отчёт)

    # Создание / синхронизация тем — работает с Telegram API
    await topic_service.create_system_topic(bot, key)  → int | None
    await topic_service.sync_all_topics(bot)           → dict (отчёт)

    # Быстрая проверка при запуске (без API)
    await topic_service.check_topics_startup()  → list[str]

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
        # Кэш списка иконок-стикеров (getForumTopicIconStickers).
        # Заполняется при первом запросе; не меняется в течение жизни процесса.
        self._icon_stickers: list | None = None

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
        logger.info(
            "Ветка '%s' → thread_id=%s emoji=%s",
            topic_name, thread_id, icon_custom_emoji_id,
        )

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

    # ── Иконки тем (Telegram API) ──────────────────────────────────────────────

    async def get_icon_stickers(self, bot: Bot) -> list:
        """
        Возвращает список доступных стикеров-иконок для форумных тем.
        Результат кэшируется в памяти на весь срок жизни процесса.

        Каждый стикер имеет:
            .emoji            — символ Unicode-эмодзи (str | None)
            .custom_emoji_id  — ID, используемый в createForumTopic / editForumTopic

        Telegram Bot API: getForumTopicIconStickers не требует аргументов.
        """
        if self._icon_stickers is None:
            self._icon_stickers = await bot.get_forum_topic_icon_stickers()
            logger.info(
                "Загружено %d иконок-стикеров (кэш заполнен)",
                len(self._icon_stickers),
            )
        return self._icon_stickers

    def _build_emoji_map(self, stickers: list) -> dict[str, str]:
        """
        Строит словарь emoji → custom_emoji_id из списка стикеров.
        При дублировании emoji берётся первый стикер (что соответствует порядку Telegram).
        """
        result: dict[str, str] = {}
        for s in stickers:
            if s.custom_emoji_id and s.emoji and s.emoji not in result:
                result[s.emoji] = s.custom_emoji_id
        return result

    async def find_matching_icon(self, bot: Bot, topic_key: str) -> str | None:
        """
        Ищет custom_emoji_id, соответствующий эмодзи темы в реестре.
        Возвращает None, если подходящий стикер не найден.
        """
        defn = TOPIC_REGISTRY.get(topic_key)
        if not defn:
            return None
        try:
            stickers  = await self.get_icon_stickers(bot)
            emoji_map = self._build_emoji_map(stickers)
            return emoji_map.get(defn.emoji)
        except Exception as exc:
            logger.warning("find_matching_icon '%s': %s", topic_key, exc)
            return None

    async def apply_topic_icon(self, bot: Bot, topic_key: str, emoji_id: str) -> bool:
        """
        Применяет icon_custom_emoji_id к существующей теме через editForumTopic
        и сохраняет значение в БД.

        Telegram Bot API: editForumTopic позволяет менять name И icon_custom_emoji_id
        существующей темы (в отличие от icon_color, который задаётся только при создании).

        Возвращает True при успехе (в т.ч. если TOPIC_NOT_MODIFIED — иконка уже та).
        """
        topic = await self.get_topic(topic_key)
        if not topic or topic.message_thread_id is None:
            logger.warning("apply_topic_icon '%s': тема не настроена", topic_key)
            return False
        try:
            await bot.edit_forum_topic(
                chat_id=self._chat_id,
                message_thread_id=topic.message_thread_id,
                icon_custom_emoji_id=emoji_id,
            )
            await self.set_topic(topic_key, topic.message_thread_id, emoji_id)
            logger.info(
                "Иконка '%s' #%d → emoji_id=%s",
                topic_key, topic.message_thread_id, emoji_id,
            )
            return True
        except TelegramBadRequest as exc:
            if "TOPIC_NOT_MODIFIED" in str(exc):
                # Иконка уже та самая — сохраняем в БД для синхронности
                await self.set_topic(topic_key, topic.message_thread_id, emoji_id)
                return True
            logger.warning("apply_topic_icon '%s': %s", topic_key, exc)
            return False
        except Exception as exc:
            logger.warning("apply_topic_icon '%s': %s", topic_key, exc)
            return False

    async def sync_all_icons(self, bot: Bot) -> dict:
        """
        Автоматически назначает иконки всем темам, у которых ещё нет icon_custom_emoji_id.
        Темы с уже установленной иконкой пропускаются (не перезаписываются).

        Алгоритм для каждой темы:
          - Нет thread_id → "no_thread" (тема не настроена, пропуск)
          - Есть icon_custom_emoji_id в БД → "already_set" (пропуск)
          - Нет иконки → ищет стикер по emoji → применяет
              Нашёл → "applied"
              Не нашёл → "no_match"

        Возвращает отчёт-словарь:
        {
          "applied":     [keys],
          "already_set": [keys],
          "no_match":    [keys],
          "no_thread":   [keys],
          "errors":      {key: msg},
          "fetch_error": str | None,
        }
        """
        report: dict = {
            "applied":     [],
            "already_set": [],
            "no_match":    [],
            "no_thread":   [],
            "errors":      {},
            "fetch_error": None,
        }

        # Загружаем стикеры (с кэшем)
        try:
            stickers  = await self.get_icon_stickers(bot)
            emoji_map = self._build_emoji_map(stickers)
        except Exception as exc:
            report["fetch_error"] = str(exc)
            logger.error("sync_all_icons: не удалось получить стикеры: %s", exc)
            return report

        for topic_key, defn in TOPIC_REGISTRY.items():
            topic     = await self.get_topic(topic_key)
            thread_id = topic.message_thread_id if topic else None

            if thread_id is None:
                report["no_thread"].append(topic_key)
                continue

            if topic and topic.icon_custom_emoji_id:
                # Иконка уже установлена — не трогаем
                report["already_set"].append(topic_key)
                continue

            emoji_id = emoji_map.get(defn.emoji)
            if not emoji_id:
                report["no_match"].append(topic_key)
                continue

            ok = await self.apply_topic_icon(bot, topic_key, emoji_id)
            if ok:
                report["applied"].append(topic_key)
            else:
                report["errors"][topic_key] = "Не удалось применить"

        return report

    # ── Управление темами через Telegram API ───────────────────────────────────

    async def create_system_topic(self, bot: Bot, topic_key: str) -> int | None:
        """
        Создаёт форумную тему в Telegram, автоматически подбирает иконку
        и сохраняет thread_id + icon_custom_emoji_id в БД.

        Ограничение Telegram:
          - icon_color нельзя изменить после создания.
          - icon_custom_emoji_id можно поменять позже через editForumTopic.

        Требует, чтобы бот имел права can_manage_topics в группе.
        Возвращает thread_id созданной темы или None при ошибке.
        """
        defn = TOPIC_REGISTRY.get(topic_key)
        if not defn:
            logger.error("create_system_topic: неизвестный ключ '%s'", topic_key)
            return None

        # Пробуем автоматически подобрать иконку
        emoji_id = await self.find_matching_icon(bot, topic_key)

        try:
            tg_topic = await bot.create_forum_topic(
                chat_id=self._chat_id,
                name=defn.name,
                icon_color=defn.icon_color,
                icon_custom_emoji_id=emoji_id,  # None — создаётся с цветом без кастомной иконки
            )
            thread_id = tg_topic.message_thread_id
            await self.set_topic(topic_key, thread_id, emoji_id)
            logger.info(
                "Создана тема '%s' → thread_id=%d emoji_id=%s",
                topic_key, thread_id, emoji_id,
            )
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
        Синхронизирует все системные темы с Telegram (имена; иконки — через sync_all_icons).

        Алгоритм для каждой темы из реестра:
        - Если thread_id настроен → вызывает editForumTopic для проверки/исправления имени.
          Telegram API: editForumTopic меняет name и icon_custom_emoji_id;
          icon_color нельзя менять после создания.
        - Если thread_id не настроен → вызывает create_system_topic
          (автоматически подбирает иконку при создании).

        Возвращает словарь-отчёт:
        {
          "created":       [keys],
          "name_fixed":    [keys],
          "ok":            [keys],
          "missing":       [keys],
          "no_permission": [keys],
          "errors":        {key: msg},
        }

        Синхронизация безопасна: не удаляет и не пересоздаёт существующие темы.
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
                # Тема не настроена — создаём (с автоподбором иконки)
                new_id = await self.create_system_topic(bot, topic_key)
                if new_id is not None:
                    report["created"].append(topic_key)
                else:
                    report["no_permission"].append(topic_key)
            else:
                # Тема настроена — проверяем/исправляем имя через editForumTopic
                try:
                    await bot.edit_forum_topic(
                        chat_id=self._chat_id,
                        message_thread_id=thread_id,
                        name=defn.name,
                    )
                    report["name_fixed"].append(topic_key)
                    logger.info("Исправлено имя темы '%s' #%d", topic_key, thread_id)
                except TelegramBadRequest as exc:
                    msg = str(exc)
                    if "TOPIC_NOT_MODIFIED" in msg:
                        report["ok"].append(topic_key)
                    elif "MESSAGE_THREAD_NOT_FOUND" in msg or "THREAD_NOT_FOUND" in msg:
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
