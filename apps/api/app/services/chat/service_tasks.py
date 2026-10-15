"""Compatibility entry point; goal intake now lives under the agent Turn Router."""

from app.services.agent.router.turn_router import TurnRouter


async def maybe_create_order_task(db, conversation, *, text: str, history: list, metadata: dict):
    action = await TurnRouter(db).route(
        conversation=conversation, text=text, history=history, metadata=metadata
    )
    return action.handled


__all__ = ["maybe_create_order_task"]
