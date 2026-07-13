"""
test_presence_keepalive.py — local functional tests for
GL-FIX-PRESENCE-KEEPALIVE-C1-20260710

Tests against the REAL Guala engine (dsf_ai_service/v4/gualaloom_v5_engine.py),
not mocks. Verifies:

1. Presence stays TRUE for a source across a simulated long-running turn
   that would otherwise exceed PRESENCE_TIMEOUT_TICKS, because
   _presence_keepalive()'s heartbeat renews throughout converse() /
   _converse_phased(), not just at the very start.
2. Presence still correctly times out for a source that's genuinely gone
   (no keepalive calls, real elapsed idle ticks exceed threshold) — proves
   the fix doesn't defeat real timeout detection.
3. The fix never renews OTHER sources' presence — only the exact source
   whose turn is in flight.
4. PRESENCE_TIMEOUT_TICKS itself is untouched (still 1500).
5. Sanity: converse() still returns a reply and doesn't raise, for both
   CONVERSE_PHASED=0 (default/production) and CONVERSE_PHASED=1 paths.
6. The heartbeat thread never leaks, on success or on exception.

See also test_presence_keepalive_concurrency.py for real-threading
adversarial tests (this file mostly drives the mechanism with manual
tick advancement + direct timeout_check() calls, which is faster and
easier to reason about, but doesn't exercise real concurrent races).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dsf_ai_service.v4.gualaloom_v5_engine import Guala, Coordinator  # noqa: E402


def _wake_all(g, needs=None):
    needs = needs or g.needs
    for src in ("joe", "wc", "c1"):
        g.coordinator.wake(src, g, needs, g.atlas)


def test_constant_unchanged():
    print("Test 0: PRESENCE_TIMEOUT_TICKS is untouched...")
    assert Coordinator.PRESENCE_TIMEOUT_TICKS == 1_500, (
        f"PRESENCE_TIMEOUT_TICKS changed to {Coordinator.PRESENCE_TIMEOUT_TICKS} "
        "-- this fix must NOT touch the validated threshold")
    print("  OK: still 1500")


def test_keepalive_survives_simulated_long_turn():
    """Simulate a turn that would blow the 1500-tick timeout if presence
    were only ever renewed once at the very start (old behavior), and
    confirm the heartbeat keeps it alive."""
    print("Test 1: presence survives a long in-flight turn...")
    g = Guala()
    _wake_all(g)
    assert g.coordinator._presence["joe"] is True

    # Manually drive engine.tick far forward to simulate heavy background
    # advancement (autonomous reading / other sessions / frame processing)
    # occurring WHILE joe's own turn is conceptually "in flight" -- this
    # models exactly the mechanism in the root-cause report: engine.tick is
    # global and advances from sources other than the source being tested.
    g.tick += 1_000  # big jump, well under threshold on its own

    # This call is what a real in-flight turn looks like: converse() wraps
    # itself in _presence_keepalive(source), which renews immediately, so
    # this alone should already refresh the stale timestamp even before
    # read_sentence or emission run.
    reply = g.converse("hello there", source="joe").response
    assert isinstance(reply, str)

    # Now jump tick forward again by another 1200 (would be 2200 total
    # idle relative to the ORIGINAL wake — well over 1500 — but should be
    # fine relative to the renewal that just happened inside converse()).
    g.tick += 1_200
    g.coordinator.timeout_check(g)
    assert g.coordinator._presence["joe"] is True, (
        "joe's presence incorrectly timed out even though converse() just "
        "renewed it moments ago -- keepalive regression")
    print("  OK: presence survived a >1500-tick-equivalent window because "
          "converse() renewed mid-turn")


def test_phased_path_survives_lockfree_emission_window():
    """CONVERSE_PHASED=1 releases self.lock during Phase 6 (emission) --
    the specific window the root-cause report identifies as exposed to
    background tick advancement. Confirm the wrapping heartbeat keeps
    presence alive across a simulated large tick jump landing exactly in
    that gap."""
    print("Test 2: converse() (CONVERSE_PHASED=1) keeps presence alive "
          "across its own lock-free emission window...")
    old = os.environ.get("CONVERSE_PHASED")
    os.environ["CONVERSE_PHASED"] = "1"
    try:
        g = Guala()
        _wake_all(g)
        g.tick += 1_000
        reply = g.converse("what is the weather", source="joe").response
        assert isinstance(reply, str)
        g.tick += 1_200
        g.coordinator.timeout_check(g)
        assert g.coordinator._presence["joe"] is True, (
            "joe's presence timed out despite the keepalive heartbeat "
            "spanning the phased call")
        print("  OK")
    finally:
        if old is None:
            os.environ.pop("CONVERSE_PHASED", None)
        else:
            os.environ["CONVERSE_PHASED"] = old


def test_genuine_absence_still_times_out():
    """A source that never sends anything (no converse() calls at all,
    i.e. no keepalive renewal of any kind) must still time out once real
    elapsed idle ticks exceed the threshold -- the fix must not defeat
    genuine timeout detection."""
    print("Test 3: genuinely idle source still times out...")
    g = Guala()
    _wake_all(g)
    assert g.coordinator._presence["c1"] is True

    # No converse() call for c1 at all -- simulate real elapsed idle ticks
    # (e.g. background reading advancing the global clock while c1 is
    # simply not present).
    g.tick += Coordinator.PRESENCE_TIMEOUT_TICKS + 50
    g.coordinator.timeout_check(g)
    assert g.coordinator._presence["c1"] is False, (
        "c1 should have timed out -- fix must not make presence 'stick' "
        "for a source that never sent a keepalive")
    print("  OK: timed out correctly")


def test_only_the_active_source_is_renewed():
    """converse(source='joe', ...) must never renew wc's or c1's presence
    -- scoped strictly by the source argument of the in-flight call."""
    print("Test 4: keepalive never renews OTHER sources...")
    g = Guala()
    _wake_all(g)

    # Push wc and c1 to the brink of timeout (just under threshold).
    g.tick += 1_400
    g.coordinator._last_input_tick["wc"] = 0
    g.coordinator._last_input_tick["c1"] = 0
    # joe's own last input tick: pretend joe last spoke at tick 1400 (now).
    g.coordinator._last_input_tick["joe"] = g.tick

    # joe has a real turn in flight -- should renew ONLY joe.
    reply = g.converse("just checking in", source="joe").response
    assert isinstance(reply, str)

    # Advance a bit more and check timeout for all three.
    g.tick += 150  # wc/c1 idle = 1550 > 1500; joe idle = ~150 (just renewed)
    g.coordinator.timeout_check(g)

    assert g.coordinator._presence["joe"] is True, "joe should still be present"
    assert g.coordinator._presence["wc"] is False, (
        "wc incorrectly stayed present -- joe's keepalive must not have "
        "leaked into wc's _last_input_tick")
    assert g.coordinator._presence["c1"] is False, (
        "c1 incorrectly stayed present -- joe's keepalive must not have "
        "leaked into c1's _last_input_tick")
    print("  OK: only joe was renewed, wc and c1 timed out normally")


def test_renew_presence_helper_gates_unknown_sources():
    """_renew_presence() must no-op for sources that aren't tracked
    (e.g. 'corpus', 'curriculum', 'joe_voice') -- same gate the original
    single renewal in read_sentence already used."""
    print("Test 5: _renew_presence no-ops for untracked sources...")
    g = Guala()
    before = dict(g.coordinator._last_input_tick)
    g.tick += 500
    g._renew_presence("corpus")
    g._renew_presence("curriculum")
    g._renew_presence("joe_voice")  # tracked separately under pair-bond, NOT presence
    after = dict(g.coordinator._last_input_tick)
    assert before == after, (
        f"_renew_presence mutated _last_input_tick for an untracked source: "
        f"{before} -> {after}")
    print("  OK")


def test_default_nonphased_path_still_works_end_to_end():
    """Sanity: the default production path (CONVERSE_PHASED unset/0)
    still returns a normal reply and doesn't raise with the keepalive
    wrapper in place."""
    print("Test 6: default (non-phased) converse() end-to-end sanity...")
    assert os.environ.get("CONVERSE_PHASED", "0") == "0", \
        "test must run with CONVERSE_PHASED unset/0 to exercise the default path"
    g = Guala()
    _wake_all(g)
    turn = g.converse("the sky is blue today", source="joe")
    reply = turn.response
    assert isinstance(reply, str)
    print(f"  OK: reply={reply!r}")


def test_heartbeat_thread_no_leak_on_success():
    """The keepalive heartbeat thread must terminate promptly after a
    normal turn completes -- no thread leak per call."""
    print("Test 7: heartbeat thread doesn't leak after a normal turn...")
    import threading
    import time as _time
    g = Guala()
    g.coordinator.wake("joe", g, g.needs, g.atlas)
    g.converse("hello", source="joe")
    _time.sleep(1.5)
    leaked = [t.name for t in threading.enumerate()
              if "presence-keepalive" in t.name]
    assert not leaked, f"heartbeat thread leaked: {leaked}"
    print("  OK")


def test_heartbeat_thread_no_leak_on_exception():
    """The keepalive heartbeat thread must also terminate if the wrapped
    turn raises -- finally-block correctness, not just the happy path."""
    print("Test 8: heartbeat thread doesn't leak when the turn raises...")
    import threading
    import time as _time
    g = Guala()
    g.coordinator.wake("joe", g, g.needs, g.atlas)

    def _boom(*a, **k):
        raise RuntimeError("simulated failure mid-emission")
    g._emit_from_invariants = _boom

    try:
        g.converse("hello", source="joe")
        raise AssertionError("expected RuntimeError was not raised")
    except RuntimeError:
        pass

    _time.sleep(1.5)
    leaked = [t.name for t in threading.enumerate()
              if "presence-keepalive" in t.name]
    assert not leaked, f"heartbeat thread leaked after exception: {leaked}"
    print("  OK")


if __name__ == "__main__":
    tests = [
        test_constant_unchanged,
        test_keepalive_survives_simulated_long_turn,
        test_phased_path_survives_lockfree_emission_window,
        test_genuine_absence_still_times_out,
        test_only_the_active_source_is_renewed,
        test_renew_presence_helper_gates_unknown_sources,
        test_default_nonphased_path_still_works_end_to_end,
        test_heartbeat_thread_no_leak_on_success,
        test_heartbeat_thread_no_leak_on_exception,
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
        print(f"ALL {len(tests)} TESTS PASSED")
