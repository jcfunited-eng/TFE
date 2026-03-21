# DSF Primitive Interpretation Recovery

Purpose:
- restore a readable primitive interpretation layer for DSF
- keep the primitive audit lane clean
- prevent flattening, helper-score drift, and transport fallback drift
- support primitive interpretation before full L5 governance is applied

Status:
- active

Honest current state:
- the primitive lane contract is clean again
- the primitive audit gate is active and currently passing
- the primitive interpreter has recovered the 9 reference anchors again
- current 9-anchor pressure result is `9/9`
- the current runtime now implements the current closed-form primitive candidate from [DSF_PRIMITIVE_LAW_SKETCH.md](/workspaces/Tao_Financial_Engine/DSF_PRIMITIVE_LAW_SKETCH.md)
- the current runtime still treats weakest-reserve coverage as first-class and still avoids raw `U_star_k` as a standalone collapse penalty
- the latest bounded primitive replay against the previous candidate on the same frozen 5-symbol raw-feed sample is:
- old candidate: `Accumulate=86`, `Hold=1029`, `Avoid=2900`
- current candidate: `Accumulate=98`, `Hold=1017`, `Avoid=2900`
- net frozen transitions in that replay are:
- `Hold -> Accumulate = 12`
- `Avoid -> Avoid = 2900`
- no `Hold -> Avoid` increase in that bounded replay compare
- that bounded mix comes from a bounded raw-feed primitive diagnostic sample only
- that bounded mix is not a production policy target and not a claim about full governed L5 behavior
- the runtime is still `Avoid`-heavy on that bounded sample
- true interpretation accuracy is still unknown because this lane does not yet have an approved true DSF oracle

Scope:
- `/workspaces/Tao_Financial_Engine/real_world_cleaned_universe_l5_primitive_only_row_trace_export.py`
- `/workspaces/Tao_Financial_Engine/tools/run_uf_dynamic_decision_native_rowtrace_eval.py`
- `/workspaces/Tao_Financial_Engine/web/src/lib/uf-dynamic-decision.ts`
- `/workspaces/Tao_Financial_Engine/web/src/lib/uf-dynamic-decision-pressure-test.ts`

## 1. Scope Boundary

This document is:
- a primitive DSF interpretation note
- a diagnostic bridge for the approved primitive field surface
- a recovery note for missing semantic interpretation
- a correction contract for primitive-runtime rewrites in this lane

This document is not:
- the canonical full L5 governance contract
- the CP-0 production decision-selection rule
- the runtime policy-cell selection rule
- a claim that primitive DSF alone equals full production semantics

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

Current anchor state:
- `Accumulate` anchors: `3/3`
- `Hold` anchors: `3/3`
- `Avoid` anchors: `3/3`

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
- runtime `Hold` may also arise from guard-fail default or broader governance behavior outside this primitive lane

Important distinction:
- primitive `Avoid` means collapse-leaning or inadmissible primitive geometry
- runtime `Avoid` may carry broader protective or governed no-add semantics beyond primitive collapse alone

## 11. Current Rewrite Direction

The current rewrite direction is:
- make weakest-reserve coverage first-class
- keep trajectory relational
- keep reversal special
- keep conflict and persistence bounded
- let covered-side one-sided edge support decay faster once weakest-side coverage is genuinely positive
- implement the closed-form primitive candidate from [DSF_PRIMITIVE_LAW_SKETCH.md](/workspaces/Tao_Financial_Engine/DSF_PRIMITIVE_LAW_SKETCH.md)

The runtime now centers:
- weakest-reserve coverage
- one-sided versus double-sided coverage structure
- explicit forward, contested, and rupture geometry
- bounded load
- explicit basin tendencies with tie-to-`Hold`

It does not treat:
- raw `U_star_k` as a second independent collapse penalty

This is a primitive field reformulation, not a bucket dampener.

## 12. What The Primitive Must Not Do

Things the primitive must not do:
- `D_k > 0 => Accumulate`
- `S_UF low => Avoid`
- `U_star_k high => Avoid`
- `B_k negative => Hold`
- any single-field threshold ladder

Reason:
- the field is relational
- the same field value can appear in different surrounding geometry
- action must come from agreement or conflict across the field, not one parameter alone

## 13. Honest Use Of This Note

This note is useful for:
- explaining what the primitive field is seeing
- checking whether a primitive interpreter has drifted
- diagnosing whether one field is being over-read
- giving a readable vocabulary for continuation, stillness, and collapse

This note is not enough by itself for:
- full governed L5 semantics
- CP-0 production policy truth
- final production decision explanation

## 14. Honest Current Audit Target

This recovery lane is only supposed to prove:
- raw feed bars are used
- adjusted bars are not used
- integrity-filtered bars are not used
- the bridge uses only the approved primitive inputs
- the runtime uses only the approved primitive inputs
- the pressure-test bridge uses only the approved primitive inputs
- no out-of-scope primitive names have been introduced
- blocked and structurally incomplete runtime rows are handled correctly
