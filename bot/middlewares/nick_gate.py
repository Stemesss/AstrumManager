# -*- coding: utf-8 -*-
"""
Middleware-шлюз профиля.

Блокирует доступ к командам бота до завершения первичной
настройки профиля (установки игрового ника).

Регистрируется на private.message ПОСЛЕ LoggingMiddleware,
ТОЛЬКО на приватных сообщениях.
"""
import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.services.user_service import UserService
from bot.states.nick import NickSetup

logger = logging.getLogger(__name__)

_SETUP_PROMPT = (
    "👋 Сначала настройте профиль — без этого бот недоступен.\n\n"
    "🎮 <b>Введите ваше игровое имя:</b>\n\n"
    "• от 3 до 20 символов\n"
    "• только буквы, цифры, пробел, дефис\n"
    "• без эмодзи и спецсимволов\n"
    "• только имя, без титулов"
)


class NickGateMiddleware(BaseMiddleware):
    """
    Перехватывает сообщения пользователей без установленного ника
    и перенаправляет их на первичную настройку профиля.

    Пропускает без проверки:
      • команды (начинаются с /)
      • сообщения пока пользователь уже находится в NickSetup FSM
    """

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if not event.from_user:
            return await handler(event, data)

        # Команды /start, /help и т.д. — пропускаем (у них собственная логика)
        if event.text and event.text.startswith("/"):
            return await handler(event, data)

        # Уже идёт настройка профиля — не мешаем
        state: FSMContext | None = data.get("state")
        if state:
            current = await state.get_state()
            if current and current.startswith("NickSetup"):
                return await handler(event, data)

        # Проверяем наличие ника в БД
        user_service: UserService | None = data.get("user_service")
        if user_service:
            has_nick = await user_service.has_nick(event.from_user.id)
            if not has_nick:
                logger.info(
                    "NickGate: user %s без ника — перенаправление на настройку профиля",
                    event.from_user.id,
                )
                if state:
                    await state.set_state(NickSetup.waiting_name)
                await event.answer(_SETUP_PROMPT)
                return  # Прерываем дальнейшую обработку

        return await handler(event, data)
