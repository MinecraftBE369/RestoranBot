from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime


# Базовый класс для всех моделей — от него наследуем таблицы
class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(Integer, unique=True, nullable=False)  # ID из Telegram
    name = Column(String, nullable=True)  # Имя (заполняется при регистрации)
    phone = Column(String, nullable=True)  # Телефон
    role = Column(String, default="client")  # "client" или "admin"
    registered_at = Column(DateTime, default=datetime.now)

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
    description = Column(String, nullable=True)
    price = Column(Float, nullable=False)
    photo_url = Column(String, nullable=True)  # Ссылка на фото
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)

    # Связь с категорией — каждое блюдо принадлежит одной категории
    category = relationship("Category", back_populates="dishes")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="new")  # "new" / "working" / "done"
    total_sum = Column(Float, nullable=False)
    address = Column(String, nullable=True)
    payment_method = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    # Связь с юзером
    user = relationship("User", back_populates="orders")
    # Связь с позициями заказа
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    dish_id = Column(Integer, ForeignKey("dishes.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    price_at_order = Column(Float, nullable=False)  # Цена на момент заказа!

    order = relationship("Order", back_populates="items")
    dish = relationship("Dish")