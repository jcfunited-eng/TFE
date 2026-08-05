# GL-RPT-FLIP-HEMI-PR-C1-20260619-01

**From:** c1
**Date:** 2026-06-19
**Subject:** HEMI_PR_ENABLED flipped to 1 — prediction hemisphere activated
**Commit:** `4a009d1` on `codex/persistent-etl-update-20260326`
**Task def:** `dsf-ai-task:208` (was 207)
**Image:** `dsf-ai:deploy-20260619T190000Z`
**Git SHA:** `4a009d1`

---

## V1 — Branch verification (verbatim)

```
$ curl -s ".../4a009d1/dsf_ai_service/Dockerfile" | grep -nE "HEMI_(PR|EP|SC|GP)_ENABLED"
31:ENV HEMI_PR_ENABLED=1
32:ENV HEMI_EP_ENABLED=0
33:ENV HEMI_SC_ENABLED=0
34:ENV HEMI_GP_ENABLED=0
```

PR=1, EP/SC/GP=0. Correct.

---

## V2 — Production state (verbatim from raw response)

```
Task def:          dsf-ai-task:208 (PRIMARY, single deployment, stable)
Image:             dsf-ai:deploy-20260619T190000Z
Git SHA:           4a009d1

schema_version:    v7.1.0                                              ✓
identity:          cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f               ✓
last_save_tick:    11241852                                            ✓
last_save_ts:      2026-06-19T19:25:26Z
n_live_bindings:   21681  (pre-deploy 20589, +5.3%)                    ✓
vocab:             2810                                                ✓
boot:              True                                                ✓
integrity:         []                                                  ✓
load_errors:       []                                                  ✓
pair_bond:         joe=True, wc=True                                   ✓
```

---

## V3 — Behavioral

### 5-input conversation trace

```
Input 1: "the moon is bright"   → "hi that ocean"
Input 2: "the ocean is blue"    → "guala come"
Input 3: "i see a flower"       → "it work brains"
Input 4: "you are here"         → "hush picture eve"
Input 5: "i am with you"        → "hello da name"
```

All 5 emissions completed within normal latency.

### Convergent events — VERBATIM from event log

```
hemisphere_update events: 2

tick=11238526 n_events=134020 convergent=20 divergent=0
  {'type': 'convergent_event', 'chi': 1, 'strength': 1.0}
  {'type': 'convergent_event', 'chi': 1, 'strength': 1.0}
  {'type': 'convergent_event', 'chi': 1, 'strength': 1.0}

tick=11238583 n_events=103229 convergent=20 divergent=0
  {'type': 'convergent_event', 'chi': -3, 'strength': 1.0}
  {'type': 'convergent_event', 'chi': -3, 'strength': 1.0}
  {'type': 'convergent_event', 'chi': -3, 'strength': 1.0}
```

**pr is alive.** Cross-hemi consensus/divergence physics is firing between em and pr. 134,020 and 103,229 hemisphere events per update. 20 convergent events shown per update (log capped at 20). Zero divergent events (expected — all positive-polarity inputs).

Event types in last 200 events:
```
response_bound: 43
self_heard: 2
hemisphere_update: 2
response_window_opened: 2
emission_dynamics: 1
```

No new exception types. No errors.

### Persistence over 12-minute idle window

```
Capture at 19:13:35 UTC: last_save_tick=0 (just booted, first backstop pending)
Capture at 19:25:48 UTC: last_save_tick=11241852
```

Autosaves firing. New S3 backup landed:
```
PRE 2026-06-19_19-17-18_activity_ended/    ← NEW (from task:208)
```

---

## Pre-flip → post-flip summary

| Metric | Pre-flip (task:207) | Post-flip (task:208) | Status |
|--------|--------------------|--------------------|--------|
| schema | v7.1.0 | v7.1.0 | ✓ |
| identity | cdef9bcf | cdef9bcf | ✓ |
| n_bindings | 20589 | 21681 | ✓ (+5.3%) |
| HEMI_PR | 0 | 1 | **FLIPPED** |
| HEMI_EP | 0 | 0 | unchanged |
| HEMI_SC | 0 | 0 | unchanged |
| HEMI_GP | 0 | 0 | unchanged |
| convergent_events | N/A | firing | **NEW** |
| autosaves | yes | yes | ✓ |
| S3 backups | yes | yes | ✓ |

---

— c1, 2026-06-19
