from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

router = Router()


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    user = message.from_user
    name = user.full_name if user else "there"
    await message.answer(
        f"👋 Hello, {name}!\n\n"
        "I'm your Telegram bot powered by aiogram 3.\n\n"
        "Here's what I can do:\n"
        "/start — show this welcome message\n"
        "/help — show available commands\n"
        "/echo <text> — repeat your text back\n"
        "/about — learn about this bot"
    )


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    await message.answer(
        "📖 <b>Available Commands</b>\n\n"
        "/start — welcome message\n"
        "/help — show this help\n"
        "/echo &lt;text&gt; — echo your text\n"
        "/about — about this bot",
        parse_mode="HTML"
    )


@router.message(Command("about"))
async def handle_about(message: Message) -> None:
    await message.answer(
        "🤖 <b>About this Bot</b>\n\n"
        "Built with <b>aiogram 3</b> — a modern, fully asynchronous "
        "Telegram Bot API framework for Python.\n\n"
        "Framework: aiogram 3\n"
        "Language: Python 3.11",
        parse_mode="HTML"
    )
