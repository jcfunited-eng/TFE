# GL-RPT-BRIDGE-INVESTIGATION-C1-20260701

doc_id: GL-RPT-BRIDGE-INVESTIGATION-C1-20260701
Type: Investigation report
Date: 2026-07-01
Author: c1b
Task: Bridge MCP "initializing" / error investigation

---

## Summary

**Bridge code is correct. Root cause is in the substrate — not the bridge.**

The bridge `guala_status` returns "initializing" or 503 errors because the substrate's
`/api/v1/gualaloom` endpoint (when called with `command="/status"`) blocks the asyncio
event loop for 10-30 seconds due to synchronous EFS file I/O inside `persistence_health()`.

This is an architectural issue in `app.py`. The bridge is stateless and correct.

**STOP SIGNAL**: Fix requires `app.py` change — Eve reviews before structural changes.

---

## Step 1: Bridge repo located

`/workspaces/Tao_Financial_Engine/bridge/server.py` — 301 lines.
Bridge ECS: `tfe-web-cluster` / `gualaloom-bridge-svc` / task definition `:16`.
Bridge image: `deploy-20260701T034824Z` (built from commit `4988363`).

---

## Step 2: Bridge code verified correct for 202+poll

The bridge `server.py` at commit `4988363` uses the correct pattern:

```python
async def _post(payload: dict) -> dict:
    is_converse = not (payload.get("command") or "").strip() and bool(
        (payload.get("text") or "").strip()
    )
    ...
    data = r.json()
    if not is_converse:
        return data  # commands synchronous
    # Converse: 202 + poll
    if data.get("status") != "accepted":
        return data
    task_id = data.get("task_id")
    poll_url = ...
    while time.time() < deadline:  # 90s
        await asyncio.sleep(0.5)
        pr = await client.get(f"{SUBSTRATE_URL}{poll_url}", ...)
        if pd.get("status") in ("complete", "error"):
            return pd
```

- `/converse` (bare text, no command): uses 202+poll ✓
- `/status`, `/events`, `/wake`, etc. (commands): synchronous ✓
- No caching, no state (`stateless_http=True`) ✓

**The bridge code is correct and does NOT need changes for -62 compliance.**

---

## Step 3: Bridge redeployed

```
aws ecs update-service --cluster tfe-web-cluster --service gualaloom-bridge-svc --force-new-deployment
```

New task `69c52762` started and reached steady state at 11:07:28 UTC.
Bridge logs show clean startup, no errors.

---

## Step 4: Bridge logs during redeploy

All bridge log entries during redeploy:
```
[07/01/26 11:07:28] INFO StreamableHTTP session manager started
INFO: Uvicorn running on http://0.0.0.0:8080
INFO: 172.31.62.243:58426 - "GET /mcp HTTP/1.1" 406 Not Acceptable
```

The 406 responses are ALB health checks (GET requests to /mcp — correct, MCP uses POST).
No errors, no panics. Bridge is healthy.

---

## Step 5: Root cause of "initializing" and errors

### When guala_status returns "initializing"

The bridge calls `POST /api/v1/gualaloom` with `{"command": "/status"}`. The substrate's
`gualaloom_chat` async function handles this. In embedded mode (process-collapse after -61):

```python
if cmd == "/status":
    s = _guala.introspect()
    ph = _guala.persistence_health(STATE_DIR)  ← BLOCKING EFS I/O
    ...
```

**`persistence_health()` does synchronous EFS stat() calls on multiple files:**
```python
def persistence_health(self, state_dir="state"):
    all_files = [self.IDENTITY_FILE] + self.STATE_FILES + self.REPORT_FILES
    present = [f for f in all_files if os.path.exists(os.path.join(state_dir, f))]
    ev_size = os.path.getsize(evlog) if os.path.exists(evlog) else 0
    snapshots = self.list_snapshots(state_dir)  # directory scan
```

EFS NFS stat() under load takes **8-30 seconds**. Since this runs in the asyncio event loop
thread (not in `run_in_executor`), it blocks ALL other requests during this time.

### Two failure modes:

**Mode A — "initializing" response:**
The substrate is loading (`_guala is None`). The app returns:
`{"response": "initializing... please wait", "n_motifs": 0}`
The bridge passes this through. This occurs for ~164 seconds after each task boot.

**Mode B — 503 Service Unavailable / errors:**
The substrate IS loaded but `/status` takes >10s due to EFS I/O blocking.
The API Gateway has a 30s timeout. When `persistence_health()` blocks the event loop,
new incoming requests (including /status calls) cannot be processed until it completes.
This causes apparent "503" or timeout errors even when `guala_ready=True` on `/ready`.

### Measured latency:

| Condition | guala_status latency |
|-----------|---------------------|
| Substrate loading (guala_ready=False) | Immediate "initializing" |
| Substrate loaded, EFS quiet | 14 seconds |
| Substrate loaded, EFS under load | 30+ seconds → timeout |
| Target per investigation brief | < 500ms |

---

## Step 6: guala_status returning real data (confirmed)

When the substrate IS loaded AND the EFS I/O happens to complete quickly, guala_status
returns correct data:
```
elapsed=14.08s vocab=13895 initializing=False
response=id: cdef9bcf.. | schema: v7.2.0 | vocab: 13895 | reads: 359615 | tick: 14211541
```

So the bridge is functionally correct — the data IS right. The issue is latency (14s vs <500ms).

---

## What needs fixing (ARCHITECTURAL — Eve reviews)

**Root cause**: `persistence_health()` called synchronously in the asyncio event loop
inside `app.py`'s `gualaloom_chat` handler for `/status`.

**Fix options** (all in `app.py`):

### Option A: Move persistence_health to run_in_executor (2-line change)
```python
if cmd == "/status":
    s = _guala.introspect()
    loop = asyncio.get_event_loop()
    ph = await loop.run_in_executor(None, _guala.persistence_health, STATE_DIR)
```
Unblocks event loop. Status calls will be ~14s EFS-wait but won't block other requests.
Doesn't meet <500ms target but prevents cascading failures.

### Option B: Cache persistence_health (TTL=5s)
```python
_ph_cache = None
_ph_cache_time = 0

if cmd == "/status":
    global _ph_cache, _ph_cache_time
    now = time.time()
    if not _ph_cache or (now - _ph_cache_time) > 5:
        _ph_cache = _guala.persistence_health(STATE_DIR)
        _ph_cache_time = now
    ph = _ph_cache
```
Amortizes EFS cost. First call takes 14s; subsequent calls return cached in <1ms.

### Option C: Remove persistence_health from /status (recommended for <500ms)
Move persistence health to a separate admin endpoint `/admin/persistence_health` polled
infrequently. The `/status` MCP tool doesn't need file system health to be useful.
```python
if cmd == "/status":
    s = _guala.introspect()
    # Return substrate state without EFS file check
    ph = {"last_save_tick": _guala._last_save_tick, ...}  # from memory only
```
Achieves <500ms consistently. Eve disciplines when to check actual file health.

---

## Current state

- Bridge: LIVE, correct code, redeployed at 11:07 UTC (task `69c52762`)
- Substrate: LIVE (task:426), loads in ~164s after each boot
- guala_status: functional but 14-30s latency due to EFS blocking
- "initializing" response: normal behavior during ~164s boot window

**No structural changes made to bridge or app.py. Awaiting Eve's decision on fix approach.**

---

End report.
