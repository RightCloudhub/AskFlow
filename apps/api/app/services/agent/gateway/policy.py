"""In-house versioned policy engine; model output never grants authority (arch §4.4)."""

from dataclasses import dataclass

from app.services.agent.gateway.capabilities import CapabilitySpec
from app.services.agent.gateway.settings import GatewaySettings

# Business limits: writes above the auto-approval amount require a human.
AMOUNT_LIMITS: dict[str, float] = {"refund.submit": 50.0, "payments.refund": 50.0}
AMOUNT_KEYS = ("amount_eur", "amount")
AMOUNT_CENTS_KEYS = ("amount_cents",)
CENTS_PER_EUR = 100


@dataclass(frozen=True)
class PolicyDecision:
    allow: bool
    requires_confirmation: bool = False
    requires_human_approval: bool = False
    step_up_required: bool = False
    reasons: tuple[str, ...] = ()
    version: str = "1"

    def to_dict(self) -> dict:
        return {
            "allow": self.allow,
            "requires_confirmation": self.requires_confirmation,
            "requires_human_approval": self.requires_human_approval,
            "step_up_required": self.step_up_required,
            "reasons": list(self.reasons),
            "version": self.version,
        }


class PolicyEngine:
    def __init__(self, settings: GatewaySettings | None = None) -> None:
        self.settings = settings or GatewaySettings()

    def evaluate(
        self,
        *,
        capability: CapabilitySpec,
        args: dict,
        assurance: int,
        has_confirmation: bool = False,
    ) -> PolicyDecision:
        version = self.settings.policy_version
        if assurance < capability.required_assurance:
            return PolicyDecision(
                allow=False,
                step_up_required=True,
                reasons=("assurance_too_low",),
                version=version,
            )
        requires_human = self._over_amount_limit(capability, args)
        reasons = ("amount_over_limit",) if requires_human else ()
        return PolicyDecision(
            allow=True,
            requires_confirmation=capability.requires_confirmation and not has_confirmation,
            requires_human_approval=requires_human,
            reasons=reasons,
            version=version,
        )

    @staticmethod
    def _over_amount_limit(capability: CapabilitySpec, args: dict) -> bool:
        limit = AMOUNT_LIMITS.get(capability.name)
        if limit is None:
            return False
        for key in AMOUNT_KEYS:
            value = args.get(key)
            if isinstance(value, (int, float)) and value > limit:
                return True
        for key in AMOUNT_CENTS_KEYS:
            value = args.get(key)
            if isinstance(value, (int, float)) and value > limit * CENTS_PER_EUR:
                return True
        return False
