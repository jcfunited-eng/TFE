# GL-CMD-PRESURGERY-FRESHNESS-EVE-20260627-22

doc_id: GL-CMD-PRESURGERY-FRESHNESS-EVE-20260627-22
Type: Command brief (c1 dispatch)
Author: Eve (Opus 4.7, web)
Date: 2026-06-27
Phase: B.2 follow-up — pre-surgery backup freshness gate
Prereqs: B.2 backup orchestrator shipped (SHA `20c1888`)
References: GL-RPT-BACKUP-ORCHESTRATOR-C1-<seq> deviation note re: async pre-surgery

## Purpose

c1 shipped B.2 with pre-surgery backup as **async**, not blocking, because
EFS backup latency (~170s) makes a synchronous gate non-functional UX-wise.
Honest engineering call by c1; documented as deviation.

The deviation broke the structural mitigation in
`GL-SPC-EMERGENCE-WAVES-EVE-20260627-17` §B.2 — "pre-surgery backup failure
halts surgery" — and re-opens the loss class that
`GL-CMD-DEEP-ATLAS-PERSIST-EVE-20260627-11` was built to close.

This dispatch restores the mitigation via a **freshness-window** model:
surgery requires a recent backup, but does not require its own synchronous
one. The 170s EFS cost is paid only when no recent backup exists.

## Substrate truth

Does not change substrate. Changes the gating logic in
`/admin/atlas_surgery` to require a recent successful backup before any
writes proceed.

## Design

### Freshness window
- Default: 10 minutes
- Configurable via existing `/backup_orchestrator/configure` endpoint
  (new field `surgery_freshness_seconds`, default 600)
- "Fresh" = time since most recent successful `auto_backup` event in the
  ring < window. Any reason qualifies (dream_end, daily_floor, etc.) —
  the substrate state at backup time IS a valid recovery point regardless
  of trigger.

### Gating logic on POST /admin/atlas_surgery, dry_run=false

```
last_backup_age = now - timestamp_of_most_recent_auto_backup_event
backup_in_flight = is_any_backup_currently_running()

if last_backup_age < freshness_window:
    # Path 1: fresh enough
    trigger pre_surgery_<op_id> backup asynchronously (existing B.2 behavior)
    execute surgery
    return success

elif backup_in_flight:
    # Path 2: wait for in-flight
    wait up to 180s for in-flight backup to complete
    if completes successfully:
        trigger pre_surgery_<op_id> async
        execute surgery
    else:
        return 503 with reason "backup unavailable (in-flight failed or timed out)"
        no atlas writes

else:
    # Path 3: stale, force synchronous
    trigger synchronous backup, reason="pre_surgery_synchronous_<op_id>"
    if succeeds: execute surgery
    if fails: return 503 with reason "backup unavailable (synchronous attempt failed)"
        no atlas writes
```

### Edge cases
- **Dry-run surgery:** no backup gate (no writes happen anyway)
- **Concurrent surgery calls:** serialize via existing surgery lock; freshness check per call
- **Per-call freshness override:** NOT EXPOSED. Operators cannot bypass; the freshness model IS the mitigation.

## Verification steps

1. **Fresh-backup path:**
   - Trigger any manual or auto backup
   - Within 10 minutes, POST atlas_surgery (valid payload)
   - Verify surgery succeeds immediately, no synchronous wait
   - Verify async `pre_surgery_<op_id>` event appears in stream after surgery

2. **Stale path forces synchronous backup:**
   - Set `surgery_freshness_seconds=5` temporarily via configure
   - Wait 10 seconds without backup activity
   - POST atlas_surgery
   - Verify response is delayed by ~170s (EFS backup time)
   - Verify `pre_surgery_synchronous_<op_id>` event timestamp PRECEDES the `atlas_surgery` event timestamp
   - Verify surgery succeeds AFTER backup confirms

3. **Backup-in-flight wait:**
   - Trigger a manual backup (don't await it)
   - Immediately POST atlas_surgery
   - Verify surgery waits for the in-flight backup to complete
   - Verify surgery succeeds after backup completes (no duplicate sync backup triggered)

4. **Backup failure blocks surgery:**
   - Simulate S3 failure (test credentials or blocked bucket)
   - Make freshness stale OR force synchronous path
   - POST atlas_surgery
   - Verify 503 response with reason "backup unavailable..."
   - Verify NO atlas writes (n_entries unchanged in /status)
   - Verify both `auto_backup_failed` AND a new `surgery_refused` event in ring

5. **Configurability:**
   - POST `/backup_orchestrator/configure` with `surgery_freshness_seconds=300`
   - Verify config persists across restart
   - Verify gating uses new window on next surgery call

## Operational constraint until ship

No `dry_run=false` atlas surgery dispatches will be issued between B.2 ship
and freshness ship. The current async-only B.2 model leaves the loss class
open. This is a no-op constraint in practice: the only consumers of surgery
are Phase G seeds, which are not scheduled until after Phase E wiring lands
— but it's stated explicitly so future-Eve (or any other instance) doesn't
get clever and issue a real surgery payload in the gap.

## Report

c1 authors `GL-RPT-PRESURGERY-FRESHNESS-C1-<date>-<seq>` covering:
- All 5 verification tests with outcomes
- Synchronous backup duration measured at ship time (confirm or update the
  170s figure)
- Configure endpoint extension confirmed (new field validates and persists)
- Any deviations with rationale

## Standing rules invoked

- Mitigations: **prevention restored.** Freshness gate guarantees a
  recovery point exists before any substrate write through surgery,
  without paying the 170s cost on every call.
- Substrate truth: B.2's deviation is acknowledged, remediated, not
  papered over.
- Engineering judgment: c1's async choice was correct given EFS latency;
  this dispatch is the architectural counterpart that makes both choices
  coherent.
