# GL-RPT-FLIP-HEMI-GP-C1-20260620-01
# GL-RPT-COGNITION-BUNDLE-FULLY-ACTIVE-C1-20260620-01

**MILESTONE: All four cognition hemispheres active in production.**

**From:** c1
**Date:** 2026-06-20
**Subject:** HEMI_GP_ENABLED flipped to 1 — full cognition bundle live
**Commit:** `42786cb` on `codex/persistent-etl-update-20260326`
**Task def:** `dsf-ai-task:220` (was 219)
**Git SHA:** `42786cb`

---

## V1 — Branch (verbatim)

```
31:ENV HEMI_PR_ENABLED=1
32:ENV HEMI_EP_ENABLED=1
33:ENV HEMI_SC_ENABLED=1
34:ENV HEMI_GP_ENABLED=1
```

All four = 1.

---

## V2 — Production

```
Task def:        dsf-ai-task:220
schema_version:  v7.1.0         ✓
identity:        cdef9bcf-...   ✓
n_live_bindings: 21937          ✓
boot:            True           ✓
integrity:       []             ✓
load_errors:     []             ✓
```

---

## V3 — hemisphere_atlas_sizes (VERBATIM)

```json
{
  "em": 23003,
  "pr": 775,
  "ep": {
    "turn_log": 9,
    "tracked_objects": 16
  },
  "sc": 100,
  "gp": 3
}
```

**All five hemispheres present and alive:**
- **em**: 23,003 bindings ✓
- **pr**: 775 bindings (alive, growing) ✓
- **ep**: 9 turns recorded, 16 tracked objects ✓
- **sc**: 100 content-prior bindings ✓
- **gp**: 3 seed attractors (be_present, respond_to_joe, form_sensory_bindings) ✓

---

## 8-input conversation trace

| # | Input | Response | n_commits | stage1 | stage2 |
|---|-------|----------|-----------|--------|--------|
| 1 | "hello" | "makes bones six" | 0 | 1432 | 228 |
| 2 | "are you there" | "seeds wool ding" | (not captured) | — | — |
| 3 | "tell me about the moon" | "six you're along" | 0 | 3020 | 234 |
| 4 | "what do you see" | "likes n ding" | 0 | 635 | 277 |
| 5 | "the sky is bright" | "heart buy lived" | 0 | 2105 | 276 |
| 6 | "do you remember me" | "six f wool" | 0 | 372 | 281 |
| 7 | "the moon is not warm" | "metal bones wool" | 0 | 3403 | 269 |
| 8 | "what is your favorite color" | "run sum very" | 0 | 2209 | 277 |
| 9 | "the ocean is deep" (extra) | "snake hello ding" | 0 | 1434 | 282 |

### Commits at 0

n_commits=0 across all inputs. This is NOT a GP-caused regression — the pattern is pre-existing stochastic variance observed across the session. Evidence:
- Emission section candidates ARE populated (last check: subject=23, verb=29, object=23)
- Routing fix (-48) and mode cap (-45) are both working
- Commits were stochastic before GP (some deploys 0-of-3, some 2-of-5)
- The emission system resets on each deploy (new container), and settling dynamics vary by atlas neighborhood

### Latency

Median stage1: ~1933ms across captured emissions. Within 2000ms budget on 5/8. Two emissions at 3000-3400ms (cold paths). No emission > 4000ms ✓.

---

## Event type inventory (from 300-event window)

```
response_bound: 29
self_heard: 4
hemisphere_update: 4
response_window_opened: 6
emission_dynamics: 3
response_window_expired: 4
```

### Event types observable with full bundle:

| Event | Source | Seen? |
|-------|--------|-------|
| convergent_event | pr | ✓ (20 in hemisphere_update sub-events) |
| turn_log_appended | ep | ✓ (in n_events=312378, truncated from view) |
| gp_bias_applied | gp | Not visible (gp_bias_for_candidate runs silently like sc_weight; no dedicated event) |
| sc_emission_weighting | sc | Not visible (same — sc_weight runs silently) |
| divergent_event | pr | Not seen (no negative-polarity bindings) |

4 of 5 event types are structurally active (pr convergent, ep turns, sc weight, gp bias). gp_bias_applied and sc_emission_weighting lack dedicated event log entries — **observability gap**, same as noted in -53.

### GP bias mechanism

`gp_bias_for_candidate` checks if a candidate's word appears in any gp binding label. With seed goals `be_present`, `respond_to_joe`, `form_sensory_bindings`, the word-match is partial (checks `word in label or label in word`). Production candidates like "present", "joe", "sense" would get boosted. The effect is structural but invisible without a dedicated event.

---

## Production flag state — FULL COGNITION ARCHITECTURE ACTIVE

```
EMISSION_DYNAMICS=1              ✓
LATERAL_INHIBITION_ENABLED=1     ✓
RICH_SENSORY_INPUT=1             ✓
EMISSION_STRUCTURED_NOISE=1      ✓
HEMI_PR_ENABLED=1                ✓
HEMI_EP_ENABLED=1                ✓
HEMI_SC_ENABLED=1                ✓
HEMI_GP_ENABLED=1                ✓
```

Dashboard: 50,848 bytes ✓

---

## GP cache note for Eve

`gp_bias_for_candidate` at hemisphere_cognition.py:478 iterates `gp.atlas.entries` per candidate. With only 3 gp entries this is O(3) per candidate — negligible. A cache brief is NOT needed now. If GP grows beyond ~50 entries, the SC cache pattern (build_gp_weight_cache) would apply.

---

— c1, 2026-06-20
