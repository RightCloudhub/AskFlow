"""Application identity mapping shared by authenticated Agent endpoints."""

from app.services.agent.service.contracts import Scope

# The current account model has no tenant memberships; each deployment owns its database.
DEPLOYMENT_SCOPE = "deployment"


def customer_scope(user_id: str) -> Scope:
    return Scope(organization_id=DEPLOYMENT_SCOPE, customer_id=user_id)
