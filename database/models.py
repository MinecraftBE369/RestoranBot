from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime


# Статусы заказа (см. ТЗ п.3: new -> in_progress -> ready -> completed, + cancelled)
STATUS_NEW = "new"
STATUS_IN_PROGRESS = "in_progress"
STATUS_READY = "ready"
STATUS_COMPLETED = "completed"
STATUS_CANCELLED = "cancelled"

# Человекочитаемые названия статусов для кнопок и сообщений
STATUS_LABELS = {
    STATUS_IN_PROGRESS: "🔥 В работе",
    STATUS_READY: "✅ Готово",
    STATUS_COMPLETED: "🏁 Завершён",
    STATUS_CANCELLED: "❌ Отменён",
}

STATUS_ICONS = {
    STATUS_NEW: "🆕 Новый",
    STATUS_IN_PROGRESS: "🔥 В работе",
    STATUS_READY: "✅ Готово",
    STATUS_COMPLETED: "🏁 Завершён",
    STATUS_CANCELLED: "❌ Отменён",
}


# Базовый класс для всех моделей — от него наследуем таблицы
class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # telegram_id — большие числа, поэтому BigInteger (на 32-битных движках int переполнится)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)  # ID из Telegram
    name = Column(String, nullable=True)              # Имя (заполняется при регистрации)
    username = Column(String, nullable=True)          # @username из Telegram
    first_name = Column(String, nullable=True)        # Имя из Telegram
    phone = Column(String, nullable=True)             # Телефон (phone_number по ТЗ)
    role = Column(String, default="client")           # "client" или "admin"
    registered_at = Column(DateTime, default=datetime.now)  # registration_date по ТЗ

    # Связь с заказами — один юзер может иметь много заказов
    orders = relationship("Order", back_populates="user")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)

    # Связь с блюдами — в одной категории много блюд
    dishes = relationship("Dish", back_populates="category")


class Dish(Base):
    __tablename__ = "dishes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)   # Состав/описание
    price = Column(Float, nullable=False)
    photo_url = Column(String, nullable=True)      # Ссылка на фото (если нет file_id)
    photo_file_id = Column(String, nullable=True)  # ID файла в Telegram (загрузка админом)
    is_active = Column(Boolean, default=True, nullable=False)  # Архивация: False = скрыто из меню
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)

    # Связь с категорией — каждое блюдо принадлежит одной категории
    category = relationship("Category", back_populates="dishes")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # new / in_progress / ready / completed / cancelled
    status = Column(String, default=STATUS_NEW, nullable=False, index=True)
    total_sum = Column(Float, nullable=False)
    address = Column(String, nullable=True)          # Адрес доставки или номер стола
    payment_method = Column(String, nullable=True)   # Способ оплаты
    created_at = Column(DateTime, default=datetime.now)

    # Связь с юзером
    user = relationship("User", back_populates="orders")
    # Связь с позициями заказа
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    dish_id = Column(Integer, ForeignKey("dishes.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    price_at_order = Column(Float, nullable=False)  # Цена на момент заказа (price_at_moment по ТЗ)!

    order = relationship("Order", back_populates="items")
    dish = relationship("Dish")