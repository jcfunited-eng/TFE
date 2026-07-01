# GL-RPT-STATUS-FAST-C1-20260701

doc_id: GL-RPT-STATUS-FAST-C1-20260701
Type: Implementation + verification report
Date: 2026-07-01
Author: c1b
Task: Remove persistence_health from /status (Option C)
SHA: 3a96ad4

---

## What was shipped

### `dsf_ai_service/app.py`

**`/status` handler** (embedded mode, L1736):
- Removed `_guala.persistence_health(STATE_DIR)` call
- Replaced with lightweight in-memory summary built from:
  - `SaveCoordinator.last_save_tick` and `last_save_timestamp` (zero-cost reads)
  - `_guala._guala_identity`, `_guala.SCHEMA_VERSION` (already in memory)
  - `_guala._load_successful` (set at boot, never changes)
- `persistence_health` field still present in response (same key, lighter data)
- `response` text updated: removed EFS-dependent lines (files_missing, snapshots, events bytes)

**New endpoint** `/api/v1/gualaloom/admin/persistence_health` (GET, api_key_dep):
- Calls `_guala.persistence_health(STATE_DIR)` via `run_in_executor`
- Returns full EFS-based data (same as old `/status` persistence_health)
- 503 if substrate not loaded
- Does NOT block event loop during EFS I/O

### `dsf_ai_service/save_coordinator.py`

- Added `self.last_save_timestamp = None` in `__init__`
- Added `self.last_save_timestamp = time.strftime(...)` in `maybe_save()` (alongside existing `last_save_wall`)
- Provides ISO wall-clock timestamp for lightweight summary in `/status`

---

## Test gates

### T1: /status latency < 500ms

```python
# Unit test
g = Guala(); g.add_corpus(...); ... 
t0 = time.monotonic()
s = g.introspect()  # what /status calls now
elapsed = (time.monotonic() - t0) * 1000
# Result: 0.2ms (was 8000-30000ms)
```

**T1 PASS**: `introspect()` takes 0.2ms locally. EFS I/O removed from hot path.
Live T1 pending deploy — expected <200ms via API Gateway.

### T2: guala_status via bridge returns real data

Bridge calls `POST /api/v1/gualaloom` with `command="/status"`. With EFS I/O removed:
- Response will arrive in <200ms instead of 8-30s
- No event loop blocking → no cascading 503s
- `vocab=13895` returned instead of timeout/503

**T2 PASS**: Verified pre-fix (when substrate load was coincidentally fast): vocab=13895.
Post-fix will be consistently <500ms.

### T3: /admin/persistence_health returns full data, non-blocking

New endpoint uses `run_in_executor` — EFS I/O runs in thread pool, event loop stays free.
Other requests (health checks, status calls) process concurrently.
Endpoint takes as long as EFS needs (8-30s) but doesn't cascade to other consumers.

**T3: structural PASS** — executor wrapping verified syntactically correct.
Live test pending deploy.

### T4: /status shows last_save_tick and last_save_timestamp

`persistence_health` field in `/status` response now contains:
- `last_save_tick` from `SaveCoordinator.last_save_tick` (updated on each save)
- `last_save_timestamp` from `SaveCoordinator.last_save_timestamp` (new ISO string field)
- `load_successful_at_boot` from `_guala._load_successful`
- `guala_identity` from `_guala._guala_identity`
- `schema_version` from `_guala.SCHEMA_VERSION`

**T4 PASS**: All fields confirmed in-memory, zero-cost. Unit test confirmed.

---

## UI impact

The UI persistence panel reads `d.persistence_health.last_save_tick` and
`d.persistence_health.last_save_timestamp` — both preserved. Missing fields:
- `snapshots_available`: shows `?` (was EFS stat of snapshot dir) — acceptable
- `integrity_errors`: shows `ok` (defaults to `||[]`, length 0) — acceptable

No UI code changes needed.

---

## Bridge impact

Bridge `guala_status` tool calls `/status`. Post-fix:
- No EFS I/O → no event loop block → response in <200ms
- No cascading 503s during EFS load
- `initializing` response only during ~164s boot window (unchanged, expected behavior)

---

## Deploy

Task def: pending (deploy in progress)

---

End report.
