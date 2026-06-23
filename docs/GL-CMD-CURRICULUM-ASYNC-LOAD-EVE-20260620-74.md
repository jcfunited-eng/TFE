# GL-CMD-CURRICULUM-ASYNC-LOAD-EVE-20260620-74

**Doc ID:** GL-CMD-CURRICULUM-ASYNC-LOAD-EVE-20260620-74
**Author:** Eve
**Date:** 2026-06-20
**Type:** CMD (dispatch)
**Subject:** Replace synchronous `/api/v1/curriculum/load_corpus` with an async job pattern
**Refs:** GL-CMD-CURRICULUM-INFRASTRUCTURE-EVE-20260619-68, GL-CMD-CURRICULUM-BUILD-DISPATCH-EVE-20260620-69, GL-CMD-73 (implementation), b5d110e (deploy)

---

## Why this brief exists

GL-CMD-73 shipped synchronous load: client POSTs, server feeds N sentences through `read_sentence`, server returns aggregate response. The deploy cycle that surfaced this (tasks 229–234) revealed the synchronous shape collides with two hard limits:

1. **ALB idle timeout is 180s.** Confirmed live: `idle_timeout.timeout_seconds = 180`.
2. **RLock contention with the autonomy loop.** 107 sentences × `read_sentence` while the autonomy thread is taking 200ms ticks pushes total wall time past 180s. The 23f91ce patch (pause autonomy during bulk feed) works for Peter Rabbit. It will not survive a Khan Academy chapter or a Gutenberg novel.

The curriculum infrastructure spec (GL-CMD-68) anticipates six sources — Project Gutenberg, Khan Academy Kids, PBS Kids, Internet Archive, Spotify, YouTube. Any of them will produce single-corpus loads larger than 107 sentences. The synchronous shape will not carry us there.

This brief defines an async load pattern that decouples HTTP request lifetime from substrate work lifetime, without changing how the substrate processes sentences.

---

## Substrate-true check

Required before any code is written.

| Concern | Status |
|---|---|
| Does the brief change how `read_sentence` works? | No. Still one call per sentence, same source tag. |
| Does the brief introduce a batching shortcut that compresses sentence boundaries? | No. Sentences are fed one at a time, in order. |
| Does the brief introduce a heuristic load-rate throttle? | No. The substrate processes as fast as RLock contention allows. If too slow, that is substrate physics; it is not a knob to be tuned. |
| Does the brief introduce ML, learned policies, or hardcoded mechanism choices presented as physics? | No. The pattern is pure HTTP transport. |
| Is the 23f91ce autonomy pause preserved? | Yes. Pause-before-feed, resume-after-feed is the right primitive for bulk load. Async wraps around it; it does not replace it. |

**STOP if any of the above flips during implementation.** Write a substrate-true brief addressing the flip before continuing.

---

## The pattern

### POST `/api/v1/curriculum/load_corpus`

Same request body as GL-CMD-73 (corpus_id, title, lines OR url).

**Response:** `202 Accepted`, immediately, in <500ms.

```json
{
  "job_id": "<uuid4>",
  "corpus_id": "gutenberg-peter-rabbit",
  "n_sentences": 107,
  "state": "queued"
}
```

Server-side actions before responding:
- Validate corpus_id, title, lines/url (same validation as GL-CMD-73).
- If `lines` not supplied, fetch via existing executor path (3fbec41) **synchronously, with a 30s timeout** — this is a fast operation and worth surfacing fetch errors as HTTP errors rather than as a failed job. If fetch fails, return 502.
- If a job for this corpus_id is currently `queued` or `running`, return 409 Conflict with the existing job_id. (Idempotency: same corpus_id → same in-flight job; do not start a duplicate.)
- Register the job in an in-memory dict on the web container.
- Schedule the work via `asyncio.create_task(_run_load_job(job_id))`.
- Return 202.

### GET `/api/v1/curriculum/load_corpus/job/{job_id}`

**Response:** 200 if found, 404 if not.

```json
{
  "job_id": "...",
  "corpus_id": "gutenberg-peter-rabbit",
  "state": "running",
  "progress": {
    "n_fed": 47,
    "n_total": 107
  },
  "started_at": "2026-06-20T20:15:32Z",
  "completed_at": null,
  "result": null,
  "error": null
}
```

When `state == "complete"`, `result` carries the full GL-CMD-73 response body (corpus_id, n_sentences, n_new_vocab, reads_delta, atlas_strength_before/after/delta).

When `state == "failed"`, `error` carries the exception string. Progress reflects how far we got before the failure.

### State machine

```
queued → running → complete
                 → failed
```

No retry built in. Client decides whether to re-POST.

### Job lifecycle

- Job dict TTL: 1 hour after `completed_at` or `failed_at`. Background GC task cleans up.
- Total in-memory job dict capped at 100 entries. If full, oldest completed job is evicted before accepting new.

### Concurrency

Single in-flight load job per substrate. If a job is `queued` or `running`, second POST for a *different* corpus returns 409 Conflict. (Two concurrent bulk loads would race on the autonomy pause refcount and double the substrate work; not worth the complexity for V1.)

### Progress reporting

`_run_load_job` updates `progress.n_fed` after each batch of 10 sentences (or every sentence if `n_total < 20`). This is the only place batching exists; it is purely a progress-update granularity, not a substrate-feeding granularity. `read_sentence` is still called once per sentence.

### Autonomy pause refcounting

The 23f91ce patch pauses autonomy unconditionally. For async jobs we need a refcount, so concurrent legitimate uses of pause (load_corpus, manual_sleep, sleep_for_deploy) cooperate.

- Add `_guala._autonomy_pause_refcount` (int, default 0).
- `pause_autonomy_for_bulk()` increments; resumes only when decremented to 0.
- All current `_guala.stop_autonomy_loop()` callers updated to use the refcounted helper.

---

## Failure modes the pattern handles

| Scenario | Behavior |
|---|---|
| HTTP client drops connection mid-load | Substrate work continues. Result available at GET endpoint. |
| ALB 180s idle timeout | Client gets disconnected; polls GET endpoint instead. |
| Client polls before job completes | Returns `state: running` with progress. |
| Same corpus_id POSTed twice in flight | 409 with existing job_id (idempotency). |
| Different corpus_id POSTed while job running | 409 (single-job constraint). |
| Web container restart mid-load | Job lost. Documented limitation. corpus_id is the recovery key — client re-POSTs after restart; duplicate corpus_id registration is overwrite (current GL-CMD-73 semantics, preserved). |
| Substrate crashes mid-load | Job marked `failed`. Partial state persists (whatever sentences fed before crash are committed). |

---

## V1 — Implementation tasks (in order)

1. **Refcounted autonomy pause.** Replace direct `start_autonomy_loop`/`stop_autonomy_loop` calls in substrate_runner with refcounted helpers. Verify existing callers still work (sleep_for_deploy, the 23f91ce load_corpus path, any others — audit before changing).
2. **Job registry.** `dsf_ai_service/curriculum/job_registry.py` — in-memory dict, asyncio-safe, TTL-based GC.
3. **`_run_load_job` background task.** Takes job_id, corpus_id, lines. Pauses autonomy via refcount. Feeds sentences in chunks of 10 (or smaller) updating progress. Resumes autonomy on completion or exception. Updates job state.
4. **POST handler** rewrite. Validation → fetch (if url, 30s exec) → registry check → create job → `asyncio.create_task` → return 202.
5. **GET job handler.** Read from registry, return job dict.
6. **GC task.** Periodic (every 60s) cleanup of expired jobs.

---

## V2 — Identity + state verification

Run after deploy.

- `id == cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f`
- `schema == v7.2.0` (no schema bump needed; this is HTTP transport only)
- vocab matches pre-deploy
- atlas counts match pre-deploy

Pre-deploy state must be captured and posted in V2 of the report.

---

## V3 — Behavioral verification

### V3.a — Peter Rabbit via async pattern

```
POST /api/v1/curriculum/load_corpus
body: {corpus_id: "gutenberg-peter-rabbit-async-v3a", title: ..., lines: [...107 lines...]}

Expected: 202 in <500ms, body has job_id
```

Poll GET every 5s. Expected:
- First poll: `state: running`, `progress.n_fed > 0`
- Within 180s of POST: `state: complete`
- `result.n_sentences == 107`
- `result.n_new_vocab` documented
- `result.reads_delta` documented

### V3.b — Larger-than-ALB-timeout corpus

Pick any Gutenberg text >500 sentences (`/cache/epub/<id>/pg<id>.txt`). Load via async pattern. Document:
- 202 in <500ms (same)
- Total substrate wall time (must exceed 180s — this is the point)
- HTTP client never sees timeout
- GET poll returns progress increases
- Final `state: complete`

If V3.b cannot exceed 180s with the test corpus, pick a larger one. This case must be demonstrated, not assumed.

### V3.c — Conflict detection

```
POST corpus A → 202
POST corpus A again (while running) → 409 with same job_id
POST corpus B (while A running) → 409
```

### V3.d — Autonomy resume

After V3.a or V3.b completes:
- `_guala._autonomy_pause_refcount == 0`
- Autonomy ticks resume (check substrate logs for new `[v7-intro]` entries within 30s of completion)
- Subsequent `/v7/converse` calls work normally

### V3.e — Substrate-side event check

For each completed job, the substrate event log must show one `curriculum_loaded` event with matching corpus_id, n_sentences, reads_delta. This is the substrate-side ground truth that the work happened — independent of the HTTP path.

---

## Out of scope (deferred to separate briefs if needed)

- Multi-job concurrency (refcount design supports it, but the single-job constraint is enforced at the registry layer; lifting it is a V2 brief once we understand load patterns).
- Job persistence across web container restart.
- In-ECS URL fetching (ECS egress to Project Gutenberg is currently not reachable; document but do not fix in this brief).
- Streaming progress to the client (SSE/WebSocket). Polling is sufficient for V1.
- Retry policy. Failed jobs are the client's problem.

---

## Filing

c1 produces report `GL-RPT-CURRICULUM-ASYNC-LOAD-C1-20260620-01.md` (or next-day sequence if filed after midnight UTC) with V1 implementation summary + V2/V3 outputs. Filed means written, git added, committed, pushed.

If V1.x audit findings change the design, c1 stops and writes a follow-up brief before continuing.
