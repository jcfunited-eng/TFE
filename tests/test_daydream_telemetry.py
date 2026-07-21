"""
Telemetry tests for the dormant legacy periodic-daydream implementation.

Proves:
  - daydream self.lock waits are recorded into a bounded window from the
    real _daydream_tick path;
  - lock-wait p95 above 50ms raises a loud daydream_telemetry_alert;
  - tick_rate dropping >30% below the daydream-enabled baseline raises a
    loud daydream_telemetry_alert;
  - healthy numbers raise nothing (no alert spam).

Production boot-disable is covered in tests/test_daydream_loop_reconnect.py.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SUBSTRATE_MODE", "embedded")

from dsf_ai_service.v4.gualaloom_v5_engine import Guala  # noqa: E402


def _alerts(g):
    return [ev for ev in g._substrate_events
            if ev.kind == "daydream_telemetry_alert"]


def test_daydream_tick_records_real_lock_waits():
    g = Guala()
    try:
        # Give the tick something to snapshot so it passes Phase 1.
        g.read_sentence("sun rises early", source="test")
        before = len(getattr(g, '_daydream_lock_wait_ms', ()) or ())
        g._daydream_tick()
        after = len(getattr(g, '_daydream_lock_wait_ms', ()) or ())
        assert after > before, (
            "a real _daydream_tick recorded no lock-wait samples -- the "
            "telemetry is not measuring where the contention happens")
        print("test_daydream_tick_records_real_lock_waits: PASS "
              f"({after - before} waits recorded)")
    finally:
        g.shutdown()


def test_lock_wait_p95_breach_alerts_loudly():
    g = Guala()
    try:
        for _ in range(100):
            g._daydream_note_lock_wait(60.0)  # p95 = 60ms > 50ms threshold
        g._daydream_telemetry_check()
        alerts = _alerts(g)
        assert alerts, "50ms p95 breach raised no daydream_telemetry_alert"
        assert alerts[-1].detail["reason"] == "lock_wait_p95"
        assert alerts[-1].detail["p95_ms"] > 50.0
        print("test_lock_wait_p95_breach_alerts_loudly: PASS")
    finally:
        g.shutdown()


def test_tick_rate_drop_alerts_loudly():
    g = Guala()
    try:
        g._daydream_tick_rate_baseline = 10.0
        g._daydream_tick_rate_samples = []
        g.get_tick_rate = lambda: 5.0  # 50% drop > 30% threshold
        g._daydream_telemetry_check()
        alerts = [a for a in _alerts(g)
                  if a.detail.get("reason") == "tick_rate_drop"]
        assert alerts, ">30% tick_rate drop raised no alert"
        assert alerts[-1].detail["baseline"] == 10.0
        assert alerts[-1].detail["tick_rate"] == 5.0
        print("test_tick_rate_drop_alerts_loudly: PASS")
    finally:
        g.shutdown()


def test_healthy_telemetry_stays_quiet():
    g = Guala()
    try:
        for _ in range(100):
            g._daydream_note_lock_wait(2.0)  # healthy
        g._daydream_tick_rate_baseline = 10.0
        g._daydream_tick_rate_samples = []
        g.get_tick_rate = lambda: 9.5  # 5% dip, within tolerance
        g._daydream_telemetry_check()
        assert not _alerts(g), (
            f"healthy telemetry produced alerts: "
            f"{[a.detail for a in _alerts(g)]} -- alert spam would train "
            "operators to ignore the real one")
        print("test_healthy_telemetry_stays_quiet: PASS")
    finally:
        g.shutdown()


if __name__ == "__main__":
    test_daydream_tick_records_real_lock_waits()
    test_lock_wait_p95_breach_alerts_loudly()
    test_tick_rate_drop_alerts_loudly()
    test_healthy_telemetry_stays_quiet()
    print("ALL PASS: test_daydream_telemetry")
