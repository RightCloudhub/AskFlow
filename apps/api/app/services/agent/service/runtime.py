"""Observe, choose a feasible micro-step, execute, and verify on the next tick."""

import asyncio
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Awaitable, Callable

from app.services.agent.service.contracts import (
    Candidate, Decision, Environment, RecoverySignal, Scope, Task,
)
from app.services.agent.service.executor import Executor
from app.services.agent.service.registry import OperationRegistry
from app.services.agent.service.recovery import candidate_rejection
from app.services.agent.service.store import TaskStore

POLICY_TIMEOUT_SECONDS = 10.0
OWNER_REVIEW_SECONDS = 60
MAX_CANDIDATES_PER_DECISION = 16


@dataclass(frozen=True)
class AgentPolicy:
    """Application-owned callbacks; a model may propose candidates, never verify itself."""

    observe: Callable[[Task], Awaitable[Environment]]
    propose: Callable[[Task, Environment], Awaitable[list[Candidate]]]
    verify: Callable[[Task, Environment], bool]


class ServiceAgent:
    def __init__(self, store: TaskStore, registry: OperationRegistry, policy: AgentPolicy) -> None:
        self.store, self.registry, self.policy = store, registry, policy
        self.executor = Executor(registry, store)

    async def tick(self, task_id: str, scope: Scope) -> Task:
        task = await self.store.load(task_id, scope)
        if task.status != "active":
            return task
        if any(entry.status == "running" for entry in task.ledger):
            if self._in_flight(task):
                return task
            self._mark_interrupted(task)
            return await self._wait(task, "reconcile_running_operation")
        try:
            env = await asyncio.wait_for(
                self.policy.observe(task.model_copy(deep=True)), timeout=POLICY_TIMEOUT_SECONDS,
            )
        except Exception:
            return await self._policy_failed(task, "observe")
        if env.scope != scope:
            raise PermissionError("scope_mismatch")
        return await self._advance(task, env)

    async def _advance(self, task: Task, env: Environment) -> Task:
        view = self._fresh_view(task)
        try:
            verified = bool(view.evidence and self.policy.verify(view, env))
        except Exception:
            return await self._policy_failed(task, "verify")
        if verified:
            task.status, task.wake_condition, task.review_at = "resolved", None, None
            await self.store.save(task)
            return task
        if task.calls_used >= task.max_calls:
            return await self._wait(task, "owner_review:task_budget_exhausted")
        try:
            candidates = await asyncio.wait_for(
                self.policy.propose(view, deepcopy(env)), timeout=POLICY_TIMEOUT_SECONDS,
            )
            call = self._choose(task, candidates, env=env)
        except Exception:
            return await self._policy_failed(task, "propose")
        if call is None:
            return await self._wait(task, "owner_review:no_feasible_action")
        await self.executor.execute(task, call, env=env)
        return task

    def _choose(self, task: Task, candidates: list[Candidate], *, env: Environment):
        if len(candidates) > MAX_CANDIDATES_PER_DECISION:
            raise ValueError("Candidate budget exhausted")
        candidates = [Candidate.model_validate(c) for c in candidates]
        rejected: dict[str, str] = {}
        feasible: list[Candidate] = []
        for candidate in candidates:
            candidate = self._retry_candidate(task, candidate)
            reason = self._rejection(task, candidate, env=env)
            if reason:
                rejected[candidate.call.operation_id] = reason
            else:
                feasible.append(candidate)
        selected = min(feasible, key=lambda c: c.priority) if feasible else None
        task.decisions.append(Decision(
            candidates=[c.call.operation_id for c in candidates], rejected=rejected,
            selected=selected.call.operation_id if selected else None,
            reason=selected.reason if selected else "No feasible operation",
        ))
        return selected.call if selected else None

    def _rejection(self, task: Task, candidate: Candidate, *, env: Environment) -> str | None:
        if any(e.call.key == candidate.call.key for e in task.ledger):
            return "already_attempted"
        if self._uncertain_write(task, candidate):
            return "reconcile_required"
        return (self.registry.rejection(candidate.call, env)
                or candidate_rejection(task, candidate.call))

    def _retry_candidate(self, task: Task, candidate: Candidate) -> Candidate:
        signals = [s for s in task.recovery_signals
                   if s.operation_id == candidate.call.operation_id]
        if not signals or signals[-1].action != "retry":
            return candidate
        op = self.registry.operations.get(candidate.call.operation_id)
        if op is None or op.effect != "read":
            return candidate
        candidate = candidate.model_copy(deep=True)
        candidate.call.key = f"{signals[-1].request_key}:retry"
        return candidate

    async def _policy_failed(self, task: Task, stage: str) -> Task:
        task.recovery_signals.append(RecoverySignal(
            operation_id=f"policy.{stage}", request_key=f"checkpoint:{task.version}",
            kind="permanent", action="owner_review",
        ))
        return await self._wait(task, f"owner_review:policy_{stage}_failed")

    async def _wait(self, task: Task, reason: str) -> Task:
        task.status, task.wake_condition = "waiting_external", reason
        task.review_at = datetime.now(UTC) + timedelta(seconds=OWNER_REVIEW_SECONDS)
        await self.store.save(task)
        return task

    @staticmethod
    def _fresh_view(task: Task) -> Task:
        now = datetime.now(UTC)
        view = task.model_copy(deep=True)
        view.evidence = [e for e in view.evidence
                         if not e.simulated and e.observed_at <= now < e.expires_at]
        return view

    def _uncertain_write(self, task: Task, candidate: Candidate) -> bool:
        op = self.registry.operations.get(candidate.call.operation_id)
        uncertain = any(e.status in {"running", "unknown"} for e in task.ledger)
        return bool(op and op.effect != "read" and uncertain)

    @staticmethod
    def _in_flight(task: Task) -> bool:
        now = datetime.now(UTC)
        return any(e.status == "running" and e.deadline_at and e.deadline_at > now
                   for e in task.ledger)

    @staticmethod
    def _mark_interrupted(task: Task) -> None:
        for entry in task.ledger:
            if entry.status == "running":
                entry.status = "unknown"
