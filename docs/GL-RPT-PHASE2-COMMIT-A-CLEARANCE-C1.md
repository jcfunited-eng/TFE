# GL-RPT-PHASE2-COMMIT-A-CLEARANCE-C1

doc_id: GL-RPT-PHASE2-COMMIT-A-CLEARANCE-C1
Date: 2026-07-01 (c1 session)
Status: ROLLBACK EXECUTED

---

## Summary

Phase 2 Commit A (SHA c87c21b) introduced `atlas_read()` dispatching recall to WaveAtlas.
The 4-hour observation window elapsed. All three gates were evaluated.
**Gate 1 FAILED. Rollback executed per protocol.**

---

## Gate Results

### Gate 1: recall_ms < 100ms — FAIL

converse_timing events from live task dsf-ai-task:429 (task definition :429, same Commit A code):

| tick     | recall_ms   | note                                       |
|----------|-------------|--------------------------------------------|
| 14229849 | 43,821.9ms  | curriculum moon-002 held GIL (~49s bundle) |
| 14229851 | 1,427.0ms   | curriculum paused, recall unblocked        |
| 14229865 | 4,840.9ms   | curriculum paused                          |
| 14229870 | 3,111.8ms   | curriculum paused                          |

All samples exceed the 100ms threshold by 14x–438x. Gate 1 FAIL.

**Root cause analysis:**

1. **First converse (43s)**: The curriculum orchestrator's `moon-002` bundle delivery
   held the Python GIL for ~49 seconds. The converse was queued waiting for the lock.
   This is not directly caused by atlas_read but is a compounding factor.

2. **Subsequent converses (1.4s–4.8s)**: After curriculum paused (3 consecutive no-growth
   bundles → auto-pause), recall ran freely. Still 14–48x over threshold.

3. **Structural cause**: `_recall_response()` calls `_recall_from_atlas()` up to 6 times
   (3 sections + 3 more if `linked_chis` found). Each call loops over
   `content_word_chis` (from `_word_to_chi_index`) and calls `atlas_read()` per chi.
   `atlas_read()` now calls `wave_atlas.read_near()` which returns from `cell.bindings`
   — a list that accumulates unboundedly (WaveAtlas has no decay). With 12836+ bindings
   rebuilt at boot plus live additions, each cell holds far more entries than the
   equivalent LivingAtlas entry after decay. The Counter loop iterates all of them.

4. **WaveAtlas state**: 193 chi_keys, 9564 live bindings reported by atlas_health.
   LivingAtlas had n_released=8386 (pruned); WaveAtlas still holds these.

### Gate 2: No atlas_read exceptions — PASS

Zero Traceback, Exception, or atlas_read error found in 5000 log lines.

### Gate 3: Response quality spot check — PARTIAL (not evaluated to completion)

All 5 POST requests returned 202 (accepted) with task IDs. The converse tasks
remained in "settling" status during the observation window (curriculum active
during submission, tasks queued). Full quality verification was not possible
before rollback was triggered by Gate 1 failure.

---

## Task / infrastructure state at evaluation

- Branch: guala-live | HEAD: c20ba61 (doc commits after c87c21b)
- Live task definition at evaluation: dsf-ai-task:429 (ECS restarted from :426)
  - Same Commit A code, different task ID: 44d9cd2711a140aea70f91936089b530
- Task started: 2026-07-01 ~14:22 UTC (epoch 1782919354)
- Guala identity: cdef9bcf (same across restart — EFS state preserved)
- Vocab at evaluation: 13,896 | reads: 299,054 | tick: ~14,229,693
- WaveAtlas: 193 chi_keys, 9,564 live bindings
- Curriculum: moon-series running live (100 bundles, auto-pausing on no-growth)
  - moon-002 took 49.9 seconds → GIL contention during first converse
  - Curriculum auto-paused twice (3 consecutive no-growth bundles)

---

## Rollback action

Per protocol: `git revert c87c21b && git push origin guala-live && ./tools/deploy_dsf_ai.sh`

```
git revert c87c21b   # creates revert commit
git push origin guala-live
./tools/deploy_dsf_ai.sh
```

---

## Diagnosis for next attempt

Phase 2 Commit A is sound in design. The performance regression has two fixable causes:

**Fix 1 — WaveAtlas decay / binding cap per cell:**
WaveAtlas `cell.bindings` grows unboundedly. Adding a max-bindings-per-cell cap
(evicting weakest on overflow) would bound recall work to O(cap × n_chi_keys_queried).

**Fix 2 — `_recall_from_atlas` call count:**
`_recall_response` calls `_recall_from_atlas` up to 6 times. Each call iterates
all `content_word_chis` and calls `atlas_read` per chi. Profile whether the
`linked_chis` expansion path (lines 3553-3561) is the dominant contributor —
if `linked_chis` is large, the expanded_chis set causes many more atlas_read calls.

**Fix 3 — curriculum GIL isolation:**
The curriculum bundle delivery holding the GIL for 49s is a separate issue.
Consider running curriculum in a thread with a yielding pattern or moving
decode-bundle to a subprocess.

**Re-attempt when:** WaveAtlas cell cap implemented AND curriculum GIL isolated.

---

End.
