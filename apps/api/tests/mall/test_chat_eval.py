"""Offline mall evals exercise real chat orchestration, services and Gateway evidence."""

import pytest
from sqlalchemy import select

from app.commerce.inventory.models import Inventory
from app.commerce.order.service import OrderService
from app.models.operation_ledger import OperationLedgerEntry
from app.schemas.chat import ConversationCreate
from app.services.chat.session.service import ChatService
from app.services.chat.session.turn import ChatInput, ChatTurn
from .helpers import place, seed, transaction

pytestmark = [pytest.mark.asyncio, pytest.mark.mall_profile("mall")]


async def conversation(runtime, identity):
    async def create(db):
        row = await ChatService(db).create_conversation(identity["user_id"], ConversationCreate(title="订单咨询"))
        return row.id

    return await transaction(runtime, create)


async def turn(runtime, identity, *, conversation_id: str, content: str):
    async def run(db):
        request = ChatInput(conversation_id=conversation_id, user_id=identity["user_id"], content=content)
        _user, _assistant, result = await ChatTurn(ChatService(db), request).run()
        return result

    return await transaction(runtime, run)


async def test_chat_own_order_lookup(mall_runtime):
    identity = await seed(mall_runtime)
    order = await transaction(mall_runtime, lambda db: place(db, identity))
    chat = await conversation(mall_runtime, identity)
    result = await turn(mall_runtime, identity, conversation_id=chat, content="我的订单 " + order["id"] + " 到哪了")
    assert "PENDING_PAYMENT" in result.answer
    assert result.route == "tool"


async def test_chat_cancel_confirmation_releases_inventory(mall_runtime):
    identity = await seed(mall_runtime, stock=1)
    order = await transaction(mall_runtime, lambda db: place(db, identity))
    chat = await conversation(mall_runtime, identity)
    offered = await turn(mall_runtime, identity, conversation_id=chat, content="取消订单 " + order["id"])
    assert offered.metadata_patch["mall_pending"]["confirmation_token"]
    async with mall_runtime.sessions() as db:
        assert (await OrderService(db).get(identity["user_id"], order["id"]))["status"] == "PENDING_PAYMENT"
    result = await turn(mall_runtime, identity, conversation_id=chat, content="确认")
    assert "CANCELLED" in result.answer
    async with mall_runtime.sessions() as db:
        stock = await db.scalar(select(Inventory).where(Inventory.sku_id == identity["sku_id"]))
        assert (stock.available, stock.reserved) == (1, 0)
        ledger = list(await db.scalars(select(OperationLedgerEntry).where(
            OperationLedgerEntry.capability == "mall.order.cancel").order_by(OperationLedgerEntry.seq)))
        assert [row.status for row in ledger] == ["NEEDS_CONFIRMATION", "INTENT", "EXECUTED"]


async def test_chat_foreign_refund_is_rejected(mall_runtime):
    owner, intruder = await seed(mall_runtime), await seed(mall_runtime)
    order = await transaction(mall_runtime, lambda db: place(db, owner))
    chat = await conversation(mall_runtime, intruder)
    result = await turn(mall_runtime, intruder, conversation_id=chat, content="退款订单 " + order["id"])
    assert "resource_not_found" in result.answer
    assert result.metadata_patch["mall_pending"] is None
    async with mall_runtime.sessions() as db:
        assert (await OrderService(db).get(owner["user_id"], order["id"]))["status"] == "PENDING_PAYMENT"
