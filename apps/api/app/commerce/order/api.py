"""Customer cart, checkout and owner-scoped orders."""

from fastapi import APIRouter

from app.commerce.core.commands import command
from app.commerce.core.deps import MallContext
from app.commerce.core.governance import governed
from app.commerce.order import cart, checkout, schemas
from app.commerce.order.refunds import RefundService
from app.commerce.order.service import OrderService
from app.services.agent.gateway.idempotency import args_hash

router = APIRouter()


@router.get("/cart")
async def cart_items(ctx: MallContext):
    return await cart.items(ctx.db, ctx.user.id)


@router.put("/cart/items")
async def cart_item(payload: schemas.Item, ctx: MallContext):
    return await command(ctx, "cart.item", payload=payload,
                         action=lambda: cart.set_item(ctx.db, ctx.user.id, payload))


@router.delete("/cart/items/{sku_id}")
async def remove_item(sku_id: str, ctx: MallContext):
    return await command(ctx, "cart.remove", payload={"sku_id": sku_id},
                         action=lambda: cart.remove(ctx.db, ctx.user.id, sku_id))


@router.post("/checkout")
async def quote(payload: schemas.Checkout, ctx: MallContext):
    return await command(ctx, "checkout", payload=payload,
                         action=lambda: checkout.prepare(ctx.db, ctx.user.id, payload))


@router.post("/orders")
async def place(payload: schemas.PlaceOrder, ctx: MallContext):
    return await command(ctx, "order.place", payload=payload,
                         action=lambda: OrderService(ctx.db).place(ctx.user.id, payload))


@router.get("/orders")
async def orders(ctx: MallContext, cursor: str = "", status: str = ""):
    return await OrderService(ctx.db).list(ctx.user.id, cursor=cursor, status=status)


@router.get("/orders/{order_id}")
async def order(order_id: str, ctx: MallContext):
    return await OrderService(ctx.db).get(ctx.user.id, order_id)


@router.get("/orders/{order_id}/logistics")
async def logistics(order_id: str, ctx: MallContext):
    data = await OrderService(ctx.db).get(ctx.user.id, order_id)
    return {"order_id": order_id, "status": data["fulfillment_status"],
            "tracking_number": data["tracking_number"], "data_source": "mock"}


@router.post("/orders/{order_id}/cancel")
async def cancel(order_id: str, payload: schemas.Change, ctx: MallContext):
    await OrderService(ctx.db).get(ctx.user.id, order_id)
    args = {"order_id": order_id, **payload.model_dump(exclude={"confirmation_token"})}
    return await governed(ctx, "mall.order.cancel", arguments=args, confirmation=payload.confirmation_token,
        action=lambda _review: OrderService(ctx.db).cancel(ctx.user.id, order_id,
                                                          expected_version=payload.expected_version))


@router.post("/orders/{order_id}/refunds")
async def refund(order_id: str, payload: schemas.RefundRequest, ctx: MallContext):
    await OrderService(ctx.db).get(ctx.user.id, order_id)
    args = {"order_id": order_id, **payload.model_dump(exclude={"confirmation_token"})}
    key = args_hash({"user_id": ctx.user.id, "key": ctx.key, "order_id": order_id})
    return await governed(ctx, "mall.refund.submit", arguments=args, confirmation=payload.confirmation_token,
        action=lambda review: RefundService(ctx.db).request(ctx.user.id, order_id=order_id,
            payload=payload, key=key, force_review=review))


@router.post("/orders/{order_id}/received")
async def received(order_id: str, payload: schemas.Versioned, ctx: MallContext):
    change = schemas.Transition(expected_version=payload.expected_version, status="DELIVERED")
    return await command(ctx, "order.received:" + order_id, payload=payload,
        action=lambda: OrderService(ctx.db).advance(ctx.user.id, order_id, payload=change, actor_id=ctx.user.id))


@router.get("/refunds/{refund_id}")
async def refund_detail(refund_id: str, ctx: MallContext):
    return await RefundService(ctx.db).get(ctx.user.id, refund_id)


@router.get("/refunds")
async def refund_list(ctx: MallContext, cursor: str = ""):
    return await RefundService(ctx.db).list(ctx.user.id, cursor=cursor)
