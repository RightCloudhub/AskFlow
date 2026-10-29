"""Database guards apply in both development fixtures and migrated deployments."""

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import DBAPIError

from app.commerce.wallet.models import JournalEntry, Posting
from app.commerce.wallet.service import WalletService
from .helpers import seed, transaction


@pytest.mark.asyncio
async def test_financial_rows_cannot_be_rewritten_or_deleted(mall_runtime):
    identity = await seed(mall_runtime)
    await transaction(mall_runtime, lambda db: WalletService(db).credit(identity["user_id"], 100, key="original"))
    statements = [update(Posting).values(amount_cents=999), delete(Posting),
                  update(JournalEntry).values(description="tampered"), delete(JournalEntry)]
    for statement in statements:
        async with mall_runtime.sessions() as db:
            with pytest.raises(DBAPIError):
                await db.execute(statement)
            await db.rollback()
    async with mall_runtime.sessions() as db:
        assert len(list(await db.scalars(select(Posting)))) == 2
