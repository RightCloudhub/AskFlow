"""Topups credit only after authoritative payment settlement."""

from http import HTTPStatus

from app.commerce.core.errors import MallError
from app.commerce.core.repository import cas, owned
from app.commerce.core.services import service
from app.commerce.wallet.operations_models import Topup
from app.commerce.wallet.service import WalletService
from app.core.config import get_settings


async def create(db, user_id: str, *, amount_cents: int, key: str):
    if not get_settings().mall_payment_mock_enabled:
        raise MallError("payment_gateway_unavailable", status=HTTPStatus.SERVICE_UNAVAILABLE)
    row = Topup(user_id=user_id, amount_cents=amount_cents,
                currency=get_settings().mall_currency, request_key=key, status="pending")
    db.add(row)
    await db.flush()
    payment = await service("payment", db).start_topup(user_id, {
        "id": row.id, "amount_cents": row.amount_cents, "currency": row.currency})
    row.payment_id = payment["id"]
    return {"id": row.id, "payment": payment, "status": row.status}


async def complete(db, user_id: str, *, topup_id: str, payment_id: str):
    row = await owned(db, Topup, owner_id=user_id, resource_id=topup_id, lock=True)
    if row.payment_id != payment_id:
        raise MallError("topup_payment_mismatch")
    if row.status == "succeeded":
        return
    await WalletService(db).credit(user_id, row.amount_cents, key="topup:" + row.id)
    await cas(db, row, values={"status": "succeeded"})
