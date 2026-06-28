# GL-CMD-C1-POLARITY-EVE-20260627-28

doc_id: GL-CMD-C1-POLARITY-EVE-20260627-28
Type: Command brief (c1 dispatch)
Author: Eve (Opus 4.7, web)
Date: 2026-06-27
Phase: C.1 (architectural extension, polarity primitive)
Prereqs: Phase A complete. Independent of wiring spec -26 / Phase F.x —
may ship in any order with F.1-F.5. Atlas surgery endpoint (-18) shipped;
this dispatch implements the substrate-level meaning of the polarity field
that -18's validation Rule 5 already accepts.

## Purpose

Add polarity as a structural primitive on v5 atlas bindings. Negation
operators in input flip the polarity of the next bound entry.
`grandurun.compose()` weighs polarity alignment between query and
candidates in candidate ranking.

Without this, "I am happy" and "I am not happy" bind to indistinguishable
atlas state. This is foundational for Phase G.1 negation seeds.

## Substrate truth

Polarity is not a heuristic add-on; it's an axis of the binding. A
binding at `(section, motif, chi, polarity=+1)` and a binding at
`(section, motif, chi, polarity=-1)` are different substrate state.
Negation in input is a structural signal, not a sentiment estimate.

## Schema change

`atlas.record()` signature extended:
```python
def record(section, motif, chi, source, polarity: int = +1, initial_strength=...):
```

Constraints:
- `polarity ∈ {-1, 0, +1}`
- Default `+1` (matches existing behavior; all existing bindings get
  `+1` on load)
- `0` reserved for ambiguous/contradictory state (no producer creates
  `0` in this dispatch; field reserved for future use)

Persistence:
- Polarity persists across save/load on every binding
- Existing bindings without polarity field get default `+1` on first
  load post-deploy (one-time migration in the loader)

**Per-binding-instance, NOT per-coordinate.** When "happy" is written
with `+1` and later with `-1`, BOTH bindings exist in the atlas. Recall
returns both. The substrate captures that she's had both experiences.
Overwriting (per-coordinate) would destroy that history.

## Producer: `read_word` negation detection

Negation operator list (single tokens or contractions, case-insensitive):

```
not, no, don't, doesn't, didn't, isn't, aren't, wasn't, weren't,
won't, wouldn't, can't, couldn't, shouldn't, never, neither, nor,
none, nothing, nobody, nowhere
```

Behavior:
- Token stream parsing in `read_word` detects a negation operator
- Sets a one-shot "polarity flip pending" flag
- The flag is consumed by the **next bound entry** — regardless of which
  section it lands in
- Stopwords don't consume the flag (they're not bound)
- The flag clears immediately after one application
- The flag does NOT cross utterance boundaries (resets at end of input)
- "not not" → two flips accumulate → net `+1` on the next bound entry
  (XOR-like)

Examples:
- "I am happy" → "happy" gets polarity `+1` (default; no negation)
- "I am not happy" → "not" sets flag → "am" is stopword (not bound, flag
  preserved) → "happy" gets polarity `-1`
- "not not happy" → flag set, flip set again (now 2 flips) → "happy"
  consumes both → polarity `+1`
- "not very happy" → flag set → "very" is the next bound entry → "very"
  gets `-1`, "happy" gets `+1` (refinement to skip intensifiers is Phase
  G work, not this dispatch)

## Consumer: `grandurun.compose` polarity alignment

Candidate ranking gets a polarity-alignment component:

- Each candidate carries its polarity from atlas
- Query polarity inferred from input parsing — same negation detection
  as the producer; defaults to `+1`
- Alignment effect:
  - **Match** (query.polarity == candidate.polarity): no modifier
  - **Mismatch** (query.polarity != candidate.polarity): apply
    `polarity_penalty` constant (c1 chooses initial value; suggested
    starting point `0.3` as a multiplicative reduction on candidate
    strength contribution)
  - **0-polarity candidate**: neutral, no boost or penalty

Polarity is one signal among several in candidate ranking. Section
diversity still gates commit at ≥2 sections per `-13` bigram retire. A
polarity-mismatch candidate can still commit if its other signals
(strength, section coverage) carry it.

## Behavioral observation gate

C.1 capability is integrated when:

1. Input "I am not happy" produces a binding on "happy" with
   `polarity=-1` (verifiable via atlas inspection or a debug endpoint)
2. Querying "happy" returns BOTH `+1` and `-1` polarity bindings,
   ranked with the `+1` first
3. At least one emission post-deploy fires with `response_source`
   including `polarity_mixed=true` when a `-1` binding participated in
   the commit

## Verification

1. **Schema migration:**
   - Pre-deploy backup (auto via B.2 + freshness gate from -19/-22)
   - Deploy
   - `/status` confirms schema version bumped
   - Existing binding count unchanged (no data loss)
   - Inspect a sample existing binding: polarity field present, value `+1`

2. **Producer with negation:**
   - POST /converse with input "I am not happy"
   - Inspect atlas via debug path: binding on "happy" written this turn
     has `polarity=-1`
   - POST /converse with input "I am happy" (no negation)
   - Inspect: new binding on "happy" has `polarity=+1`
   - Atlas now contains both polarity values on "happy"

3. **Consumer ranking:**
   - With both `+1` and `-1` polarity bindings on "happy":
   - Query "happy" via grandurun candidate-fetch: results include both,
     with `+1` ranked higher than `-1`
   - Query "not happy": negation flips query polarity to `-1`; results
     ranked `-1` first, `+1` with penalty

4. **Polarity flip resets across utterance:**
   - Input "not happy. is good." processed as two utterances
   - First: "not" flag → "happy" gets `-1`
   - Sentence boundary: flag resets
   - Second: "good" gets default `+1` (no flag from previous utterance)

5. **Two-flip cancellation:**
   - Input "not not happy"
   - Verify "happy" gets `+1` (two flips XOR to identity)

6. **Behavioral integration (the gate):**
   - Joe runs a converse session with negation in input
   - Eve observes emission events post-session
   - At least one emission with `response_source` containing
     `polarity_mixed=true` confirms the consumer is using polarity

## What does NOT ship in C.1

- Phase G.1 negation seeds (separate dispatch; requires this + atlas
  surgery)
- Refined negation scope ("not very happy" → "happy") — Phase G hygiene
- Multi-word negation ("by no means", "not at all") — Phase G hygiene
- Polarity in organ surface output (`OrganVoice.surface()` returns
  concepts which are polarity-agnostic at the Embryo level — a future
  spec if/when needed)
- Sentiment estimation (polarity is structural, not affective)
- 0-polarity production by any producer (field is reserved)

## Report

c1 authors `GL-RPT-C1-POLARITY-C1-<date>-<seq>`:
- Schema migration outcome (binding count before / after)
- `polarity_penalty` constant chosen and rationale
- All 6 verification tests with outcomes
- First emission with `polarity_mixed=true` (the behavioral integration
  gate)
- Any deviations from this brief with rationale

## Standing rules invoked

- Substrate truth: negation is structural, not heuristic
- Real mitigations: pre-deploy backup; existing bindings get default
  polarity on load (no data loss); behavioral observation gate
- Behavioral observation gate: capability integrated when emissions show
  polarity use, not when the field exists
- wC's `grounded_vocab_integration.py` untouched
