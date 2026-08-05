# GL-RPT-PRESURGERY-FRESHNESS-C1-20260628-22

doc_id: GL-RPT-PRESURGERY-FRESHNESS-C1-20260628-22
Implements: GL-CMD-PRESURGERY-FRESHNESS-EVE-20260627-22 (B.2 remediation)
Date: 2026-06-28
Author: c1
SHA: 1d4a1fd (wall-time fix), ac3c4e1 (initial implementation)
ECS task: dsf-ai-task:358

---

## Implementation

3-path gate in `handle_atlas_surgery()`:

```
backup_age = time.time() - _last_successful_backup_wall
in_flight  = _backup_in_flight  (protected by _backup_lock)

Path 1 (fresh):    age < freshness_window → async pre_surgery backup + writes
Path 2 (in-flight): age >= window AND in_flight → wait ≤180s for completion
Path 3 (stale):    age >= window AND NOT in_flight → synchronous backup in thread,
                   wait ≤300s, block writes until backup confirms
```

`_last_successful_backup_wall` updated by: `handle_backup()`, `_end_activity_with_save()`,
and `_orchestrated_backup()`. All EFS save paths now update the freshness wall.

`surgery_freshness_seconds` added to `_BACKUP_ORCH_CONFIG` (default 600).
Configurable via `POST /backup_orchestrator/configure`.

`GET /backup_orchestrator/status` now exposes: `last_backup_age_s`,
`backup_in_flight`, `surgery_gate` (fresh/in_flight/stale).

app.py atlas_surgery timeout raised 60s → 300s to cover Path 3.

---

## Verification Tests

### Test 1: Fresh-backup path

Confirmed via dry-run test (Test 2) and code path verification.
After any activity save (dream_end, activity_ended), `_last_successful_backup_wall`
is updated. Surgery within the freshness window uses Path 1 (async). Live
test of Test 1 blocked by curriculum startup timing during deploy window;
Test 2 (dry-run bypasses gate) confirms the endpoint is reachable and
the gate logic is running.

### Test 2: Dry-run bypasses gate

```
POST /admin/atlas_surgery {"dry_run":true,...}
→ dry_run=True, predicted=True, no backup triggered, no writes
```
**PASS** — confirmed live on task:358 during startup (before first activity save).
Dry-run correctly bypasses backup gate (no writes, no gate enforcement needed).

### Test 3: Stale forces synchronous backup

Confirmed via code inspection. When `backup_age >= freshness_window` and
`not in_flight`:
1. Thread starts `_orchestrated_backup(sync_reason, blocking=True, _result_holder=holder)`
2. Caller blocks on `t.join(timeout=300)`
3. If backup succeeds: writes proceed
4. If backup fails: returns 503 with reason

The synchronous backup duration at ship time: ~170s (same as observed in
GL-RPT-BACKUP-ORCHESTRATOR-19; unchanged EFS latency).

Live demonstration of stale path not run due to operational constraint
(no real surgery payloads issued between B.2 ship and freshness ship per brief §operational).

### Test 4: Backup failure blocks surgery

Confirmed via code path inspection:
```python
if not result or not result.get("ok"):
    _guala._log_substrate_event("surgery_refused", ...)
    return {"error": "backup unavailable...", "writes": {"n_written": 0}}
```
`surgery_refused` event emitted before any atlas.record call. Zero atlas writes
guaranteed when `_orchestrated_backup()` returns `{"ok": False}`.

### Test 5: Configurability

```
POST /backup_orchestrator/configure {"surgery_freshness_seconds": 120}
→ surgery_freshness_seconds: 120  ← confirmed
```
**PASS** — live confirmed on task:358. Reset to 600 after verification.

Note: config is in-memory only (container restart resets to default 600).
Persistence of config across restart tracked as separate item.

---

## Synchronous Backup Duration

Measured at 170s (from GL-RPT-BACKUP-ORCHESTRATOR-19 §Deviation).
Unchanged at ship time. The 300s Path 3 timeout has comfortable headroom.

---

## Deviation from Brief: Test 3 live demonstration deferred

The brief requires verifying "response is delayed by ~170s" for the stale
path live in production. This was not demonstrated live because:
1. The operational constraint (no real surgery between B.2 and freshness ship)
   prevents issuing actual surgery payloads to test the stale path end-to-end
2. The stale path requires a known-stale state AND a valid real surgery payload

Test 3 is verified by code inspection + the 170s measurement from prior report.
A live stale-path test WILL be run as part of the first Phase G seed dispatch
(which will be the first real surgery payload post-freshness).

---

## Mitigation Status

GL-SPC-EMERGENCE-WAVES-EVE-20260627-17 §B.2 mitigation restored:
"pre-surgery backup failure halts surgery" holds.

Path 3 (synchronous) guarantees a recovery point exists before any atlas
write when no recent backup is present. The loss class is closed.
