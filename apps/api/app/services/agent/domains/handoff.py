"""Queue once and require observed human acceptance before resolving."""

from pydantic import Field

from app.services.agent.domains.receipts import receipt_for
from app.services.agent.intake.goals import GOAL_HUMAN_HANDOFF
from app.services.agent.service.contracts import Candidate, Operation, OperationCall, Record
from app.services.agent.service.registry import OperationRegistry
from app.services.agent.service.runtime import AgentPolicy, ServiceAgent
from app.services.handoff.service import HandoffService

HANDOFF_GOAL = GOAL_HUMAN_HANDOFF
HANDOFF_OPERATION = "handoff.enqueue"
HANDOFF_PERMISSION = "handoffs.write"
HANDOFF_COMPENSATION = "owner_review:handoff.cancel"


class HandoffInput(Record):
    conversation_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    summary: str = ""
    intent: str = "handoff"


def handoff_operations(sessions) -> list[Operation]:
    async def enqueue(call):
        args = HandoffInput.model_validate(call.arguments)
        async with sessions.begin() as db:
            row = await HandoffService(db).enqueue(**args.model_dump())
            if row.user_id != args.user_id:
                raise PermissionError("handoff_owner_mismatch")
            data = {
                "handoff_id": row.id,
                "status": row.status,
                "conversation_id": row.conversation_id,
                "user_id": row.user_id,
            }
        return receipt_for(call, data, source="handoff_store")

    return [
        Operation(
            operation_id=HANDOFF_OPERATION,
            version="1",
            effect="write",
            permission=HANDOFF_PERMISSION,
            input_schema=HandoffInput,
            handler=enqueue,
            precondition=lambda args, env: args.user_id == env.scope.customer_id,
            compensation=HANDOFF_COMPENSATION,
            replay_receipts_when_waiting=True,
        )
    ]


async def propose_handoff(task, _env):
    return [
        Candidate(
            call=OperationCall(
                operation_id=HANDOFF_OPERATION,
                key=f"handoff:{task.conversation_id}",
                arguments=task.inputs,
            ),
            reason="Queue the customer's request for a human",
        )
    ]


def verify_handoff(task, env) -> bool:
    if task.completion_condition != HANDOFF_GOAL or HANDOFF_PERMISSION not in env.permissions:
        return False
    return env.facts.get("handoff_status") == "claimed" and any(
        e.operation_id == HANDOFF_OPERATION
        and e.source == "handoff_store"
        and bool(e.data.get("handoff_id"))
        for e in task.evidence
    )


def handoff_agent(store, observe):
    return ServiceAgent(
        store,
        OperationRegistry(handoff_operations(store.sessions)),
        AgentPolicy(observe=observe, propose=propose_handoff, verify=verify_handoff),
    )
