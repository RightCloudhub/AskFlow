"""Database-serialized first-result replay within the business transaction."""

from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json

from fastapi.encoders import jsonable_encoder

from sqlalchemy import select

from app.commerce.core.errors import MallError
from app.commerce.core.constants import NAME_SIZE
from app.commerce.core.models import IdempotencyRecord
from app.commerce.core.repository import insert_once
from app.core.config import get_settings
from app.services.agent.gateway.idempotency import args_hash

ENCRYPTED_RESPONSE = "__mall_response_v1"


def encode_response(result):
    from app.commerce.account.crypto import encrypt

    return {ENCRYPTED_RESPONSE: encrypt(json.dumps(jsonable_encoder(result), ensure_ascii=False))}


def decode_response(result):
    from app.commerce.account.crypto import decrypt

    if isinstance(result, dict) and set(result) == {ENCRYPTED_RESPONSE}:
        return json.loads(decrypt(result[ENCRYPTED_RESPONSE]))
    return result


async def execute(db, *, scope: str, key: str, arguments: dict, action):
    if not key or len(key) > NAME_SIZE:
        raise MallError("idempotency_key_required", status=400)
    key_hash, digest = sha256(key.encode()).hexdigest(), args_hash(arguments)
    created = await insert_once(db, IdempotencyRecord, values={
        "scope": scope, "key_hash": key_hash, "request_hash": digest, "status": "pending",
        "expires_at": datetime.now(UTC) + timedelta(seconds=get_settings().mall_idempotency_seconds),
    }, unique=["scope", "key_hash"])
    row = await db.scalar(select(IdempotencyRecord).where(
        IdempotencyRecord.scope == scope, IdempotencyRecord.key_hash == key_hash))
    if row.request_hash != digest:
        raise MallError("idempotency_conflict")
    if not created:
        if row.status != "completed":
            raise MallError("idempotency_in_progress")
        return decode_response(row.response)
    result = await action()
    row.status, row.response, row.http_status = "completed", encode_response(result), 200
    await db.flush()
    return result
