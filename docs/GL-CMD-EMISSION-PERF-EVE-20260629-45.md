# GL-CMD-EMISSION-PERF-EVE-20260629-45

doc_id: GL-CMD-EMISSION-PERF-EVE-20260629-45
Type: Implementation command (single dispatch, single ship)
Date: 2026-06-29
Author: Eve (Opus 4.7, web)
Prereq: GL-CMD-COMPOSER-MULTIANCHOR-EVE-20260629-43 (SHA caa60a1, task :370) shipped
Blocks: GL-CMD-SUSTAINED-SPEECH-EVE-20260629-44 (draft, not shipped; this dispatch must land first)

---

## 1. Two issues, both blocking

Per c1 report on -43 (GL-RPT-COMPOSER-MULTIANCHOR-C1-20260629-43):

**Issue 1.** `_grandurun_select_candidates` (gualaloom_v5_engine.py:248) executes ~25,200 `cmath.exp()` calls per emission attempt (300 candidates × 7 sections × 3 motifs × 4 input_chis, typical). Stage 1 timing: **551ms blocking on `self.lock`**. ALB drops concurrent requests during the window. This is why bridge calls fail repeatedly during emission and curriculum activity.

**Issue 2.** The daydream loop from -42 holds `self.lock` for the entire chi-neighborhood scan + `atlas.record()` cycle. At 2 Hz, with the scan reading from `self.deep_atlas.entries` (read-only), this blocks /converse round-trips and bridge calls for the scan duration too.

Both are correctness-of-architecture issues — the substrate is currently single-lock and that lock is held for inappropriately long stretches.

**Why this blocks -44**: -44 adds emission chaining + dynamic cooldown. Both increase emission frequency. More emissions × 551ms each = substrate becomes mostly-unavailable. Must fix perf first.

---

## 2. Changes

### 2.1 Numpy-vectorize Stage 1 amplitude computation

In `_grandurun_select_candidates` (L248-308), replace the per-candidate scalar `_grandurun_amplitude_multichi` call (L288) with a single numpy vectorized batch.

Refactor structure:

```python
def _grandurun_select_candidates(input_chis, deep_candidates, sections,
                                 input_words_set, top_k=200):
    import numpy as _np
    
    _multi_input_chis = input_chis if input_chis else [0]
    input_chi_arr = _np.array(_multi_input_chis, dtype=_np.float64)
    
    # First pass: collect viable candidates WITHOUT amplitude computation.
    # Build flat lists for vectorization.
    pending = []  # list of dicts pending amplitude computation
    seen = set()  # (section, motif) dedup
    
    for de, co, clarity in deep_candidates:
        de_chi = de.get("chi", 0)
        for sec_name in co:
            sec_co = co[sec_name]
            if not sec_co:
                continue
            top_in_sec = _heapq.nlargest(GRANDURUN_POOL_K, sec_co.items(),
                                         key=lambda x: float(x[1]))
            for mid_str, strength in top_in_sec:
                mid = int(mid_str)
                sec = sections.get(sec_name)
                if sec is None or mid >= len(sec.modes):
                    continue
                _, _, word_label = sec.modes[mid]
                if (not word_label
                        or word_label.lower() in input_words_set):
                    continue
                key = (sec_name, mid)
                if key in seen:
                    continue
                seen.add(key)
                pending.append({
                    "chi": de_chi,
                    "section": sec_name,
                    "motif": mid,
                    "word": word_label,
                    "strength": float(strength),
                    "source": de.get("source", "corpus"),
                    "arousal": de.get("arousal", 0.5),
                    "valence": de.get("valence", 0.0),
                    "surprise": de.get("surprise", 0.0),
                    "polarity": de.get("polarity", 1.0),
                    "sensory_refs": de.get("sensory_refs", []),
                })
    
    if not pending:
        return []
    
    # Second pass: vectorized amplitude computation
    chis_arr = _np.array([p["chi"] for p in pending], dtype=_np.float64)
    strengths_arr = _np.array([p["strength"] for p in pending], dtype=_np.float64)
    
    # Phase matrix: shape (M, N) where M=candidates, N=input_chis
    # phi[i,j] = pi * |chi_i - input_chi_j| / CHI_CORR_LENGTH
    phi_matrix = _np.pi * _np.abs(
        chis_arr[:, None] - input_chi_arr[None, :]
    ) / CHI_CORR_LENGTH
    
    # Amplitudes per (M, N): sqrt(strength) * exp(i*phi)
    sqrt_strengths = _np.sqrt(_np.maximum(strengths_arr, 0.0))
    amp_per_input = sqrt_strengths[:, None] * _np.exp(1j * phi_matrix)
    
    # Average over input dimension: shape (M,)
    amp_avg = amp_per_input.mean(axis=1)
    coh_mag_arr = _np.abs(amp_avg) ** 2
    
    # Attach coherent_magnitude to each pending dict
    for i, p in enumerate(pending):
        p["coherent_magnitude"] = float(coh_mag_arr[i])
    
    pending.sort(key=lambda c: -c["coherent_magnitude"])
    return pending[:top_k]
```

Mathematical equivalence: each candidate's amplitude is `mean(sqrt(strength) * exp(i*phi_n))` across n input_chis. Numpy matrix op produces identical values to the scalar loop, up to floating-point precision.

### 2.2 Vectorize Stage 2 selectors

`_grandurun_select` (L100, single-anchor) and `_grandurun_select_multichi` (added by -43) both have per-iteration amplitude calls inside the greedy loop. The greedy selection must remain sequential (decisions depend on running sum), but amplitudes can be pre-computed in one numpy batch before the loop.

For `_grandurun_select_multichi(candidates, input_chis)`:

```python
def _grandurun_select_multichi(candidates, input_chis):
    import numpy as _np
    pool = sorted(candidates, key=lambda c: -c[1])
    if not pool:
        return [], 0.0
    
    # Pre-compute all amplitudes via vectorized op
    input_chi_arr = _np.array(input_chis if input_chis else [0], dtype=_np.float64)
    chis = _np.array([c[0] for c in pool], dtype=_np.float64)
    strengths = _np.array([c[1] for c in pool], dtype=_np.float64)
    
    phi = _np.pi * _np.abs(chis[:, None] - input_chi_arr[None, :]) / CHI_CORR_LENGTH
    sqrt_str = _np.sqrt(_np.maximum(strengths, 0.0))
    amp_per_input = sqrt_str[:, None] * _np.exp(1j * phi)
    amps = amp_per_input.mean(axis=1)  # shape (M,) complex
    
    # Greedy selection — sequential, but amps are precomputed
    chosen_amps = []
    chosen_words = []
    last_coh = 0.0
    running_sum = 0.0 + 0.0j
    for i, (_, _, word) in enumerate(pool):
        amp = amps[i]
        new_sum = running_sum + amp
        new_coh = abs(new_sum) ** 2
        gain = new_coh - last_coh
        if gain > MIN_GAIN_THRESHOLD:
            chosen_words.append(word)
            chosen_amps.append(amp)
            running_sum = new_sum
            last_coh = new_coh
        if len(chosen_words) >= MAX_COMPOSITION_LEN:
            break
    return chosen_words, last_coh
```

Same pattern for `_grandurun_select` — pre-compute amplitudes against the single target_chi as a single numpy op, then greedy loop.

### 2.3 Daydream lock release pattern

Restructure `_daydream_tick` (in the engine, added by -42) into three phases — short lock for read snapshot, lock-free for traversal, short lock for writes.

```python
def _daydream_tick(self):
    """One pass of parallel associative surfacing.
    
    Lock structure (after -45):
    - Phase 1 (under lock): snapshot section commits → recent_chis
    - Phase 2 (no lock): chi-neighborhood traversal, candidate gathering
    - Phase 3 (under lock): atlas.record() writes + event logging
    
    Phase 2 reads self.deep_atlas.entries (defaultdict) without lock.
    Possible momentary inconsistency if a write happens concurrently;
    acceptable for substrate-physical parallel thinking — daydream
    is allowed to walk through slightly stale views.
    """
    
    # ===== Phase 1: snapshot under lock =====
    with self.lock:
        recent_chis = []
        for sec in self.sections.values():
            for c in sec.commits[-10:]:
                recent_chis.append(c["chi"])
        # Snapshot needs/atlas references for later use
        # (band is constant, no snapshot needed)
        current_arousal = self.needs.arousal() * 0.3
        current_valence = self.needs.valence() * 0.3
        current_tick = self.tick
        atlas_band = self.atlas.band
    
    if not recent_chis:
        return
    
    seed_chi = recent_chis[current_tick % len(recent_chis)]
    
    # ===== Phase 2: traversal without lock =====
    # Read-only access to deep_atlas.entries; reads may see momentarily
    # inconsistent state but that's substrate-physical for parallel thought.
    associated = []
    for d in range(-atlas_band, atlas_band + 1):
        # .get() on defaultdict returns default if missing; thread-safe read
        entries = self.deep_atlas.entries.get(seed_chi + d, [])
        for de in entries:
            co = de.get("co_occurrence", {})
            if not co:
                continue
            best_sec = None
            best_mid = None
            best_w = 0.0
            for sec_name, motif_dict in co.items():
                if not motif_dict:
                    continue
                top_mid = max(motif_dict, key=motif_dict.get)
                top_w = motif_dict[top_mid]
                if top_w > best_w:
                    best_w = top_w
                    best_sec = sec_name
                    best_mid = int(top_mid)
            if best_sec is not None:
                associated.append((best_sec, best_mid, best_w, de["chi"]))
    
    if not associated:
        return
    
    # ===== Extensions A/B/C (from -42) — same phase split =====
    # Novel jump computation: read-only, do outside lock
    import random as _random
    novel_write = None  # (sec, mid, chi, word_label, w) if novel jump fires
    if _random.random() < 1.0 / max(2, atlas_band):
        chi_keys = list(self.atlas.entries.keys())  # snapshot keys, may be stale
        if chi_keys:
            min_distance = 5 * atlas_band
            far_candidates = [c for c in chi_keys if abs(c - seed_chi) >= min_distance]
            if far_candidates:
                far_chi = far_candidates[current_tick % len(far_candidates)]
                for de in self.deep_atlas.entries.get(far_chi, []):
                    co = de.get("co_occurrence", {})
                    if not co:
                        continue
                    far_best = None
                    far_w = 0.0
                    for sec_name, motif_dict in co.items():
                        if motif_dict:
                            mid_str = max(motif_dict, key=motif_dict.get)
                            if motif_dict[mid_str] > far_w:
                                far_w = motif_dict[mid_str]
                                far_best = (sec_name, int(mid_str))
                    if far_best is not None:
                        far_sec, far_mid = far_best
                        if far_sec in self.sections and far_mid < len(self.sections[far_sec].modes):
                            _, _, far_label = self.sections[far_sec].modes[far_mid]
                            novel_write = (far_sec, far_mid, far_chi, far_label, far_w)
                    break
    
    # Affect-weighted sort: needs current_v/current_a snapshot
    # (already snapshot in Phase 1 via current_arousal/current_valence at /0.3)
    # Apply Extension B sorting here outside lock — math only
    # ... (keep existing Extension B logic, using snapshot values) ...
    
    # Select top association for surface write
    associated.sort(key=lambda x: x[2], reverse=True)
    top_sec, top_mid, top_w, top_chi = associated[0]
    
    # Resolve word_label outside lock
    word_label = ""
    if top_sec in self.sections:
        sec = self.sections[top_sec]
        if top_mid < len(sec.modes):
            _, _, word_label = sec.modes[top_mid]
    
    # Decide if consolidation side effect fires this tick
    do_consolidate = (current_tick % (atlas_band * 10) == 0)
    
    # ===== Phase 3: writes under lock =====
    with self.lock:
        # Surface write
        self.atlas.record(
            section=top_sec, motif=top_mid, chi=top_chi,
            tick=self.tick,
            salience=top_w,
            dwell_ticks=1,
            arousal=current_arousal,
            valence=current_valence,
            surprise=0.0,
            source="daydream",
        )
        if word_label:
            self._log_substrate_event("daydream_surface",
                seed_chi=seed_chi, surfaced_chi=top_chi,
                section=top_sec, word=word_label,
                strength=round(top_w, 3))
        
        # Novel jump write (if any)
        if novel_write is not None:
            far_sec, far_mid, far_chi, far_label, far_w = novel_write
            self.atlas.record(
                section=far_sec, motif=far_mid, chi=far_chi,
                tick=self.tick, salience=far_w, dwell_ticks=1,
                arousal=current_arousal, valence=current_valence,
                surprise=0.5, source="daydream",
            )
            self._log_substrate_event("daydream_novel",
                seed_chi=seed_chi, far_chi=far_chi,
                near_word=word_label, far_word=far_label,
                far_strength=round(far_w, 3))
        
        # Consolidation side effect
        if do_consolidate:
            for de in self.deep_atlas.entries.get(top_chi, []):
                if de.get("section") == top_sec and de.get("motif") == top_mid:
                    self.deep_atlas._update_invariant(de, top_chi, self.atlas)
                    self._log_substrate_event("daydream_consolidate",
                        chi=top_chi, section=top_sec, motif=top_mid)
                    break
```

The lock release pattern: snapshot the values needed at top, traverse without lock, take lock again for writes. Phase 2 traversal is read-only against `defaultdict` and `dict` — Python's GIL plus structural safety of these types makes the reads acceptable for substrate-true parallel thinking even if a write happens concurrently.

---

## 3. Tests

### T1 — Stage 1 timing reduction

Pre-deploy timing of `_grandurun_select_candidates`: ~551ms per emission attempt (per -43 c1 report).
Post-deploy expected: < 5ms per emission attempt.

Instrument the function with timing at entry/exit. Average over 20 emission attempts. Expected: 100×+ speedup.

### T2 — Mathematical equivalence

For 5 representative emission scenarios, capture the pre-vectorization Stage 1 candidate list and the post-vectorization candidate list. Confirm:
- Same candidates (same `(section, motif)` tuples).
- `coherent_magnitude` values match within 1e-10 (floating-point precision).
- Sort order identical.

If sort order differs even with mathematically equivalent values (due to floating-point), confirm differences are negligible (< 1e-9 in magnitude) and don't change downstream behavior.

### T3 — Bridge availability under load

Run a curriculum drive (5-10 /listen sentences over 30 seconds) AND a series of /converse calls in parallel (5 calls over 30 seconds). Measure: how many /converse calls succeed vs. fail/timeout. Pre-deploy: most fail (substrate locked during 551ms Stage 1 windows). Post-deploy: most should succeed.

Also confirm bridge tools (`guala_status`, `guala_say`) reachable consistently during this same window.

### T4 — Daydream lock window measurement

Instrument `_daydream_tick`: measure (a) total tick duration, (b) lock-held duration. Pre-deploy: lock held ~entirety of tick. Post-deploy: lock held only during Phase 1 snapshot (microseconds) and Phase 3 writes (microseconds for atlas.record + log).

Lock-held fraction should drop from ~100% to < 5% per daydream tick.

### T5 — Daydream behavior unchanged

Same `daydream_surface`, `daydream_novel`, `daydream_consolidate` event rates and content as pre-deploy. The substrate-true behavior is preserved; only the lock pattern changes.

### T6 — Substrate stability

After 30 min: no exceptions, no atlas corruption, no race condition symptoms. Vocab/atlas growth normal. Emission output (post -43) at same length/quality.

### T7 — End-to-end live emission round-trip

Send /converse from bridge while curriculum is running. Pre-deploy: bridge unreachable for ~half the time. Post-deploy: bridge consistently reachable. End-to-end round-trip latency for /converse should drop from current 500-1500ms to < 100ms.

---

## 4. Rollback

§2.1 / §2.2: revert numpy refactor back to scalar loop. Pure restoration, no state to migrate.

§2.3 daydream lock pattern: revert to whole-tick lock if race conditions appear in T6.

---

## 5. Reporting

c1 produces `GL-RPT-EMISSION-PERF-C1-20260629-45.md` with:
- Diff summary for §2.1, §2.2, §2.3.
- T1: pre/post timing numbers, sample size 20.
- T2: numerical equivalence verification on 5 scenarios.
- T3: success rate of parallel /converse + curriculum.
- T4: lock-held fraction per daydream tick, pre vs post.
- T7: end-to-end /converse round-trip latency, sample size 10.
- Final SHA, task number.

---

## 6. Out of scope

- Fine-grained locking (per-section locks, per-organ locks). Single `self.lock` retained.
- Atomicity guarantees on daydream Phase 2 reads. Treating momentary inconsistency as substrate-acceptable per "parallel thinking" framing.
- `MIN_GAIN_THRESHOLD` / `CHI_CORR_LENGTH` substrate derivation (still flagged from -43; not changed here).
- Sustained speech architecture (-44) — explicitly held until this dispatch lands and T3/T7 confirm bridge availability is restored.
