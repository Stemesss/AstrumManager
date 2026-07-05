# -*- coding: utf-8 -*-
"""Сервис рассылки анонсов об обновлении AstrumManager.

Использование:
    await send_update_announcement(bot, chat_id)
    await send_update_announcement(bot, chat_id, state=state)  # + очистка FSM
"""
import logging

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove

from bot.keyboards.announcement import build_update_announcement_kb

logger = logging.getLogger(__name__)

UPDATE_ANNOUNCEMENT_TEXT = (
    "🚀 <b>AstrumManager обновлён!</b>\n"
    "\n"
    "Дорогие участники клана Astrum!\n"
    "\n"
    "Мы продолжаем активно развивать нашего кланового помощника. Уже сейчас "
    "бот получил множество улучшений и новых возможностей, а впереди — ещё "
    "больше полезных функций.\n"
    "\n"
    "━━━━━━━━━━━━━━━━━━\n"
    "\n"
    "📌 <b>Что нужно сделать каждому участнику?</b>\n"
    "\n"
    "1️⃣ Нажмите кнопку «🚀 Обновить AstrumManager» ниже.\n"
    "\n"
    "2️⃣ Откройте раздел «👤 Мой профиль».\n"
    "\n"
    "3️⃣ Проверьте свой игровой ник.\n"
    "\n"
    "4️⃣ Если ник отсутствует или указан неверно — обязательно измените его.\n"
    "\n"
    "⚠️ Игровой ник в боте должен ПОЛНОСТЬЮ совпадать с вашим ником в игре.\n"
    "\n"
    "Это необходимо для корректной работы:\n"
    "\n"
    "• 👥 списка участников;\n"
    "• 📊 статистики активности;\n"
    "• 🏆 рейтингов;\n"
    "• ⚙️ будущих функций AstrumManager.\n"
    "\n"
    "━━━━━━━━━━━━━━━━━━\n"
    "\n"
    "💡 Если вы обнаружили:\n"
    "\n"
    "• 🐞 ошибку;\n"
    "• ⚠️ недоработку;\n"
    "• 💭 интересную идею;\n"
    "• ✨ предложение по новой функции —\n"
    "\n"
    "обязательно сообщите об этом через раздел\n"
    "«💡 Жалобы и предложения» внутри бота.\n"
    "\n"
    "Каждое обращение будет рассмотрено администрацией, а лучшие идеи могут "
    "появиться уже в следующих обновлениях.\n"
    "\n"
    "❤️ Спасибо каждому участнику Astrum за помощь в развитии проекта!\n"
    "\n"
    "Вместе мы создаём современную и удобную систему управления нашим "
    "кланом."
)


async def send_update_announcement(bot: Bot, chat_id: int, state: FSMContext | None = None) -> bool:
    """Отправляет анонс обновления AstrumManager в указанный chat_id.

    Универсальная функция — используется как для тестовой отправки
    администратору, так и (в будущем) для рассылки в клановую группу.

    Поведение:
      • username бота получается динамически через bot.get_me() —
        ссылка всегда актуальна, даже если username сменится;
      • сообщение содержит ровно одну inline-кнопку со ссылкой на бота
        (InlineKeyboardButton(url=...)), без «голых» ссылок в тексте;
      • если передан state — FSM полностью завершается (state.clear());
      • любая «зависшая» ReplyKeyboard (например «❌ Отмена») удаляется
        через ReplyKeyboardRemove() без видимого следа — служебное
        сообщение отправляется и сразу удаляется, у пользователя
        остаётся только сам анонс с inline-кнопкой.

    Возвращает True при успешной отправке, False при ошибке
    (например, если chat_id недоступен).
    """
    try:
        if state is not None:
            await state.clear()

        me = await bot.get_me()
        bot_username = me.username
        if not bot_username:
            logger.error("send_update_announcement: у бота отсутствует username — ссылка не сформирована")
            return False

        keyboard = build_update_announcement_kb(bot_username)

        # Снимаем возможную зависшую ReplyKeyboard («❌ Отмена» и т.п.), не оставляя следов
        try:
            cleanup_msg = await bot.send_message(
                chat_id=chat_id,
                text="🔄",
                reply_markup=ReplyKeyboardRemove(),
            )
            await bot.delete_message(chat_id=chat_id, message_id=cleanup_msg.message_id)
        except Exception as cleanup_error:
            logger.warning(
                "send_update_announcement: не удалось снять ReplyKeyboard в chat_id=%s: %s",
                chat_id, cleanup_error,
            )

        await bot.send_message(
            chat_id=chat_id,
            text=UPDATE_ANNOUNCEMENT_TEXT,
            reply_markup=keyboard,
        )
        logger.info(
            "Анонс обновления отправлен в chat_id=%s (бот=@%s)", chat_id, bot_username
        )
        return True
    except Exception as e:
        logger.error("Не удалось отправить анонс обновления в chat_id=%s: %s", chat_id, e)
        return False
