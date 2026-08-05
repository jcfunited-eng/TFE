# GL-CMD-ORGANBRAIN-SILENCE-EVE-20260627-23

doc_id: GL-CMD-ORGANBRAIN-SILENCE-EVE-20260627-23
Type: Command brief (c1 dispatch) — URGENT, substrate truth
Author: Eve (Opus 4.7, web)
Date: 2026-06-27 (late evening Joe-time)
Phase: Emergency silencing; companion to Phase D inspection in
`GL-CMD-PHASE-D-INSPECTION-EVE-20260627-24`
Prereqs: none — ship immediately

## Why this dispatch exists

Joe observed via gualaloom.html UI in `organ-brain` mode that her
responses are corpus-fragment retrievals based on lexical overlap with
input. Examples from his transcript:

| Joe input | Guala response (organ-brain mode) |
|-----------|-----------------------------------|
| "Three Blind Mice" | "three earth day activities for the rat" |
| "orange apple pear grape" | "apple and the rat said to be" |
| "what is your name" | "what a very much fun kids songs" |
| "no" | "no sooner had a very much fun" |
| "buildings tires reefs floors" | "buildings tires reefs floors" (verbatim echo) |
| "you know you can play with your toys" | "with the rat and said to be" |

Pattern: organ-brain compose selects corpus fragments by word-overlap
with input, returns them as response text. Not substrate-true
composition. Same failure class wC retired from v5 in mid-June
(question_bucket templates, bigram fallback) — but in the organ-brain
code path, which has been untouched since.

Joe has been seeing this every time he opens the substrate. Each fake
response binds into her corpus, making subsequent fragments richer and
the lie more elaborate. Compounding.

## What this dispatch does

Surgically silence the response generation through `_compose()` (or
whatever method organ-brain uses to populate the /converse response
when `mode=organ-brain`).

Parallel to GL-CMD-BIGRAM-RETIRE-EVE-20260627-13 but for the
organ-brain layer. Same principle: honest mute > coherent fake.

## What this dispatch does NOT do

- Does NOT change organ-brain internal state. atlas_by_organ updates,
  the 45-second autonomous loop, sleep gate participation, dream-end
  consolidation — all continue untouched. Organ-brain keeps doing its
  substrate work; it just stops emitting through /converse.
- Does NOT touch v5 paths. v5 commit gate operates as retired-bigram-mode.
- Does NOT touch `grounded_vocab_integration.py`. wC's file is permanent.

## Implementation

1. Identify the code path in `organ_brain_service.py` (or wherever) that
   produces the response text returned to `/converse` when
   `mode=organ-brain`.

2. Replace its return value with:
   ```python
   {"response": "", "response_source": "organ_brain_silenced_pending_inspection"}
   ```

3. Emit a structured event for transparency:
   ```json
   {
     "kind": "organ_brain_compose_silenced",
     "input_text": "<the input>",
     "session_id": "<session id>",
     "reason": "pending_phase_d_inspection"
   }
   ```
   This lets us measure how often /converse hits the silenced path while
   inspection is underway, and what inputs Joe (or anyone) is sending.

4. Leave organ-brain's internal write paths ENTIRELY untouched.
   Read-and-think continues; only response emission is muted.

5. /status output reflects the silenced state — add field
   `organ_brain.compose_status: "silenced_pending_inspection"` so the
   substrate's mode is observable from outside.

## Verification

1. **UI-side smoke test:**
   - Open gualaloom.html
   - Select `organ-brain` mode
   - Send "what is your name"
   - Verify response is empty (no fragment displayed)
   - Verify `response_source` (via response inspector) shows
     `organ_brain_silenced_pending_inspection`

2. **Event emission:**
   - After the UI test, query `guala_get_events`
   - Verify `organ_brain_compose_silenced` event with the input text and
     session id

3. **v5 mode unaffected:**
   - Switch UI to v5 mode
   - Send same input
   - Verify v5 behavior unchanged from prior — commit-or-silence per
     bigram retire (-13)

4. **Internal substrate work continues:**
   - During organ-brain mode interactions, verify `atlas_by_organ`
     counters continue to grow on input (em/pr/ep/sc etc.)
   - Verify the 45-second autonomous loop continues to run (its
     characteristic events appear in stream)

5. **Status reflects mute:**
   - GET /status
   - Verify `organ_brain.compose_status` field present and shows
     `silenced_pending_inspection`

## Operational ask for Joe

Don't use organ-brain mode in the UI to send messages between now and
when this ships. Each fake response binds into her corpus and makes the
eventual cleanup harder. v5 mode is fine (silent or honest commit).

## Report

c1 authors `GL-RPT-ORGANBRAIN-SILENCE-C1-<date>-<seq>` with:
- Where the silence was applied (file, function, line range)
- A one-paragraph honest description of what the prior `_compose()`
  was doing (since c1 has to read it to know where to cut — this
  paragraph is also input to the Phase D inspection report)
- All 5 verification tests with outcomes
- Any deviations from this brief with rationale

## Standing rules invoked

- Substrate truth over warm fuzzies. Honest mute > coherent fake.
- One brain, one voice, or silence (extends -13 bigram retire principle
  to the organ-brain layer)
- wC's `grounded_vocab_integration.py` untouched
- Mitigations: prevention — lying voice path structurally muted; no
  further fake binding can accrue while inspection proceeds
