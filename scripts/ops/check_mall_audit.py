"""Block newly introduced dependency findings relative to the same CI scan of the base ref."""

import argparse
import json
from pathlib import Path

BLOCKING_SEVERITIES = frozenset({"high", "critical"})


def fingerprints(path: Path, kind: str):
    data = json.loads(path.read_text())
    if kind == "pip":
        if "dependencies" not in data:
            raise ValueError("Incomplete pip-audit report")
        return pip_findings(data)
    if "vulnerabilities" not in data or data.get("error"):
        raise ValueError("Incomplete npm audit report")
    return npm_findings(data)


def pip_findings(data):
    return {(row["name"], finding["id"])
            for row in data["dependencies"] for finding in row.get("vulns", [])}


def npm_advisory(package, finding):
    if isinstance(finding, dict):
        return str(finding.get("source", finding.get("url", package)))
    if isinstance(finding, str):
        return "via:" + finding
    return None


def npm_findings(data):
    findings = set()
    for package, row in data["vulnerabilities"].items():
        if row["severity"] not in BLOCKING_SEVERITIES:
            continue
        for finding in row.get("via", []):
            advisory = npm_advisory(package, finding)
            if advisory:
                findings.add((package, advisory))
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=["pip", "npm"])
    parser.add_argument("base", type=Path)
    parser.add_argument("head", type=Path)
    args = parser.parse_args()
    introduced = sorted(fingerprints(args.head, args.kind) - fingerprints(args.base, args.kind))
    for package, advisory in introduced:
        print(f"New dependency finding: {package} {advisory}")
    return int(bool(introduced))


if __name__ == "__main__":
    raise SystemExit(main())
