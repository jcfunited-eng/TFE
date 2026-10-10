# Guala D3 local receptor-current boundary

Date: 2026-08-04

Status: corrected physical boundary. Exact current arithmetic exists in an
isolated candidate; biological receptor gating and production mounting remain
unavailable.

## Architecture honesty gate

1. **Requested architecture:** a calibrated local stimulus changes finite
   receptor conformation, which changes conductance and membrane charge.
2. **Current code reality:** exact current can be computed from an explicitly
   supplied conductance and reversal potential, but no measured receptor law
   derives the conductance from a live sensory event.
3. **Conflict:** yes until one named preparation supplies the complete reached
   finite-state gate and its physical inputs.
4. **Mechanisms not extended:** ensemble probability as literal state,
   fractional or rounded channels, selected saturation points, fitted fallback
   curves, normalized signals as current, stored polarity, semantic lookup,
   ML, or DSF-to-current conversion.
5. **Single exact next item:** determine an exact finite Type II vestibular
   channel-transition law or preserve an explicit unavailable boundary.
6. **DSF evaluation:** none; complete explicit L0-L4 remains unchanged.
7. **Declared loss:** receptor current does not replace or summarize a neuronal
   fractal.

## Admissible local relation

For integer conformational populations `n_i`, declared open conformations `O`,
unit conductance `gamma`, membrane potential `V`, and local reversal potential
`E`:

```text
N_open = sum(n_i for i in O)
g_open = N_open * gamma
I_out = g_open * (V - E)
```

At `V = E`, current is exactly zero. Crossing `E` changes direction without a
stored excitatory/inhibitory flag. Multi-ion pores require an ion-specific
electrodiffusion and material law rather than an ohmic shortcut.

A biological transition must move integer channel populations between named
conformations through reached physical or biochemical events. A population
probability or Boltzmann curve is evidence about an ensemble, not enough by
itself to identify the finite successor in one deterministic organism.

## Fluid and organism boundary

The fluid mechanism must supply named local material, temperature, and
electrochemical state. The receptor law must supply physical stimulus,
geometry, conformational anatomy, and measured transition dynamics. Missing
values remain unavailable; no sense label, default coefficient, or saturation
value may substitute for them.

Biological membrane voltage uses charge and capacitance. Krimelack coupling is
a distinct unresolved neuronal relation. Neither current nor chemistry directly
means reward, mood, word, identity, excitation, or inhibition.
