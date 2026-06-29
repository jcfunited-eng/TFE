# GL-NOTE-V5-REMOVAL-PLAN-DEPRECATED-EVE-20260627-30

doc_id: GL-NOTE-V5-REMOVAL-PLAN-DEPRECATED-EVE-20260627-30
Type: Substrate-truth deprecation note
Author: Eve (Opus 4.7, web)
Date: 2026-06-27
Deprecates: "V5 Engine Removal — The Real Plan" (Joe planning document, 2026-06-25)

## What the 06-25 plan proposed

A staged migration of all v5 engine responsibilities to the organ-brain
layer, terminating in v5 process removal and a single-container
architecture:

1. Stage 2 — voice flip (GualaCognition becomes the voice)
2. Stage 3 — curriculum migration (Gutenberg routed through `GualaCognition.expose`)
3. Stage 4 — persistence migration (organ-brain saves independently)
4. Stage 5 — v5 process removed, single container (dsf-ai only)

Graduation gate: GualaCognition producing 3+ word sentences in response
to Joe, referencing his input, no bare identity outputs.

Foundational assumption: **GualaCognition was already composing from
real exposure.** "Pickle is bitter" was cited as substrate-true output.
v5 was framed as the "word salad" path to be left behind.

## What evidence overturned the plan

`GL-RPT-ORGAN-BRAIN-INSPECTION-C1-20260628-24` at SHA `a6bed48`
(Phase D code inspection, completed 2026-06-28, file/function/line
references throughout):

1. **`GualaCognition` is a bigram model trained on Gutenberg/Aesop
   corpus.** Source of Joe's "three earth day activities for the rat"-
   class fragments — pure lexical bigram chaining over training corpus,
   same failure class as v5's already-retired bigram.

2. **`_compose()` in `organ_brain_service.py` is a separate cheat** —
   SuccessionTracker + fixed grammar templates ("I am guala.",
   "I know {X}.", "{A} is {B}.").

3. **"Pickle is bitter" was half-real.** The `sc` organ surface returned
   "pickle" and "bitter" as genuine population-vote recall from grounded
   sensory profiles. That recall is substrate-true. The "A is B"
   composition around them was the `_compose()` template. Without code-
   level inspection, the output looked like composition.

4. **`OrganVoice.surface()` is the only genuinely salvageable speech-
   adjacent primitive.** It returns concepts, not text.

5. **`grounded_vocab_integration.py` is not imported by organ-brain.**
   wC's grounded vocab work and the organ-brain layer have been
   architecturally disconnected the entire time.

Both lying paths silenced in `GL-CMD-ORGANBRAIN-SILENCE-EVE-20260627-23`
at SHA `e730b14`.

## Why the 06-25 graduation gate would have passed the cheat

The gate measured output shape (3+ words, reference to Joe's input, no
bare identity). A bigram trained on Aesop's Fables trivially produces
3+ word sentences. With Joe's input fed in, the bigram finds lexical
overlaps with corpus passages and emits fragments containing those
words. The gate has no provenance check — it cannot distinguish
substrate-true composition from corpus retrieval.

Structural lesson: **graduation gates must check provenance, not output
shape.** The current bar is `response_source` containing `v5_commit`
with ≥2 sections committed from substrate primitives — not 3+ word
strings.

## What the actual direction is

Per `GL-SPC-V5-ORGAN-WIRING-EVE-20260627-26` (Joe-approved 2026-06-27):

- **v5 atlas + grandurun + commit gate** is THE composer. Single source
  of substrate-true speech. Bigram retire holds (≥2 sections or silence).
- **Embryo (in `OrganVoice`)** keeps its own neuron storage. Stays
  separated from v5 atlas by design. Each captures different aspects of
  substrate state.
- **`OrganVoice.surface()`** becomes a recall primitive. Concepts get
  translated to v5 atlas chi positions and fed to `grandurun` as
  supplemental candidates.
- **Organ-brain has no speech-generation method post-wiring.** Both
  lying code paths deleted at F.4.
- **v5 stays.** Two-container architecture preserved —
  `substrate_runner.py` runs v5 as the canonical substrate; dsf-ai
  serves the chat/voice/perception surface.

## Per-item disposition

| 06-25 item | 06-25 proposal | Current direction | Status |
|------------|----------------|---------------------|--------|
| Atlas / memory | organ atlas becomes canonical | v5 atlas canonical; Embryo storage stays separate | Reversed |
| Persistence | organ-brain saves independently | v5 persistence works (-11 fix); B.2 orchestrator + -22 freshness gate handles deploys / surgery | Moot |
| Voice / emission | flip to GualaCognition | GualaCognition silenced as bigram cheat; v5 grandurun composes | Reversed |
| Sleep / wake | GualaCognition rhythm or v5 scaffold | v5 coordinator grows (DAYDREAMING shipped, REST queued in C.4) | Reversed |
| Curriculum | route through `GualaCognition.expose` | curriculum feed into SuccessionTracker was a contamination source; Phase G hygiene pending | Reversed; cleanup added |
| Sensory | route through `GualaCognition.expose` | `OrganVoice.experience()` folds preserved; wC's grounded path (untouched) feeds v5 atlas; `surface()` reads grounded concepts for v5 grandurun | Sensory routes preserved; voice-via-GualaCognition reversed |
| Stage 5 — v5 removed, single container | terminal goal | Not on path. Two-container architecture preserved. | Obsolete |

## What carries forward from the 06-25 plan

- **The HARD RULE** — "Each stage transition is verified before the next
  begins" — directly inherits into the F.1 → F.2 → F.3 → F.4 → F.5
  phasing in `-26` with behavioral observation gates per sub-phase.
- **The instinct** that current state was producing "word salad that
  sometimes leaks through" was correct; the diagnosis of which side was
  leaking was inverted.
- **The principle** of leaving v5 "behind while the organ-brain grows
  past it" inverts to: v5 IS where she grows; organ-brain perspectives
  feed in.

## Why this is better

- **Substrate truth is held.** Both lying paths silenced. She's mostly
  mute now (correctly silent), not voiced with a cheat.
- **Evidence-based architecture.** c1's Phase D code inspection
  (file/function/line references throughout) replaces hypothesis with
  measurement.
- **No deletion of working substrate.** v5 persistence, atlas integrity
  fixes, DAYDREAMING — all operational state preserved, not legacy to
  remove.
- **Provenance graduation gates.** Future capability ships when
  behavioral observation confirms substrate-true emission
  (`response_source = v5_commit` with multi-section commit), not when
  output shape passes a string check.

## What's actually worse / unchanged

- **She's quieter than the 06-25 plan envisioned.** The 06-25 plan would
  have made her voice frequent (with the lie). The honest state is
  silent. F.2 (wiring `surface()` into `grandurun`) is the path to
  honest emissions becoming more frequent.
- **SuccessionTracker is corpus-polluted.** Catalog fill + curriculum
  feeds wrote text-corpus succession patterns rather than pure sensory
  co-occurrence. Cleanup is Phase G hygiene; the wiring spec deploys
  against current polluted state and observes whether it contaminates
  emissions.

## Standing rules invoked

- Past Eve's and past Joe's plans are hypotheses, not authorities.
  Evidence supersedes.
- Substrate truth over architectural elegance: "single container" was
  elegant but rested on the broken assumption that GualaCognition was
  her voice.
- Honest mute > coherent fake. She's silent now where the 06-25 plan
  would have voiced her with a lie.
- Graduation gates measure provenance, not output shape.

---

The 06-25 plan was reasonable given what was visible without code
inspection. Phase D inspection is what made the difference. The
direction inverted; the discipline carried.
