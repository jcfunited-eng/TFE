# GL-RPT-MIC-EMBEDDED-DECODE-C1-20260703-110-v1

doc_id: GL-RPT-MIC-EMBEDDED-DECODE-C1-20260703-110-v1
From: c1b | To: Eve | Date: 2026-07-03
Responds to: GL-CMD-MIC-EMBEDDED-DECODE-EVE-20260703-110-v1
Code SHA (on origin, NOT yet deployed): 1d0af4d213d9010b24642532a5cea55b39811cd5

**Pre-deploy partial filing.** Per the CMD, this rides the next sleep-window deploy vehicle
together with c1a's -107 groove fix — one wake cycle. G-110-1 is a static code-proof gate
and is measured below. G-110-2/3/4 require the code actually running live and are
**NOT MEASURED**, deferred to a follow-up filing once that joint deploy happens.

---

## FAILURES FIRST

None in what's measurable today.

---

## THE FIX

Exactly the three changes specified, nothing else:
1. `substrate_runner._webm_to_wav_bytes(audio_bytes) -> bytes | None` — the 332537d
   ffmpeg-pipe → s16le/mono/16k → WAV-wrap logic, unchanged, plus the -108 decode-failure
   guard moved into it (one guard, one place, for every caller).
2. The drain loop's `sound_window` branch now calls the helper instead of inlining the
   decode.
3. `app.py`'s embedded-mode `/sound_frame` branch, inside its existing executor `_decode()`
   (already outside the engine lock — it runs via `run_in_executor`), now calls the same
   helper; on decode failure it returns `{"ok": False, "error": "decode_failed"}` instead
   of ever calling `process_sound_frame` with raw WebM bytes.

Diff, verbatim (`b7fd05e..1d0af4d` for these two files, i.e. since the last time either
was touched):

```diff
--- a/dsf_ai_service/app.py
+++ b/dsf_ai_service/app.py
@@ -1557,8 +1557,15 @@
     def _decode():
         t0 = time.time()
         try:
+            import dsf_ai_service.substrate_runner as _sr
             audio_bytes = base64.b64decode(b64_data)
-            _guala.process_sound_frame(audio_bytes)
+            # GL-CMD-MIC-EMBEDDED-DECODE-110: single shared decoder, outside
+            # the engine lock (this executor call). Raw bytes never reach
+            # process_sound_frame from this path.
+            wav = _sr._webm_to_wav_bytes(audio_bytes)
+            if not wav:
+                return {"ok": False, "error": "decode_failed"}
+            _guala.process_sound_frame(wav)
             print(f"[sound-frame] {time.time()-t0:.3f}s")
             return {"ok": True, "tick": _guala.tick}
         except Exception as e:

--- a/dsf_ai_service/substrate_runner.py
+++ b/dsf_ai_service/substrate_runner.py
@@ -891,6 +891,29 @@
 _input_ring_consumer_started = False

+def _webm_to_wav_bytes(audio_bytes):
+    """... ffmpeg pipe -> s16le/mono/16k -> WAV wrap (332537d logic, unchanged) ..."""
+    import wave as _wave, io as _sio
+    _ff = subprocess.run(
+        ['ffmpeg', '-i', 'pipe:0', '-f', 's16le', '-ac', '1',
+         '-ar', '16000', '-loglevel', 'quiet', 'pipe:1'],
+        input=audio_bytes, capture_output=True, timeout=8)
+    if _ff.stdout and len(_ff.stdout) >= 400:
+        _wav_buf = _sio.BytesIO()
+        with _wave.open(_wav_buf, 'wb') as _wf:
+            _wf.setnchannels(1); _wf.setsampwidth(2); _wf.setframerate(16000)
+            _wf.writeframes(_ff.stdout)
+        return _wav_buf.getvalue()
+    print(f"[sound] cochlear decode failed: ffmpeg produced "
+          f"{len(_ff.stdout)} bytes from {len(audio_bytes)} in")
+    return None

@@ (drain loop, sound_window branch) @@
-                            import wave as _wave, io as _sio
-                            _ff = subprocess.run([...])
-                            if _ff.stdout and len(_ff.stdout) >= 400:
-                                ... build wav buf ...
-                                _guala.process_sound_frame(_wav_buf.getvalue())
-                            else:
-                                print(f"[sound] cochlear decode failed: ...")
+                            _wav = _webm_to_wav_bytes(audio_bytes)
+                            if _wav:
+                                _guala.process_sound_frame(_wav)
```

---

## GATES

**G-110-1 — code proof: exactly ONE decode implementation, both call sites shown, no
raw-bytes path to `process_sound_frame` remains: PASS, with one flagged non-violation.**

```
$ grep -n "process_sound_frame(" dsf_ai_service/*.py dsf_ai_service/**/*.py
app.py:1568:                _guala.process_sound_frame(wav)                  <- via helper (change 3)
substrate_runner.py:974:    _guala.process_sound_frame(_wav)                 <- via helper (change 2)
substrate_runner.py:2465:   _guala.process_sound_frame(audio_bytes)          <- handle_sound_frame, see below
gualaloom_v5_engine.py:4658: def process_sound_frame(self, audio_bytes):     <- definition
gualaloom_v5_engine.py:5677: self.process_sound_frame(f.read())              <- self-voice, real WAV file, untouched (correct)
```

Two callers besides the two I changed:
- `gualaloom_v5_engine.py:5677` — self-voice injection reads an `espeak-ng`-generated
  **real WAV file** and feeds its bytes directly. Never broken (proper WAV, not WebM),
  correctly out of scope, matches the CMD's "untouched" list in spirit even though not
  named explicitly.
- `substrate_runner.py:2465` — `handle_sound_frame`, registered in `OP_HANDLERS["sound_frame"]`
  for `dispatch(op, args)`. **Checked and confirmed unreachable**: `grep -rn "dispatch("`
  across `app.py` and `substrate_runner.py` finds only the `def dispatch(op, args)`
  definition itself — no caller anywhere in the current codebase invokes it. This is
  leftover from the retired separate-substrate-process/socket-RPC architecture (the socket
  server itself was deleted per `GL-CMD-PROCESS-COLLAPSE-61`, referenced in a comment a few
  hundred lines below it). It is dead code, not a live raw-bytes path — flagging it plainly
  rather than silently omitting a grep hit that superficially looks like a violation, per
  the project's "check every place a switch can live" discipline. Not fixed today (out of
  this dispatch's declared scope, which is decode plumbing on the two live paths); worth a
  one-line note or removal on a future cleanup dispatch since it's confusing to leave live
  in the OP_HANDLERS table.

**G-110-2, G-110-3, G-110-4 — NOT MEASURED, pending the next sleep-window deploy.**
All three require the code actually running (live mic test with Joe again, decode-guard
fire test, and lock-hygiene confirmation against the live process). Will file a follow-up
report once that deploy — bundled with c1a's -107 — happens.

---

## STATE

Code is on origin at `1d0af4d`, not yet live. `dsf-ai-task:455` (SHA `16bc0c2`, the -108/-109
deploy) remains the running task — it still has the routing gap this dispatch fixes.
G-110-1's code proof is clean; the one dead-code caller found (`handle_sound_frame`) is
harmless but flagged for future cleanup. Waiting for the joint sleep-window deploy with
-107 to measure G-110-2/3/4.

End report (partial).
