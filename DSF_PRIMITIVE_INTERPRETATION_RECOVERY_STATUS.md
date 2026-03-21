# DSF Primitive Interpretation Recovery Status

Generated UTC: 2026-03-18T22:44:01Z
Workspace: `/workspaces/Tao_Financial_Engine`

## Scope

Only this is in scope:
- whether the latest active L5 primitive logic in `/workspaces/Tao_Financial_Engine/web/src/lib/uf-dynamic-decision.ts`
- can interpret L4 DSF output into:
  - `Accumulate`
  - `Hold`
  - `Avoid`

This is still a reduced approximation, not full governed L5.

Missing higher-layer structure:
- hard blockers
- soft blockers
- strategy class
- horizon governance
- `IS_h`
- epoch / sector / company adjustments

## Active Primitive Contract

The active primitive input contract is now limited to:
- `barCount`
- `S_UF`
- `R_UF`
- `D_k`
- `M_k`
- `R_rev_k`
- `U_star_k`
- `C_k`
- `P_k`
- `B_k`

Explicitly removed from the primitive contract:
- `stabilityScore`
- `regime`

## Clean Native Evaluation Lane

Separate clean primitive-only exporter:
- `/workspaces/Tao_Financial_Engine/real_world_cleaned_universe_l5_primitive_only_row_trace_export.py`

Clean native evaluator:
- `/workspaces/Tao_Financial_Engine/tools/run_uf_dynamic_decision_native_rowtrace_eval.py`

Shared legacy exporter that must not be extended for this work:
- `/workspaces/Tao_Financial_Engine/real_world_cleaned_universe_l5_row_trace_export.py`

## Latest Primitive Change

The latest primitive change did one exact thing:
- made the instability bundle conditional on surrounding support instead of letting `U_star`, `P`, and `C_k` always contribute at full fixed strength

This was implemented in:
- `/workspaces/Tao_Financial_Engine/web/src/lib/uf-dynamic-decision.ts`
- mirrored exactly in:
  - `/workspaces/Tao_Financial_Engine/tools/run_uf_dynamic_decision_native_rowtrace_eval.py`

Important truth:
- this is still a reduced approximation
- it is not a full dynamic field evaluator

## Verified Results After The Change

### 1. Anchor Pressure Test

Report:
- `/workspaces/Tao_Financial_Engine/backups/runtime/uf_dynamic_decision_pressure_test_report_20260318T223855Z.json`

Result:
- `totalCases = 9`
- `matchedExpectedCount = 9`
- `mismatchedExpectedCount = 0`
- `Accumulate = 3`
- `Hold = 3`
- `Avoid = 3`

Important truth:
- the change did not break the verified anchors

### 2. Clean Native Bounded Evaluation

Report:
- `/workspaces/Tao_Financial_Engine/backups/runtime/uf_dynamic_decision_native_rowtrace_eval_20260318T224401Z.json`

Run shape:
- single explicit horizon: `20` forward bars
- bounded native run: `50` symbols
- rows evaluated: `35,694`

Top line:
- `overall_accuracy = 37.0482%`

Oracle counts:
- `Accumulate = 15,444`
- `Hold = 3,700`
- `Avoid = 16,550`

Runtime counts:
- `Accumulate = 1,573`
- `Hold = 11,512`
- `Avoid = 22,609`

Per-class:
- `Accumulate`
  - precision: `45.8360%`
  - recall: `4.6685%`
  - f1: `0.0847`
- `Hold`
  - precision: `14.4805%`
  - recall: `45.0541%`
  - f1: `0.2192`
- `Avoid`
  - precision: `47.9278%`
  - recall: `65.4743%`
  - f1: `0.5534`

Confusion matrix:
- true `Accumulate`
  - predicted `Accumulate = 721`
  - predicted `Hold = 4,824`
  - predicted `Avoid = 9,899`
- true `Hold`
  - predicted `Accumulate = 159`
  - predicted `Hold = 1,667`
  - predicted `Avoid = 1,874`
- true `Avoid`
  - predicted `Accumulate = 693`
  - predicted `Hold = 5,021`
  - predicted `Avoid = 10,836`

## Comparison To The Prior Clean Native Run

Prior report:
- `/workspaces/Tao_Financial_Engine/backups/runtime/uf_dynamic_decision_native_rowtrace_eval_20260318T221024Z.json`

What changed:
- overall accuracy got worse:
  - from `39.8470%`
  - to `37.0482%`
- `Accumulate` precision / recall / f1 did not improve at all
- `Hold` recall improved:
  - from `30.4595%`
  - to `45.0541%`
- `Avoid` recall fell:
  - from `74.7734%`
  - to `65.4743%`

Exact confusion shift:
- true `Accumulate`
  - `Avoid -> Hold = 1,483`
  - `Avoid -> Accumulate = 0`
- true `Hold`
  - `Avoid -> Hold = 540`
  - `Avoid -> Accumulate = 0`
- true `Avoid`
  - `Avoid -> Hold = 1,539`
  - `Avoid -> Accumulate = 0`

Important truth:
- the conditional relation did not recover `Accumulate`
- it only moved many prior `Avoid` calls into `Hold`

## Honest Read

This change accomplished only this:
- it made the primitive less absolute about instability under support

But it did not accomplish this:
- it did not improve `Accumulate` recognition
- it did not improve `Accumulate` recall
- it did not improve overall bounded native accuracy

So the current honest status is:
- anchors remain intact
- the clean native lane remains weak
- the dominant problem is still failure to recognize real `Accumulate`
- the latest change mostly reclassified part of that failure from `Avoid` into `Hold`

## Exact Next Recommended Task

Do this next and nothing broader until it is answered:

- inspect `oracle=Accumulate, runtime=Hold` rows in the clean native report, because the latest change only shifted part of the dominant failure from `Avoid` into `Hold` and did not recover `Accumulate`
