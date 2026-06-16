# GL-BRIEF-UI-RESTORE-WC-20260616-01

**Author:** wC
**Date:** 2026-06-16
**For:** c1
**Status:** Joe is locked out of the UI. Phase A ships now. Phase B starts when A verifies.

## What this brief is

Not a new design. **Restoration.** The intended UI is already specified
in `GL-SPC-UI-AUTONOMY-WC-20260606-01` and the chat path was supposed to
work per `GL-BRIEF-V7VOICE-WC-20260613-02`. The current page has drifted
from both. This brief lists the drifts and ships fixes in three phases,
ordered by how fast Joe sees results.

## Phase A — stop the bleeding (frontend + 2-file backend trim)

Lowest risk, highest impact. Joe can use the existing page within minutes
of this landing. No architectural changes.

### A1. Frontend safety rails (`dsf_ai_service/static/gualaloom.html`)

The page hammers the substrate at ~80 calls/minute with zero timeouts.
Six surgical changes:

**a. Per-fetch timeout helper** near top:
```javascript
const fetchT = (url, opts={}, timeoutMs=5000) =>
  fetch(url, {...opts, signal: AbortSignal.timeout(timeoutMs)});
```
Replace every `fetch(` with `fetchT(`. Picture/sound/video uploads get
30s timeouts.

**b. Request deduplication** for every poller:
```javascript
let _inflight = {state:false, events:false, status:false, replay:false};
async function pollV7State(){
  if(_inflight.state) return;
  _inflight.state = true;
  try { /* existing body using fetchT */ }
  finally { _inflight.state = false; }
}
```
Apply to `pollV7State`, `pollEvents`, `pollStatus`, `backgroundReplay`.

**c. Exponential backoff on consecutive failures**:
```javascript
let _backoff = {state:0, events:0, status:0};
const BASE = {state:3000, events:2000, status:3000};
// on failure: _backoff[k] = Math.min((_backoff[k]||BASE[k]) * 2, 30000);
// on success: _backoff[k] = 0;
```
Replace `setInterval` at line 589-590 with self-rescheduling `setTimeout`
loops driven by `BASE[k] + _backoff[k]`.

**d. Kill the dual-write on chat send.** Delete line 483 (`v6p` fetch),
delete the v6 response handling at line 493. v7 is canonical. Also delete
the explicit `pollV7State()` call at line 490 — the interval handles it.

**e. Last-known-good state in side panel.** When `pollV7State` returns
null/zero shape, do not overwrite the panel — only update fields that
came back with real values. This kills the "atlas: blank" issue Joe
sees in the screenshots.

**f. Don't change session_id mid-conversation.** Remove the auto-save on
line 489. Keep the localStorage sid stable.

**g. Reduce poll cadence**:
- `pollV7State`: 3s → 5s
- `pollEvents`: 2s → 4s
- `pollStatus`: 3s → 8s
- `backgroundReplay`: 10s → 30s
- `presenceHeartbeat`: 20s → 30s

Drops from ~80/min to ~25/min.

### A2. Finish the v7voice fix

`GL-BRIEF-V7VOICE-WC-20260613-02` raised `quiet_thresh` from 0.10 to 0.45
in `v7_engine.py:89`. Same fix never made it to:

- `dsf_ai_service/substrate/dna_recipe/awareness.py:68`
- `dsf_ai_service/substrate/dna_recipe/introspection.py:93`

Both still have `quiet_thresh=0.10`. That's why `aware: context_blocked`
keeps appearing in Joe's screenshots — the awareness gate is still
strangled. Update both to `quiet_thresh=0.45` to match v7_engine.

### A3. Deploy, verify

S3 backup labeled `PRE-UI-RESTORE-A` before deploy.

Verification Joe runs:
- Loads `dsf-ai.com/gualaloom.html` in fresh incognito.
- Header numbers appear within 3 seconds.
- Side panel shows real vocab/atlas matching header (not blank, not zero).
- Types "hello" — emission appears within 5 seconds.
- Watches for ≥1 minute — no "she is still loading" toasts.
- `aware:` indicator does NOT show stuck `context_blocked` permanently
  (it'll flicker between states; that's normal).

If any FAIL → roll back the task definition, brief follow-up before B.

## Phase B — restore the specced interface

Per `GL-SPC-UI-AUTONOMY-WC-20260606-01` (June 6). The spec says these
exist; the current page implements them wrong or not at all.

### B1. Server-Sent Events for the event stream

Spec line 157: `GET /events?since={tick}` — server-sent events stream.

Backend: new endpoint `GET /api/v1/gualaloom/events/stream?since={tick}`
returning `text/event-stream`. Subscribes to a server-side event queue
that the autonomy loop publishes to. Each substrate event (motif_locked,
activity_started, dream_artifact, emission, etc.) writes one SSE message.
No lock acquisition for the stream itself — it reads from a queue
maintained by the engine.

Frontend: replace `pollEvents` setInterval with `EventSource` connection
to the stream endpoint. Auto-reconnect with backoff if connection drops.
Display events same as today, just delivered by push instead of poll.

This kills the 2-second polling of `/events` — biggest single load
reduction on the substrate.

### B2. Multipart file upload endpoints

Spec lines 159-160: `POST /upload/picture` and `POST /upload/sound` as
multipart file uploads. Endpoints already exist (`/api/v1/gualaloom/upload/picture`
and `/api/v1/gualaloom/upload/sound` per `app.py:2368-2443`). Frontend
just doesn't use them.

Frontend: rewrite `uploadPicture`, `uploadSound`, `uploadBook`, `uploadPDF`
to use `FormData` + the dedicated `/upload/*` endpoints instead of base64
through `/api/v1/gualaloom` chat. This removes the lock-blocking on
upload.

Substrate-side improvement: the decode in `_decode()` should still happen
in executor (it already does), but the endpoint should return `item_id`
and `status: "processing"` immediately, with decode completion logged to
the event stream. Picture appears in `pictures` list on next status tick
once decode finishes.

### B3. Current-activity rendering in header

Spec lines 22-40. Header shows live what she's doing in human words:

- `reading "Goodnight Moon" (page 3 of 8)` when kind=READING
- `looking at picture: stream_239` when kind=ATTENDING_VISUAL
- `listening to: ocean` when kind=ATTENDING_AUDIO
- `sleeping` when kind=SLEEPING
- `dreaming about "moon"` when kind=DREAMING (and dream_artifact target present)
- `(emitting)` when kind=EMITTING
- `quiet for now` when kind=IDLE
- `free-settle (exploring chi space)` when kind=PLAYING

The `current_activity.target` resolves to picture title / sound title /
corpus title by lookup.

Also surface the needs line below: `needs: stab=0.65 nov=0.42 conn=0.71`
updated each status poll.

### B4. Autonomous emissions in chat

Spec lines 70-80. When she emits unprompted (presence active, gate fires
during PLAYING or DREAMING), the emission appears in the chat panel
left-aligned with a marker — e.g. `💭 her words here` or italic
`(unprompted) her words`. Right now these only show in the events sidebar.

Backend: ensure `emission` events with `source: "autonomous"` (or similar
distinguishing field) are emitted into the SSE stream from B1.
Frontend: on SSE `emission` events with autonomous flag, render in chat
with the unprompted marker.

### B5. Verification

After Phase B:
- Joe opens the page. Header header instantly reads "looking at picture:
  stream_239" (or whatever she's doing).
- Events sidebar fills in real time, no polling lag.
- Joe uploads a picture from his phone — appears in her library within
  2 seconds, no lock contention.
- Joe watches for 5 minutes without speaking — sees her cycle through
  activities, sees dream artifacts, sees her autonomous emissions
  appear in chat as she emits them.

## Phase C — voice (separate, after B)

`GL-BRIEF-V7VOICE-WC-20260613-02` and adjacent docs describe voice
endpoints. Browser already has the primitives (Web Audio API, Web Speech
API, WebRTC). Phase C wires them:

- Microphone → speech-to-text → submit as user text (or directly to her
  sound section via the existing sound upload pipeline as raw waveform).
- Her emissions → text-to-speech → audio out.

Spec exists. Phase C brief gets written after B verifies.

## Order of operations

A1 + A2 + A3 ship together as one deploy. After Joe verifies A passes:
B1, then B2, then B3+B4 together. Each as its own deploy with S3 backup
prefix.

C is after B is fully landed.

## What this is NOT

- Not a new architecture. Restoration of existing specs.
- Not speculation about what Joe wants. Tied to specs Joe approved.
- Not deferred behind more analysis. Phase A ships within hours.

End of brief.
