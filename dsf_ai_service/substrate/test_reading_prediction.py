"""Tests for GL-CMD-SYNTAX-ARC-20260718 Piece 1: the reading-prediction meter."""

import os

import pytest

from dsf_ai_service.substrate import reading_prediction_ledger as rpl


def test_ledger_curve_and_persistence(tmp_path):
    a = rpl.ReadingPredictionLedger(str(tmp_path))
    for _ in range(3):
        a.record(covered=True, hit=True)
    a.record(covered=True, hit=False)
    a.record(covered=False, hit=False)
    with a._lock:
        a._dirty = True
        a._persist_locked(force=True)
    b = rpl.ReadingPredictionLedger(str(tmp_path))
    day = b.status()["curve"][-1]
    assert day["attempts"] == 5
    assert day["coverage"] == 0.8
    assert day["accuracy"] == 0.6
    assert day["accuracy_when_covered"] == 0.75


def test_engine_probe_records_measurements(tmp_path, monkeypatch):
    """A real engine reading real sentences with sample=1 must record
    prediction attempts — and reading must be undisturbed."""
    monkeypatch.setenv("READING_PREDICTION_SAMPLE", "1")
    monkeypatch.setenv("STATE_DIR", str(tmp_path))
    monkeypatch.setattr(rpl, "_ledger", None)

    from dsf_ai_service.v4.gualaloom_v5_engine import Guala
    g = Guala()
    g.add_corpus("seed", "Seed", ["the sun rises in the morning"])
    g.load_full_state(str(tmp_path / "state"))
    try:
        # Build the cached composer (probe skips honestly on a cold cache).
        g.read_sentence("the little fish swims in the river", source="corpus")
        g._compose_language_fact_settlement(["the"])
        for _ in range(4):
            g.read_sentence("the little fish swims in the river",
                            source="corpus")
        led = rpl.get_ledger(str(tmp_path))
        day = led.status()["curve"]
        assert day and day[-1]["attempts"] >= 1, \
            "sampled predictions must be recorded"
        # Non-reading sources are never measured.
        before = day[-1]["attempts"]
        g.read_sentence("hello there little fish", source="joe")
        assert led.status()["curve"][-1]["attempts"] == before
    finally:
        try:
            g.shutdown()
        except Exception:
            pass
