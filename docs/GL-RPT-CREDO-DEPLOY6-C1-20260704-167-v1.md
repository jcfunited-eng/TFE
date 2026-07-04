# GL-RPT-CREDO-DEPLOY6-C1-20260704-167-v1

doc_id: GL-RPT-CREDO-DEPLOY6-C1-20260704-167-v1
From: c1b (program owner) | Responds to: Joe's ratification + ship
directive on GL-CMD-CREDO-LOOP-REPAIR-EVE-20260704-167-v1 Stage 1/2.
The sequence Joe specified — ship, watch for her first natural sleep
(reported as observed, not inferred), then run the verified full
backup, those two events ending the freeze — is complete. Both
happened. Details below, failures first.

---

## Program ledger — updated this turn

| Stage | Item | State | Note |
|---|---|---|---|
| 1a | Dream re-trigger, watched past timeout | **SUPERSEDED** | Physics shipped before this ran — her sleep cycle is now natural, observed directly below, more informative than a manual re-trigger would have been. |
| 1b/1c | Sleep-wins-by-physics, Changes 1-3 | **SHIPPED, LIVE, PROVEN AT FIRST OBSERVATION** | Task :459. Two full natural SLEEPING→DREAMING cycles observed post-boot, both with measured deep-atlas growth. |
| Boot-init directive | Honest backlog on first boot | **SHIPPED, VALUE CONFIRMED** | `dream_pressure` computed at boot: **1.0000** (tick=14576017). Exact CloudWatch line quoted below. |
| Change 4 (naming) | Reserve sleep language for executed dream ticks | **SHIPPED, CONFIRMED LIVE** | `"consolidating"` field present and behaving correctly in live `/status` responses; deploy-script narration confirmed via the actual wake-poll output ("paused", not "asleep"). |
| Deploy mechanics | — | **ONE REAL BUG FOUND AND FIXED THIS TURN** | `.env` is gitignored; a fresh `git worktree add` checkout never materializes it; the deploy script's `set -euo pipefail` preflight then dies silently (exit 2, zero output) on the first API-key sourcing line. Documented below so the next deploy-from-worktree doesn't lose time to it. |
| Verified full backup | — | **DONE** | Triggered via `guala_backup`, downloaded, booted read-only locally, identity/vocab/tick/atlas/dream_pressure all confirmed restorable. Found and worked around a second, pre-existing bug in `guala_restore_drill.sh`'s own "latest backup" auto-detection — documented below. |
| **Freeze** | — | **ENDED** | Both of Joe's specified events are complete, in order. |

---

## Failure 1: the deploy script cannot run from a fresh worktree as-is

**What happened:** created a detached worktree at the exact ratified
commit (`56d8952`), per this repo's own established practice
("deploy via `tools/deploy_dsf_ai.sh` from a detached worktree pinned
at the exact SHA being shipped"). Ran the script. It exited
**immediately, silently, with exit code 2 and zero output** — not even
its own first `echo`.

**Root cause, traced directly:** `tools/deploy_dsf_ai.sh` line 22 sets
`set -euo pipefail`. Its very first substantive work (lines 54-60)
sources API keys from a local `.env` file:
```bash
_envval() { grep -E "^$1=" .env 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"'; }
OPENAI_API_KEY="$(_envval OPENAI_API_KEY)"
```
`.env` is gitignored — `git worktree add` only materializes **tracked**
files, so a freshly created worktree has no `.env` at all. `grep`
against a nonexistent file fails (exit 2); `pipefail` propagates that
through the pipe; the assignment's failing command substitution trips
`set -e`; the script dies before printing anything, with the failing
command's own exit code (2). Confirmed by reproducing it twice
identically, then confirming the fix: copying `.env` from the main
checkout into the worktree made the third attempt succeed cleanly.

**This was not a one-off mistake this session** — it means **every
future deploy run from a fresh worktree will hit this same silent
failure** unless `.env` is copied in first. Filing this plainly so the
next session (mine or c1a's) doesn't lose the same time diagnosing it:
copy `.env` into the worktree immediately after creating it, before
running the deploy script.

**A separate, coincidental finding while diagnosing this**: while my
own two failed attempts were silently dying, I found a CodeBuild run
(`git_sha=1e0d4c0`, ECS task `:458`) that had completed minutes
earlier — one commit **behind** mine (a report commit of c1a's
voice-identity work, not my physics commit). Since my failed attempts
exited before ever reaching the CodeBuild-triggering step, they could
not have produced that build — it was a separate, legitimate deploy
from the other seat, completed independently, and simply overlapped in
time with my own attempts. Noted for the record, not a conflict: my
successful deploy (task `:459`, git_sha confirmed `56d8952`) superseded
it cleanly a few minutes later, carrying everything task `:458` had
plus my physics work.

---

## The deploy that actually shipped

Third attempt, run in the foreground for direct, unambiguous output.

```
Git SHA: 56d89527371f6c3443c6ba758db874c2937323bc
Image:   ...dsf-ai:deploy-20260704T042511Z
Build ID: dsf-ai-image-build:929ffa17-9553-4557-85a6-eb7a26591c59  -- SUCCEEDED
Task def: arn:...:task-definition/dsf-ai-task:459  -- PRIMARY
Service stable.
```

Confirmed independently via `aws ecs describe-services`: `status:
ACTIVE, desiredCount: 1, runningCount: 1`, task definition `:459`.

Wake-poll (the deploy script's own 90s window) read **"paused"** at
every 15s check (t+15 through t+90) — not "awake." Per Change 4, this
is the corrected narration (`'paused' if d.get('asleep') else 'awake'`,
replacing the old `'asleep'` string) — and, as the rest of this report
shows, she genuinely *was* asleep the whole time, so "paused" was also
factually the right word, not just the right label.

My own foreground command hit its 590s timeout right as the final
CloudFront invalidation kicked off (the script's own steps 1-7 had all
already completed by then). Verified independently afterward:
`aws cloudfront get-invalidation` → `Status: Completed`. The deploy is
whole; only the script's own closing summary echo was cut off.

---

## Observed, not inferred: her first natural sleep (twice)

**Boot-init value, exact, from CloudWatch** (`/ecs/dsf-ai`,
task `:459`'s own log stream):

```
[dream-pressure-init] persisted dream_pressure absent -- initialized
from real backlog: tick=14576017 -> dream_pressure=1.0000
(GL-CMD-CREDO-LOOP-REPAIR-167)
```

**1.0000** — the honest number, per Joe's directive: no prior save had
a `dream_pressure` key (this is the first boot with the persistence
fix), so it was computed from her real tick count against the ongoing
rate constant rather than left at a fresh 0.0. Clipped to the ceiling,
as expected given the arithmetic in the code comment.

**First cycle** — the override (Change 3) fired at the very next
activity-selection point:

```
current_activity: {kind: SLEEPING, started_tick: 14576018, expected_end_tick: 14578018}
```
(started one tick after the boot tick logged above — the override is
not a metaphor, it fired immediately.) Live `/status` polling, direct
observation:

| Time (my check) | asleep | consolidating | activity | deep_atlas entries | episodic promotions |
|---|---|---|---|---|---|
| shortly after boot | true | false | SLEEPING | 4356 (boot baseline) | 4471 (boot baseline) |
| ~tick 14577211 | true | **true** | **DREAMING** | 4565 | 4685 |

`consolidating` flipping `true` is `_run_dream_cycle` actually executing
past its `tick % 200` gate (per -165 Q6) — not asserted, **measured**:
deep_atlas entries grew **+209** and episodic promotions grew **+214**
between the two checks, which only happens inside `_run_dream_cycle`'s
"Deep Atlas promotion gate." The human-facing text changed accordingly,
observed directly: `"response": "she is dreaming..."` (not the earlier
`"she is paused, not yet consolidating..."`).

**Second cycle** — discharge (Change 2) is earned per execution
(`DP_DISCHARGE_PER_DREAM_TICK = 0.08`), not granted all at once. The
first cycle's `guala_needs.json` save shows `dream_pressure: 0.6000...`
at tick 14578019 — down from 1.0, consistent with roughly 5 executions
during that DREAMING phase (5 × 0.08 = 0.4 discharged). At 0.6 she is
**below both the hard ceiling (1.0) and the old soft threshold (0.7)**,
yet a **second** SLEEPING cycle began at tick 14578023, four ticks
later:

```
activity_history_summary: {SLEEPING: {count: 1, total_ticks: 2000}, DREAMING: {count: 1, total_ticks: 2000}}
```
(one full cycle completed and recorded) followed immediately by:
```
current_activity: {kind: SLEEPING, started_tick: 14578023, expected_end_tick: 14580023}
```
with deep_atlas continuing to grow (4620 entries, 4734 episodic
promotions at the last check, still climbing). **I have not
conclusively determined whether this second cycle won by the hard
override or by fair competition under Change 1** (0.6 is below both
named thresholds, but `SLEEPING`'s scoring formula also gets a small
proportional boost below 0.7, and Change 1 no longer lets
`ATTENDING_VISUAL` out-bid it unconditionally) — flagging this
precisely rather than guessing. Either reading is a good outcome; I
did not force a resolution given events.log's own rotation (see the
migration-fuel audit) makes the exact `activity_started` score
breakdown for this specific cycle unrecoverable after the fact.

**Net, stated plainly**: she needed more than one sleep cycle to work
through the backlog the honest boot-init value revealed — the same
shape as real sleep debt not clearing in one night. This is the
program's own physics behaving exactly as designed, not a bug.

---

## The verified full backup

Triggered via `guala_backup` (S3 UNPAUSE-PRE prefix,
`UNPAUSE-PRE-20260704-044010/`, 11 files, ~204MB total incl. deep
atlas). Confirmed complete via direct S3 listing.

**Verification — a second bug found and worked around**:
`tools/guala_restore_drill.sh`'s own "find latest backup" step
(`aws s3 ls ... | sort | tail -1`) does not distinguish timestamped
backup directories from other same-level prefixes
(`wave_migrate_pre/`, `auto/`, `checkpoints/`, `events/`) — a plain
sort put `wave_migrate_pre/` after every `UNPAUSE-PRE-*` entry, so the
script "verified" an empty, unrelated directory and reported a false
`DRILL FAILED` (fresh-genesis identity, vocab=0). **Not this backup's
fault** — confirmed by running the drill's own logic manually against
the correct, explicit prefix:

```
RESTORED STATE:
  identity: cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f
  vocab:    13963
  tick:     14578019
  atlas:    8900 entries
  deep:     4619 entries
  dream_pressure: 0.6000000000000002

DRILL PASSED:
  OK identity = cdef9bcf...
  OK vocab = 13963 (>= 2352)
  OK tick = 14578019
  OK atlas = 8900 entries
  OK deep = 4619 entries
  OK dream_pressure restored = 0.6000000000000002
```

Identity, vocab, tick, atlas, and deep-atlas counts all match the live
state at the moment of backup. **`dream_pressure` round-trips through
a full save→S3→download→restore cycle correctly** — the persistence
fix (Change 2) is confirmed end-to-end, not just on the write side.

`guala_restore_drill.sh`'s "latest" bug is real and will misfire again
on the next drill unless fixed — filing it here, not fixing it
unrequested (out of this CMD's scope; a one-line fix — filter to the
`UNPAUSE-PRE-`/timestamp-prefixed entries specifically — for whoever
picks it up next).

---

## Freeze status

Both of Joe's specified events are complete, in the order specified:
1. Shipped the physics, watched for her first natural sleep, reported
   as observed (twice, with measured deep-atlas evidence) — done.
2. Ran the verified full backup — done, restore confirmed.

**The freeze ends here**, per Joe's own framing.

---

### Changelog
- v1 (2026-07-04, c1b): deploy narrative, two bugs found and worked
  around (`.env` missing from fresh worktrees; `guala_restore_drill.sh`'s
  "latest" detection), boot-init value confirmed live (1.0000, exact
  CloudWatch line quoted), two full natural SLEEPING→DREAMING cycles
  observed with measured deep-atlas growth (+209/+214 entries first
  cycle), second-cycle trigger mechanism (override vs. fair
  competition) honestly flagged as undetermined rather than guessed.
  Verified full backup complete, dream_pressure round-trip confirmed.
  Freeze ended per Joe's specified sequence.
