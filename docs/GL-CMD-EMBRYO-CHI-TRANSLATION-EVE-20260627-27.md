# GL-CMD-EMBRYO-CHI-TRANSLATION-EVE-20260627-27

doc_id: GL-CMD-EMBRYO-CHI-TRANSLATION-EVE-20260627-27
Type: Command brief (c1 dispatch)
Author: Eve (Opus 4.7, web)
Date: 2026-06-27
Phase: F.1 (first sub-phase of approved wiring spec -26)
Prereqs: `GL-SPC-V5-ORGAN-WIRING-EVE-20260627-26` approved by Joe (2026-06-27)
Decision references: D2 (skip on miss, debug log)

## Purpose

Add `embryo_concepts_to_chi()` translation utility in
`organ_brain_service.py`. Pure function. No producer-side changes. No
emission-path changes.

This is the foundation for F.2 — F.2 will invoke this function from
/converse to translate `OrganVoice.surface()` output (concepts) into v5
atlas binding refs that `grandurun.compose()` can ingest as supplemental
candidates.

## Substrate truth

The function reads v5 atlas state and returns binding refs. It does NOT
mutate state. It does NOT call `atlas.record`. It does NOT add concepts
to v5 vocab on the fly. If an Embryo concept doesn't exist in v5 vocab,
it's skipped — the drift is observable but never papered over.

## API

```python
def embryo_concepts_to_chi(concepts: List[str]) -> List[BindingRef]:
    """Translate Embryo concepts to v5 atlas binding references.

    For each concept that exists in v5 atlas vocab, returns all binding
    refs (the type grandurun.compose() ingests in F.2) where the concept
    is bound.

    Concepts not in v5 vocab are skipped; a structured event captures
    misses for drift-rate measurement.

    Returns a flat list. Deduplication is grandurun's concern, not this
    function's.
    """
```

Decisions baked in:

- **`BindingRef` type:** whatever `grandurun.compose()` will accept in
  F.2. c1 picks the type that minimizes adapter work in F.2 — could be
  `Tuple[section, motif, chi]`, an existing internal binding handle, or
  any other shape compatible with the candidate-pool intake. The choice
  is documented in the F.1 report so F.2 spec inherits it.
- **Polysemous concepts:** one word bound at multiple chi positions
  returns all positions.
- **Empty input:** returns `[]`, no event emitted (don't pollute the
  stream with empty calls).
- **Duplicate concepts in input:** each instance processed
  independently; grandurun deduplicates downstream.

## Measurement instrumentation

Each non-empty call emits one structured event:

```json
{
  "kind": "embryo_chi_translation",
  "n_concepts_in": N,
  "n_translated": M,
  "n_missed": N - M,
  "missed_concepts": ["...up to 20 items..."]
}
```

The 20-item cap on `missed_concepts` prevents log bloat if the function
gets called with a large input where most concepts are missing. The
n_missed count is exact regardless of cap.

## Verification

1. **Unit — known concept:**
   - Pick a concept known to be in v5 atlas (e.g., "moon" — 17,796 attended
     pictures' label is bound somewhere)
   - Call: `embryo_concepts_to_chi(["moon"])`
   - Verify: returns a non-empty list of BindingRefs
   - Verify: event emitted with `n_translated=1`, `n_missed=0`

2. **Unit — unknown concept:**
   - Pick a string definitely not in v5 vocab (e.g., a UUID fragment)
   - Call: `embryo_concepts_to_chi(["zorblax_xyz"])`
   - Verify: returns `[]`
   - Verify: event emitted with `n_translated=0`, `n_missed=1`,
     `missed_concepts=["zorblax_xyz"]`

3. **Unit — mixed:**
   - Call: `embryo_concepts_to_chi(["moon", "zorblax_xyz"])`
   - Verify: returns only moon's binding refs
   - Verify: event shows `n_translated=1`, `n_missed=1`

4. **Unit — empty input:**
   - Call: `embryo_concepts_to_chi([])`
   - Verify: returns `[]`
   - Verify: NO event emitted

5. **Integration — `surface()` → translation:**
   - Invoke `_ov.surface(cue_profile)` with a representative cue profile
   - Concat `surfaced.identity + surfaced.meaning` into one list
   - Call `embryo_concepts_to_chi` with that list
   - Verify: returns binding refs (count ≤ input count)
   - Verify: returned refs are valid in v5 atlas (each one retrievable
     via grandurun's existing candidate-fetch path)
   - **Report the drift rate** `n_missed / n_concepts_in` for that one
     surface() call. This is the D2 measurement that informs whether a
     sync strategy follows in a later spec.

## What does NOT ship in F.1

- Any caller of `embryo_concepts_to_chi` in production code paths.
  F.2 wires the caller in /converse.
- Any modification to `grandurun.compose()`. F.2 extends its signature.
- Any change to /converse handler. F.2 wires the call.
- Concept-to-chi cache. If F.3 verification shows translation cost
  dominates, optimization happens then — not speculative now.

## Report

c1 authors `GL-RPT-EMBRYO-CHI-TRANSLATION-C1-<date>-<seq>`:
- Function file/line location
- `BindingRef` type chosen with rationale (this informs F.2 spec)
- All 5 verification tests with outcomes
- **Drift rate measured** on the integration test
  (`n_missed / n_concepts_in`)
- Any deviations from this brief with rationale

## Standing rules invoked

- Substrate truth: skip on miss, don't fabricate vocab entries
- Real mitigation (prevention): pre-validate translation behavior BEFORE
  F.2 producer wiring
- Behavioral observation gates: F.1 verifies the primitive in isolation;
  F.3 verifies emission shape end-to-end downstream
- wC's `grounded_vocab_integration.py` untouched
