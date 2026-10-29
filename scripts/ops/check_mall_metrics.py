"""Incremental report using the unmodified repository metric checker.

Numeric findings remain visible. Only documented test literals and route-layer
HTTP statuses are exempt from the blocking gate; structure is never exempt.
"""

import argparse
import hashlib
import json
import subprocess
from dataclasses import asdict
from pathlib import Path

from check_code_metrics import (
    MAX_FILE_LINES,
    ROOT,
    Finding,
    Report,
    check_python,
    count_physical_lines,
)

HTTP_STATUS_MIN = 100
HTTP_STATUS_MAX = 599


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def changed_files(base):
    names = set(git("diff", "--name-only", base).splitlines())
    names.update(git("ls-files", "--others", "--exclude-standard").splitlines())
    return sorted(ROOT / name for name in names if (ROOT / name).is_file()
                  and Path(name).suffix in {".py", ".ts", ".tsx"})


def exempt(finding):
    if finding.metric != "magic_number":
        return False
    if "/tests/" in finding.path:
        return True
    return (finding.path.endswith(("api.py", "routes.py"))
            and isinstance(finding.value, int)
            and HTTP_STATUS_MIN <= finding.value <= HTTP_STATUS_MAX)


def report(base):
    result = Report()
    paths = changed_files(base)
    for path in paths:
        size = count_physical_lines(path)
        if size > MAX_FILE_LINES:
            result.add(Finding("file_size", str(path.relative_to(ROOT)),
                               "physical lines", size, MAX_FILE_LINES, 1))
        if path.suffix == ".py":
            check_python(path, result)
    return evidence(base, paths, result)


def evidence(base, paths, result):
    blocking = [asdict(f) for f in result.findings if not exempt(f)]
    production_structure = [f for f in blocking if "/tests/" not in f["path"]
                            and f["metric"] != "magic_number"]
    return {"base": git("rev-parse", base), "head": git("rev-parse", "HEAD"),
            "working_tree": bool(git("status", "--porcelain")), "files": {
                str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
            "production_structure": production_structure, "blocking": blocking,
            "raw_findings": [asdict(f) for f in result.findings]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="main")
    parser.add_argument("--output", type=Path, default=Path("docs/mall/fix-metrics.json"))
    args = parser.parse_args()
    result = report(args.base)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"production structure: {len(result['production_structure'])}; "
          f"blocking: {len(result['blocking'])}; report: {args.output}")
    return int(bool(result["blocking"]))


if __name__ == "__main__":
    raise SystemExit(main())
