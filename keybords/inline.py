# Inline-клавиатуры (кнопки под сообщениями)
# Здесь собираются: категории меню, карточки блюд, корзина,
# оплата, подтверждение заказа и админ-панель.

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database.models import Order, STATUS_LABELS, STATUS_ICONS, STATUS_COMPLETED, STATUS_CANCELLED


# ---------- КЛИЕНТ: МЕНЮ ----------

def categories_kb(categories) -> InlineKeyboardMarkup:
    """Список категорий меню в две колонки."""
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    row = []
    for cat in categories:
        row.append(InlineKeyboardButton(
            text=f"📂 {cat.name}",
            callback_data=f"menu:cat:{cat.id}",
        ))
        if len(row) == 2:
            kb.inline_keyboard.append(row)
            row = []
    if row:
        kb.inline_keyboard.append(row)

    kb.inline_keyboard.append([
        InlineKeyboardButton(text="🛒 Корзина", callback_data="cart:show"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="nav:main"),
    ])
    return kb


def dish_card_kb(in_cart_qty: int = 0) -> InlineKeyboardMarkup:
    """Кнопки под карточкой блюда: «➕ В корзину» или управление количеством."""
    if in_cart_qty > 0:
        row = [
            InlineKeyboardButton(text="➖", callback_data="cart:last:-1"),
            InlineKeyboardButton(text=f"🛒 В корзине: {in_cart_qty}", callback_data="noop"),
            InlineKeyboardButton(text="➕", callback_data="cart:last:1"),
        ]
    else:
        row = [InlineKeyboardButton(text="➕ В корзину", callback_data="cart:last:1")]
    return InlineKeyboardMarkup(inline_keyboard=[
        row,
        [InlineKeyboardButton(text="⬅️ Назад к категориям", callback_data="menu:show")],
    ])


def dish_list_kb(category_id: int, dishes) -> InlineKeyboardMarkup:
    """Список блюд категории — кнопка на каждое блюдо (открывает карточку)."""
    rows = [[InlineKeyboardButton(
        text=f"{d.name} — {d.price:.2f} ₽", callback_data=f"dish:open:{d.id}",
    )] for d in dishes]
    rows.append([
        InlineKeyboardButton(text="🛒 Корзина", callback_data="cart:show"),
        InlineKeyboardButton(text="⬅️ Категории", callback_data="menu:show"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ---------- КЛИЕНТ: КОРЗИНА ----------

def cart_item_kb(item_key: str, quantity: int) -> InlineKeyboardMarkup:
    """Управление количеством одной позиции корзины."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➖", callback_data=f"cart:qty:{item_key}:-1"),
            InlineKeyboardButton(text=f"{quantity} шт.", callback_data="noop"),
            InlineKeyboardButton(text="➕", callback_data=f"cart:qty:{item_key}:1"),
            InlineKeyboardButton(text="🗑", callback_data=f"cart:del:{item_key}"),
        ],
    ])


def cart_total_kb(total_count: int) -> InlineKeyboardMarkup:
    """Нижняя часть корзины: оформить / очистить / назад в меню."""
    rows = []
    if total_count > 0:
        rows.append([InlineKeyboardButton(
            text="✅ Оформить заказ", callback_data="order:start",
        )])
        rows.append([InlineKeyboardButton(
            text="🗑 Очистить корзину", callback_data="cart:clear",
        )])
    rows.append([InlineKeyboardButton(text="🍔 В меню", callback_data="menu:show")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ---------- КЛИЕНТ: ОФОРМЛЕНИЕ ----------

PAYMENT_VARIANTS = [
    ("💵 Наличные", "cash"),
    ("💳 Карта при получении", "card"),
    ("🌐 Онлайн", "online"),
]

PAYMENT_LABELS = dict(PAYMENT_VARIANTS)  # {"cash": "💵 Наличные", ...}


def payment_kb() -> InlineKeyboardMarkup:
    """Выбор способа оплаты."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data=f"order:pay:{value}")]
        for text, value in PAYMENT_VARIANTS
    ])


def confirm_order_kb() -> InlineKeyboardMarkup:
    """Финальное подтверждение заказа."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить заказ", callback_data="order:confirm"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="order:cancel_confirm"),
        ],
        [InlineKeyboardButton(text="✏️ Изменить оплату", callback_data="order:reselect_pay")],
    ])


# ---------- АДМИН: ЗАКАЗЫ ----------

def order_admin_kb(order: Order) -> InlineKeyboardMarkup:
    """Кнопки смены статуса под уведомлением о заказе."""
    buttons = []
    if order.status not in (STATUS_COMPLETED, STATUS_CANCELLED):
        for status, label in STATUS_LABELS.items():
            if status == order.status:
                continue  # не показываем текущий статус
            buttons.append(InlineKeyboardButton(
                text=label, callback_data=f"adm:status:{order.id}:{status}",
            ))

    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton(
        text="👤 Связаться с клиентом", callback_data=f"adm:contact:{order.id}",
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def orders_list_kb(orders) -> InlineKeyboardMarkup:
    """Список активных заказов — кнопка на каждый заказ."""
    rows = [[InlineKeyboardButton(
        text=f"№{o.id} | {STATUS_ICONS.get(o.status, o.status)} | {o.total_sum:.2f} ₽",
        callback_data=f"adm:view:{o.id}",
    )] for o in orders]
    rows.append([InlineKeyboardButton(text="🏠 Админ-панель", callback_data="adm:panel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ---------- АДМИН: ПАНЕЛЬ / CRUD ----------

def admin_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Активные заказы", callback_data="adm:orders")],
        [InlineKeyboardButton(text="🍽 Управление меню", callback_data="adm:menu")],
    ])


def admin_categories_kb(categories) -> InlineKeyboardMarkup:
    """Для CRUD: список категорий + кнопка добавить."""
    rows = [[InlineKeyboardButton(
        text=f"✏️ {cat.name}", callback_data=f"adm:cat:{cat.id}",
    )] for cat in categories]
    rows.append([InlineKeyboardButton(text="➕ Добавить категорию", callback_data="adm:addcat")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="adm:panel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_dishes_kb(category_id: int, dishes) -> InlineKeyboardMarkup:
    """Блюда категории: редактирование / архивация / добавление."""
    rows = []
    for d in dishes:
        mark = "" if d.is_active else " 🚫"
        rows.append([InlineKeyboardButton(
            text=f"{d.name}{mark} — {d.price:.2f} ₽",
            callback_data=f"adm:dish:{d.id}",
        )])
    rows.append([InlineKeyboardButton(
        text="➕ Добавить блюдо", callback_data=f"adddish:start:{category_id}",
    )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад к категориям", callback_data="adm:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_dish_edit_kb(dish_id: int, category_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """Действия над одним блюдом: поля, архивация, удаление."""
    toggle_label = "♻️ Вернуть в меню" if not is_active else "🚫 Скрыть (архив)"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Название", callback_data=f"admedit:name:{dish_id}"),
            InlineKeyboardButton(text="📝 Описание", callback_data=f"admedit:desc:{dish_id}"),
        ],
        [
            InlineKeyboardButton(text="💰 Цена", callback_data=f"admedit:price:{dish_id}"),
            InlineKeyboardButton(text="📷 Фото", callback_data=f"admedit:photo:{dish_id}"),
        ],
        [
            InlineKeyboardButton(text=toggle_label, callback_data=f"admdish:toggle:{dish_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admdish:delete:{dish_id}"),
        ],
        [InlineKeyboardButton(text="⬅️ Назад к блюдам", callback_data=f"adm:cat:{category_id}")],
    ])


def admin_confirm_delete_kb(callback_ok: str, callback_back: str) -> InlineKeyboardMarkup:
    """Подтверждение опасного действия (удаление)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=callback_ok),
            InlineKeyboardButton(text="❌ Отмена", callback_data=callback_back),
        ],
    ])
