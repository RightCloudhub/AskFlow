"""CAS updates and value-free tombstones prevent stale clients resurrecting deleted memory."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.customer_preference import CustomerPreference
from app.services.agent.memory.contracts import ALLOWED_VALUES, PreferenceChange, PreferenceView
from app.services.agent.service.contracts import Scope


class MemoryConflict(RuntimeError):
    """Reload the current version before changing this preference."""


class PreferenceStore:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self.sessions = sessions

    @staticmethod
    def _scope(scope: Scope):
        return (CustomerPreference.organization_id == scope.organization_id,
                CustomerPreference.customer_id == scope.customer_id)

    async def list(self, scope: Scope) -> list[PreferenceView]:
        async with self.sessions() as db:
            rows = await db.scalars(select(CustomerPreference).where(*self._scope(scope))
                                    .order_by(CustomerPreference.key))
            return [self._view(row) for row in rows]

    async def active(self, scope: Scope) -> dict[str, str]:
        views = await self.list(scope)
        return {v.key: v.value for v in views
                if v.status == "active" and v.value in ALLOWED_VALUES[v.key]}

    async def put(self, scope: Scope, change: PreferenceChange) -> PreferenceView:
        # Revalidate even if an internal caller constructed or mutated a model directly.
        change = PreferenceChange.model_validate(change.model_dump())
        now = datetime.now(UTC)
        values = {"value": change.value, "version": change.expected_version + 1,
                  "verified_at": now, "expires_at": now + timedelta(days=change.retention_days)}
        try:
            async with self.sessions.begin() as db:
                if change.expected_version == 0:
                    row = CustomerPreference(organization_id=scope.organization_id,
                                             customer_id=scope.customer_id, key=change.key, **values)
                    db.add(row)
                    await db.flush()
                else:
                    await self._update(db, scope, key=change.key,
                                       expected_version=change.expected_version, values=values)
                row = await db.scalar(select(CustomerPreference).where(
                    *self._scope(scope), CustomerPreference.key == change.key))
                view = self._view(row)
            return view
        except IntegrityError as exc:
            raise MemoryConflict("Preference version changed") from exc

    async def delete(self, scope: Scope, key: str, *, expected_version: int) -> PreferenceView:
        now = datetime.now(UTC)
        async with self.sessions.begin() as db:
            await self._update(db, scope, key=key, expected_version=expected_version,
                               values={"value": None, "version": expected_version + 1,
                                       "expires_at": now})
            row = await db.scalar(select(CustomerPreference).where(
                *self._scope(scope), CustomerPreference.key == key))
            view = self._view(row)
        return view

    async def _update(self, db: AsyncSession, scope: Scope, *, key: str,
                      expected_version: int, values: dict) -> None:
        result = await db.execute(update(CustomerPreference).where(
            *self._scope(scope), CustomerPreference.key == key,
            CustomerPreference.version == expected_version,
        ).values(**values))
        if result.rowcount != 1:
            raise MemoryConflict("Preference version changed or does not exist")

    @staticmethod
    def _view(row: CustomerPreference) -> PreferenceView:
        expiry = row.expires_at.replace(tzinfo=UTC) if row.expires_at.tzinfo is None else row.expires_at
        verified = row.verified_at.replace(tzinfo=UTC) if row.verified_at.tzinfo is None else row.verified_at
        state = "active" if expiry > datetime.now(UTC) else "expired"
        if row.value is None:
            state = "deleted"
        return PreferenceView(memory_id=row.id, key=row.key,
                              value=row.value if state == "active" else None,
                              version=row.version, status=state,
                              verified_at=verified, expires_at=expiry)
