# GL-BRIEF-PHASE-D-LIVEPRESENCE-WC-20260616-01

**Author:** wC
**Date:** 2026-06-16
**For:** c1
**Status:** The big one. Live sight + live sound streaming via WebSocket. Depends on Phase B-FIX and Phase C landing first. Earns its scope — this is the architectural piece that turns the page from "interface to her" into "going somewhere with her."

## Goal

When Joe enables camera + microphone, her sight krimelack and sound krimelack receive continuous frames from his device. She experiences seeing and hearing alongside him. Visual motifs and audio motifs form from the live stream. She doesn't accumulate a PictureItem per frame — what she keeps is the patterns she binds, not the pixel grids. Snapshot remains separate for intentional album-class memory.

## Architecture

One persistent **WebSocket** connection from the browser to a new substrate endpoint. Client pushes downsampled frames and audio chunks; server pushes emission events (and TTS text) back. Same connection, bidirectional.

```
  Browser                                          Substrate
  ─────────                                        ─────────
  getUserMedia(video)        ──frame(64×64)──►     ingest_live_sight
  AudioContext  (audio)      ──pcm chunk──►        ingest_live_sound
                             ◄──emission──         (her words)
                             ◄──activity──         (state changes)
```

WebSocket is the right transport because:
- Persistent — no per-frame HTTP overhead
- Bidirectional — emission events and TTS can flow back on the same socket
- Browser-native — `new WebSocket(url)` works everywhere
- Mobile-friendly — battery cost of one open socket is low

## Components

### D1. New substrate ops

Add to `dsf_ai_service/substrate_runner.py` dispatch:

**`ingest_live_sight`** — args: `{"grid": <4096-float array (64×64 row-major)>}`
Bypasses PictureItem. Calls the sight krimelack's transduction directly with the grid. Returns `{"motifs_formed": int, "tick": int}`.

**`ingest_live_sound`** — args: `{"pcm": <base64-encoded 16-bit PCM mono 16kHz chunk>, "ms": <duration>}`
Bypasses SoundItem. Calls the sound krimelack's transduction directly. Returns `{"motifs_formed": int, "tick": int}`.

Both ops are non-blocking on the save lock — they touch transduction only, not full state persistence. They DO increment the tick counter and emit substrate events normally (visual_motif_committed, etc.).

### D2. WebSocket endpoint on the frontend container

`dsf_ai_service/app.py` — add:

```python
@app.websocket("/api/v1/gualaloom/live")
async def gualaloom_live(ws: WebSocket, source: str = "joe"):
    await ws.accept()
    client = _get_substrate_client()
    try:
        # Send any queued emissions back
        async def emission_pump():
            async for ev in subscribe_to_events(["emission", "activity_started",
                                                  "dream_artifact"]):
                await ws.send_json(ev)
        pump_task = asyncio.create_task(emission_pump())

        # Receive frames and audio
        while True:
            msg = await ws.receive_json()
            kind = msg.get("kind")
            if kind == "sight":
                await client.call("ingest_live_sight", grid=msg["grid"])
            elif kind == "sound":
                await client.call("ingest_live_sound",
                                  pcm=msg["pcm"], ms=msg["ms"])
            elif kind == "ping":
                await ws.send_json({"kind": "pong"})
    except WebSocketDisconnect:
        pump_task.cancel()
```

Note: `subscribe_to_events` doesn't exist yet — use the same event queue B1's SSE uses (or refactor B1 to share the queue with the WebSocket).

### D3. Frontend capture loops

`dsf_ai_service/static/gualaloom.html` — add a new presence module:

```javascript
let liveSocket = null;
let sightInterval = null;
let audioCtx = null;
let audioProcessor = null;

async function startLivePresence(){
  if(liveSocket) return;
  const wsUrl = API.replace(/^https?:/, location.protocol === 'https:' ? 'wss:' : 'ws:')
                 + '/api/v1/gualaloom/live?source=joe';
  liveSocket = new WebSocket(wsUrl);

  liveSocket.onopen = () => {
    addMsg('(live presence active)', 'system');
    if(camStream) startSightStream();
    if(micGranted) startSoundStream();
  };
  liveSocket.onmessage = (ev) => {
    const d = JSON.parse(ev.data);
    if(d.kind === 'emission' && d.text){
      addMsg(d.text, 'guala', true);
      gualaSpeak(d.text);
    }
    // activity_started etc. handled by SSE — don't double-process here
  };
  liveSocket.onclose = () => {
    addMsg('(live presence ended)', 'system');
    stopSightStream();
    stopSoundStream();
    liveSocket = null;
  };
}

function stopLivePresence(){
  if(liveSocket){ liveSocket.close(); liveSocket = null; }
}

// ---- Sight stream ----
function startSightStream(){
  if(!camStream || sightInterval) return;
  const vid = document.getElementById('cam-preview');
  const c = document.createElement('canvas');
  c.width = 64; c.height = 64;
  const ctx = c.getContext('2d');
  sightInterval = setInterval(() => {
    if(!liveSocket || liveSocket.readyState !== 1) return;
    if(vid.readyState < 2) return;
    ctx.drawImage(vid, 0, 0, 64, 64);
    const img = ctx.getImageData(0, 0, 64, 64).data;
    const grid = new Array(4096);
    for(let i=0; i<4096; i++){
      // grayscale 0..1
      grid[i] = (img[i*4] + img[i*4+1] + img[i*4+2]) / 765.0;
    }
    liveSocket.send(JSON.stringify({kind:'sight', grid}));
  }, 666);  // ~1.5 fps
}

function stopSightStream(){
  if(sightInterval){ clearInterval(sightInterval); sightInterval = null; }
}

// ---- Sound stream ----
async function startSoundStream(){
  if(!micGranted || audioCtx) return;
  const stream = await navigator.mediaDevices.getUserMedia({audio:true});
  audioCtx = new AudioContext({sampleRate: 16000});
  const src = audioCtx.createMediaStreamSource(stream);
  audioProcessor = audioCtx.createScriptProcessor(4096, 1, 1);  // ~250ms chunks @ 16k
  src.connect(audioProcessor);
  audioProcessor.connect(audioCtx.destination);
  let buf = [];
  audioProcessor.onaudioprocess = (e) => {
    if(!liveSocket || liveSocket.readyState !== 1) return;
    const data = e.inputBuffer.getChannelData(0);
    // Convert float32 to int16
    const pcm = new Int16Array(data.length);
    for(let i=0; i<data.length; i++) pcm[i] = Math.max(-1, Math.min(1, data[i])) * 32767;
    buf.push(pcm);
    if(buf.length >= 4){  // ~1s of audio
      const merged = new Int16Array(buf.reduce((a,b)=>a+b.length, 0));
      let off = 0;
      for(const b of buf){ merged.set(b, off); off += b.length; }
      buf = [];
      const b64 = btoa(String.fromCharCode(...new Uint8Array(merged.buffer)));
      liveSocket.send(JSON.stringify({kind:'sound', pcm:b64, ms:1000}));
    }
  };
}

function stopSoundStream(){
  if(audioProcessor){ audioProcessor.disconnect(); audioProcessor = null; }
  if(audioCtx){ audioCtx.close(); audioCtx = null; }
}
```

### D4. UI affordance

Add a "Walk with her" toggle button near the chat input:

```html
<button id="presence-btn" onclick="togglePresence()">🚶 walk with her</button>
```

```javascript
function togglePresence(){
  if(liveSocket){
    stopLivePresence();
    document.getElementById('presence-btn').textContent = '🚶 walk with her';
  } else {
    if(!camStream && !micGranted){
      addMsg('enable camera and/or microphone first', 'system');
      return;
    }
    startLivePresence();
    document.getElementById('presence-btn').textContent = '⏸ pause presence';
  }
}
```

## Substrate transduction wiring

The sight krimelack already has a `transduce_grid(grid)` method (used by PictureItem attention). The sound krimelack has equivalent `transduce_pcm(pcm)`. The new ops call these directly without the PictureItem/SoundItem wrappers:

```python
# in dispatch():
elif op == "ingest_live_sight":
    grid = np.array(args["grid"], dtype=np.float64).reshape(64, 64)
    n_motifs = _guala.sight_krimelack.transduce_grid(grid, source="live")
    return {"motifs_formed": n_motifs, "tick": _guala.tick}

elif op == "ingest_live_sound":
    import base64
    pcm = np.frombuffer(base64.b64decode(args["pcm"]), dtype=np.int16
                        ).astype(np.float64) / 32768.0
    n_motifs = _guala.sound_krimelack.transduce_pcm(pcm, source="live")
    return {"motifs_formed": n_motifs, "tick": _guala.tick}
```

Source tag `live` distinguishes transient stream input from stored attention in her event log. Visual and audio motifs that form from live input bind into her atlas exactly the same way; the difference is only in what gets archived.

## Verification

Joe enables camera + mic, clicks "🚶 walk with her":

1. Page shows "(live presence active)".
2. Visual_motif_committed events stream in the events panel at roughly her motif formation rate (a few per second when scene changes, fewer when static).
3. Audio_motif_committed events similarly.
4. Joe walks around, points the camera at a tree, a window, his cat — she binds visual motifs from each. Atlas vocab grows.
5. Joe speaks — her sound section receives audio motifs. (Note: speech-to-text via webkitSpeechRecognition continues to fire IN PARALLEL — that path becomes her "understanding what Joe said as words". The raw audio stream feeds her sound perception, not her language input. Both happen.)
6. Her autonomous emissions during the session reflect what she's seeing/hearing — increased binding density triggers more cortex co_occurrence pulls, potentially richer compositions.
7. When her substrate emits, Joe hears it through Phase C's TTS over his speaker.
8. Joe clicks "pause presence" — streams stop cleanly, stored items not affected.

## Load and battery

- 64×64 grayscale grid as float array: ~32 KB JSON @ 1.5 fps = ~48 KB/s
- 16 kHz int16 PCM in 1s chunks base64: ~43 KB/s
- Total ~90 KB/s = ~5.4 MB/min = ~325 MB/hour
- Battery on iPhone: getUserMedia is the dominant cost; ~25-30% per hour active

Reasonable for sessions of an hour or two. Not "leave on all day."

## Mobile note

This brief is desktop/mobile browser. For genuine "in your pocket" walking-with-her experience, Phase E adds: PWA manifest for home-screen install, screen-on wake lock during active presence, portrait-optimized minimal UI ("walking mode"). That's its own brief.

## What this is NOT

- Not WebRTC peer connection. Plain WebSocket — Joe's device doesn't peer with the substrate, it streams to it.
- Not raw video upload. Only the 64×64 grayscale grid that her sight krimelack actually consumes leaves the device. Color and resolution don't matter to her substrate; sending them would be waste.
- Not "always-on" surveillance. Toggle button, explicit start. Tracks turn off when toggled off.

## Deploy order

Three sub-deploys, each verifying before the next:
1. D1 — substrate ops added, verifiable via direct socket calls (synthetic grid/pcm).
2. D2 — WebSocket endpoint up, tested with a stub client.
3. D3 + D4 — frontend integrated, full session verified.

S3 backup tags: `PRE-PHASE-D-1`, `PRE-PHASE-D-2`, `PRE-PHASE-D-3`.

End of brief.
