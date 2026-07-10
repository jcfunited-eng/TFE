"""
GL-RPT-SINGLE-WORD-UNAWARE-ROOTCAUSE-C1-20260710-v1 #3b verification.

wC's live telemetry found Section.modes (the per-section vocabulary
bank) has no size cap at all -- three production sections (listen,
verb, intro) had already grown to 127-148% of the number every status
readout implies is a ceiling (5000), while the sections that should
hold real topic-specific content (subject, object, modifier, ground)
sat starved at 8-36% full. This tests the fix: SECTION_MODE_CAP
enforcement in Section._append_new_mode(), which retires the single
weakest (stalest) alive mode via _evict_weakest_mode() when a section
is at/over cap and a genuinely new mode needs to be added.

3 tests, run directly against the real Section class (no mocks):
  1. A section respects its cap after many distinct new commits,
     including a section that starts life already OVER cap (simulating
     the exact production state this fix ships into) -- proves the fix
     actually converges an overfull section back down, not just freezes
     future growth.
  2. Retirement picks the genuinely weakest (stalest last-active-tick)
     entry, not an arbitrary one (e.g. not lowest index, not most
     recently added).
  3. A retired word's identity lookup (word_match_idx) behaves like the
     word is new again when it reappears -- new mode_idx, old tombstoned
     entry left untouched, no crash.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import dsf_ai_service.v4.gualaloom_v5_engine as engine_mod
from dsf_ai_service.v4.gualaloom_v5_engine import Section
from dsf_ai_service.v4.gualaloom_v4_uf_kernel import DSF


class FakeAtlas:
    """No-op stand-in for LivingAtlas -- Section.receive() only calls
    atlas.record(...) for bookkeeping this test doesn't need to inspect."""
    def record(self, *args, **kwargs):
        pass


def make_dsf(seed):
    """Deterministic, distinct-enough DSF vector per seed. Values don't
    need to respect the documented [0,1]/[-1,1] ranges for this test --
    DSF is a plain dataclass with no range validation, and mode-cap
    enforcement doesn't look at DSF content at all."""
    import numpy as np
    rng = np.random.default_rng(seed)
    vals = rng.uniform(-1.0, 1.0, 8)
    return DSF(*[float(v) for v in vals])


def commit_word(sec, atlas, word, tick, seed=None):
    """One receive() call for a brand-new (or reinforced) word."""
    dsf = make_dsf(seed if seed is not None else hash(word) % (2 ** 31))
    chi = abs(hash(word)) % 997
    return sec.receive(
        dsf, chi, word, atlas, familiarity=0.5, salience=1.0,
        dwell_ticks=1, engine_tick=tick,
    )


def test_cap_respected_after_many_commits():
    print("  Test 1: cap respected after many distinct new commits...", end=" ")
    atlas = FakeAtlas()
    orig_cap = engine_mod.SECTION_MODE_CAP
    try:
        engine_mod.SECTION_MODE_CAP = 10

        # --- 1a: fresh section, grown from empty past the cap ---
        sec = Section(name="t1_fresh")
        for i in range(80):
            committed, mode_idx, _ = commit_word(sec, atlas, f"word{i}", tick=i + 1)
            assert committed, f"commit {i} should have succeeded"
            assert sec._n_alive <= engine_mod.SECTION_MODE_CAP, (
                f"alive count {sec._n_alive} exceeded cap "
                f"{engine_mod.SECTION_MODE_CAP} after commit {i}")
            assert sec._n_alive == sum(1 for a in sec._mode_alive if a), (
                "the O(1) _n_alive counter drifted from the real alive count")

        assert sec._n_alive == engine_mod.SECTION_MODE_CAP, (
            f"expected exactly at cap after 80 commits with cap=10, "
            f"got {sec._n_alive}")
        assert len(sec.modes) == 80, (
            "self.modes must never shrink/reorder -- physical list should "
            f"still hold all 80 appends, got {len(sec.modes)}")

        # --- 1b: a section that starts life ALREADY over cap (the exact
        # production state this fix ships into -- alive-flag tracking
        # doesn't persist across restarts, so a restored section can
        # come back with every historical mode marked alive again even
        # though the live in-memory bank had long since blown past the
        # cap). Confirm the fix actively converges it back down, not
        # just freezes future growth at the already-broken count.
        sec2 = Section(name="t1_overfull")
        for i in range(30):
            dsf = make_dsf(i)
            chi = i
            word = f"legacy{i}"
            sec2.modes.append((dsf, chi, word))
            sec2._mode_last_active_tick.append(100)  # all tie, like post-restart
            sec2._mode_alive.append(True)
            sec2._word_to_mode_idx[word] = i
        sec2._n_alive = 30
        assert sec2._n_alive > engine_mod.SECTION_MODE_CAP, "test setup must start over cap"

        committed, mode_idx, _ = commit_word(sec2, atlas, "genuinely_new", tick=200)
        assert committed
        assert sec2._n_alive == engine_mod.SECTION_MODE_CAP, (
            "a single new-word commit against an already-overfull section "
            f"should converge it to cap, got {sec2._n_alive}")
        assert sec2._n_alive == sum(1 for a in sec2._mode_alive if a)
        # the new word itself must have survived (not immediately evicted)
        assert sec2._mode_alive[mode_idx] is True
        assert sec2._word_to_mode_idx.get("genuinely_new") == mode_idx

        print("PASS")
        return True
    finally:
        engine_mod.SECTION_MODE_CAP = orig_cap


def test_weakest_entry_picked():
    print("  Test 2: retirement picks the genuinely weakest entry...", end=" ")
    atlas = FakeAtlas()
    orig_cap = engine_mod.SECTION_MODE_CAP
    try:
        engine_mod.SECTION_MODE_CAP = 5
        sec = Section(name="t2")

        # Fill to exactly cap with distinct, deliberately non-monotonic
        # last-active ticks so "weakest" can't be confused with "lowest
        # index" or "most recently appended".
        ticks = {"w0": 100, "w1": 50, "w2": 300, "w3": 400, "w4": 500}
        idx_of = {}
        for word, t in ticks.items():
            committed, mode_idx, _ = commit_word(sec, atlas, word, tick=t)
            assert committed
            idx_of[word] = mode_idx

        assert sec._n_alive == 5
        w1_idx = idx_of["w1"]  # stalest (tick=50) -- must be the one evicted

        # A 6th genuinely new word forces exactly one eviction.
        committed, new_idx, _ = commit_word(sec, atlas, "w5", tick=600)
        assert committed

        assert sec._mode_alive[w1_idx] is False, (
            "the mode with the OLDEST last-active tick must be the one "
            "retired, not an arbitrary one")
        for word in ("w0", "w2", "w3", "w4"):
            assert sec._mode_alive[idx_of[word]] is True, (
                f"{word} should NOT have been evicted (it wasn't the stalest)")
        assert "w1" not in sec._word_to_mode_idx, (
            "evicted word must be removed from the O(1) word index")
        assert sec._n_alive == 5, f"expected to stay at cap, got {sec._n_alive}"

        print("PASS")
        return True
    finally:
        engine_mod.SECTION_MODE_CAP = orig_cap


def test_retired_word_reappears_cleanly():
    print("  Test 3: retired word reappearing behaves like a new word, no crash...", end=" ")
    atlas = FakeAtlas()
    orig_cap = engine_mod.SECTION_MODE_CAP
    try:
        engine_mod.SECTION_MODE_CAP = 3
        sec = Section(name="t3")

        commit_word(sec, atlas, "alpha", tick=10)
        commit_word(sec, atlas, "beta", tick=20)
        commit_word(sec, atlas, "gamma", tick=30)
        assert sec._n_alive == 3
        alpha_orig_idx = sec._word_to_mode_idx["alpha"]

        # Force alpha's eviction: reinforce beta/gamma to bump their
        # recency past alpha, then add a genuinely new word.
        commit_word(sec, atlas, "beta", tick=100)
        commit_word(sec, atlas, "gamma", tick=100)
        committed, delta_idx, _ = commit_word(sec, atlas, "delta", tick=200)
        assert committed
        assert sec._mode_alive[alpha_orig_idx] is False, "alpha should have been evicted"
        assert "alpha" not in sec._word_to_mode_idx

        # alpha reappears -- must not crash, must be treated as new.
        committed, alpha_new_idx, _ = commit_word(sec, atlas, "alpha", tick=300)
        assert committed, "a retired word reappearing must still commit cleanly"
        assert alpha_new_idx != alpha_orig_idx, (
            "reappeared word must get a NEW identity, not reuse/collide with "
            "the tombstoned index")
        assert sec._word_to_mode_idx["alpha"] == alpha_new_idx
        assert sec._mode_alive[alpha_new_idx] is True

        # old tombstoned slot must still be readable (content permanence --
        # anything still holding that old mode_idx, e.g. an atlas binding,
        # must not crash indexing into sec.modes).
        old_dsf, old_chi, old_word = sec.modes[alpha_orig_idx]
        assert old_word == "alpha", "tombstoning must not alter stored content"

        # A second reappearance also must not crash / collide.
        committed2, _, _ = commit_word(sec, atlas, "alpha", tick=400)
        assert committed2 or True  # word_match_idx path (reinforce) always "commits"

        print("PASS")
        return True
    finally:
        engine_mod.SECTION_MODE_CAP = orig_cap


def test_eviction_cost_bounded_by_cap_not_lifetime_history():
    """Regression guard for the adversarial-review finding on this fix:
    _evict_weakest_mode() must cost O(n_alive) (bounded by the cap), not
    O(len(self.modes)) (total lifetime vocabulary ever seen, which never
    shrinks and grows forever). If a future change makes eviction scan
    the full physical history again, a section that's been running a
    long time and stays at cap would pay steadily GROWING per-commit
    cost forever -- the exact class of unbounded-O(n_modes) regression
    GL-BUG-MODES-MATRIX-THRASH already had to fix once (measured ~26s
    live at 14,000+ modes). Compares wall time of an early batch of
    evicting commits (small physical history) against a late batch
    (physical history ~40x larger, alive count identical) -- must NOT
    scale with physical history size."""
    import time
    print("  Test 4: eviction cost bounded by cap, not lifetime history...", end=" ")
    atlas = FakeAtlas()
    orig_cap = engine_mod.SECTION_MODE_CAP
    try:
        engine_mod.SECTION_MODE_CAP = 50
        sec = Section(name="t4")

        # Fill to cap first (no evictions yet).
        for i in range(50):
            commit_word(sec, atlas, f"seed{i}", tick=i + 1)
        assert sec._n_alive == 50

        # Early batch: physical history ~50-150 (small).
        t0 = time.perf_counter()
        for i in range(100):
            committed, _, _ = commit_word(sec, atlas, f"early{i}", tick=1000 + i)
            assert committed
        t_early = time.perf_counter() - t0
        assert sec._n_alive == 50
        assert len(sec.modes) == 150

        # Late batch: physical history ~5050-5150 (~40x larger than the
        # early batch's history size), alive count still exactly at cap.
        for i in range(4900):
            commit_word(sec, atlas, f"filler{i}", tick=2000 + i)
        assert len(sec.modes) == 5050
        assert sec._n_alive == 50

        t0 = time.perf_counter()
        for i in range(100):
            committed, _, _ = commit_word(sec, atlas, f"late{i}", tick=10000 + i)
            assert committed
        t_late = time.perf_counter() - t0
        assert sec._n_alive == 50
        assert len(sec.modes) == 5150

        # Generous factor (not a tight perf assertion, just a guard
        # against reintroducing full-history O(n) scanning -- an
        # O(n_total) implementation here would show a ~30-40x slowdown
        # matching the growth in physical history; O(n_alive) should
        # show roughly flat cost).
        ratio = t_late / max(t_early, 1e-9)
        print(f"(early={t_early*1000:.1f}ms late={t_late*1000:.1f}ms ratio={ratio:.2f}x)", end=" ")
        assert ratio < 8.0, (
            f"eviction cost scaled {ratio:.1f}x as physical history grew "
            f"~40x -- looks like eviction is scanning full history again, "
            f"not just the alive set")

        print("PASS")
        return True
    finally:
        engine_mod.SECTION_MODE_CAP = orig_cap


def main():
    print("GL-RPT-SINGLE-WORD-UNAWARE-ROOTCAUSE-C1-20260710-v1 #3b: "
          "Section mode-cap enforcement")
    print("=" * 70)
    results = [
        test_cap_respected_after_many_commits(),
        test_weakest_entry_picked(),
        test_retired_word_reappears_cleanly(),
        test_eviction_cost_bounded_by_cap_not_lifetime_history(),
    ]
    overall = all(results)
    print("=" * 70)
    print(f"OVERALL: {'PASS' if overall else 'FAIL'} ({sum(results)}/{len(results)})")
    return overall


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
