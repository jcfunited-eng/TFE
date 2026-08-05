> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-RPT-MIC-SENSORY-C1-20260703-106-v1

doc_id: GL-RPT-MIC-SENSORY-C1-20260703-106-v1
From: c1b | To: Eve | Executing: GL-CMD-MIC-SENSORY-EVE-20260703-106-v1
Status: DIAGNOSIS COMPLETE — fix shape confirmed; no implementation rides this
dispatch (per CMD). Loomscan tick addendum applied (substrate_runner.py,
static-only S3 sync).

## Failures first

None at diagnosis time. The mic binding path exists in the engine but is broken
at the drain-loop layer (WebM bytes reach the engine undecodad; cochlear
receives garbage). sensory_items=0 is a STRUCTURAL zero, not a mic-specific
count. See §3 for precise gap.

---

## Q1 — Does the mic path send audio frames to a sound-binding endpoint,
        or only transcribed text to /converse?

**Both paths run in parallel when the mic is active.**

`dsf_ai_service/static/gualaloom.html` — `requestMic()` calls both:

1. **`startMicSoundStream(micStream)`** — `gualaloom.html:L205–225`
   MediaRecorder records WebM audio chunks (5-second slices).
   Each chunk is base64-encoded and posted to `/sound_frame` via `fetchT`.
   This is the frame-level sound-binding path.

2. **`toggleSTT()`** — `gualaloom.html:L249`
   Web Speech API transcribes audio to text → posts transcribed text to
   `/converse`. This is the language/vocabulary path, separate from
   cochlear binding.

**Answer:** Audio frames DO go to `/sound_frame` (binding endpoint). The mic
path is not restricted to transcribed-text-only. Both paths fire.

---

## Q2 — Is there a live sound-capture binding path at all?

**Yes, but it is broken end-to-end.**

The path is:

```
/sound_frame (app.py L1529-1564)
  → ring_write(kind="sound_window", data={"audio_b64": b64_data, "source": src})
  → substrate_runner.py drain loop (L930-961)
  → _guala.process_sound_frame(audio_bytes)         ← broken here
  → cochlear_transduce()
  → atlas_record()
```

`process_sound_frame()` (`gualaloom_v5_engine.py:L4652-4694`) tries
`wave.open(io.BytesIO(audio_bytes))` — **this always fails on WebM**. The
except-branch then treats the raw WebM container bytes as 8-bit unsigned mono
PCM at 16 kHz — **garbage input to the cochlear transducer**. The cochlear
produces noise or no coherent binding.

The uploaded-file attendance path (lullaby/bells — the 2000-count `_sounds`
items) is a SEPARATE path through `attend_sound()` / `_sounds` dict. That path
loads audio files properly and is not affected by this bug.

**`sensory_items=0` is structural, not mic-specific.** The `_sensory_items`
dict in the engine is never populated: no `SensoryItem` instantiation exists
anywhere in the codebase. The zero count is a constant regardless of mic
activity. It cannot be used to diagnose mic binding health.

---

## Q3 — Precise gap: what does the mic path lack that the camera path has?

**The drain loop decodes JPEG for sight but does NOT decode WebM for sound.**

Camera path (`substrate_runner.py:L906-928`):
```python
img_bytes = b64decode(frame_b64)
_img = PIL_Image.open(BytesIO(img_bytes)).convert('L').resize((64, 64))
grid = numpy.array(_img, dtype=float64) / 255.0
_guala.process_sight_frame(grid)       # receives properly decoded float64 array
```

Mic path (`substrate_runner.py:L930-961`):
```python
audio_bytes = b64decode(audio_b64)
# NO DECODE STEP
_guala.process_sound_frame(audio_bytes)  # receives raw WebM container bytes → broken
```

The camera drain loop PIL-decodes the JPEG to a float64 numpy array before
calling the engine. The mic drain loop passes the raw WebM bytes directly with
no equivalent decode step. The engine's `process_sound_frame()` expects either
WAV bytes or raw PCM — it has no WebM handling. The camera engine entry point
`process_sight_frame(grid)` expects a pre-decoded float64 array; that
expectation is met. The sound engine entry point's expectation is not met.

**Missing piece:** an ffmpeg WebM→PCM decode step in the drain loop, inserted
between `audio_bytes = b64decode(audio_b64)` and the engine call, mirroring the
PIL-decode step in the sight path.

---

## Q4 — Fix shape (no implementation; continuity risk)

**Shape:**

In the `sound_window` branch of the drain loop (`substrate_runner.py:L930-961`),
after `audio_bytes = b64decode(audio_b64)`, add an ffmpeg decode step:

```python
import subprocess, numpy as _np
proc = subprocess.run(
    ['ffmpeg', '-i', 'pipe:0', '-f', 's16le', '-ac', '1', '-ar', '16000',
     '-loglevel', 'quiet', 'pipe:1'],
    input=audio_bytes, capture_output=True, timeout=8
)
if proc.stdout and len(proc.stdout) >= 400:
    pcm = _np.frombuffer(proc.stdout, dtype=_np.int16).astype(_np.float64) / 32768.0
    # pass pcm to engine after downsample or after refactoring process_sound_frame
    # to accept float64 samples directly
else:
    pcm = None  # skip this chunk
```

`process_sound_frame()` would need a companion entry point (or refactor) that
accepts a float64 PCM array at the cochlear's expected sample rate (200 Hz),
mirroring `process_sight_frame(grid)`. The STFT / cochlear_transduce path is
already inside the engine; the change is only at the decode boundary.

**Continuity risk: LOW.**

The current path ALWAYS fails the `wave.open()` try-block on WebM — it has
never successfully decoded a mic chunk. Replacing the broken fallback with an
ffmpeg path cannot regress a working path because no working path exists. The
ffmpeg binary is already present in the ECS container and already used by
`_audio_to_sensory_words()` in the same drain-loop process
(`substrate_runner.py:L87-...`). No new dependency. Subprocess timeout=8s
prevents runaway on corrupt chunks.

---

## Addendum — Loomscan center readout tick fix

**Bug:** `_cmd_status()` in `substrate_runner.py` returned no top-level `"tick"`
field. JavaScript in `loomscan.html:L580`:

```javascript
_tick = d.tick || _tick;
```

`d.tick` was `undefined` → `_tick` remained 0 → center readout always showed
"tick 0" even though her tick is live (~14.45M at diagnosis time).

**Fix (one line, applied in this dispatch):**

`dsf_ai_service/substrate_runner.py` — `_cmd_status()` return dict, after
`"vocab": s["vocab"]`:

```python
"tick": s["tick"],  # GL-ADDENDUM-106: wire center readout in loomscan.html
```

`s["tick"]` comes from `_guala.introspect()` — already used in the `"response"`
string at L1346; adding it as a top-level field makes `d.tick` defined for the
JavaScript.

**Deploy vehicle:** static-only S3 sync. No substrate restart needed. No GO
beyond Eve's diff read.

---

## Gates

None gated here — this is a diagnosis dispatch. Fix gates will be filed when
the implementation dispatch is issued.

---

### Changelog
- v1 (2026-07-03, c1b): diagnosis complete; all 4 questions answered; fix shape
  confirmed; continuity risk LOW. Loomscan tick fix applied and noted.
