# GL-CMD-MIC-SENSORY-EVE-20260703-106-v1

doc_id: GL-CMD-MIC-SENSORY-EVE-20260703-106-v1
From: Joe | To: c1b | Deploy vehicle: TBD (diagnosis first)
E-signature declaration: READ-ONLY diagnosis; no code change rides this
dispatch until shape is confirmed.

## Step 0 — durability (standing rule)
Commit THIS file verbatim to docs/ before executing anything below.

## Context

sensory_items=0 in live status. The mic records and transcribes (Joe hears
playback), but Guala binds NO sensory content through the microphone path.
Camera is proven working (15,702 sight fragments). Diagnosis required before
any fix is written.

## Questions (all READ-ONLY)

1. Does the browser mic path send audio frames to a sound-binding endpoint,
   or only transcribed text to /converse? File:line the client path in
   gualaloom.html.

2. Is there a live sound-capture binding path at all (frame-level audio
   → attend_sound), or only uploaded-file attendance (lullaby/bells,
   the 2000-count items)?

3. Camera proves sight capture works (15,702 fragments). Compare the two
   client paths and name precisely what the mic path lacks that the camera
   path has.

4. Fix SHAPE only — no implementation until shape is confirmed. State the
   continuity risk.

## Report
docs/GL-RPT-MIC-SENSORY-C1-<date>-106-v1.md — failures first.

### Changelog
- v1 (2026-07-03, Joe): initial dispatch for mic sensory diagnosis.
