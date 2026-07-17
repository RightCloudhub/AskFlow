#!/usr/bin/env python3
"""CLI: python -m evals.runners.run_eval  (from apps/api with PYTHONPATH)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow running as script from repo
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.services.eval_runner.runner import EvalRunner  # noqa: E402


async def main() -> int:
    report = await EvalRunner().run()
    print(f"passed={report.passed} failed={report.failed} ok={report.ok}")
    for r in report.results:
        mark = "OK" if r.ok else "FAIL"
        print(f"  [{mark}] {r.path}: {r.detail}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
