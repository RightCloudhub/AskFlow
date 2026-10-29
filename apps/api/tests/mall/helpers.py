"""Fixtures use real domain services and one database transaction per command."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import text

from app.commerce.account.sessions import issue_session
from app.commerce.catalog.models import Sku, SkuPrice, Spu
from app.commerce.core.errors import MallError
from app.commerce.inventory.models import Inventory
from app.commerce.order import checkout
from app.commerce.order.schemas import Checkout, Item, PlaceOrder
from app.commerce.order.service import OrderService
from app.models.user import User


async def transaction(runtime, action):
    async with runtime.sessions() as db:
        if db.bind.dialect.name == "sqlite":
            await db.execute(text("BEGIN IMMEDIATE"))
        try:
            result = await action(db)
            await db.commit()
            return result
        except MallError as exc:
            from app.commerce.core.deps import finish_error

            await finish_error(db, exc)
            raise


async def seed(runtime, *, stock=100, price=1000, role="user"):
    async def create(db):
        user = User(username="customer_" + uuid4().hex, email=uuid4().hex + "@example.com",
                    hashed_password="!fixture", role=role)
        product = Spu(title="Fixture product", status="active")
        db.add_all([user, product])
        await db.flush()
        sku = Sku(spu_id=product.id, title="Fixture SKU", code=uuid4().hex, status="active", currency="CNY")
        db.add(sku)
        await db.flush()
        db.add_all([SkuPrice(sku_id=sku.id, sale_cents=price, original_cents=price, valid_from=datetime.now(UTC)),
                    Inventory(sku_id=sku.id, available=stock)])
        bundle = await issue_session(db, user)
        return {"user_id": user.id, "sku_id": sku.id, "spu_id": product.id, **bundle}

    return await transaction(runtime, create)


async def place(db, identity):
    payload = Checkout(items=[Item(sku_id=identity["sku_id"], qty=1)])
    quote = await checkout.prepare(db, identity["user_id"], payload)
    return await OrderService(db).place(identity["user_id"], PlaceOrder(
        **payload.model_dump(), checkout_token=quote["checkout_token"]))


def headers(identity, *, key=None):
    return {"Authorization": "Bearer " + identity["access_token"], "Idempotency-Key": key or str(uuid4())}
