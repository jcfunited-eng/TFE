# Primitive Direct Field-State Calculation Draft

Requested architecture:
- primitive decision should come from a direct field-state calculation
- no replacement signal
- no replacement gate
- no static-style threshold ladder pretending to be physics

Current code reality:
- `web/src/lib/uf-dynamic-decision.ts` still uses reduced field-evolution terms plus gates
- that is still not the direct joint-state rule

Conflict with requested architecture:
- yes

What exact mechanism or files will not be extended:
- `web/src/lib/uf-snapshot.ts`
- `pscf_policy_runtime.json`
- `policy_horizon_overrides.json`
- `l5_policy_learning_pipeline.py`
- `backups/pscf-policy-anomaly-watch-20260218T142043Z.json`

The single exact next item:
- define one direct field-state calculation draft only

Am I evaluating the full field or a reduced approximation?
- a reduced approximation

If reduced, what exact field structure is being lost?
- hard blockers
- soft blockers
- strategy class
- horizon governance
- `IS_h`
- epoch / sector / company adjustments

## Core Idea

The primitive should not ask:
- is one term positive?
- is one score above a line?

The primitive should ask:
- what field-state is implied by the joint configuration of
  - `D_k`
  - `M_k`
  - `R_rev_k`
  - `U_star_k`
  - `C_k`
  - `P_k`
  - `B_k`
  - `S_UF`
  - `R_UF`

## Direct State Variables

Use the row fields to form only 3 direct state quantities:

1. `continuation_state`

Meaning:
- whether directional persistence is being sustained by the field

Draft calculation:

```text
continuation_state =
  D_k * (
    S_UF
    + 0.7 * R_UF
    + 0.6 * M_k
    + 0.3 * B_k
    - 0.4 * R_rev_k
  )
```

2. `instability_state`

Meaning:
- whether uncertainty / reversal / pressure / complexity are dominating the field

Draft calculation:

```text
instability_state =
  U_star_k
  + 0.8 * R_rev_k
  + 0.5 * P_k
  + 0.25 * C_k
  - 0.2 * B_k
```

3. `admissibility_state`

Meaning:
- whether stillness / weak direction is structurally admissible rather than collapsing

Draft calculation:

```text
admissibility_state =
  S_UF
  + 0.8 * R_UF
  - U_star_k
  - 0.5 * P_k
  + 0.3 * B_k
```

## Primitive Reading Rule

The primitive decision should come from the ordering of those states, not from one gate:

```text
if continuation_state is dominant over instability_state
and admissibility_state is not broken:
  Accumulate

elif instability_state is dominant over both
continuation_state and admissibility_state:
  Avoid

else:
  Hold
```

## Why This Is Closer To The Requested Architecture

- it uses joint field interaction
- it does not elevate one shorthand term into decision authority
- it does not ask one directional-sign question first
- it allows `Accumulate` to exist even when median `D_k` is neutral, if the field-state is continuation-favoring overall

## Honest Boundary

This draft still does not prove:
- the exact coefficients
- the exact nonlinear form
- the exact final ordering rule
- the full governed L5 behavior

It is only the first explicit draft of a direct field-state primitive calculation.
