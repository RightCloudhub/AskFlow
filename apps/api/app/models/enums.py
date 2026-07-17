"""Shared domain enums (PRD §6.2 / agent-behavior contracts)."""

from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    USER = "user"
    AGENT = "agent"
    ADMIN = "admin"


class ConversationStatus(StrEnum):
    ACTIVE = "active"
    CLOSED = "closed"
    TRANSFERRED = "transferred"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    STAFF = "staff"


class TicketStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class HandoffStatus(StrEnum):
    QUEUED = "queued"
    CLAIMED = "claimed"
    RESOLVED = "resolved"
    RETURNED = "returned"
    TIMED_OUT = "timed_out"


class DocumentStatus(StrEnum):
    PENDING = "pending"
    INDEXING = "indexing"
    ACTIVE = "active"
    FAILED = "failed"
    ARCHIVED = "archived"


class GapStatus(StrEnum):
    OPEN = "open"
    PROMOTED = "promoted"
    DISMISSED = "dismissed"


class DraftStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"


class Intent(StrEnum):
    FAQ = "faq"
    PRODUCT = "product"
    ORDER_QUERY = "order_query"
    FAULT_REPORT = "fault_report"
    COMPLAINT = "complaint"
    HANDOFF = "handoff"
    OUT_OF_SCOPE = "out_of_scope"  # enterprise: domain refusal (PRD E4 / §12.2)


class Route(StrEnum):
    RAG = "rag"
    TOOL = "tool"
    TICKET = "ticket"
    HANDOFF = "handoff"
    CLARIFY = "clarify"
    REFUSE = "refuse"  # cold: out_of_scope dedicated refuse (not RAG invent)


class SLAState(StrEnum):
    OK = "ok"
    WARNING = "warning"
    BREACHED = "breached"


class NotifyEvent(StrEnum):
    TICKET_CREATED = "ticket.created"
    HANDOFF_TIMEOUT = "handoff.timeout"
    SLA_WARNING = "sla.warning"
    SLA_BREACHED = "sla.breached"


class LoopPhase(StrEnum):
    PLAN = "plan"
    ACT = "act"
    OBSERVE = "observe"
    RECOVER = "recover"
    FINALIZE = "finalize"


class LLMPurpose(StrEnum):
    INTENT_CLASSIFY = "intent_classify"
    QUERY_REWRITE = "query_rewrite"
    RAG_GENERATE = "rag_generate"
    HANDOFF_SUMMARY = "handoff_summary"
    GAP_DRAFT_ASSIST = "gap_draft_assist"
    EMBEDDING = "embedding"


# Built-in intent → route fallback (cold, code-level)
DEFAULT_INTENT_ROUTES: dict[Intent, Route] = {
    Intent.FAQ: Route.RAG,
    Intent.PRODUCT: Route.RAG,
    Intent.ORDER_QUERY: Route.TOOL,
    Intent.FAULT_REPORT: Route.TICKET,
    Intent.COMPLAINT: Route.TICKET,
    Intent.HANDOFF: Route.HANDOFF,
    Intent.OUT_OF_SCOPE: Route.REFUSE,
}

LEGAL_INTENTS = frozenset(Intent)
LEGAL_ROUTES = frozenset(Route)
