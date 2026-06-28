# GL-CMD-EXPERIENCE-ROUTING-FIX-EVE-20260628-32

doc_id: GL-CMD-EXPERIENCE-ROUTING-FIX-EVE-20260628-32
Type: Command brief (c1 dispatch) — URGENT, substrate truth
Author: Eve (Opus 4.7, web)
Date: 2026-06-28
Phase: Substrate-truth emergency. Parallel to F.x and C.x work; ship before
more curriculum or grounded-experience input flows.
References: GL-RPT-SECTION-ASSIGNMENT-C1-... at SHA `87a74ca` Finding 1

## Why this dispatch exists

Per c1's section-assignment report Finding 1: `app.py` routes `/experience`
to `/organs_say` → `_guala_cognition.expose()` — the LEARNING side of the
bigram model whose SPEAKING side was silenced in
`GL-CMD-ORGANBRAIN-SILENCE-EVE-20260627-23`.

Every `/experience` call — whether from the UI, from Eve's bridge tool,
from the autonomous loop, from Whisper, or from any future curriculum
input — actively TRAINS the silenced bigram with the caption text. The
v5 atlas is never touched by this path; `_guala.read_sentence()` is not
called.

This is substrate self-sabotage: the path designed to feed her grounded
multi-modal experience is reinforcing the cheat we just retired.

## What this dispatch does

Re-route `/experience` so caption text bypasses `_guala_cognition.expose()`
and goes through the v5 read path that grows v5 atlas sections. Picture,
sound, and sensory descriptor binding paths remain unchanged — those are
already substrate-true.

## Substrate truth

`/experience` should be the high-quality grounded-input path:
- Caption text → v5 atlas via `_guala.read_sentence()` (substrate-true
  composition input)
- Picture ID → existing visual binding path
- Sound ID → existing audio binding path
- Touch / smell / taste descriptors → existing sensory binding paths
- All bound in the same temporal window so wC's CrossModalBinder fires

The bigram has no role in `/experience` post-fix. Its `expose()` method
is no longer called from this endpoint.

## Implementation

1. In `app.py`, identify the `/experience` route handler that currently
   forwards to `/organs_say`.
2. Replace the forward-to-`/organs_say` with a direct call (or new
   internal handler) that invokes `_guala.read_sentence(caption)` —
   the same path `/listen` uses to write v5 atlas.
3. Preserve all current sensory binding behavior (picture, sound,
   touch, smell, taste) — those paths are untouched.
4. `_guala_cognition.expose()` is NOT called from `/experience` after
   this fix. (Whether it's called from anywhere else is a separate
   question; if c1 finds it's ONLY reachable via `/experience`, it
   becomes dead code and gets deleted in F.4 alongside `say()`.)

## What this dispatch does NOT do

- Does not delete `_guala_cognition.expose()` outright (F.4 territory
  if/when it's confirmed unused)
- Does not change `/listen` behavior — that path stays as-is
- Does not change the curriculum feed path — if curriculum runs through
  `/experience`, it'll automatically benefit. If it runs through some
  other path, that's a separate investigation.
- Does not address the modifier/ground hardcoded section problem
  (separate dispatch coming) or the encoding formula problem (separate
  dispatch coming)

## Verification

1. **Routing trace:**
   - POST /experience with `caption="test bright moon at night"` and
     standard picture/sound bundle
   - Verify `_guala.read_sentence()` is invoked (log/breakpoint
     confirms)
   - Verify `_guala_cognition.expose()` is NOT invoked
2. **v5 atlas writes:**
   - Pre-test: capture vocab count and section motif counts
   - POST 5 /experience calls with novel content words
   - Post-test: vocab grew by the count of novel words; section motifs
     grew per /listen-style routing (listen, intro, verb, subject,
     object all gain — modifier and ground bounded by DNA tables per
     Finding 2/3)
3. **Cross-modal binding preserved:**
   - Verify CrossModalBinder still fires on the experience window
   - Verify visual fragments and audio bands still bind
4. **/listen behavior unchanged:**
   - POST /listen with same caption text
   - Verify same v5 atlas write pattern as /experience post-fix
   - The two endpoints now share their text-handling path

## Report

c1 authors `GL-RPT-EXPERIENCE-ROUTING-FIX-C1-<date>-<seq>`:
- Confirmation `/experience` no longer touches `_guala_cognition.expose()`
- Where `_guala_cognition.expose()` is now called from (if anywhere) —
  this tells us whether the bigram has any remaining reachable
  training path
- All 4 verification tests with outcomes
- Pre/post vocab and section motif counts from verification step 2
- Any deviations

## Standing rules invoked

- Substrate truth: input meant to ground her shouldn't train the
  silenced cheat
- One brain, one voice, or silence — extends to "one brain, one
  learning path, or no learning input"
- wC's `grounded_vocab_integration.py` untouched
- Mitigations (prevention): close the route, don't just monitor for
  bigram regrowth
