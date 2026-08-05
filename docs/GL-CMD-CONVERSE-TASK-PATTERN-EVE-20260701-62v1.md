# GL-CMD-CONVERSE-TASK-PATTERN-EVE-20260701-62v1

doc_id: GL-CMD-CONVERSE-TASK-PATTERN-EVE-20260701-62v1
Type: Architecture change + implementation command
Date: 2026-07-01 (UTC)
Author: Eve (Opus 4.7, web)
Handoff: **Give this entire dispatch to c1a as one message. One commit. One deploy.**
Repo: `jcfunited-eng/TFE` branch `guala-live`
Supersedes: 60-O (streaming SSE was wrong — see §0)

---

## 0. Why

SSE for /converse was theater. There is no incremental substrate output today — `_guala.converse()` is a single blocking call that returns the final response as its return value. SSE was sending fake "processing" events between initial receipt and the final complete event, holding the HTTP connection open the whole time. That broke the bridge (its HTTP client hangs waiting for the stream) and made the empty responses you're seeing (client timeout hits before the "complete" event fires).

The industry pattern for this exact class of problem — long-running server work where the server can't respond synchronously — is **202 Accepted + task polling**. Used by AWS batch APIs, Stripe async, OpenAI batch, Anthropic batch, GitHub workflow runs. It fits Guala's substrate physics too:

- Substrate operates on tick time, not HTTP time
- `converse_timing` event already reports real phase progression (recall_ms, tag_ms, read_ms, emit_ms, etc)
- Substrate keeps working whether client is watching or not
- Client's polling clock and substrate's tick clock are independent (brain-analogous — visual cortex doesn't wait for you to look at it)

This dispatch retires SSE for /converse, replaces it with 202 + poll. Generalizes cleanly to other slow substrate ops (`/sleep_for_deploy`, `/backup`, `/atlas_surgery`) as a future consolidation, not this dispatch.

---

## 1. Architecture

### 1.1 Task registry (in-process)

```python
# In app.py or a new dsf_ai_service/task_registry.py
from typing import Dict, Any, Optional
from uuid import uuid4
import time

_converse_tasks: Dict[str, Dict[str, Any]] = {}
_TASK_TTL_SECONDS = 300  # 5 min after complete before GC


def _prune_stale_tasks():
    """Remove completed tasks older than TTL. Called opportunistically."""
    now = time.time()
    to_delete = [
        tid for tid, task in _converse_tasks.items()
        if task["status"] in ("complete", "error")
        and (now - task.get("completed_at", now)) > _TASK_TTL_SECONDS
    ]
    for tid in to_delete:
        del _converse_tasks[tid]
```

Registry lives in the FastAPI process (which now IS the substrate process post-collapse). No Redis, no external state, no persistence — tasks are ephemeral. If the process restarts, in-flight tasks are lost. Acceptable: same behavior as today with in-flight substrate work.

### 1.2 POST /api/v1/gualaloom — starts a task

The old /converse endpoint becomes the task-start endpoint. Returns immediately with 202.

```python
@app.post("/api/v1/gualaloom", status_code=202)
async def start_converse(msg: GualaMessage):
    # Handle non-converse commands (/status, /events, /sleep, etc) same as before —
    # those stay synchronous. Only "empty command + text" (the plain converse path)
    # switches to 202 pattern.

    is_converse = not (msg.command or "").strip() and bool(msg.text)

    if not is_converse:
        # Fall through to existing synchronous command handling
        return await _handle_command(msg)

    # Converse path: 202 + task
    _prune_stale_tasks()

    task_id = f"cv_{_guala.tick}_{uuid4().hex[:8]}"
    now = time.time()
    _converse_tasks[task_id] = {
        "task_id": task_id,
        "status": "queued",
        "phase": None,
        "response": None,
        "response_source": None,
        "started_tick": _guala.tick,
        "started_at": now,
        "text": msg.text[:200],  # for debugging, not returned
        "source": msg.source or "unknown",
    }

    # Fire the substrate work
    asyncio.create_task(_run_converse(task_id, msg.text, msg.source or "unknown"))

    return JSONResponse(
        status_code=202,
        content={
            "task_id": task_id,
            "status": "accepted",
            "poll_url": f"/api/v1/gualaloom/task/{task_id}",
            "started_tick": _guala.tick,
            "retry_after_ms": 500,  # client polling hint
        }
    )


async def _run_converse(task_id: str, text: str, source: str):
    """Run substrate converse in executor, update task registry with progress."""
    task = _converse_tasks.get(task_id)
    if task is None:
        return

    loop = asyncio.get_event_loop()
    task["status"] = "settling"
    task["phase"] = "queued"

    try:
        # Update phase when substrate starts working on it.
        # If _guala.converse supports a phase-callback in a future dispatch,
        # wire it here. For now, "processing" until complete.
        task["phase"] = "processing"

        result = await loop.run_in_executor(
            None,
            lambda: _guala.converse(text, source=source)
        )

        # log_event moved to executor too — EFS write shouldn't block event loop
        await loop.run_in_executor(
            None,
            lambda: _guala.log_event(STATE_DIR, "converse",
                                     text=text[:200], source=source,
                                     response=str(result)[:200])
        )

        task["status"] = "complete"
        task["response"] = result if isinstance(result, str) else str(result)
        task["response_source"] = getattr(_guala, "_last_response_source", "converse")
        task["completed_tick"] = _guala.tick
        task["completed_at"] = time.time()

    except Exception as e:
        task["status"] = "error"
        task["error"] = str(e)[:500]
        task["completed_at"] = time.time()
```

### 1.3 GET /api/v1/gualaloom/task/{task_id} — poll for result

```python
@app.get("/api/v1/gualaloom/task/{task_id}")
async def get_converse_task(task_id: str):
    task = _converse_tasks.get(task_id)

    if task is None:
        return JSONResponse(
            status_code=404,
            content={
                "task_id": task_id,
                "status": "not_found",
                "error": "task_id not found (may have expired after 5 min TTL)"
            }
        )

    # Complete — return the response
    if task["status"] == "complete":
        return JSONResponse(status_code=200, content={
            "task_id": task_id,
            "status": "complete",
            "response": task["response"],
            "response_source": task["response_source"],
            "started_tick": task["started_tick"],
            "completed_tick": task.get("completed_tick"),
            "elapsed_ms": int((task.get("completed_at", time.time()) - task["started_at"]) * 1000),
        })

    # Error — return the error
    if task["status"] == "error":
        return JSONResponse(status_code=200, content={
            "task_id": task_id,
            "status": "error",
            "error": task["error"],
        })

    # Still working — return progress
    return JSONResponse(status_code=200, content={
        "task_id": task_id,
        "status": task["status"],
        "phase": task["phase"],
        "started_tick": task["started_tick"],
        "current_tick": _guala.tick,
        "elapsed_ms": int((time.time() - task["started_at"]) * 1000),
        "retry_after_ms": 500,
    })
```

### 1.4 Delete SSE machinery

- Delete the SSE StreamingResponse handler in the old /converse path
- Delete `_readConverseSSE` in the UI JavaScript, replace with the two-call polling pattern
- Delete `_converse_client` — no more dedicated SSE client
- Keep `_substrate_client` (used for non-converse commands and the shim into substrate ops)

---

## 2. Client updates (bridge + UI)

### 2.1 Bridge (gualaloom-bridge)

`guala_say` and any other bridge tool that uses the converse path must be updated to:

1. POST `/api/v1/gualaloom` with `{text, source}` — receive 202 + task_id
2. Poll GET `/api/v1/gualaloom/task/{task_id}` every 500ms
3. When response contains `"status": "complete"` — return `response` to Claude
4. If polling exceeds 60 seconds — return timeout message (Guala may still be settling; user can retry)

Bridge code lives in `dsf_ai_service/bridge_mcp.py` (or wherever gualaloom-bridge is defined — c1a: locate and update).

### 2.2 UI (static/converse.html or wherever)

Same pattern in JavaScript. Fetch POST → get task_id → setInterval polling → clear interval on complete or error. Reference implementation:

```javascript
async function converse(text, source) {
  const startResp = await fetch('/api/v1/gualaloom', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({text, source})
  });
  const start = await startResp.json();
  const taskId = start.task_id;

  return new Promise((resolve, reject) => {
    const startTime = Date.now();
    const poll = async () => {
      const resp = await fetch(`/api/v1/gualaloom/task/${taskId}`);
      const data = await resp.json();
      if (data.status === 'complete') {
        resolve(data);
      } else if (data.status === 'error') {
        reject(new Error(data.error));
      } else if (Date.now() - startTime > 60000) {
        reject(new Error('timeout'));
      } else {
        setTimeout(poll, 500);
      }
    };
    setTimeout(poll, 500);
  });
}
```

---

## 3. Non-converse paths stay synchronous

`/status`, `/events`, `/sleep`, `/backup`, `/wake`, `/rest`, `/repause`, `/unpause`, `/atlas_snapshot`, all admin commands — these stay synchronous 200 OK responses.

Rationale: they're fast (introspect, event log read) or they're operational (sleep/backup) with existing sync semantics. Migrating them to 202 pattern would be a follow-on cleanup, not this dispatch.

Only the `is_converse` path (no command + text) becomes 202.

---

## 4. Test gates

### T1 — POST /converse returns 202 fast

```
curl -w "\ntime:%{time_total}s\n" -X POST https://[api]/api/v1/gualaloom \
  -H 'Content-Type: application/json' \
  -d '{"text": "hello", "source": "joe"}'
```

PASS:
- HTTP 202
- Response body contains `task_id`, `status: "accepted"`, `poll_url`, `retry_after_ms`
- `time_total < 0.5s`

### T2 — GET /task/{task_id} returns progress then complete

Send /converse, capture task_id, poll `/task/{task_id}` every 500ms until status != accepted/settling.

PASS:
- Each poll returns 200 OK (never 503, never empty body, never timeout)
- Poll during settling returns `{"status": "processing", "phase": "processing", ...}`
- Eventually returns `{"status": "complete", "response": "...", "elapsed_ms": N}`
- `elapsed_ms` matches actual substrate work time (~1500-2500ms for a simple converse)

### T3 — Bridge status during active converse (THE gate)

Send a /converse task. While it's settling (poll status = processing), send bridge `guala_status`.

PASS:
- Bridge status returns 200 with real data
- No 503
- Both requests independent — neither blocks the other

### T4 — Curriculum pause resilience

During a curriculum chunk (which holds _guala.lock for 30-50s), send /converse. Poll for result.

PASS:
- POST /converse still returns 202 immediately (task registry write is lock-free)
- Task registry shows the task queued, then settling once lock releases
- Eventually completes
- No client-side timeout up to 90 seconds

### T5 — Task registry TTL

Send /converse, wait for complete, then wait 5+ minutes, then poll /task/{task_id}.

PASS:
- Returns 404 with `"status": "not_found"` after TTL expires
- Registry doesn't grow unboundedly

### T6 — 10 concurrent converses

Fire 10 /converse calls, capture all task_ids, poll each until complete.

PASS:
- All 10 return 202 immediately
- All 10 eventually complete (may serialize on _guala.lock — expected until -59 Phase 3)
- Poll endpoints stay responsive throughout — no hanging polls

---

## 5. What NOT to do

- **Do not** keep the SSE path as a fallback. Delete it entirely. If we ever want streaming for real (60-G multi-stream emission), we'll re-add it purposefully.
- **Do not** add server-side long-polling on the task endpoint (holding the connection open until complete). That reintroduces the original problem.
- **Do not** persist the task registry to disk. Ephemeral is correct.
- **Do not** touch WaveAtlas, Guala engine, or process-collapse code. This is the /converse endpoint pattern only.

---

## 6. Rollback

Single commit. `git revert HEAD && ./tools/deploy_dsf_ai.sh`. State on disk is untouched. Bridge and UI can revert their client-side changes independently but should stay coordinated with server side.

---

## 7. Report

`GL-RPT-CONVERSE-TASK-PATTERN-C1-20260701-62v1.md`:
- SHA and task number of deploy
- T1-T6 results with actual latencies
- Bridge and UI client update SHAs (if separate commits)
- Any anomalies

---

## 8. What this enables next

Once this ships, we can migrate other slow substrate operations (`/sleep_for_deploy`, `/backup`, `/atlas_surgery`) to the same pattern. That's a small follow-on dispatch — same task registry, same poll endpoint, different substrate handlers. Consolidates the "long-running substrate op" pattern across the whole API.

When 60-G multi-stream emission ships and there's actual incremental content to stream, we upgrade the poll endpoint to return partial responses as they accumulate. Or add a WebSocket for real-time streaming. That's future work — this dispatch is the honest solution for what the substrate does today.

---

End.
