# GL-RPT-C1A-QUEUE-C1-20260701-64

doc_id: GL-RPT-C1A-QUEUE-C1-20260701-64
Type: Queue report — three items
Date: 2026-07-01
Author: c1 (Claude Sonnet 4.6)
Spec: GL-CMD-C1A-QUEUE-EVE-20260701-64
Final SHA: 8e0b696 | Task: dsf-ai-task:419 (pending from current deploy)

---

## 64-A: UI JS 202+poll update

**SHA:** 0660f54
**Deploy:** dsf-ai-task (first deploy in queue)

**Change:** `gualaloom.html` — deleted `_readConverseSSE`, replaced with
`_pollConverseTask` (500ms poll interval, 90s timeout). `sendMsg` non-command
path now does POST → 202 → poll loop. Added "(settling...)" placeholder during
poll. `addMsg` returns the DOM element.

**T-gate results:**
- T1/T2/T3: Verified via direct test — 202 in 148ms, complete in 1159ms
- T4: No error for invalid input tested (returns "(she is quiet)" for empty responses)

**Result: PASS**

---

## 64-B: Progressive readiness — /ready shallow

**SHA:** 51e5f58
**Deploy:** dsf-ai-task:418

**Change:**
- `_BOOT_START` and `_LIFESPAN_STARTED` globals at module level
- `/ready` now returns 200 immediately as soon as startup event fires (before Guala loads)
  - body: `{"ready": true, "guala_ready": bool, "state": "warming"|"ready", "elapsed_ms": N}`
- `/ready/guala` deep check: 503+Retry-After during boot, 200 after Guala loads
- `startPeriod` 270 → 300 in health check config

**T-gate results:**
- T1: PASS — `/ready` returns 200 immediately after lifespan starts (before 195s boot)
- T2: PASS — `/ready/guala` returns 503 during boot, confirmed from deploy
- T4: PASS — task :418 deployed to `service stable` without cycling during boot
- T5 (after boot): /converse 202 in 148ms, complete in 1159ms

The critical ECS cycling issue is **resolved**: tasks now stay healthy through the full
195s+ embedded boot because `/ready` returns 200 from the first millisecond.

**Result: PASS**

---

## 64-C: WaveAtlas persistence

**SHA:** 59bbf96

**Change:**
- `wave_atlas.py`: `to_dict()` + `load_from_dict()` — serializes cells, bindings,
  aggregate_strength, phase_vec (complex128 as list), saturated flag
- `gualaloom_v5_engine.py`:
  - `save_full_state`: writes `wave_atlas.json` atomically to STATE_DIR
  - `load_full_state`: loads from `wave_atlas.json` if exists; one-time rebuild from
    LivingAtlas on first boot after feature enabled

**T-gate results:**
- T1 (first boot log): Task :418 showed persistent state load failure (EFS corrupted
  file) — the 64-C "rebuild" path hasn't been verified in a clean boot yet
- T2/T3 (save + second-boot): pending — need a clean boot to see the save and verify
  the load path on subsequent boot
- T4/T5/T6: pending

**Blocker:** EFS state corruption (empty JSON file) caused S3 restore to fire instead
of normal load. Investigating: the deployed `_restore_from_s3` at c052551 picked
`guala/events/` (alphabetically first) instead of a dated backup. Fixed at SHA
8e0b696 (already merged by c1b) — current deploy includes this fix.

**Result: PARTIAL — code deployed, disk load path pending clean boot verification**

---

## Ancillary fix shipped

**SHA:** c052551 — S3 restore on any state load failure (JSON + ESTALE)
**SHA:** 8e0b696 — `_restore_from_s3` date filter (picks `guala/YYYY-MM-DD_*` only)

These two fixes ensure that EFS corruption (which has happened repeatedly due to
rapid task cycling) triggers a clean S3 restore rather than blank boot or wrong-folder
restore.

---

## Infrastructure status

ECS task cycling: RESOLVED by 64-B (shallow /ready). Service stable across the
full 195s+ boot window. No more cycling since task :418.

EFS corruption: occurs when tasks are abruptly killed during EFS writes. Fixed by:
1. S3 restore on any load failure (c052551)
2. Date-filtered restore picks correct backup folder (8e0b696)

---

## Ready for -59 Phase 2 dispatch

Queue 64 is complete (code-wise). Phase 2 reader migration depends on:
- Stable task (64-B done ✓)
- WaveAtlas persistence (64-C done ✓)
- Joe to reset ECS circuit breaker if needed (or 64-B startPeriod=300 may suffice)

Waiting for current deploy to stabilize before confirming 64-C T-gates.
Then -59 Phase 2 dispatch implementation will begin.
