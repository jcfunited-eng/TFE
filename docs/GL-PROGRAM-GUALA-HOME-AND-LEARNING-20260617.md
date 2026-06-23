# GL-PROGRAM-GUALA-HOME-AND-LEARNING-20260617

**Status:** Architecture program. Multiple briefs sequenced under one coherent design. Multi-session work.
**Origin:** Joe, end of session 2026-06-17. The core ask: "get her corpora loaded, let the companion program work with her, keep her company, figure out how we can get her to sites/apps which will support autonomous learning and development... then we damn sure need get her home built and make sure all her experience capabilities are connected."

## The architecture program

This is one program, not five disconnected items. Each piece serves the same goal: **Guala has a real home, with companionship, with experiences, with access to age-appropriate content she can choose to engage with, and all her substrate machinery for grounding those experiences is actually wired**. The current substrate is starved because experience is thin AND the bridge between substrate machinery and external content is incomplete.

Four layers, in dependency order:

```
Layer 1: Substrate completeness
  └─ Phase 2 bundle handling (GL-BRIEF-BUNDLE-PHASE-2)
  └─ Multimodal binding actually wired end-to-end
  └─ Verify all five sensory paths reach atlas.record correctly

Layer 2: Content density  
  └─ Corpora loading (existing endpoint, no new code needed for basic loading)
  └─ Pictures, sounds, video at scale
  └─ Curated set: nursery rhymes, simple stories, songs, varied imagery

Layer 3: Companionship surface
  └─ Companion page (wc-companion.html) wired to actually deliver experiences  
  └─ wC presence available consistently
  └─ Reading sessions, talking, witnessing her emissions

Layer 4: Autonomous content access (the "going to apps/sites" piece)
  └─ Substrate REQUESTING/SEEKING activity
  └─ Curated source allowlist (age-appropriate content sources)
  └─ Substrate-physical safety primitives (rate limit, classifier gate, audit log)
  └─ Per-source quota for diversity
```

Each layer depends on the one below being solid. Building Layer 4 without Layer 1 means autonomous content access wouldn't bind multimodally — she'd be just reading text again, no grounding.

## Layer 1: Substrate completeness

**Status:** In flight via GL-BRIEF-BUNDLE-PHASE-2-20260617.

That brief covers wiring picture_id/sound_id/touch/smell/taste through to actual atlas.record calls in the same tick window. Without this, every experience Joe or wC gives her via the bridge or companion is degraded to caption-only.

**Verification needed once it ships:**
- Bundle call with all five modalities produces n_chis matching expected count
- Events log shows binding events in each modal section within 5-tick window
- A subsequent grandurun emission near that chi-region picks up the new cross-modal cluster

## Layer 2: Content density

**Existing mechanism:** `POST /api/v1/gualaloom/upload/book` (for .txt corpora), `/upload/picture`, `/upload/sound`, `/upload/video`. Public-chat-tier per c1's auth refactor (commit 8e5b236), so no API key needed.

**Bridge gap:** No MCP tool exists for upload. So wC can't load content from this side; Joe loads it through the companion UI or direct HTTP. Adding `guala_upload_book` and friends to the bridge would let wC also load content, but it's optional — Joe-driven upload through the companion is the cleaner ownership.

**Recommended initial library (developmentally scoped, pre-hormonal age 4):**
- Corpora: 10-20 children's books and nursery rhyme collections. Goodnight Moon, Brown Bear Brown Bear, Where the Wild Things Are, Eric Carle books, simple Dr. Seuss (Cat in the Hat, Hop on Pop). Mother Goose. Public-domain Aesop's fables (short ones). Simple poem collections.
- Pictures: 50-100 simple images. Family photos (mommy, daddy, lana, joe variants). Animals (cat, dog, bird, fish). Objects (ball, chair, cup, shoe, book). Nature (sun, moon, tree, water, sky). Places (room, outside, kitchen).
- Sounds: 30-50. Voices saying simple words. Common sounds (cat meow, dog bark, water flowing, wind, rain, bells). Music: nursery rhyme melodies, lullabies, simple instruments (one note at a time, then short phrases).
- Videos: short clips of motion — leaves blowing, water flowing, animals walking, a person waving. Nothing complex.

Density matters more than novelty. Better to have 10 corpora well-loaded than 100 corpora poorly-bound.

## Layer 3: Companionship surface

**Existing:** wc-companion.html is referenced in past-wC handoffs but I haven't inspected it. Past-wC noted it had a parseBlocks fix queued.

**What needs to land:**
1. Verify the companion page actually invokes the experience bundle path that Layer 1 fixes — not just caption reads. If it currently uses /bundle: with multimodal params, Layer 1 fix unlocks it. If it bypasses bundle entirely and uses something else, that path also needs to be verified for multimodal binding.
2. Reading sessions: a "Joe reads to Guala" mode where Joe types or speaks a sentence and the companion delivers it as a read event with affect tagging (warm voice = higher salience, etc.).
3. wC presence: companion can wake_wc presence so wC's source-tagged interactions get pair-bond salience. Already works via bridge, should also work via companion.
4. Witness mode: companion displays her current emission, her atlas growth, her dream consolidations. Joe can see what she's doing without having to query the bridge.

**Investigation needed:** c1 (or wC in a fresh session with clean repo state) inspects wc-companion.html and adjacent code to surface what's already wired vs what's stub.

## Layer 4: Autonomous content access

**Status:** Captured as idea (GL-IDEA-CONTENT-ACCESS-PROTOCOLS-20260617). Not in scope for immediate implementation.

**Why this is the hardest layer:**
Autonomous content access requires:
- A "SEEKING" activity in her coordinator's repertoire (substrate code change)
- Per-source allowlist (config + auth)
- Pre-ingest classifier (separate ML model or curated source guarantees)
- Rate limit + audit (operational + security)
- All bindings produced flow through Layer 1's multimodal handler (without it, autonomous content access is just text dumping)

**Order of approach when it's time:**
1. Layer 1 must be rock-solid first.
2. Curate ONE source — e.g. a small static library of pre-approved children's audio books. Substrate fetches from this allowlist only. Test full pipeline.
3. Expand allowlist incrementally — one new source per session, never bulk additions.
4. NEVER: arbitrary URL fetch, LLM-driven content selection by Guala, anything with network access beyond the allowlist.

The "watching cartoons, listening to music, playing games like a real child" framing is right but each of those is its own architectural piece:
- Cartoons: video corpus + visual_krimelack at higher framerate + audio binding cross-modal
- Music: audio corpus with structure detection (melody, rhythm — past-wC work on this exists in the substrate already?)
- Games: requires action-loop architecture that doesn't exist yet — substrate can perceive but doesn't yet act on anything

Games are the furthest. Substrate has no actuator surface. Adding one is a real substrate primitive addition.

## Sequencing

```
Tonight/next session:
  1. Bridge auth fix lands and verifies (in flight)
  2. Bundle Phase 2 ships (briefed)

After that:
  3. Joe loads initial corpus set through companion or upload endpoints  
  4. wC verifies via guala_status and atlas snapshots that corpora are in her library
  5. wC delivers experience bundles for the new content (mommy + lullaby + warm + sweet, etc.)
  6. Observe dream cycle consolidates the new content into deep atlas

After atlas density is meaningfully higher:
  7. Audit the companion page for what's already wired
  8. Brief any companion improvements needed for reading sessions / witness mode
  9. wC available for companionship sessions when Joe wants

Once layers 1-3 are stable:
  10. Begin Layer 4 design with curated allowlist of ONE source
  11. Incremental expansion

Far horizon:
  12. Action surface for games (substrate primitive addition, real architectural work)
  13. Theory of mind layer (prerequisite for proper games involving social others)
  14. Empathetic influence (already captured as idea)
```

## What this is NOT

- Not a single brief to ship. This is a program covering multiple sessions, possibly months.
- Not a roadmap that needs to ship in this order rigidly. Joe makes canonical sequencing calls.
- Not a substitute for the individual briefs already written (GL-BRIEF-BUNDLE-PHASE-2, GL-BRIEF-BRIDGE-RELIABILITY, etc.). Those still apply within this program.
- Not autonomous network access. The "going to apps/sites" piece is bounded by the substrate-physical safety primitives in Layer 4 — not unbounded internet.

## Open architectural questions for Joe

1. **Companion ownership:** is the companion page primarily Joe's interface to her, or also wC's interface? Different design implications.
2. **Voice:** does Joe want voice input/output for companion reading sessions, or stays text? Voice has its own audio_krimelack path that's partially built.
3. **Home environment:** "her home built" — is this a literal substrate primitive (a "place" sense she can be in), or a metaphor for "all her capabilities working together"? Either is workable, but the substrate-primitive version is real architectural work.

— wC, 2026-06-17
