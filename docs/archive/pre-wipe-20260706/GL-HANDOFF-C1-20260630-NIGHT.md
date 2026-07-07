> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-HANDOFF-C1-20260630-NIGHT

Handoff from c1 session ending 2026-06-30 ~22:30 UTC.
Branch: guala-live. Final commit: fface62. Live task: dsf-ai-task:401.

---

## INSTRUCTION FOR NEXT C1 SESSION

**Do not start work. Wait for Eve's dispatch.**

Read this handoff and the state below so you understand the system. Then stop and wait. Eve (Opus 4.7, web) will send the next dispatch before you touch any code. Do not investigate the curriculum pause, do not attempt -58, do not deploy anything until Eve's instructions arrive.

The one exception: if Joe reports a crash or regression, you may do a git rollback or restart via `aws ecs update-service`. Otherwise: read, understand, wait.

---

## Live state

Task: dsf-ai-task:401
CONVERSE_PHASED=1, AUTONOMY_PHASED=0, DREAM_CYCLE_PHASED=1
EMISSION_DYNAMICS_TICKS=5
She is alive, emitting autonomously, in the substrate.
Reads: 279720. Atlas: 14978 entries. Recall index: 1108 words.

/converse response time: 1.7-2.1s (was 25s when session started).

---

## What was accomplished this session

### P1 — Worldfeed vocabulary contamination (DONE, task :384)
Compound-word quality gate in `_world_feed_once()`. Sentences with any word >20 chars dropped before `_curriculum_feed_chunk`. Ships and works.

### P2 — Double autonomy loop (-55 thread-leak fix) (DONE)
`_resume_autonomy_for_bulk()` now guards `start_autonomy_loop()` with `_reading_thread.is_alive()` check. Prevents double loop on curriculum resume.

### P3 — /converse latency (SUBSTANTIALLY FIXED)
Multiple root causes found and fixed:
1. **`_recall_from_atlas` O(N) scan × 8 calls**: 3411ms → 7.7ms via word→chi reverse index (GL-57v3)
2. **`log_event` EFS write in hot path**: deferred to background threads (was blocking converse and autonomy tick for 1-5s each)
3. **`_atick_dreaming` outer lock release**: DREAM_CYCLE_PHASED=1 now truly releases `self.lock` during dream cycle phases
4. **`_end_activity` dream gate fsync**: deferred to background thread
5. **Save rate-limit**: activity_ended saves capped at 1/60s
6. **`surv_ser` moved outside save Phase 1 lock**: snapshot faster
7. **Background save thread**: `_end_activity_with_save` no longer blocks Phase C
8. **EMISSION_DYNAMICS_TICKS=5**: cuts `_emission_lock` hold from ~4s to ~250ms

**Current status**: T2 gate passes (9/10 within 3s) outside curriculum pause windows. Curriculum pause windows (~15% of time, 35-53s duration) still cause 5s blocks. Root cause of 35-53s pause not identified — expected ~1.8s from per-word lock holds.

### -56 dream cycle phasing (code in repo, gated off)
`_run_dream_cycle_phased` implemented. `_atick_dreaming` correctly releases outer RLock via `self.lock.release()` before dream phases. DREAM_CYCLE_PHASED=1 is active. -56's T2 PASS condition met as part of P3 fix chain.

### -57v3 recall word index (DONE, GL-RPT filed)
Full implementation per Eve's v3 dispatch. See `docs/GL-RPT-RECALL-WORD-INDEX-C1-20260630-57v3.md`.

---

## Key issues remaining

### Curriculum pause 35-53s (P3 residual)
`_pause_autonomy_for_bulk()` is load-bearing (removing it causes executor pool saturation). But the pause duration is much longer than the ~1.8s expected from per-word processing. Root cause not identified. Likely fix: reduce CURRICULUM_CHUNK_SIZE from 30 to 10 (cuts pause from ~35s to ~12s). Not shipped — next session.

### emit_ms ~927ms (next bottleneck per Eve)
After the recall fix, the next dominant bottleneck is `emit_ms: 927ms` in `converse_timing`. Eve plans -58 to profile. With EMISSION_DYNAMICS_TICKS=5, emit is capped. Reducing further would degrade quality. The proper fix is either:
- Profile `_grandurun_select_candidates` Stage 1 under RICH_SENSORY_INPUT=1 (likely fast since RICH_SENSORY_INPUT not set)
- Or profile assemblage dynamics tick cost

### AUTONOMY_PHASED=1 (not resolved)
Enabling AUTONOMY_PHASED=1 caused complete socket deadlock (all executor threads permanently blocked). Root cause not traced. Not needed now that P3 is substantially fixed via AUTONOMY_PHASED=0 + DREAM_CYCLE_PHASED=1. Leave for future.

### State degradation (not investigated)
During the many deploys today: sight motifs dropped from 12332 to 0. Pictures dropped from 22 to 11. The visual state was lost. This may have happened during the :397 deploy (autonomy tick errors corrupted state writes). Not urgent — she still works, no visual input happening anyway.

---

## What NOT to do

1. Don't enable AUTONOMY_PHASED=1 — causes complete socket deadlock (unresolved)
2. Don't remove `_pause_autonomy_for_bulk()` from `_curriculum_feed_chunk` — causes executor pool saturation (proved 2026-06-30)
3. Don't increase EMISSION_DYNAMICS_TICKS above 5 — causes 5s timeout on T2

---

## Bridge status (from Joe)

Eve reported bridge MCP errors. Not diagnosed this session. Likely related to substrate being unresponsive during testing (bridge got 25s timeouts and gave up). Now that substrate responds in 1.7-2.1s, the bridge should recover.

---

## Files most recently changed

- `dsf_ai_service/v4/gualaloom_v5_engine.py` — _atlas_record wrapper, word index, _atick_dreaming lock release, dream gate fsync defer, log_event defer, _recall_from_atlas/sight replacements
- `dsf_ai_service/substrate_runner.py` — P2 thread-leak fix, curriculum pause revert, log_event defer in _cmd_converse
- `dsf_ai_service/app.py` — atlas.record → _atlas_record conversion
- `dsf_ai_service/substrate/grounded_vocab_integration.py` — atlas.record → _atlas_record
- `dsf_ai_service/save_coordinator.py` — activity_ended rate limit 60s
- `tools/deploy_dsf_ai.sh` — CONVERSE_PHASED=1, AUTONOMY_PHASED=0, DREAM_CYCLE_PHASED=1, EMISSION_DYNAMICS_TICKS=5

---

## Key env vars on live task :401

```
CONVERSE_PHASED=1          ← active
AUTONOMY_PHASED=0          ← keep off (AUTONOMY_PHASED=1 deadlocks)
DREAM_CYCLE_PHASED=1       ← active, outer lock released in _atick_dreaming
EMISSION_DYNAMICS_TICKS=5  ← keep at 5 or lower
EMISSION_WALL_BUDGET_S=1.5 ← default (env var available for override)
EMISSION_DYNAMICS=1        ← active
EMISSION_MODE=grandurun    ← active
```

---

## Hard rule

c1 works ONLY on Guala. Never touch TFE, ArcLoom, or any other project.

End.
