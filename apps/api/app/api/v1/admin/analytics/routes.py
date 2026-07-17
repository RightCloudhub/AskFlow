from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.core.deps import DbSession, require_admin
from app.models.conversation import Message
from app.models.cost_entry import CostLedgerEntry
from app.models.feedback import Feedback
from app.models.handoff import HandoffSession
from app.models.knowledge import KnowledgeGap
from app.models.notify import NotificationLog
from app.models.ticket import Ticket
from app.models.user import User
from app.services.agent.cost.store import CostStore

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/summary")
async def analytics_summary(db: DbSession, _user: User = Depends(require_admin)) -> dict:
    async def count(model) -> int:
        r = await db.execute(select(func.count()).select_from(model))
        return int(r.scalar_one() or 0)

    tickets_open = await db.execute(
        select(func.count()).select_from(Ticket).where(Ticket.status.in_(["pending", "processing"]))
    )
    handoffs_queued = await db.execute(
        select(func.count()).select_from(HandoffSession).where(HandoffSession.status == "queued")
    )
    gaps_open = await db.execute(
        select(func.count()).select_from(KnowledgeGap).where(KnowledgeGap.status == "open")
    )
    thumbs_down = await db.execute(
        select(func.count()).select_from(Feedback).where(Feedback.rating == -1)
    )
    sla_breached = await db.execute(
        select(func.count()).select_from(Ticket).where(Ticket.sla_state == "breached")
    )
    handoff_timeouts = await db.execute(
        select(func.count())
        .select_from(HandoffSession)
        .where(HandoffSession.status == "timed_out")
    )
    notifies = await count(NotificationLog)
    messages = await count(Message)
    cost = await CostStore(db).aggregate()
    cost_usd = sum(p["estimated_usd"] for p in cost.get("by_purpose") or [])

    return {
        "messages": messages,
        "tickets_open": int(tickets_open.scalar_one() or 0),
        "handoffs_queued": int(handoffs_queued.scalar_one() or 0),
        "gaps_open": int(gaps_open.scalar_one() or 0),
        "thumbs_down": int(thumbs_down.scalar_one() or 0),
        "sla_breached": int(sla_breached.scalar_one() or 0),
        "handoff_timeouts": int(handoff_timeouts.scalar_one() or 0),
        "notifications": notifies,
        "cost_estimated_usd": round(cost_usd, 6),
        "cost": cost,
    }
