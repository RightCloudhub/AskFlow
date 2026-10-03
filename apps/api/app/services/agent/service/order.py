"""Order-status scenario using the existing connector and application-owned authorization."""

from datetime import UTC, datetime, timedelta
from typing import Awaitable, Callable

from pydantic import Field, field_validator

from app.services.agent.service.contracts import (
    Candidate, Environment, Evidence, Operation, OperationCall, Receipt, Record, Task,
)
from app.services.agent.service.registry import OperationRegistry
from app.services.agent.service.runtime import AgentPolicy, ServiceAgent
from app.services.agent.service.store import TaskStore
from app.services.tools.search_order.handler import search_order

ORDER_OPERATION = "order.get_status"
ORDER_PERMISSION = "orders.read"
ORDER_GOAL = "order_status"
ORDER_EVIDENCE_TTL_SECONDS = 60
CONNECTOR_ERRORS = {
    "bad_params": "invalid_input", "auth": "permission", "http_4xx": "permanent",
    "timeout": "transient", "http_5xx": "unavailable",
}


class OrderInput(Record):
    order_id: str = Field(min_length=1)


class OrderStatus(Record):
    order_id: str
    status: str = Field(min_length=1)

    @field_validator("status")
    @classmethod
    def concrete_status(cls, value: str) -> str:
        value = value.strip()
        if not value or value.lower() in {"unknown", "mock", "unavailable"}:
            raise ValueError("Order connector did not return a concrete status")
        return value


def owns_order(args: OrderInput, env: Environment) -> bool:
    """The host must obtain this mapping from its authenticated business service."""
    owners = env.facts.get("order_owners", {})
    return owners.get(args.order_id) == env.scope.customer_id


async def query_order(call: OperationCall) -> Receipt:
    result = await search_order(call.arguments)
    if result.get("status") == "mock" or result.get("data_source") == "mock":
        return Receipt(status="mock", error_kind="simulated", error="live_order_unavailable")
    if result.get("status") != "ok":
        kind = CONNECTOR_ERRORS.get(result.get("error_class"), "permanent")
        return Receipt(status="failed", error_kind=kind, error="order_connector_failed")
    data = result.get("data") or {}
    returned_id = data.get("order_id", result.get("order_id"))
    if returned_id != call.arguments["order_id"]:
        return Receipt(status="failed", error_kind="conflict", error="order_identity_mismatch")
    verified = OrderStatus(order_id=returned_id, status=data.get("status", ""))
    return Receipt(status="succeeded", evidence=Evidence(
        operation_id=ORDER_OPERATION, source="order_webhook", data=verified.model_dump(),
        expires_at=datetime.now(UTC) + timedelta(seconds=ORDER_EVIDENCE_TTL_SECONDS),
    ))


async def propose_order(task: Task, env: Environment) -> list[Candidate]:
    args = OrderInput.model_validate(task.inputs)
    return [Candidate(
        call=OperationCall(operation_id=ORDER_OPERATION, arguments=args.model_dump(),
                           key=f"{task.task_id}:order_status"),
        reason="Query the authorized order's current status",
    )]


def verify_order(task: Task, env: Environment) -> bool:
    args = OrderInput.model_validate(task.inputs)
    authorized = ORDER_PERMISSION in env.permissions and owns_order(args, env)
    if task.completion_condition != ORDER_GOAL or not authorized:
        return False
    return any(e.operation_id == ORDER_OPERATION and e.data.get("order_id") == args.order_id
               and bool(e.data.get("status")) for e in task.evidence)


def order_agent(
    store: TaskStore, observe: Callable[[Task], Awaitable[Environment]],
) -> ServiceAgent:
    """Caller supplies fresh identity, ownership, permissions and connector health each tick."""
    op = Operation(
        operation_id=ORDER_OPERATION, version="1", effect="read", permission=ORDER_PERMISSION,
        input_schema=OrderInput, handler=query_order, precondition=owns_order,
    )
    return ServiceAgent(store, OperationRegistry([op]), AgentPolicy(
        observe=observe, propose=propose_order, verify=verify_order,
    ))
