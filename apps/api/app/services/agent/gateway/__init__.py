"""Action Gateway: policy, capabilities, idempotency, confirmation and the operation ledger."""

from app.services.agent.gateway.capabilities import (
    CapabilitySpec,
    spec_for_operation,
    spec_for_side_effect,
    spec_for_tool,
)
from app.services.agent.gateway.confirmation import issue_confirmation, validate_confirmation
from app.services.agent.gateway.context import ExecContext
from app.services.agent.gateway.gateway import ActionGateway
from app.services.agent.gateway.ledger import LedgerAppend, LedgerStore
from app.services.agent.gateway.policy import PolicyDecision, PolicyEngine

__all__ = [
    "ActionGateway",
    "CapabilitySpec",
    "ExecContext",
    "LedgerAppend",
    "LedgerStore",
    "PolicyDecision",
    "PolicyEngine",
    "issue_confirmation",
    "spec_for_operation",
    "spec_for_side_effect",
    "spec_for_tool",
    "validate_confirmation",
]
