"""Append-only ledger with a hash chain; a status change is a new row (arch §4.11)."""

from dataclasses import dataclass
from hashlib import sha256
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.operation_ledger import OperationLedgerEntry

STATUS_INTENT = "INTENT"
STATUS_EXECUTED = "EXECUTED"
STATUS_FAILED = "FAILED"
STATUS_OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
STATUS_VERIFIED = "VERIFIED"
STATUS_COMPENSATED = "COMPENSATED"
STATUS_DENIED = "DENIED"
STATUS_NEEDS_CONFIRMATION = "NEEDS_CONFIRMATION"

REPLAYABLE_STATUSES = frozenset({STATUS_EXECUTED, STATUS_VERIFIED})


@dataclass(frozen=True)
class LedgerAppend:
    organization_id: str
    customer_id: str
    capability: str
    capability_version: str
    args_hash: str
    idempotency_key: str
    policy_decision: dict
    policy_version: str
    status: str
    actor: str = "agent"
    task_id: str | None = None
    turn_id: str | None = None
    step: str | None = None
    external_ref: str | None = None
    error: dict | None = None
    latency_ms: int | None = None
    cost: dict | None = None


class LedgerStore:
    def __init__(self, sessions: async_sessionmaker[AsyncSession] | None = None) -> None:
        self.sessions = sessions

    def _require_sessions(self):
        if self.sessions is None:
            raise RuntimeError("Ledger store needs a session factory for standalone appends")
        return self.sessions

    async def append(self, entry: LedgerAppend) -> OperationLedgerEntry:
        async with self._require_sessions().begin() as db:
            return await self.append_in_transaction(db, entry)

    async def append_in_transaction(self, db: AsyncSession, entry: LedgerAppend) -> OperationLedgerEntry:
        """Participate in the caller's transaction (same-txn with the audited action)."""
        from app.services.agent.gateway.ledger_lock import acquire

        await acquire(db)
        prev = await db.scalar(
            select(OperationLedgerEntry).order_by(OperationLedgerEntry.seq.desc()).limit(1)
        )
        prev_hash = prev.row_hash if prev is not None else None
        op_id = str(uuid4())
        row = OperationLedgerEntry(
            op_id=op_id,
            prev_hash=prev_hash,
            row_hash=_row_hash(prev_hash, op_id, entry),
            organization_id=entry.organization_id,
            customer_id=entry.customer_id,
            task_id=entry.task_id,
            turn_id=entry.turn_id,
            step=entry.step,
            capability=entry.capability,
            capability_version=entry.capability_version,
            args_hash=entry.args_hash,
            idempotency_key=entry.idempotency_key,
            policy_decision=entry.policy_decision,
            policy_version=entry.policy_version,
            actor=entry.actor,
            status=entry.status,
            external_ref=entry.external_ref,
            error=entry.error,
            latency_ms=entry.latency_ms,
            cost=entry.cost,
        )
        db.add(row)
        await db.flush()
        return row

    async def current(self, idempotency_key: str, *, db: AsyncSession | None = None):
        statement = (
            select(OperationLedgerEntry)
            .where(OperationLedgerEntry.idempotency_key == idempotency_key)
            .order_by(OperationLedgerEntry.seq.desc())
            .limit(1)
        )
        if db is not None:
            return await db.scalar(statement)
        async with self._require_sessions()() as session:
            return await session.scalar(statement)

    async def transition(
        self,
        idempotency_key: str,
        status: str,
        *,
        db: AsyncSession | None = None,
        external_ref: str | None = None,
        error: dict | None = None,
        latency_ms: int | None = None,
    ) -> OperationLedgerEntry | None:
        """Append a status-change row copying policy/identity from the latest row for the key."""
        if db is not None:
            return await self._transition_in_transaction(
                db,
                key=idempotency_key,
                status=status,
                external_ref=external_ref,
                error=error,
                latency_ms=latency_ms,
            )
        async with self._require_sessions().begin() as session:
            return await self._transition_in_transaction(
                session,
                key=idempotency_key,
                status=status,
                external_ref=external_ref,
                error=error,
                latency_ms=latency_ms,
            )

    async def _transition_in_transaction(self, db, *, key, status, external_ref, error, latency_ms):
        current = await self.current(key, db=db)
        if current is None:
            return None
        entry = LedgerAppend(
            organization_id=current.organization_id,
            customer_id=current.customer_id,
            capability=current.capability,
            capability_version=current.capability_version,
            args_hash=current.args_hash,
            idempotency_key=key,
            policy_decision=current.policy_decision,
            policy_version=current.policy_version,
            status=status,
            actor=current.actor,
            task_id=current.task_id,
            turn_id=current.turn_id,
            step=current.step,
            external_ref=external_ref or current.external_ref,
            error=error,
            latency_ms=latency_ms,
        )
        return await self.append_in_transaction(db, entry)


def _row_hash(prev_hash: str | None, op_id: str, entry: LedgerAppend) -> str:
    material = "|".join(
        [
            prev_hash or "",
            op_id,
            entry.capability,
            entry.args_hash,
            entry.idempotency_key,
            entry.status,
            entry.external_ref or "",
        ]
    )
    return sha256(material.encode("utf-8")).hexdigest()
