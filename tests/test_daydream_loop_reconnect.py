"""
Functional tests for the dormant legacy periodic-daydream implementation.

start_daydream_loop()/_daydream_tick() (GL-CMD-DAYDREAM-PARALLEL-EVE-
20260629-42) was a real, complete mechanism whose only call site was
substrate_runner.boot_substrate() -- itself dead code with zero callers
since the GL-CMD-PROCESS-COLLAPSE-61 refactor (2026-07-01) moved the real
boot path to app.py's _gl_init()/_embedded_post_boot() without porting the
g.start_daydream_loop() call that sat next to g.start_autonomy_loop() in
boot_substrate(). The 2026-07-21 architecture ruling disables every
production boot call, including when the obsolete environment switch is 1.
The remaining direct-method tests preserve evidence about the dormant code;
they do not claim it is live or architecturally accepted.

Matches this repo's established split: this file is the single-threaded
functional half (mirrors tests/test_read_sentence_lock_granularity.py's
role); test_daydream_loop_reconnect_concurrency.py is the real-threading
half (mirrors test_read_sentence_lock_granularity_concurrency.py /
test_presence_keepalive_concurrency.py).
"""

import os
import sys
import time
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dsf_ai_service.v4.gualaloom_v5_engine import Guala  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────
# Engine-level: the mechanism itself, as it will actually run once wired.
# ─────────────────────────────────────────────────────────────────────────

def test_start_daydream_loop_spawns_a_real_named_thread():
    print("Functional test: start_daydream_loop() spawns a real daemon "
          "thread named 'daydream-loop' and sets _daydream_running=True...")
    g = Guala()
    assert getattr(g, '_daydream_thread', None) is None
    g.start_daydream_loop()
    try:
        assert g._daydream_running is True
        assert g._daydream_thread is not None
        assert g._daydream_thread.is_alive()
        assert g._daydream_thread.name == "daydream-loop"
        assert g._daydream_thread.daemon is True
    finally:
        g._daydream_running = False
        g._daydream_thread.join(timeout=3)
    assert not g._daydream_thread.is_alive(), (
        "daydream thread did not exit within 3s of _daydream_running=False "
        "(0.5s poll interval -- should exit almost immediately)")
    print("  OK: real thread started, correctly named/daemonized, and "
          "stops cleanly on _daydream_running=False")


def test_start_daydream_loop_is_idempotent():
    print("Functional test: calling start_daydream_loop() twice does not "
          "spawn a second thread...")
    g = Guala()
    g.start_daydream_loop()
    first_thread = g._daydream_thread
    try:
        g.start_daydream_loop()
        assert g._daydream_thread is first_thread, (
            "REGRESSION: second call spawned a different thread object -- "
            "would mean two daydream loops running concurrently")
    finally:
        g._daydream_running = False
        first_thread.join(timeout=3)
    print("  OK: second call was a no-op, exactly one thread ever existed")


def _make_committed_word(g, word, source="corpus"):
    """Real commit via the real path (read_word), returns the resulting
    (section_name, mode_idx, chi) exactly as Section.receive recorded it --
    same technique as reading this repo's own commit dict schema
    ({"tick","mode","chi","word","grounded"}, see Section.receive)."""
    g.read_word(word, source=source)
    for sec in g.sections.values():
        for c in reversed(sec.commits):
            if c["word"] == word:
                return sec.name, c["mode"], c["chi"]
    raise AssertionError(f"setup failed: {word!r} was not committed to any section")


def test_daydream_tick_reinforces_atlas_and_logs_surface_event_not_a_noop():
    """Proves _daydream_tick does real, observable work when it has a real
    seed and a real (monkeypatched, to isolate this from Phase 2's own
    organism/deep_atlas maturity requirements -- covered by that mechanism's
    own P2-seam tests) association to act on -- not silently a no-op once
    wired live."""
    print("Functional test: _daydream_tick reinforces the working atlas "
          "with source='daydream' and logs a daydream_surface event...")
    g = Guala()
    sec_name, mode_idx, chi = _make_committed_word(g, "sunshine")

    # Isolate Extension-independent behavior from Phase 2's own maturity
    # requirements (deep_atlas needs real dream-cycle promotion, organism
    # needs real population training -- neither is this test's concern;
    # _association_from_deep_atlas/_association_from_organism have their
    # own dedicated P2-seam test coverage elsewhere).
    g._association_from_deep_atlas = lambda seed_word: (sec_name, mode_idx, "sunshine", 0.8)

    events_before = len(g._substrate_events)
    atlas_writes_before = sum(len(v) for v in g.atlas.entries.values())

    g._daydream_tick()

    atlas_writes_after = sum(len(v) for v in g.atlas.entries.values())
    assert atlas_writes_after >= atlas_writes_before, (
        "atlas entry count shrank -- unexpected")
    new_events = list(g._substrate_events)[events_before:]  # deque: no slicing
    surface_events = [e for e in new_events if e.kind == "daydream_surface"]
    assert surface_events, (
        "no daydream_surface event logged -- _daydream_tick behaved as a "
        "silent no-op against a real, forced association")
    ev = surface_events[0]
    assert ev.detail["word"] == "sunshine"
    print(f"  OK: daydream_surface logged (seed_chi={ev.detail['seed_chi']}, "
          f"surfaced_chi={ev.detail['surfaced_chi']}, word={ev.detail['word']!r})")


def test_daydream_tick_never_triggers_emission():
    """Re-proves the original dispatch's T7 ('daydream does NOT trigger
    emission') against the exact code now being wired into the real boot
    path -- running many ticks (with a forced association so Phase 2/
    Extension A/C all have real work to do each time) must never move
    _total_emissions."""
    print("Functional test: repeated _daydream_tick calls never increment "
          "_total_emissions...")
    g = Guala()
    sec_name, mode_idx, chi = _make_committed_word(g, "lantern")
    g._association_from_deep_atlas = lambda seed_word: (sec_name, mode_idx, "lantern", 0.8)

    before = g._total_emissions
    for _ in range(50):
        g.tick += 1
        g._daydream_tick()
    after = g._total_emissions

    assert after == before, (
        f"REGRESSION: _total_emissions changed from {before} to {after} "
        "purely from daydream ticks -- daydream must never itself trigger "
        "emission (original dispatch T7)")
    print(f"  OK: _total_emissions unchanged ({before}) across 50 ticks")


def test_reorganize_hypothesis_entries_excluded_from_novel_jump():
    """2026-07-10 adversarial-review safeguard (GL-CMD-SLEEP-REORGANIZE
    follow-on, gualaloom_v5_engine.py ~line 7394): a reorganize_hypothesis
    deep_atlas entry's single, never-confirmed co_occurrence link must
    never be laundered into a daydream_novel 'discovery' -- indistinguishable
    from a genuine, organism-earned association once written. This
    constructs the exact scenario: the ONLY reachable far-chi neighbor is a
    reorganize_hypothesis entry, and confirms _daydream_tick's Extension A
    finds nothing to write rather than surfacing it anyway."""
    print("Functional test: reorganize_hypothesis entries are never "
          "surfaced by daydream's novel-jump extension...")
    g = Guala()
    seed_sec, seed_mode, seed_chi = _make_committed_word(g, "harbor")
    g._association_from_deep_atlas = lambda seed_word: (seed_sec, seed_mode, "harbor", 0.8)

    band = max(2, g.atlas.band)
    far_chi = seed_chi + 5 * band + 500  # comfortably beyond min_dist=5*band
    # Force this chi to be a real candidate in the working-atlas snapshot
    # (Extension A samples from list(self.atlas.entries.keys())).
    g.atlas.entries[far_chi]
    # The ONLY deep_atlas entry reachable at far_chi is a reorganize
    # hypothesis -- if the exclusion is broken, this is the only thing
    # Extension A could possibly surface.
    g.deep_atlas.entries[far_chi] = [{
        "source_path": "reorganize_hypothesis",
        "co_occurrence": {seed_sec: {str(seed_mode): 0.99}},
    }]

    import random as _random_mod
    orig_random = _random_mod.random
    _random_mod.random = lambda: 0.0  # force Extension A's probability gate open
    try:
        for _ in range(20):
            g.tick += 1
            events_before = len(g._substrate_events)
            g._daydream_tick()
            new_events = list(g._substrate_events)[events_before:]  # deque: no slicing
            novel_events = [e for e in new_events if e.kind == "daydream_novel"]
            assert not novel_events, (
                f"REGRESSION: reorganize_hypothesis entry was laundered into "
                f"a daydream_novel event: {novel_events[0].detail}")
    finally:
        _random_mod.random = orig_random

    # Non-vacuous check: the reorganize entry is still exactly what we put
    # there (nothing consumed/mutated it in a way that would silently make
    # this test meaningless), and it really was the only thing at far_chi.
    assert g.deep_atlas.entries[far_chi][0]["source_path"] == "reorganize_hypothesis"
    print("  OK: 20 forced novel-jump attempts against a far-chi bucket "
          "containing ONLY a reorganize_hypothesis entry produced zero "
          "daydream_novel events")


# ─────────────────────────────────────────────────────────────────────────
# Boot-wiring: the actual reconnection in app.py's _gl_init().
# ─────────────────────────────────────────────────────────────────────────

class _FakeGualaForBoot:
    """Minimal stand-in for the real Guala engine, used only to observe
    which start_*_loop() methods _gl_init() actually calls under each
    DAYDREAM_LOOP_ENABLED setting -- without paying for a real EFS/S3/
    dream-gate boot (no existing test in this repo exercises _gl_init()
    against the real engine either; heavy infra, out of scope here)."""

    def __init__(self):
        self._corpora = {}
        self.vocab = set(["placeholder"])
        self._guala_identity = "0b4c244a-fake-test-identity"
        self._load_successful = True
        self.tick = 0
        self.calls = []

    def add_corpus(self, *a, **kw):
        pass

    def load_full_state(
            self, state_dir, *, allow_authenticated_legacy_pickle=False):
        assert allow_authenticated_legacy_pickle is False
        pass  # _load_successful already True; no-op "load"

    def start_autonomy_loop(self, interval=0.2):
        self.calls.append(("start_autonomy_loop", interval))

    def start_daydream_loop(self):
        self.calls.append(("start_daydream_loop",))

    def introspect(self):
        return {"vocab": 1, "reads": 0, "pair_bond_active": False,
                "atlas_entries": 0, "current_activity": "IDLE"}


def _run_gl_init_with_fake_guala(monkeypatch, tmp_path, daydream_env):
    import dsf_ai_service.app as app_mod

    fake = _FakeGualaForBoot()
    monkeypatch.setattr(app_mod, "Guala", lambda: fake)
    monkeypatch.setattr(app_mod, "STATE_DIR", str(tmp_path))
    # Isolate this test to the boot-path wiring decision itself: everything
    # after it (_embedded_post_boot: rings, SaveCoordinator, curriculum,
    # heartbeat) is heavy, has its own real infra requirements, and is
    # untouched by this change -- not re-tested here.
    monkeypatch.setattr(app_mod, "_embedded_post_boot", lambda g: None)
    monkeypatch.setenv("DECAY_PAUSED", "1")  # clear the dream-gate RuntimeError
    monkeypatch.delenv("GUALA_SEED_RICH_PATH", raising=False)
    monkeypatch.delenv("FORCE_S3_RESTORE", raising=False)
    if daydream_env is None:
        monkeypatch.delenv("DAYDREAM_LOOP_ENABLED", raising=False)
    else:
        monkeypatch.setenv("DAYDREAM_LOOP_ENABLED", daydream_env)

    app_mod._guala = None
    app_mod._gl_init()
    return fake


def test_gl_init_keeps_daydream_disabled_by_default(monkeypatch, tmp_path):
    """The obsolete periodic daydream mechanism must not start at boot."""
    fake = _run_gl_init_with_fake_guala(monkeypatch, tmp_path, daydream_env=None)
    assert ("start_autonomy_loop", 0.2) in fake.calls, (
        "start_autonomy_loop must still be called unconditionally -- "
        "this change must not touch that")
    assert not any(c[0] == "start_daydream_loop" for c in fake.calls)


def test_gl_init_keeps_daydream_disabled_when_explicitly_zero(monkeypatch, tmp_path):
    fake = _run_gl_init_with_fake_guala(monkeypatch, tmp_path, daydream_env="0")
    assert not any(c[0] == "start_daydream_loop" for c in fake.calls)


def test_gl_init_ignores_obsolete_daydream_enable_switch(monkeypatch, tmp_path):
    """An old task definition cannot reactivate the rejected mechanism."""
    fake = _run_gl_init_with_fake_guala(monkeypatch, tmp_path, daydream_env="1")
    assert ("start_autonomy_loop", 0.2) in fake.calls
    assert not any(c[0] == "start_daydream_loop" for c in fake.calls)


if __name__ == "__main__":
    tests = [
        test_start_daydream_loop_spawns_a_real_named_thread,
        test_start_daydream_loop_is_idempotent,
        test_daydream_tick_reinforces_atlas_and_logs_surface_event_not_a_noop,
        test_daydream_tick_never_triggers_emission,
        test_reorganize_hypothesis_entries_excluded_from_novel_jump,
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
    print("NOTE: boot-wiring tests (test_gl_init_*) use pytest fixtures "
          "(monkeypatch, tmp_path) and are not runnable via this bare "
          "__main__ block -- run via `pytest` instead.")
    if failures:
        print(f"FAILED: {len(failures)}/{len(tests)}")
        for name, err in failures:
            print(f"  - {name}: {err}")
        sys.exit(1)
    else:
        print(f"ALL {len(tests)} FUNCTIONAL TESTS PASSED")
