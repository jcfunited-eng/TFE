"""
GL-RPT-READ-MS-ROOTCAUSE-C1-20260711-v1 fix #1 verification.

read_ms telemetry (live production, two real conversational turns) found
Section.receive()'s similarity-scan fallback -- used for any word that
misses the O(1) word-identity fast path -- was the dominant real cost of
a live turn (77-92% of total wall-clock), because it built a vectorized
cosine-similarity matrix against EVERY alive mode in the section
(_get_modes_matrix()) before comparing. The "listen" section alone was
documented (GL-BUG-MODES-MATRIX-THRASH) at 14,000+ modes.

Fix: bucket a section's alive modes by their own chi value (already
computed and passed into receive(), already stored per-mode as
self.modes[i][1]) and restrict the fallback scan to a small
+/-SECTION_CHI_BAND neighborhood around the query chi -- the same
coarse-pre-categorization-before-detailed-comparison pattern ChiAtlas
already uses (dsf_ai_service/v4/gualaloom_v4_chi_atlas_l6.py, CHI_BAND),
reusing its exact band width rather than inventing a new radius.

5 tests, run directly against the real Section class (no mocks):
  1. Correctness at production shape: for many real (word-labeled) new-
     word commits against a large, multi-chi-value section, the fixed
     Section (chi-bucketed scan) produces IDENTICAL (committed, mode_idx)
     decisions to a reference Section that overrides only the candidate-
     gathering step to reproduce the OLD full-alive-set scan -- proving
     zero behavior change for the contract every real call site
     (gualaloom_v5_engine.py's read_word/read_sentence) actually uses:
     word_label is always a non-empty string at every real receive()
     call site (confirmed by direct code inspection), and the append/
     reinforce decision structurally never depends on best_sim once
     word_label is truthy (`best_sim < thresh or word_label` short-
     circuits) -- so the ONLY way this fix could change real behavior is
     if it were narrowed enough to miss a same-word-identity fast-path
     hit, which it cannot (word-identity lookup is untouched, chi-
     independent).
  2. In-band matches are still found: when a near-duplicate DSF vector
     exists at a chi WITHIN SECTION_CHI_BAND of the query chi, the
     bucketed scan finds it and computes the same best_sim (within
     floating tolerance) as the full scan -- the direct "a word that
     WOULD have matched via the full scan must still be found via the
     bucketed scan" check for the in-band case.
  3. Documents the deliberate narrowing boundary: a near-duplicate
     OUTSIDE the band is (by design) not found by the bucketed scan,
     confirmed against the same reference full-scan Section, but this
     is proven (test 1) to never change committed/mode_idx for any real
     call site's word-labeled contract -- not a silent gap.
  4. Speed: chi-bucketed scan is meaningfully faster than the full-
     alive-set scan at the exact 14,000-mode "listen" section scale the
     live root-cause report measured.
  5. Existing mode-cap machinery (_n_alive/_alive_indices, the fix this
     one extends) stays exactly correct alongside the new chi-bucket
     index across append/evict/forget/rebuild-on-load -- i.e. the new
     _chi_buckets index never drifts from _alive_indices.
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import numpy as np

import dsf_ai_service.v4.gualaloom_v5_engine as engine_mod
from dsf_ai_service.v4.gualaloom_v5_engine import Section, SECTION_CHI_BAND
from dsf_ai_service.v4.gualaloom_v4_uf_kernel import DSF


class FakeAtlas:
    """No-op stand-in for LivingAtlas -- Section.receive() only calls
    atlas.record(...) for bookkeeping this test doesn't need to inspect."""
    def record(self, *args, **kwargs):
        pass


class FullScanSection(Section):
    """Reference section reproducing PRE-fix receive() behavior: the
    similarity-scan fallback compares against every alive mode in the
    section, not just a chi neighborhood. Overrides ONLY the one method
    receive() calls to gather scan candidates -- every other line of
    receive() (word-identity fast path, bootstrap/dead-zone gate,
    commit bookkeeping, mode-cap eviction) is the real, unmodified,
    currently-shipping code. This isolates exactly what this fix
    changed, rather than hand-duplicating receive()'s whole body."""
    def _get_chi_neighborhood_matrix(self, chi):
        if not self._alive_indices:
            return None, None, None
        real_indices = list(self._alive_indices)
        vecs = np.array([self.modes[i][0].to_array() for i in real_indices])
        norms = np.linalg.norm(vecs, axis=1) + 1e-12
        return real_indices, vecs, norms


def make_dsf(seed):
    """Deterministic, distinct-enough DSF vector per seed."""
    rng = np.random.default_rng(seed)
    vals = rng.uniform(-1.0, 1.0, 8)
    return DSF(*[float(v) for v in vals])


def commit_word(sec, atlas, word, tick, chi, seed=None):
    dsf = make_dsf(seed if seed is not None else hash(word) % (2 ** 31))
    return sec.receive(
        dsf, chi, word, atlas, familiarity=0.5, salience=1.0,
        dwell_ticks=1, engine_tick=tick,
    )


def _populate_production_shape(sec, atlas, n_modes, chi_spread, seed_base=0):
    """Fill a section to roughly the live 'listen' section's documented
    scale (14,000+ modes) with chi values spread across chi_spread
    distinct buckets -- comparable density to test_section_mode_cap.py's
    own commit_word() convention (chi = hash(word) % ~1000), representing
    a section that has accumulated modes across a wide chi range over a
    long lifetime, the exact shape GL-BUG-MODES-MATRIX-THRASH's own
    comment documents."""
    for i in range(n_modes):
        word = f"hist{seed_base}_{i}"
        chi = (seed_base * 7919 + i * 31) % chi_spread
        commit_word(sec, atlas, word, tick=i + 1, chi=chi, seed=i + seed_base * 100000)


def test_correctness_matches_full_scan_at_production_shape():
    print("  Test 1: bucketed scan matches full-scan decisions at "
          "production shape (many words, many chi values)...", end=" ")
    atlas = FakeAtlas()
    orig_cap = engine_mod.SECTION_MODE_CAP
    try:
        engine_mod.SECTION_MODE_CAP = 20000  # high enough that this test's fill never evicts
        n_modes = 14000
        chi_spread = 997  # comparable bucket density to test_section_mode_cap.py

        sec_fixed = Section(name="prod_fixed")
        sec_full = FullScanSection(name="prod_full")
        _populate_production_shape(sec_fixed, atlas, n_modes, chi_spread)
        _populate_production_shape(sec_full, atlas, n_modes, chi_spread)
        assert sec_fixed._n_alive == sec_full._n_alive == n_modes

        # Now commit many genuinely NEW words (real call-site contract:
        # word_label always a non-empty string) at a spread of chi values,
        # including chi values that land squarely inside a dense existing
        # bucket and chi values in sparser regions.
        mismatches = []
        for i in range(500):
            word = f"newword_{i}"
            chi = (i * 53) % chi_spread
            tick = n_modes + i + 1
            r_fixed = commit_word(sec_fixed, atlas, word, tick=tick, chi=chi, seed=900000 + i)
            r_full = commit_word(sec_full, atlas, word, tick=tick, chi=chi, seed=900000 + i)
            committed_fixed, mode_idx_fixed, _ = r_fixed
            committed_full, mode_idx_full, _ = r_full
            if (committed_fixed, mode_idx_fixed) != (committed_full, mode_idx_full):
                mismatches.append((word, r_fixed, r_full))

        assert not mismatches, (
            f"{len(mismatches)} of 500 new-word commits diverged between "
            f"the chi-bucketed scan and the full-scan reference: "
            f"{mismatches[:5]}")

        # Also re-commit (reinforce) a sample of already-known words --
        # the O(1) word-identity fast path must be completely unaffected
        # (it never even reaches the scan this fix changed).
        for i in range(0, 14000, 700):
            word = f"hist0_{i}"
            r_fixed = commit_word(sec_fixed, atlas, word, tick=99999, chi=0, seed=i)
            r_full = commit_word(sec_full, atlas, word, tick=99999, chi=0, seed=i)
            assert r_fixed[:2] == r_full[:2], f"reinforcement diverged for {word}"

        print(f"PASS (500 new-word + 20 reinforce commits, 0 mismatches, "
              f"{n_modes} modes across {chi_spread} chi buckets)")
        return True
    finally:
        engine_mod.SECTION_MODE_CAP = orig_cap


def test_in_band_match_still_found():
    print("  Test 2: a near-duplicate WITHIN band is still found "
          "(same best_sim as full scan)...", end=" ")
    atlas = FakeAtlas()
    sec_fixed = Section(name="inband_fixed")
    sec_full = FullScanSection(name="inband_full")

    # Fill both sections identically: a spread of unrelated modes, PLUS
    # one near-duplicate of the upcoming query vector at a chi exactly
    # SECTION_CHI_BAND away from the query chi (the edge of what should
    # still be found).
    query_chi = 500
    near_dup_chi = query_chi + SECTION_CHI_BAND  # edge of the band, inclusive
    query_seed = 42
    for i in range(300):
        chi = (i * 17) % 997
        if chi in (query_chi, near_dup_chi):
            chi = (chi + 1) % 997  # keep unrelated filler out of the two chi keys we care about
        w = f"filler{i}"
        r1 = commit_word(sec_fixed, atlas, w, tick=i + 1, chi=chi, seed=i)
        r2 = commit_word(sec_full, atlas, w, tick=i + 1, chi=chi, seed=i)
        assert r1[:2] == r2[:2]

    # The near-duplicate: same DSF seed as the query vector will use
    # (so cosine similarity ~1.0), placed at near_dup_chi.
    r1 = commit_word(sec_fixed, atlas, "near_duplicate", tick=1000, chi=near_dup_chi, seed=query_seed)
    r2 = commit_word(sec_full, atlas, "near_duplicate", tick=1000, chi=near_dup_chi, seed=query_seed)
    assert r1[:2] == r2[:2]

    # Directly probe the scan mechanism (not full receive(), which would
    # short-circuit on word_label truthy regardless of best_sim -- see
    # module docstring) with word_label=None, the one case where best_sim
    # actually drives the decision.
    query_dsf = make_dsf(query_seed)
    real_idx_fixed, mat_fixed, norms_fixed = sec_fixed._get_chi_neighborhood_matrix(query_chi)
    real_idx_full, mat_full, norms_full = sec_full._get_chi_neighborhood_matrix(query_chi)
    assert mat_fixed is not None and mat_full is not None, "both scans must find candidates"

    cur_v = query_dsf.to_array()
    cur_norm = float(np.linalg.norm(cur_v)) + 1e-12
    sims_fixed = (mat_fixed @ cur_v) / (norms_fixed * cur_norm)
    sims_full = (mat_full @ cur_v) / (norms_full * cur_norm)
    best_fixed = float(np.max(sims_fixed))
    best_full = float(np.max(sims_full))

    assert abs(best_fixed - best_full) < 1e-9, (
        f"in-band best_sim diverged: bucketed={best_fixed} full={best_full}")
    assert best_fixed > 0.999, (
        f"expected the near-duplicate (edge of band, offset={SECTION_CHI_BAND}) "
        f"to be found with ~1.0 cosine similarity, got {best_fixed}")
    print(f"PASS (near-dup at exactly +{SECTION_CHI_BAND} chi found, "
          f"best_sim bucketed={best_fixed:.6f} full={best_full:.6f})")
    return True


def test_out_of_band_boundary_is_documented_and_harmless():
    print("  Test 3: out-of-band near-duplicate is (by design) not found "
          "by the bucketed scan, but never changes real commit "
          "decisions (word_label always set at every real call site)...",
          end=" ")
    atlas = FakeAtlas()
    sec_fixed = Section(name="oob_fixed")
    sec_full = FullScanSection(name="oob_full")

    query_chi = 500
    far_chi = query_chi + SECTION_CHI_BAND + 1  # just outside the band
    query_seed = 7

    for i in range(200):
        chi = (i * 13) % 997
        if chi in (query_chi, far_chi):
            chi = (chi + 1) % 997
        w = f"filler{i}"
        commit_word(sec_fixed, atlas, w, tick=i + 1, chi=chi, seed=i)
        commit_word(sec_full, atlas, w, tick=i + 1, chi=chi, seed=i)

    commit_word(sec_fixed, atlas, "far_duplicate", tick=1000, chi=far_chi, seed=query_seed)
    commit_word(sec_full, atlas, "far_duplicate", tick=1000, chi=far_chi, seed=query_seed)

    query_dsf = make_dsf(query_seed)
    cur_v = query_dsf.to_array()
    cur_norm = float(np.linalg.norm(cur_v)) + 1e-12

    real_idx_fixed, mat_fixed, norms_fixed = sec_fixed._get_chi_neighborhood_matrix(query_chi)
    real_idx_full, mat_full, norms_full = sec_full._get_chi_neighborhood_matrix(query_chi)
    best_fixed = float(np.max((mat_fixed @ cur_v) / (norms_fixed * cur_norm))) if mat_fixed is not None else -1.0
    best_full = float(np.max((mat_full @ cur_v) / (norms_full * cur_norm)))

    # The deliberate, documented narrowing: the bucketed scan does NOT
    # see the out-of-band duplicate; the full scan does.
    assert best_full > 0.999, "full scan (reference) must find the far duplicate"
    assert best_fixed < best_full - 0.5, (
        "bucketed scan unexpectedly found the out-of-band duplicate -- "
        "SECTION_CHI_BAND filtering is not actually restricting the scan")

    # But prove this boundary is harmless for every REAL call-site
    # contract: with word_label set (as every real caller always passes),
    # receive()'s actual commit decision is identical regardless.
    r_fixed = commit_word(sec_fixed, atlas, "real_new_word", tick=2000, chi=query_chi, seed=query_seed)
    r_full = commit_word(sec_full, atlas, "real_new_word", tick=2000, chi=query_chi, seed=query_seed)
    assert r_fixed[:2] == r_full[:2], (
        "even though best_sim differs at the scan level, the real "
        "receive() decision (word_label always truthy) must still match")

    print(f"PASS (far dup at +{SECTION_CHI_BAND + 1} correctly excluded from "
          f"bucketed scan: best_sim bucketed={best_fixed:.3f} vs "
          f"full={best_full:.3f}; real receive() decision unaffected)")
    return True


def test_speed_meaningfully_faster_at_production_scale():
    print("  Test 4: chi-bucketed scan meaningfully faster than full-alive "
          "scan at 14,000-mode production scale...", end=" ")
    atlas = FakeAtlas()
    orig_cap = engine_mod.SECTION_MODE_CAP
    try:
        engine_mod.SECTION_MODE_CAP = 20000
        n_modes = 14000
        chi_spread = 997

        sec_fixed = Section(name="speed_fixed")
        sec_full = FullScanSection(name="speed_full")
        _populate_production_shape(sec_fixed, atlas, n_modes, chi_spread)
        _populate_production_shape(sec_full, atlas, n_modes, chi_spread)

        n_calls = 200
        chis = [(i * 61) % chi_spread for i in range(n_calls)]

        t0 = time.perf_counter()
        for i, chi in enumerate(chis):
            r = commit_word(sec_fixed, atlas, f"speedword_{i}", tick=n_modes + i, chi=chi, seed=800000 + i)
            assert r[0]
        t_fixed = time.perf_counter() - t0

        t0 = time.perf_counter()
        for i, chi in enumerate(chis):
            r = commit_word(sec_full, atlas, f"speedword_{i}", tick=n_modes + i, chi=chi, seed=800000 + i)
            assert r[0]
        t_full = time.perf_counter() - t0

        speedup = t_full / max(t_fixed, 1e-9)
        print(f"(bucketed={t_fixed*1000:.1f}ms full={t_full*1000:.1f}ms "
              f"speedup={speedup:.1f}x for {n_calls} calls @ {n_modes} modes)", end=" ")
        # Generous, not a tight perf assertion (matches this file's sibling
        # test's own convention) -- just a real, meaningful, measured
        # speedup, not a claim.
        assert speedup > 5.0, (
            f"expected the chi-bucketed scan to be meaningfully faster "
            f"than the full-alive-set scan at this scale, got only "
            f"{speedup:.1f}x")
        print("PASS")
        return True
    finally:
        engine_mod.SECTION_MODE_CAP = orig_cap


def test_chi_buckets_stay_consistent_with_alive_indices():
    print("  Test 5: _chi_buckets never drifts from _alive_indices across "
          "append/evict/forget/rebuild-on-load...", end=" ")
    atlas = FakeAtlas()
    orig_cap = engine_mod.SECTION_MODE_CAP

    def _assert_consistent(sec, label):
        total_in_buckets = sum(len(v) for v in sec._chi_buckets.values())
        assert total_in_buckets == sec._n_alive == len(sec._alive_indices), (
            f"[{label}] bucket total={total_in_buckets} n_alive={sec._n_alive} "
            f"alive_indices={len(sec._alive_indices)}")
        union_of_buckets = set()
        for v in sec._chi_buckets.values():
            union_of_buckets |= v
        assert union_of_buckets == sec._alive_indices, f"[{label}] bucket contents diverged from alive_indices"
        for chi_key, idx_set in sec._chi_buckets.items():
            for idx in idx_set:
                assert sec.modes[idx][1] == chi_key, (
                    f"[{label}] mode {idx} filed under chi bucket {chi_key} "
                    f"but its own chi is {sec.modes[idx][1]}")

    try:
        engine_mod.SECTION_MODE_CAP = 30
        sec = Section(name="consistency")

        # Append past cap (forces evictions) with a handful of repeated
        # chi values so multiple modes share a bucket.
        for i in range(100):
            chi = i % 7
            commit_word(sec, atlas, f"w{i}", tick=i + 1, chi=chi, seed=i)
            _assert_consistent(sec, f"after append {i}")

        # Force forget_stale_modes to tombstone a chunk.
        sec.forget_stale_modes(current_tick=1 + Section.MODE_FORGET_TICKS + 50)
        _assert_consistent(sec, "after forget_stale_modes")

        # Simulate a restore: hand-build modes/mode_alive like a loaded
        # save (the exact production restore path), then rebuild.
        sec2 = Section(name="consistency_restore")
        for i in range(50):
            dsf = make_dsf(i)
            chi = i % 5
            word = f"legacy{i}"
            sec2.modes.append((dsf, chi, word))
            sec2._mode_last_active_tick.append(10)
            sec2._mode_alive.append(i % 3 != 0)  # tombstone every 3rd on "restore"
            sec2._word_to_mode_idx[word] = i
        sec2._rebuild_word_index(current_tick=10)
        _assert_consistent(sec2, "after _rebuild_word_index (restore path)")

        # And after further commits post-restore (mixing append + evict).
        for i in range(60):
            commit_word(sec2, atlas, f"post_restore_{i}", tick=100 + i, chi=i % 4, seed=1000 + i)
        _assert_consistent(sec2, "after post-restore commits")

        print("PASS")
        return True
    finally:
        engine_mod.SECTION_MODE_CAP = orig_cap


def main():
    print("GL-RPT-READ-MS-ROOTCAUSE-C1-20260711-v1 fix #1: "
          "Section chi-bucketed similarity scan")
    print("=" * 70)
    results = [
        test_correctness_matches_full_scan_at_production_shape(),
        test_in_band_match_still_found(),
        test_out_of_band_boundary_is_documented_and_harmless(),
        test_speed_meaningfully_faster_at_production_scale(),
        test_chi_buckets_stay_consistent_with_alive_indices(),
    ]
    overall = all(results)
    print("=" * 70)
    print(f"OVERALL: {'PASS' if overall else 'FAIL'} ({sum(results)}/{len(results)})")
    return overall


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
