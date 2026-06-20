# GL-RPT-CACHE-SC-WEIGHTS-C1-20260620-01

**From:** c1
**Date:** 2026-06-20
**Subject:** SC weight cache — stage1 latency cut from 4.7s to 1.2s median
**Commit:** `9801ecd` on `codex/persistent-etl-update-20260326`
**Task def:** `dsf-ai-task:219` (was 218)
**Git SHA:** `9801ecd`

---

## V1 — Branch (verbatim)

```
386:def build_sc_weight_cache(guala):
405:def sc_weight_for_candidate(candidate, guala, _cache=None):
407:    If _cache is provided (from build_sc_weight_cache), uses O(1) dict lookup.
602:    Pass sc_cache from build_sc_weight_cache for O(1) SC lookup.
605:        w = sc_weight_for_candidate(candidate, guala, _cache=sc_cache)
```

---

## V2 — Production

```
Task def:        dsf-ai-task:219
schema_version:  v7.1.0         ✓
identity:        cdef9bcf-...   ✓
n_live_bindings: 21827          ✓
boot:            True           ✓
```

hemisphere_atlas_sizes:
```json
{"em": 21952, "pr": 732, "ep": {"turn_log": 5, "tracked_objects": 7}, "sc": 100}
```
All hemispheres healthy. ✓

---

## V3 — Latency comparison (verbatim)

| Emission | Input | Pre-cache stage1 | Post-cache stage1 | n_commits |
|----------|-------|-------------------|-------------------|-----------|
| 1 | "hello" | 3673ms | **1307ms** | 0 |
| 2 | "the moon is bright" | 4714ms | **2478ms** | **2** |
| 3 | "tell me a story" | 5292ms | **581ms** | 0 |
| 4 | "what do you remember" | — | (not captured) | — |
| 5 | "i see the ocean" | — | **1150ms** | **1** |

- **Median stage1: ~1228ms** (was ~4700ms) — **74% improvement**
- 3 of 4 captured emissions under 2000ms ✓
- No emission over 3000ms ✓
- n_commits ≥ 1 on 2 of 4 captured ✓ (input 2: n_commits=2, input 5: n_commits=1)
- Dashboard: 50,848 bytes ✓

---

## Tests (13/13 green)

Test 13 verifies cached weights match uncached for all chi values.

---

— c1, 2026-06-20
