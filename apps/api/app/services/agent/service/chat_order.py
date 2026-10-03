"""Authenticated order workflow for background chat tasks; upstream ownership is mandatory."""

from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select

from app.core.config import get_settings
from app.models.conversation import Conversation
from app.models.user import User
from app.services.agent.service.contracts import Environment, Evidence, Operation, Receipt
from app.services.agent.service.order import (
    ORDER_EVIDENCE_TTL_SECONDS, ORDER_OPERATION, ORDER_PERMISSION, OrderInput, OrderStatus,
    propose_order,
)
from app.services.agent.service.registry import OperationRegistry
from app.services.agent.service.runtime import AgentPolicy, ServiceAgent

CONNECTOR_TIMEOUT_SECONDS = 5.0
HTTP_SERVER_ERROR = 500
HTTP_BAD_REQUEST = 400
HTTP_FORBIDDEN = 403
HTTP_UNAUTHORIZED = 401


async def scoped_order(call, scope) -> Receipt:
    settings = get_settings()
    if not settings.order_lookup_url:
        return Receipt(status="failed", error_kind="unavailable", error="connector_not_configured")
    headers = {}
    if settings.order_lookup_token:
        headers["Authorization"] = f"Bearer {settings.order_lookup_token}"
    try:
        async with httpx.AsyncClient(timeout=CONNECTOR_TIMEOUT_SECONDS) as client:
            response = await client.get(settings.order_lookup_url, headers=headers, params={
                "order_id": call.arguments["order_id"], "customer_id": scope.customer_id,
            })
    except httpx.TransportError:
        return Receipt(status="failed", error_kind="transient", error="connector_transport")
    if response.status_code >= HTTP_SERVER_ERROR:
        return Receipt(status="failed", error_kind="transient", error="connector_unavailable")
    if response.status_code in {HTTP_UNAUTHORIZED, HTTP_FORBIDDEN}:
        return Receipt(status="failed", error_kind="permission", error="connector_permission")
    if response.status_code >= HTTP_BAD_REQUEST:
        return Receipt(status="failed", error_kind="permanent", error="connector_rejected")
    return _receipt(call, scope, data=response.json())


def _receipt(call, scope, *, data):
    if data.get("data_source") == "mock" or data.get("status") == "mock":
        return Receipt(status="mock", error_kind="simulated")
    if data.get("customer_id") != scope.customer_id:
        return Receipt(status="failed", error_kind="permission", error="ownership_unverified")
    if data.get("order_id") != call.arguments["order_id"]:
        return Receipt(status="failed", error_kind="conflict", error="order_mismatch")
    order = OrderStatus(order_id=data["order_id"], status=data.get("status", ""))
    return Receipt(status="succeeded", evidence=Evidence(
        operation_id=ORDER_OPERATION, source="scoped_order_webhook",
        data={**order.model_dump(), "customer_id": scope.customer_id},
        expires_at=datetime.now(UTC) + timedelta(seconds=ORDER_EVIDENCE_TTL_SECONDS),
    ))


def chat_order_agent(store, scope):
    async def observe(task):
        async with store.sessions() as db:
            user = await db.scalar(select(User).where(User.id == scope.customer_id, User.is_active))
            conv = await db.scalar(select(Conversation).where(
                Conversation.id == task.conversation_id, Conversation.user_id == scope.customer_id,
                Conversation.status == "active",
            ))
        permissions = frozenset({ORDER_PERMISSION}) if user and conv else frozenset()
        return Environment(scope=scope, permissions=permissions,
                           available_operations=frozenset({ORDER_OPERATION}))

    async def handler(call):
        return await scoped_order(call, scope)

    def verify(task, env):
        return ORDER_PERMISSION in env.permissions and any(
            e.operation_id == ORDER_OPERATION and e.data.get("customer_id") == scope.customer_id
            and e.data.get("order_id") == task.inputs.get("order_id") for e in task.evidence)

    op = Operation(operation_id=ORDER_OPERATION, version="scoped-1", effect="read",
                    permission=ORDER_PERMISSION, input_schema=OrderInput, handler=handler,
                    precondition=lambda args, env: True)
    return ServiceAgent(store, OperationRegistry([op]), AgentPolicy(
        observe=observe, propose=propose_order, verify=verify,
    ))
