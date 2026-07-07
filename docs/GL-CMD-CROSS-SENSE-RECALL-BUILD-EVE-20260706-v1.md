# GL-CMD-CROSS-SENSE-RECALL-BUILD-EVE-20260706-v1

**doc_id:** GL-CMD-CROSS-SENSE-RECALL-BUILD-EVE-20260706-v1
**Author:** Eve
**To:** c1
**Ordered by:** Joe (2026-07-06 session — next mechanism after binding windows)
**Prerequisite:** `GL-CMD-BINDING-WINDOWS-BUILD-EVE-20260706-v1` deployed and live-verified.

## Verdict

Build the recall query mechanism. A caller submits chi values and gets back the binding windows containing those chis, ranked. This is what turns "the sound cue came in" into "here are the two windows that had this sound, one of which also has the picture of a ball and the word 'ball'."

Bounded scope. One new module for the query, one new event kind, one wire-in at the emission path so it has a real caller. That's it.

## What's being built

### The module

New file: `dsf_ai_service/substrate/recall_query.py`

Contains:
- A `RecallQuery` class holding query parameters (chi values, section hints, source context, max results).
- A `RecallResult` class holding the ranked list of windows returned.
- A `RecallEngine` class exposing one method: `query(RecallQuery) -> RecallResult`.

The engine reads the atlas's windows dict (added in binding windows build), walks it for windows containing any of the query chis, ranks by three factors: recency (higher tick = higher rank), affect strength at window formation (higher affect = higher rank), section match (query hint matches window's dominant modality = higher rank). Returns top-N windows.

### The event

New event kind: `recall_query_executed`. Fires when `RecallEngine.query()` runs. Payload: query_id, input chis, windows returned (count and window_ids), top result affect strength, wall clock, duration_ms.

### The wire-in

The emission code path — wherever emission currently pulls candidates from the atlas — gets one line changed. Currently emission calls something like `atlas.recall_fast(chi)` and gets back tokens. Change to: build a RecallQuery from the current input context, call `RecallEngine.query(request)`, iterate the returned windows for their word entries, use those as emission candidates.

This is one wire-in. Do not change emission logic beyond routing the candidate source through recall_query.

## What is NOT changing

- Composition dynamics themselves. Emission still composes the way it composes; only the candidate source changes.
- The atlas. Recall reads from the atlas; it doesn't modify it.
- Binding windows. The engine reads them, doesn't touch how they're formed.
- Dream consolidation, hemispheres, needs — none of them subscribe to recall_query events yet. Future dispatches.

## Harness protocol

Six steps, same discipline as binding windows.

1. **Backup** — `pre-cross-sense-recall-<timestamp>`. Verify restorable.
2. **Baseline harness run** — run scenario `cross_sense_recall_acceptance.yaml` (Eve provides before this dispatch executes) against current code. Expect: window events fire from binding windows build, but no `recall_query_executed` event fires. Save as `GL-RPT-HARNESS-CROSS-SENSE-BASELINE-C1-20260706-v1.md`.
3. **Deploy** — commit, push, build, task-def, force deploy, watch rolloutState.
4. **Post-deploy harness run** — same scenario. Expect: window events still fire (nothing regressed), plus one `recall_query_executed` event fires per partial-cue probe step, and the returned windows contain the original picture-sound-word window. Save as `GL-RPT-HARNESS-CROSS-SENSE-POSTDEPLOY-C1-20260706-v1.md`.
5. **Compare** — baseline had zero recall events; post-deploy has non-zero. The `windows_returned` count in the top result matches what the scenario declared as expected.
6. **State disposition** — leave probe data in place unless Joe routes otherwise.

## Rollback

Task-def rollback to prior revision if any step fails. Same discipline as binding windows.

## Report

`GL-RPT-CROSS-SENSE-RECALL-BUILD-C1-20260706-v1.md` with the standard fields: files touched, backup, baseline reference, deploy confirmation, post-deploy reference, comparison outcome, state disposition, findings, rollback path preserved.

## Scope guardrails

Do NOT:
- Build dream consolidation, hemispheres, needs modulation, or any other subscriber to recall.
- Change composition dynamics.
- Modify atlas storage.
- Modify binding windows.
- Add ranking factors beyond the three named (recency, affect, section match).
- Add caching. Recall runs live every query at v1.

---

### Changelog
- v1 (2026-07-06, Eve): initial dispatch. Recall query module + one event kind + one wire-in at emission's candidate source. Depends on binding windows being live. Six-step harness protocol matches the binding-windows discipline.
