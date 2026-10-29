"""Support context is resolved from scoped services and linked to AskFlow records."""

from app.commerce.core.events import publish
from app.commerce.core.services import service
from app.commerce.support.models import SupportLink
from app.schemas.chat import ConversationCreate
from app.schemas.ticket import TicketCreate
from app.services.agent.gateway.capabilities import spec_for_side_effect
from app.services.agent.gateway.context import ExecContext
from app.services.agent.gateway.gateway import ActionGateway
from app.services.agent.gateway.ledger import LedgerStore
from app.services.agent.identity import customer_scope
from app.services.chat.session.service import ChatService
from app.services.handoff.service import HandoffService
from app.services.ticket.repository.service import TicketRepository


async def open_support(ctx, payload):
    snapshot = {}
    if payload.order_id:
        snapshot["order"] = await service("order", ctx.db).get(ctx.user.id, payload.order_id)
    if payload.wallet_journal_id:
        snapshot["wallet"] = await service("wallet", ctx.db).entry(ctx.user.id, payload.wallet_journal_id)
    if payload.refund_id:
        from app.commerce.order.refunds import RefundService

        snapshot["refund"] = await RefundService(ctx.db).get(ctx.user.id, payload.refund_id)
    conversation = await ChatService(ctx.db).create_conversation(ctx.user.id, ConversationCreate(title=payload.title))
    if payload.order_id:
        conversation.metadata_json = {**(conversation.metadata_json or {}), "mall_order_id": payload.order_id}
    row = SupportLink(user_id=ctx.user.id, conversation_id=conversation.id, order_id=payload.order_id,
        refund_id=payload.refund_id, wallet_journal_id=payload.wallet_journal_id, snapshot=snapshot)
    ctx.db.add(row)
    await ctx.db.flush()
    if payload.ticket:
        result = await _effect(ctx, row, handoff=False, title=payload.title)
        row.ticket_id = result.id
    if payload.handoff:
        await _effect(ctx, row, handoff=True, title=payload.title)
    await publish(ctx.db, row, event_type="mall.support.opened", payload={"user_id": ctx.user.id,
        "conversation_id": conversation.id, "ticket_id": row.ticket_id})
    return {"id": row.id, "conversation_id": conversation.id, "ticket_id": row.ticket_id}


async def _effect(ctx, link, *, handoff: bool, title: str):
    name = "handoff.enqueue" if handoff else "ticket.create"
    spec, gateway = spec_for_side_effect(name), ActionGateway(LedgerStore())
    execution = ExecContext(scope=customer_scope(ctx.user.id), turn_id=link.id, step=name, assurance=2)
    args = {"conversation_id": link.conversation_id, "user_id": ctx.user.id, "title": title}
    decision = gateway.evaluate(capability=spec, args=args, ctx=execution)
    intent = await gateway.record_intent(capability=spec, args=args, ctx=execution, decision=decision, db=ctx.db)
    if handoff:
        row = await HandoffService(ctx.db).enqueue(conversation_id=link.conversation_id,
            user_id=ctx.user.id, summary=title, intent="handoff")
    else:
        row, _created = await TicketRepository(ctx.db).create_or_get_open(ctx.user.id,
            TicketCreate(title=title, conversation_id=link.conversation_id, description=title,
                         content={"mall_link_id": link.id}))
    await gateway.record_outcome(key=intent.idempotency_key, status="EXECUTED", external_ref=row.id, db=ctx.db)
    return row
