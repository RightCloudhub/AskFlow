"""Serialize relation creation so concurrent reciprocal invitations cannot form a cycle."""

from datetime import UTC, datetime

from sqlalchemy import select

from app.commerce.core.errors import MallError
from app.commerce.core.models import WorkerLease
from app.commerce.core.repository import insert_once
from app.commerce.referral.models import ReferralRelation

GRAPH_LOCK = "mall:referral:graph"
MAX_ANCESTORS = 1024


async def ensure_acyclic(db, *, inviter_id: str, invitee_id: str):
    await insert_once(db, WorkerLease, values={"key": GRAPH_LOCK, "owner": "",
        "expires_at": datetime.now(UTC)}, unique=["key"])
    await db.scalar(select(WorkerLease).where(WorkerLease.key == GRAPH_LOCK).with_for_update())
    current = inviter_id
    for _ in range(MAX_ANCESTORS):
        if current == invitee_id:
            raise MallError("invalid_invitation")
        parent = await db.scalar(select(ReferralRelation.inviter_id).where(ReferralRelation.invitee_id == current))
        if parent is None:
            return
        current = parent
    raise MallError("invitation_depth_limit")
