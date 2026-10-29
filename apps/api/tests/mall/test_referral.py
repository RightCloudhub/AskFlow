"""Invitation immutability and concurrency cannot manufacture a referral cycle."""

import asyncio

import pytest
from sqlalchemy import select

from app.commerce.core.errors import MallError
from app.commerce.referral.models import ReferralRelation
from app.commerce.referral.service import ReferralService

from .helpers import seed, transaction


async def code(runtime, identity):
    result = await transaction(runtime, lambda db: ReferralService(db).code(identity["user_id"]))
    return result["code"]


@pytest.mark.asyncio
async def test_concurrent_reciprocal_binding_is_acyclic(mall_runtime):
    first, second = await seed(mall_runtime), await seed(mall_runtime)
    first_code, second_code = await code(mall_runtime, first), await code(mall_runtime, second)

    async def bind(identity, invitation):
        try:
            await transaction(mall_runtime, lambda db: ReferralService(db).bind(identity["user_id"],
                code=invitation, device="shared-device", ip="192.0.2.1"))
            return True
        except MallError as exc:
            assert exc.code == "invalid_invitation"
            return False

    results = await asyncio.gather(bind(first, second_code), bind(second, first_code))
    assert sum(results) == 1
    async with mall_runtime.sessions() as db:
        assert len(list(await db.scalars(select(ReferralRelation)))) == 1


@pytest.mark.asyncio
async def test_repeat_binding_keeps_first_inviter(mall_runtime):
    inviter, other, invitee = await seed(mall_runtime), await seed(mall_runtime), await seed(mall_runtime)
    invitation, different = await code(mall_runtime, inviter), await code(mall_runtime, other)

    async def bind(value):
        return await transaction(mall_runtime, lambda db: ReferralService(db).bind(invitee["user_id"],
            code=value, device="device", ip="192.0.2.2"))

    first, repeated = await bind(invitation), await bind(invitation)
    assert first["id"] == repeated["id"] and not repeated["created"]
    with pytest.raises(MallError, match="invitation_immutable"):
        await bind(different)
