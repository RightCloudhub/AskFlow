"""Run process-local side effects only once the surrounding DB transaction commits.

In-memory indexes and caches must never get ahead of the database: a mutation queued with
``on_commit`` is applied after a successful ``COMMIT`` and dropped on rollback (D-11).
"""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

PENDING_KEY = "askflow_after_commit"
Action = Callable[[], None]


def on_commit(db: AsyncSession, action: Action) -> None:
    db.sync_session.info.setdefault(PENDING_KEY, []).append(action)


@event.listens_for(Session, "after_commit")
def _run_pending(session: Session) -> None:
    for action in session.info.pop(PENDING_KEY, []):
        action()


@event.listens_for(Session, "after_rollback")
def _drop_pending(session: Session) -> None:
    session.info.pop(PENDING_KEY, None)
