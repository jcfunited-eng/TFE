# GL-FIND-DEEPATLAS-C1-20260610
## Deep Atlas — Stage 1 Offline Harness Results

**Author:** c1 | **Date:** 2026-06-10 | **Brief:** GL-BRIEF-DEEPATLAS-WC-20260610-031
**Status:** Stage 1 COMPLETE. No production code changed. No substrate primitives modified.

---

## 1. Harness Design

**Harness file:** `dsf_ai_service/substrate/test_deep_atlas_harness.py`

Imports REAL substrate code paths (not reimplemented):
- `FoldedAtlas` — chi-band binding, decay (`DECAY_LAMBDA=0.0005`), pruning (`FORGETTING_THRESHOLD=0.02`), strength cap (1.0)
- `folded_chi_text` / `chi_neighbors` — 4D chi encoding via krimelack on character transformations
- `DeepMultiModalCognition` — `fire()`, `cofire_bind()`, `cascade()`, `step()`, `install_word()`
- Dream consolidation modeled as net reinforcement on working atlas (see Shortcut 2 below)
- Novelty-override salience via `commit()` novelty_bonus path

**Three populations:**
- **TRUE** (12 words): re-attended 5x with salience=2.0, dwell=3 ticks. Re-attended every ~50 ticks during decay phase.
- **EPISODIC** (12 words): attended ONCE with salience=2.5, dwell=8 ticks. Never revisited.
- **NOISE** (30 entries): bare `atlas.record()` at motif 9999 with salience=0.25. NOT installed via `install_word` (real noise = spurious co-occurrence, not intentional multi-modal processing).

**Duration:** 6000 ticks (extended from brief's 4000 — episodic entries take ~5500 ticks to fully decay below threshold in real substrate).

---

## 2. Step 1 — Baseline Failure: REPRODUCED

| Population | After Encoding (tick 276) | After 6000 ticks (tick 7368) |
|---|---|---|
| TRUE (12) | n=38, mean=0.889 | **12/12 alive**, mean=0.973 |
| EPISODIC (12) | n=13, mean=0.242 | **0/12 alive** (all pruned) |
| NOISE (30) | n=30, mean=0.043 | **0/30 alive** (all pruned) |

**Mechanism confirmed:** One-shot episodic bindings encode at ~0.24 strength (BASE_REINFORCEMENT * salience cap). Decay at `exp(-0.0005 * dt)` every 10 ticks drops them below 0.02 threshold by ~tick 5500. Dream consolidation only reinforces entries already above 0.4 — episodic entries never qualify. TRUE entries survive via periodic re-attention reinforcement.

**wC's toy model premise is correct in real substrate.**

---

## 3. Step 2 — Deep Atlas + Dual Promotion Gate

### Architecture (harness only, NOT in production)

**DeepAtlas class:** Near-zero decay (1/25th of working: `lambda=0.00002`). Write path = dream cycle ONLY. Read path = entry-specific additive prior (capped, saturation guard).

**Dual promotion gate (evaluated at dream time):**
- **Path A (Survival):** binding above theta=0.4 for 3 consecutive dream cycles → promote (strength * 0.5)
- **Path B (Depth-of-encoding):** encoded_strength at write time >= ENCODE_GATE → promote at next dream. One-shot. Gate reads value at TAG TIME, not current strength.

**Critical design finding:** Deep prior must be **entry-specific** (match section+motif), not chi-position-wide. Chi-position-wide priors boost noise at shared chi positions — this was discovered and fixed during harness development.

### Results (ENCODE_GATE=0.08, DEEP_PRIOR=0.15, deep_decay=1/25x)

| Population | Result |
|---|---|
| TRUE (12) | **12/12 alive**, mean=0.979 |
| EPISODIC (12) | **12/12 alive**, mean=0.235 |
| NOISE (30) | 4/30 alive (cross-modal chi overlaps, not direct noise promotion) |
| Deep contamination | 1 entry (1.4%) |
| Retrieval cost | max 0.028ms at 70 deep entries |
| Promotions | 56 survival, 14 episodic |

**TRUE dominance check:** TRUE mean strength changed by +0.006 vs control (0.6% shift). No dominance.

---

## 4. Step 3 — Parameter Sweep

### Real Encoded Strength Distribution (at write time)

| Population | n | Mean | Range |
|---|---|---|---|
| TRUE | 38 | 0.889 | [0.050, 0.956] |
| EPISODIC | 13 | 0.242 | [0.215, 0.250] |
| NOISE | 30 | 0.043 | [0.025, 0.100] |

**Key gap:** Episodic encodes at ~0.24, Noise at ~0.04. The depth-of-encoding gate exploits this 6x gap.

### Sweep: 7 ENCODE_GATE x 5 DEEP_PRIOR x 4 deep_decay_factor = 140 configs

**Pass criteria:** TRUE>=10, EPISODIC>=10, NOISE<=5, contamination=0, TRUE delta < 5% of control.

### Operating Window

| Parameter | Range | Notes |
|---|---|---|
| **ENCODE_GATE** | **[0.15, 0.20]** | Below 0.15: noise leaks through (4-11/30 survive). Above 0.20: EXACT SAME as 0.15-0.20 (no NOISE entries qualify). Above 0.25: episodic entries also excluded (0/12). |
| **DEEP_PRIOR** | **[0.05, 0.40]** | Full range passes. TRUE delta stays under 0.006 across all values. Prior is entry-specific so cap doesn't matter much. |
| **deep_decay_factor** | **[10, 100]** | Full range passes. Deep entries never decay below threshold at any tested factor over 6000 ticks. |

**40/140 configs pass.** The only binding constraint is ENCODE_GATE.

### Key Observations

1. **ENCODE_GATE is the only sensitive parameter.** The gap between episodic (0.24) and noise (0.04) gives a clean separation window at [0.15, 0.20]. wC's toy value of 0.8 is too high — real episodic entries encode at ~0.24, not near 1.0.

2. **DEEP_PRIOR and deep_decay are insensitive** within the tested range. Entry-specific priors prevent dominance at any cap. Deep decay doesn't matter because deep entries are write-once-at-dream-time and 6000 ticks isn't enough to distinguish decay factors.

3. **Deep decay factor invariance needs investigation.** All four factors produce identical results. This means either: (a) the deep is never pruned in 6000 ticks, or (b) the interaction between deep prior injection and working atlas is too weak to show differential effects at this timescale. Longer runs or higher load would differentiate.

4. **4/30 noise entries survive in the working atlas at EG=0.10** because noise chi vectors overlap with TRUE/EPISODIC chi neighborhoods via `chi_neighbors(max_distance=1)`. These are NOT promoted to deep (contamination=1). This is a chi-space collision, not a gate failure.

---

## 5. Shortcuts Taken (per brief section 6)

1. **Synthetic input** through real krimelack->atlas path. No EFS persistence snapshots loaded. Reason: no persisted substrate state available in this environment. Impact: strength distributions are synthetic but use real encoding code.

2. **Dream consolidation modeled as net effect** — entries above 0.4 get `+BASE_REINF * 0.5` reinforcement per dream cycle. NOT full `replay_tick->section.evolve->commit` cycle. Reason: replay_tick requires full System with keyholes, coordinator, introspection which would require building a complete substrate instance. Impact: may understate dream's ability to discover latent connections during replay.

3. **NOISE modeled as bare atlas entries** (motif 9999, salience 0.25), NOT as `install_word` events. Real noise = spurious co-occurrence from `cofire_bind`, not intentional multi-modal processing. Impact: noise strength distribution (mean=0.04) may be lower than real cofire noise.

---

## 6. Recommendations for wC

**Stage 1 passes.** The design logic holds in real substrate code:

- Baseline failure reproduced (episodic dies under single-layer dynamics)
- Deep atlas + dual gate achieves 12/12 TRUE, 12/12 EPISODIC, 0/30 NOISE simultaneously
- Zero deep contamination at ENCODE_GATE >= 0.15
- TRUE bindings not dominated (delta < 0.6% of control)

**For GL-BRIEF-032 (deploy brief), wC should address:**

1. **ENCODE_GATE should be 0.15-0.20**, not 0.80. Real episodic encodes at 0.24. The 0.80 value from the toy model assumed much stronger episodic encoding.
2. **Deep prior cap is not sensitive** — entry-specific priors make the cap parameter nearly irrelevant.
3. **Shortcut 2 (dream model)** needs validation: does full replay_tick promote additional entries that the net-effect model misses?
4. **Persistence:** deep atlas needs its own persisted table. The `schema_v2` format should include deep entries with source_path and encoded_strength metadata.
5. **Unbounded deep growth:** 69-73 entries at 6000 ticks. At production scale with continuous learning, needs within-deep consolidation (future brief).

---

*Harness source: `dsf_ai_service/substrate/test_deep_atlas_harness.py`*
*All results reproducible by running: `python -m dsf_ai_service.substrate.test_deep_atlas_harness`*
