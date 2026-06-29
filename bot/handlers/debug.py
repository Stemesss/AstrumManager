# -*- coding: utf-8 -*-
"""
ВРЕМЕННЫЙ обработчик /threadid — удалить после проверки веток.

Работает в любом чате: личка, группа, тема форума.
"""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("threadid"))
async def cmd_threadid(message: Message) -> None:
    """Возвращает Chat ID, Thread ID и название темы (если доступно)."""
    chat_id   = message.chat.id
    thread_id = message.message_thread_id  # None если не в теме форума

    lines = [
        "🔍 <b>Debug: Thread Info</b>",
        "",
        f"<b>Chat ID:</b> <code>{chat_id}</code>",
        f"<b>Thread ID:</b> <code>{thread_id if thread_id is not None else 'нет (обычный чат)'}</code>",
    ]

    # Название темы доступно только у форумных топиков через forum_topic_created
    # В обычных сообщениях — недоступно напрямую, показываем тип чата
    chat_type = message.chat.type
    lines.append(f"<b>Тип чата:</b> <code>{chat_type}</code>")

    if message.chat.title:
        lines.append(f"<b>Название чата:</b> {message.chat.title}")

    await message.reply("\n".join(lines))
