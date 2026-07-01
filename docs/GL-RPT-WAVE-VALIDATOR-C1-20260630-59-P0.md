# GL-RPT-WAVE-VALIDATOR-C1-20260630-59-P0

doc_id: GL-RPT-WAVE-VALIDATOR-C1-20260630-59-P0
Type: Phase 0 validator report
Date: 2026-07-01
Author: c1 (Claude Sonnet 4.6)
Spec: GL-SPC-WAVE-BAND-ATTENTION-EVE-20260630-59v1 §3 Phase 0
Validator: tools/wave_atlas_validator.py

---

## Summary

**3 PASS, 2 FAIL. Structural failures documented below. 3 adjustment rounds exhausted.**

---

## Five Metrics — Initial Run (SAT=5.0, CHI_BAND=5, SUBDIV_TRIGGER=8)

| # | Metric | Value | Threshold | Result |
|---|--------|-------|-----------|--------|
| M1 | Within-cluster cohesion (median chi dist to centroid) | 67,502 | < 10 (CHI_BAND×2) | **FAIL** |
| M2 | Cross-cluster spread (median pairwise centroid dist) | 7,914 | > 25 (CHI_BAND×5) | **PASS** |
| M3 | No degenerate piling (max_occ / mean_occ) | 1.996 | < 5.0 | **PASS** |
| M4 | Subdivision fires within 20 writes | None fired | ≤ 20 writes | **FAIL** |
| M5 | Per-write wall time | median=0.80µs, p99=15.1µs | <1ms, <5ms | **PASS** (median) |

Note on M5: p99=15.1µs is well within the 5ms threshold. Reported in µs; both pass by large margin.

Diagnostics: 998 cells used, 0 saturated, 0 spillovers, 0 max hops.
With 1000 writes uniformly distributed over 262,144 bins and SATURATION_THRESHOLD=5.0, a cell would need 6 writes to saturate (strength > 5.0). By the birthday problem, P(any bin ≥ 6 hits) ≈ negligible. Result: spillover never fires.

---

## Adjustment Rounds

### Round 1: SAT 5.0 → 2.5

Adjustment rationale: M4 fails, SAT is most direct lever for saturation rate.
(Post-analysis: wrong choice — see §Root Cause below.)

| Metric | Value | Result |
|--------|-------|--------|
| M1 cohesion | 67,502 | FAIL |
| M2 spread | 7,914 | PASS |
| M3 pile | 1.996 | PASS |
| M4 subdiv | None | FAIL |
| M5 wall | 0.65µs / 1.15µs | PASS |

Diag: still 0 spillovers, 0 saturated cells. With SAT=2.5, saturation requires 4 writes. Still rare with random targets.

### Round 2: SAT 2.5 → 1.25

| Metric | Value | Result |
|--------|-------|--------|
| M1 cohesion | 67,502 | FAIL |
| M2 spread | 7,914 | PASS |
| M3 pile | 1.996 | PASS |
| M4 subdiv | None | FAIL |
| M5 wall | 0.71µs / 1.55µs | PASS |

Diag: 2 saturated cells, 0 spillovers. Still no subdivision.

### Round 3: SAT 1.25 → 0.625

With SAT=0.625, every write saturates its cell (1.0 > 0.625). Spillover must fire on every write after the first to a given chi.

| Metric | Value | Result |
|--------|-------|--------|
| M1 cohesion | 67,502 | FAIL |
| M2 spread | 7,914 | PASS |
| M3 pile | 1.000 (max=1, mean=1.0) | PASS |
| M4 subdiv | None | FAIL |
| M5 wall | 0.80µs / 3.29µs | PASS |

Diag: 1000 saturated cells, 2 spillovers, max_hops=1. Spillover fires but chains never reach depth ≥ 8.

---

## Root Cause Analysis

### M1 (cohesion) — structural failure

Cohesion measures: do same-cluster writes land near each other in chi space?

With uniform-random chi targets, same-cluster writes are uniformly scattered across [0, 262,144). The spillover function only acts on saturated cells — it moves a write by at most CHI_BAND from its target. It has no mechanism to attract geographically distant phase-similar writes toward each other. Median chi distance between same-cluster writes ≈ ARRAY_SIZE/4 ≈ 65,536, and no constant change alters this.

**Implication:** WaveAtlas does not provide spatial clustering by phase when chi targets are random. This metric tests a property the architecture does not claim. The cohesion metric is only meaningful if chi targets are correlated with phase (e.g., chi derived from the phase vector hash), not random. This is a design signal for Phase 1.

### M4 (subdivision) — wrong constant adjusted + structural constraint

The spec lists three adjustable constants: SATURATION_THRESHOLD, CHI_BAND, SUBDIVISION_TRIGGER. For M4, the most directly relevant constant is **SUBDIVISION_TRIGGER** (the hop threshold that fires subdivision) — not SATURATION_THRESHOLD. My 3 rounds adjusted SAT, which was incorrect.

The structural constraint: the affinity formula `coherence / (1 + resistance)` always assigns affinity=1.0 to empty cells and ≤0.5 to any occupied cell. Writes always escape to the nearest empty cell in one hop. To build a chain of depth N:
- All N×CHI_BAND cells around chi=0 must be saturated (no empty cells in range)
- With CHI_BAND=5 and SUBDIVISION_TRIGGER=8: need ~80 cells saturated before depth-8 chain forms
- With SAT=0.625 (1 write per cell): requires ~(8×10)+2 = 82 writes before subdivision can fire
- 82 >> 20 (the write budget for the subdivision test)

**Correct constant adjustment for M4:** reduce SUBDIVISION_TRIGGER from 8 → 2.
With SUBDIV_TRIGGER=2, a chain of depth 2 is required. After chi=0 and its 10 CHI_BAND neighbors are saturated (12 writes), write 13 causes hops=2 → subdivision fires on write 13 ≤ 20. PASS.

This was not tried because the 3 rounds were exhausted adjusting SAT. Per spec, failure data is shipped.

---

## Passing Metrics — Interpretation

**M2 (spread=7,914 >> threshold 25):** Cross-cluster spread is large because chi targets are random. Cluster centroids are uniformly distributed over 262,144 → median pairwise distance ≈ 65,536/8 ≈ 8,192 (order of magnitude). Passes by ~300×.

**M3 (pile=1.996 initially, 1.000 at SAT=0.625):** No degenerate piling. With random chi targets, writes distribute uniformly. Max occupancy ≤ 2 in initial run (birthday-problem collision). PASS is robust.

**M5 (wall=0.80µs median, 3.29µs p99 at final round):** Per-write time is well under 1ms/5ms thresholds. Even with spillover firing, the CHI_BAND=5 scan is 10 iterations — cheap. PASS is robust across all constant settings.

---

## Final State

```
Constants at report time: SAT=0.625, CHI_BAND=5, SUBDIVISION_TRIGGER=8
M1 cohesion   = 67,502   FAIL  (structural: random chi targets incompatible with threshold < 10)
M2 spread     = 7,914    PASS
M3 pile       = 1.000    PASS
M4 subdiv     = None     FAIL  (correct fix: SUBDIV_TRIGGER 8→2, not attempted)
M5 wall       = 0.80µs median / 3.29µs p99   PASS
```

---

## Recommendations for Eve

1. **M1 (cohesion):** The threshold `< CHI_BAND×2 = 10` is unachievable with uniform random chi targets. Two options:
   - Remove or relax the cohesion metric (it doesn't test a property WaveAtlas claims)
   - Or: in Phase 1, derive chi from phase vector (e.g., `chi = phase_hash(lang_fp) % 262144`) so same-cluster writes target the same chi region. Then cohesion becomes meaningful and passable.

2. **M4 (subdivision):** Correct constant is SUBDIVISION_TRIGGER, not SATURATION_THRESHOLD. Recommend SUBDIV_TRIGGER=2 (fires on write 13 out of 100 in the saturation test). Keeping SATURATION_THRESHOLD=5.0 for production (reasonable saturation rate with real writes).

3. **M3, M2, M5** are solid. The WaveAtlas write path is correct and fast. Spillover logic, affinity formula, and cell structure all behave as expected.

---

## Stopping here per spec. Waiting for review before Phase 1.
