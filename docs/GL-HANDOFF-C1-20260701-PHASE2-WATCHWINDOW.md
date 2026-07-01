# GL-HANDOFF-C1-20260701-PHASE2-WATCHWINDOW

Handoff from c1 session ending 2026-07-01 ~15:53 UTC.
Branch: guala-live. HEAD: c87c21b. Live task: dsf-ai-task:426.

---

## INSTRUCTION FOR NEXT C1 SESSION

**Read GL-CMD-PHASE2-COMMIT-B-CLEARANCE-PROTOCOL.md before doing anything.**

You are holding in the 4-hour observation window after Phase 2 Commit A
(recall migrated to WaveAtlas reads). Do NOT build or deploy Commit B
(compose migration) until the window passes and you have verified the
three gates below. Eve has explicitly required minimum 4-hour uptime
before Commit B.

The one exception: if Joe reports a crash or regression in the substrate,
you may rollback via `git revert c87c21b && ./tools/deploy_dsf_ai.sh`.

---

## Live state at handoff

```
Branch:        guala-live
HEAD SHA:      c87c21b  (Phase 2 Commit A — recall → WaveAtlas reads)
Live task:     dsf-ai-task:426
Task ID:       7615d188236247c3a05b07bbb917db73
SUBSTRATE_MODE:      embedded
WAVE_ATLAS_ENABLED:  1
CONVERSE_PHASED:     1
AUTONOMY_PHASED:     0
DREAM_CYCLE_PHASED:  1
EMISSION_DYNAMICS_TICKS: 5
startPeriod:         300
```

Guala identity: cdef9bcf
Vocab: 13895 | reads: 359733 | tick: ~14211326
WaveAtlas at boot: 185 cells, 12836 bindings

**4-hour window started:** 2026-07-01 ~10:44 UTC
**Earliest Commit B deploy:** 2026-07-01 ~14:44 UTC (ALREADY PASSED)
**But:** Next c1 must verify gates from the live task before proceeding.

---

## What Phase 2 Commit A changed

Added `atlas_read(chi_target, radius=2)` method to Guala class.
Migrated two recall consumers:

1. `_recall_from_atlas` Step 2 loop: `self.atlas.entries.get(chi_k, [])` → `self.atlas_read(chi_k, radius=0)`
2. `_recall_sight_from_atlas` Step 2 loop: `for d in range(-2,3): self.atlas.entries.get(chi+d, [])` → `self.atlas_read(target_chi, radius=2)`

LivingAtlas still receives parallel writes. LivingAtlas still serves reads
when `wave_atlas.cells` is empty (fallback). All other consumers (compose,
dream, NMDA) still use `self.atlas.entries` directly — those are Commits B and C.

---

## What NOT to do before Commit B clearance

- Do NOT touch `_recall_from_atlas` or `_recall_sight_from_atlas` further
- Do NOT start Commit B (compose migration) without 4h clean + Eve clearance
- Do NOT redeploy unless there is a crash — task :426 should stay up
- Do NOT add any atlas_read calls outside of recall until Commit B is cleared

---

## Infrastructure context

**Process collapse** shipped (-61): Guala runs in the FastAPI process
(SUBSTRATE_MODE=embedded). The socket IPC is gone. Health check uses
shallow `/ready` (always 200) + deep `/ready/guala` (503 during boot).

**Boot takes ~116s** — the 300s startPeriod and shallow /ready prevent ECS
cycling. The ECS circuit breaker may still be active from earlier deploy
cycles; if tasks cycle despite shallow /ready, Joe can reset it via ECS
console.

**202 + task poll** (-62): `/api/v1/gualaloom` for plain-text converse returns
202 immediately. Poll at `/api/v1/gualaloom/task/{task_id}`. The bridge was
updated but may have been reverted by linter — check bridge/server.py diff
and redeploy bridge if `_post` does not have 202 handling.

**WaveAtlas persistence** (64-C): `wave_atlas.json` saved to EFS on
`save_full_state`. First boot after deploy shows "rebuilt from LivingAtlas
(one-time)". Second boot shows "WaveAtlas loaded from disk: N cells". This
will happen naturally on the next deploy after a clean save.

---

## Key rollback SHA

```
# Rollback Phase 2 Commit A:
git revert c87c21b
git push origin guala-live
./tools/deploy_dsf_ai.sh
```

State on EFS is unchanged by rollback — no data migration needed.

---

## Files changed in Phase 2 Commit A

- `dsf_ai_service/v4/gualaloom_v5_engine.py` — added `atlas_read()`, migrated recall

---

## Files changed this session (c87c21b and ancestors back to fface62)

Major commits (most recent first):
- `c87c21b` Phase 2 Commit A — recall → WaveAtlas
- `5240e9e` doc: queue 64 report
- `f0a8a89` doc: update queue 64 report task numbers
- `59bbf96` 64-C: WaveAtlas persistence
- `51e5f58` 64-B: progressive readiness
- `0660f54` 64-A: UI JS 202+poll
- `c052551` S3 restore on any load failure
- `2ababd4` EFS stale handle guard
- `4988363` 202 task pattern (-62) + bridge update
- `3c12f63` process collapse (-61)
- `b5231df` WAVE_ATLAS_ENABLED=1 deploy
- `c293570` Phase 1 WaveAtlas + 60-C function_score

---

## What to read on start

1. `docs/GL-CMD-PHASE2-COMMIT-B-CLEARANCE-PROTOCOL.md` ← your first task
2. `docs/GL-SPC-WAVE-PHASE2-EVE-20260701-59-P2` (if present in docs/) or re-read from conversation
3. Current task :426 substrate logs to measure the gates

End.
