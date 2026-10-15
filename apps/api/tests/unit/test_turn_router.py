"""Turn Router: control intents, resume, confidence bands, step-up and decision records."""

import re

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
from app.models.conversation import Conversation
from app.models.enums import UserRole
from app.models.otp_challenge import OtpChallenge
from app.models.router_decision import RouterDecisionRecord
from app.models.service_dispatch import ServiceDispatch
from app.models.service_task import ServiceTask
from app.models.user import User
from app.services.agent.gateway.confirmation import issue_confirmation
from app.services.agent.router.turn_router import (
    ROUTE_CONTROL,
    ROUTE_INTERACTIVE,
    ROUTE_STEP_UP,
    ROUTE_TASK_CREATE,
    ROUTE_TASK_RESUME,
    TurnRouter,
)
from app.services.agent.service.contracts import PendingConfirmation
from app.services.agent.service.store import TaskStore
from app.utils.merge import merge_patch

ORDER_ID = "ORD202401010001"
ORDER_TEXT = f"查询订单 {ORDER_ID}"
CODE_PATTERN = re.compile(r"(\d{6})")


@pytest_asyncio.fixture
async def sessions(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'router.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def make_conversation(session, *, email: str = "user@example.com"):
    user = User(
        username=email.split("@")[0],
        email=email,
        hashed_password="x",
        role=UserRole.USER.value,
    )
    session.add(user)
    await session.flush()
    conversation = Conversation(user_id=user.id, title="t", status="active", metadata_json={})
    session.add(conversation)
    await session.flush()
    return conversation


async def route(session, conversation, text: str):
    action = await TurnRouter(session).route(
        conversation=conversation, text=text, history=[], metadata={}
    )
    if action.handled is not None and action.handled.metadata_patch:
        conversation.metadata_json = merge_patch(
            conversation.metadata_json or {}, action.handled.metadata_patch
        )
    await session.commit()
    return action


async def create_task(session, conversation):
    action = await route(session, conversation, ORDER_TEXT)
    assert action.route == ROUTE_TASK_CREATE
    return action


@pytest.mark.asyncio
async def test_goal_message_creates_task_and_records_decision(sessions):
    async with sessions() as session:
        conversation = await make_conversation(session)
        await create_task(session, conversation)
        task_row = await session.scalar(select(ServiceTask))
        assert task_row is not None
        assert task_row.checkpoint["assurance_level"] == 2
        decision = await session.scalar(select(RouterDecisionRecord))
        assert decision.route == ROUTE_TASK_CREATE
        assert decision.goal_key == "order_status"
        assert decision.goal_version == 1
        assert decision.confidence >= 0.7
        assert decision.method
        assert decision.slots["order_id"] == ORDER_ID


@pytest.mark.asyncio
async def test_duplicate_request_resumes_and_keeps_single_task(sessions):
    async with sessions() as session:
        conversation = await make_conversation(session)
        await create_task(session, conversation)
        action = await route(session, conversation, ORDER_TEXT)
        assert action.route == ROUTE_TASK_RESUME
        assert action.relation == "modification"
        info = action.handled.side_effects["service_task"]
        assert info["status"] == "active"
        assert await session.scalar(select(ServiceTask).where(ServiceTask.id == info["task_id"]))


@pytest.mark.asyncio
async def test_control_cancel_closes_open_task(sessions):
    async with sessions() as session:
        conversation = await make_conversation(session)
        await create_task(session, conversation)
        action = await route(session, conversation, "算了，取消吧")
        assert action.route == ROUTE_CONTROL
        row = await session.scalar(select(ServiceTask))
        assert row.checkpoint["status"] == "closed_unresolved"
        dispatch = await session.scalar(select(ServiceDispatch))
        assert dispatch.due_at is None
        decision = await session.scalars(select(RouterDecisionRecord).order_by(RouterDecisionRecord.created_at))
        assert [d.route for d in decision][-1] == ROUTE_CONTROL


@pytest.mark.asyncio
async def test_waiting_customer_reply_resumes_task(sessions):
    async with sessions() as session:
        conversation = await make_conversation(session)
        action = await create_task(session, conversation)
        task_id = action.handled.side_effects["service_task"]["task_id"]
        store = TaskStore(sessions)
        task = await store.load(task_id, _scope_for(conversation))
        task.status, task.wake_condition = "waiting_customer", "ask_customer:call-1"
        await store.save(task)
        resumed = await route(session, conversation, "补充信息：地址是上海市")
        assert resumed.route == ROUTE_TASK_RESUME
        assert resumed.relation == "answer"
        refreshed = await store.load(task_id, _scope_for(conversation))
        assert refreshed.status == "active"


@pytest.mark.asyncio
async def test_confirmation_message_grants_and_wakes(sessions):
    async with sessions() as session:
        conversation = await make_conversation(session)
        action = await create_task(session, conversation)
        task_id = action.handled.side_effects["service_task"]["task_id"]
        store = TaskStore(sessions)
        task = await store.load(task_id, _scope_for(conversation))
        token = await issue_confirmation(
            session, scope_id=task_id, step="call-1", args={"order_id": ORDER_ID}, task_id=task_id
        )
        await session.commit()
        task.status = "waiting_customer"
        task.wake_condition = f"confirm:{token.nonce}"
        task.pending_confirmation = PendingConfirmation(
            capability="orders.cancel",
            step="call-1",
            args_hash=token.args_hash,
            nonce=token.nonce,
            token=token.token,
            expires_at=token.expires_at,
        )
        await store.save(task)
        await session.commit()
        result = await route(session, conversation, "确认")
        assert result.route == ROUTE_TASK_RESUME
        refreshed = await store.load(task_id, _scope_for(conversation))
        assert refreshed.status == "active"
        assert refreshed.pending_confirmation is None
        assert refreshed.confirmations[0].args_hash == token.args_hash
        # Replaying the confirmation cannot grant twice.
        await route(session, conversation, "确认")
        replay = await store.load(task_id, _scope_for(conversation))
        assert len(replay.confirmations) == 1


@pytest.mark.asyncio
async def test_unrelated_message_answers_with_reminder(sessions):
    async with sessions() as session:
        conversation = await make_conversation(session)
        await create_task(session, conversation)
        action = await route(session, conversation, "你们周末上班吗")
        assert action.route == ROUTE_INTERACTIVE
        assert action.handled is None
        assert action.relation == "unrelated"
        assert "order_status" in action.reminder


@pytest.mark.asyncio
async def test_guest_is_step_up_challenged_before_task(sessions):
    async with sessions() as session:
        conversation = await make_conversation(session, email="abc@guest.askflow.local")
        first = await route(session, conversation, ORDER_TEXT)
        assert first.route == ROUTE_STEP_UP
        assert await session.scalar(select(OtpChallenge)) is not None
        assert (conversation.metadata_json or {}).get("pending_step_up")
        code = CODE_PATTERN.search(first.handled.answer).group(1)
        second = await route(session, conversation, code)
        assert second.route == ROUTE_TASK_CREATE
        row = await session.scalar(select(ServiceTask))
        assert row.checkpoint["assurance_level"] == 2
        assert "pending_step_up" not in (conversation.metadata_json or {})
        requirement = await session.scalar(
            select(RouterDecisionRecord).where(RouterDecisionRecord.route == ROUTE_STEP_UP)
        )
        assert requirement.identity_requirement["required"] == 1
        assert requirement.identity_requirement["action"] == "STEP_UP"


@pytest.mark.asyncio
async def test_wrong_step_up_code_keeps_challenge(sessions):
    async with sessions() as session:
        conversation = await make_conversation(session, email="abc@guest.askflow.local")
        first = await route(session, conversation, ORDER_TEXT)
        code = CODE_PATTERN.search(first.handled.answer).group(1)
        wrong = "000000" if code != "000000" else "111111"
        second = await route(session, conversation, wrong)
        assert second.route == ROUTE_STEP_UP
        assert "验证码不正确" in second.handled.answer
        assert (conversation.metadata_json or {}).get("pending_step_up")


@pytest.mark.asyncio
async def test_faq_message_records_interactive_decision(sessions):
    async with sessions() as session:
        conversation = await make_conversation(session)
        action = await route(session, conversation, "退货政策是什么")
        assert action.route in {ROUTE_INTERACTIVE, "CLARIFY", "REFUSE"}
        decision = await session.scalar(select(RouterDecisionRecord))
        assert decision is not None
        assert decision.router_version


def _scope_for(conversation):
    from app.services.agent.identity import customer_scope

    return customer_scope(conversation.user_id)
