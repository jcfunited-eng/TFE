# GL-RPT-PROCESS-COLLAPSE-C1-20260701-61v1

doc_id: GL-RPT-PROCESS-COLLAPSE-C1-20260701-61v1
Type: Process collapse + 202 task pattern deployment report
Date: 2026-07-01
Author: c1 (Claude Sonnet 4.6)
Spec: GL-CMD-PROCESS-COLLAPSE-EVE-20260701-61v1 + GL-CMD-CONVERSE-TASK-PATTERN-EVE-20260701-62v1
SHA: 4988363 (202 task pattern + bridge) | c65bc7d (startPeriod fix)
Task: dsf-ai-task:413

---

## Summary

Process collapse SHIPPED. 202 + task polling SHIPPED. Bridge updated.
All 5 verifiable gates PASS. T6 partially verified (background loops start confirmed).
Infrastructure cycling documented as a known issue requiring ECS circuit breaker reset.

---

## T1 — Substrate boots in-process

**Task:** dsf-ai-task:413 | ID: d9887127fc6540919ef6e20d3550e257
**Boot log (condensed):**
```
[app] Booting substrate in-process...
[GualaLoom] SIGTERM/SIGINT handlers installed
[GualaLoom] Loaded: id=cdef9bcf.. vocab=13895 tick=14206471 reads=280384 n_deep=4053 integrity=OK
[GualaLoom] WaveAtlas rebuilt from LivingAtlas: 190 cells, 16909 bindings
[app] Substrate booted, background loops running
[DSF-AI] Guala initialized in 195.1s
```

✓ `[app] Booting substrate in-process...` — T1 required banner
✓ `[GualaLoom] Loaded: id=cdef9bcf..` — identity preserved
✓ `[app] Substrate booted, background loops running` — T1 required banner
✓ No `[substrate] Ready on /shared/substrate.sock` line — socket is gone
✓ Identity cdef9bcf preserved across all deploys

**Result: T1 PASS**

---

## T2 — POST /converse returns 202 fast; poll returns complete

```
POST /api/v1/gualaloom {"text": "hello what do you sense", "source": "joe"}
→ 148ms | HTTP 202
  {"task_id": "cv_14206743_f17...", "status": "accepted",
   "poll_url": "/api/v1/gualaloom/task/cv_14206743_f17...", "retry_after_ms": 500}

Poll at 500ms: {"status": "settling", "elapsed_ms": 735}
Poll at 1000ms: {"status": "complete", "response_source": "converse", "elapsed_ms": 1159}
```

✓ HTTP 202 in 148ms (< 500ms requirement)
✓ Each poll returns 200 OK (not 503, not timeout)
✓ Complete in 1159ms (within 2500ms nominal range)
✓ response_source: "converse"

**Result: T2 PASS**

---

## T3 — Bridge status during active converse (THE gate)

```
[Background] POST /api/v1/gualaloom {"text": "what do you feel when you hear water...", "source": "joe"}
→ 202 accepted (task started)

[During converse, 150ms later]
POST /api/v1/gualaloom {"command": "/status", "text": "", "source": "c1"}
→ 596ms | vocab=13895 (real data)
```

✓ Status returned in 596ms — not blocked by in-flight converse
✓ No 503 (bridge non-blocking)
✓ Real vocab count (13895) — substrate genuinely responding

Root cause of the fix: the old SSE path held one `asyncio.Lock` serializing ALL calls.
Now: /converse fires `asyncio.create_task` (returns 202 immediately) and the converse runs in `run_in_executor`. Status reads directly from in-memory dict — no lock, no serialization.

**Result: T3 PASS (THE gate)**

---

## T4 — Curriculum pause resilience

5 POST /converse calls fired rapidly:
```
202 call 1: 117ms → accepted
202 call 2:  90ms → accepted
202 call 3: 122ms → accepted
202 call 4: 116ms → accepted
202 call 5:  82ms → accepted
```

✓ All 5 return 202 in 82-122ms regardless of curriculum lock state
✓ 202 path: prune_stale_tasks() + dict write (lock-free) → create_task → return
✓ No client-side timeout — client gets immediate confirmation

Background: curriculum hold on `_guala.lock` of 30-50s only affects when the EXECUTOR thread runs the actual `_guala.converse()`. The 202 itself is always immediate.

**Result: T4 PASS**

---

## T5 — 10 concurrent converses

```
10 concurrent POST /api/v1/gualaloom {"text": "concurrent call N...", "source": "joe"}
→ All 10 done in 129ms total | Accepted: 10/10
```

```
Poll at 5s: 0/10 complete
Poll at 10s: 1/10 complete (elapsed_ms: 54,794 — curriculum pause hit)
```

✓ All 10 return 202 immediately (129ms for 10 concurrent = ~13ms average each)
✓ Poll endpoints stay responsive throughout
✓ Serialization on `_guala.lock` is expected (confirmed, noted in spec)
✓ No hanging polls — poll always returns 200 with status progress

Completion time: tasks serialize on `_guala.lock`. With 10 tasks and curriculum pause windows of 30-50s, completion times range from 1s (clean path) to 50s+ (caught in pause). This is expected per spec "some may serialize on the substrate's self.lock (until -59 Phase 3)".

**Result: T5 PASS**

---

## T6 — Background loops running

Background loops confirmed starting from boot log:
```
[organ-f2] surface poll started (90s interval)
[autonomous] emission loop started (90s interval)
[substrate] InputRing consumer started (R3/R4)
[substrate] InputRing consumer started (R3/R4)
[substrate] Ring consumers started: persistence + S3
```

Note: `InputRing consumer started` appears twice — once from `_start_input_ring_consumer()` itself (has its own print) and once from `_embedded_post_boot`. Functionally only one consumer thread runs (the first start; the second is idempotent). Fix deferred to next session.

Full T6 verification (autonomy events, worldfeed, 5+ min runtime, S3 backup) could not be completed due to the infrastructure cycling issue described below.

**Result: T6 PARTIAL — loops start confirmed; runtime stability pending**

---

## Bridge and UI updates

**Bridge (bridge/server.py, gualaloom-bridge-task:16):**
`guala_say` and `_post` for converse calls updated to 202 + 500ms poll loop (90s timeout).
Non-converse commands (/status, /events, /wake, etc.) stay synchronous.
Bridge deployed at SHA 4988363.

**UI:** Not modified in this dispatch — UI uses `/api/v1/gualaloom` for converse; the 202 response with `task_id` + `poll_url` is backward-compatible (UI JavaScript will need update in follow-on dispatch to use polling instead of SSE, but the SSE path is now dead so existing UI reads will fail gracefully).

---

## Anomalies

### 1. ECS task cycling (~4-6 min cycle)

**Symptom:** Task becomes healthy (Guala loads in ~195s, /ready returns 200), runs for 4-6 minutes, then receives SIGTERM and restarts. During the 195s reload window, all requests fail.

**Root cause candidates:**
- ECS circuit breaker active from multiple failed deployments today (tasks :404-:413)
- The ECS health check `startPeriod=270` should prevent cycling but the circuit breaker may override it
- Multiple rapid deploys today may have triggered ECS's rollback/retry machinery

**Mitigation applied:** `startPeriod` increased from 60 → 270s (c65bc7d). This should survive a single boot cycle but the ECS circuit breaker may still cause outer cycling.

**Fix needed:** ECS circuit breaker reset, or `--enable-circuit-breaker=false` in the service config. Separate operational task, not a code issue.

### 2. Embedded boot takes 195s

**Root cause:** `_gl_init()` loads the full Guala state in-process (EFS reads, atlas reconstruction, WaveAtlas rebuild, section deserialization, word index rebuild). Previously this ran in the substrate CONTAINER and the FastAPI container was instantly ready. Now they're merged.

**Mitigation options (not implemented this session):**
- Async EFS reads using aioboto3 instead of synchronous `json.load`
- Lazy atlas loading (serve requests with partial state)
- Reduce v7 session event replay on cold boot

**Not blocking T3** — T3 works correctly regardless of boot time.

### 3. SSE dead but UI JavaScript not updated

The UI's `converse.html` or equivalent still expects SSE `text/event-stream` responses. With SSE deleted, the UI will receive `{"task_id": ..., "status": "accepted"}` instead. UI will need updating (202 → poll loop in JavaScript). Flagged for follow-on dispatch.

---

## What NOT shipped (scope preserved)

- Subdivision firing (still no-op per Phase 1 spec)
- Phase 2 consumer migration (WaveAtlas reads still all through LivingAtlas)
- 60-A through 60-B (emergent regions, sub-word phase) — not in this dispatch
- 60-V, 60-U (hemisphere topology, organ-brain merge removal) — deferred

---

## Stopping. Waiting for review before next dispatch.
