"""
test_curiosity_ledger_gate_step4.py — GL-SPC-DRIVE-PHYSICS-SUBSTRATE-
TRUE-20260718-v1 Step 4: the emission gate's derivative branch runs on
the reading-prediction ledger's accuracy curve, not needs.novelty.

Gates:
1. Cold start honest: fewer than LPROG_MIN_DAYS recorded days keeps the
   branch closed no matter how favorable the needs state is.
2. Genuine learning progress (2-day mean rise >= LPROG_RISE_MIN inside
   the inverted-U band) opens the branch.
3. A flat or declining curve keeps it closed.
4. The inverted-U band holds on the accuracy axis: mastered (high) and
   no-gap/unlearnable (low) both keep it closed even when rising.
5. needs.novelty no longer drives the branch (a strong novelty rise
   with an insufficient ledger changes nothing).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dsf_ai_service.substrate.reading_prediction_ledger as rpl
from dsf_ai_service.v4.gualaloom_v5_engine import Guala


class _StubLedger:
    def __init__(self, accs):
        self._accs = accs

    def status(self):
        return {"curve": [
            {"day": f"2026-07-{10 + i:02d}", "attempts": 5000,
             "coverage": 0.5, "accuracy": a / 2,
             "accuracy_when_covered": a}
            for i, a in enumerate(self._accs)]}


def _gate_ready_engine():
    """Engine in a state where every co-gate of the derivative branch is
    open and the other two urgency branches are closed."""
    g = Guala()
    g.tick = 1_000_000
    g.last_autonomous_emission_tick = -1_000_000
    g._last_converse_tick = -1_000_000
    g._current_activity = None
    g.coordinator._presence["joe"] = True
    g.coordinator._pair_bond["joe"] = True
    g.needs.dream_pressure = 0.0          # branch A closed
    g.needs.connection = 0.65             # branch B closed (<= 0.70)
    g.needs.stability = 1.0               # stability_ok, feeds arousal
    g.needs.novelty = 1.0                 # feeds arousal, valence >= 0
    return g


def _with_curve(monkey_accs, g):
    g._lprog_cache = None      # the gate caches per 1000 ticks; force a re-read
    real = rpl.get_ledger
    rpl.get_ledger = lambda state_dir=None: _StubLedger(monkey_accs)
    try:
        return g._should_attempt_autonomous_emission()
    finally:
        rpl.get_ledger = real


def test_gate1_cold_start_closed():
    print("Gate 1: cold start...")
    g = _gate_ready_engine()
    assert _with_curve([0.30, 0.40, 0.50], g) is False, \
        "3 recorded days must keep the branch closed"
    print("  PASS: closed below LPROG_MIN_DAYS")


def test_gate2_genuine_rise_opens():
    print("Gate 2: genuine rise...")
    g = _gate_ready_engine()
    assert _with_curve([0.30, 0.32, 0.40, 0.44], g) is True, \
        "recent 0.42 vs prior 0.31 inside the band must open the branch"
    print("  PASS: opens on real learning progress")


def test_gate3_flat_or_decline_closed():
    print("Gate 3: flat/decline...")
    g = _gate_ready_engine()
    assert _with_curve([0.40, 0.40, 0.40, 0.40], g) is False, \
        "flat curve must keep the branch closed"
    assert _with_curve([0.50, 0.48, 0.40, 0.38], g) is False, \
        "declining curve must keep the branch closed"
    print("  PASS: flat and declining both closed")


def test_gate4_inverted_u_band():
    print("Gate 4: inverted-U band...")
    g = _gate_ready_engine()
    assert _with_curve([0.80, 0.85, 0.92, 0.95], g) is False, \
        "mastered (recent mean >= 0.90) must keep the branch closed"
    assert _with_curve([0.02, 0.04, 0.10, 0.13], g) is False, \
        "no-gap/unlearnable (recent mean <= 0.15) must stay closed"
    print("  PASS: both extremes closed despite rising accuracy")


def test_gate5_novelty_no_longer_drives():
    print("Gate 5: novelty decoupled...")
    g = _gate_ready_engine()
    # Simulate the strongest possible novelty rise the old mechanism
    # would have seen; the ledger is insufficient, so nothing may open.
    g.needs.novelty = 0.2
    first = _with_curve([0.40], g)
    g.needs.novelty = 1.0
    second = _with_curve([0.40], g)
    assert first is False and second is False, \
        "needs.novelty movement must no longer open the derivative branch"
    print("  PASS: novelty level/rate is decoupled from the gate")


if __name__ == "__main__":
    test_gate1_cold_start_closed()
    test_gate2_genuine_rise_opens()
    test_gate3_flat_or_decline_closed()
    test_gate4_inverted_u_band()
    test_gate5_novelty_no_longer_drives()
    print("\nAll Step-4 gates pass.")
