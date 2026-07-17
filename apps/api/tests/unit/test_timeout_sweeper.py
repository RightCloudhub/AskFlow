"""Handoff timeout unit (repository-level)."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.models.conversation import Conversation
from app.models.enums import ConversationStatus, HandoffStatus, UserRole
from app.models.handoff import HandoffSession
from app.models.user import User
from app.core.security import hash_password
from app.services.handoff.timeout import HandoffTimeoutSweeper
from app.core.config import Settings


@pytest.mark.asyncio
async def test_sweep_creates_ticket_and_reactivates():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as db:
        user = User(
            username="u1",
            email="u1@e.com",
            hashed_password=hash_password("password123"),
            role=UserRole.USER.value,
        )
        db.add(user)
        await db.flush()
        conv = Conversation(user_id=user.id, title="c", status=ConversationStatus.TRANSFERRED.value)
        db.add(conv)
        await db.flush()
        hs = HandoffSession(
            conversation_id=conv.id,
            user_id=user.id,
            status=HandoffStatus.QUEUED.value,
            summary="need human",
        )
        db.add(hs)
        await db.flush()
        hs.created_at = datetime.now(UTC) - timedelta(hours=1)
        await db.flush()

        settings = Settings(
            ASKFLOW_ENV="test",
            SECRET_KEY="test-secret-key-not-for-prod",
            handoff_timeout_seconds=60,
        )
        sweeper = HandoffTimeoutSweeper(db)
        sweeper.settings = settings
        outcomes = await sweeper.sweep()
        await db.commit()

        assert len(outcomes) == 1
        await db.refresh(hs)
        await db.refresh(conv)
        assert hs.status == HandoffStatus.TIMED_OUT.value
        assert conv.status == ConversationStatus.ACTIVE.value
        assert outcomes[0]["ticket_id"]

    await engine.dispose()
