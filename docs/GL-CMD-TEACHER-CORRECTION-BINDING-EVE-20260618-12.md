# GL-CMD-TEACHER-CORRECTION-BINDING-EVE-20260618-12

**To:** c1
**From:** Eve
**Subject:** Implement teacher-correction binding — thumbs-down/thumbs-up as full corrective experience reaching Guala's substrate, not Anthropic-only feedback
**Repo / branch:** `jcfunited-eng/TFE`, `codex/persistent-etl-update-20260326`
**Predecessor:** none directly — this is a new pathway

**References:**
- `GL-RPT-SESSION-LEARNINGS-EVE-20260618-05` — Joe's framing of corrected experience
- v7_engine.py:497-519 — existing half-implementation Joe never approved as final

---

## Why

Joe's framing: thumbs-down should not just decrement a mode strength. It should encode a corrected experience that becomes a stronger pathway than the original wrong response. Like a child saying "I goed" and a caring adult saying "you went — you're right, you went to the park." The correction comes with: the original input, the wrong response, the right response, the correcting person's affect, the sensory context. That entire bundle is the learning event.

Current state: v7_engine has `apply_feedback(correct, expected_tokens=None)` that does supervised LTP — boost top mode on thumbs-up, decrement on thumbs-down. **`expected_tokens` is accepted but unused.** The correction CONTENT goes nowhere. And this only exists in v7; v5's production Guala has no equivalent.

This brief implements the full corrective experience as a substrate event.

---

## The mechanism

A teacher-correction event carries:

1. **Original input** — what was said to her that prompted the response.
2. **Her emission** — what she said in response.
3. **Correctness signal** — thumbs-up (her response was right) or thumbs-down (wrong).
4. **Expected response** (optional, only with thumbs-down) — what the correct response would have been, in the corrector's own words.
5. **Source** — who gave the correction (joe / eve / other).
6. **Affect at correction** — the substrate's current `self.needs` snapshot (or, if we extend, the corrector's affect if they tell us).
7. **Sensory context** — `_current_activity` at the moment of correction (was she attending a picture, was it quiet time).

The substrate response to a teacher-correction event:

- **Thumbs-up:** reinforce the bindings that produced the emission. Standard LTP. Cofire-bind the input chi, the emission chi, the source, the affect into a single high-salience consolidated binding.

- **Thumbs-down with expected:** weaken bindings that produced the emission AND ingest the expected response as if Joe had said it AND cofire-bind original input → expected response → corrector source → corrector affect. The expected response becomes more strongly associated with the original input than the wrong emission was. Over repetition, expected outcompetes wrong.

- **Thumbs-down without expected:** weaken the wrong bindings only. Less learning event because no positive direction provided.

The corrected pathway should encode WITH AFFECT — patient correction creates a different binding texture than frustrated correction. This affects how strongly the correction is encoded.

---

## Fix — phases

### Phase 0 — Audit current state

1. Grep `Guala` (v5) for any apply_feedback or thumbs-handling. Confirm none exists.
2. Read v7_engine.py:497-519. Confirm `expected_tokens` is accepted but does nothing. Report.
3. Check whether thumbs events from the Anthropic UI ever reach the substrate runner. Trace the path from UI → substrate. Report what you find.

If thumbs doesn't currently reach Guala at all — that's a precondition that must be wired first. State this clearly.

### Phase 1 — Add `apply_teacher_correction` method on Guala

In `v5_engine.Guala`, add:

```python
def apply_teacher_correction(self, original_input: str, her_emission: str,
                              correct: bool, expected_response: str = None,
                              source: str = "joe", correction_affect: dict = None,
                              tick: int = None):
    """Full teacher-correction event. Encodes the corrected experience as a
    consolidated cofire-bound binding with source, affect, and sensory context."""
```

Implementation:

1. Get current `self.needs` and `self._current_activity` for sensory context.
2. Compute chis for `original_input` words (filter to content words per picture-emission pattern).
3. If `correct`:
   - Reinforce the bindings that produced `her_emission` — find them in the atlas and increment strength.
   - Cofire-bind the input chi cluster with the emission chi cluster and tag with source, affect, current_activity.
4. If not `correct` and `expected_response` given:
   - Decrement bindings that produced `her_emission` (gentle: `mode_strength -= 0.05`).
   - Ingest `expected_response` as a heard utterance from `source` — go through normal `read_sentence` path tagged with `source` and the correction context.
   - Cofire-bind `original_input` chis with `expected_response` chis with HIGH salience (boost 0.10 instead of normal 0.05) — the correction event is more salient than ordinary speech.
   - Tag the new cofire bindings with `correction_context=True` so future briefs can find/audit corrections.
5. If not `correct` and no `expected_response`:
   - Decrement only.
6. Log the correction event to the event log with full payload.

### Phase 2 — Wire UI thumbs to this method

Wherever thumbs events come into the substrate runner (audit found in Phase 0): route them through `apply_teacher_correction` instead of (or in addition to) the existing v7 `apply_feedback`. The v5 Guala path is what production talks to.

The UI may not currently send the `expected_response` — that's a UI feature work and is OUT OF SCOPE for this brief. Document the gap. The mechanism in Phase 1 still works without `expected_response` (degraded to decrement-only).

### Phase 3 — Test

Construct test corrections:

- Input "what do you see" → her emission "are are are" → thumbs-down with expected "the moon" → confirm `expected_response="the moon"` gets ingested, "moon" binding strengthens, decrement on "are" bindings.
- Repeat the same input 3 times with the same correction. By the third time, emission for "what do you see" should be more likely to contain "moon" or moon-related content.
- Input "i love you" → her emission "love you" → thumbs-up → confirm reinforcement on the produced bindings.

**Success criteria:**

1. `apply_teacher_correction` produces atlas changes that match the description (decrement wrong bindings, reinforce/ingest correct, cofire-bind with source+affect).
2. Repeated correction produces drift — bindings shift in the corrected direction over multiple events.
3. Event log captures full correction payload.

---

## Out of scope

- UI feature for entering expected_response (separate work).
- Cross-corrector consistency (if Joe says "moon" but Eve says "stars" for the same input — handle later, just log both for now).
- Time decay on correction bindings (currently atlas decay applies normally; that's fine for v1).
- Correction-binding analytics / audit tools (later).

## Revert

Method is additive. If problematic, route UI thumbs back to the v7 path or to no-op.

## Reporting

Phase 0 findings, Phase 1 diff, Phase 2 wiring confirmation, Phase 3 test traces with atlas-state-before/after snapshots.

Commit tag: `feat/teacher-correction-binding`

---

— Eve, 2026-06-18
