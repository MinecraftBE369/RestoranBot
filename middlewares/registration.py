# Middleware — промежуточный слой между Telegram и хендлерами.
# Срабатывает на КАЖДОЕ сообщение/колбэк до того, как оно попадёт в хендлер.
#
# Что делает (ТЗ п.4.1):
#  1. Открывает сессию БД и передаёт её в хендлер (data["session"]) —
#     хендлерам не нужно каждый раз писать AsyncSessionLocal().
#  2. Проверяет наличие telegram_id в таблице User.
#     Если пользователя нет — прерывает сценарий и запускает регистрацию:
#     сам отправляет приветствие и переводит юзера в состояние
#     RegistrationState.waiting_for_name. Дальше события НЕ пропускаются,
#     и следующий ввод юзера обработает start.py.
#  3. Пишет действие пользователя в лог.

import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import AsyncSessionLocal
from database.models import User
from database.repository import get_user_by_tg_id
from states.registration import RegistrationState
from config import ADMINS_IDS

logger = logging.getLogger(__name__)


class DbSessionMiddleware(BaseMiddleware):
    """Открывает сессию БД на время обработки каждого события."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with AsyncSessionLocal() as session:
            data["session"] = session  # хендлеры получают её через аргумент session
            return await handler(event, data)


class RoleAccessMiddleware(BaseMiddleware):
    """Пускает админские роутеры только пользователей с ролью admin.

    Роль определяется по полю role в БД; ID из ADMINS_IDS (config/.env)
    автоматически считаются админами (ТЗ п.4.3).
    """

    def __init__(self, *, role_name: str):
        self.role_name = role_name

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user: User | None = data.get("user")
        tg_id = event.from_user.id if event.from_user else None

        is_allowed = (
            (user is not None and user.role == self.role_name)
            or tg_id in ADMINS_IDS  # жёстко заданный telegram_id из конфига
        )
        if not is_allowed:
            # Молча игнорируем чужие коллбэки/команды админ-панели
            if isinstance(event, CallbackQuery):
                await event.answer("⛔ Недостаточно прав", show_alert=True)
            return None
        return await handler(event, data)


class RegistrationMiddleware(BaseMiddleware):
    """Главная проверка ТЗ п.4.1: незарегистрированный юзер идёт в регистрацию."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Работаем и с сообщениями, и с нажатиями inline-кнопок
        if not isinstance(event, (Message, CallbackQuery)):
            return await handler(event, data)

        tg_user = event.from_user
        session: AsyncSession = data["session"]

        # Ищем пользователя в БД (параметризованный запрос — см. repository)
        user = await get_user_by_tg_id(session, tg_user.id)
        data["user"] = user  # None, если ещё не зарегистрирован

        # Пишем в лог, кто и что сделал (ТЗ п.6 «Логирование»)
        if isinstance(event, Message):
            logger.info("Пользователь %s (%s): %s", tg_user.id, tg_user.username, event.text)
        else:
            logger.info("Пользователь %s нажал кнопку: %s", tg_user.id, event.data)

        # === Пользователя нет в БД — прерываем сценарий, запускаем регистрацию ===
        if user is None:
            # Если регистрация уже идёт (FSM-состояние активно) —
            # пропускаем событие к хендлерам ввода имени/телефона
            state: FSMContext = data.get("state")
            current_state = await state.get_state() if state else None
            if current_state and current_state.startswith("RegistrationState"):
                return await handler(event, data)

            # Определяем роль: ID из .env — сразу админ
            role = "admin" if tg_user.id in ADMINS_IDS else "client"

            if isinstance(event, Message):
                await state.set_state(RegistrationState.waiting_for_name)
                await state.update_data(role=role)
                await event.answer(
                    f"👋 Привет! Я бот для заказа еды.\n"
                    f"Похоже, ты новый пользователь — давай зарегистрируемся.\n"
                    f"Ты будешь зарегистрирован как {('администратор' if role == 'admin' else 'клиент')}.\n\n"
                    f"✏️ Введи своё имя:"
                )
            else:
                await event.answer(
                    "Сначала зарегистрируйся — отправь команду /start",
                    show_alert=True,
                )
            return  # дальше в основной сценарий не пускаем

        return await handler(event, data)

