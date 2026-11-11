# Reply-клавиатуры (нативные кнопки Telegram под полем ввода)
# По ТЗ п.5: весь интерфейс на нативных возможностях Telegram, без внешних ссылок.

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove


# Главное меню клиента: «🍔 Меню», «🛒 Корзина», «📞 Помощь/Связь»
def main_menu_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🍔 Меню"),
                KeyboardButton(text="🛒 Корзина"),
            ],
            [
                KeyboardButton(text="📞 Помощь/Связь"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери раздел...",
    )
    return kb


# Кнопка «Отмена» для шагов оформления заказа / добавления блюд
def cancel_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    return kb


# Contact Keyboard — кнопка «Поделиться контактом» для быстрого ввода телефона
def contact_share_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📤 Отправить контакт", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    return kb


# Убирает клавиатуру (после завершения регистрации/заказа)
remove_kb = ReplyKeyboardRemove()
