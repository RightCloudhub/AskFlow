"""The first migration can add/remove task storage alongside existing application tables."""

import os
from pathlib import Path
import sqlite3
import subprocess
import sys


def test_task_migration_round_trip(tmp_path):
    database = tmp_path / "migration.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE existing_business_data (id TEXT PRIMARY KEY)")
        connection.execute("INSERT INTO existing_business_data VALUES ('preserved')")
    env = {**os.environ, "DATABASE_URL": f"sqlite+aiosqlite:///{database}"}
    root = Path(__file__).resolve().parents[2]
    _migrate(root, env, direction="upgrade", target="head")
    with sqlite3.connect(database) as connection:
        columns = connection.execute("PRAGMA table_info(service_tasks)").fetchall()
        assert {column[1] for column in columns} == {
            "id", "organization_id", "customer_id", "version", "checkpoint",
            "created_at", "updated_at",
        }
    _migrate(root, env, direction="downgrade", target="base")
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA table_info(service_tasks)").fetchall() == []
        assert connection.execute("SELECT id FROM existing_business_data").fetchall() == [
            ("preserved",),
        ]


def _migrate(root, env, *, direction, target):
    subprocess.run([sys.executable, "-m", "alembic", direction, target], cwd=root,
                   env=env, check=True, capture_output=True, text=True, timeout=30)
