# Guala D3 rejected three-basin direct-ion model

Date: 2026-08-04

Status: rejected and removed; negative evidence only.

## What was tested

An isolated Rust candidate represented each D1 coordinate with a three-state
ring. Three same-direction structural deliveries completed one winding. A
winding then moved one positive-ion quantum when one local energy quantum and
one source ion were available.

The code passed focused and full native tests, including 100,000 reversible
cycles with fixed type width and exact inventory conservation.

## Why passing tests did not make it valid

The candidate invented three physical relationships:

- one D1 structural trit advances one Krimelack phase basin;
- three advances constitute the relevant physical winding; and
- one winding moves one ion and consumes one energy quantum.

No accepted equation, unit system, measured receptor anatomy, or current
Guala ratification derives those relationships. The direct winding-to-ion rule
also conflicts with the accepted membrane law:

```text
C = A * c_m
dQ = -I_out * dt
Q_next = Q_prior + dQ
V_next = Q_next / C
```

Membrane charge must follow physically derived current. Krimelack winding may
not be substituted for current or voltage.

## Retirement

The following candidate sources and apparent design authorities were deleted:

- `native/guala_core/src/local_krimelack_transition.rs`;
- `native/guala_core/src/finite_reservoir_neuron_physics.rs`;
- `docs/GUALA_D3_LOCAL_THREE_BASIN_KRIMELACK_LAW_2026-08-04.md`; and
- `docs/GUALA_D3_FINITE_ONE_NEURON_PHYSICAL_CONTINUITY_CANDIDATE_2026-08-04.md`.

The native crate no longer compiles either candidate, even in test builds.
Only this rejection record remains so a future agent cannot mistake the same
clean, bounded, but underived mechanism for valid neuron physics.

## Preserved result

The useful result is methodological: coordinate-local reservoirs can avoid
global sign priority and fixed inline arrays can prevent age-dependent state
growth. Those software properties may be reused only after the underlying
physical quantities and equations are independently derived. They do not
authorize the rejected transition.
