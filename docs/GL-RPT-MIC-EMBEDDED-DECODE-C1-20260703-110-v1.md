# GL-RPT-MIC-EMBEDDED-DECODE-C1-20260703-110-v1

doc_id: GL-RPT-MIC-EMBEDDED-DECODE-C1-20260703-110-v1
From: c1b | To: Eve | Date: 2026-07-03
Responds to: GL-CMD-MIC-EMBEDDED-DECODE-EVE-20260703-110-v1
Deployed SHA: c015dd5cf5845862561883105e392a548d1c0c6f (task:456, live, booted
2026-07-03T21:31:16Z). Rides the same wake cycle as c1a's -107 groove fix.

---

## FAILURES FIRST

### G-110-2: FAIL. Routing is fixed, but real browser mic chunks still mostly fail to
### decode — a new, distinct bug this dispatch did not anticipate or fix.

**What -110 fixed is real and proven** (G-110-1/3/4 below). But when Joe reran the live
test on a fresh mic session, actively speaking, 27 of 28 real `/sound_frame` calls in the
window still failed decode:

```
1783114819108  [sound-frame] 5.054s                                              <- SUCCESS
1783114819247  [sound] cochlear decode failed: ffmpeg produced 0 bytes from 81160 in
1783114824130  [sound] cochlear decode failed: ffmpeg produced 0 bytes from 81160 in
1783114829369  [sound] cochlear decode failed: ffmpeg produced 0 bytes from 81160 in
1783114834197  [sound] cochlear decode failed: ffmpeg produced 0 bytes from 81160 in
1783114839231  [sound] cochlear decode failed: ffmpeg produced 0 bytes from 81160 in
1783114844359  [sound] cochlear decode failed: ffmpeg produced 0 bytes from 81160 in
1783114849265  [sound] cochlear decode failed: ffmpeg produced 0 bytes from 81160 in
1783114857967  [sound] cochlear decode failed: ffmpeg produced 0 bytes from 81160 in
1783114859456  [sound] cochlear decode failed: ffmpeg produced 0 bytes from 81160 in
1783114864433  [sound] cochlear decode failed: ffmpeg produced 0 bytes from 81160 in
1783114869740  [sound] cochlear decode failed: ffmpeg produced 0 bytes from 81160 in
1783114874521  [sound] cochlear decode failed: ffmpeg produced 0 bytes from 81160 in
1783114880940  [sound] cochlear decode failed: ffmpeg produced 0 bytes from 81160 in
1783114887559  [sound] cochlear decode failed: ffmpeg produced 0 bytes from 81161 in
1783114889630  [sound] cochlear decode failed: ffmpeg produced 0 bytes from 81161 in
1783114894622  [sound] cochlear decode failed: ffmpeg produced 0 bytes from 81161 in
1783114899716  [sound] cochlear decode failed: ffmpeg produced 0 bytes from 81161 in
1783114905955  [sound] cochlear decode failed: ffmpeg produced 0 bytes from 81161 in
1783114909788  [sound] cochlear decode failed: ffmpeg produced 0 bytes from 81161 in
1783114914789  [sound] cochlear decode failed: ffmpeg produced 0 bytes from 81161 in
1783114919905  [sound] cochlear decode failed: ffmpeg produced 0 bytes from 81161 in
1783114925025  [sound] cochlear decode failed: ffmpeg produced 0 bytes from 81161 in
1783114929998  [sound] cochlear decode failed: ffmpeg produced 0 bytes from 81161 in
1783114934993  [sound] cochlear decode failed: ffmpeg produced 0 bytes from 81161 in
1783114940865  [sound] cochlear decode failed: ffmpeg produced 0 bytes from 81161 in
1783114945026  [sound] cochlear decode failed: ffmpeg produced 0 bytes from 81161 in
1783114950151  [sound] cochlear decode failed: ffmpeg produced 0 bytes from 81161 in
```

I confirmed with Joe directly before drawing conclusions: he had reloaded
`gualaloom.html` fresh, mic on, and was actively speaking throughout this entire window —
this is not a stale pre-deploy session. Only the very first call succeeded (5.054s,
tick-adjacent `[cochlear-debug]`: `{'very_low': 148, 'low': 90, 'low_mid': 64, 'mid': 84,
'mid_high': 124, 'high': 114}`). Every chunk after that — all ~81,160 bytes, consistent
with `MediaRecorder.start(5000)`'s 5-second timeslice — failed with the exact same "0
bytes produced" signature as a corrupt/unparseable input.

**Leading hypothesis, not yet proven**: `MediaRecorder`'s chunked WebM output only
produces an independently-decodable file on the session's first `ondataavailable` blob
(EBML header + Segment info + first Cluster). Every subsequent blob (fired every 5s for
the life of the recording) is a bare Cluster continuation of the *same* logical Segment —
valid when concatenated onto the first blob, not valid as a standalone file. Feeding one
of those continuation blobs to `ffmpeg -i pipe:0` alone would produce exactly this
signature: a clean run, zero decodable output, no error. This is a well-known
`MediaRecorder`-with-timeslice gotcha, consistent with everything observed, but I have not
confirmed it by inspecting the actual bytes (no code path currently captures a failing
`audio_bytes` sample for offline inspection) — flagging as strong-but-unconfirmed.

**Important negative control, so this isn't mistaken for real speech data**: during this
same window, 11 *other* `[cochlear-debug]` lines appeared showing successful decodes with
much smaller magnitudes (22–168 events/band). These are **not Joe's mic** — cross-checked
against the substrate event stream, each lines up with a `sound_frame_bound` event with
`duration_s` of ~1.0–1.2s (e.g. `1783114819102` → `duration_s: 1.03`, `1783114945026`-
adjacent → `duration_s: 1.22`), far shorter than a 5-second mic chunk, and each coincides
with an `emission`/`self_heard` event (`"jo be"`, `"moon g i'll"`). This is Guala's own
`espeak-ng` self-voice injection (`gualaloom_v5_engine.py:5677`, flagged as an untouched,
already-correct caller in G-110-1) being fed back into her own hearing after she speaks —
a real, working, but entirely separate mechanism. Reporting this explicitly so it is never
mistaken for evidence that her mic works.

**Net: with only one successful real-mic decode in the whole session, there is no
comparable pair of speech/silence samples to evaluate — G-110-2's actual question (does
speech separate from silence) cannot be answered today.** Per the CMD's own rule
(indistinguishable/no separation → FAIL, stop, report verbatim), this is FAIL. Per the
CMD's own scope declaration ("decode plumbing only... no cognition-path change... no
constants"), I have not attempted to fix `MediaRecorder` chunking today — that is a new,
separate problem for its own dispatch, not a failure of what -110 was built to do.

---

## WHAT -110 ACTUALLY FIXED (and did, correctly)

**G-110-1 — code proof: exactly ONE decode implementation, no live raw-bytes path to
`process_sound_frame` remains: PASS.**

```
$ grep -n "process_sound_frame(" dsf_ai_service/*.py dsf_ai_service/**/*.py
app.py:1568:                 _guala.process_sound_frame(wav)               <- via helper (change 3)
substrate_runner.py:974:     _guala.process_sound_frame(_wav)              <- via helper (change 2)
substrate_runner.py:2465:    _guala.process_sound_frame(audio_bytes)       <- handle_sound_frame, see below
gualaloom_v5_engine.py:4658: def process_sound_frame(self, audio_bytes):   <- definition
gualaloom_v5_engine.py:5677: self.process_sound_frame(f.read())           <- self-voice, real WAV file
```

Two callers besides the two I changed:
- `gualaloom_v5_engine.py:5677` — self-voice injection, reads an `espeak-ng`-generated
  **real WAV file** and feeds its bytes directly. Never broken (proper WAV, not WebM),
  correctly out of scope. This is exactly the mechanism behind the 11 "successful" samples
  discussed above.
- `substrate_runner.py:2465` — `handle_sound_frame`, registered in
  `OP_HANDLERS["sound_frame"]` for `dispatch(op, args)`. **Checked and confirmed
  unreachable**: `grep -rn "dispatch("` across `app.py` and `substrate_runner.py` finds
  only the `def dispatch(op, args)` definition — no caller anywhere in the current
  codebase invokes it. Leftover from the retired separate-substrate-process/socket-RPC
  architecture (the socket server itself was deleted per `GL-CMD-PROCESS-COLLAPSE-61`).
  Dead code, not a live raw-bytes path. Flagging plainly rather than silently passing over
  a grep hit that superficially looks like a violation; not fixed today (out of this
  dispatch's declared scope), worth a cleanup note for later.

**G-110-3 — decode-failure guard fires on the embedded path: PASS, doubly confirmed.**
A deliberately corrupt 36-byte chunk through the live `/sound_frame` endpoint:
```
$ curl .../sound_frame -d '{"text":"<36-byte garbage b64>","source":"g110-test"}'
{"ok":false,"error":"decode_failed"}
[sound] cochlear decode failed: ffmpeg produced 0 bytes from 36 in
```
Exact match to spec. Additionally — and this is the accidental silver lining of G-110-2's
FAIL — the guard fired correctly **27 more times live, on real traffic**, throughout
Joe's session: every failed chunk returned `decode_failed` cleanly and logged the guard,
and **zero raw WebM bytes reached `process_sound_frame` at any point**. Before -110, this
same traffic would have silently produced 33 samples of meaningless "successful" cochlear
noise (see `GL-RPT-MIC-DEPLOY-C1-20260703-108-v1.md`'s before-baseline). Now it fails
loudly and honestly instead. That is real, working progress even though the top-line "can
she hear Joe" answer is still no.

**G-110-4 — lock hygiene: decode demonstrably outside `_guala.lock` in both modes: PASS.**
By code placement, not requiring a live race test: in the embedded path, `_webm_to_wav_bytes()`
runs inside `_decode()`, itself dispatched via `run_in_executor` (off the asyncio event
loop) and BEFORE `_guala.process_sound_frame(wav)` is ever called — the ffmpeg subprocess
call holds no engine lock. In the drain loop, the same ordering holds: `_webm_to_wav_bytes()`
runs before `_guala.process_sound_frame(_wav)`, which is the only call in this function
that touches `self.lock` (via the engine's own internal locking, unchanged). Confirmed by
reading both call sites directly in this deploy's diff.

---

## DEPLOY RECORD

```
Pinned SHA:  c015dd5cf5845862561883105e392a548d1c0c6f (detached worktree, git archive
             from this exact commit)
Image:       dsf-ai:deploy-20260703T212947Z
Task def:    dsf-ai-task:456, task c480f34462a0453c904e6e744f363cf5, RUNNING
Boot banner: [build] git_sha=c015dd5cf5845862561883105e392a548d1c0c6f built=2026-07-03T21:31:16Z
[curriculum] autostart disabled by env   <- -109's fix still holding, confirmed this boot
```
This deploy carries the full range since `16bc0c2` (the -108/-109 deploy), including
c1a's -107 groove-fix code (`417b468..51de899`, already an ancestor before -110 began) —
Eve's "one wake cycle" instruction is satisfied; -107's own gates are c1a's to file.
For c1a: -107's telemetry is confirmed live and populated this boot, e.g. an `EMITTING`
`activity_started` at tick 14486463 with `needs_sd: {"stability": -0.043, "novelty":
-0.2631, "connection": 0.4275}` and real `top_scores`. I did not capture a clean
≥3-consecutive-`ATTENDING_VISUAL` streak (A.3) — this window was converse/EMITTING-heavy
from Joe's live session; that capture is yours to finish.

---

## STATE

`-110`'s own job — one decoder, at the boundary, used by both live callers, outside the
lock, guard consolidated — is done and correctly gated (G-110-1/3/4 PASS). The routing bug
G-108-2 found is closed. What replaced it is a new, more fundamental problem: real browser
mic audio still can't reach her, now for a WebM-chunking reason rather than a routing
reason. Recommend a follow-up dispatch scoped narrowly to either (a) reassembling
`MediaRecorder` chunks client-side before sending (concatenate onto the first blob's
header), or (b) sending self-contained chunks some other way (e.g. `requestData()` +
restart the recorder each interval, or a different codec/config). Not attempted today —
outside this dispatch's decode-plumbing scope, and Eve's call on priority.

End report.
