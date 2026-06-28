# -*- coding: utf-8 -*-
"""Обработчики основных команд: /start, /help, /about."""
from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

router = Router()


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    """Приветственное сообщение при первом запуске или команде /start."""
    user = message.from_user
    name = user.full_name if user else "пользователь"
    await message.answer(
        f"👋 Привет, {name}!\n\n"
        "Я ваш Telegram-бот на базе aiogram 3.\n\n"
        "Вот что я умею:\n"
        "/start — показать это приветствие\n"
        "/help — показать доступные команды\n"
        "/echo &lt;текст&gt; — повторить ваш текст\n"
        "/about — узнать о боте",
        parse_mode="HTML"
    )


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    """Показывает список доступных команд."""
    await message.answer(
        "📖 <b>Доступные команды</b>\n\n"
        "/start — приветственное сообщение\n"
        "/help — показать эту справку\n"
        "/echo &lt;текст&gt; — повторить ваш текст\n"
        "/about — о боте",
        parse_mode="HTML"
    )


@router.message(Command("about"))
async def handle_about(message: Message) -> None:
    """Информация о боте и используемых технологиях."""
    await message.answer(
        "🤖 <b>О боте</b>\n\n"
        "Создан на базе <b>aiogram 3</b> — современного полностью асинхронного "
        "фреймворка Telegram Bot API для Python.\n\n"
        "Фреймворк: aiogram 3\n"
        "Язык: Python 3.11",
        parse_mode="HTML"
    )
