"""GL-CMD-CAMERA-TURN-LATENCY — real tests for the live priority gate.

  A live human interaction (a converse
     turn, or a real sight/sound frame) marks itself pending so the
     background self.lock hogs (the autonomous emission loop and the 5Hz
     autonomy tick) DEFER their self.lock acquisition and let the live work
     win the lock first for the complete balanced causal interaction scope.

These are real tests against the real engine: real Guala() instances, the
real threading.RLock self.lock, the real module-level backpressure gate
(_frame_backpressure_acquire / _frame_inflight / _frame_dropped) and real
threads. The only things stubbed are UNRELATED collaborators (the heavy
six-section converse() and its bind/remember tail) when a test needs to
isolate the sight-routing decision -- never the locking or backpressure
mechanism itself. Same convention as
tests/test_read_sentence_lock_granularity_concurrency.py.
"""

import os
import sys
import threading
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dsf_ai_service.app as appmod  # noqa: E402
from dsf_ai_service.v4.gualaloom_v5_engine import Guala  # noqa: E402


@pytest.fixture
def clean_frame_state():
    """Snapshot + restore the module-level backpressure counters and _guala."""
    saved_inflight = dict(appmod._frame_inflight)
    saved_dropped = dict(appmod._frame_dropped)
    saved_guala = appmod._guala
    appmod._frame_inflight["sight"] = 0
    appmod._frame_inflight["sound"] = 0
    appmod._frame_dropped["sight"] = 0
    appmod._frame_dropped["sound"] = 0
    try:
        yield
    finally:
        appmod._frame_inflight.clear()
        appmod._frame_inflight.update(saved_inflight)
        appmod._frame_dropped.clear()
        appmod._frame_dropped.update(saved_dropped)
        appmod._guala = saved_guala


# ── live-interaction priority gate ─────────────────────────────────────────

def test_defer_toggles_with_pending_and_clears():
    """Unit-level: a background site defers only while an interaction is
    pending, and proceeds again the moment it clears (background eventually
    runs -- no permanent skip)."""
    g = Guala()
    assert g._defer_for_live_interaction("bg") is False  # nothing pending
    g._enter_live_interaction()
    assert g._live_interaction_pending == 1
    assert g._defer_for_live_interaction("bg") is True   # defer while pending
    g._exit_live_interaction()
    assert g._live_interaction_pending == 0
    assert g._defer_for_live_interaction("bg") is False  # resumes after clear


def test_gate_also_defers_on_preexisting_live_converse_pending():
    """The self.lock deferral gate mirrors/extends the pre-existing
    _live_converse_pending counter (which engine converse() self-increments):
    a converse turn already counted there -- even one that never went through
    the app-level scope -- must make the background sites defer, and the gate
    must resume when it clears. We only READ that counter here; we never
    mutate its underflow-checked write path."""
    g = Guala()
    assert g._defer_for_live_interaction("bg") is False
    # Simulate exactly what converse() does at line ~5120.
    with g._live_converse_state_lock:
        g._live_converse_pending += 1
    try:
        assert g._defer_for_live_interaction("bg") is True
    finally:
        with g._live_converse_state_lock:
            g._live_converse_pending -= 1
    assert g._defer_for_live_interaction("bg") is False


def test_counter_supports_overlapping_interactions():
    """The gate is a counter, not a boolean: overlapping live interactions
    (a turn plus concurrent frames) must both be released before background
    resumes."""
    g = Guala()
    g._enter_live_interaction()
    g._enter_live_interaction()
    assert g._live_interaction_pending == 2
    assert g._defer_for_live_interaction("bg") is True
    g._exit_live_interaction()
    assert g._defer_for_live_interaction("bg") is True   # still one pending
    g._exit_live_interaction()
    assert g._defer_for_live_interaction("bg") is False
    # over-release can never drive it negative / permanently suppress deferral
    g._exit_live_interaction()
    assert g._live_interaction_pending == 0


def test_live_interaction_scope_clears_on_exception(clean_frame_state):
    """try/finally correctness: the flag is released even if the live
    interaction's processing raises."""
    g = Guala()
    appmod._guala = g
    with pytest.raises(RuntimeError):
        with appmod._live_interaction_scope():
            assert g._live_interaction_pending == 1
            raise RuntimeError("boom during turn")
    assert g._live_interaction_pending == 0, "flag cleared despite exception"


def test_live_interaction_scope_is_noop_without_guala(clean_frame_state):
    """Remote mode / not-ready: no in-process _guala -> scope is a safe no-op
    and never raises."""
    appmod._guala = None
    with appmod._live_interaction_scope():
        pass  # must not raise


def test_causal_scope_remains_authoritative_beyond_former_timer():
    """Elapsed wall time cannot let background work split one interaction."""
    g = Guala()
    g._enter_live_interaction()
    try:
        assert g._defer_for_live_interaction("tick") is True
        time.sleep(2.05)
        assert g._defer_for_live_interaction("tick") is True
    finally:
        g._exit_live_interaction()
    assert g._defer_for_live_interaction("tick") is False


def test_real_thread_background_defers_then_resumes():
    """Real threads, real self.lock: a background loop that respects the gate
    STOPS acquiring the lock while a live interaction is pending, then RESUMES
    once it clears -- proving genuine deferral + no permanent starvation."""
    g = Guala()
    stop = threading.Event()
    acquisitions = []
    lock_for_list = threading.Lock()

    def background():
        while not stop.is_set():
            if g._defer_for_live_interaction("tick"):
                time.sleep(0.005)
                continue
            with g.lock:
                with lock_for_list:
                    acquisitions.append(time.monotonic())
                time.sleep(0.01)  # a real (short) held-lock work chunk
            time.sleep(0.005)

    t = threading.Thread(target=background, daemon=True)
    t.start()
    try:
        time.sleep(0.1)  # let it acquire freely a few times
        with lock_for_list:
            before = len(acquisitions)
        assert before > 0, "background acquires the lock when nothing pending"

        g._enter_live_interaction()
        mark = time.monotonic()
        time.sleep(0.1)  # observe the pending window
        with lock_for_list:
            during = [t_ for t_ in acquisitions if t_ >= mark]
        assert during == [], "background does NOT acquire the lock while pending"

        g._exit_live_interaction()
        time.sleep(0.1)  # let it resume
        with lock_for_list:
            after = len(acquisitions)
        assert after > before, "background RESUMES acquiring once pending clears"
    finally:
        stop.set()
        t.join(timeout=2)


def test_live_turn_wait_is_bounded_by_the_gate():
    """Timing proof (test d): a background loop modeling the autonomy tick
    (repeatedly grabbing self.lock, unfair RLock re-acquisition) would
    normally make a live turn wait through many hold cycles. With the gate,
    once the turn marks itself pending the background stops re-acquiring, so
    the live turn wins the lock after at most the one in-progress hold.

    We measure the live turn's real wait and assert it is bounded by roughly a
    single hold, and that the background made ZERO acquisitions during the
    wait (the deterministic mechanism proof)."""
    g = Guala()
    HOLD = 0.05
    stop = threading.Event()
    acq_times = []
    acq_lock = threading.Lock()

    def background_tick_loop():
        # Models start_autonomy_loop: tick calls _defer_for_live_interaction
        # at its top (real gate), only taking self.lock when not deferring.
        while not stop.is_set():
            if g._defer_for_live_interaction("autonomy_tick"):
                time.sleep(0.002)
                continue
            with g.lock:
                with acq_lock:
                    acq_times.append(time.monotonic())
                time.sleep(HOLD)  # real long-ish hold, like an EMITTING tick
            # tight re-loop (the unfair-RLock hazard) -- no sleep here

    t = threading.Thread(target=background_tick_loop, daemon=True)
    t.start()
    try:
        time.sleep(0.15)  # background is churning, grabbing the lock in a loop
        with acq_lock:
            n_before = len(acq_times)
        assert n_before >= 1

        # A live turn arrives: mark pending, then wait for the lock.
        g._enter_live_interaction()
        mark = time.monotonic()
        got = g.lock.acquire(timeout=2.0)
        waited = time.monotonic() - mark
        try:
            assert got, "live turn eventually acquires the lock"
            # bounded by ~one in-progress hold, not many cycles:
            assert waited < HOLD * 3, (
                f"live-turn wait {waited:.3f}s should be bounded by ~one hold "
                f"({HOLD}s), not many background cycles")
            with acq_lock:
                acquired_during_wait = [x for x in acq_times if x >= mark]
            assert acquired_during_wait == [], (
                "background made ZERO new lock acquisitions while the live "
                "turn was pending -- it deferred instead of racing")
        finally:
            if got:
                g.lock.release()
            g._exit_live_interaction()
    finally:
        stop.set()
        t.join(timeout=2)
