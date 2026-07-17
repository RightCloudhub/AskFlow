"""Resolve enabled plugins from features.yaml + env profile/deltas."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

DEFAULT_PROFILE = "full"
MANIFEST_CANDIDATES = (
    Path(__file__).resolve().parents[4] / "packages" / "contracts" / "features.yaml",
    Path(__file__).resolve().parents[3] / "packages" / "contracts" / "features.yaml",
    Path.cwd() / "packages" / "contracts" / "features.yaml",
    Path.cwd().parent.parent / "packages" / "contracts" / "features.yaml",
)


class ManifestError(RuntimeError):
    """Invalid profile, unknown plugin, or dependency cycle/missing dep."""


def _find_manifest() -> Path:
    for path in MANIFEST_CANDIDATES:
        if path.is_file():
            return path
    raise ManifestError(
        "features.yaml not found; expected under packages/contracts/features.yaml"
    )


@lru_cache
def load_manifest_raw() -> dict[str, Any]:
    path = _find_manifest()
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ManifestError("features.yaml root must be a mapping")
    return data


def clear_manifest_cache() -> None:
    load_manifest_raw.cache_clear()


def parse_feature_deltas(raw: str | None) -> tuple[set[str], set[str]]:
    """Parse ASKFLOW_FEATURES like '+sla,-mcp,teams' into add/remove sets."""
    add: set[str] = set()
    remove: set[str] = set()
    if not raw or not raw.strip():
        return add, remove
    for part in raw.split(","):
        token = part.strip()
        if not token:
            continue
        if token.startswith("+"):
            add.add(token[1:].strip())
        elif token.startswith("-"):
            remove.add(token[1:].strip())
        else:
            add.add(token)
    return add, remove


def resolve_features(
    profile: str | None = None,
    feature_deltas: str | None = None,
    *,
    manifest: dict[str, Any] | None = None,
) -> frozenset[str]:
    data = manifest if manifest is not None else load_manifest_raw()
    profiles: dict[str, list[str]] = data.get("profiles") or {}
    plugins_meta: dict[str, Any] = data.get("plugins") or {}
    known = set(plugins_meta.keys())

    name = (profile or DEFAULT_PROFILE).strip() or DEFAULT_PROFILE
    if name not in profiles:
        raise ManifestError(f"Unknown profile {name!r}; known={sorted(profiles)}")

    selected: set[str] = set(profiles[name])
    add, remove = parse_feature_deltas(feature_deltas)
    selected |= add
    selected -= remove

    unknown = selected - known
    if unknown:
        raise ManifestError(f"Unknown plugin id(s): {sorted(unknown)}")

    return frozenset(_expand_deps(selected, plugins_meta))


def _expand_deps(selected: set[str], plugins_meta: dict[str, Any]) -> set[str]:
    """Close dependency set; fail if missing dependency not in selection after close."""
    resolved: set[str] = set()
    visiting: set[str] = set()

    def visit(pid: str) -> None:
        if pid in resolved:
            return
        if pid in visiting:
            raise ManifestError(f"Plugin dependency cycle at {pid!r}")
        if pid not in plugins_meta:
            raise ManifestError(f"Unknown plugin in dependency graph: {pid!r}")
        visiting.add(pid)
        deps = list((plugins_meta[pid] or {}).get("depends") or [])
        for dep in deps:
            visit(dep)
        visiting.discard(pid)
        resolved.add(pid)

    for pid in sorted(selected):
        visit(pid)
    return resolved


def topological_order(
    enabled: frozenset[str],
    *,
    manifest: dict[str, Any] | None = None,
) -> list[str]:
    data = manifest if manifest is not None else load_manifest_raw()
    plugins_meta: dict[str, Any] = data.get("plugins") or {}
    order: list[str] = []
    seen: set[str] = set()
    visiting: set[str] = set()

    def visit(pid: str) -> None:
        if pid in seen or pid not in enabled:
            return
        if pid in visiting:
            raise ManifestError(f"Plugin dependency cycle at {pid!r}")
        visiting.add(pid)
        for dep in (plugins_meta.get(pid) or {}).get("depends") or []:
            visit(dep)
        visiting.discard(pid)
        seen.add(pid)
        order.append(pid)

    for pid in sorted(enabled):
        visit(pid)
    return order
