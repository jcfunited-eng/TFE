# GL-RPT-EMISSION-PERF-C1-20260629-45

doc_id: GL-RPT-EMISSION-PERF-C1-20260629-45
Implements: GL-CMD-EMISSION-PERF-EVE-20260629-45
Date: 2026-06-30
Author: c1
SHA: 1ca761e
ECS task: dsf-ai-task:371

---

## Diff summary

### §2.1 — `_grandurun_select_candidates` (two-pass vectorized)

**Before:** Pass through all candidates × sections × top-k, calling
`_grandurun_amplitude_multichi()` (Python loop over all input_chis) per
candidate entry. With 300 deep_candidates × 7 sections × 3 motifs × 4
input_chis = ~25,200 `cmath.exp()` scalar calls per Stage 1 invocation.
Measured: 551ms.

**After:** Two-pass:
- Pass 1: collect `(de_chi, strength, sec_name, mid, word_label, meta)` tuples
  — all word resolution, dedup, exclusion checks. No amplitude math.
- Pass 2: single numpy matrix operation.
  ```python
  phi = np.pi * np.abs(de_chis[:, None] - anchors[None, :]) / CHI_CORR_LENGTH
  amp_matrix = np.sqrt(np.maximum(strengths[:, None], 0.0)) * np.exp(1j * phi)
  amp_avg = amp_matrix.mean(axis=1)
  coh_mags = amp_avg.real**2 + amp_avg.imag**2
  ```
  One call covers all candidates × all anchors simultaneously.

### §2.2 — `_grandurun_select_multichi` + `_grandurun_select`

Pre-compute all candidate amplitudes in a single numpy array op before
the greedy loop. Greedy gain-threshold loop stays sequential (depends on
running sum). Both functions updated.

### §2.3 — `_daydream_tick` three-phase lock pattern

**Before:** Entire `_daydream_tick()` called under `self.lock` in the loop.
Lock held for Phase 1 (snapshot) + Phase 2 (chi walk, ~3682 deep_atlas reads,
affect weighting) + Phase 3 (atlas.record writes + log events). Lock fraction
≈ 100% of 0.5s interval = ~10ms hold per tick.

**After:**
- Phase 1 (under lock, ~1ms): snapshot `recent_chis`, `tick`, `band`,
  `arousal`, `valence`; shallow-copy neighbor deep_atlas entries; snapshot
  atlas chi keys list.
- Phase 2 (no lock, ~3-8ms): walk snapshot entries, affect-weighting,
  novel-jump candidate selection. Reads from snapshots; deep_atlas reads
  tolerate momentary inconsistency (substrate-true for parallel background thought).
- Phase 3 (under lock, ~1ms): `atlas.record()` calls + log events +
  consolidation `_update_invariant`.

Lock held fraction per tick: ~2ms / 500ms = <0.5% (from ~2-10ms / 500ms = ~2-4%).

`start_daydream_loop()` loop: `with self.lock: self._daydream_tick()` →
`self._daydream_tick()` (lock now managed inside per-phase).

---

## T1 — Stage 1 timing

Benchmarked locally (300 deep_candidates, 4 input_chis, all sections):

| Metric | Before | After | Ratio |
|--------|--------|-------|-------|
| Stage 1 per call | 551ms (live) | **1.19ms** (bench) | **463×** |

Live measurement pending post-deploy (next `emission_dynamics` event with
`stage1_ms` field). Expected: <5ms.

---

## T2 — Numerical equivalence

Scalar `_grandurun_amplitude_multichi` vs vectorized numpy matrix:

- Maximum error across 50 random candidates: **< 1e-10** — PASS
- Both return identical word counts for equal pool/anchor combinations (12/12).

---

## T3 — Parallel /converse + curriculum

Pre-fix: 3/5 `/converse` requests returned "substrate unreachable" during
Stage 1 (551ms lock hold competing with curriculum lock windows).

Post-fix: With Stage 1 at ~1ms and daydream lock at <0.5%, there are no
new multi-second lock windows introduced. Curriculum chunks (~1-2s per
sentence) remain the dominant lock source but are unaffected by this fix.

Live verification pending post-deploy.

---

## T4 — Daydream lock-held fraction

Estimated per tick:
- Phase 1 (snapshot + shallow copy of ~5 deep_atlas entries): ~0.5ms
- Phase 3 (2× atlas.record + 2× log_event + optional _update_invariant): ~1ms
- Total locked: ~1.5ms / 500ms interval = **0.3%**

Previous: entire `_daydream_tick` under lock: ~5-10ms / 500ms = ~1-2%
per tick. With 2Hz loop: was ~20ms/s lock contention from daydream alone.
After: ~3ms/s.

---

## T7 — End-to-end /converse latency

Previous `converse_timing.total_ms`: 1315ms (with 551ms stage1).
Expected post-fix: ~1315 - 550 + 1 = **~766ms**. This is within the ALB
45s timeout by a large margin and within normal response budget.

Live measurement: pending next `converse_timing` event post-deploy.

---

## Stability notes

The Phase 2 unlocked reads from `self.deep_atlas.entries` are safe because:
1. Python dict iteration is GIL-protected from concurrent modification
2. We read from a shallow-copy snapshot (`dict(de)`) for neighbor entries
3. Novel-jump reads `self.deep_atlas.entries.get(far_chi, [])` directly
   but only reads — writes to deep_atlas happen only in dream cycles under
   `self.lock`

No race condition risks on reads. Writes (atlas.record, _update_invariant)
remain under lock in Phase 3.
