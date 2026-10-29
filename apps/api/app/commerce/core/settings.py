"""Commerce business configuration; secrets are never runtime admin settings."""

import logging

from pydantic import Field

from app.commerce.infra.settings import InfraSettings

MIN_SECRET_SIZE = 32
SENSITIVE_KEYS = ("payment_callback_secret", "mall_totp_key", "mall_refresh_secret")
DEVELOPMENT_SECRET = "development-commerce-secret-never-for-production"


class CommerceSettings(InfraSettings):
    mall_currency: str = Field(default="CNY", pattern=r"^[A-Z]{3}$")
    mall_public_register: bool = False
    mall_access_minutes: int = Field(default=15, ge=1)
    mall_refresh_days: int = Field(default=30, ge=1)
    mall_verification_seconds: int = Field(default=300, ge=1)
    mall_verification_attempts: int = Field(default=5, ge=1)
    mall_verification_interval_seconds: int = Field(default=60, ge=1)
    mall_password_min_length: int = Field(default=12, ge=1)
    mall_password_max_length: int = Field(default=128, ge=1)
    mall_login_max_failures: int = Field(default=5, ge=1)
    mall_login_lock_seconds: int = Field(default=30, ge=1)
    mall_login_max_lock_seconds: int = Field(default=3600, ge=1)
    mall_login_min_seconds: float = Field(default=0.25, ge=0)
    mall_step_up_seconds: int = Field(default=300, ge=1)
    mall_totp_key: str = DEVELOPMENT_SECRET + ":totp"
    mall_refresh_secret: str = DEVELOPMENT_SECRET + ":refresh"
    payment_callback_secret: str = DEVELOPMENT_SECRET + ":payment"
    mall_payment_mock_enabled: bool = True
    mall_payment_callback_window_seconds: int = Field(default=300, ge=1)
    mall_payment_step_up_cents: int = Field(default=100000, ge=0)
    mall_checkout_seconds: int = Field(default=300, ge=1)
    mall_reservation_seconds: int = Field(default=900, ge=1)
    mall_idempotency_seconds: int = Field(default=86400, ge=1)
    mall_order_max_items: int = Field(default=50, ge=1)
    mall_order_max_quantity: int = Field(default=100, ge=1)
    mall_shipping_cents: int = Field(default=0, ge=0)
    mall_auto_refund_cents: int = Field(default=5000, ge=0)
    mall_referral_reward_cents: int = Field(default=100, ge=0)
    mall_referral_registration_cents: int = Field(default=0, ge=0)
    mall_referral_valid_days: int = Field(default=30, ge=1)
    mall_referral_phone_prefix_length: int = Field(default=7, ge=3, le=12)
    mall_referral_ip_limit: int = Field(default=10, ge=1)
    mall_referral_phone_limit: int = Field(default=3, ge=1)
    mall_referral_payer_limit: int = Field(default=1, ge=1)
    mall_risk_device_score: int = Field(default=50, ge=0)
    mall_risk_ip_score: int = Field(default=25, ge=0)
    mall_risk_phone_score: int = Field(default=25, ge=0)
    mall_risk_payer_score: int = Field(default=100, ge=0)
    mall_referral_basis_points: int = Field(default=0, ge=0, le=10000)
    mall_referral_delay_days: int = Field(default=7, ge=0)
    mall_referral_daily_cents: int = Field(default=10000, ge=0)
    mall_referral_total_cents: int = Field(default=100000, ge=0)
    mall_referral_device_limit: int = Field(default=1, ge=1)
    mall_risk_review_score: int = Field(default=50, ge=1)
    mall_withdraw_enabled: bool = False
    mall_notification_rate_per_hour: int = Field(default=20, ge=1)
    mall_password_breach_check: bool = False
    mall_captcha_enabled: bool = False
    mall_demo_mailbox_enabled: bool = False

    def commerce_enabled(self) -> bool:
        from app.plugins.manifest import resolve_features

        return "mall_core" in resolve_features(self.askflow_profile, self.askflow_features)

    def mall_register_allowed(self) -> bool:
        if self.disable_local_register:
            return False
        return self.local_register_allowed() or self.mall_public_register

    def assert_commerce_safe(self) -> None:
        if not self.commerce_enabled():
            return
        unsafe = self._commerce_unsafe_reasons()
        if not unsafe:
            return
        if self.is_production_like:
            raise RuntimeError("Unsafe commerce configuration: " + "; ".join(unsafe))
        logging.getLogger("askflow.mall").warning("Commerce degradation: %s", "; ".join(unsafe))

    def _commerce_unsafe_reasons(self) -> list[str]:
        reasons = []
        multi = max(self.instance_count, self.web_concurrency) > 1
        if multi and (self.lock_backend == "memory" or self.rate_limit_backend == "memory"):
            reasons.append("multi-instance memory coordination/rate limiting")
        if multi and not self.mall_rate_limit_enabled:
            reasons.append("multi-instance rate limiting is disabled")
        if multi and self.database_url.startswith("sqlite"):
            reasons.append("multi-instance SQLite deployment")
        if self.is_production_like:
            reasons.extend(self._weak_commerce_keys())
        if self.mall_demo_mailbox_enabled and self.is_production_like:
            reasons.append("demo verification mailbox is forbidden")
        return reasons

    def _weak_commerce_keys(self) -> list[str]:
        values = [getattr(self, name) for name in SENSITIVE_KEYS]
        reasons = []
        for name, value in zip(SENSITIVE_KEYS, values, strict=True):
            if len(value) < MIN_SECRET_SIZE or value.startswith(DEVELOPMENT_SECRET):
                reasons.append(name + " must be an independent strong secret")
        if len(set(values)) != len(values):
            reasons.append("commerce secrets must be distinct")
        return reasons
