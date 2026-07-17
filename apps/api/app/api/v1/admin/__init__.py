"""Admin router is mounted by plugins onto AppContext.admin_router.

This module remains for import compatibility; prefer plugin assembly.
"""

from fastapi import APIRouter

# Legacy empty shell — real routes come from plugins
admin_router = APIRouter(prefix="/admin")
