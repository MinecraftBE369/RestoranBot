from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from database.database import AsyncSessionLocal
from ..filter import IsAdmin

router = Router()


# Команда /make_admin <telegram_id> — назначает юзера админом
@router.message(IsAdmin(), Command("make_admin"))
async def cmd_make_admin(message: Message):
    # Парсим аргумент команды — telegram_id целевого юзера
    # Пример: /make_admin 123456789
    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            "❌ Использование: /make_admin <telegram_id>\n"
            "Пример: /make_admin 123456789"
        )
        return

    try:
        target_id = int(args[1])
    except ValueError:
        await message.answer("❌ Telegram ID должен быть числом.")
        return

    # Ищем юзера в БД
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == target_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            await message.answer(
                f"❌ Юзер с ID {target_id} не найден в базе данных.\n"
                f"Сначала он должен написать боту /start."
            )
            return

        # Меняем роль на admin
        user.role = "admin"
        await session.commit()

    await message.answer(
        f"✅ Юзер {user.name} (ID: {target_id}) теперь администратор!"
    )


# Команда /demote <telegram_id> — снимает админку
@router.message(IsAdmin(), Command("demote"))
async def cmd_demote(message: Message):
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Использование: /demote <telegram_id>")
        return

    try:
        target_id = int(args[1])
    except ValueError:
        await message.answer("❌ Telegram ID должен быть числом.")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == target_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            await message.answer(f"❌ Юзер с ID {target_id} не найден.")
            return

        user.role = "client"
        await session.commit()

    await message.answer(
        f"✅ Юзер {user.name} (ID: {target_id}) теперь обычный клиент."
    )