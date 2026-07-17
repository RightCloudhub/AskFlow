"""User-facing ticket CRUD (PRD §4.6)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.core.deps import CurrentUser, DbSession
from app.models.enums import TicketStatus
from app.schemas.ticket import TicketCreate, TicketOut, TicketUpdate
from app.services.ticket.repository.service import TicketRepository

router = APIRouter()


@router.post("", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
async def create_ticket(payload: TicketCreate, user: CurrentUser, db: DbSession) -> TicketOut:
    ticket, _ = await TicketRepository(db).create_or_get_open(user.id, payload)
    return TicketOut.model_validate(ticket)


@router.get("", response_model=list[TicketOut])
async def list_my_tickets(user: CurrentUser, db: DbSession) -> list[TicketOut]:
    rows = await TicketRepository(db).list_for_user(user.id)
    return [TicketOut.model_validate(r) for r in rows]


@router.get("/{ticket_id}", response_model=TicketOut)
async def get_ticket(ticket_id: str, user: CurrentUser, db: DbSession) -> TicketOut:
    ticket = await TicketRepository(db).get(ticket_id)
    if ticket is None or ticket.user_id != user.id:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return TicketOut.model_validate(ticket)


@router.patch("/{ticket_id}", response_model=TicketOut)
async def update_my_ticket(
    ticket_id: str,
    payload: TicketUpdate,
    user: CurrentUser,
    db: DbSession,
) -> TicketOut:
    repo = TicketRepository(db)
    ticket = await repo.get(ticket_id)
    if ticket is None or ticket.user_id != user.id:
        raise HTTPException(status_code=404, detail="Ticket not found")
    # users may only close their own tickets in MVP
    if payload.status and payload.status != TicketStatus.CLOSED.value:
        raise HTTPException(status_code=403, detail="Users may only close tickets")
    ticket = await repo.update_status(ticket, status=payload.status)
    return TicketOut.model_validate(ticket)
