# Роутер «Оформление заказа» (ТЗ п.4.2):
# адрес → способ оплаты → подтверждение → сохранение в БД →
# уведомление администратору → ответ клиенту.

import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import ADMINS_IDS
from database.models import User
from database.repository import create_order, get_dish
from states.order import OrderState
from keybords.inline import payment_kb, confirm_order_kb, PAYMENT_LABELS
from keybords.reply import cancel_kb, main_menu_kb
from handlers.user.cart import get_cart, save_cart, cart_sum

logger = logging.getLogger(__name__)

router = Router(name="order")


async def notify_admins(bot: Bot, order, user: User, items_lines: list[str]):
    """Отправляет каждому админу уведомление о новом заказе (ТЗ п.4.2 «Финализация»)."""
    text = (
        f"🔔 <b>НОВЫЙ ЗАКАЗ №{order.id}</b>\n\n"
        f"👤 Клиент: {user.name} (тел.: {user.phone})\n"
        f"🆔 Telegram ID: <code>{user.telegram_id}</code>\n\n"
        f"📦 Состав:\n" + "\n".join(items_lines) + "\n\n"
        f"💰 Сумма: <b>{order.total_sum:.2f} ₽</b>\n"
        f"📍 Адрес/стол: {order.address}\n"
        f"💳 Оплата: {order.payment_method}"
    )
    from keybords.inline import order_admin_kb
    markup = order_admin_kb(order)

    for admin_id in ADMINS_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=text, reply_markup=markup)
        except Exception as e:
            # Например, админ не написал боту ранее — Telegram запретит отправку
            logger.warning("Не удалось уведомить админа %s: %s", admin_id, e)


# === Старт оформления (кнопка «✅ Оформить заказ») ===
@router.callback_query(F.data == "order:start")
async def cb_start_order(callback: CallbackQuery, state: FSMContext):
    cart = await get_cart(state)
    if not cart:
        await callback.answer("Корзина пуста!", show_alert=True)
        return

    await state.set_state(OrderState.waiting_for_address)
    await callback.message.answer(
        "📦 Оформление заказа...\n\n"
        "Введи, пожалуйста, <b>адрес доставки</b> или <b>номер столика</b>:",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


# === Отмена на любом шаге ===
@router.message(OrderState.*, F.text == "❌ Отмена")
async def cancel_order(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Оформление отменено. Заказ остался в корзине.",
                         reply_markup=main_menu_kb())


# === Шаг 1: адрес ===
@router.message(OrderState.waiting_for_address, F.text & ~F.text.startswith("/"))
async def get_address(message: Message, state: FSMContext):
    address = message.text.strip()
    if len(address) < 5:
        await message.answer("Слишком короткий адрес 🤔 Напиши подробнее "
                             "(или номер стола, например: «Стол №5»):")
        return

    await state.update_data(address=address)
    await state.set_state(OrderState.waiting_for_payment)
    await message.edit_reply_markup(reply_markup=None)
    await message.answer(
        f"📍 Запомнил: <i>{address}</i>\n\n"
        f"💳 Выбери способ оплаты:",
        reply_markup=payment_kb(),
    )


# === Шаг 2: оплата (inline-кнопки) ===
@router.callback_query(OrderState.waiting_for_payment, F.data.startswith("order:pay:"))
async def choose_payment(callback: CallbackQuery, state: FSMContext):
    pay_value = callback.data.split(":")[-1]
    pay_label = PAYMENT_LABELS.get(pay_value)
    if pay_label is None:
        await callback.answer("Неизвестный способ оплаты", show_alert=True)
        return

    await state.update_data(payment=pay_label)
    await state.set_state(OrderState.waiting_for_confirm)

    # Показываем сводку для финального подтверждения
    data = await state.get_data()
    cart = data.get("cart", {})
    lines = ["🧾 <b>Проверь заказ:</b>", ""]
    for item in cart.values():
        lines.append(f"• {item['name']} — {item['qty']} шт. × {item['price']:.2f} ₽ "
                     f"= {item['qty'] * item['price']:.2f} ₽")
    lines += [
        "",
        f"💰 Итого: <b>{cart_sum(cart):.2f} ₽</b>",
        f"📍 Адрес/стол: <i>{data['address']}</i>",
        f"💳 Оплата: <i>{pay_label}</i>",
    ]
    await callback.message.answer("\n".join(lines), reply_markup=confirm_order_kb())
    await callback.answer()


# === Шаг 2 (back): изменить оплату ===
@router.callback_query(OrderState.waiting_for_confirm, F.data == "order:reselect_pay")
async def reselect_payment(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OrderState.waiting_for_payment)
    await callback.message.answer("💳 Выбери способ оплаты:", reply_markup=payment_kb())
    await callback.answer()


# === Отмена подтверждения ===
@router.callback_query(OrderState.waiting_for_confirm, F.data == "order:cancel_confirm")
async def cancel_confirmation(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OrderState.waiting_for_address)
    await callback.message.delete()
    await callback.message.answer(
        "❌ Оформление отменено. Корзина сохранена — вернись к заказу через «🛒 Корзина».",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()


# === Шаг 3: финальное подтверждение и сохранение в БД ===
@router.callback_query(OrderState.waiting_for_confirm, F.data == "order:confirm")
async def confirm_order(callback: CallbackQuery, state: FSMContext,
                        session: AsyncSession, user: User, bot: Bot):
    data = await state.get_data()
    cart = data.get("cart", {})
    if not cart:
        await state.clear()
        await callback.answer("Корзина пуста 😔", show_alert=True)
        return

    # Пересчитываем по актуальным ценам из БД; цены фиксируем в OrderItem.price_at_order
    items = []          # [(dish_id, qty, price_at_order)]
    items_lines = []    # для уведомления админу
    total = 0.0
    for key, item in cart.items():
        dish = await get_dish(session, int(key))
        if dish is None or not dish.is_active:
            await state.clear()
            await callback.message.answer(
                f"😔 Блюдо «{item['name']}» больше недоступно. Обнови корзину."
            )
            await callback.answer("Есть недоступное блюдо", show_alert=True)
            return
        qty = item["qty"]
        items.append((dish.id, qty, dish.price))
        items_lines.append(f"• {dish.name} — {qty} шт. × {dish.price:.2f} ₽ "
                           f"= {qty * dish.price:.2f} ₽")
        total += qty * dish.price

    order = await create_order(
        session=session,
        user_pk=user.id,
        total_sum=round(total, 2),
        address=data["address"],
        payment_method=data["payment"],
        items=items,
    )
    logger.info("Создан заказ №%s пользователем %s на сумму %.2f ₽",
                order.id, user.telegram_id, order.total_sum)

    # Корзина очищается, состояние сбрасывается
    await save_cart(state, {})
    await state.clear()

    # Уведомление администраторам
    await notify_admins(bot, order, user, items_lines)

    # Ответ клиенту
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"✅ Заказ №{order.id} принят!\n\n"
        f"💰 Сумма: {order.total_sum:.2f} ₽\n"
        f"📍 {order.address}\n"
        f"💳 {order.payment_method}\n\n"
        f"Скоро свяжемся с тобой для подтверждения 🍕",
        reply_markup=main_menu_kb(),
    )
    await callback.answer("Заказ оформлен!")
