# -*- coding: utf-8 -*-
"""Обработчик команды /echo и неизвестных сообщений."""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("echo"))
async def handle_echo(message: Message) -> None:
    """Повторяет текст, переданный после команды /echo."""
    args = message.text.split(maxsplit=1) if message.text else []
    if len(args) < 2 or not args[1].strip():
        # Подсказка об использовании команды
        await message.answer("Использование: /echo &lt;ваш текст&gt;", parse_mode="HTML")
        return
    await message.answer(args[1])


@router.message()
async def handle_unknown(message: Message) -> None:
    """Ответ на любое нераспознанное сообщение."""
    await message.answer(
        "🤔 Я не понял это сообщение. Используйте /help, чтобы увидеть доступные команды."
    )
