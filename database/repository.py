# Слой репозитория — все запросы к БД в одном месте.
# ВАЖНО: здесь используются только ОТСЮДА-параметризованные запросы SQLAlchemy
# (select().where(Model.column == value)) — SQL-инъекции исключены (ТЗ п.6).

from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import User, Category, Dish, Order, OrderItem


# ---------- Пользователи ----------

async def get_user_by_tg_id(session: AsyncSession, telegram_id: int) -> Optional[User]:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def create_user(session: AsyncSession, telegram_id: int, name: str, phone: str,
                      role: str = "client", username: str = None,
                      first_name: str = None) -> User:
    user = User(telegram_id=telegram_id, name=name, phone=phone, role=role,
                username=username, first_name=first_name)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


# ---------- Меню (категории и блюда) ----------

async def get_categories(session: AsyncSession) -> list[Category]:
    result = await session.execute(select(Category).order_by(Category.id))
    return list(result.scalars().all())


async def get_category(session: AsyncSession, category_id: int) -> Optional[Category]:
    return await session.get(Category, category_id)


async def get_dishes(session: AsyncSession, category_id: int,
                     only_active: bool = True) -> list[Dish]:
    stmt = select(Dish).where(Dish.category_id == category_id)
    if only_active:
        stmt = stmt.where(Dish.is_active.is_(True))
    result = await session.execute(stmt.order_by(Dish.name))
    return list(result.scalars().all())


async def get_dish(session: AsyncSession, dish_id: int) -> Optional[Dish]:
    return await session.get(Dish, dish_id)


async def add_category(session: AsyncSession, name: str, description: str = None) -> Category:
    cat = Category(name=name, description=description)
    session.add(cat)
    await session.commit()
    await session.refresh(cat)
    return cat


async def add_dish(session: AsyncSession, name: str, description: str, price: float,
                   category_id: int, photo_file_id: str = None,
                   photo_url: str = None) -> Dish:
    dish = Dish(name=name, description=description, price=price,
                category_id=category_id, photo_file_id=photo_file_id, photo_url=photo_url)
    session.add(dish)
    await session.commit()
    await session.refresh(dish)
    return dish


async def delete_dish(session: AsyncSession, dish_id: int) -> None:
    await session.execute(delete(Dish).where(Dish.id == dish_id))
    await session.commit()


# ---------- Заказы ----------

async def create_order(session: AsyncSession, user_pk: int, total_sum: float,
                       address: str, payment_method: str,
                       items: list[tuple[int, int, float]]) -> Order:
    """Создаёт заказ вместе с позициями.

    items — список кортежей (dish_id, quantity, price_at_order).
    Цена фиксируется на момент заказа (price_at_moment из ТЗ).
    """
    order = Order(user_id=user_pk, total_sum=total_sum,
                  address=address, payment_method=payment_method)
    session.add(order)
    await session.flush()  # получаем order.id до commit

    for dish_id, qty, price in items:
        session.add(OrderItem(order_id=order.id, dish_id=dish_id,
                              quantity=qty, price_at_order=price))
    await session.commit()
    await session.refresh(order)
    return order


async def get_order(session: AsyncSession, order_id: int) -> Optional[Order]:
    result = await session.execute(
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.user))
        .where(Order.id == order_id)
    )
    return result.scalar_one_or_none()


async def get_active_orders(session: AsyncSession) -> list[Order]:
    """Заказы, которые ещё в работе (не завершены и не отменены)."""
    result = await session.execute(
        select(Order)
        .where(Order.status.notin_(["completed", "cancelled"]))
        .order_by(Order.created_at.desc())
    )
    return list(result.scalars().all())
