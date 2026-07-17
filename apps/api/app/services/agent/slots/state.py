"""Slot state machine for multi-turn tool args (PRD §4.4.2)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.core.config import get_settings
from app.utils.merge import merge_patch

ORDER_ID_RE = re.compile(
    r"(?:订单号?\s*[:：#]?\s*)?([A-Za-z]{0,4}\d{6,24})",
    re.I,
)


@dataclass
class SlotState:
    tool: str
    slot: str
    intent: str
    turns_waited: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "slot": self.slot,
            "intent": self.intent,
            "turns_waited": self.turns_waited,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> SlotState | None:
        if not data or "tool" not in data or "slot" not in data:
            return None
        return cls(
            tool=str(data["tool"]),
            slot=str(data["slot"]),
            intent=str(data.get("intent", "")),
            turns_waited=int(data.get("turns_waited", 0)),
        )


@dataclass
class SlotDecision:
    action: str  # continue | ask | abandon | filled | none
    order_id: str | None = None
    patch: dict[str, Any] | None = None
    message: str | None = None


class SlotTracker:
    def __init__(self, max_turns: int | None = None) -> None:
        self.max_turns = max_turns or get_settings().max_slot_turns

    def extract_order_id(self, text: str) -> str | None:
        m = ORDER_ID_RE.search(text)
        if not m:
            return None
        candidate = m.group(1)
        # Prefer tokens that look like order ids (have digits, reasonable length)
        if sum(c.isdigit() for c in candidate) >= 6:
            return candidate
        return None

    def decide(
        self,
        text: str,
        metadata: dict[str, Any] | None,
        *,
        new_intent: str | None = None,
        new_intent_confidence: float = 0.0,
    ) -> SlotDecision:
        pending = (metadata or {}).get("pending_slot")
        state = SlotState.from_dict(pending if isinstance(pending, dict) else None)
        order_id = self.extract_order_id(text)

        if state is None:
            if order_id:
                return SlotDecision(action="filled", order_id=order_id)
            return SlotDecision(action="none")

        # resume pending slot
        if order_id:
            return SlotDecision(
                action="filled",
                order_id=order_id,
                patch={"pending_slot": None},
            )

        # different high-confidence intent → abandon
        if (
            new_intent
            and new_intent != state.intent
            and new_intent_confidence >= 0.7
        ):
            return SlotDecision(
                action="abandon",
                patch={"pending_slot": None},
            )

        turns = state.turns_waited + 1
        if turns > self.max_turns:
            return SlotDecision(
                action="abandon",
                patch={"pending_slot": None},
                message="未能获取订单号，请重新提供完整订单号或换种方式描述问题。",
            )

        updated = state.to_dict()
        updated["turns_waited"] = turns
        return SlotDecision(
            action="ask",
            patch={"pending_slot": updated},
            message="请提供您的订单号（例如 ORD202401010001），以便查询物流与状态。",
        )

    def start_order_slot(self, metadata: dict[str, Any] | None) -> dict[str, Any]:
        patch = {
            "pending_slot": SlotState(
                tool="search_order",
                slot="order_id",
                intent="order_query",
                turns_waited=0,
            ).to_dict()
        }
        return merge_patch(metadata, patch)

    def apply_patch(
        self, metadata: dict[str, Any] | None, patch: dict[str, Any] | None
    ) -> dict[str, Any]:
        return merge_patch(metadata, patch)
