"""RFC TOTP vectors and single-use recovery credentials."""

import base64
import time

import pytest

from app.commerce.account import mfa
from app.commerce.account.crypto import TOTP_PERIOD, totp
from app.commerce.account.schemas import MfaCode
from app.commerce.core.errors import MallError
from app.models.user import User

from .helpers import seed, transaction


@pytest.mark.parametrize("timestamp,expected", [(59, "287082"), (1111111109, "081804"), (1234567890, "005924")])
def test_rfc6238_six_digit_vectors(timestamp, expected):
    secret = base64.b32encode(b"12345678901234567890").decode()
    assert totp(secret, timestamp // TOTP_PERIOD) == expected


@pytest.mark.asyncio
async def test_recovery_codes_are_one_time(mall_runtime):
    identity = await seed(mall_runtime)

    async def setup(db):
        user = await db.get(User, identity["user_id"])
        enrollment = await mfa.setup(db, user)
        code = totp(enrollment["secret"], int(time.time()) // TOTP_PERIOD)
        return await mfa.enable(db, user, MfaCode(totp=code))

    enrollment = await transaction(mall_runtime, setup)
    assert len(enrollment["recovery_codes"]) == 10
    credential = MfaCode(recovery_code=enrollment["recovery_codes"][0])
    await transaction(mall_runtime, lambda db: mfa.verify_factor(db, identity["user_id"], credential))
    with pytest.raises(MallError):
        await transaction(mall_runtime, lambda db: mfa.verify_factor(db, identity["user_id"], credential))
    with pytest.raises(MallError):
        await transaction(mall_runtime, lambda db: mfa.verify_factor(db, identity["user_id"], MfaCode()))
