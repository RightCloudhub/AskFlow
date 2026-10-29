"""Account inputs never accept role, assurance, owner or raw storage fields."""

from typing import Literal

from pydantic import Field

from app.commerce.core.constants import NAME_SIZE
from app.commerce.core.schemas import Schema, Versioned

USERNAME_SIZE = 64
MIN_USERNAME_SIZE = 3
PASSWORD_LIMIT = 128
CODE_DIGITS = 6


class VerificationSend(Schema):
    target: str = Field(min_length=1, max_length=255)
    channel: Literal["email", "sms"]
    purpose: Literal["register", "login", "password-reset", "bind-old", "bind-new", "step-up"]


class VerifyCode(Schema):
    challenge_id: str
    code: str = Field(min_length=CODE_DIGITS, max_length=CODE_DIGITS)


class Proof(Schema):
    verification_id: str
    verification_token: str


class Credentials(Schema):
    totp: str = ""
    recovery_code: str = ""


class Register(Proof):
    username: str = Field(min_length=MIN_USERNAME_SIZE, max_length=USERNAME_SIZE)
    password: str = Field(max_length=PASSWORD_LIMIT)
    referral_code: str = ""
    device: str = Field(default="", max_length=NAME_SIZE)


class Login(Credentials):
    identifier: str = Field(min_length=1, max_length=255)
    password: str = Field(default="", max_length=PASSWORD_LIMIT)
    verification_id: str = ""
    verification_token: str = ""
    device: str = Field(default="", max_length=NAME_SIZE)


class OidcLogin(Credentials):
    id_token: str
    device: str = ""


class Refresh(Schema):
    refresh_token: str | None = None


class Forgot(Schema):
    identifier: str


class ResetPassword(Proof):
    new_password: str = Field(max_length=PASSWORD_LIMIT)


class ChangePassword(Schema):
    old_password: str = Field(max_length=PASSWORD_LIMIT)
    new_password: str = Field(max_length=PASSWORD_LIMIT)
    step_up_token: str


class StepUp(Credentials):
    purpose: str = Field(min_length=1, max_length=NAME_SIZE)
    verification_id: str = ""
    verification_token: str = ""


class ProfilePatch(Versioned):
    nickname: str = Field(default="", max_length=NAME_SIZE)
    region: str = Field(default="", max_length=NAME_SIZE)
    locale: Literal["zh-CN", "en-US"] = "zh-CN"


class AddressInput(Schema):
    name: str = Field(min_length=1, max_length=NAME_SIZE)
    phone: str = Field(min_length=1, max_length=NAME_SIZE)
    address: str = Field(min_length=1, max_length=1024)
    is_default: bool = False


class AddressPatch(AddressInput, Versioned):
    pass


class BindingChange(Schema):
    old: Proof
    new: Proof
    channel: Literal["email", "sms"]
    step_up_token: str


class MfaCode(Credentials):
    pass


class CloseAccount(Schema):
    step_up_token: str
