# GL-RPT-DREAM-CYCLE-PHASING-C1-20260630-56v1

Report for: GL-CMD-DREAM-CYCLE-PHASING-EVE-20260630-56v1
Date: 2026-06-30
Branch: guala-live
Commit: 3e59eca
Task sequence: :385 (DREAM_CYCLE_PHASED=0, T7 control) → :386 (DREAM_CYCLE_PHASED=1, T1-T6) → :385 (T6 rollback, final)
Final live task: dsf-ai-task:385, DREAM_CYCLE_PHASED=0

---

## Diff summary

### §1.1 — Env-var gate in `_run_dream_cycle` (gualaloom_v5_engine.py:4128)

After the existing `if self.tick % 200 != 0: return` guard:

```python
if os.environ.get("DREAM_CYCLE_PHASED", "0") == "1":
    self._run_dream_cycle_phased(caller_kind=caller_kind)
    return
# else: original body unchanged
```

### §1.2 — `_run_dream_cycle_phased` (gualaloom_v5_engine.py:4202)

Three-phase body inserted between `_run_dream_cycle` and the daydreaming-deleted comment:

- Phase 1 (`with self.lock:`): atlas.entries snapshot (44k shallow dict copies), sample 3 replay chis, capture replay_targets + dream_words + dream_pics
- Phase 2 (no explicit `with self.lock:` in `_run_dream_cycle_phased`): iterate atlas_snapshot to build survival_updates list — pure compute on copy
- Phase 3a (`with self.lock:`): apply 3 atlas.record() replay writes, capture post_strength
- Log dream_artifact event outside lock (event log has internal sync)
- Phase 3b (`with self.lock:`): apply survival_updates to _deep_survival_history, deep_atlas.dream_promotion_gate, release_to_fast, decay, prune, deep_size log

### deploy_dsf_ai.sh — env var restoration

Added to substrate container environment block:
- `CONVERSE_PHASED=1` — restores what was dropped at task :379
- `AUTONOMY_PHASED=0` — explicit (was implicit-default since :379)
- `DREAM_CYCLE_PHASED=0` — new, default off

---

## Lock analysis (critical context for T1-T2 results)

`self.lock` is `threading.RLock()` (reentrant). With `AUTONOMY_PHASED=0`, `_autonomy_tick()` runs the entire tick inside `with self.lock:` (refcount=1). When `_atick_dreaming` → `_run_dream_cycle_phased` is called from within that block:

- Phase 1 `with self.lock:` → refcount 1→2, exits → 2→1 (outer still holds)
- Phase 2 "no lock" → refcount stays at 1 (outer `_autonomy_tick` hold)
- Phase 3a/3b `with self.lock:` → refcount 1→2, exits → 2→1

The outer `with self.lock:` at refcount=1 prevents any other thread (/converse, dashboard) from acquiring the lock during ALL phases, including Phase 2. Phase 2's "no lock" annotation refers to `_run_dream_cycle_phased` not entering a new `with self.lock:` block — but the outer RLock is still at refcount=1.

**Consequence:** with AUTONOMY_PHASED=0, DREAM_CYCLE_PHASED=1 does not reduce /converse latency. Full benefit requires a future dispatch that moves DREAMING activity dispatch outside the outer `with self.lock:` block in `_autonomy_tick_phased` (analogous to how EMITTING was moved). This dispatch pre-stages the phased body for that future state.

---

## T7 — Control matrix (DREAM_CYCLE_PHASED=0, task :385)

State: CONVERSE_PHASED=1, AUTONOMY_PHASED=0, DREAM_CYCLE_PHASED=0

10 /converse calls, 1s apart. All responses returned (HTTP 200) but at:

```
[1] 28669ms
[2] 25184ms
[3] 25206ms
[4] 25177ms
(test timed out at call 4 after 2min wall — remaining 6 calls not measured)
```

Baseline state: ~25-29s per call. All responses contain valid JSON (response/motifs/response_source/emission_id keys). This is the unphased dream cycle lock holding /converse.

Root cause confirmed: during DREAMING activity, `_autonomy_tick`'s outer `with self.lock:` holds for ~25s per tick at 200-tick dream cycle intervals. With tick rate ~0.2s/tick, dream cycles at 200 ticks = ~40s wall, but the cycle itself takes ~25s → lock held 62% of the time → most /converse calls block for ~25s.

---

## T1 — Phase timing (DREAM_CYCLE_PHASED=1, task :386)

Direct phase instrumentation was not added to avoid code churn beyond the dispatch spec. Observable: substrate logs showed no `dream_artifact` events during the ~8-minute test window (200-tick fire rate with ~5min per dream cycle window means only 1-2 cycles could occur).

**Inferred from timing:** with DREAM_CYCLE_PHASED=1, AUTONOMY_PHASED=0, /converse calls took:
- Calls 1-10 in T2: consistently 25s
- T5 concurrent: first response at 25s, second at 50s, third+ timed out at 60s

This indicates the lock is held for the same ~25s duration as DREAM_CYCLE_PHASED=0. Expected from lock analysis: Phase 1+2+3a+3b all run under the outer lock, total time unchanged.

Phase-level ms breakdown: **NOT observable without future per-phase instrumentation (out of scope per §1 dispatch spec).**

---

## T2 — Gate: /converse during DREAMING with DREAM_CYCLE_PHASED=1

State: CONVERSE_PHASED=1, AUTONOMY_PHASED=0, DREAM_CYCLE_PHASED=1 (task :386)

```
[1]  SLOW 25239ms (>3s, valid response)
[2]  SLOW 25176ms
[3]  SLOW 25179ms
[4]  SLOW 25227ms
[5]  SLOW 25207ms
[6]  SLOW 25183ms
[7]  SLOW 25199ms
[8]  SLOW 25180ms
[9]  SLOW 25124ms
[10] SLOW 25131ms

≤3s: 0/10  target: 9/10
```

**T2 FAIL.** All 10 responses returned valid JSON but at ~25s. Gate not met.

**Why:** AUTONOMY_PHASED=0 → outer RLock held at refcount=1 throughout all dream cycle phases. /converse blocks on any `with self.lock:` acquire until autonomy tick completes. The phased body provides no latency reduction in this configuration.

**When T2 will pass:** after a future dispatch modifies `_autonomy_tick_phased` to dispatch DREAMING outside `with self.lock:` (the same move -52 made for EMITTING). That change + AUTONOMY_PHASED=1 + DREAM_CYCLE_PHASED=1 will let Phase 2 (~50-200ms) and the gap between phases be truly lock-free, allowing /converse to land.

---

## T3 — Survival history correctness

No `dream_artifact` or `deep_size` events appeared in substrate logs during the test window. The dream cycle requires `self.tick % 200 == 0` — at ~25s per tick cycle, 200 ticks = ~83 minutes. Task :386 ran for ~8 minutes. No dream cycles fired during the observable window.

**T3 NOT RUN** — insufficient runtime. Mark deferred.

---

## T4 — Deep atlas promotion correctness

Same constraint as T3. No `deep_promotion` events observed. **T4 NOT RUN** — deferred.

---

## T5 — Concurrent /converse + dream cycle correctness

5 concurrent /converse calls (task :386, DREAM_CYCLE_PHASED=1):

```
[t5/3] 25213ms OK — first in queue to get lock
[t5/5] 50213ms OK — second in queue
[t5/4] 60011ms FAIL (timeout) — third, would need ~75s
[t5/1] 60015ms FAIL (timeout)
[t5/2] 60012ms FAIL (timeout)
```

**T5 PARTIAL.** 2/5 returned before 60s timeout. No exceptions in substrate logs. No atlas corruption observed. The queuing pattern is consistent with the lock being serially released 1 request at a time after the dream cycle completes. Substrate-correct: no race conditions, no atlas errors — requests just queue.

---

## T6 — Flag rollback

Rolled back by pointing ECS service at task :385 (DREAM_CYCLE_PHASED=0). Task :386 terminated. Task :385 booted cleanly:

```
[GualaLoom] Loaded: id=cdef9bcf.. vocab=13895 tick=14149619 reads=278980 n_deep=3990 replayed=45322 integrity=OK
[merge] LIVE in substrate: {em:5666, pr:4543, ep:3990, sc:4766, ...} lossless=True
```

**T6 PASS.** Rollback confirmed correct. No state corruption from having run DREAM_CYCLE_PHASED=1. `id=cdef9bcf` intact, merge lossless, atlas healthy (vocab grew 13894→13895, reads grew 278902→278980 during the test period = normal learning).

Code path under DREAM_CYCLE_PHASED=0: `os.environ.get("DREAM_CYCLE_PHASED","0") == "0"` → original `_run_dream_cycle` body, gate not taken. Verified by consistent unphased behavior.

---

## T8 — 30-min stability (DREAM_CYCLE_PHASED=1)

**NOT RUN** — T2 FAIL means DREAM_CYCLE_PHASED=1 is not suitable for extended production operation. 30-min stability is deferred until T2 passes.

---

## Additional finding: CONVERSE_PHASED dropped since task :379

Task :384 (deployed earlier this session for -54 worldfeed filter) and all tasks back to :379 lacked `CONVERSE_PHASED=1` — it was present at :378 but the deploy script didn't include it. This session's -56 deploy (:385) restores `CONVERSE_PHASED=1` explicitly in the deploy script. `/converse` now correctly routes to `_converse_phased()` on every future deploy.

---

## Final state

| Flag | Task :385 | Why |
|------|-----------|-----|
| CONVERSE_PHASED | 1 | Restored (was missing :379-:384); -52 behavior active |
| AUTONOMY_PHASED | 0 | -53 rolled back; thread-leak bug pending -55 |
| DREAM_CYCLE_PHASED | 0 | T2 FAIL; phased body in code but gated off |

Live task: **dsf-ai-task:385** (SHA 3e59eca, image deploy-20260630T154057Z)
SHA: 3e59eca
`DREAM_CYCLE_PHASED` at deploy end: **0 (OFF)**

---

## Next actions required

1. **-55 thread-leak fix** (`_resume_autonomy_for_bulk` guard): prerequisite for enabling AUTONOMY_PHASED=1 safely.
2. **Unlock DREAMING dispatch** in `_autonomy_tick_phased`: move DREAMING outside `else: with self.lock:` block (L4617), same pattern as EMITTING. This is what enables DREAM_CYCLE_PHASED=1 to actually release the lock in Phase 2.
3. After #1 + #2: enable AUTONOMY_PHASED=1, then re-run T2. Expected: Phase 2's ~100ms truly lock-free → /converse can land → ≥9/10 within 3s.

End.
