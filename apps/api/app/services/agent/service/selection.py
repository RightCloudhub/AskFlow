"""Fresh observations and deterministic selection without fabricated utility estimates."""

import json
from dataclasses import replace
from datetime import UTC, datetime

from app.services.agent.service.contracts import Candidate, Environment, Task


def fresh_environment(env: Environment) -> Environment:
    now = datetime.now(UTC)
    return replace(
        env,
        sourced_facts={
            key: fact
            for key, fact in env.sourced_facts.items()
            if not fact.simulated and fact.observed_at <= now < fact.expires_at
        },
    )


def budget_stop(task: Task) -> str | None:
    if task.deadline is not None and datetime.now(UTC) >= task.deadline:
        return "owner_review:deadline_exceeded"
    if task.calls_used >= task.max_calls:
        return "owner_review:task_budget_exhausted"
    if task.no_progress_cycles >= task.no_progress_limit:
        return "owner_review:no_progress"
    return None


def over_budget(task: Task, cost: float | None) -> bool:
    return task.max_cost is not None and task.cost_used + (cost or 0) > task.max_cost


def candidate_rank(candidate: Candidate):
    sourced = candidate.utility is not None and bool(candidate.utility_source)
    return (
        not sourced,
        -candidate.utility if sourced else 0,
        candidate.priority,
        candidate.risk,
        candidate.cost or 0,
        candidate.latency_ms,
        -candidate.stability,
    )


def select_candidate(candidates: list[Candidate]) -> Candidate | None:
    unique: dict[str, Candidate] = {}
    for candidate in candidates:
        identity = json.dumps(
            [candidate.call.operation_id, candidate.call.arguments], sort_keys=True
        )
        previous = unique.get(identity)
        if previous is None or candidate_rank(candidate) < candidate_rank(previous):
            unique[identity] = candidate
    return min(unique.values(), key=candidate_rank) if unique else None
