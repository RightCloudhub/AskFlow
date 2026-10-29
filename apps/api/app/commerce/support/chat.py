"""Deterministic mall actions retain Harness, ownership and Gateway confirmation."""

import re
from http import HTTPStatus
from types import SimpleNamespace
from uuid import uuid4

from app.commerce.core.audit import audit
from app.commerce.core.deps import Context
from app.commerce.core.errors import MallError
from app.commerce.core.services import service
from app.commerce.order.api import cancel, refund
from app.commerce.order.schemas import Change, RefundRequest
from app.commerce.support.reads import read
from app.core.trace import get_trace_id
from app.models.user import User
from app.plugins.runtime import get_app_context
from app.services.agent.assurance import conversation_assurance, user_assurance
from app.services.agent.harness.policy import Harness
from app.services.agent.pipeline.context import PipelineResult

ORDER_ID = re.compile(r"\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b")
CONFIRM = frozenset({"确认", "确认取消", "确认退款", "confirm"})


async def handle(db, conversation, *, text: str, history: list):
    ctx = get_app_context()
    if not available(ctx, conversation):
        return None
    if not Harness().prepare(text, history).allowed:
        return None
    pending = (conversation.metadata_json or {}).get("mall_pending")
    if pending and text.strip().lower() in CONFIRM:
        return await _perform(db, conversation, pending=pending, confirmed=True)
    if "钱包" in text and "余额" in text:
        return await _perform(db, conversation, pending={"action": "balance", "key": str(uuid4())}, confirmed=False)
    order_id = referenced_order(conversation, text)
    if not order_id:
        return None
    action = _intent(text)
    pending = {"order_id": order_id, "action": action, "key": str(uuid4())}
    return await _perform(db, conversation, pending=pending, confirmed=False)


def available(ctx, conversation):
    return bool(ctx and ctx.enabled("mall_support") and ctx.enabled("agent")
                and conversation.status == "active")


def referenced_order(conversation, text):
    matched = ORDER_ID.search(text)
    if matched:
        return matched.group()
    if any(word in text for word in ("订单", "退款", "物流", "到哪")):
        return (conversation.metadata_json or {}).get("mall_order_id")
    return None


async def _perform(db, conversation, *, pending, confirmed):
    try:
        user = await db.get(User, conversation.user_id)
        if user is None or not user.is_active:
            raise MallError("authentication_required", status=HTTPStatus.UNAUTHORIZED)
        assurance = conversation_assurance(conversation, await user_assurance(db, user.id))
        request = SimpleNamespace(headers={"idempotency-key": pending["key"]})
        ctx = Context(db, user, request, {"assurance": assurance})
        if pending["action"] in {"get", "logistics", "balance"}:
            return await _read_result(ctx, pending)
        order = await service("order", db).get(conversation.user_id, pending["order_id"])
        token = pending.get("confirmation_token", "") if confirmed else ""
        async with db.begin_nested():
            response = await _action(ctx, order, pending=pending, token=token)
    except MallError as exc:
        await audit(db, actor_id=conversation.user_id, action="chat_action_rejected",
                    detail={"action": pending["action"], "code": exc.code})
        return result("暂时无法执行：" + exc.code, {"mall_pending": None})
    if response.get("status") == "needs_confirmation":
        pending = {**pending, "confirmation_token": response["confirmation_token"], "version": order["version"]}
        return result("请回复“确认”以" + ("取消订单" if pending["action"] == "cancel" else "申请退款") + "。",
                      {"mall_pending": pending})
    return result("处理状态：" + response["status"], {"mall_pending": None})


def _intent(text):
    for word, action in (("退款", "refund"), ("取消", "cancel"), ("物流", "logistics"), ("到哪", "logistics")):
        if word in text:
            return action
    return "get"


async def _read_result(ctx, pending):
    names = {"get": "mall.order.get", "logistics": "mall.logistics.get", "balance": "mall.wallet.balance"}
    data = await read(ctx, names[pending["action"]], order_id=pending.get("order_id", ""))
    if pending["action"] == "balance":
        return result(f"钱包可用余额：{data['available_cents']} 分（{data['currency']}）。", {})
    tracking = "；模拟物流单号：" + data.get("tracking_number", "") if pending["action"] == "logistics" else ""
    return result("订单状态：" + data["status"] + tracking, {})


async def _action(ctx, order, *, pending, token):
    if pending["action"] == "cancel":
        payload = Change(expected_version=pending.get("version", order["version"]), confirmation_token=token)
        return await cancel(order["id"], payload, ctx)
    payload = RefundRequest(amount_cents=order["total_cents"] - order["refunded_cents"],
                            reason="customer_request", confirmation_token=token)
    return await refund(order["id"], payload, ctx)


def result(answer: str, metadata: dict):
    return PipelineResult(run_id=str(uuid4()), trace_id=get_trace_id() or "", answer=answer,
        route="tool", intent="order_status", confidence=1.0, metadata_patch=metadata)
