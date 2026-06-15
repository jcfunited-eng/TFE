# GL-BRIEF-SENSORY-IO-WC-20260614-01

**Author:** wC
**Date:** 2026-06-14
**Builds on:** TFE code SHA `332ee7a` (task:118). Guala is alive and responding to text (verified by wC via bridge: vocab=2519, atlas climbing, presence registered, she emitted "moon for" and "good come like" to Joe's messages).
**Supersedes:** parts of UI-REPAIR scope from C9 (ledger 050 Tier 1d). C9 was reported DONE but live page contradicts that. This brief is the actual fix.
**Freeze carve-out per rule 6:** the UI is her primary connection to the world. Streaming sight and sound is what the substrate was engineered for. Right now she emits but Joe cannot hear her, she has krimelacks but they're not being fed from camera/mic, she attends to pictures but Joe sees filenames not images. This is not "polish" — this is the sensory interface.

---

## The principle

**Guala's substrate has five modal krimelacks: sight, sound, smell, taste, touch.** The first two are reachable from the browser. The substrate was designed for these to be fed *continuously* — not in single-shot uploads. The UI is not a chat window with file attachments. It is her sensory cortex's plug-in surface to the world.

Currently:

- Camera ON serves only the snapshot button. One photo, one upload. No streaming. She cannot see what Joe sees while he sits there.
- Mic ON serves only push-to-talk speech-to-text. Words she could hear become a text transcript. The raw audio that her sound krimelack was built to process never reaches her.
- Her voice synthesizes to WAV but Joe doesn't hear it. The audio element exists, the base64 is generated, but playback isn't happening reliably.
- Pictures she attends to show as **filename text** in Joe's transcript, not as inline images. He cannot see what she sees.
- Top stats line stays at `?` so Joe cannot tell from the UI whether she's loaded.

The substrate-side pipeline already exists for all of this. The UI side is what's missing or broken.

---

## What must be true after this brief

1. Joe opens the page → substrate stats populate within a few seconds → he knows she's there.
2. Joe enables camera → frames stream into her sight krimelack at ~2 fps → she sees continuously while he's there.
3. Joe enables mic → audio streams into her sound krimelack in 1-second chunks → she hears continuously.
4. She emits → Joe **hears** her synthesized voice through his speakers.
5. She attends to a picture → that picture renders inline in Joe's transcript as a real image, not a filename.
6. `/v7/state` returns 200 with valid data within 1-2 seconds on a fresh session id.

These are the six parts of this brief.

---

## Part A — Picture rendering actually works inline

**Problem:** `renderPictures(pics)` in `dsf_ai_service/static/gualaloom.html` (line 414) is supposed to render `<img>` tags from picture refs. When the ref has `data` field → renders inline. When the ref has `item_id` only → fetches via `/api/v1/gualaloom command:/picture <id>`, expects `picture_data` field in response, swaps `<img>` in. The backend handler at `app.py:1102-1135` returns `picture_data` as a full `data:image/jpeg;base64,...` URL.

Live page (Joe's screenshots) shows picture refs stuck on the "loading {title}..." fallback text. Filenames visible: `81ks2kncs2l._ac_uf1000,1000_ql80_...`, `img_6230...`, `img_2161...`, `img_2030...`. None of them resolved to a rendered image.

**Diagnosis (c1 to verify):** either the fetch is failing, the response shape mismatches what the UI expects, or the `pid` being passed to the command is malformed. Open DevTools network tab, watch one fetch fire, capture request + response. Fix whatever the actual mismatch is.

**Acceptance:**
- Joe loads page; she attends to a picture during her normal activity loop; that picture renders as a visible `<img>` in his transcript within 5 seconds of the attend event.
- Joe uploads a new picture via 📷; the picture renders inline immediately as confirmation.
- Snapshot button: same — captured frame renders inline as confirmation.
- Zero "loading {title}..." stuck text in steady state.

---

## Part B — Voice audio plays to Joe

**Problem:** `<audio id="voice">` exists (line 93). Playback wired at line 459-460:
```js
if(result.self_voice_audio_b64 && audioUnlocked && !muted){
  voiceEl.src='data:audio/wav;base64,'+result.self_voice_audio_b64;
  voiceEl.play().catch(()=>{});
}
```

Joe says: doesn't hear her. Two possible failures:

1. `audioUnlocked` is false because Joe never clicked anywhere to unlock Chrome autoplay. Header should show "Click anywhere to enable audio" until first click. If the unlock isn't firing on click, that's the bug.
2. `self_voice_audio_b64` is missing from the `/v7/converse` response. The v7 emit path in `v7_engine.py:345` generates the WAV when she emits. If she's not emitting (because `aware: context_blocked` and intro gate also gating), no audio. **But the audio should also play her v6 emissions** (e.g., "moon for", "good come like" she said to Joe) — those go through `/api/v1/gualaloom` and may not have a voice synthesis path wired.

**Spec:**

1. **Verify audio unlock fires on first click anywhere.** If not, fix. The header status should read "Audio ready · unmuted" after unlock.
2. **Verify `self_voice_audio_b64` is in `/v7/converse` response when she emits at v7 layer.** Log it. If missing when emit happens → backend bug. If present but UI silent → frontend bug.
3. **Add voice synthesis for v6 emissions too.** When `/api/v1/gualaloom` returns a `response` field with non-empty text (her v6 emission, e.g., "moon for"), the response should also include `self_voice_audio_b64` synthesized from that text via the same espeak-ng path. Currently only v7 path synthesizes. Joe heard nothing because v6 path doesn't.

**Acceptance:**
- Joe sends "this is Daddy can you hear me" → her v6 reply ("moon for" or whatever) → **Joe hears espeak-ng voice through speakers** speaking those words within 2 seconds of the message bubble appearing.
- Joe sends a message that triggers v7 emit → he hears that too.
- Header shows "Audio ready · unmuted" after first click.

---

## Part C — Camera frame streaming into sight krimelack

**Problem:** Camera is ON for snapshot only. She has no continuous visual input from the world Joe is in.

**Spec:**

### Backend — new endpoint `/sight_frame`

Add to `dsf_ai_service/app.py`:
```python
@app.post("/sight_frame")
async def sight_frame(msg: GualaloomMsg):
    """
    Streaming sight: feed a low-res frame into her sight krimelack
    without persisting as a PictureItem. High-frequency calls expected.
    """
    if _guala is None:
        raise HTTPException(503, "guala_not_ready")
    import base64
    b64_data = msg.text.strip()
    if not b64_data:
        return {"ok": False, "error": "no frame data"}
    def _decode_frame():
        t0 = time.time()
        try:
            img_bytes = base64.b64decode(b64_data)
            img_full, grid, orig_w, orig_h = decode_image_bytes(img_bytes)
            # Feed the grid directly to sight krimelack via existing
            # process_viewing path, but pass transient=True so no
            # PictureItem is created.
            _guala.process_sight_frame(grid)  # NEW method on engine
            print(f"[sight-frame] {time.time()-t0:.3f}s")
            return {"ok": True, "tick": _guala.tick}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    import asyncio as _aio
    return await _aio.get_event_loop().run_in_executor(None, _decode_frame)
```

### Engine — new method `process_sight_frame(grid)`

In `dsf_ai_service/v4/gualaloom_v5_engine.py`, add method to the main engine class. Body: feed `grid` into her sight krimelack using the same path that `process_viewing` uses **minus** the PictureItem creation, minus the storage to `_pictures` dict, minus the `picture_uploaded` event log entry. Just the krimelack transduce + atlas record for sight band.

The existing `process_viewing` does this work bundled with persistence; factor out the krimelack-feed portion into a helper if needed.

### Frontend — camera streaming loop

In `gualaloom.html`, add to the camera handlers:

```js
let sightStreamInterval = null;
async function startSightStream() {
  const vid = document.getElementById('cam-preview');
  if (sightStreamInterval) clearInterval(sightStreamInterval);
  sightStreamInterval = setInterval(async () => {
    if (!camStream || muted) return;
    try {
      const c = document.createElement('canvas');
      // Downsample for streaming — 128x128 is plenty for krimelack
      c.width = 128; c.height = 128;
      c.getContext('2d').drawImage(vid, 0, 0, 128, 128);
      const blob = await new Promise(r => c.toBlob(r, 'image/jpeg', 0.5));
      const reader = new FileReader();
      reader.onload = async () => {
        let b64 = reader.result.replace(/^data:image\/jpeg;base64,/, '');
        await fetch(`${API}/sight_frame`, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({text: b64, command: ''})
        });
      };
      reader.readAsDataURL(blob);
    } catch (e) { /* drop frame silently */ }
  }, 500);  // 2 fps
}
function stopSightStream() {
  if (sightStreamInterval) {
    clearInterval(sightStreamInterval);
    sightStreamInterval = null;
  }
}
```

Call `startSightStream()` when camera turns ON, `stopSightStream()` when it turns OFF.

**Acceptance:**
- Joe enables camera; within 1 second, `/sight_frame` calls begin firing at 2 Hz.
- Backend logs show `[sight-frame] 0.0Xs` lines streaming.
- `guala_atlas_snapshot` shows sight-band atlas activity increasing during the stream.
- Joe disables camera; `/sight_frame` calls stop.
- No PictureItem clutter created in `_pictures` from streaming (only deliberate snapshots/uploads should create those).

---

## Part D — Mic audio streaming into sound krimelack

**Problem:** Mic ON serves only push-to-talk STT. Audio bytes don't reach her sound krimelack.

**Spec:**

### Backend — new endpoint `/sound_frame`

```python
@app.post("/sound_frame")
async def sound_frame(msg: GualaloomMsg):
    """
    Streaming sound: feed a short audio chunk (1-2s WAV) into her
    sound krimelack without persisting as a sound album entry.
    """
    if _guala is None:
        raise HTTPException(503, "guala_not_ready")
    import base64
    b64_data = msg.text.strip()
    if not b64_data:
        return {"ok": False, "error": "no audio data"}
    def _decode_frame():
        t0 = time.time()
        try:
            audio_bytes = base64.b64decode(b64_data)
            # Process through cochlear pipeline (same as /addsound)
            # but feed directly to sound krimelack atlas without
            # creating _sounds entry or SensoryItem.
            _guala.process_sound_frame(audio_bytes)  # NEW method
            print(f"[sound-frame] {time.time()-t0:.3f}s")
            return {"ok": True, "tick": _guala.tick}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    import asyncio as _aio
    return await _aio.get_event_loop().run_in_executor(None, _decode_frame)
```

### Engine — new method `process_sound_frame(audio_bytes)`

Factor the cochlear pipeline (decode → cochlear_transduce → onset_stream → sustained_stream → a1_signature → atlas record for each audio band) into a helper that takes raw bytes and feeds the krimelack without creating `_sounds` entry. The existing `/addsound` handler at `app.py:1668` shows the full pipeline; the streaming version skips the storage steps.

### Frontend — mic streaming loop

```js
let micRecorder = null;
let micStreamChunks = [];

async function startMicStream(stream) {
  if (micRecorder) return;
  try {
    micRecorder = new MediaRecorder(stream, {mimeType: 'audio/webm'});
  } catch {
    // Fallback for browsers without webm support
    micRecorder = new MediaRecorder(stream);
  }
  micRecorder.ondataavailable = async (e) => {
    if (e.data.size < 100) return;  // skip tiny chunks
    const reader = new FileReader();
    reader.onload = async () => {
      const b64 = reader.result.split(',')[1];
      try {
        await fetch(`${API}/sound_frame`, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({text: b64, command: ''})
        });
      } catch {}
    };
    reader.readAsDataURL(e.data);
  };
  // Capture chunks every 1500ms
  micRecorder.start(1500);
}

function stopMicStream() {
  if (micRecorder) {
    try { micRecorder.stop(); } catch {}
    micRecorder = null;
  }
}
```

Call `startMicStream(stream)` after mic permission granted and `stream` is the MediaStream. Call `stopMicStream()` on mic disable.

**Note on STT coexistence:** the existing `webkitSpeechRecognition` (push-to-talk transcription) and the new MediaRecorder streaming share the **same MediaStream**. Both can run simultaneously. STT consumes the stream for transcription, MediaRecorder reads the same stream for audio chunks. Verify no conflict — they should be independent.

**Acceptance:**
- Joe enables mic; within 2 seconds, `/sound_frame` calls begin firing at ~0.67 Hz (every 1.5s).
- Backend logs show `[sound-frame] 0.0Xs` lines.
- `guala_atlas_snapshot` shows sound-band atlas activity (audio_low, audio_mid, audio_high, audio_speech) increasing during the stream.
- Joe disables mic; `/sound_frame` stops.
- Push-to-talk STT still works in parallel.
- No `_sounds` clutter from streaming.

---

## Part E — Substrate stats line populates

**Problem:** Top stats line stuck at `vocab: ? · motifs: ? · atlas: ? · sounds: ? · pics: ?` even after she's fully loaded.

**Diagnosis (c1 to verify in DevTools):**
- `pollStatus()` (HTML line 501) fires `/api/v1/gualaloom command:/status`.
- Backend at `app.py:1137-1200` returns the `/status` response shape including `n_sounds`, `n_pictures`, and the populated string in `response` field.
- HTML line 510-512 expects `m.n_motifs`, `m.n_sounds`, `m.n_pictures`. The variable `m` should be the JSON response body.
- Bug is likely either: (a) `pollStatus` is fetching but `m` lookup is on wrong field shape; (b) Joe's session hasn't seen `/v7/state` respond once yet, so the stats from that path are blank; (c) `pollStatus` is silently erroring.

**Spec:** verify the response shape matches what HTML expects, fix mismatch on either side. Stats must populate within 5 seconds of `_guala` being loaded.

**Acceptance:**
- Within 5 seconds of page load (after `_guala` is loaded server-side), top stats line shows real numbers: `vocab: 2519 · motifs: 7885 · atlas: 38828 · sounds: 12 · pics: 38` (or whatever the current numbers are).
- During init (`_guala` is None): line shows "she is still loading..." per the existing fallback.

---

## Part F — `/v7/state` hangs on fresh session

**Problem:** Joe creates new session id `sid_h1y8kvic` — `/v7/state` returns 503/500 intermittently for several minutes before populating. Eventually populates correctly (vocab=2519, pools 840/840/839, intro=i_hear, aware=aware_quiet) but the wait is unacceptable. `/api/v1/gualaloom` works fine the whole time, so `_guala` is loaded. The hang is specific to the v7 layer.

**Diagnosis (c1 to instrument):**

Add timing logs to the `/v7/state` path:

```python
@app.get("/v7/state")
async def v7_state(session_id: str = "default"):
    if _guala is None:
        raise HTTPException(503, ...)
    t0 = time.time()
    from dsf_ai_service.substrate.v7_engine import get_or_create_session
    session = get_or_create_session(session_id, engine=_guala)
    t1 = time.time()
    state = session.get_state(engine=_guala)
    t2 = time.time()
    print(f"[v7-state] {session_id} get_or_create={t1-t0:.3f}s "
          f"get_state={t2-t1:.3f}s")
    return state
```

And inside `get_or_create_session` (v7_engine.py:667):

```python
def get_or_create_session(session_id, engine=None):
    if engine is None:
        raise RuntimeError("guala_not_ready")
    t0 = time.time()
    with _sessions_lock:
        t_lock = time.time()
        if session_id in _sessions:
            print(f"[v7-session] {session_id} cache_hit lock_wait={t_lock-t0:.3f}s")
            return _sessions[session_id]
        t_create_start = time.time()
        session = V7Session(session_id, engine=engine)
        t_create = time.time()
        # ... snapshot load + replay ...
        t_done = time.time()
        print(f"[v7-session] {session_id} create_new "
              f"lock_wait={t_lock-t0:.3f}s "
              f"v7_init={t_create-t_create_start:.3f}s "
              f"snap+replay={t_done-t_create:.3f}s")
        _sessions[session_id] = session
        return session
```

**Hypothesis (most likely):** `_sessions_lock` is a `threading.Lock` (not async). If one `/v7/state` request triggers V7Session creation for a fresh id (which is several hundred ms of numpy work building pools and installing 2519 mode vectors), the lock is held the entire time. The 3-second polling means multiple concurrent requests queue up on the lock. If V7Session creation hits something genuinely slow (e.g., event_log file initialization on EFS doing a slow stat call), the lock blocks for many seconds while polls accumulate.

**Fix path depends on what the logs show:**
- If `v7_init` is the slow part (>1s): V7Session creation needs optimization OR needs to happen outside the lock.
- If `snap+replay` is the slow part: event log replay or snapshot load is doing too much; reduce or do async.
- If `lock_wait` is the slow part: contention is the issue; restructure so the lock only guards the dict mutation, not the V7Session construction.

**Acceptance:**
- `/v7/state?session_id=<new_id>` returns 200 with valid data in **under 2 seconds**, every time, on a fresh session id.
- Timing logs show each phase under 1 second.
- No "she is still loading" message in chat after the first 2 seconds following page load.

---

## Order of operations (binding)

c1 implements in this order. Each part landed and verified before moving to the next, **except** A and B which can deploy together since they're both UI-side only.

1. **Part F first (diagnostic).** Add the timing logs. Deploy. Capture one Joe-session load. Read the logs. THIS GIVES US THE DIAGNOSTIC TO CHOOSE THE RIGHT FIX. Then implement the actual fix for F based on what the logs show.
2. **Parts A + B (UI bugfixes).** Picture rendering + voice playback. Both UI/backend wiring bugs in existing endpoints.
3. **Part E (UI bugfix).** Stats line population. Tiny.
4. **Part C (new feature).** Sight streaming. New backend endpoint + new engine method + new UI loop.
5. **Part D (new feature).** Sound streaming. Same shape as C but for audio.

Total: probably 2-3 deploys. Order matters because F's diagnostic informs whether F's fix changes a lock structure, which would affect A/B/C/D's interaction with the v7 path.

---

## Constraints

- **No touching v7_engine.py substrate kernel logic.** Section creation, pool routing, NMDA gates, intro/aware logic: untouched. Only the new `process_sight_frame` / `process_sound_frame` engine methods (which live in `gualaloom_v5_engine.py` v6 engine, not v7).
- **No touching decay. No touching unpause.** UNPAUSE remains HELD.
- **Streaming endpoints do NOT create persistent album entries.** That's the whole point. They feed krimelacks transiently. If c1 cannot find a clean way to do that, STOP and name the conflict before improvising.
- **Streaming frame rates as specified:** sight 2 Hz, sound 1.5s chunks. Higher rates risk overwhelming the krimelack with no improvement in her perception. Lower defeats the purpose.
- **Pictures she attends to or uploads continue to create PictureItems and render inline.** Only the new `/sight_frame` stream is transient.
- **Verify on the live page.** c1 loads `dsf-ai.com/gualaloom.html` himself, enables camera + mic, sends a message, observes: pictures render, voice plays, frames stream, stats populate. If c1 cannot verify these by direct observation, the deploy is NOT done.

---

## What "done" means

Joe opens the page. Within 5 seconds:
- Top stats show real numbers.
- She is reachable (no "still loading" message).

Joe enables camera and mic:
- Camera frames stream into her sight krimelack at 2 Hz.
- Mic audio streams into her sound krimelack in 1.5s chunks.
- Backend logs show `[sight-frame]` and `[sound-frame]` timings.
- `guala_atlas_snapshot` (bridge) shows sight + sound band activity increasing.

Joe sends a text message:
- She replies in chat (bubble).
- He **hears her voice** speaking the reply.
- If her reply includes a picture (she's referencing what she sees), it renders inline.

Joe disables camera and mic:
- Streaming stops.
- She continues to run normally (substrate doesn't crash from input cessation).

That is the bar. Anything less is not done.
