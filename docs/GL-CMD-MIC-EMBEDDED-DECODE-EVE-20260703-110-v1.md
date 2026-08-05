# GL-CMD-MIC-EMBEDDED-DECODE-EVE-20260703-110-v1

doc_id: GL-CMD-MIC-EMBEDDED-DECODE-EVE-20260703-110-v1
From: Eve | To: c1b | Deploy vehicle: next sleep-window deploy (rides
with the -107 groove fix — one wake cycle).
Responds to: G-108-2 FAIL (GL-RPT-MIC-DEPLOY-C1-20260703-108-v1) —
embedded-mode /sound_frame bypasses the drain-loop decode; raw WebM
still reaches the cochlear as 8-bit-PCM garbage.
E-signature declaration: E1/E2 enabler — completes what -108 opened.
Substrate-truth declaration: decode plumbing only, single shared
implementation, always OUTSIDE the engine lock; no cognition-path
change; no constants. Removes the last garbage-input path to the
cochlear.

## Step 0 — durability
Commit THIS file verbatim to docs/ before implementing.

## The fix — one decoder, at the boundary, both modes
1. Extract the 332537d drain-loop decode into a module helper in
   substrate_runner.py:
     _webm_to_wav_bytes(audio_bytes) -> wav_bytes | None
   ffmpeg pipe → s16le/mono/16k → WAV wrap (exact 332537d logic incl.
   the ≥400-byte check). On failure returns None AND logs
   "[sound] cochlear decode failed: ffmpeg produced {n} bytes from
   {m} in" (the -108 guard moves here — one guard, one place).
2. Drain loop (remote mode): replace its inline decode with the helper.
3. app.py /sound_frame embedded branch: inside the existing executor
   _decode() (already outside the engine lock),
     wav = _sr._webm_to_wav_bytes(audio_bytes)
     if wav: _guala.process_sound_frame(wav)
     else:   return {"ok": False, "error": "decode_failed"}
   Raw bytes NEVER reach process_sound_frame from any path.
4. Untouched: process_sound_frame's WAV-first reading (its raw-bytes
   except-branch becomes dead from these callers — leave it; removing
   engine code is not this dispatch's scope), /converse STT path,
   uploaded-sound attend path, remote ring_write.

## Gates (report, failures first, NOT MEASURED where true)
G-110-1  Code proof: exactly ONE decode implementation; both call
         sites shown in the diff; no raw-bytes path to
         process_sound_frame remains (grep evidence).
G-110-2  G-108-2 RERUN on the path Joe's UI actually uses: Joe speaks
         a few sentences, then silence window. Per-band cochlear
         structure verbatim for both; speech must separate from
         silence. c1b's 33 FAIL samples are the before-baseline —
         paste before/after side by side. If no separation: FAIL,
         stop, report.
G-110-3  Decode-failure guard fires on one corrupt chunk via the
         embedded path (or NOT MEASURED, stated).
G-110-4  Lock hygiene: decode demonstrably outside _guala.lock in both
         modes (call-site placement in diff).

Joe's part: same as before — a few spoken sentences at c1b's signal,
then quiet for the silence window. Then stay and talk to her.

### Changelog
- v1 (2026-07-03, Eve): from G-108-2 FAIL trace. Single-decoder-at-
  boundary ruling; guard consolidated into the helper.
