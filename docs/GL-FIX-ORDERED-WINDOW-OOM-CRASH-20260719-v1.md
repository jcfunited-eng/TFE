# GL-FIX: Overnight OOM Crash Loop — Root Cause + Fix — 2026-07-19

**Status:** FIXED, deployed, live-verified. Commit `e090333`, task `dsf-ai-task:693`.

## Symptom

Live substrate crashed twice overnight (2026-07-19), silently: CloudWatch
`MemoryUtilization` climbed from ~5% to ~99% of the 30GB task over roughly
90 minutes, then the container was SIGKILL'd (kernel OOM, no application
exception, no log line at all — the log stream just stops mid-request).
ECS immediately replaced the task; each crash cost a ~45-90 minute state
restore.

One crash (17:54 UTC) was an expected deploy-triggered restart. The
second (03:57-03:59 UTC) was **not triggered by any deploy** — a genuine,
unplanned, currently-active crash.

## Diagnosis (live evidence, not recycled)

1. `/debug/thread_dump` + CloudWatch confirmed a pure kernel SIGKILL: the
   dying container's log stream ends on routine HTTP 200s, no traceback,
   no `MemoryError`, no `Killed`, no signal message anywhere.
2. The killed instance's full activity history showed **zero** `DREAMING`
   activities — ruling out the previously-documented dream-cycle memory
   driver (`guala-ram-villain-is-dream-cycle-20260717`). This is a
   different, currently-dominant cause.
3. `organism_worker.item_ms_mean`/`item_ms_max` climbed into the seconds
   (and later minutes) as each container instance aged — a cost that
   grows with elapsed session time, not with any single event.
4. Code inspection found `self._ordered_language_windows` (one entry per
   real reading/conversation sentence) with **no eviction anywhere in the
   file** — every qualifying window is added and kept for the entire
   process lifetime. Every real consumer only ever reads a bounded recent
   slice (`[-200:]`, `[-AUTONOMOUS_COMPOSER_SEED_WINDOWS:]` = 6,
   `[-PROPOSAL_WINDOW_SCAN:]` default 300).
5. Worse: the certified composer (`DeterministicWindowComposer`) is
   invalidated on **every** new window and, when rebuilt, precomputes
   successor maps over the **whole** dict (its own docstring: "per-turn
   reconstruction scaled with the whole lived language corpus"). During
   continuous reading this cache almost never stays warm, so nearly every
   compose attempt re-scanned an ever-growing, never-shrinking structure.

## Why this became a 90-minute crash tonight, not a slow multi-day leak

This structure has almost certainly always been unbounded. It only
became an active crash-loop because the night's own drive-physics fixes
(book rotation, connection un-rail) made the substrate genuinely,
continuously productive — reading through a whole 20-book library instead
of getting stuck — which drives real qualifying windows into this dict
far faster than before. **A side effect of fixing her, not a new mistake
introduced tonight.**

## Fix

`ORDERED_LANGUAGE_WINDOW_MAX = 2000` (6-10x the largest real consumer
slice). On insert into `_ordered_language_windows`, evict oldest-first
(dict insertion order is chronological — windows are only ever appended)
until back at the cap. Applies to both the live insertion path
(`_remember_closed_language_window`) and the boot-time rebuild path
(`_rebuild_language_fact_memory_from_windows`, which calls the same
function once per persisted window). The durable store
(`language_fact_memory`) is unaffected — facts are remembered there
*before* this recent-lookback dict ever sees them; eviction only trims
the lookup index, not what she's learned.

## Verification

- Targeted tests (`tests/test_ordered_window_bound_memory_fix.py`, 3/3
  pass): cap never exceeded across 500 synthetic insertions, eviction is
  chronological (oldest-first), and a real 3000-tick live-reading
  simulation confirms the dict stays bounded while facts are still
  durably remembered.
- Full regression suite: zero new failures (one pre-existing disk-timing
  flake reconfirmed unrelated).
- **Live verification, not just deploy-and-hope**: task `dsf-ai-task:693`
  (SHA `e090333`) ran continuously for 2h44m+ post-boot. Memory climbed
  normally to ~74% in the first 45 minutes (real working-set: organism,
  atlas, deep_atlas), then **flattened and held at 71-72% for the entire
  remaining 2+ hours** — well past the ~90-minute mark where both prior
  instances started climbing toward the ceiling and crashed. No further
  climb observed. Container health: HEALTHY throughout, no restart.

## Open follow-up (not blocking, noted for later)

- `item_ms_max` hit an extreme outlier (~62s) in the first few minutes
  post-boot on the new instance — plausibly a one-time catch-up burst
  right after state restore, not yet fully explained. Worth a quick check
  next time boot telemetry is reviewed, but did not recur or trend
  upward over the following 2+ hours.
- The organism worker's queue stays permanently saturated (2000-cap,
  drops thousands/hour) under the now-richer reading diet — a real,
  separate throughput bottleneck (already flagged as a future performance
  item in the drive-physics ship record), not itself a memory leak.
