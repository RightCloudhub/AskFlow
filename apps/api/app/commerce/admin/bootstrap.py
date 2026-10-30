"""One-time local administrator provisioning; password is never a CLI argument."""

import argparse
import asyncio
import getpass
import sys

from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, text

from app.core import database
from app.core.config import get_settings
# Register the ORM models before commerce services load their dependencies.
from app.models.user import User

from app.commerce.account.hooks import password_policy
from app.commerce.account.identity import initialize_extensions
from app.commerce.admin.permissions import seed_roles
from app.commerce.core.audit import audit
from app.services.auth.password import hash_password

BOOTSTRAP_LOCK = 1095976519
USERNAME_MIN = 3
USERNAME_MAX = 64


class Administrator(BaseModel):
    username: str = Field(min_length=USERNAME_MIN, max_length=USERNAME_MAX, pattern=r"^[a-z0-9_-]+$")
    email: EmailStr


async def provision(identity, password: str):
    get_settings().assert_startup_safe()
    await password_policy(password)
    hashed = await asyncio.to_thread(hash_password, password)
    async with database.SessionLocal() as db:
        if db.bind.dialect.name == "sqlite":
            await db.execute(text("BEGIN IMMEDIATE"))
        else:
            await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": BOOTSTRAP_LOCK})
        if await db.scalar(select(User.id).where(User.role == "admin").limit(1)):
            raise ValueError("Administrator already exists; use authenticated user administration")
        user = User(username=identity.username, email=str(identity.email), hashed_password=hashed, role="admin")
        db.add(user)
        await db.flush()
        await initialize_extensions(db, user.id)
        await seed_roles(db)
        await audit(db, actor_id=user.id, action="administrator_bootstrap")
        await db.commit()
        return user.id


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password-stdin", action="store_true")
    args = parser.parse_args()
    identity = Administrator(username=args.username, email=args.email)
    password = sys.stdin.readline().rstrip("\n") if args.password_stdin else getpass.getpass("Password: ")
    print("Administrator created:", asyncio.run(provision(identity, password)))


if __name__ == "__main__":
    main()
