"""Ticket writes use the same convergent repository as the legacy chat path."""

from hashlib import sha256
from typing import Literal

from pydantic import Field

from app.schemas.ticket import TicketCreate
from app.services.agent.domains.receipts import receipt_for
from app.services.agent.intake.goals import GOAL_TICKET_RESOLUTION
from app.services.agent.service.contracts import Candidate, Operation, OperationCall, Record
from app.services.agent.service.registry import OperationRegistry
from app.services.agent.service.runtime import AgentPolicy, ServiceAgent
from app.services.ticket.repository.service import TicketRepository

TICKET_GOAL = GOAL_TICKET_RESOLUTION
TICKET_OPERATION = "ticket.create"
TICKET_PERMISSION = "tickets.write"
TICKET_COMPENSATION = "owner_review:ticket.cancel"
MAX_TITLE_LENGTH = 255


class TicketInput(Record):
    conversation_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=MAX_TITLE_LENGTH)
    description: str = ""
    ticket_type: str = "fault_report"
    priority: Literal["low", "medium", "high", "urgent"] = "high"


def ticket_operations(sessions) -> list[Operation]:
    async def create(call):
        args = TicketInput.model_validate(call.arguments)
        payload = TicketCreate(
            title=" ".join(args.title.split()),
            description=args.description,
            type=args.ticket_type,
            priority=args.priority,
            conversation_id=args.conversation_id,
        )
        async with sessions.begin() as db:
            row, _created = await TicketRepository(db).create_or_get_open(args.user_id, payload)
            data = {
                "ticket_id": row.id,
                "status": row.status,
                "user_id": row.user_id,
                "conversation_id": row.conversation_id,
            }
        return receipt_for(call, data, source="ticket_store")

    return [
        Operation(
            operation_id=TICKET_OPERATION,
            version="1",
            effect="write",
            permission=TICKET_PERMISSION,
            input_schema=TicketInput,
            handler=create,
            precondition=lambda args, env: args.user_id == env.scope.customer_id,
            compensation=TICKET_COMPENSATION,
            replay_receipts_when_waiting=True,
        )
    ]


async def propose_ticket(task, _env):
    args = TicketInput.model_validate(task.inputs)
    title_hash = sha256(" ".join(args.title.split()).encode()).hexdigest()
    return [
        Candidate(
            call=OperationCall(
                operation_id=TICKET_OPERATION,
                key=f"ticket:{args.conversation_id}:{args.ticket_type}:{title_hash}",
                arguments=args.model_dump(),
            ),
            reason="Create or locate the customer's open ticket",
        )
    ]


def verify_ticket(task, env) -> bool:
    if task.completion_condition != TICKET_GOAL or TICKET_PERMISSION not in env.permissions:
        return False
    return any(
        e.operation_id == TICKET_OPERATION
        and e.source == "ticket_store"
        and e.data.get("user_id") == env.scope.customer_id
        and e.data.get("conversation_id") == task.conversation_id
        and bool(e.data.get("ticket_id"))
        for e in task.evidence
    )


def ticket_agent(store, observe):
    return ServiceAgent(
        store,
        OperationRegistry(ticket_operations(store.sessions)),
        AgentPolicy(observe=observe, propose=propose_ticket, verify=verify_ticket),
    )
