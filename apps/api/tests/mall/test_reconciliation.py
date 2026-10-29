"""Provider refund mismatches and callback/provider disagreement are detected."""

from types import SimpleNamespace

from app.commerce.payment.refund_reconciliation import compare


def test_extra_gateway_refund_is_detected():
    payment = SimpleNamespace(id="payment", status="partially_refunded", refunded_cents=100, external_cents=1000)
    receipts = [{"id": "refund", "provider_ref": "expected", "external_cents": 100, "amount_cents": 100}]
    provider = [SimpleNamespace(id=identifier, amount_cents=100, status="succeeded", kind="refund")
                for identifier in ("expected", "unexpected")]
    differences = list(compare(payment, receipts=receipts, provider=provider))
    assert len(differences) == 1
    assert differences[0]["entity"] == "unexpected"


def test_wallet_destination_needs_no_external_refund():
    payment = SimpleNamespace(id="payment", status="refunded", refunded_cents=100, external_cents=100)
    receipts = [{"id": "refund", "provider_ref": "", "external_cents": 0, "amount_cents": 100}]
    assert list(compare(payment, receipts=receipts, provider=[])) == []
