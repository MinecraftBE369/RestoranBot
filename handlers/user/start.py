# Роутер старта/регистрации и главного меню клиента.
# Сессия БД и объект user приходят из middleware (data["session"], data["user"]).

import logging

from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from database.repository import create_user
from states.registration import RegistrationState
from keybords.reply import main_menu_kb, contact_share_kb, remove_kb
from config import ADMINS_IDS

logger = logging.getLogger(__name__)

router = Router(name="start")


def is_admin_tg_id(tg_id: int) -> bool:
    return tg_id in ADMINS_IDS


async def show_main_menu(message: Message, user: User):
    """Главное меню клиента или админ-панель — в зависимости от роли."""
    if user.role == "admin" or is_admin_tg_id(user.telegram_id):
        from keybords.inline import admin_main_kb  # локальный импорт во избежание цикла
        await message.answer(
            f"👋 Привет, {user.name}!\n"
            f"Ты зарегистрирован как <b>администратор</b>. 🛠\n\n"
            f"Выбери раздел:",
            reply_markup=admin_main_kb(),
        )
    else:
        await message.answer(
            f"👋 Привет, {user.name}! Рад тебя видеть 🍕\n\n"
            f"Что будем делать?",
            reply_markup=main_menu_kb(),
        )


# === /start ===
# Регистрация незарегистрированных пользователей берёт на себя
# RegistrationMiddleware: он сам спросит имя. Здесь показываем главное меню.
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext,
                    session: AsyncSession, user: User | None):
    await state.clear()  # сбрасываем любые зависшие состояния

    if user is None:
        # Middleware уже выдал приглашение к регистрации — ничего не дублируем
        return

    await show_main_menu(message, user)


# === Шаг 1: ввод имени (состояние ставит middleware) ===
@router.message(RegistrationState.waiting_for_name, F.text & ~F.text.startswith("/"))
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(RegistrationState.waiting_for_phone)

    await message.answer(
        "📱 Отлично! Теперь отправь свой номер телефона.\n\n"
        "Можно напечатать (например: <code>+7 999 123-45-67</code>)\n"
        "или нажать кнопку «📤 Отправить контакт» ниже ⬇️",
        reply_markup=contact_share_kb(),
    )


# === Шаг 2: телефон прислали контактом (Contact Keyboard) ===
@router.message(RegistrationState.waiting_for_phone, F.contact)
async def process_phone_contact(message: Message, state: FSMContext,
                                session: AsyncSession):
    data = await state.get_data()
    await _finish_registration(
        message=message, state=state, session=session,
        name=data.get("name") or message.from_user.first_name,
        phone=message.contact.phone_number,
    )


# === Шаг 2 (альтернатива): телефон напечатан текстом ===
@router.message(RegistrationState.waiting_for_phone, F.text & ~F.text.startswith("/"))
async def process_phone_text(message: Message, state: FSMContext,
                             session: AsyncSession):
    data = await state.get_data()
    phone = message.text.strip()

    # Простейшая проверка, что это похоже на телефон
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) < 10:
        await message.answer("❌ Похоже, это не номер телефона. Попробуй ещё раз, "
                             "например: <code>+7 999 123-45-67</code>")
        return

    await _finish_registration(
        message=message, state=state, session=session,
        name=data.get("name"), phone=phone,
    )


# === Финал регистрации: сохраняем в БД и открываем главное меню ===
async def _finish_registration(message: Message, state: FSMContext,
                               session: AsyncSession, name: str, phone: str):
    data = await state.get_data()
    role = data.get("role", "client")

    new_user = await create_user(
        session=session,
        telegram_id=message.from_user.id,
        name=name,
        phone=phone,
        role=role,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    await state.clear()

    logger.info("Зарегистрирован новый пользователь: %s (%s), роль=%s",
                new_user.telegram_id, new_user.name, new_user.role)

    await message.answer(
        f"✅ Регистрация завершена!\n"
        f"Имя: {new_user.name}\n"
        f"Телефон: {new_user.phone}\n"
        f"Роль: {new_user.role}",
        reply_markup=remove_kb,
    )
    await show_main_menu(message, new_user)


# === Навигация: кнопка «🏠 Главное меню» под inline-сообщениями ===
@router.callback_query(F.data == "nav:main")
async def cb_nav_main(callback: CallbackQuery, user: User):
    await callback.message.edit_reply_markup(reply_markup=None)
    await show_main_menu(callback.message, user)
    await callback.answer()


# === Кнопка «📞 Помощь/Связь» — ТЗ п.5: связь с администратором ===
# Клиент пишет вопрос обычным сообщением в состоянии ожидания помощи,
# бот пересылает его в личку каждому админу.
HELP_STATE = "start:waiting_help"


@router.message(F.text == "📞 Помощь/Связь")
async def btn_help(message: Message, state: FSMContext):
    if not ADMINS_IDS:
        await message.answer("😔 К сожалению, служба поддержки сейчас недоступна.")
        return

    await state.set_state(HELP_STATE)
    await message.answer(
        "📞 Сейчас я перешлю твой вопрос администратору ресторана.\n"
        "Напиши, пожалуйста, что случилось (одним сообщением):"
    )


@router.message(F.state == HELP_STATE, F.text & ~F.text.startswith("/"))
async def send_help_to_admins(message: Message, state: FSMContext,
                              bot: Bot, user: User):
    await state.clear()

    sent = 0
    for admin_id in ADMINS_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=(
                    f"🆘 Вопрос от клиента!\n\n"
                    f"👤 Имя: {user.name}\n"
                    f"🆔 Telegram ID: <code>{user.telegram_id}</code>\n"
                    f"📱 Телефон: {user.phone}\n\n"
                    f"💬 Сообщение:\n{message.text}"
                ),
            )
            sent += 1
        except Exception as e:
            logger.warning("Не удалось отправить сообщение админу %s: %s", admin_id, e)

    if sent:
        await message.answer("✅ Сообщение отправлено администратору. Он скоро ответит!")
    else:
        await message.answer("😔 Не удалось доставить сообщение. Попробуй позже.")
