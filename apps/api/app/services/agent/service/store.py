"""Durable compare-and-swap checkpoints; commit intentions before external calls."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.service_task import ServiceTask
from app.services.agent.service.contracts import Scope, Task

DEFAULT_TASK_PAGE_SIZE = 20
MAX_TASK_PAGE_SIZE = 100


class TaskConflict(RuntimeError):
    """Another worker changed the task; reload and decide again."""


class TaskStore:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self.sessions = sessions

    async def create(self, task: Task) -> None:
        if task.version != 0:
            raise ValueError("New tasks must start at version zero")
        async with self.sessions.begin() as db:
            db.add(
                ServiceTask(
                    id=task.task_id,
                    organization_id=task.scope.organization_id,
                    customer_id=task.scope.customer_id,
                    version=task.version,
                    checkpoint=task.model_dump(mode="json"),
                )
            )

    @staticmethod
    def _scope(task_id: str, scope: Scope):
        return (
            ServiceTask.id == task_id,
            ServiceTask.organization_id == scope.organization_id,
            ServiceTask.customer_id == scope.customer_id,
        )

    async def load(self, task_id: str, scope: Scope) -> Task:
        async with self.sessions() as db:
            return await self.load_in_transaction(db, task_id, scope=scope)

    async def load_in_transaction(self, db: AsyncSession, task_id: str, *, scope: Scope) -> Task:
        row = await db.scalar(select(ServiceTask).where(*self._scope(task_id, scope)))
        if row is None:
            raise LookupError("Task not found")
        return Task.model_validate(row.checkpoint)

    async def save(self, task: Task) -> None:
        async with self.sessions.begin() as db:
            await self.write_checkpoint(db, task)
        task.version += 1

    async def write_checkpoint(self, db: AsyncSession, task: Task) -> None:
        """Participate in a host transaction; caller increments version only after commit."""
        checkpoint = task.model_dump(mode="json")
        checkpoint["version"] = task.version + 1
        statement = (
            update(ServiceTask)
            .where(
                *self._scope(task.task_id, task.scope),
                ServiceTask.version == task.version,
            )
            .values(checkpoint=checkpoint, version=task.version + 1)
        )
        result = await db.execute(statement)
        if result.rowcount != 1:
            raise TaskConflict("Stale task checkpoint")

    async def list(
        self, scope: Scope, *, limit: int = DEFAULT_TASK_PAGE_SIZE, after: str | None = None
    ) -> list[Task]:
        if not 1 <= limit <= MAX_TASK_PAGE_SIZE:
            raise ValueError("Invalid task page size")
        statement = select(ServiceTask).where(
            ServiceTask.organization_id == scope.organization_id,
            ServiceTask.customer_id == scope.customer_id,
        )
        if after is not None:
            statement = statement.where(ServiceTask.id > after)
        async with self.sessions() as db:
            rows = await db.scalars(statement.order_by(ServiceTask.id).limit(limit))
            return [Task.model_validate(row.checkpoint) for row in rows]
