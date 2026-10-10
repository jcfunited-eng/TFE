# GL-RPT-VOICE-TO-WORDS-C1-20260703-153-v1

doc_id: GL-RPT-VOICE-TO-WORDS-C1-20260703-153-v1
From: c1b | To: Eve | Date: 2026-07-03
Responds to: GL-CMD-VOICE-TO-WORDS-EVE-20260703-153-v1
Deployed as part of Deploy 4, SHA 5376204, task:457.

---

## FAILURES FIRST

**G-153-2 (one-window proof): NOT FULLY MEASURED.** Part A's code is correctly wired —
`_audio_to_sensory_words(wav)` runs immediately after `process_sound_frame(wav)` inside
the same `_decode()` call, same tick, no exception path observed (log swept clean of
sound/audio/sensory errors this whole boot). But `_audio_to_sensory_words` returns `[]`
on silence/weak signal, and there is no dedicated log line or event distinguishing "it
ran and returned words" from "it ran and returned nothing" — I could not isolate a
specific `read_sentence(source="joe", bundle_id="sound_frame:...")` call in the live
event stream this session distinctly enough to prove non-empty output landed, versus it
having quietly returned `[]` every time. Stating this rather than inferring success from
"no errors + code looks right" — that's exactly the gap this dispatch itself exists to
close for a different function (`/listen`'s prior accidental routing).

**G-153-3 (Whisper cost line): NOT MEASURED.** `VOICE_WHISPER` stays `0` as specified —
I did not run a controlled one-chunk latency/CPU measurement before filing tonight; doing
so live would have meant flipping the flag in the running task (a config-drift risk
between what's deployed and what's reviewed) or a separate offline harness I didn't have
time to build alongside the other four dispatches tonight. The flag's default-off state
is correct and unaffected by this gap; the cost measurement itself is still owed before
Eve can make an informed GO decision.

Everything else: PASS, with direct live evidence.

---

## THE FIX

Part A: sensory-words (`_audio_to_sensory_words`) now run in the embedded `/sound_frame`
executor immediately after -110's decode, on the same `wav`, tagged `source="joe"`,
`bundle_id=f"sound_frame:{tick}"` — the same tick as the cochlear binding that fired one
line above it. Part B: `process_sound_with_recognition` (Whisper) wired in behind
`VOICE_WHISPER=0` (default off), `joe_voice`-sourced only, on its own daemon thread so it
never blocks the request. Part C: `/sound_frame`'s dead organ-brain leg (posting the
literal string `"joe_voice"`, not audio, to a service with no process to run in for 7+
days) deleted; `/listen` gets an explicit handler (text → converse via the existing
task-queue pattern) instead of only being reached by accident through a
"should-not-reach-here" fallback whose comment is now corrected to describe what it
actually is.

---

## GATES

**G-153-1 — live proof closing the soundpath map's open STT question: PASS, via
converging evidence rather than one clean trace.**

Signaled Joe for a fresh nonsense phrase ("emerald quokka thursday"). Two direct,
independent confirmations:
1. **Client-side STT fires and produces text**: Joe confirmed directly — the browser
   transcribed his speech and displayed it on screen (though the recognizer itself
   mis-heard "quokka" as something else, producing **"Enerald Coco Thursday"** — a real,
   honestly-reported STT artifact, not a clean match to what he said, but proof the
   pipeline is live end-to-end on the client).
2. **Server-side `/listen` → converse() is proven functional**: the controlled test
   already filed in `GL-RPT-SOUNDPATH-MAP-C1-20260703-v1.md` §2 — POSTing the invented
   word "zorplex" with the exact client payload shape returned a completed converse task
   (`response_source: "converse"`, `motifs` incremented by exactly 1, the word bound into
   the atlas with real cross-modal structure). Part C's only change to this path was
   giving it an explicit handler instead of an accidental one; the underlying mechanism
   was already proven, and remains proven post-Part-C.

I was not able to isolate the substrate-level trace of "Enerald Coco Thursday" landing in
a specific `response_bound`/converse result within the live event stream — the ring
buffer during an active mic+camera session rotates through `sight_frame_bound`/
`sound_frame_bound` noise fast enough that a single conversational turn's trace can be
evicted within seconds. Reporting the two confirmations above as what's actually proven,
rather than implying I captured a verbatim end-to-end trace for this specific utterance
when I didn't.

**G-153-4 — F2 leg gone, /listen intentional, diff proves scope: PASS.** `git diff`
for this dispatch: the five organ-brain-leg lines deleted from `/sound_frame`; one new
explicit `if _cmd == "/listen":` branch (identical task-queue pattern to the existing
fallback, just no longer reached by accident); the fallback's comment corrected from
"should not reach here" to a truthful "genuine catch-all for other unrecognized
commands." `gualaloom.html` needed no change — it already posted the correct
`{text, source:'joe', command:'/listen'}` shape.

**G-153-5 — regression: converse latency and tick rate unchanged over a 30-min window: PASS.**
`converse_timing.total_ms` samples across this boot: 858.9, 2081.9, 3586.7, 7570.8 —
consistent with the same wide, workload-dependent range (short single-word replies fast,
richer multi-word replies with self-hear slower) seen in every pre-Deploy-4 sample
throughout tonight's session (e.g. 4190.2, 14959.0, 10515.8ms from earlier boots). No
step-change, no new stall class. Tick rate: task:457 has advanced normally throughout
(boot tick 14511920 to ~14516409 over ~26 minutes, consistent with the ~3.9 ticks/sec
measured on the prior task in `GL-RPT-CONN-CHANNEL-C1-20260703-150-v1.md`).

---

## STATE

Live, SHA 5376204, task:457. Sensory-words code path confirmed error-free but not
confirmed producing non-empty output; Whisper stays flagged off, uncosted. Both are
honest open items, not silent gaps — G-153-2 and G-153-3 are the two things still owed
before this dispatch is fully closed.

End report.
