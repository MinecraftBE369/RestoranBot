from aiogram.fsm.state import State, StatesGroup


# Состояния оформления заказа
class OrderState(StatesGroup):
    waiting_for_address = State()   # Юзер вводит адрес доставки / номер стола
    waiting_for_payment = State()   # Юзер выбирает способ оплаты (inline-кнопки)
    waiting_for_confirm = State()   # Финальное подтверждение (inline-кнопки)


# Состояния добавления блюда админом
class AddDishState(StatesGroup):
    waiting_for_name = State()         # Название блюда
    waiting_for_description = State()  # Описание/состав
    waiting_for_price = State()        # Цена
    waiting_for_photo = State()        # Фото (загрузкой/ссылкой/пропуском)


# Состояние добавления категории админом
class AddCategoryState(StatesGroup):
    waiting_for_name = State()


# Состояния редактирования блюда админом
class EditDishState(StatesGroup):
    waiting_for_value = State()  # Ввод нового значения (текст или фото)
