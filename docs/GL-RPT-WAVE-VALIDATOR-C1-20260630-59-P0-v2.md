# GL-RPT-WAVE-VALIDATOR-C1-20260630-59-P0-v2

doc_id: GL-RPT-WAVE-VALIDATOR-C1-20260630-59-P0-v2
Type: Phase 0 validator report (v2 — Eve corrections applied)
Date: 2026-07-01
Author: c1 (Claude Sonnet 4.6)
Spec: GL-SPC-WAVE-BAND-ATTENTION-EVE-20260630-59v1 §3 Phase 0
Replaces: GL-RPT-WAVE-VALIDATOR-C1-20260630-59-P0.md
Validator: tools/wave_atlas_validator.py

---

## Result: ALL 5 PASS

Constants used: `SAT=5.0  CHI_BAND=5  SUBDIVISION_TRIGGER=8` (unchanged from spec §1.2)

---

## Five Metrics

| # | Metric | Value | Threshold | Result |
|---|--------|-------|-----------|--------|
| M1a | Within-cluster cohesion — stage 1 (1000 writes) | 21.5 | < 100 | **PASS** |
| M1b | Within-cluster cohesion — stage 2 (500 saturating) | 9.8 | < 200 | **PASS** |
| M2 | Cross-cluster spread (median pairwise centroid dist) | 64,575 | > 25 | **PASS** |
| M3 | No degenerate piling (max_occ / mean_occ) | 2.772 (max=6, mean=2.165) | < 5.0 | **PASS** |
| M4 | Subdivision fires under sustained pressure | write 277 of 500 | < 500 | **PASS** |
| M5 | Per-write wall time | 1.87µs median / 40.85µs p99 | <1ms / <5ms | **PASS** |

---

## Eve Corrections Applied

### Correction 1 — M1 chi correlated with phase

Per Eve's dispatch: uniform-random chi targets put same-cluster writes 65K apart on average; CHI_BAND=5 spillover cannot span that gap. Fixed:

- Each cluster is assigned a `cluster_center_chi` drawn uniform random from [0, 262144)
- Each experience: `chi_target = (cluster_center_chi + round(N(0,30))) % 262144`
- Phase vector unchanged: `pv = cluster_base + N(0, 0.1)` (complex)
- Stage 2 added: 500 additional writes (50 per cluster) all targeting `cluster_center_chi`
- M1 threshold updated to stage1 < 100, stage2 < 200

### Correction 2 — M4 sustained pressure test

Per Eve's dispatch: 20-write budget was insufficient to build a depth-8 saturation chain. Fixed:

- 500 writes all targeting `chi=131072`
- Phase vector: `bases[0]` exactly, identical for every write (no noise)
- Pass condition: subdivision fires before write 500

---

## Metric Notes

### M1: cohesion tightens under saturation (stage 2 < stage 1)

Stage 1 cohesion = 21.5 (writes scattered with std=30 around center). Stage 2 cohesion = 9.8 (writes concentrated exactly at center). Under saturation, same-cluster writes trigger spillover and the affinity formula routes them to neighbors that already contain same-cluster phase content (coherence ≈ 1.0), which are closer to the center than writes that escaped to empty outlier cells. The spillover is working correctly: phase-coherent writes accumulate in a tight neighborhood.

Main atlas diagnostics: 693 cells occupied, 94 saturated, 455 spillovers, max 2 hops.

### M3: pile ratio 2.772 expected

Cluster centers are hit by both stage-1 (biased toward center) and stage-2 writes. Cells at the center accumulate more writes than outlier cells, producing pile_ratio > 1. 2.772 is well below the 5.0 threshold and reflects the intended usage pattern (frequently-experienced content resides in dense cells).

### M4: subdivision fires on write 277, max_hops=16, total_subdivisions=224

Analytic prediction (written before running): 277 writes. Actual: 277.

Chain path: chi=131072 → 131067 → 131062 → 131057 → 131052 → 131047 → 131042 → 131037 → 131032 (9 saturated cells). Each ring of CHI_BAND=5 cells takes 6×10=60 or 6×5=30 writes to saturate (ring 0: 6, ring 1: 60, rings 2-7: 30 each). Total to saturate 8 deep rings: 6+60+30×6=246. Write 247 starts chain of depth 8 but the ring-8 band (131032..131036) is still unsaturated — so _hop at commit = 7, just below SUBDIVISION_TRIGGER=8. Writes 247-276 (30 writes) saturate ring-8. Write 277: chain 131072→…→131032 (saturated)→131027 (empty), _hop=8 ≥ 8 → SUBDIVISION FIRES.

After subdivision fires, writes continue and hit progressively deeper chains (max_hops observed = 16, total 224 subdivision events across all remaining writes). The trigger is live and persistent.

### M5: wall time 1.87µs / 40.85µs p99

1.87µs median is well within 1ms. The p99 of 40.85µs reflects occasional saturated-cell paths (10-iteration CHI_BAND scan × multiple recursive hops). All within threshold. Stage-2 writes (which hit saturated clusters) drive the p99 up versus stage-1, but still ~100× under the 5ms bound.

---

## Spillover correctness verified

The affinity formula `coherence / (1 + resistance)` behaves as intended:

1. Empty cells always preferred over occupied (affinity=1.0 vs ≤0.5). Writes find the least-contested neighbor.
2. Among occupied neighbors, lower resistance (fewer prior writes) preferred. Distributes load.
3. Under identical phase (M4 test): resistance is the only discriminator. Writes fill cells in round-robin order, building compact saturated regions that eventually force deep chains.
4. Under correlated-phase (M1 corrected test): same-cluster phase content has coherence≈1.0 with new writes. Same-cluster occupied cells are preferred over cross-cluster occupied cells when resistance is equal. Stage-2 writes cluster tighter (9.8) than the initial scatter (21.5), proving the formula routes by phase under pressure.

No pathological behavior observed: no infinite recursion, no degenerate piling, no hot-cell monopoly.

---

## Stopping here per spec. Waiting for Phase 1 dispatch.
