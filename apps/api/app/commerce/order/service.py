"""Order boundary exposes scoped DTOs to payment, support and account services."""

from datetime import UTC, datetime

from sqlalchemy import func, select, update

from app.commerce.core.constants import BASIS_POINTS
from app.commerce.core.errors import MallError
from app.commerce.core.repository import owned, owned_page
from app.commerce.core.schemas import utc, view
from app.commerce.core.services import enabled, service
from app.commerce.order import checkout
from app.commerce.order.models import Order, OrderItem
from app.commerce.order.states import transition

ORDER_FIELDS = ("id", "user_id", "status", "fulfillment_status", "currency", "total_cents",
                "wallet_cents", "refunded_cents", "refund_reserved_cents", "version",
                "tracking_number", "created_at", "expires_at")
ITEM_FIELDS = ("id", "sku_id", "title_snapshot", "price_cents", "qty", "total_cents")


class OrderService:
    def __init__(self, db):
        self.db = db

    async def row(self, user_id: str, order_id: str, *, lock: bool = False):
        return await owned(self.db, Order, owner_id=user_id, resource_id=order_id, lock=lock)

    async def get(self, user_id: str, order_id: str, *, lock: bool = False):
        row = await self.row(user_id, order_id, lock=lock)
        items = await self.db.scalars(select(OrderItem).where(OrderItem.order_id == row.id))
        return {**view(row, ORDER_FIELDS), "items": [view(item, ITEM_FIELDS) for item in items]}

    async def list(self, user_id: str, *, cursor: str = "", status: str = ""):
        filters = (Order.status == status,) if status else ()
        rows, after = await owned_page(self.db, Order, owner_id=user_id, cursor=cursor, filters=filters)
        return {"items": [view(row, ORDER_FIELDS) for row in rows], "next_cursor": after}

    async def place(self, user_id: str, payload):
        row = await checkout.place(self.db, user_id, payload)
        return await self.get(user_id, row.id)

    async def cancel(self, user_id: str, order_id: str, *, expected_version: int | None = None):
        row = await self.row(user_id, order_id, lock=True)
        if expected_version is not None and row.version != expected_version:
            raise MallError("version_conflict")
        await transition(self.db, row, target="CANCELLED", actor_id=user_id)
        await service("inventory", self.db).finish(row.id, consume=False)
        if enabled("payment"):
            await service("payment", self.db).cancel_order(user_id, row.id)
        return view(row, ORDER_FIELDS)

    async def paid(self, user_id: str, order_id: str, *, wallet_cents: int):
        row = await self.row(user_id, order_id, lock=True)
        if row.status == "PAID":
            return
        if utc(row.expires_at) <= datetime.now(UTC):
            raise MallError("order_expired")
        row.wallet_cents = wallet_cents
        await self.db.flush()
        await transition(self.db, row, target="PAID", actor_id=user_id)
        await service("inventory", self.db).finish(row.id, consume=True)

    async def advance(self, user_id: str, order_id: str, *, payload, actor_id: str):
        row = await self.row(user_id, order_id, lock=True)
        if row.version != payload.expected_version:
            raise MallError("version_conflict")
        if row.status == "PARTIALLY_REFUNDED":
            from app.commerce.order.states import allowed

            allowed(row.fulfillment_status, payload.status)
        if payload.tracking_number:
            row.tracking_number = payload.tracking_number
            await self.db.flush()
        await transition(self.db, row, target=payload.status, actor_id=actor_id)
        return view(row, ORDER_FIELDS)

    async def unfinished(self, user_id: str):
        return bool(await self.db.scalar(select(Order.id).where(Order.user_id == user_id,
            Order.status.not_in(["CANCELLED", "COMPLETED", "REFUNDED"])).limit(1)))

    async def anonymize(self, user_id: str):
        await self.db.execute(update(Order).where(Order.user_id == user_id).values(address_snapshot={}))

    async def export(self, user_id: str):
        rows = await self.db.scalars(select(Order).where(Order.user_id == user_id))
        return [view(row, ORDER_FIELDS) for row in rows]

    async def first_completed(self, user_id: str):
        row = await self.db.scalar(select(Order).where(Order.user_id == user_id,
            Order.fulfillment_status == "COMPLETED").order_by(Order.created_at, Order.id).limit(1))
        return view(row, ORDER_FIELDS) if row else None

    async def summary(self):
        from app.core.config import get_settings

        paid = Order.fulfillment_status.in_(["PAID", "SHIPPED", "DELIVERED", "COMPLETED"])
        count = await self.db.scalar(select(func.count()).select_from(Order))
        paid_count = await self.db.scalar(select(func.count()).select_from(Order).where(paid))
        gmv = await self.db.scalar(select(func.coalesce(func.sum(Order.total_cents), 0)).where(paid))
        refunds = await self.db.scalar(select(func.count()).select_from(Order).where(Order.refunded_cents > 0))
        return {"orders": count, "paid_orders": paid_count, "gmv_cents": gmv,
                "refunded_orders": refunds, "currency": get_settings().mall_currency,
                "payment_conversion_basis_points": paid_count * BASIS_POINTS // count if count else 0,
                "refund_rate_basis_points": refunds * BASIS_POINTS // paid_count if paid_count else 0}

    async def flash_order(self, user_id: str, *, sku_id: str, price_cents: int):
        from datetime import timedelta

        from app.commerce.core.events import publish
        from app.core.config import get_settings

        quote = await service("catalog", self.db).quote(sku_id, lock=True)
        settings = get_settings()
        row = Order(user_id=user_id, currency=quote["currency"], total_cents=price_cents,
            expires_at=datetime.now(UTC) + timedelta(seconds=settings.mall_reservation_seconds))
        self.db.add(row)
        await self.db.flush()
        self.db.add(OrderItem(order_id=row.id, sku_id=sku_id, price_cents=price_cents, qty=1,
                             total_cents=price_cents, title_snapshot=quote["title"]))
        await service("inventory", self.db).reserve(row.id, [{"sku_id": sku_id, "qty": 1}], expires_at=row.expires_at)
        await publish(self.db, row, event_type="mall.order.created", payload={"user_id": user_id, "order_id": row.id})
        return view(row, ORDER_FIELDS)
