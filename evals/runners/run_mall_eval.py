"""Execute deterministic mall chat evals without a model or external test services."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEST_FILE = "tests/mall/test_chat_eval.py"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="Require explicit test PostgreSQL/Redis URLs")
    parser.add_argument("--output", default="artifacts/mall-eval.xml")
    args = parser.parse_args()
    report = ROOT / args.output
    report.parent.mkdir(parents=True, exist_ok=True)
    environment = {**os.environ, "ASKFLOW_ENV": "test", "LLM_BASE_URL": "", "LLM_API_KEY": "",
                   "EMBEDDING_BASE_URL": "", "EMBEDDING_API_KEY": ""}
    selection = "full" if args.full else "lite"
    if args.full:
        environment["MALL_REQUIRE_FULL"] = "1"
    command = [sys.executable, "-m", "pytest", TEST_FILE, "-q", "-k", selection,
               "--junitxml=" + str(report)]
    result = subprocess.run(command, cwd=ROOT / "apps/api", env=environment, check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
