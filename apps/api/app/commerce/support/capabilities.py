"""Mall capability catalog is enabled only by the support plugin."""

from app.services.agent.gateway.capabilities import CapabilitySpec

CAPABILITIES = {
    "mall.order.get": CapabilitySpec(name="mall.order.get"),
    "mall.logistics.get": CapabilitySpec(name="mall.logistics.get"),
    "mall.wallet.balance": CapabilitySpec(name="mall.wallet.balance"),
    "mall.order.cancel": CapabilitySpec(name="mall.order.cancel", side_effect="irreversible_write",
        required_assurance=2, requires_confirmation=True),
    "mall.refund.submit": CapabilitySpec(name="mall.refund.submit", side_effect="irreversible_write",
        required_assurance=2, requires_confirmation=True),
}
