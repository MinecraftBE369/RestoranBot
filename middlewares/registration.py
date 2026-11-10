# Middleware — промежуточный слой между Telegram и хендлерами.
# Срабатывает на КАЖДОЕ сообщение/колбэк до того, как оно попадёт в хендлер.
#
# Что делает:
#  1. Открывает сессию БД и передаёт её в хендлер (data["session"]) —
#     хендлерам не нужно каждый раз писать AsyncSessionLocal().
#  2. Проверяет, зарегистрирован ли пользователь в БД.
#     Если нет — пропускает только /start (там идёт регистрация),
#     остальным предлагает сначала зарегистрироваться.
#  3. Пишет действие пользователя в лог.

import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.models import User

logger = logging.getLogger(__name__)


class RegistrationMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Middleware работает и с сообщениями, и с нажатиями inline-кнопок
        if not isinstance(event, (Message, CallbackQuery)):
            return await handler(event, data)

        tg_user = event.from_user

        # Открываем сессию БД на время обработки события
        async with AsyncSessionLocal() as session:
            data["session"] = session  # хендлеры получают её через аргумент session

            # Ищем пользователя в БД
            result = await session.execute(
                select(User).where(User.telegram_id == tg_user.id)
            )
            user = result.scalar_one_or_none()
            data["user"] = user  # None, если ещё не зарегистрирован

            # Пишем в лог, кто и что сделал
            if isinstance(event, Message):
                logger.info("Пользователь %s (%s): %s", tg_user.id, tg_user.username, event.text)
            else:
                logger.info("Пользователь %s нажал кнопку: %s", tg_user.id, event.data)

            # Если пользователя нет в БД — разрешаем только команду /start
            if user is None:
                is_start = isinstance(event, Message) and event.text and event.text.startswith("/start")
                if not is_start:
                    if isinstance(event, Message):
                        await event.answer("Сначала зарегистрируйся — отправь команду /start")
                    else:
                        await event.answer("Сначала зарегистрируйся — отправь /start", show_alert=True)
                    return  # дальше в хендлер не пускаем

            return await handler(event, data)
