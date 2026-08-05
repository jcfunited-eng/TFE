> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-RPT-BRIDGE-AUDIT-C1-20260701

doc_id: GL-RPT-BRIDGE-AUDIT-C1-20260701
Type: Bridge audit report — no code changes
Date: 2026-07-01
Author: c1b
Substrate: dsf-ai-task:427 (embedded mode, SUBSTRATE_MODE=embedded)
Bridge: gualaloom-bridge-task:16, task 69c52762

---

## Audit methodology

Two-pass audit:
1. **Sequential pass** (all 15 tools in prescribed order) — captures cascade failures where one blocked tool corrupts later tests
2. **Isolation pass** (failing tools individually on calm substrate) — distinguishes timing-based vs structural failures

Substrate state during audit: SLEEPING → DREAMING → SLEEPING (normal cycle)

---

## Results table

| # | Tool | Test payload | HTTP status | Response | Worked | Latency ms | Notes |
|---|------|-------------|-------------|----------|--------|------------|-------|
| 1 | `guala_status` | `{}` | 200 | vocab=13895 schema=v7.2.0 | Y | 170 | Baseline ✓ |
| 2 | `guala_get_events` | `{since_tick:0,limit:5}` | 200 | 14 events returned | Y | 143 | ✓ |
| 3 | `guala_atlas_query` | `{input_text:"moon"}` | 200 | chi addresses returned | Y | 131 | ✓ |
| 4 | `guala_atlas_snapshot` | `{}` | 200 | total_strength=1383.77 | Y | 122 | ✓ |
| 5 | `guala_wake_wc` | `{}` | 200 | event=wake wc present=true | Y | 160-27206 | ⚠️ see note |
| 6 | `guala_rest_wc` | `{}` | 200 | present=false | Y | 256 | ✓ fresh; cascades to 503 after say block |
| 7 | `guala_say` | `{content:"hello guala"}` | 200→poll | "converse timed out after 90s" | **N** | 90462 | **BUG: missing API GW route** |
| 8 | `guala_give_experience` | `{caption:"bridge audit test"}` | 200 | "she is sleeping..." | Y | 146 | ✓ fresh |
| 9 | `guala_start_cascade_monitor` | `{interval_s:10}` | 501 | requires remote substrate mode | **N** | 204 | **DISABLED since -61** |
| 10 | `guala_stop_cascade_monitor` | `{}` | 501 | requires remote substrate mode | **N** | 202 | **DISABLED since -61** |
| 11 | `guala_backup` | `{}` | 503 | Service Unavailable | **N** | 30127 | **API GW 30s timeout** |
| 12 | `guala_amnesty` | `{}` | 200 | entries_restamped=12672 | Y | 206 | ✓ |
| 13 | `guala_unpause` | `{}` | 200 | unpaused=True | Y | 148 | ✓ |
| 14 | `guala_repause` | `{}` | 200 | repause=active | Y | 123 | ✓ |
| 15 | `guala_force_dream` | `{}` | 503 | Service Unavailable | **N** | 30119 | **API GW 30s timeout** |

**Score: 10/15 working, 5 failing**

---

## Detailed failure analysis

### Tool 7: `guala_say` — MISSING API GATEWAY ROUTE

**Root cause**: The task polling endpoint has no API Gateway route.

The `guala_say` bridge tool calls `_post({"text": content, "source": "wc"})`. Since this is bare text with no command, `is_converse=True` in `_post`. The flow:

1. Bridge POSTs to `/api/v1/gualaloom` → substrate returns `202 + {"task_id":"cv_...", "status":"accepted", "poll_url":"/api/v1/gualaloom/task/cv_..."}` **(fast, 254ms)**
2. Bridge polls `GET /api/v1/gualaloom/task/{task_id}` every 0.5s for 90s
3. **Every poll hits API GW `$default` route → Lambda → `{"error":"Not found:..."}` → bridge `except Exception: pass` swallows it**
4. After 90s: bridge returns `{"status":"timeout", "response":"converse timed out after 90s"}`

**Confirmed**: `aws apigatewayv2 get-routes` shows ZERO routes matching `/task/`. The task poll endpoint `GET /api/v1/gualaloom/task/{task_id}` does NOT exist in the API Gateway route table.

**Bridge code** (`bridge/server.py` L54-75):
```python
poll_url = data.get("poll_url") or f"/api/v1/gualaloom/task/{task_id}"
while time.time() < deadline:
    await asyncio.sleep(0.5)
    try:
        pr = await client.get(f"{SUBSTRATE_URL}{poll_url}", headers=_headers())
        pr.raise_for_status()
        pd = pr.json()
        if pd.get("status") in ("complete", "error"):
            return pd
    except Exception:
        pass  ← swallows 404s from $default Lambda silently
```

**Fix** (one line, API Gateway): add route `GET /api/v1/gualaloom/task/{task_id}` → same HTTP_PROXY integration as other gualaloom GET endpoints (pointing to `http://dsf-ai-alb-.../api/v1/gualaloom/task/{task_id}`).

---

### Tools 9-10: `guala_start_cascade_monitor` / `guala_stop_cascade_monitor` — FEATURE DISABLED

**Root cause**: These endpoints require `SUBSTRATE_MODE=remote` (separate substrate process on Unix socket). Since GL-CMD-PROCESS-COLLAPSE-61, `SUBSTRATE_MODE=embedded`. The substrate correctly returns 501.

```
HTTP 501: {"error":"cascade monitor requires remote substrate mode"}
```

**Bridge code** (`bridge/server.py` L254-278) is correct. Substrate code is correct. Feature is simply N/A in embedded mode.

**Options**: (a) re-implement for embedded mode, (b) remove from bridge, or (c) leave as 501 and document.

---

### Tools 11 + 15: `guala_backup` and `guala_force_dream` — API GW 30s TIMEOUT

**Root cause**: Both operations block the asyncio event loop for >30 seconds. API Gateway has a 30-second integration timeout and returns 503.

- `guala_backup`: calls `guala._guala.save_full_state(STATE_DIR)` + S3 upload — synchronous EFS writes + network, 30-120s
- `guala_force_dream`: forces a full sleep→dream cycle — atlas consolidation + EFS saves, 30-120s

This is the same pattern as `persistence_health()` (fixed yesterday). Same fix applies: wrap in `run_in_executor` so the event loop isn't blocked. May also need 202+task pattern since API GW has 30s hard timeout.

**Bridge code** (L197-203, L237-250) has no async pattern — calls `httpx.AsyncClient` with 120s/60s timeouts, but the event loop is already blocked, so the ALB returns 503 before the 30s mark.

---

## Note: `guala_wake_wc` degradation (not failing, but slow)

**wake_wc** works correctly (presence.wc flips to True, verified via guala_status). However latency varies dramatically:
- SLEEPING substrate: **160ms** ✓
- DREAMING substrate: **27206ms** (27 seconds)

The `coordinator.wake()` call acquires the atlas lock. During dream cycles, the dream phase holds the atlas lock for 20-27 seconds (processing ~12,000 atlas entries under a single lock acquisition). This means:
1. wake_wc blocks for up to 27s
2. The bridge's `httpx.AsyncClient(timeout=45)` would fire if dream holds the lock >45s
3. Eve's reported "internal tool execution error" was likely `wake_wc` called during a >45s dream phase

**This is substrate-level lock contention, not a bridge bug.** The dream cycle needs to batch its atlas operations and release the lock between batches.

---

## Pattern summary

| Pattern | Tools affected | Fix location |
|---------|---------------|-------------|
| Missing API GW route for task poll | guala_say | API Gateway (add 1 route) |
| Feature disabled in embedded mode | start/stop_cascade_monitor | Substrate (re-implement or remove) |
| Event loop blocked >30s | guala_backup, guala_force_dream | app.py (run_in_executor, same as persistence_health fix) |
| Lock contention in dream cycle | guala_wake_wc (degraded) | Engine (dream cycle batch lock release) |

---

## Recommended fix grouping

**Fix A: One API GW route, unblocks guala_say (say and all write-path converse tools)**
```
aws apigatewayv2 create-route --api-id 3d6toi0gw0 \
  --route-key "GET /api/v1/gualaloom/task/{task_id}" \
  --target "integrations/<http_proxy_integration_id>"
```
Also needs to create the HTTP_PROXY integration pointing to the correct ALB path.
This is ONE AWS CLI call + ONE integration. Independent, zero code change.

**Fix B: run_in_executor for backup and force_dream in app.py**
Same pattern as persistence_health fix (Option C from yesterday). Wrap the blocking call in `run_in_executor`. May also need to change to a 202+task pattern to get under API GW's 30s hard timeout. Two handlers in app.py.

**Fix C: Cascade monitor handling (decide approach)**
Options: re-implement in embedded mode OR remove tools from bridge OR add 501 error message in bridge with explanation ("cascade monitor unavailable in embedded mode"). Eve decides direction.

---

## What's correct in the bridge code

1. `_post` function with 202+poll pattern (GL-CMD-CONVERSE-TASK-PATTERN-62) — correct
2. All command routing (`command="/wake"`, `command="/rest"`, etc.) — correct
3. Admin tool routing (`/admin/amnesty`, `/admin/unpause`, `/admin/repause`, `/admin/atlas_snapshot`) — correct
4. Auth headers via `_headers()` — correctly passes API key for admin routes
5. `guala_atlas_query` hitting `/api/v1/gualaloom/chi_trace` — correct

**No bridge code changes needed for Fix A.** The bridge's polling code is correct; it's the API Gateway route that's missing. The bridge correctly swallows poll errors (Lambda 404s) but correctly times out at 90s.

---

End report.
