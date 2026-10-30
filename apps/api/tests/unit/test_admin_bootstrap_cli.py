"""Exercise bootstrap in fresh interpreters so app imports cannot hide cycles."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.commerce.account.models import UserProfile, UserSecurity
from app.models.audit import AuditLog
from app.models.user import User
from app.services.auth.password import verify_password

API_ROOT = Path(__file__).resolve().parents[2]
CLI_TIMEOUT_SECONDS = 30
PASSWORD = "Bootstrap-test-password-123"


def cli_environment(tmp_path):
    return {
        **os.environ,
        "ASKFLOW_ENV": "test",
        "ASKFLOW_PROFILE": "mall-lite",
        "DATABASE_URL": "sqlite+aiosqlite:///" + str(tmp_path / "bootstrap.db"),
        "DATABASE_READ_URLS": "",
        "MALL_PASSWORD_BREACH_CHECK": "false",
    }


def run_python(arguments, environment, *, input_text=None):
    return subprocess.run(
        [sys.executable, *arguments], cwd=API_ROOT, env=environment,
        input=input_text, text=True, capture_output=True, timeout=CLI_TIMEOUT_SECONDS,
    )


def test_bootstrap_help_in_fresh_process(tmp_path):
    result = run_python(
        ["-m", "app.commerce.admin.bootstrap", "--help"], cli_environment(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    assert "--username" in result.stdout
    assert "--password-stdin" in result.stdout


@pytest.mark.asyncio
async def test_bootstrap_persists_admin_and_refuses_second_admin(tmp_path):
    environment = cli_environment(tmp_path)
    initialized = run_python(
        ["-c", "import asyncio; from app.core.database import init_db; asyncio.run(init_db())"],
        environment,
    )
    assert initialized.returncode == 0, initialized.stderr
    arguments = ["-m", "app.commerce.admin.bootstrap", "--username", "admin",
                 "--email", "admin@example.com", "--password-stdin"]
    created = run_python(arguments, environment, input_text=PASSWORD + "\n")
    assert created.returncode == 0, created.stderr
    assert "Administrator created:" in created.stdout
    assert PASSWORD not in created.stdout + created.stderr
    rejected = run_python(arguments, environment, input_text=PASSWORD + "\n")
    assert rejected.returncode != 0
    assert "Administrator already exists" in rejected.stderr
    await assert_admin_persisted(environment["DATABASE_URL"])


async def assert_admin_persisted(url):
    engine = create_async_engine(url)
    try:
        sessions = async_sessionmaker(engine)
        async with sessions() as db:
            assert await db.scalar(select(func.count()).select_from(User)) == 1
            user = await db.scalar(select(User).where(User.username == "admin"))
            assert user.role == "admin"
            assert verify_password(PASSWORD, user.hashed_password)
            assert await db.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
            assert await db.scalar(select(UserSecurity).where(UserSecurity.user_id == user.id))
            assert await db.scalar(select(AuditLog).where(AuditLog.action == "mall.administrator_bootstrap"))
    finally:
        await engine.dispose()
