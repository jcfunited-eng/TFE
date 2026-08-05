"""Persistence proof for the bounded reading-prediction measurement ledger."""

from dsf_ai_service.substrate import reading_prediction_ledger as rpl


def test_ledger_curve_and_persistence(tmp_path):
    first = rpl.ReadingPredictionLedger(str(tmp_path))
    for _ in range(3):
        first.record(covered=True, hit=True)
    first.record(covered=True, hit=False)
    first.record(covered=False, hit=False)
    with first._lock:
        first._dirty = True
        first._persist_locked(force=True)

    restored = rpl.ReadingPredictionLedger(str(tmp_path))
    day = restored.status()["curve"][-1]
    assert day["attempts"] == 5
    assert day["coverage"] == 0.8
    assert day["accuracy"] == 0.6
    assert day["accuracy_when_covered"] == 0.75
