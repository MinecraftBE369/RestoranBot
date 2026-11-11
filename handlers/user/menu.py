# Роутер «Меню»: категории, список блюд, карточка блюда (ТЗ п.4.2).
# Карточка блюда: фото, название, описание, цена + кнопка «➕ В корзину».

import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.repository import get_categories, get_category, get_dishes, get_dish
from keybords.inline import categories_kb, dish_card_kb, dish_list_kb

logger = logging.getLogger(__name__)

router = Router(name="menu")


async def safe_edit(message: Message, *, text: str = None, photo=None, markup=None):
    """Редактирует сообщение, а если тип не позволяет — удаляет и шлёт новое."""
    try:
        if photo is not None:
            await message.edit_media(media=photo, reply_markup=markup)
        else:
            await message.edit_text(text=text, reply_markup=markup)
    except TelegramBadRequest:
        # Тип сообщения не совпадает (текст <-> фото) — пересылаем заново
        try:
            await message.delete()
        except TelegramBadRequest:
            pass
        if photo is not None:
            await message.answer_photo(photo=photo.media, caption=text, reply_markup=markup)
        else:
            await message.answer(text=text, reply_markup=markup)


async def render_dish(callback: CallbackQuery, state: FSMContext,
                      session: AsyncSession, dish_id: int):
    """Показывает карточку блюда: фото (если есть) + текст + кнопки."""
    from handlers.user.cart import get_cart  # локальный импорт — нет цикла зависимостей

    dish = await get_dish(session, dish_id)
    if dish is None or not dish.is_active:
        await callback.answer("😔 Блюдо недоступно", show_alert=True)
        return

    # Запоминаем последнюю открытую карточку — по ней работает «➕ В корзину»
    await state.update_data(last_dish_id=dish.id)

    cart = await get_cart(state)
    qty_in_cart = cart.get(str(dish.id), {}).get("qty", 0)

    text = (
        f"🍽 <b>{dish.name}</b>\n\n"
        f"📝 {dish.description or 'Описание отсутствует'}\n\n"
        f"💰 <b>{dish.price:.2f} ₽</b>"
    )
    markup = dish_card_kb(qty_in_cart)

    if dish.photo_file_id or dish.photo_url:
        await safe_edit(callback.message, text=text,
                        photo=dish.photo_file_id or dish.photo_url, markup=markup)
    else:
        await safe_edit(callback.message, text=text, markup=markup)


# === Кнопка «🍔 Меню» (reply-клавиатура) ===
@router.message(F.text == "🍔 Меню")
async def btn_menu(message: Message, session: AsyncSession):
    categories = await get_categories(session)
    if not categories:
        await message.answer("😔 Меню пока пустое — загляни позже!")
        return
    await message.answer("🍽 Выбери категорию:", reply_markup=categories_kb(categories))


# === Колбэк «показать категории» ===
@router.callback_query(F.data == "menu:show")
async def cb_show_categories(callback: CallbackQuery, session: AsyncSession):
    categories = await get_categories(session)
    if not categories:
        await callback.answer("Меню пока пустое", show_alert=True)
        return
    await safe_edit(callback.message, text="🍽 Выбери категорию:",
                    markup=categories_kb(categories))
    await callback.answer()


# === Колбэк «выбрана категория» → список блюд ===
@router.callback_query(F.data.startswith("menu:cat:"))
async def cb_category(callback: CallbackQuery, session: AsyncSession):
    category_id = int(callback.data.split(":")[-1])
    category = await get_category(session, category_id)
    if category is None:
        await callback.answer("Категория не найдена", show_alert=True)
        return

    dishes = await get_dishes(session, category_id, only_active=True)
    if not dishes:
        await callback.answer("В этой категории пока пусто 😔", show_alert=True)
        return

    lines = [f"📂 <b>{category.name}</b>", ""]
    for d in dishes:
        lines.append(f"🍽 <b>{d.name}</b> — {d.price:.2f} ₽")
    lines.append("")
    lines.append("Нажми на блюдо, чтобы открыть карточку 👇")

    await safe_edit(callback.message, text="\n".join(lines),
                    markup=dish_list_kb(category_id, dishes))
    await callback.answer()


# === Колбэк «открыть карточку блюда» ===
@router.callback_query(F.data.startswith("dish:open:"))
async def cb_open_dish(callback: CallbackQuery, state: FSMContext,
                       session: AsyncSession):
    dish_id = int(callback.data.split(":")[-1])
    await render_dish(callback, state, session, dish_id)
    await callback.answer()


# === Пустая информационная кнопка ===
@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()
