"""A deterministic task timeline stores references rather than receipt payloads."""

from typing import Literal
from uuid import NAMESPACE_URL, uuid5

from pydantic import AwareDatetime

from app.services.agent.memory.records import active_records, insert_record, record_values
from app.services.agent.service.contracts import Record, Task


class TimelineEvent(Record):
    event_id: str
    task_id: str
    conversation_id: str | None
    kind: Literal["transition", "operation"]
    ref: str
    summary: str
    occurred_at: AwareDatetime


def _event(task, *, kind, ref, summary, occurred_at) -> TimelineEvent:
    return TimelineEvent(
        event_id=str(uuid5(NAMESPACE_URL, f"askflow:timeline:{task.task_id}:{kind}:{ref}")),
        task_id=task.task_id,
        conversation_id=task.conversation_id,
        kind=kind,
        ref=ref,
        summary=summary,
        occurred_at=occurred_at,
    )


def materialize(task: Task) -> list[TimelineEvent]:
    events = [
        _event(
            task,
            kind="transition",
            ref=f"transition:{index}",
            summary=f"{transition.previous} → {transition.current}",
            occurred_at=transition.occurred_at,
        )
        for index, transition in enumerate(task.transitions)
    ]
    for entry in task.ledger:
        if entry.status == "running":
            continue
        evidence = entry.receipt.evidence if entry.receipt else None
        events.append(
            _event(
                task,
                kind="operation",
                ref=entry.call.key,
                summary=f"{entry.call.operation_id}: {entry.status}",
                occurred_at=evidence.observed_at if evidence else entry.started_at,
            )
        )
    return sorted(events, key=lambda event: (event.occurred_at, event.event_id))


class TimelineStore:
    def __init__(self, sessions):
        self.sessions = sessions

    async def append(self, task: Task) -> int:
        count = 0
        async with self.sessions.begin() as db:
            for event in materialize(task):
                values = record_values(
                    task.scope,
                    kind="event",
                    key=event.event_id,
                    values={
                        "value": event.ref,
                        "payload": event.model_dump(mode="json"),
                        "source": "task_checkpoint",
                        "verification": "observed",
                        "verified_at": event.occurred_at,
                    },
                )
                count += await insert_record(db, values)
        return count

    async def list(self, scope, *, conversation_id: str) -> list[TimelineEvent]:
        rows = await active_records(self.sessions, scope, kind="event")
        events = [
            TimelineEvent.model_validate(row.payload)
            for row in rows
            if row.payload.get("conversation_id") == conversation_id
        ]
        return sorted(events, key=lambda event: (event.occurred_at, event.event_id))
