# GL-CMD-VOICE-TO-WORDS-EVE-20260703-153-v1

doc_id: GL-CMD-VOICE-TO-WORDS-EVE-20260703-153-v1
From: Eve | To: c1b | Vehicle: Deploy 4 (server parts) + static (client
bits). Responds to: GL-RPT-SOUNDPATH-MAP-C1-20260703-v1 §1/§2.
E-signature declaration: E1/E5 enabler — Joe's speech gains word-lane
binding co-windowed with its cochlear texture; the STT leg becomes
intentional instead of accidental.
Substrate-truth declaration: wiring EXISTING word extractors into the
live route; decode/extract outside the engine lock; source-tagged per
-152; no cognition-path change; Whisper leg flagged + costed, not
assumed cheap. Removes one dead mislabeled leg.

## Step 0 — durability
Commit THIS file verbatim to docs/ before implementing.

## Findings being fixed (map §1/§2, filed)
F1 Live /sound_frame binds cochlear energy only; both word extractors
   (_audio_to_sensory_words FFT sensory-words; process_sound_with_
   recognition Whisper) live in the never-executing drain branch.
F2 The organ-brain "transcription" leg posts the literal string
   "joe_voice" to a dead service — dead, mislabeled code.
F3 Browser STT reaches converse() only via /listen's "should not
   reach here" fallback; /experience leg dead behind _is_remote().
F4 Whether Joe's browser STT actually fires live is UNPROVEN.

## The fix
Part A (cheap words, Deploy 4): in the embedded /sound_frame executor,
  after the -110 decode succeeds, call _audio_to_sensory_words on the
  decoded audio; route resulting words through read_sentence with
  source per -152 tagging and the SAME bundle window as the cochlear
  binding (word + texture, one window = E1). Outside the engine-lock
  decode section as today.
Part B (Whisper, flagged): process_sound_with_recognition wired behind
  env flag VOICE_WHISPER=0 default, joe-tagged sources only, async off
  the request path; FIRST measure cost on one chunk (latency, CPU) and
  file it — the flag flips to 1 only on Eve GO after the cost line.
Part C (route truth): give /listen an intentional handler (text →
  converse, source from request) and delete the fallthrough comment
  path; retire F2's dead leg entirely; client (gualaloom.html) posts
  STT text to the intentional route with source="joe". Static ship.

## Gates (failures first, NOT MEASURED where true)
G-153-1 Live proof: Joe speaks a nonsense phrase on signal; the FFT
        sensory-words bind (event evidence) AND the STT text arrives
        at converse with source="joe" (server log of the exact
        phrase). This closes map §2's open item.
G-153-2 One-window proof: a spoken chunk's word bindings and cochlear
        bindings share a bundle window (event evidence).
G-153-3 Whisper cost line filed; flag remains 0 unless Eve flips.
G-153-4 F2 leg gone; /listen intentional; diff proves scope.
G-153-5 Regression: converse latency and tick rate unchanged over a
        30-min window.

Joe's part: one short nonsense phrase at c1b's signal ("purple bicycle
seventeen" class), then normal talk — and stay a few minutes after.

### Changelog
- v1 (2026-07-03, Eve): from the soundpath map. Sensory-words now,
  Whisper flagged+costed, accidental route made intentional, dead leg
  removed.
