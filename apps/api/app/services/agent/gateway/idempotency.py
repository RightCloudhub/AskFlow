"""Deterministic idempotency keys: hash(scope, step, capability, normalized args) (arch §4.4)."""

import hashlib
import json


def normalize_args(args: dict) -> str:
    return json.dumps(args, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def args_hash(args: dict) -> str:
    return hashlib.sha256(normalize_args(args).encode("utf-8")).hexdigest()


def derive_key(*, scope_id: str, step: str, capability: str, args: dict) -> str:
    material = f"{scope_id}|{step}|{capability}|{normalize_args(args)}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
