"""Capability registry: side-effect class, assurance, confirmation, compensation (arch §4.4)."""

from dataclasses import dataclass
from typing import Literal

SideEffect = Literal["read", "reversible_write", "irreversible_write"]

# Explicit overrides; everything else derives from the operation's declared effect.
IRREVERSIBLE_CAPABILITIES = frozenset({"refund.submit", "orders.cancel", "payments.refund"})
REQUIRED_ASSURANCE = {
    "refund.submit": 2,
    "orders.cancel": 2,
    "payments.refund": 2,
}
EFFECT_MAP: dict[str, SideEffect] = {
    "read": "read",
    "write": "reversible_write",
    "notify": "reversible_write",
}


@dataclass(frozen=True)
class CapabilitySpec:
    name: str
    version: str = "1"
    side_effect: SideEffect = "read"
    required_assurance: int = 1
    requires_confirmation: bool = False
    compensation: str | None = None
    cost_units: int = 1

    @property
    def is_write(self) -> bool:
        return self.side_effect != "read"


def spec_for_operation(op) -> CapabilitySpec:
    """Derive the spec from a service-runtime Operation contract."""
    irreversible = op.operation_id in IRREVERSIBLE_CAPABILITIES
    side: SideEffect = "irreversible_write" if irreversible else EFFECT_MAP[op.effect]
    return CapabilitySpec(
        name=op.operation_id,
        version=op.version,
        side_effect=side,
        required_assurance=REQUIRED_ASSURANCE.get(op.operation_id, 1),
        requires_confirmation=irreversible,
        compensation=op.compensation,
    )


def spec_for_tool(name: str) -> CapabilitySpec:
    return CapabilitySpec(name=f"tool.{name}", side_effect="read")


def spec_for_side_effect(name: str) -> CapabilitySpec:
    """Legacy pipeline side effects (ticket/handoff/notify/gap) are reversible writes."""
    return CapabilitySpec(name=name, side_effect="reversible_write")


COMPENSATION_IRREVERSIBLE_PREFIX = "irreversible:"
COMPENSATION_OWNER_REVIEW_PREFIX = "owner_review:"
RESERVED_COMPENSATION_PREFIXES = (
    COMPENSATION_IRREVERSIBLE_PREFIX,
    COMPENSATION_OWNER_REVIEW_PREFIX,
)


def automatic_compensation(op) -> str | None:
    """The declared compensation op id when it is a plain executable id (arch §4.6)."""
    declared = (op.compensation or "").strip()
    if not declared or declared.startswith(RESERVED_COMPENSATION_PREFIXES):
        return None
    return declared
