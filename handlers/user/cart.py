# Роутер «Корзина» (ТЗ п.4.2): добавление, изменение количества, удаление,
# очистка и показ списка позиций с итоговой суммой.
#
# Корзина живёт в FSM-хранилище под ключом "cart":
#   { "<dish_id>": {"name": str, "price": float, "qty": int} }

import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.repository import get_dish
from keybords.inline import cart_item_kb, cart_total_kb, dish_card_kb

logger = logging.getLogger(__name__)

router = Router(name="cart")


# ---------- Работа с корзиной в FSM ----------

async def get_cart(state: FSMContext) -> dict:
    """Возвращает корзину пользователя из FSM-хранилища."""
    data = await state.get_data()
    return data.get("cart", {})


async def save_cart(state: FSMContext, cart: dict):
    await state.update_data(cart=cart)


async def change_cart_item(state: FSMContext, dish_id: int, name: str,
                           price: float, delta: int) -> int:
    """Меняет количество блюда на delta. Возвращает новое количество (0 = удалено)."""
    cart = await get_cart(state)
    key = str(dish_id)
    item = cart.get(key, {"name": name, "price": price, "qty": 0})
    new_qty = item["qty"] + delta

    if new_qty <= 0:
        cart.pop(key, None)
    else:
        # Цена всегда актуальная — берём из БД на момент нажатия
        item.update(name=name, price=price, qty=new_qty)
        cart[key] = item

    await save_cart(state, cart)
    return new_qty


def cart_sum(cart: dict) -> float:
    return sum(item["price"] * item["qty"] for item in cart.values())


def cart_count(cart: dict) -> int:
    return sum(item["qty"] for item in cart.values())


# ---------- Показ корзины ----------

def build_cart_view(cart: dict) -> tuple[str, InlineKeyboardMarkup]:
    """Собирает текст и клавиатуру корзины (позиции + итоги)."""
    if not cart:
        return ("🛒 Корзина пуста.\nДобавь что-нибудь из меню! 🍔",
                cart_total_kb(0))

    lines = ["🛒 <b>Твоя корзина:</b>", ""]
    rows = []
    for key, item in cart.items():
        lines.append(
            f"• {item['name']} — {item['qty']} шт. × {item['price']:.2f} ₽ "
            f"= <b>{item['qty'] * item['price']:.2f} ₽</b>"
        )
        rows.append(cart_item_kb(key, item["qty"]).inline_keyboard[0])
    lines.append("")
    lines.append(f"💰 <b>Итого: {cart_sum(cart):.2f} ₽</b>")

    rows.extend(cart_total_kb(cart_count(cart)).inline_keyboard)
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=rows)


async def render_cart(message: Message, state: FSMContext):
    """Обновляет сообщение с корзиной (или шлёт новое)."""
    cart = await get_cart(state)
    text, markup = build_cart_view(cart)
    try:
        await message.edit_text(text=text, reply_markup=markup)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            return  # содержимое не изменилось — ничего делать не нужно
        await message.answer(text=text, reply_markup=markup)


# ---------- Хендлеры ----------

# Кнопка «🛒 Корзина» (reply-клавиатура)
@router.message(F.text == "🛒 Корзина")
async def btn_cart(message: Message, state: FSMContext):
    cart = await get_cart(state)
    text, markup = build_cart_view(cart)
    await message.answer(text, reply_markup=markup)


# Колбэк «показать корзину»
@router.callback_query(F.data == "cart:show")
async def cb_show_cart(callback: CallbackQuery, state: FSMContext):
    await render_cart(callback.message, state)
    await callback.answer()


# Добавление из карточки блюда: cart:last:<delta>.
# ID блюда берём из state["last_dish_id"] — его ставит menu.render_dish.
@router.callback_query(F.data.startswith("cart:last:"))
async def cb_add_last(callback: CallbackQuery, state: FSMContext,
                     session: AsyncSession):
    delta = int(callback.data.split(":")[-1])
    data = await state.get_data()
    last_dish_id = data.get("last_dish_id")
    if not last_dish_id:
        await callback.answer("Сначала открой карточку блюда", show_alert=True)
        return

    dish = await get_dish(session, last_dish_id)
    if dish is None or not dish.is_active:
        await callback.answer("😔 Блюдо недоступно", show_alert=True)
        return

    new_qty = await change_cart_item(state, dish.id, dish.name, dish.price, delta)
    if new_qty == 0:
        await callback.answer("Позиция убрана из корзины 🗑")
    elif delta > 0:
        await callback.answer(f"🛒 Добавлено: {dish.name}")
    else:
        await callback.answer(f"➖ {dish.name}: {new_qty} шт.")

    # Обновляем счётчик прямо под карточкой блюда
    try:
        await callback.message.edit_reply_markup(reply_markup=dish_card_kb(new_qty))
    except TelegramBadRequest:
        pass


# Изменение конкретной позиции: cart:qty:<dish_id>:<delta>
@router.callback_query(F.data.startswith("cart:qty:"))
async def cb_change_qty(callback: CallbackQuery, state: FSMContext,
                        session: AsyncSession):
    _, _, dish_id_s, delta_s = callback.data.split(":")
    dish_id, delta = int(dish_id_s), int(delta_s)

    dish = await get_dish(session, dish_id)
    if dish is None:
        await callback.answer("Блюдо не найдено", show_alert=True)
        return

    await change_cart_item(state, dish_id, dish.name, dish.price, delta)
    await render_cart(callback.message, state)
    await callback.answer()


# Удалить позицию целиком: cart:del:<dish_id>
@router.callback_query(F.data.startswith("cart:del:"))
async def cb_delete_item(callback: CallbackQuery, state: FSMContext):
    dish_id = callback.data.split(":")[-1]
    cart = await get_cart(state)
    cart.pop(dish_id, None)
    await save_cart(state, cart)
    await render_cart(callback.message, state)
    await callback.answer("🗑 Позиция удалена")


# Очистить корзину
@router.callback_query(F.data == "cart:clear")
async def cb_clear_cart(callback: CallbackQuery, state: FSMContext):
    await save_cart(state, {})
    await render_cart(callback.message, state)
    await callback.answer("Корзина очищена 🧹")
