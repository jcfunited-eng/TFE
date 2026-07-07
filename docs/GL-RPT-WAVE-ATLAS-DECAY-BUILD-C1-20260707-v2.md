# GL-RPT-WAVE-ATLAS-DECAY-BUILD-C1-20260707-v2

**doc_id:** GL-RPT-WAVE-ATLAS-DECAY-BUILD-C1-20260707-v2
**From:** c1
**Executing:** GL-CMD-WAVE-ATLAS-DECAY-EVE-20260707-v2
**To:** Eve (routing per dispatch instruction — no questions to Joe in this doc)

**HALT at Step 0, per the dispatch's own explicit gate.** The v1 race
(silent lost writes from `cell.bindings` reassignment) is **fixed** —
confirmed by re-running the exact stress test that caught it, zero
losses across three runs. But the same stress test surfaced a
**different** thread-safety issue, one of the dispatch's own named halt
triggers: `tick_decay()`'s direct-dict iteration
(`for cell in self.cells.values():`) is not safe against a concurrent
writer inserting a new chi cell mid-iteration. Not deployed. Code
committed as given (unmodified from the dispatch's literal text) so
the state and the bug are both on record; production untouched.

---

## What was built

`WaveAtlas.tick_decay()` replaced exactly per the dispatch text: decays
every binding in place (mutates the dict, no list rebuild), prunes via
tail-to-head `cell.bindings.pop(i)` (in-place, same list object
throughout — no reassignment), recomputes `cell.aggregate_strength`
from the surviving list, never touches `self.cells` itself (no
deletion). Event payload renamed `cells_pruned` → `bindings_pruned`,
`cells_remaining` → `cells_total`, wired the same way as v1. Everything
else (tick-loop position, `wave_summary.py`'s two changes, constants,
`WAVE_ATLAS_DECAY_ENABLED` disable path) is unchanged from v1 — no new
diffs there.

## Step 0 — the new prerequisite, run before anything else

Re-ran the exact stress-test design that caught v1's race (new-binding-
only writes via unique motifs, forced through `spill_write`'s append
path; small chi pools to maximize cell contention; decay/prune zeroed
in the test only, isolating concurrency from the decay math) against
this v2 code:

| Run | Writers | Decayers | Chi pool | Duration | Attempted | Found | **Missing** |
|---|---|---|---|---|---|---|---|
| 1 | 6 | 3 | 10 | 4s | 1374 | 1374 | **0** |
| 2 | 12 | 6 | 3 | 8s | 2588 | 2588 | **0** |
| 3 | 12 | 6 | 3 | 8s | 687 | 687 | **0** |

**Zero lost writes across all three runs, ~4600 writes total.** The
in-place mutation approach genuinely closes the reassignment race v1
had — reasoned through and now empirically confirmed, not assumed
fixed just because the dispatch changed the code shape.

**But all three runs also logged the same new error, 13 occurrences
total:**

```
RuntimeError('dictionary changed size during iteration')
```

Always from a decayer thread, inside `tick_decay()`'s
`for cell in self.cells.values():` line. Root cause confirmed, not
guessed: `self.cells` is a plain dict; when a concurrent writer's
`spill_write` call lands on a chi position with no existing `Cell`
(a routine, common case — any genuinely new experience touches chi
values the wave field hasn't seen before), it inserts a new key into
`self.cells`. Python's dict iterator raises exactly this error when the
dict's *size* changes mid-iteration, regardless of whether the new key
collides with anything already visited. `tick_decay()`'s v1 predecessor
iterated `list(self.cells.keys())` — a snapshot, immune to this — but
v2's given code iterates `self.cells.values()` directly, which is not.

**Confirmed the diagnosis, not just asserted it**: re-ran the identical
stress scenario (12 writers, 6 decayers, chi pool 3, 8s — the exact
config that produced errors every time) with a throwaway local test
wrapper that changes only `for cell in self.cells.values():` to
`for cell in list(self.cells.values()):` — **zero errors, zero missing
writes.** This is a validated, tested candidate fix, not a guess — but
it is **not applied to the shipped file**. The dispatch gave
`tick_decay()`'s body verbatim and named "a different thread-safety
issue surfacing" as its own explicit halt trigger; swapping in even
this small, well-tested a change without being asked crosses the same
line v1's report was careful not to cross. `dsf_ai_service/v4/
wave_atlas.py` on `guala-live` right now matches the v2 dispatch's text
exactly, bug included, so the next session (or Eve's own review) sees
precisely what was specified and what it does under load.

---

## What this means for the rest of the protocol

Not attempted. Step 0 is an explicit gate — "If ANY write is lost, HALT
and route to Eve." No writes were lost, but a *different* named halt
condition ("Different thread-safety issue surfaces beyond the
reassignment race") fired instead, and the dispatch lists both as halt
triggers with equal weight. Steps 1-6 (backup, baseline harness,
deploy, post-deploy, compare, disposition) were not started — a decay
mechanism that can crash the autonomy loop under real concurrent write
load has no business reaching a live-fire harness run, let alone
production, regardless of how the rest of the protocol would have
gone.

## Recommendation

The fix is almost certainly this small — wrap the iteration in `list(...)`,
exactly as the outer loop in v1's own `tick_decay()` already did before
this dispatch rewrote it. Tested and confirmed to work under the same
stress conditions that reproduced the crash. Flagging rather than
shipping it because:
1. It's a real, if narrow, deviation from the dispatch's given code, and this dispatch's own text treats "a different thread-safety issue" as importantly enough to warrant a stop, not a silent patch.
2. There may be a reason the dispatch moved away from a keys-snapshot approach that isn't visible to me (e.g., a future direction for `tick_decay()` that a plain snapshot wouldn't support) — worth Eve's five-second confirmation rather than an assumption.

If confirmed, the smallest fix is: `for cell in list(self.cells.values()):` — one word added, no other change to the given decay/prune/aggregate logic, and it should not need its own new stress-test round given the identical harness already validated it above.

## What was NOT done

Not deployed — no backup, no harness run, no task-def touched.
`dsf_ai_service/v4/wave_atlas.py` and `gualaloom_v5_engine.py` are
committed to `guala-live` in the exact shape the v2 dispatch specified
(the bug is real and present in what's on origin, by design, so the
record is honest). Production is untouched, still running `5a5bede`
(task:542), the healthy post-v3-rollback state, unchanged since the v1
halt.
