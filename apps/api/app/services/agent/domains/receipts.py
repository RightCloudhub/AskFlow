"""Create expiring receipts from application-owned connector results."""

from datetime import UTC, datetime, timedelta

from app.services.agent.service.contracts import Evidence, OperationCall, Receipt

EVIDENCE_TTL_SECONDS = 60


def receipt_for(call: OperationCall, data: dict, *, source: str) -> Receipt:
    if data.get("status") == "mock" or data.get("data_source") == "mock":
        return Receipt(status="mock", error_kind="simulated")
    return Receipt(
        status="succeeded",
        evidence=Evidence(
            operation_id=call.operation_id,
            source=source,
            data=data,
            expires_at=datetime.now(UTC) + timedelta(seconds=EVIDENCE_TTL_SECONDS),
        ),
    )


def connector_receipt(call: OperationCall, data: dict, *, source: str) -> Receipt:
    if data.get("status") not in {"ok", "mock"}:
        return Receipt(status="failed", error_kind="permanent", error="connector_rejected")
    return receipt_for(call, data, source=source)
