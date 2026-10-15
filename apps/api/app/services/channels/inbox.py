"""Replay-safe webhook ingestion: dedup, ordered claims, at-least-once processing (arch §9.1)."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import exists, select, tuple_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased

from app.models.channel_inbox import ChannelInbox
from app.services.channels.canonical import CanonicalMessage

LEASE_SECONDS = 60
ERROR_LENGTH = 255


async def record_inbound(db, message: CanonicalMessage) -> ChannelInbox | None:
    """Insert-once keyed on (channel, message id); None when the webhook is a replay."""
    row = ChannelInbox(
        channel=message.channel,
        channel_message_id=message.channel_message_id,
        session_key=message.session_key,
        payload=message.to_payload(),
    )
    try:
        async with db.begin_nested():
            db.add(row)
        return row
    except IntegrityError:
        return None


async def claim_batch(db, *, limit: int, max_attempts: int) -> list[ChannelInbox]:
    """Claim at most one unpublished head row per session, skipping rows under retry."""
    earlier = aliased(ChannelInbox)
    now = datetime.now(UTC)
    lease_free = (ChannelInbox.lease_until.is_(None)) | (ChannelInbox.lease_until <= now)
    has_earlier = exists(
        select(1).select_from(earlier).where(
            earlier.published_at.is_(None),
            earlier.session_key == ChannelInbox.session_key,
            tuple_(earlier.created_at, earlier.id)
            < tuple_(ChannelInbox.created_at, ChannelInbox.id),
        )
    )
    rows = list(
        await db.scalars(
            select(ChannelInbox)
            .where(
                ChannelInbox.published_at.is_(None),
                ChannelInbox.attempts < max_attempts,
                lease_free,
                ~has_earlier,
            )
            .order_by(ChannelInbox.created_at, ChannelInbox.id)
            .limit(limit)
        )
    )
    claimed: list[ChannelInbox] = []
    for row in rows:
        result = await db.execute(
            update(ChannelInbox)
            .where(
                ChannelInbox.id == row.id,
                ChannelInbox.published_at.is_(None),
                (ChannelInbox.lease_until.is_(None)) | (ChannelInbox.lease_until <= now),
            )
            .values(
                lease_token=str(uuid4()),
                lease_until=datetime.now(UTC) + timedelta(seconds=LEASE_SECONDS),
            )
            .execution_options(synchronize_session=False)
        )
        if result.rowcount == 1:
            claimed.append(row)
    await db.commit()
    return claimed


async def mark_published(db, row: ChannelInbox) -> None:
    await db.execute(
        update(ChannelInbox)
        .where(ChannelInbox.id == row.id)
        .values(published_at=datetime.now(UTC), lease_token=None, lease_until=None, last_error=None)
        .execution_options(synchronize_session=False)
    )


async def record_failure(db, row: ChannelInbox, error: str) -> None:
    await db.execute(
        update(ChannelInbox)
        .where(ChannelInbox.id == row.id)
        .values(
            attempts=ChannelInbox.attempts + 1,
            last_error=error[:ERROR_LENGTH],
            lease_token=None,
            lease_until=None,
        )
        .execution_options(synchronize_session=False)
    )
