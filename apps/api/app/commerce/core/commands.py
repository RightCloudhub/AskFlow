"""One transaction for a write, its audit and its first response."""

from app.commerce.core.audit import audit
from app.commerce.core.idempotency import execute

SENSITIVE = ("password", "token", "secret", "code", "cipher", "cookie", "payer")


def safe_detail(value):
    if isinstance(value, dict):
        return {key: "[redacted]" if any(word in key.lower() for word in SENSITIVE)
                else safe_detail(item) for key, item in value.items()}
    if isinstance(value, list):
        return [safe_detail(item) for item in value]
    return value


async def command(ctx, name: str, *, payload, action):
    arguments = payload.model_dump(mode="json") if hasattr(payload, "model_dump") else payload

    async def perform():
        result = await action()
        await audit(ctx.db, actor_id=ctx.user.id, action=name,
                    detail=safe_detail({"request": arguments, "result": result}))
        return result

    return await execute(ctx.db, scope=name + ":" + ctx.user.id, key=ctx.key,
                         arguments=arguments, action=perform)
