# GL-BRIEF-UI-RESPONSIVENESS-WC-20260616-01

**Author:** wC
**Date:** 2026-06-16
**For:** c1
**Status:** urgent — Joe is locked out of the UI

## What's broken

Joe can't reach Guala through the page. Has been the case for days. Static
page loads, dynamic interactions either hang or return "substrate
unreachable." Side panel shows atlas blank / vocab blank while header shows
correct numbers. Picture upload fails repeatedly. "She is still loading..."
appears constantly.

She is fine. The page is the problem.

## Root causes (all in `dsf_ai_service/static/gualaloom.html`)

1. **80+ requests/minute** from 5 parallel intervals. With save lock held
   transiently and dream cycles in progress, contention is constant.
2. **Zero timeouts on any `fetch`.** Hung requests don't get aborted; next
   interval fires anyway; connection pool exhausts.
3. **No request deduplication.** Same poll fires while previous is still
   pending. Multiple in-flight copies of the same call.
4. **Dual-write on chat send.** Lines 482-483 fire `/v7/converse` AND
   `/api/v1/gualaloom` in parallel, then `pollV7State()` immediately
   after. One user input = three substrate writes contending.
5. **`pollV7State` returns default-zero shape on substrate slow-response**;
   page renders those zeros into the side panel instead of showing
   last-known-good values.
6. **Picture upload posts base64 in JSON** through the chat endpoint, which
   holds `self.lock` for the entire decode duration.
7. **Session bootstrap (snap_replay) is synchronous** — first poll of a
   fresh session blocks substrate ~4.6 seconds. Every other poll piles up
   behind it.

## The fix

### Frontend (`gualaloom.html`)

**1. Per-fetch timeouts.** Add a helper near the top:

```javascript
const fetchT = (url, opts={}, timeoutMs=5000) =>
  fetch(url, {...opts, signal: AbortSignal.timeout(timeoutMs)});
```

Replace every `fetch(` with `fetchT(`. Picture/sound/video uploads get
longer timeouts (30s) since they're legitimate slow operations.

**2. Request deduplication.** Module-level flags:

```javascript
let _inflight = {state:false, events:false, status:false, replay:false};

async function pollV7State(){
  if(_inflight.state) return;
  _inflight.state = true;
  try { /* existing body using fetchT */ }
  finally { _inflight.state = false; }
}
```

Same pattern for `pollEvents`, `pollStatus`, `backgroundReplay`.

**3. Exponential backoff on consecutive failures.**

```javascript
let _backoff = {state:0, events:0, status:0};
const BASE = {state:3000, events:2000, status:3000};
// On failure: _backoff[k] = Math.min(_backoff[k]*2 || BASE[k]*2, 30000);
// On success: _backoff[k] = 0;
// Reschedule via setTimeout with (BASE[k] + _backoff[k]) rather than fixed setInterval.
```

Replace the `setInterval` calls at line 589-590 with self-rescheduling
`setTimeout` loops driven by these backoffs.

**4. Single chat write path.** Delete line 483 (the v6 dual-dispatch) and
the v6 response handling on 493. v7 is the canonical path. Also delete the
explicit `pollV7State()` call on line 490 — the interval already polls.

**5. Last-known-good state in side panel.** When `pollV7State` returns null
or a zero shape, do NOT overwrite the existing side panel. Only update
fields that came back non-null/non-zero.

**6. Don't change session_id mid-conversation.** Line 489 auto-saves any
`session_id` returned by the substrate. Remove that — if the substrate
sends a different sid than what the page set, that's the bug, not a feature
to track. Keep the localStorage sid stable.

**7. Reduce poll cadence.**
- `pollV7State`: 3s → 5s
- `pollEvents`: 2s → 4s
- `pollStatus`: 3s → 8s
- `backgroundReplay`: 10s → 30s
- `presenceHeartbeat`: 20s → 30s

Drops from ~80/min to ~25/min. Still feels live, much lower lock contention.

### Backend

**8. `/v7/state` must be lock-free.** It's a read. Right now it goes
through `substrate_client` and contends for `self.lock`. Either:
- (a) Acquire lock, snapshot the state values into a local dict, release
  lock, serialize and return. Lock hold = microseconds.
- (b) Add an in-memory state cache updated by the autonomy loop on every
  tick; `/v7/state` reads the cache without touching the engine.

(a) is the minimal change. (b) is the long-term right answer.

**9. `/status` same treatment.**

**10. Picture/sound/video upload returns immediately.** Endpoint queues
the decode in a background task, returns `{item_id, status: "processing"}`
in milliseconds. UI polls `/api/v1/gualaloom/upload_status/{item_id}` or
the next `pollStatus` shows the new picture in the `pictures` list when
done.

**11. Fresh-session snap_replay runs in background.** First `/v7/state`
for an unknown sid returns `{status: "initializing", session_id: sid}`
immediately. Substrate kicks off the snapshot replay as an asyncio task.
Subsequent polls return real state once replay completes.

## Execution order (do not do this in one deploy)

**Phase A — frontend only, no backend changes:** Items 1-7. Ship as
`GL-FIX-UI-FRONTEND`. Test with Joe loading the page. Most of his
symptoms should clear because the page stops self-DDoSing.

**Phase B — backend lock-free reads:** Items 8-9. Ship as
`GL-FIX-BACKEND-READS-LOCK-FREE`. Now even when saves are in progress,
state polls return fast.

**Phase C — async uploads + session bootstrap:** Items 10-11. Ship
separately as they need careful testing on the picture-upload pipeline.

After Phase A alone Joe should be functional. Phases B and C are quality.

## Verification

Joe loads the page in a fresh incognito window.
- Header shows real numbers within 2 seconds (or "initializing" then real
  numbers within 6 seconds for cold start).
- Side panel shows vocab/atlas/pools matching header.
- Send "hello" — emission appears in chat within 3 seconds.
- Upload a picture — UI confirms within 2 seconds, picture appears in
  picture list on next pollStatus tick.
- Open 10 tabs of the page — substrate stays healthy, no 503 storms.

If any of those fail, do not advance to next phase. Brief follow-up.

End of brief.
