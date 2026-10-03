"""Bounded application entry point for goal execution and verified event resumption."""

from app.services.agent.service.contracts import Scope, Task
from app.services.agent.service.lifecycle import VerifiedWakeup, wake_task
from app.services.agent.service.runtime import ServiceAgent

MAX_TICKS_PER_DISPATCH = 25


async def advance(agent: ServiceAgent, task_id: str, *, scope: Scope) -> Task:
    """Finish available micro-steps; return waiting work to the host's durable scheduler."""
    for _ in range(MAX_TICKS_PER_DISPATCH):
        task = await agent.tick(task_id, scope)
        if task.status != "active" or any(e.status == "running" for e in task.ledger):
            return task
    # Yield fairly to the host. Calls already spent remain charged to the task.
    return task


async def resume(agent: ServiceAgent, event: VerifiedWakeup) -> Task:
    """The host authenticates the event and durably retries delivery after process failure."""
    await wake_task(agent.store, event)
    return await advance(agent, event.task_id, scope=event.scope)
