"""Argon2id for new hashes with transparent legacy bcrypt verification."""

from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from passlib.context import CryptContext

ARGON_MEMORY_KIB = 19_456
ARGON_ITERATIONS = 2
ARGON_PARALLELISM = 1
ARGON_SALT_BYTES = 16
ARGON_HASH_BYTES = 32
LEGACY_PASSWORDS = CryptContext(schemes=["bcrypt"], deprecated="auto")


@lru_cache
def hasher():
    return PasswordHasher(time_cost=ARGON_ITERATIONS, memory_cost=ARGON_MEMORY_KIB,
                          parallelism=ARGON_PARALLELISM, salt_len=ARGON_SALT_BYTES,
                          hash_len=ARGON_HASH_BYTES)


def hash_password(password: str) -> str:
    return hasher().hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed.startswith("$argon2"):
        try:
            return LEGACY_PASSWORDS.verify(plain, hashed)
        except (ValueError, TypeError):
            return False
    try:
        return hasher().verify(hashed, plain)
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    return not hashed.startswith("$argon2id$") or hasher().check_needs_rehash(hashed)


@lru_cache
def dummy_hash() -> str:
    return hash_password("timing-only-placeholder-never-a-real-password")
