"""Authenticated observation for local ticket and human-handoff builders."""

from sqlalchemy import select

from app.models.conversation import Conversation
from app.models.handoff import HandoffSession
from app.models.user import User
from app.plugins.runtime import get_app_context
from app.services.agent.domains.handoff import HANDOFF_OPERATION, HANDOFF_PERMISSION, handoff_agent
from app.services.agent.domains.ticket import TICKET_OPERATION, TICKET_PERMISSION, ticket_agent
from app.services.agent.service.contracts import Environment


def support_builder(*, handoff: bool):
    operation = HANDOFF_OPERATION if handoff else TICKET_OPERATION
    permission = HANDOFF_PERMISSION if handoff else TICKET_PERMISSION
    plugin = "handoff" if handoff else "ticket"
    factory = handoff_agent if handoff else ticket_agent

    def build(store, task):
        async def observe(current):
            return await support_environment(
                store.sessions, current, operation=operation, permission=permission, plugin=plugin
            )

        return factory(store, observe)

    return build


async def support_environment(sessions, task, *, operation: str, permission: str, plugin: str):
    async with sessions() as db:
        user = await db.scalar(
            select(User).where(User.id == task.scope.customer_id, User.is_active)
        )
        conv = await db.scalar(
            select(Conversation).where(
                Conversation.id == task.conversation_id,
                Conversation.user_id == task.scope.customer_id,
                Conversation.status.in_({"active", "transferred"}),
            )
        )
        handoff = await db.scalar(
            select(HandoffSession).where(
                HandoffSession.conversation_id == task.conversation_id,
                HandoffSession.user_id == task.scope.customer_id,
                HandoffSession.status.in_({"queued", "claimed"}),
            )
        )
    ctx = get_app_context()
    enabled = ctx is None or ctx.enabled(plugin)
    return Environment(
        scope=task.scope,
        permissions=frozenset({permission}) if user and conv else frozenset(),
        available_operations=frozenset({operation}) if enabled else frozenset(),
        facts={"handoff_status": handoff.status} if handoff else {},
    )
