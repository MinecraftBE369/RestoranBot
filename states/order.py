from aiogram.fsm.state import State, StatesGroup


# Состояния оформления заказа
class OrderState(StatesGroup):
    waiting_for_address = State()        # Юзер вводит адрес доставки
    waiting_for_payment = State()        # Юзер выбирает способ оплаты


# Состояния добавления блюда админом
class AddDishState(StatesGroup):
    waiting_for_category = State()   # Выбор категории
    waiting_for_name = State()       # Название блюда
    waiting_for_description = State()  # Описание
    waiting_for_price = State()      # Цена
    waiting_for_photo = State()      # Фото или ссылка на фото


# Состояние добавления категории админом
class AddCategoryState(StatesGroup):
    waiting_for_name = State()
