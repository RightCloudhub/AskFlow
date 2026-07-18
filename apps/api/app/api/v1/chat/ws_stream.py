"""WebSocket token emission helpers (progressive delivery)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

SendJson = Callable[[dict[str, Any]], Awaitable[None]]

# Progressive chunk size when chunking a finalized answer (no live LLM stream)
WS_TOKEN_STEP = 32


async def emit_answer_tokens(send_json: SendJson, answer: str) -> None:
    """Chunk a finalized answer into `token` frames for WS clients."""
    text = answer or ""
    step = WS_TOKEN_STEP
    for i in range(0, len(text), step):
        await send_json({"type": "token", "content": text[i : i + step]})


async def emit_side_effects(send_json: SendJson, side_effects: dict[str, Any]) -> None:
    if side_effects.get("ticket"):
        await send_json({"type": "ticket", **side_effects["ticket"]})
    if side_effects.get("handoff"):
        await send_json({"type": "handoff", **side_effects["handoff"]})


def message_end_payload(
    *,
    asst_msg_id: str,
    user_msg_id: str,
    result: Any,
) -> dict[str, Any]:
    return {
        "type": "message_end",
        "message_id": asst_msg_id,
        "user_message_id": user_msg_id,
        "run_id": result.run_id,
        "trace_id": result.trace_id,
        "route": result.route,
        "intent": result.intent,
        "sources": result.sources,
        "verification": result.verification,
        "answer_confidence": result.answer_confidence,
        "flags": result.flags,
        "refused": result.refused,
    }
