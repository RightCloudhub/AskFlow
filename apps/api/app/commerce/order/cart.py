"""Persistent carts; availability and prices are refreshed at checkout."""

from sqlalchemy import delete, func, select

from app.commerce.core.errors import MallError
from app.commerce.core.repository import insert_once
from app.commerce.core.services import service
from app.commerce.order.models import Cart, CartItem
from app.core.config import get_settings


async def cart_for(db, user_id: str):
    await insert_once(db, Cart, values={"user_id": user_id}, unique=["user_id"])
    return await db.scalar(select(Cart).where(Cart.user_id == user_id))


async def items(db, user_id: str):
    statement = select(CartItem).join(Cart, Cart.id == CartItem.cart_id).where(Cart.user_id == user_id)
    rows = await db.scalars(statement.order_by(CartItem.id))
    result = []
    for row in rows:
        sku = await service("catalog", db).ensure_sku(row.sku_id)
        result.append({"sku_id": row.sku_id, "qty": row.qty, "version": row.version, "title": sku["title"]})
    return {"items": result}


async def set_item(db, user_id: str, payload):
    await service("catalog", db).quote(payload.sku_id)
    cart = await cart_for(db, user_id)
    existing = await db.scalar(select(CartItem.id).where(CartItem.cart_id == cart.id, CartItem.sku_id == payload.sku_id))
    count = await db.scalar(select(func.count()).select_from(CartItem).where(CartItem.cart_id == cart.id))
    if not existing and count >= get_settings().mall_order_max_items:
        raise MallError("cart_item_limit")
    await insert_once(db, CartItem, values={"cart_id": cart.id, "sku_id": payload.sku_id,
        "qty": payload.qty}, unique=["cart_id", "sku_id"])
    row = await db.scalar(select(CartItem).where(CartItem.cart_id == cart.id, CartItem.sku_id == payload.sku_id))
    row.qty, row.version = payload.qty, row.version + 1
    return {"sku_id": row.sku_id, "qty": row.qty, "version": row.version}


async def remove(db, user_id: str, sku_id: str):
    carts = select(Cart.id).where(Cart.user_id == user_id)
    await db.execute(delete(CartItem).where(CartItem.cart_id.in_(carts), CartItem.sku_id == sku_id))
    return {"status": "removed"}
