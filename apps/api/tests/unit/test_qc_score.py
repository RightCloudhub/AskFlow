"""QC scoring unit tests."""

from types import SimpleNamespace

from app.services.qc.service import QcService


def test_score_refused_and_weak_flags():
    svc = QcService.__new__(QcService)
    ok = SimpleNamespace(refused=False, flags=[])
    assert svc.score_run(ok) == 100
    refused = SimpleNamespace(refused=True, flags=[])
    assert svc.score_run(refused) == 70
    weak = SimpleNamespace(refused=False, flags=["weak_evidence", "oos"])
    # 100 - 15 - 15
    assert svc.score_run(weak) == 70
