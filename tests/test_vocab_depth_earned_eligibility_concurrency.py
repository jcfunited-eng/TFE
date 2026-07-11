"""
test_vocab_depth_earned_eligibility_concurrency.py -- real-threading
adversarial tests for GL-DES-VOCAB-DEPTH-EARNED-ELIGIBILITY-C1-20260711
Part 1 (wiring DeepAtlas.strength into the real-speech eligibility
backfill).

Matches the established pattern in tests/test_daydream_loop_reconnect_
concurrency.py and tests/test_read_sentence_lock_granularity_concurrency.py
(see those files' own docstrings): real Guala() instances, real
threading.Thread, real self.lock -- no mocks of the locking mechanism
itself.

What this specifically targets: _backfill_eligibility_for_promotion /
_grant_emission_eligibility_for_word write TWO shared structures
(self._word_to_emission_sections and self._grounded_words) from inside a
real dream cycle's Phase 3b (_run_dream_cycle_phased, DREAM_CYCLE_PHASED=1
-- confirmed the actual live production setting via deploy_dsf_ai.sh) --
the same `with self.lock:` block DeepAtlas.dream_promotion_gate's real
promotion writes already happen in. A concurrent reader (the real pattern
converse()'s default single-lock body uses) must NEVER observe a torn
intermediate state -- e.g. a word promoted in deep_atlas with sufficient
strength but only ONE of the two eligibility structures updated. This
file proves that empirically under real concurrent load, plus that the
promotion+backfill sequence does not deadlock or crash against a real
contending thread.
"""

import os
import sys
import time
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dsf_ai_service.v4.gualaloom_v5_engine import (  # noqa: E402
    Guala, LanguageKrimelack, deterministic_motif_id,
)
from dsf_ai_service.substrate.deep_atlas import DeepAtlas  # noqa: E402

ENV_FLAG = "DEEP_ATLAS_ELIGIBILITY_BACKFILL_ENABLED"


def _make_mode(g, word, section):
    k = LanguageKrimelack()
    k.transduce(word)
    chi = k.winding
    mid = deterministic_motif_id(word)
    sec = g.sections[section]
    while len(sec.modes) <= mid:
        sec.modes.append((0, 0, ""))
    sec.modes[mid] = (0, 0, word)
    return chi, mid


def _teach_via_atlas(g, word, section, chi, mid, tick=10, salience=1.0):
    g.atlas.record(section, mid, chi, tick=tick, salience=salience,
                   dwell_ticks=1, source="corpus")
    g.sections[section].commits.append({
        "tick": tick, "mode": mid, "chi": chi, "word": word, "grounded": False,
    })


class _SlowDreamPromotionGate:
    """Context manager: wraps the real g.deep_atlas.dream_promotion_gate
    (bound instance method) with a real sleep BEFORE delegating to the
    unmodified original -- same "monkeypatch a real call site with an
    artificial delay to simulate real substrate cost under load"
    convention tests/test_read_sentence_lock_granularity_concurrency.py's
    _SlowSectionReceive already uses. This extends Phase 3b's real
    self.lock hold (the block _backfill_eligibility_for_promotion also
    runs inside -- see both _run_dream_cycle/_run_dream_cycle_phased call
    sites) long enough to reliably observe a contender's acquisition
    attempts landing squarely inside vs. outside that window, without
    relying on a tiny fixture's real execution time to be slow enough on
    its own (which would make the test flaky)."""

    def __init__(self, g, sleep_s):
        self.g = g
        self.sleep_s = sleep_s
        self._orig = None

    def __enter__(self):
        self._orig = self.g.deep_atlas.dream_promotion_gate
        orig = self._orig
        sleep_s = self.sleep_s

        def _slow(*a, **kw):
            time.sleep(sleep_s)
            return orig(*a, **kw)

        self.g.deep_atlas.dream_promotion_gate = _slow
        return self

    def __exit__(self, *exc):
        self.g.deep_atlas.dream_promotion_gate = self._orig


def test_concurrent_reader_never_observes_torn_eligibility_state():
    """Real background thread runs real dream cycles (DREAM_CYCLE_PHASED=1,
    the real production phased path) promoting + backfilling 'ocean'
    while a real foreground contender repeatedly takes real g.lock-
    protected snapshots of (word_to_emission_sections membership,
    grounded_words membership). Every single snapshot must show the two
    structures in agreement -- never one updated without the other."""
    print("Concurrency test 1: no torn intermediate state between "
          "_word_to_emission_sections and _grounded_words during a real "
          "dream-cycle promotion+backfill...")
    os.environ[ENV_FLAG] = "1"
    os.environ["REQUIRE_GROUNDED_SPEECH"] = "1"
    os.environ["DREAM_CYCLE_PHASED"] = "1"
    g = Guala()
    try:
        chi, mid = _make_mode(g, "ocean", "object")
        _teach_via_atlas(g, "ocean", "object", chi, mid, tick=10, salience=1.0)
        assert "ocean" not in g._word_to_emission_sections

        snapshots = []
        mismatches = []
        stop_contender = threading.Event()
        contender_errors = []

        def _contender():
            try:
                while not stop_contender.is_set():
                    got = g.lock.acquire(timeout=0.5)
                    if got:
                        try:
                            eligible = "ocean" in g._word_to_emission_sections
                            grounded = "ocean" in g._grounded_words
                            snapshots.append((time.monotonic(), eligible, grounded))
                            if eligible != grounded:
                                mismatches.append((eligible, grounded))
                        finally:
                            g.lock.release()
                        time.sleep(0.001)
            except Exception as e:
                contender_errors.append(e)

        contender = threading.Thread(target=_contender, daemon=True)
        contender.start()

        dreamer_errors = []

        def _dream():
            try:
                # Head start: let the contender accumulate several
                # guaranteed pre-promotion snapshots before any dream
                # cycle runs at all, so "real interleaving observed
                # before eligibility" is not left to timing chance.
                time.sleep(0.05)
                with _SlowDreamPromotionGate(g, 0.05):
                    for i, t in enumerate((200, 400, 600)):
                        g.tick = t
                        g._run_dream_cycle(caller_kind="DREAMING")
                        time.sleep(0.02)
            except Exception as e:
                dreamer_errors.append(e)

        t0 = time.monotonic()
        dreamer = threading.Thread(target=_dream, daemon=True)
        dreamer.start()
        dreamer.join(timeout=30)
        elapsed = time.monotonic() - t0
        stop_contender.set()
        contender.join(timeout=5)

        assert not dreamer_errors, f"dream cycle thread raised: {dreamer_errors}"
        assert not contender_errors, f"contender thread raised: {contender_errors}"
        assert not mismatches, (
            f"REGRESSION: torn state observed -- eligible/grounded "
            f"disagreed {len(mismatches)} time(s): {mismatches[:5]}")
        assert len(snapshots) >= 2, (
            f"only {len(snapshots)} snapshot(s) taken -- test inconclusive, "
            "contender did not get enough real interleaving opportunity "
            f"(elapsed={elapsed:.3f}s)")

        # Confirm real interleaving actually happened (not just before/after):
        # at least one snapshot before 'ocean' became eligible AND at least
        # one after, proving the contender genuinely raced the promotion.
        pre = [s for s in snapshots if not s[1]]
        post = [s for s in snapshots if s[1]]
        print(f"  {len(snapshots)} real locked snapshots taken during "
              f"{elapsed:.3f}s of real dream-cycle activity "
              f"({len(pre)} pre-eligible, {len(post)} post-eligible), "
              "zero torn states")
        assert pre, "no snapshot observed 'ocean' in its ineligible state -- inconclusive"
        assert post, "no snapshot observed 'ocean' in its eligible state -- inconclusive"

        assert "ocean" in g._word_to_emission_sections, (
            "'ocean' never became eligible by the end of the real dream-cycle series")
        assert "ocean" in g._grounded_words
        print("  OK: zero torn states across real concurrent access, "
              "final state correct")
    finally:
        os.environ.pop(ENV_FLAG, None)
        os.environ.pop("REQUIRE_GROUNDED_SPEECH", None)
        os.environ.pop("DREAM_CYCLE_PHASED", None)
        g.shutdown()


def test_dream_cycle_promotion_backfill_does_not_deadlock_against_contender():
    """A real contending thread aggressively acquiring/releasing g.lock
    throughout must never cause the dream-cycle thread (which itself
    acquires g.lock internally, real RLock, real phases) to hang. Bounded
    join() timeouts below would fail the test on a real deadlock rather
    than hanging the suite forever."""
    print("Concurrency test 2: real dream-cycle promotion+backfill does "
          "not deadlock against a real contending thread...")
    os.environ[ENV_FLAG] = "1"
    os.environ["REQUIRE_GROUNDED_SPEECH"] = "1"
    os.environ["DREAM_CYCLE_PHASED"] = "1"
    g = Guala()
    try:
        chi, mid = _make_mode(g, "current", "verb")
        _teach_via_atlas(g, "current", "verb", chi, mid, tick=10, salience=1.0)

        stop_contender = threading.Event()
        contender_errors = []

        def _contender():
            try:
                while not stop_contender.is_set():
                    with g.lock:
                        _ = dict(g._word_to_emission_sections)
                        _ = set(g._grounded_words)
                    time.sleep(0.001)
            except Exception as e:
                contender_errors.append(e)

        contender = threading.Thread(target=_contender, daemon=True)
        contender.start()

        dreamer_errors = []

        def _dream():
            try:
                with _SlowDreamPromotionGate(g, 0.03):
                    for i, t in enumerate((200, 400, 600)):
                        g.tick = t
                        g._run_dream_cycle(caller_kind="DREAMING")
            except Exception as e:
                dreamer_errors.append(e)

        dreamer = threading.Thread(target=_dream, daemon=True)
        dreamer.start()
        dreamer.join(timeout=15)
        stop_contender.set()
        contender.join(timeout=5)

        assert not dreamer.is_alive(), "REGRESSION: dream-cycle thread appears deadlocked"
        assert not dreamer_errors, f"dream cycle thread raised: {dreamer_errors}"
        assert not contender_errors, f"contender thread raised: {contender_errors}"
        assert "current" in g._word_to_emission_sections
        print("  OK: no deadlock, 'current' correctly became eligible")
    finally:
        os.environ.pop(ENV_FLAG, None)
        os.environ.pop("REQUIRE_GROUNDED_SPEECH", None)
        os.environ.pop("DREAM_CYCLE_PHASED", None)
        g.shutdown()


if __name__ == "__main__":
    tests = [
        test_concurrent_reader_never_observes_torn_eligibility_state,
        test_dream_cycle_promotion_backfill_does_not_deadlock_against_contender,
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
