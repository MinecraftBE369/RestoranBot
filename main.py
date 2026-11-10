import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from config import BOT_TOKEN, PROXY_URL

# === ИМПОРТЫ БД И РОУТЕРОВ ===
# Импортируем функцию создания таблиц из папки database
from database import init_db

# Импортируем роутеры из папок handlers
# (убедись, что файлы start.py и promote.py созданы внутри этих папок!)
from handlers.user.start import router as user_router
from handlers.admin.promote import router as admin_router

# Настраиваем логирование чтобы видеть в консоли, что происходит в боте
logging.basicConfig(
    level=logging.INFO,  # показываем все важные события от INFO и выше
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# === СОЗДАНИЕ ОБЪЕКТА БОТА С ПРОКСИ ===
session = AiohttpSession(proxy=PROXY_URL)
bot = Bot(token=BOT_TOKEN, session=session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

# === ХРАНИЛИЩЕ FSM ===
storage = MemoryStorage()

# === ДИСПЕТЧЕР ===
dp = Dispatcher(storage=storage)

# === ИНИЦИАЛИЗАЦИЯ РОУТЕРОВ ===
# Подключаем роутеры к диспетчеру, чтобы бот знал, где искать хендлеры
dp.include_router(user_router)
dp.include_router(admin_router)

# === ГЛАВНАЯ ФУНКЦИЯ ДЛЯ ЗАПУСКА БОТА ===
async def main():
    # Инициализируем БД (создаём таблицы, если их ещё нет)
    await init_db()
    logger.info("База данных инициализирована.")

    # Запускаем опрос сервера Telegram
    await dp.start_polling(bot)

# === ЗАПУСК БОТА ===
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")