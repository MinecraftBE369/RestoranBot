from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from database.models import Base
from config import DATABASE_URL

# URL берём из config.py:
#   - по умолчанию SQLite ("sqlite+aiosqlite:///./restaurant.db") — для тестов
#   - через переменную окружения DATABASE_URL можно указать PostgreSQL
#     ("postgresql+asyncpg://user:pass@host:5432/db") — для продакшена

# Создаём движок — он управляет подключением к БД
engine = create_async_engine(DATABASE_URL, echo=False)  # echo=True для отладки SQL

# Создаём фабрику сессий — каждая сессия = одно подключение к БД
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


# Функция для создания таблиц при первом запуске
async def init_db():
    async with engine.begin() as conn:
        # create_all() создаёт все таблицы, которых ещё нет
        # Если таблицы уже есть — ничего не делает (данные не теряются)
        await conn.run_sync(Base.metadata.create_all)


# Функция-генератор сессии — используется в middleware и хендлерах
async def get_session():
    async with AsyncSessionLocal() as session:
        yield session