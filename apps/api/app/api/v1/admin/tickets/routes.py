"""Admin / agent ticket list and updates."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import DbSession, require_agent_or_admin
from app.models.user import User
from app.schemas.ticket import TicketOut, TicketUpdate
from app.services.ticket.repository.service import TicketRepository

router = APIRouter(dependencies=[Depends(require_agent_or_admin)])


@router.get("", response_model=list[TicketOut])
async def list_tickets(
    db: DbSession,
    status: str | None = None,
    _user: User = Depends(require_agent_or_admin),
) -> list[TicketOut]:
    rows = await TicketRepository(db).list_all(status=status)
    return [TicketOut.model_validate(r) for r in rows]


@router.patch("/{ticket_id}", response_model=TicketOut)
async def update_ticket(
    ticket_id: str,
    payload: TicketUpdate,
    db: DbSession,
    _user: User = Depends(require_agent_or_admin),
) -> TicketOut:
    repo = TicketRepository(db)
    ticket = await repo.get(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket = await repo.update_status(
        ticket,
        status=payload.status,
        priority=payload.priority,
        assignee=payload.assignee,
        description=payload.description,
    )
    return TicketOut.model_validate(ticket)
