# Фильтр, который проверяет: "является ли этот юзер админом?"
# Если да — хендлер сработает. Если нет — проигнорируется.

from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from config import ADMINS_IDS

class IsAdmin(BaseFilter):
    """
    Кастомный фильтр для aiogram
    Использование: @router.message(IsAdmin(), Command("add_dish"))
    """

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        # event.from_user.id - это tg_id того, кто отправил сообщение/нажал на кнопку
        return event.from_user.id in ADMINS_IDS