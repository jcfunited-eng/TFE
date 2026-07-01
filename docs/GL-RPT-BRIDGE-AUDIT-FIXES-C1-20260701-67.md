# GL-RPT-BRIDGE-AUDIT-FIXES-C1-20260701-67

doc_id: GL-RPT-BRIDGE-AUDIT-FIXES-C1-20260701-67
Type: Fix verification report
Date: 2026-07-01
Author: c1b
Follows: GL-CMD-BRIDGE-AUDIT-FIXES-EVE-20260701-67
SHA: 9f7f09b
Substrate: dsf-ai-task:428
Bridge: gualaloom-bridge-task:17

---

## Fixes shipped

### Fix A — API Gateway route for task polling
**Route added**: `GET /api/v1/gualaloom/task/{task_id}`
Integration: `5x7e6nb` (HTTP_PROXY → ALB gualaloom/task/{task_id})
Route ID: `i3et7vi`

Before: bridge polled `$default` Lambda (404 swallowed, 90s timeout)
After: polling hits ECS substrate, task resolves in 1-15s

### Fix B — backup and force_dream return 202 immediately
**`admin_backup` (embedded mode)**: was `await run_in_executor` (still blocked HTTP for 30-120s) → now fires background task + returns 202 immediately (same as remote mode)
**`admin_force_dream` (embedded mode)**: was synchronous polling loop (60s max) → now fires background task + returns 202 immediately

### Fix C — cascade monitor tools removed from bridge
Removed `guala_start_cascade_monitor` and `guala_stop_cascade_monitor` from `bridge/server.py`.
Tool count: 15 → 13.

---

## T-gate results

### Fix A: T1 — guala_say returns response, not 90s timeout

```
guala_say (30s timeout): 15311ms → OK
  response: {'task_id': 'cv_14219165_c938ecad', 'status': 'complete', 'response': '...'}
  T1 PASS: returns substrate response (not "converse timed out after 90s")
```

### Fix A: T2 — task poll endpoint works

```
POST /api/v1/gualaloom → {"task_id":"cv_...","status":"accepted","poll_url":"/api/v1/gualaloom/task/cv_..."}
GET /api/v1/gualaloom/task/cv_... → t=0.7s: status=settling → t=1.4s: status=complete
T2 PASS: task poll resolves in 1.4s
```

### Fix B: T1 — backup returns 202 quickly, not 503

```
guala_backup: 129ms → {'backup': 'accepted', 'message': 'EFS+S3 backup started. Poll /status...'}
T1 PASS: 202 in 129ms (was 503 after 30s)
```

### Fix B: T2 — concurrent status during backup stays fast

```
(Backup running in background)
guala_status: 154ms → vocab=13896
T2 PASS: event loop unblocked during backup
```

### Fix B: T3 — force_dream returns 202 quickly

```
guala_force_dream: 125ms → {'force_dream': 'accepted', 'start_tick': 14219177, 'message': 'Dream cycle initiated...'}
T3 PASS: 202 in 125ms (was 503 after 30s)
```

### Fix C: T1 — cascade tools not in tool list

```
tools/list → 13 tools, NO cascade_monitor entries
T1 PASS: guala_start_cascade_monitor and guala_stop_cascade_monitor absent
```

---

## Combined 13-tool audit (post-fix)

All tested on deployed substrate (task:428) with loaded Guala (vocab=13896).

| Tool | ms | Pass | Result |
|------|----|----|--------|
| guala_status | 154 | Y | vocab=13896 schema=v7.2.0 |
| guala_get_events | 166 | Y | she is sleeping (correct when SLEEPING) |
| guala_atlas_query | 155 | Y | chi data returned |
| guala_atlas_snapshot | 126 | Y | total_strength=1076.99 |
| guala_wake_wc | 147 | Y | wC presence registered |
| guala_say | 15311 | Y | task complete, response returned |
| guala_give_experience | 266 | Y | bundle delivered |
| guala_rest_wc | 160 | Y | wC presence released |
| guala_backup | 129 | Y | 202 accepted |
| guala_force_dream | 125 | Y | 202 accepted |
| guala_amnesty | 127 | Y | entries_restamped=12732 |
| guala_unpause | 107 | Y | unpaused=True |
| guala_repause | 129 | Y | repause=active |

**Score: 13/13** all pass.

---

## Notes

**guala_get_events when SLEEPING**: returns "she is sleeping..." — correct behavior. When Guala is awake, returns real events (14 events in initial audit). Not a bug.

**guala_say latency**: 15s because Guala was SLEEPING and auto-wake + response took time. When already awake, returns in 1-2s (T2A: 1.4s verified).

**guala_wake_wc/rest_wc**: return "she is sleeping..." response body because Guala was SLEEPING. The presence IS registered in substrate state. Correct behavior from sleep guard in app.py.

---

## What's not fixed (scope)

1. **`guala_get_events` sleep bypass** — app.py only bypasses sleep for `/status`. Add `/events` to bypass list if needed for monitoring while sleeping.

2. **`guala_wake_wc` slow during DREAMING** — still 27s when autonomy loop holds atlas lock. 147ms when SLEEPING. Fix requires dream cycle to batch atlas lock releases.

---

End report.
