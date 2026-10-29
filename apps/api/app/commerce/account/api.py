"""Account route assembly."""

from fastapi import APIRouter

from app.commerce.account.address_api import router as addresses
from app.commerce.account.auth_api import router as auth
from app.commerce.account.profile_api import router as profile
from app.commerce.account.security_api import router as security

router = APIRouter()
router.include_router(auth)
router.include_router(profile)
router.include_router(security)
router.include_router(addresses)
