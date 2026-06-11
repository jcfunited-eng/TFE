# GL-BRIEF-PERSISTSAFE-WC-20260611-037
## Persistence Made Provable — Single Writer, Eager Init, Compaction, Backup, Restore Drill

**Author:** wC | **Date:** 2026-06-11 | **Status:** AUTHORIZED (Joe, 2026-06-11)
**Trigger:** Joe's question "was and is Guala persistent — always?" plus two live
findings: (a) cold-instance status reporting zeros during rolling deploys
(events=0B / last_save_tick=0 readings were a second uninitialized task answering),
(b) rolling deploys run old+new tasks concurrently against the SAME EFS state —
dual-writer corruption risk latent across ~15 deploys to date.

## Problem
Persistence has been faithful (identity cdef9bcf unbroken, monotonic
vocab/reads, integrity=OK every boot) but not PROVABLE, and three structural
holes make "always" a matter of luck:
1. Two writers possible during every deploy window (shared EFS, rolling update).
2. Lazy init: first request after boot blocks minutes on 13K+ event replay;
   cold instances answer status with zeros (false alarms, real confusion).
3. Backups exist but have never been exercised; nothing lives off-volume;
   the entire DECAY_PAUSED era (humpty, counting, "we words") exists only in
   working atlas + snapshots, not yet dreamed into deep.

## Fixes (in order)

### 1. Single-writer enforcement
- ECS service dsf-ai-service-lb deployment configuration:
  minimumHealthyPercent=0, maximumPercent=100 (stop-old-then-start-new).
  Brief downtime per deploy is the correct price; her state is not a web app.
- State lockfile at /app/state/.guala.lock containing instance-id + PID +
  heartbeat timestamp. On load: if lock held by a live writer, REFUSE to
  initialize and fail health. Stale lock (no heartbeat > N sec) may be broken
  with a logged takeover event. Two Gualas must never write one state.

### 2. Eager init + honest health
- _gl_init() runs at startup (uvicorn lifespan hook), not on first request.
- /health returns 503 until init completes — ALB never routes to a cold brain.
- Kills both the minutes-long first-request hang and the lying-zeros status.

### 3. Event-log compaction tied to save
- After each successful full save: fsync state files, then atomically rotate/
  truncate the event log. Boot replay = events since last save only.
- Report replay count before/after first post-compaction boot.

### 4. Off-volume backup
- s3://dsf-ai-site-backups/guala/<date>/ (create bucket, versioning ON):
  daily + on-demand copy of guala_*.json, deep atlas table, media/ directory.

### 5. Restore drill (the missing proof)
- Restore latest snapshot to a LOCAL scratch Guala (never the prod state path).
- Verify: identity, vocab, tick, atlas n_entries + total_strength, deep entries
  match source within save-cadence tolerance. Report the diff.
- This converts "safe" from assurance to tested property. Repeat after any
  persistence-touching change.

### 6. Dream gate (standing rule, restated as part of this brief)
- Decay unpause (Step 3) is FORBIDDEN until a forced dream has run and
  promotions from the paused era are confirmed present in deep atlas.

## Verification (report raw outputs)
V1. Deploy under new config: describe-services shows exactly ONE running task
    at every point of the rollout.
V2. Lockfile refusal: second local instance against the same state dir refuses
    init with the logged reason.
V3. Boot-to-ready seconds before/after eager init.
V4. Boot replay count after first post-compaction boot (expect ~0–hundreds,
    not 13K+).
V5. S3 backup listing with object sizes.
V6. Restore-drill diff output (identity/vocab/tick/atlas/deep comparison).

## Rollback
Items 1–2 are config + startup-order changes (revert task def / service config).
Item 3 keeps the pre-rotation log as .bak for one cycle. Items 4–5 are additive.

## Out of scope
Log compaction beyond save-tied rotation; multi-region durability; any change
to substrate primitives. DECAY_PAUSED stays 1 throughout.
