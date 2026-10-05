"""Submit a refund once, then independently verify settlement or confirmation."""

from pydantic import Field

from app.services.agent.domains.order import owns_order
from app.services.agent.domains.receipts import connector_receipt
from app.services.agent.intake.goals import GOAL_REFUND_REQUEST
from app.services.agent.service.contracts import (
    DEFAULT_TIMEOUT_SECONDS,
    Candidate,
    Operation,
    OperationCall,
    Record,
)
from app.services.agent.service.registry import OperationRegistry
from app.services.agent.service.runtime import AgentPolicy, ServiceAgent

REFUND_GOAL = GOAL_REFUND_REQUEST
REFUND_OPERATION = "refund.submit"
REFUND_STATUS_OPERATION = "refund.get_status"
REFUND_PERMISSION = "refunds.write"
REFUND_STATUS_PERMISSION = "refunds.read"
REFUND_COMPENSATION = "irreversible:refund.submit"
CONFIRMATION_SOURCES = {"refund_connector", "customer_confirmed", "staff_confirmed"}
SETTLED_STATUSES = {"refunded", "received"}


class RefundInput(Record):
    order_id: str = Field(min_length=1)
    amount_cents: int = Field(gt=0, strict=True)
    reason: str = Field(min_length=1)


class RefundStatusInput(Record):
    order_id: str = Field(min_length=1)


def refund_operations(
    *, submit, status_query, submit_timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
) -> list[Operation]:
    async def submit_refund(call):
        data = await submit(call)
        receipt = connector_receipt(call, data, source="refund_connector")
        if receipt.status == "succeeded" and not data.get("refund_id"):
            raise ValueError("Refund submission requires a receipt identifier")
        return receipt

    async def query_status(call):
        data = await status_query(call)
        if data.get("order_id") != call.arguments["order_id"]:
            raise ValueError("Refund order mismatch")
        return connector_receipt(call, data, source="refund_connector")

    return [
        Operation(
            operation_id=REFUND_OPERATION,
            version="1",
            effect="write",
            permission=REFUND_PERMISSION,
            input_schema=RefundInput,
            handler=submit_refund,
            precondition=owns_order,
            compensation=REFUND_COMPENSATION,
            timeout_seconds=submit_timeout_seconds,
            replay_receipts_when_waiting=True,
        ),
        Operation(
            operation_id=REFUND_STATUS_OPERATION,
            version="1",
            effect="read",
            permission=REFUND_STATUS_PERMISSION,
            input_schema=RefundStatusInput,
            handler=query_status,
            precondition=owns_order,
        ),
    ]


async def propose_refund(task, _env):
    submitted = any(e.operation_id == REFUND_OPERATION for e in task.evidence)
    operation = REFUND_STATUS_OPERATION if submitted else REFUND_OPERATION
    args = {"order_id": task.inputs["order_id"]} if submitted else task.inputs
    return [
        Candidate(
            call=OperationCall(
                operation_id=operation, key=f"{task.task_id}:{operation}", arguments=args
            ),
            reason="Verify settlement" if submitted else "Submit the authorized refund",
        )
    ]


def verify_refund(task, env) -> bool:
    args = RefundStatusInput.model_validate({"order_id": task.inputs["order_id"]})
    authorized = REFUND_STATUS_PERMISSION in env.permissions and owns_order(args, env)
    if task.completion_condition != REFUND_GOAL or not authorized:
        return False
    return any(
        e.operation_id == REFUND_STATUS_OPERATION
        and e.source in CONFIRMATION_SOURCES
        and e.data.get("order_id") == args.order_id
        and e.data.get("refund_status") in SETTLED_STATUSES
        for e in task.evidence
    )


def refund_agent(store, observe, *, submit, status_query):
    registry = OperationRegistry(refund_operations(submit=submit, status_query=status_query))
    return ServiceAgent(
        store, registry, AgentPolicy(observe=observe, propose=propose_refund, verify=verify_refund)
    )
