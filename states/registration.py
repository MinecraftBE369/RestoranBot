from aiogram.fsm.state import State, StatesGroup


# Класс состояний — каждое поле = один шаг регистрации
class RegistrationState(StatesGroup):
    waiting_for_name = State()   # Юзер вводит имя
    waiting_for_phone = State()  # Юзер вводит телефон