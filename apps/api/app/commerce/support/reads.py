"""Authenticated offline reads share Gateway policy and immutable evidence."""

from uuid import uuid4

from app.commerce.core.errors import MallError
from app.commerce.core.services import service
from app.commerce.support.capabilities import CAPABILITIES
from app.core import database
from app.services.agent.gateway.context import ExecContext
from app.services.agent.gateway.gateway import ActionGateway
from app.services.agent.gateway.ledger import LedgerStore
from app.services.agent.service.contracts import Scope


async def read(ctx, name: str, *, order_id: str = ""):
    spec = CAPABILITIES[name]
    execution = ExecContext(scope=Scope(organization_id="deployment", customer_id=ctx.user.id),
        assurance=ctx.claims.get("assurance", 1), turn_id=str(uuid4()), step=name)
    gateway = ActionGateway(LedgerStore(database.SessionLocal))
    args = {"order_id": order_id} if order_id else {}
    decision = gateway.evaluate(capability=spec, args=args, ctx=execution)
    if not decision.allow:
        await gateway.record_decision(capability=spec, args=args, ctx=execution,
                                      decision=decision, status="DENIED", db=ctx.db)
        raise MallError("step_up_required", status=403, persist=True)
    try:
        data = await _load(ctx, name, order_id=order_id)
    except MallError as exc:
        await gateway.record_decision(capability=spec, args=args, ctx=execution,
            decision=decision, status="DENIED", error={"code": exc.code}, db=ctx.db)
        raise
    await gateway.record_decision(capability=spec, args=args, ctx=execution,
                                  decision=decision, status="EXECUTED", db=ctx.db)
    return data


async def _load(ctx, name: str, *, order_id: str):
    if name == "mall.wallet.balance":
        return await service("wallet", ctx.db).balance(ctx.user.id)
    order = await service("order", ctx.db).get(ctx.user.id, order_id)
    if name == "mall.logistics.get":
        return {"status": order["fulfillment_status"],
                "tracking_number": order["tracking_number"], "data_source": "mock"}
    return order
