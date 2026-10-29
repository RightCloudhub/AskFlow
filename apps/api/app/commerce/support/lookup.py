"""Scoped in-process and token-protected HTTP order connector contracts."""

import hmac
from http import HTTPStatus

from fastapi import APIRouter, Request

from app.commerce.core.deps import MallDb
from app.commerce.core.errors import MallError
from app.commerce.order.service import OrderService
from app.core import database
from app.core.config import get_settings
from app.services.agent.domains.order import _receipt

router = APIRouter()


async def lookup(db, *, order_id: str, customer_id: str):
    order = await OrderService(db).get(customer_id, order_id)
    return {"order_id": order["id"], "customer_id": order["user_id"],
            "status": order["status"].lower(), "data_source": "mall_database"}


async def scoped(call, scope):
    from app.services.agent.service.contracts import Receipt

    async with database.SessionLocal() as db:
        try:
            result = await lookup(db, order_id=call.arguments["order_id"], customer_id=scope.customer_id)
        except MallError:
            return Receipt(status="failed", error_kind="permission", error="order_unavailable")
    return _receipt(call, scope, data=result)


@router.get("/internal/mall/orders/lookup")
async def internal(request: Request, db: MallDb, *, order_id: str, customer_id: str):
    token = get_settings().order_lookup_token
    supplied = request.headers.get("authorization", "").removeprefix("Bearer ")
    if not token or not hmac.compare_digest(token, supplied):
        raise MallError("authentication_required", status=HTTPStatus.UNAUTHORIZED)
    return await lookup(db, order_id=order_id, customer_id=customer_id)
