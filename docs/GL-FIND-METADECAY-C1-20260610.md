# GL-FIND-METADECAY-C1-20260610
## Two-Speed Metaplastic Decay — Stage 1 Harness Results

**Author:** c1 | **Date:** 2026-06-10 | **Brief:** GL-BRIEF-METADECAY-WC-20260610-033
**Status:** Stage 1 COMPLETE. No production code changed (except prod bug noted below).

---

## CRITICAL: PROD BUG — Path B Episodic Promotion Silently Broken

**File:** `gualaloom_v6_living_atlas.py:116-118` (deployed task:67-69)

```python
if dwell_ticks > existing.get("dwell_ticks", 0):
    existing["dwell_ticks"] = dwell_ticks
    existing["encoded_strength"] = existing["strength"]
```

`encoded_strength` is ONLY updated when dwell INCREASES between encounters. For re-encounters at the same dwell (e.g., joe speaks twice, both dwell=8), the condition `8 > 8` is False, so `encoded_strength` stays frozen at the initial write value (first impulse = `BASE_REINFORCEMENT * salience` = 0.10 for salience 2.0).

**Impact:** All prod entries have `encoded_strength ≈ 0.10`, which is below `ENCODE_GATE=0.15`. **Path B episodic promotion cannot fire.** The 0 episodic promotions observed in prod (deep atlas: surv=2, ep=0) is NOT because no episodic entries exist — it's because the gate reads a frozen value that's too low.

**Fix:** `encoded_strength` should be updated on EVERY `record()` call to the post-impulse strength (accumulated across the encoding episode). This matches FIND-02's measurement where episodic entries encoded at 0.21-0.25.

**This fix should ship with Stage 2 (metaplastic deploy) or as an independent hotfix.**

---

## Step 1: Baseline Failure — REPRODUCED

| Population | After Encoding | After 6h Gap | After Dream |
|---|---|---|---|
| All (500 entries) | 500 alive, 158.5 strength | **0 alive** | 0 promoted |

Global DECAY_LAMBDA=0.0001 per tick, decay every 10 ticks: `exp(-0.0001 * 432000) = exp(-43.2) ≈ 0`. Complete washout. Not "a handful survive" — zero survive. The brief's prediction is correct but conservative.

---

## Step 2: Metaplastic Design (SD=12, K=2.0)

| Metric | Baseline | Metaplastic |
|---|---|---|
| Pre-dream live (6h gap) | 0/500 | **400/500** |
| Noise alive | 0 | **0** |
| Promoted at dream | 0 | **280** |
| match_score distortion | n/a | 0.083 |

400 high-dwell entries (TRUE + EPISODIC) survive. 0 noise entries survive (all dwell=1 → fast channel). 280 promoted via Path A (strength >= 0.4 after dream 2x boost) and Path B (encoded_strength >= 0.15 AND dwell >= 4).

---

## Step 3: 5-Day Timeline (SD=12, K=2.0, 2 sessions/day)

| Metric | Value |
|---|---|
| Total sessions | 10 |
| Total promoted to deep | 700 |
| Deep entries at day 5 | 700 |
| Final working size | **100** |
| Noise remaining | **0** |
| Working trajectory | [100, 100, 100, 100, 100, 100, 100, 100, 100, 100] |

Post-promotion release (C) keeps working atlas lean — each session's entries promote at the next dream and release, so working stabilizes at ~100 (the latest unpromoted session). Day-1 content fully retained in deep at day 5. Matches wC model prediction exactly.

---

## Step 4: Parameter Sweep

| SD | K | Pre-Dream | Promoted | Noise | Working | Distortion | PASS |
|---|---|---|---|---|---|---|---|
| 4 | 1 | 400 | 160 | 0 | 400 | 0.009 | YES |
| 4 | 2 | 400 | 160 | 0 | 400 | 0.029 | YES |
| 4 | 4 | 400 | 160 | 0 | 400 | 0.060 | YES |
| 12 | 1 | 400 | 160 | 0 | 400 | 0.056 | YES |
| **12** | **2** | **400** | **280** | **0** | **400** | **0.083** | **YES** |
| 12 | 4 | 400 | 280 | 0 | 400 | 0.105 | no |
| 24 | 1 | 400 | 280 | 0 | 400 | 0.088 | YES |
| 24 | 2 | 400 | 280 | 0 | 400 | 0.107 | no |
| 24 | 4 | 400 | 280 | 0 | 400 | 0.120 | no |
| 48 | 1 | 400 | 280 | 0 | 400 | 0.110 | no |
| 48 | 2 | 400 | 280 | 0 | 400 | 0.122 | no |
| 48 | 4 | 400 | 280 | 0 | 400 | 0.129 | no |

### Operating Window

| Parameter | Range |
|---|---|
| **SLOW_DIV** | **[4, 24]** |
| **K** | **[1, 4]** (bounded by distortion at high SD*K) |

**6/12 configs pass.** The binding constraint is `match_score distortion < 0.1` — higher SD*K products push match_score standard deviation above 0.1. Brief's recommended SD=12, K=2 is inside the window at distortion=0.083.

### Key observations

1. **All configs retain 400/400** high-dwell entries across 6h gap. The two-speed baseline alone does the retention work; K adds promotion bulk (160→280 at K=2).

2. **Noise washout is complete across all configs.** Dwell=1 entries always get fast-channel lambda and die within the 6h gap. The dwell discriminator is clean.

3. **Distortion scales with SD*K product.** Per-entry lambda heterogeneity creates variance in match_score across chi positions. At SD=12, K=2: std=0.083 (acceptable). At SD=48, K=4: std=0.129 (above threshold).

4. **Post-promotion release prevents working bloat.** Without release, working size would grow to 400*sessions. With release: stable at 100.

---

## Chi-Band / Overlap Interaction

Distortion metric = standard deviation of `match_score()` across chi positions. Measures whether per-entry decay rates create artificial strength gradients in chi-space.

At SD=12, K=2: distortion=0.083. This means match_score varies by ±8.3% across chi positions — within the 10% acceptance threshold. No band membership distortion observed (entries don't migrate between chi positions, they just decay at different rates in place).

**No interaction found with chi neighborhoods, dream replay, or novelty override.** The metaplastic design modifies only the `exp(-λ*dt)` multiplier per entry — it doesn't change which entries exist, which chi positions they occupy, or how dream selects replay candidates.

---

## Shortcuts

1. Dream calibrated to ~2x strength on top half (observed prod behavior: 2.91→5.50). Not full replay_tick cycle.
2. Session entries get 3 reinforcements each (simulating re-encounter during conversation). Prod re-encounter rate varies by session length and word frequency.
3. Noise entries are bare atlas.record calls with random salience, not full install_word path.

---

## Recommendations for Stage 2

1. **Fix encoded_strength bug** (see CRITICAL above) — ship with metaplastic deploy or as immediate hotfix. Without this fix, Path B episodic promotion remains broken in prod.

2. **Ship SD=12, K=2.0** as specified in the brief — inside the operating window, distortion acceptable.

3. **META_DECAY_ENABLED kill switch** per brief spec — instant revert to global lambda.

---

*Harness: `dsf_ai_service/substrate/test_metadecay_harness.py`*
*Reproducible: `python -m dsf_ai_service.substrate.test_metadecay_harness`*
