"""Keyset pagination; search outages fall back to parameterized SQL."""

import base64
import json
from datetime import UTC, datetime

from sqlalchemy import and_, func, or_, select

from app.commerce.catalog.models import Sku, SkuPrice, Spu
from app.commerce.core.errors import MallError
from app.commerce.infra.runtime import infra


def cursor_value(raw: str):
    if not raw:
        return None
    try:
        price, key = json.loads(base64.urlsafe_b64decode(raw).decode())
        if type(price) is not int or not isinstance(key, str):
            raise ValueError("cursor")
        return price, key
    except (ValueError, TypeError, UnicodeError) as exc:
        raise MallError("invalid_cursor", status=422) from exc


async def search(db, payload):
    now = datetime.now(UTC)
    current = select(SkuPrice.id).where(SkuPrice.sku_id == Sku.id,
        SkuPrice.valid_from <= now, or_(SkuPrice.valid_to.is_(None), SkuPrice.valid_to > now))
    current = current.order_by(SkuPrice.valid_from.desc(), SkuPrice.id.desc()).limit(1).correlate(Sku).scalar_subquery()
    price = func.coalesce(SkuPrice.activity_cents, SkuPrice.sale_cents)
    statement = select(Sku.id, Sku.spu_id, Sku.title, Sku.currency, price.label("price_cents"))
    statement = statement.join(Spu, Spu.id == Sku.spu_id).join(SkuPrice, SkuPrice.id == current)
    statement = statement.where(Sku.status == "active", Spu.status == "active",
        price >= payload.min_cents)
    statement = await _filter(db, statement, payload)
    if payload.max_cents is not None:
        statement = statement.where(price <= payload.max_cents)
    boundary = cursor_value(payload.cursor)
    statement = _page(statement, payload, price=price, boundary=boundary)
    rows = list((await db.execute(statement.limit(payload.limit + 1))).mappings())
    items, cursor = [dict(row) for row in rows[:payload.limit]], None
    if len(rows) > payload.limit:
        last = items[-1]
        cursor = base64.urlsafe_b64encode(json.dumps([last["price_cents"], last["id"]]).encode()).decode()
    return {"items": items, "next_cursor": cursor}


async def _filter(db, statement, payload):
    if payload.category_id:
        statement = statement.where(Spu.category_id == payload.category_id)
    if not payload.q:
        return statement
    try:
        async with db.begin_nested():
            ids = await infra().search.ids(db, payload.q)
    except Exception:
        ids = None
    if ids is not None:
        return statement.where(Spu.id.in_(ids))
    return statement.where(or_(Spu.title.contains(payload.q, autoescape=True),
                               Spu.description.contains(payload.q, autoescape=True)))


def _page(statement, payload, *, price, boundary):
    if payload.sort == "id":
        if boundary:
            statement = statement.where(Sku.id > boundary[1])
        return statement.order_by(Sku.id)
    descending = payload.sort == "price_desc"
    if boundary:
        amount, key = boundary
        comparison = price < amount if descending else price > amount
        statement = statement.where(or_(comparison, and_(price == amount, Sku.id > key)))
    return statement.order_by(price.desc() if descending else price.asc(), Sku.id)
