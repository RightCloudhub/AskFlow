"""Read aggregate financial invariants without altering financial records."""

from sqlalchemy import case, func, select

from app.commerce.wallet.models import Posting
from app.commerce.wallet.operations_models import ReconciliationDiff


async def snapshot(db):
    unbalanced = select(Posting.journal_id).group_by(Posting.journal_id).having(
        func.sum(case((Posting.side == "debit", Posting.amount_cents), else_=-Posting.amount_cents)) != 0)
    count = await db.scalar(select(func.count()).select_from(unbalanced.subquery()))
    diffs = await db.scalar(select(func.count()).select_from(ReconciliationDiff).where(
        ReconciliationDiff.status == "open"))
    return {"unbalanced_journals": count, "reconciliation_diffs": diffs}
