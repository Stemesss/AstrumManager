from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("echo"))
async def handle_echo(message: Message) -> None:
    args = message.text.split(maxsplit=1) if message.text else []
    if len(args) < 2 or not args[1].strip():
        await message.answer("Usage: /echo <your text>")
        return
    await message.answer(args[1])


@router.message()
async def handle_unknown(message: Message) -> None:
    await message.answer(
        "🤔 I didn't understand that. Use /help to see available commands."
    )
