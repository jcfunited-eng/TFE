# DSF Primitive Interpretation Recovery

Purpose:
- restore a readable primitive interpretation layer for DSF
- keep the primitive audit lane clean
- prevent flattening, helper-score drift, and transport fallback drift
- support primitive interpretation before full L5 governance is applied

Status:
- frozen primitive base

Honest current state:
- primitive tuning is complete for now
- the frozen primitive base is `DSF full-field sortable v3 rationalized`
- the primitive accuracy gate passed on the fixed-snapshot adjudicated sample
- the primitive still uses only the approved primitive field surface
- this lane still does not claim full governed L5
- future work now moves upward into governance overlays only

Scope:
- `/workspaces/Tao_Financial_Engine/real_world_cleaned_universe_l5_primitive_only_row_trace_export.py`
- `/workspaces/Tao_Financial_Engine/tools/run_uf_dynamic_decision_native_rowtrace_eval.py`
- `/workspaces/Tao_Financial_Engine/web/src/lib/uf-dynamic-decision.ts`
- `/workspaces/Tao_Financial_Engine/web/src/lib/uf-dynamic-decision-pressure-test.ts`
- `/workspaces/Tao_Financial_Engine/DSF_PRIMITIVE_FULL_FIELD_SORTABLE_V3_RATIONALIZED.md`

## 1. Scope Boundary

This document is:
- a primitive DSF interpretation note
- a diagnostic bridge for the approved primitive field surface
- a freeze record for the current primitive base
- a correction contract for future work above the primitive

This document is not:
- the canonical full L5 governance contract
- the CP-0 production decision-selection rule
- a claim that primitive DSF alone equals full production semantics
- a claim that full governed L5 is solved

## 2. Primitive Contract

Only these primitive inputs are in scope:
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

Nothing outside that field surface is allowed to govern the primitive decision in this lane.

## 3. Context Clarification

For this note:
- `D_k` through `B_k` are the primitive DSF core terms being interpreted
- `S_UF` and `R_UF` are L4 contextual enrichments used around that primitive interpretation

So this note should be read as:
- primitive DSF interpretation plus adjacent L4 context

not as:
- a strict redefinition of canonical DSF membership

## 4. Feed Contract

The primitive audit lane uses:
- provider daily bars
- raw unadjusted bars
- no clean-bar rewrite layer
- no bar-integrity sanitization layer

Reason:
- the lane is supposed to inspect primitive interpretation, not a later cleaned feed surface

## 5. Bridge Contract

The bridge extractor must:
- read `S_UF` and `R_UF` directly from level 4
- read `D_k`, `M_k`, `R_rev_k`, `U_star_k`, `C_k`, `P_k`, `B_k` directly from level 5
- fail closed if one of those primitive fields is missing

The bridge extractor must not:
- reconstruct primitive fields from transport positions
- inject helper signals
- use policy labels
- introduce out-of-scope primitive names

## 6. Pressure-Test Contract

The pressure-test bridge must:
- use the same explicit primitive field contract as the runtime
- refuse transport fallback
- keep null and blank field handling strict instead of coercing missing values into zero

Purpose of the 9 anchors:
- check that obvious primitive geometry is not broken
- not claim broad market correctness

Current frozen anchor state:
- `Accumulate` anchors: `3/3`
- `Hold` anchors: `3/3`
- `Avoid` anchors: `3/3`
- total: `9/9`

## 7. Canonical Primitive Meaning

`D_k`
- directional sign of resonance change
- tells whether motion is positive, neutral, or negative
- not enough by itself to authorize action

`M_k`
- local bend of the field
- helps tell whether motion is continuing or bending back
- should not be read as raw strength

`R_rev_k`
- reversal indicator
- marks a major geometry break
- should be treated as a first-class change in state, not a side penalty

`U_star_k`
- penalized uncertainty or instability
- tells whether the field remains trustworthy
- should be read against support and resonance, not alone

`C_k`
- structural complexity or conflict burden
- tells whether the structure is becoming conflict-heavy
- should not be used as a standalone veto

`P_k`
- directional discontinuity or persistence stress
- tells whether continuation is quiet, stressed, or sharply adverse
- should not dominate by itself

`B_k`
- accumulated structural carry
- tells whether the field is carrying stable potential or exhausting it
- should not be collapsed into a generic bonus or drag score

`S_UF`
- support floor
- separates weak structure from viable structure

`R_UF`
- resonance confirmation
- helps tell whether motion is structurally reinforced or only isolated

## 8. Geometry Questions

The primitive layer is supposed to answer these questions:
- is the field part of a coherent positive trajectory?
- is the field in viable stillness?
- is the field showing real collapse geometry?
- are multiple adverse terms agreeing, or is one noisy term being over-read?

These are geometry questions, not score questions.

## 9. Reading Order

Primitive reading order:
- support and resonance
- direction
- bend and reversal
- uncertainty and pressure
- carry
- then action

That order matters because:
- support and resonance tell whether a move is isolated or coherent
- direction tells which way the field is moving
- bend and reversal tell whether that move is continuing or breaking
- uncertainty, pressure, and carry tell whether the move is still admissible

## 10. Primitive Decision Meaning

Primitive interpretation should be read as:
- a lean toward `Accumulate`, `Hold`, or `Avoid` based on primitive geometry only

This is not the same thing as full runtime semantics.

Important distinction:
- primitive `Hold` means viable stillness or unresolved mixed geometry
- runtime `Hold` may also arise from broader governance behavior outside this primitive lane

Important distinction:
- primitive `Avoid` means collapse-leaning or inadmissible primitive geometry
- runtime `Avoid` may carry broader protective or governed no-add semantics beyond primitive collapse alone

## 11. Frozen Primitive Base

Status:
- frozen primitive base

Formula family:
- `DSF full-field sortable v3 rationalized`

Accuracy gate:
- passed

Accuracy proof:
- `rational_match = 90.52924791086329%`
- `conservative_but_plausible = 5.849582172701926%`
- `suspicious_mismatch = 3.6211699164345257%`
- `zero_basin_fallback = 0.0%`
- `plausible_total = 96.37883008356522%`

Proof scope:
- fixed-snapshot adjudicated sample of `502` rows
- `sample_split_global = 359`
- `sample_split_diagnostic = 143`
- `dropped_or_unscored_rows = 0`

Frozen candidate behavior:
- candidate counts matched fixed-snapshot universe totals exactly
- `Accumulate = 133`
- `Hold = 1132`
- `Avoid = 4148`
- anchors `9 / 9`

Mismatch concentration:
- top suspicious symbol: `AIZ` with `2`
- top miss directions:
- `Hold -> Accumulate = 30`
- `Avoid -> Hold = 11`

Primitive tuning stop rule:
- active

Next work:
- governance overlays only

## 12. Do Not Misstate

Do not claim:
- full governed L5 is solved
- full-universe hand-labeled truth proof exists
- primitive accuracy proof is the same thing as governed policy proof

Do not reopen primitive tuning unless:
- governance later reveals a concrete primitive failure surface

Do not describe this freeze as:
- production lock
- final governance completion
- proof that no future primitive failure can exist

## 13. Governance Move

Future work now moves upward into:
- hard blockers
- soft blockers
- strategy class
- horizon governance
- `IS_h`
- epoch / sector / company adjustments

The first governance stress bucket is:
- `Hold -> Accumulate = 30`

The first symbol-level review case is:
- `AIZ`

## 14. Honest Current Audit Target

This recovery lane has now proved:
- raw feed bars are used
- adjusted bars are not used
- integrity-filtered bars are not used
- the bridge uses only the approved primitive inputs
- the frozen primitive base clears the stated accuracy gate on the approved adjudicated sample

This recovery lane is not now tasked with:
- more primitive parameter search
- more primitive family search
- lab/runtime swap work
- governance overlay implementation
