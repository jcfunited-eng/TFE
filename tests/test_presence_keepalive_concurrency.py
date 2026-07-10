"""
test_presence_keepalive_concurrency.py — real-threading adversarial test
for GL-FIX-PRESENCE-KEEPALIVE-C1-20260710.

Unlike test_presence_keepalive.py (which manually advances g.tick to
simulate background load, then calls timeout_check() inline), this test
drives ACTUAL concurrent threads against the real engine:

  - A background thread continuously calls g.read_word(source="corpus")
    in a tight loop -- this is the real mechanism (per read_word's own
    body) that (a) advances the global engine.tick by 1 per call and
    (b) every 5 ticks invokes coordinator.regulate() -> timeout_check(),
    exactly like real autonomous/curriculum reading would in production.

  - The foreground thread runs a real converse() call for "joe" (through
    the actual public entry point, CONVERSE_PHASED=1), with
    _emit_from_invariants monkeypatched to sleep (simulating a slow real
    emission under load -- Phase 6 holds self._emission_lock, NOT
    self.lock, so the background thread's self.lock-scoped read_word
    calls are free to race ahead exactly as in production).

This reproduces the actual failure mode end-to-end with real threads,
real locks, and the real timeout_check() call path -- not just arithmetic
on g.tick.

HISTORY: an earlier version of the fix (phase-boundary renewal calls
instead of a continuous heartbeat) FAILED this exact test -- joe's
presence timed out at tick 1535 (idle_ticks=1504) because the 6s
monkeypatched emission sleep alone generated ~1500 ticks of background
pressure before the phase-boundary renewal following it ever ran. That
result is why the shipped fix uses a 0.5s-interval heartbeat thread
spanning the whole call instead of renewing only at phase boundaries.
"""

import os
import sys
import time
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dsf_ai_service.v4.gualaloom_v5_engine import Guala, Coordinator  # noqa: E402


def test_concurrent_background_load_does_not_time_out_active_source():
    print("Concurrency test: real background thread racing tick forward "
          "during joe's real in-flight converse() call (CONVERSE_PHASED=1, "
          "going through the real public entry point, not calling "
          "_converse_phased directly)...")

    old_phased = os.environ.get("CONVERSE_PHASED")
    os.environ["CONVERSE_PHASED"] = "1"

    g = Guala()
    for src in ("joe", "wc", "c1"):
        g.coordinator.wake(src, g, g.needs, g.atlas)

    stop_flag = threading.Event()
    bg_errors = []

    def _background_reader():
        i = 0
        while not stop_flag.is_set():
            try:
                g.read_word(f"bgword{i % 20}", source="corpus")
            except Exception as e:
                bg_errors.append(e)
                return
            i += 1

    bg_thread = threading.Thread(target=_background_reader, daemon=True)

    # Monkeypatch _emit_from_invariants to simulate a slow real emission
    # (Phase 6 in _converse_phased holds self._emission_lock, not
    # self.lock -- self.lock is free during this window in production).
    orig_emit = g._emit_from_invariants
    SLEEP_S = 6.0

    def _slow_emit(*args, **kwargs):
        time.sleep(SLEEP_S)
        return orig_emit(*args, **kwargs)

    g._emit_from_invariants = _slow_emit

    bg_thread.start()
    t0 = time.monotonic()
    try:
        reply = g.converse("tell me something", source="joe")
    finally:
        stop_flag.set()
        bg_thread.join(timeout=5)
        g._emit_from_invariants = orig_emit
        if old_phased is None:
            os.environ.pop("CONVERSE_PHASED", None)
        else:
            os.environ["CONVERSE_PHASED"] = old_phased

    elapsed = time.monotonic() - t0
    assert not bg_errors, f"background reader raised: {bg_errors}"
    assert isinstance(reply, str)
    print(f"  turn took {elapsed:.2f}s wall-clock, engine.tick now {g.tick} "
          f"(threshold is {Coordinator.PRESENCE_TIMEOUT_TICKS})")

    # The whole point: background activity should have raced tick well
    # past the timeout threshold DURING joe's own single in-flight turn.
    assert g.tick > Coordinator.PRESENCE_TIMEOUT_TICKS, (
        "test didn't generate enough background tick pressure to be a "
        "meaningful adversarial check -- inconclusive, not a pass")

    # Explicitly run one more timeout_check pass after the turn completes,
    # exactly like the background thread's own read_word calls would have
    # been doing throughout (every 5 ticks) via coordinator.regulate().
    g.coordinator.timeout_check(g)

    assert g.coordinator._presence["joe"] is True, (
        "REGRESSION: joe's presence was incorrectly timed out during his "
        "own real, still-in-flight turn, despite background tick pressure "
        f"({g.tick} ticks, threshold {Coordinator.PRESENCE_TIMEOUT_TICKS}) "
        "-- the keepalive fix did not hold under real concurrency")
    print("  OK: joe's presence survived real concurrent background load "
          "exceeding the timeout threshold during his own turn")


def test_concurrent_background_load_still_times_out_truly_absent_source():
    """Same real-threading background pressure, but this time NOBODY is
    having an active turn -- wc should still time out for real, proving
    the fix doesn't globally suppress timeout detection."""
    print("Concurrency test: genuinely absent source still times out under "
          "the same real background load...")
    g = Guala()
    for src in ("joe", "wc", "c1"):
        g.coordinator.wake(src, g, g.needs, g.atlas)

    stop_flag = threading.Event()
    bg_errors = []

    def _background_reader():
        i = 0
        while not stop_flag.is_set():
            try:
                g.read_word(f"bgword{i % 20}", source="corpus")
            except Exception as e:
                bg_errors.append(e)
                return
            i += 1
            if i > 3000:
                return

    bg_thread = threading.Thread(target=_background_reader, daemon=True)
    bg_thread.start()
    bg_thread.join(timeout=30)
    stop_flag.set()

    assert not bg_errors, f"background reader raised: {bg_errors}"
    assert g.tick > Coordinator.PRESENCE_TIMEOUT_TICKS, (
        f"background pressure insufficient: tick={g.tick}")

    g.coordinator.timeout_check(g)
    assert g.coordinator._presence["wc"] is False, (
        "wc should have timed out -- nobody renewed wc's presence and "
        "real background load pushed well past the threshold")
    assert g.coordinator._presence["joe"] is False
    assert g.coordinator._presence["c1"] is False
    print(f"  OK: all three timed out correctly under real background load "
          f"(tick={g.tick}) with no in-flight turns to protect them")


def test_default_path_survives_long_wait_for_lock():
    """CONVERSE_PHASED=0 (the actual current production default): a real
    turn can be blocked for a long time just WAITING to acquire self.lock
    before read_sentence ever starts (documented live: camera/mic frame
    calls holding it 12-48s, one case ~93s). Confirm the heartbeat's
    immediate synchronous renewal + periodic renewals-while-blocked keep
    joe's presence alive through that wait, using the real self.lock and
    a real second thread holding it -- not a simulated delay inside
    converse() itself."""
    print("Concurrency test: default (non-phased) path survives a long "
          "real wait for self.lock held by another thread...")
    assert os.environ.get("CONVERSE_PHASED", "0") == "0"

    g = Guala()
    for src in ("joe", "wc", "c1"):
        g.coordinator.wake(src, g, g.needs, g.atlas)

    HOLD_S = 4.0
    lock_acquired = threading.Event()

    def _hold_lock():
        with g.lock:
            lock_acquired.set()
            time.sleep(HOLD_S)

    holder = threading.Thread(target=_hold_lock, daemon=True)
    holder.start()
    lock_acquired.wait(timeout=5)

    # Push joe's presence right to the edge of the timeout the instant
    # before he tries to speak, simulating a genuinely stale prior
    # checkpoint (worst case for the wait).
    g.coordinator._last_input_tick["joe"] = g.tick

    t0 = time.monotonic()
    reply = g.converse("hello, are you there", source="joe")
    elapsed = time.monotonic() - t0
    holder.join(timeout=5)

    assert isinstance(reply, str)
    assert elapsed >= HOLD_S * 0.9, (
        f"test didn't actually wait on the lock (elapsed={elapsed:.2f}s) "
        "-- inconclusive")

    g.coordinator.timeout_check(g)
    assert g.coordinator._presence["joe"] is True, (
        "REGRESSION: joe timed out while genuinely blocked waiting for "
        "self.lock held by another real thread -- the heartbeat's "
        "immediate + while-blocked renewals did not hold")
    print(f"  OK: joe's presence survived a real {elapsed:.2f}s wait for "
          f"a lock held by another thread")


if __name__ == "__main__":
    tests = [
        test_concurrent_background_load_does_not_time_out_active_source,
        test_concurrent_background_load_still_times_out_truly_absent_source,
        test_default_path_survives_long_wait_for_lock,
    ]
    failures = []
    for t in tests:
        try:
            t()
        except Exception as e:
            import traceback
            traceback.print_exc()
            failures.append((t.__name__, str(e)))
    print("\n" + "=" * 60)
    if failures:
        print(f"FAILED: {len(failures)}/{len(tests)}")
        for name, err in failures:
            print(f"  - {name}: {err}")
        sys.exit(1)
    else:
        print(f"ALL {len(tests)} CONCURRENCY TESTS PASSED")
