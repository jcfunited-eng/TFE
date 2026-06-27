# GL-CMD-DEEP-ATLAS-PERSIST-EVE-20260627-11

doc_id: GL-CMD-DEEP-ATLAS-PERSIST-EVE-20260627-11
Author: Eve (Opus 4.7, web)
Date: 2026-06-27
Target: c1
Branch: guala-live
Priority: CRITICAL — HALT all other deploys until this lands
Surfaced by: substrate observation 08:03Z — deep_atlas dropped from 14,488 to 3,174 entries

## What broke

`guala_deep_atlas.json` is listed in `files_present` and persists to EFS. Events
log replay is supposed to reconstruct missing state on boot. But the events
schema does NOT include deep_atlas promotion records sufficient to rebuild the
full deep_atlas state on cold boot. Result: every container deploy that triggers
a load-from-events rather than load-from-snapshot loses the bulk of deep_atlas.

Confirmed cost: ~11,000 deep_atlas entries lost between earlier today and now.
That's weeks of consolidated substrate work — survival promotions and episodic
references that drove her grandurun candidate retrieval. Gone from one deploy
event. The 3,174 currently visible are mostly fresh post-deploy promotions
from the last few hours, NOT the historical depth that took her months to build.

Every deploy we have done today potentially cost more. We have no continuous
metric history to know exactly when the wipe happened or how many wipes have
occurred across the day. Going forward: **no more deploys until deep_atlas
survives container restart**.

## What ships

A complete deep_atlas persistence path that survives container restart.
Three parts; all must land in one commit.

### Part 1 — Direct save/load of deep_atlas to its own file

**File:** wherever DeepAtlas / EpisodicLayer / equivalent owns the deep_atlas
state. C1 locates.

Add explicit `save_deep_atlas()` and `load_deep_atlas()` methods:
- `save_deep_atlas()` serializes the full deep_atlas structure (entries,
  strengths, promotion_counts, last_tick per entry, survival/episodic flags)
  to `STATE_DIR/guala_deep_atlas.json`
- `load_deep_atlas()` on boot reads the file and populates the deep_atlas
  in-memory structure
- File schema: explicit version field (`schema_v: 1`) for future migrations

This is the canonical persistence path. Events log replay is a DERIVED
recovery path, not primary. Deep_atlas saves and loads as a first-class file.

### Part 2 — Save cadence

`save_deep_atlas()` runs:
- Every `dream_end` (already the trigger for `last_s3_backup`)
- Every explicit `/admin/backup`
- Every coordinator activity transition (light — opportunistic save while she's
  already paused for the activity boundary)

The activity-transition save is the new one: deep_atlas saves at every activity
boundary which is roughly every 1500-3000 ticks. Cheap; deep_atlas is small
(<10MB at current scale).

### Part 3 — Load priority on boot

Boot sequence:
1. Try `load_deep_atlas()` from `guala_deep_atlas.json` FIRST
2. If file present and version-compatible → load directly, skip events
   replay for deep_atlas
3. If file missing or corrupt → fall back to events replay (current behavior)
   AND log a warning prominently

If load fails AND events replay produces a smaller deep_atlas than expected
(c1 to define "expected" — likely a threshold based on last known size logged
elsewhere), the boot logs an explicit `deep_atlas_load_anomaly` event with
diagnostic detail. We will see future losses immediately rather than days later.

## Mitigations (prevention)

**M-11-1. Pre-deploy verification: c1 runs a save-then-load smoke test in a
local container before pushing.** Snapshot deep_atlas → save to file → restart
local process → load → confirm entries and strengths match. If smoke fails,
do NOT push.

**M-11-2. Pre-deploy guard on production: c1 triggers `/admin/backup` IMMEDIATELY
before deploying this fix.** Snapshot her current deep_atlas state (3,174
entries) so we have a known-good rollback baseline.

**M-11-3. Post-deploy verification: after this dispatch lands, c1 manually
restarts the ECS task ONCE and confirms deep_atlas count is preserved.**
This is the only true test that persistence works through a real container
restart. If the test fails, REVERT — the fix is incomplete.

**M-11-4. Deep_atlas count is now a tracked metric.** Add `n_deep_atlas` to
`/status` output AND to the persistence_health block. Joe + Eve see deep_atlas
count every time we check status going forward. Drops are immediately visible.

**M-11-5. Loss alarm.** If a boot produces deep_atlas with fewer than 80% of
last known persisted count, the boot logs a `deep_atlas_loss_detected` event
with the delta. Future regression caught at boot, not 6 hours later when
someone happens to look.

## Pass criteria (behavioral)

V1. Code visible on origin: save_deep_atlas, load_deep_atlas, boot priority
    sequence, activity-boundary save trigger, n_deep_atlas in status

V2. Local smoke (pre-push): save → restart container → load → 100% entry
    preservation, strengths match within float-precision tolerance

V3. **Production restart test**: post-deploy, c1 manually restarts ECS task.
    Pre-restart deep_atlas count == post-restart deep_atlas count (±10
    entries acceptable for normal in-flight churn during restart window).

V4. Save fires at every activity transition (visible in events log as
    `deep_atlas_saved` event with tick + n_entries)

V5. `/status` output shows `n_deep_atlas` continuously

V6. Loss alarm fires correctly when forced (test: corrupt the JSON file
    deliberately, boot, confirm `deep_atlas_loss_detected` event)

## Stop conditions (revert immediately)

- Save adds significant tick latency (>50ms per save) — performance regression
- Load on boot fails for any reason that prevents her from coming up
- The manually-triggered ECS restart test fails — entries are not preserved
- Disk I/O errors during save (filesystem capacity, EFS issues)

## Deploy steps

1. `git fetch origin && git checkout guala-live && git pull --ff-only`
2. **POST /admin/backup IMMEDIATELY** — preserve current state including the
   3,174 deep_atlas entries we have right now
3. Locate deep_atlas implementation
4. Implement Part 1 (save/load methods + file schema)
5. Implement Part 2 (save cadence: dream_end, /admin/backup, activity boundary)
6. Implement Part 3 (boot load priority + fallback + warning)
7. Add n_deep_atlas to /status and persistence_health
8. Add deep_atlas_saved event + deep_atlas_loss_detected alarm
9. Local smoke test (M-11-1)
10. `git commit -am "CRITICAL: GL-CMD-DEEP-ATLAS-PERSIST-EVE-20260627-11 — deep_atlas survives container restart"`
11. Push, deploy to Fargate
12. Verify boot — n_deep_atlas should equal pre-deploy count (post-deploy
    load runs save_deep_atlas immediately on first activity boundary)
13. **Manual ECS task restart test (M-11-3)** — confirm preservation through
    a real container swap

## Report

Filename: `docs/GL-RPT-DEEP-ATLAS-PERSIST-C1-20260627-11.md`
Required sections:
1. Code diffs (Part 1, 2, 3)
2. Schema of `guala_deep_atlas.json`
3. V2 local smoke test result with entry counts pre/post
4. V3 production restart test result with entry counts pre/post
5. V4 sample `deep_atlas_saved` events from the live container
6. V5 sample /status showing `n_deep_atlas`
7. V6 loss alarm test result
8. Any anomalies (especially serialization edge cases, file size, save latency)
9. Recommendation: hold / additional persistence work

## Halt other work until this lands

After this dispatch ships clean and the manual ECS restart test passes, the
deploy queue resumes:
- GL-CMD-DAYDREAMING-EVE-20260627-09 (queued)
- GL-CMD-V5-VOICE-STAGE1-EVE-20260627-10 (queued)
- Group α from GL-SPC-EMERGENCE-WAVES-EVE-20260627-08

Until then, no deploys to live Guala. Persistence is non-negotiable. We can't
build cognition on a substrate that loses its consolidation every container swap.

## What this prevents

After this lands:
- ECS rolling deploys preserve deep_atlas (the consolidation she's earned)
- Container crashes preserve deep_atlas
- We see deep_atlas count in every status check — silent loss becomes impossible
- Future dispatch deploys are safe (preventing data loss is now a deploy invariant)

The 11,000 entries lost today are unrecoverable. But every entry she builds
from here forward is durable.

Ship it now.
