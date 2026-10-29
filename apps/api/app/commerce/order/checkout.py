"""One-use quotes and transaction-local repricing/reservation."""

import secrets
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from http import HTTPStatus

from sqlalchemy import select, update

from app.commerce.account.addresses import AddressService
from app.commerce.admin.settings_service import value
from app.commerce.core.constants import MAX_SAFE_CENTS, TOKEN_BYTES
from app.commerce.core.errors import MallError
from app.commerce.core.events import publish
from app.commerce.core.services import service
from app.commerce.order.models import CheckoutToken, Order, OrderHistory, OrderItem
from app.core.config import get_settings
from app.services.agent.gateway.idempotency import args_hash


def item_arguments(payload):
    items = sorted([item.model_dump() for item in payload.items], key=lambda item: item["sku_id"])
    if len({item["sku_id"] for item in items}) != len(items):
        raise MallError("duplicate_sku", status=HTTPStatus.UNPROCESSABLE_ENTITY)
    return {"items": items, "address_id": payload.address_id}


async def price_items(db, items):
    result = []
    catalog = service("catalog", db)
    for item in items:
        quote = await catalog.quote(item["sku_id"], lock=True)
        if quote["currency"] != get_settings().mall_currency:
            raise MallError("currency_mismatch")
        result.append({**item, "price_cents": quote["price_cents"], "title_snapshot": quote["title"],
                       "total_cents": quote["price_cents"] * item["qty"]})
    return result


async def prepare(db, user_id: str, payload):
    args, settings = item_arguments(payload), get_settings()
    items = await price_items(db, args["items"])
    shipping = await value(db, "mall_shipping_cents")
    raw = secrets.token_urlsafe(TOKEN_BYTES)
    db.add(CheckoutToken(user_id=user_id, token_hash=sha256(raw.encode()).hexdigest(),
        items_hash=args_hash(args), expires_at=datetime.now(UTC) + timedelta(seconds=settings.mall_checkout_seconds)))
    await db.flush()
    return {"checkout_token": raw, "items": items, "shipping_cents": shipping,
            "total_cents": sum(item["total_cents"] for item in items) + shipping,
            "currency": settings.mall_currency}


async def place(db, user_id: str, payload):
    args, settings, now = item_arguments(payload), get_settings(), datetime.now(UTC)
    token = await db.scalar(select(CheckoutToken).where(CheckoutToken.user_id == user_id,
        CheckoutToken.token_hash == sha256(payload.checkout_token.encode()).hexdigest()))
    if token is None or token.items_hash != args_hash(args):
        raise MallError("checkout_invalid")
    result = await db.execute(update(CheckoutToken).where(CheckoutToken.id == token.id,
        CheckoutToken.consumed_at.is_(None), CheckoutToken.expires_at > now)
        .values(consumed_at=now).execution_options(synchronize_session=False))
    if result.rowcount != 1:
        raise MallError("checkout_expired_or_used")
    items = await price_items(db, args["items"])
    total = sum(item["total_cents"] for item in items) + await value(db, "mall_shipping_cents")
    if not 0 < total <= MAX_SAFE_CENTS:
        raise MallError("invalid_order_total", status=HTTPStatus.UNPROCESSABLE_ENTITY)
    row = Order(user_id=user_id, total_cents=total, currency=settings.mall_currency,
        expires_at=now + timedelta(seconds=settings.mall_reservation_seconds),
        address_snapshot=await AddressService(db).snapshot(user_id, payload.address_id))
    db.add(row)
    await db.flush()
    db.add_all([OrderItem(order_id=row.id, **item) for item in items])
    await service("inventory", db).reserve(row.id, items, expires_at=row.expires_at)
    db.add(OrderHistory(order_id=row.id, to_status=row.status, actor_id=user_id, version=0))
    await publish(db, row, event_type="mall.order.created", payload={"user_id": user_id, "order_id": row.id})
    await db.flush()
    return row
