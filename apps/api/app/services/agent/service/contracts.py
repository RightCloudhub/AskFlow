"""Typed operation boundaries; free text and checkpoint memory never grant authority."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

DEFAULT_TASK_CALLS = 20
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_OPERATION_RETRIES = 2
DEFAULT_NO_PROGRESS_LIMIT = 5
ErrorKind = Literal[
    "transient",
    "unavailable",
    "permission",
    "invalid_input",
    "conflict",
    "permanent",
    "unknown",
    "simulated",
]
TaskStatus = Literal[
    "active",
    "waiting_customer",
    "waiting_external",
    "handed_off",
    "resolved",
    "closed_unresolved",
]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Scope(Record):
    organization_id: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)


class Evidence(Record):
    operation_id: str
    source: str = Field(min_length=1)
    data: dict[str, Any]
    observed_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: AwareDatetime
    simulated: bool = False


class Receipt(Record):
    status: Literal["succeeded", "failed", "unknown", "mock"]
    evidence: Evidence | None = None
    error: str | None = None
    error_kind: ErrorKind | None = None


class RecoverySignal(Record):
    operation_id: str
    request_key: str
    kind: ErrorKind
    action: Literal["retry", "fallback", "ask_customer", "owner_review", "reconcile"]
    occurred_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))
    retry_at: AwareDatetime | None = None


class OperationCall(Record):
    key: str = Field(default_factory=lambda: str(uuid4()))
    operation_id: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class LedgerEntry(Record):
    call: OperationCall
    operation_version: str
    status: Literal["running", "succeeded", "failed", "unknown", "mock"] = "running"
    receipt: Receipt | None = None
    deadline_at: AwareDatetime | None = None
    started_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))


class Decision(Record):
    candidates: list[str]
    selected: str | None
    reason: str
    rejected: dict[str, str] = Field(default_factory=dict)
    expected_result: str | None = None
    stop_conditions: list[str] = Field(default_factory=list)


class TaskTransition(Record):
    previous: TaskStatus
    current: TaskStatus
    actor_id: str
    reason: str
    occurred_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))


class Task(Record):
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    scope: Scope
    conversation_id: str | None = None
    goal: str = Field(min_length=1)
    inputs: dict[str, Any] = Field(default_factory=dict)
    completion_condition: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    status: TaskStatus = "active"
    version: int = 0
    max_calls: int = Field(default=DEFAULT_TASK_CALLS, gt=0)
    calls_used: int = 0
    max_cost: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    cost_used: float = Field(default=0, ge=0, allow_inf_nan=False)
    deadline: AwareDatetime | None = None
    no_progress_limit: int = Field(default=DEFAULT_NO_PROGRESS_LIMIT, gt=0)
    no_progress_cycles: int = Field(default=0, ge=0)
    ledger: list[LedgerEntry] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    recovery_signals: list[RecoverySignal] = Field(default_factory=list)
    wake_condition: str | None = None
    review_at: AwareDatetime | None = None
    transitions: list[TaskTransition] = Field(default_factory=list)


class SourcedFact(Record):
    value: Any
    source: str = Field(min_length=1)
    observed_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: AwareDatetime
    simulated: bool = False


@dataclass(frozen=True)
class Environment:
    """Provided by authenticated application code, never parsed from model text."""

    scope: Scope
    permissions: frozenset[str] = frozenset()
    available_operations: frozenset[str] = frozenset()
    facts: dict[str, Any] = field(default_factory=dict)
    preferences: dict[str, str] = field(default_factory=dict)
    preference_status: Literal["not_loaded", "loaded", "unavailable"] = "not_loaded"
    sourced_facts: dict[str, SourcedFact] = field(default_factory=dict)
    memory_status: Literal["not_loaded", "loaded", "unavailable"] = "not_loaded"


@dataclass(frozen=True)
class Operation:
    operation_id: str
    version: str
    effect: Literal["read", "write", "notify"]
    permission: str
    input_schema: type[BaseModel]
    handler: Callable[[OperationCall], Awaitable[Receipt]]
    precondition: Callable[[BaseModel, Environment], bool]
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    output_schema: type[BaseModel] = Receipt
    compensation: str | None = None
    max_retries: int = DEFAULT_OPERATION_RETRIES
    replay_receipts_when_waiting: bool = False

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("Operation timeout must be positive")
        if self.max_retries < 0:
            raise ValueError("Operation retry budget must be nonnegative")


class Candidate(Record):
    call: OperationCall
    priority: int = 0
    reason: str
    risk: float = Field(default=0, ge=0, allow_inf_nan=False)
    cost: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    latency_ms: float = Field(default=0, ge=0, allow_inf_nan=False)
    stability: float = Field(default=0, ge=0, le=1, allow_inf_nan=False)
    utility: float | None = Field(default=None, allow_inf_nan=False)
    utility_source: str | None = None
    expected_result: str | None = None
    stop_conditions: list[str] = Field(default_factory=list)
