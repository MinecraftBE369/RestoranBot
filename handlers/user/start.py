from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from database.database import AsyncSessionLocal
from states.registration import RegistrationState
from config import ADMINS_IDS

# Создаём роутер — сюда будем складывать все хендлеры пользователя
user_router = Router()


# Хендлер команды /start
@user_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    # Подключаемся к БД
    async with AsyncSessionLocal() as session:
        # Ищем юзера по telegram_id
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

        # Если юзер уже есть в БД — пропускаем регистрацию
        if user:
            # Определяем роль для приветствия
            role_text = "администратор" if user.role == "admin" else "клиент"
            await message.answer(
                f"👋 Привет, {user.name}! Ты уже зарегистрирован как {role_text}.\n"
                f"Используй меню для навигации."
            )
            # Сбрасываем FSM-состояние (на всякий случай)
            await state.clear()
            return

        # Если юзера нет — начинаем регистрацию
        # Проверяем, есть ли ID в списке админов из config.py
        if message.from_user.id in ADMINS_IDS:
            role = "admin"
            role_text = "администратор"
        else:
            role = "client"
            role_text = "клиент"

        # Сохраняем роль в FSM-данные — пригодится на последнем шаге
        await state.update_data(role=role)

        # Переводим юзера в состояние ожидания имени
        await state.set_state(RegistrationState.waiting_for_name)

        await message.answer(
            f"👋 Привет! Я бот для заказа еды.\n"
            f"Ты будешь зарегистрирован как {role_text}.\n\n"
            f"Введи своё имя:"
        )


# Хендлер ввода имени (срабатывает только когда юзер в состоянии waiting_for_name)
@user_router.message(RegistrationState.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    # Сохраняем имя в FSM-данные
    await state.update_data(name=message.text.strip())

    # Переводим в следующее состояние
    await state.set_state(RegistrationState.waiting_for_phone)

    await message.answer(
        "📱 Отлично! Теперь введи свой номер телефона:\n"
        f"(например: +7 999 123-45-67)"
    )


# Хендлер ввода телефона — финальный шаг регистрации
@user_router.message(RegistrationState.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    # Получаем данные из FSM
    data = await state.get_data()
    name = data.get("name")
    phone = message.text.strip()
    role = data.get("role", "client")

    # Создаём нового юзера в БД
    new_user = User(
        telegram_id=message.from_user.id,
        name=name,
        phone=phone,
        role=role
    )

    async with AsyncSessionLocal() as session:
        session.add(new_user)
        await session.commit()

    # Очищаем FSM-состояние — регистрация завершена
    await state.clear()

    await message.answer(
        f"✅ Регистрация завершена!\n"
        f"Имя: {name}\n"
        f"Телефон: {phone}\n"
        f"Роль: {role}\n\n"
        f"Теперь ты можешь пользоваться ботом."
    )