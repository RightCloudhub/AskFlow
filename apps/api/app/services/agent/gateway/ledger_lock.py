"""Serialize the shared ledger chain when commerce adds concurrent writers."""

from sqlalchemy import text

from app.plugins.runtime import get_app_context

LEDGER_ADVISORY_KEY = 1095976518


async def acquire(db):
    ctx = get_app_context()
    if ctx is None or not ctx.enabled("mall_core"):
        return
    if db.bind.dialect.name == "postgresql":
        await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": LEDGER_ADVISORY_KEY})
    else:
        # A no-row write obtains SQLite's writer lock before reading the chain tip.
        await db.execute(text("UPDATE operation_ledger SET seq = seq WHERE 1 = 0"))
