"""Auth services; importing password helpers must not load token consumers."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.auth.service import AuthService

__all__ = ["AuthService"]


def __getattr__(name: str):
    if name != "AuthService":
        raise AttributeError(name)
    from app.services.auth.service import AuthService

    return AuthService
