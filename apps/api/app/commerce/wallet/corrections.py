"""Append compensating evidence; never rewrite a journal or a reconciliation finding."""

from sqlalchemy import select

from app.commerce.core.errors import MallError
from app.commerce.core.repository import cas
from app.commerce.core.schemas import view
from app.commerce.wallet.journal import reverse
from app.commerce.wallet.models import JournalEntry
from app.commerce.wallet.operations_models import ReconciliationDiff
from app.commerce.wallet.reversal_models import ReversalRequest

FIELDS = ("id", "original_id", "requested_by", "approved_by", "journal_id",
          "reason", "status", "version")


async def request_reversal(ctx, payload):
    if await ctx.db.get(JournalEntry, payload.journal_id) is None:
        raise MallError("resource_not_found", status=404)
    row = ReversalRequest(original_id=payload.journal_id, requested_by=ctx.user.id,
                          reason=payload.reason)
    ctx.db.add(row)
    await ctx.db.flush()
    return view(row, FIELDS)


async def approve_reversal(ctx, request_id: str, payload):
    row = await ctx.db.scalar(select(ReversalRequest).where(ReversalRequest.id == request_id)
                              .with_for_update().execution_options(populate_existing=True))
    if row is None:
        raise MallError("resource_not_found", status=404)
    if row.requested_by == ctx.user.id:
        raise MallError("dual_control_required", status=403)
    if row.status != "pending" or row.version != payload.expected_version:
        raise MallError("version_conflict")
    journal = None
    if payload.approved:
        journal = await reverse(ctx.db, row.original_id, business_key="reversal:" + row.id,
                                actor_id=ctx.user.id)
    await cas(ctx.db, row, values={"status": "approved" if payload.approved else "rejected",
                                   "approved_by": ctx.user.id,
                                   "journal_id": journal.id if journal else None})
    return view(row, FIELDS)


async def resolve_difference(ctx, difference_id: str, payload):
    row = await ctx.db.scalar(select(ReconciliationDiff).where(
        ReconciliationDiff.id == difference_id).with_for_update())
    if row is None:
        raise MallError("resource_not_found", status=404)
    if row.version != payload.expected_version or row.status != "open":
        raise MallError("version_conflict")
    before = view(row, ("status", "resolution_ref", "version"))
    await cas(ctx.db, row, values={"status": "reviewed", "resolution_ref": payload.reference})
    return {"id": row.id, "before": before,
            **view(row, ("status", "resolution_ref", "version"))}
