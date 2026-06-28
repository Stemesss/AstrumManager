# -*- coding: utf-8 -*-
"""Обработчики основных команд: /start, /help, /about."""
from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

router = Router()

# Главная клавиатура управления кланом
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📢 Новости"), KeyboardButton(text="📅 События")],
        [KeyboardButton(text="📚 Гайды"), KeyboardButton(text="📸 Скриншоты")],
        [KeyboardButton(text="👥 Участники"), KeyboardButton(text="⚙️ Настройки")],
        [KeyboardButton(text="❓ Помощь")],
    ],
    resize_keyboard=True,
)


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    """Приветственное сообщение с главным меню при команде /start."""
    await message.answer(
        "🌌 Добро пожаловать в Astrum!\n\n"
        "Рады видеть тебя в системе управления кланом.\n"
        "Выберите нужный раздел.",
        reply_markup=MAIN_KEYBOARD,
    )


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    """Показывает список доступных команд."""
    await message.answer(
        "📖 <b>Доступные команды</b>\n\n"
        "/start — главное меню\n"
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
