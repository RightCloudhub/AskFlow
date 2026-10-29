"""Whitelisted settings read on primary; no environment or Harness writes."""

from http import HTTPStatus

from pydantic import ValidationError
from sqlalchemy import select

from app.commerce.admin.models import MallSetting, SettingRevision
from app.commerce.core.errors import MallError
from app.commerce.core.events import publish
from app.commerce.core.repository import cas, insert_once
from app.core.config import get_settings
from app.plugins.runtime import require_app_context

EDITABLE = frozenset({
    "mall_shipping_cents", "mall_auto_refund_cents", "mall_referral_reward_cents",
    "mall_referral_basis_points", "mall_referral_delay_days", "mall_referral_daily_cents",
    "mall_referral_total_cents", "mall_referral_device_limit", "mall_risk_review_score",
    "mall_notification_rate_per_hour",
    "mall_referral_registration_cents", "mall_referral_valid_days", "mall_referral_phone_prefix_length",
    "mall_referral_ip_limit", "mall_referral_phone_limit", "mall_referral_payer_limit",
    "mall_risk_device_score", "mall_risk_ip_score", "mall_risk_phone_score", "mall_risk_payer_score",
})


async def value(db, key: str):
    if key not in EDITABLE:
        raise MallError("setting_not_editable", status=HTTPStatus.UNPROCESSABLE_ENTITY)
    row = await db.scalar(select(MallSetting).where(MallSetting.key == key))
    if row is None:
        return getattr(get_settings(), key)
    cache = require_app_context().services.setdefault("mall_setting_cache", {})
    version, cached = cache.get(key, (None, None))
    if version != row.version:
        cached = row.value["value"]
        cache[key] = row.version, cached
    return cached


async def list_settings(db):
    rows = {row.key: row for row in await db.scalars(select(MallSetting))}
    return [{"key": key, "value": rows[key].value["value"] if key in rows
             else getattr(get_settings(), key), "version": rows[key].version if key in rows else 0}
            for key in sorted(EDITABLE)]


async def change(ctx, key: str, payload):
    if key not in EDITABLE:
        raise MallError("setting_not_editable", status=HTTPStatus.UNPROCESSABLE_ENTITY)
    settings = get_settings()
    candidate = settings.model_dump()
    candidate[key] = payload.value
    try:
        type(settings).model_validate(candidate)
    except ValidationError as exc:
        raise MallError("invalid_setting_value", status=HTTPStatus.UNPROCESSABLE_ENTITY) from exc
    created = await insert_once(ctx.db, MallSetting, values={"key": key,
        "value": {"value": getattr(settings, key)}, "modified_by": ctx.user.id}, unique=["key"])
    if created:
        ctx.db.add(SettingRevision(key=key, value={"value": getattr(settings, key)},
                                   version=0, modified_by=ctx.user.id))
    row = await ctx.db.scalar(select(MallSetting).where(MallSetting.key == key))
    if row.version != payload.expected_version:
        raise MallError("version_conflict")
    previous = row.value
    await cas(ctx.db, row, values={"value": {"value": payload.value}, "modified_by": ctx.user.id})
    ctx.db.add(SettingRevision(key=key, value=row.value, version=row.version,
                               modified_by=ctx.user.id))
    await publish(ctx.db, row, event_type="mall.settings.changed", payload={"key": key})
    return {"key": key, "before": previous, "value": payload.value, "version": row.version}
