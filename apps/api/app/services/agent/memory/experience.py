"""Successful paths are scoped hints; every suggested action must be revalidated."""

import json
from typing import Any, Literal
from uuid import NAMESPACE_URL, uuid5

from pydantic import Field

from app.services.agent.memory.records import active_records, insert_record, record_values
from app.services.agent.service.contracts import Record


class ExperiencePath(Record):
    goal: str = Field(min_length=1)
    conditions: dict[str, Any] = Field(default_factory=dict)
    operation_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    outcome: Literal["success", "failure"]


class ExperienceHint(Record):
    operation_id: str
    memory_id: str
    requires_revalidation: Literal[True] = True


class ExperienceStore:
    def __init__(self, sessions):
        self.sessions = sessions

    async def record(self, scope, path: ExperiencePath) -> None:
        path = ExperiencePath.model_validate(path.model_dump())
        key = str(uuid5(NAMESPACE_URL, json.dumps([path.task_id, path.goal, path.operation_id])))
        values = record_values(
            scope,
            kind="experience",
            key=key,
            values={
                "value": path.outcome,
                "payload": path.model_dump(mode="json"),
                "source": "verified_task_path",
                "verification": "observed",
            },
        )
        async with self.sessions.begin() as db:
            await insert_record(db, values)

    async def suggest(self, scope, *, goal: str, conditions: dict) -> list[ExperienceHint]:
        rows = await active_records(self.sessions, scope, kind="experience")
        hints = []
        for row in rows:
            path = ExperiencePath.model_validate(row.payload)
            if self._matches(path, goal=goal, conditions=conditions):
                hints.append(ExperienceHint(operation_id=path.operation_id, memory_id=row.id))
        return hints

    @staticmethod
    def _matches(path, *, goal: str, conditions: dict) -> bool:
        if path.outcome != "success" or path.goal != goal:
            return False
        return all(
            key in conditions and conditions[key] == value for key, value in path.conditions.items()
        )
