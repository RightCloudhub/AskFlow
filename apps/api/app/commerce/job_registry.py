"""Bounded work discovery; execute each item in its own leased transaction."""

from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import import_module

from sqlalchemy import select

from app.commerce.core.services import enabled
from app.core.config import get_settings


@dataclass(frozen=True, kw_only=True)
class Job:
    name: str
    module: str
    model: str
    states: tuple[str, ...]
    state_column: str = "status"
    due_column: str = ""


JOBS = (
    Job(name="verification", module="account", model="VerificationCode", states=("pending", "retry"),
        state_column="delivery_status", due_column="delivery_next_at"),
    Job(name="expiry", module="order", model="Order", states=("PENDING_PAYMENT",), due_column="expires_at"),
    Job(name="refund", module="order", model="Refund", states=("approved",)),
    Job(name="payment", module="payment", model="Payment",
        states=("pending", "cancelled", "failed", "late_payment")),
    Job(name="reward", module="referral", model="ReferralReward", states=("pending",), due_column="eligible_at"),
    Job(name="notification", module="notify", model="NotificationDelivery", states=("pending", "retry"),
        due_column="next_attempt_at"),
    Job(name="flash", module="inventory", model="FlashRequest", states=("queued",)),
)


def model_for(job):
    suffix = "refund_models" if job.model == "Refund" else "models"
    return getattr(import_module("app.commerce." + job.module + "." + suffix), job.model)


def active(job):
    if job.name == "refund" and not enabled("payment"):
        return False
    if job.name in {"reward", "flash"} and not enabled("order"):
        return False
    return enabled(job.module)


async def pending_ids(db, job):
    model = model_for(job)
    statement = select(model.id).where(getattr(model, job.state_column).in_(job.states))
    if job.due_column:
        statement = statement.where(getattr(model, job.due_column) <= datetime.now(UTC))
    if job.name == "payment":
        statement = statement.where(model.external_cents > 0)
    return list(await db.scalars(statement.order_by(model.updated_at, model.id)
                                .limit(get_settings().mall_worker_batch)))
