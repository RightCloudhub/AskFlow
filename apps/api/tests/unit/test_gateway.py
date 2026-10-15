"""Action Gateway: policy, idempotency, confirmation tokens and the append-only ledger."""

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.services.agent.gateway.confirmation as confirmation_mod
from app.core.database import Base
from app.models.operation_ledger import OperationLedgerEntry
from app.services.agent.gateway import (
    ActionGateway,
    ExecContext,
    PolicyEngine,
    issue_confirmation,
    validate_confirmation,
)
from app.services.agent.gateway.capabilities import (
    spec_for_operation,
    spec_for_side_effect,
    spec_for_tool,
)
from app.services.agent.gateway.idempotency import args_hash, derive_key
from app.services.agent.gateway.ledger import (
    STATUS_DENIED,
    STATUS_EXECUTED,
    STATUS_INTENT,
    LedgerAppend,
    LedgerStore,
)
from app.services.agent.gateway.tool_bridge import ToolGatewayBridge
from app.services.agent.service.contracts import (
    ConfirmationGrant,
    LedgerEntry,
    Operation,
    OperationCall,
    Receipt,
    Scope,
    Task,
)

SCOPE = Scope(organization_id="deployment", customer_id="u1")
CTX = ExecContext(scope=SCOPE, turn_id="turn-1", step="step-1")
REFUND_ARGS = {"order_id": "10023", "amount_cents": 4900, "reason": "changed_mind"}


@pytest_asyncio.fixture
async def sessions(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'gateway.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


def refund_operation() -> Operation:
    async def handler(_call):
        return Receipt(status="succeeded")

    return Operation(
        operation_id="refund.submit",
        version="3",
        effect="write",
        permission="refunds.write",
        input_schema=Receipt,
        handler=handler,
        precondition=lambda _args, _env: True,
    )


def test_derive_key_is_deterministic_and_order_insensitive():
    first = derive_key(scope_id="t1", step="s", capability="c", args={"a": 1, "b": [2, 3]})
    second = derive_key(scope_id="t1", step="s", capability="c", args={"b": [2, 3], "a": 1})
    other = derive_key(scope_id="t1", step="s", capability="c", args={"a": 2, "b": [2, 3]})
    assert first == second and first != other
    assert args_hash({"a": 1}) != args_hash({"a": "1"})


def test_spec_derivation_for_operations_and_tools():
    spec = spec_for_operation(refund_operation())
    assert spec.side_effect == "irreversible_write"
    assert spec.required_assurance == 2
    assert spec.requires_confirmation is True
    read_spec = spec_for_tool("search_order")
    assert read_spec.side_effect == "read" and read_spec.required_assurance == 1
    assert spec_for_side_effect("ticket.create").side_effect == "reversible_write"


def test_policy_denies_low_assurance_and_requires_step_up():
    engine = PolicyEngine()
    spec = spec_for_operation(refund_operation())
    denied = engine.evaluate(capability=spec, args=REFUND_ARGS, assurance=1)
    assert denied.allow is False and denied.step_up_required is True
    allowed = engine.evaluate(capability=spec, args=REFUND_ARGS, assurance=2)
    assert allowed.allow is True and allowed.requires_confirmation is True


def test_policy_amount_limit_requires_human_approval():
    engine = PolicyEngine()
    spec = spec_for_operation(refund_operation())
    over = engine.evaluate(
        capability=spec, args={**REFUND_ARGS, "amount_cents": 6000}, assurance=2
    )
    assert over.requires_human_approval is True
    under = engine.evaluate(capability=spec, args=REFUND_ARGS, assurance=2)
    assert under.requires_human_approval is False


def test_policy_skips_confirmation_when_granted():
    engine = PolicyEngine()
    spec = spec_for_operation(refund_operation())
    decision = engine.evaluate(
        capability=spec, args=REFUND_ARGS, assurance=2, has_confirmation=True
    )
    assert decision.requires_confirmation is False


@pytest.mark.asyncio
async def test_ledger_is_append_only_with_hash_chain(sessions):
    store = LedgerStore(sessions)
    base = {
        "organization_id": "deployment",
        "customer_id": "u1",
        "capability": "refund.submit",
        "capability_version": "3",
        "args_hash": args_hash(REFUND_ARGS),
        "idempotency_key": "key-1",
        "policy_decision": {"allow": True},
        "policy_version": "1",
        "actor": "agent",
    }
    first = await store.append(LedgerAppend(**base, status=STATUS_INTENT))
    second = await store.append(LedgerAppend(**base, status=STATUS_EXECUTED, external_ref="rf-1"))
    assert second.prev_hash == first.row_hash
    current = await store.current("key-1")
    assert current.status == STATUS_EXECUTED and current.external_ref == "rf-1"
    async with sessions() as db:
        rows = list(await db.scalars(select(OperationLedgerEntry).order_by(OperationLedgerEntry.seq)))
    assert [row.status for row in rows] == [STATUS_INTENT, STATUS_EXECUTED]


@pytest.mark.asyncio
async def test_gateway_records_denied_decision(sessions):
    gateway = ActionGateway(LedgerStore(sessions))
    spec = spec_for_operation(refund_operation())
    decision = gateway.evaluate(capability=spec, args=REFUND_ARGS, ctx=CTX)
    assert decision.allow is False
    await gateway.record_decision(
        capability=spec, args=REFUND_ARGS, ctx=CTX, decision=decision, status=STATUS_DENIED
    )
    key = gateway.key_for(scope_id="turn-1", step=CTX.step, capability=spec, args=REFUND_ARGS)
    assert await gateway.prior_status(key) == STATUS_DENIED


@pytest.mark.asyncio
async def test_confirmation_token_is_bound_single_use(sessions):
    async with sessions.begin() as db:
        issued = await issue_confirmation(
            db, scope_id="task-1", step="step-1", args=REFUND_ARGS, task_id="task-1"
        )
    async with sessions.begin() as db:
        assert (
            await validate_confirmation(
                db, issued.token, scope_id="task-1", step="step-1", args=REFUND_ARGS
            )
            is True
        )
    async with sessions.begin() as db:
        assert (
            await validate_confirmation(
                db, issued.token, scope_id="task-1", step="step-1", args=REFUND_ARGS
            )
            is False
        )
    async with sessions.begin() as db:
        issued2 = await issue_confirmation(
            db, scope_id="task-1", step="step-1", args=REFUND_ARGS, task_id="task-1"
        )
        assert (
            await validate_confirmation(
                db, issued2.token, scope_id="task-1", step="step-1", args={"order_id": "999"}
            )
            is False
        )
        assert (
            await validate_confirmation(
                db, issued2.token, scope_id="task-2", step="step-1", args=REFUND_ARGS
            )
            is False
        )


@pytest.mark.asyncio
async def test_expired_confirmation_token_is_rejected(sessions, monkeypatch):
    async with sessions.begin() as db:
        issued = await issue_confirmation(
            db, scope_id="task-1", step="step-1", args=REFUND_ARGS, task_id="task-1", ttl_seconds=60
        )
    future = datetime.now(UTC) + timedelta(minutes=5)
    monkeypatch.setattr(confirmation_mod.time, "time", lambda: future.timestamp())
    async with sessions.begin() as db:
        assert (
            await validate_confirmation(
                db, issued.token, scope_id="task-1", step="step-1", args=REFUND_ARGS
            )
            is False
        )


@pytest.mark.asyncio
async def test_record_verified_marks_executed_writes(sessions):
    gateway = ActionGateway(LedgerStore(sessions))
    call = OperationCall(operation_id="refund.submit", key="call-1", arguments=dict(REFUND_ARGS))
    task = Task(
        scope=SCOPE,
        goal="refund",
        completion_condition="refund",
        owner="support",
        ledger=[LedgerEntry(call=call, operation_version="3", status="succeeded")],
    )
    key = derive_key(
        scope_id=task.task_id, step="call-1", capability="refund.submit", args=REFUND_ARGS
    )
    base = {
        "organization_id": "deployment",
        "customer_id": "u1",
        "capability": "refund.submit",
        "capability_version": "3",
        "args_hash": args_hash(REFUND_ARGS),
        "idempotency_key": key,
        "policy_decision": {"allow": True},
        "policy_version": "1",
        "status": STATUS_EXECUTED,
    }
    await gateway.ledger.append(LedgerAppend(**base))
    marked = await gateway.record_verified(task, registry=None)
    assert marked == 1
    assert await gateway.prior_status(key) == "VERIFIED"


@pytest.mark.asyncio
async def test_tool_bridge_denies_below_required_assurance(sessions):
    calls = []

    async def handler(args):
        calls.append(args)
        return {"status": "ok"}

    async with sessions.begin() as db:
        bridge = ToolGatewayBridge(turn_id="turn-9", user_id="u1", db=db, assurance=0)
        wrapped = bridge.wrap("search_order", handler)
        result = await wrapped({"order_id": "10023"})
    assert result["status"] == "error" and result["error_class"] == "auth"
    assert calls == []
    gateway = ActionGateway(LedgerStore(sessions))
    key = gateway.key_for(
        scope_id="turn-9",
        step="tool:search_order:1",
        capability=spec_for_tool("search_order"),
        args={"order_id": "10023"},
    )
    assert await gateway.prior_status(key) == STATUS_DENIED


@pytest.mark.asyncio
async def test_tool_bridge_records_intent_and_outcome(sessions):
    async def handler(args):
        return {"status": "ok", "data": {"order_id": args["order_id"]}}

    async with sessions() as db:
        bridge = ToolGatewayBridge(turn_id="turn-10", user_id="u1", db=db, assurance=1)
        result = await bridge.wrap("search_order", handler)({"order_id": "10023"})
        await db.commit()
    assert result["status"] == "ok"
    gateway = ActionGateway(LedgerStore(sessions))
    key = gateway.key_for(
        scope_id="turn-10",
        step="tool:search_order:1",
        capability=spec_for_tool("search_order"),
        args={"order_id": "10023"},
    )
    assert await gateway.prior_status(key) == STATUS_EXECUTED


def test_grant_matching_uses_capability_and_args_hash():
    grant = ConfirmationGrant(capability="refund.submit", args_hash=args_hash(REFUND_ARGS))
    task = Task(
        scope=SCOPE,
        goal="refund",
        completion_condition="refund",
        owner="support",
        assurance_level=2,
        confirmations=[grant],
    )
    assert task.confirmations[0].capability == "refund.submit"
    assert task.confirmations[0].args_hash == args_hash(dict(REFUND_ARGS))
