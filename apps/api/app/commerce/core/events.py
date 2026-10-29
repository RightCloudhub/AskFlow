"""Transaction-local commerce events using the existing outbox envelope."""

from datetime import UTC, datetime
from uuid import uuid4

from app.commerce.core.constants import DEPLOYMENT, EVENT_SCHEMA_VERSION
from app.core.trace import get_trace_id
from app.services.outbox.store import emit


async def publish(db, row, *, event_type: str, payload: dict):
    envelope = {
        "event_id": str(uuid4()), "event_type": event_type, "tenant_id": DEPLOYMENT,
        "schema_version": EVENT_SCHEMA_VERSION, "occurred_at": datetime.now(UTC).isoformat(),
        "trace_id": get_trace_id(),
        "aggregate": {"type": row.__tablename__, "id": row.id, "version": row.version},
        "payload": payload,
    }
    return await emit(db, aggregate=row.__tablename__, aggregate_id=row.id,
                      event_type=event_type, payload=envelope)
