"""Commerce audit uses the application's masking and trace context."""

from app.core.trace import get_trace_id
from app.services.audit.logger.service import AuditService


async def audit(db, *, actor_id: str, action: str, resource_id: str = "", detail: dict | None = None):
    return await AuditService(db).log(actor_id=actor_id, action="mall." + action,
                                    resource_type="mall", resource_id=resource_id,
                                    detail=detail, trace_id=get_trace_id())
