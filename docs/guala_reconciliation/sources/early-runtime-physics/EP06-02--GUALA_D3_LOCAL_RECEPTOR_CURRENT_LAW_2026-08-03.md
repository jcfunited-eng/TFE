# Guala D3 Local Receptor Current Law — 2026-08-03

## Status

The exact local current relation is accepted as a receiving-physics primitive.
It is not yet native, runtime-reachable, deployed, a receptor-binding law, a
membrane-voltage transition, a Krimelack coupling law, or D3 completion.

## Architecture honesty gate

1. **Requested architecture:** a synaptic effect derived from the receiving
   neuron's local biology and fluid state rather than stored polarity, learned
   weight, or endpoint lookup.
2. **Current code reality:** production D2 has no synaptic receiving transition.
3. **Conflict with requested architecture:** yes.
4. **Mechanisms not extended:** the rejected phase-node sign equation, stored
   excitatory/inhibitory flags, guessed conductances, fitted Guala rates, float
   membrane placeholders, global summation, or Python body authority.
5. **Single exact next item:** derive one exact membrane-state transition from
   current, capacitance, and a mounted physical interval.
6. **Full field or reduced approximation:** this law does not evaluate DSF.
   Frozen L0-L4 and every explicit field remain upstream and unchanged.
7. **Declared loss:** receptor current is not a projection of DSF and does not
   replace a neuronal fractal.

## Local physical law

For one reached receptor population with exact open conductance `g`, receiving
membrane potential `V`, and local reversal potential `E`, outward-positive
current is:

```text
I = g * (V - E)
```

The implementation uses exact rational arithmetic. It stores no polarity. At
`V = E`, current is exactly zero. With the same receptor and conductance, the
current changes direction when the receiving membrane crosses its reversal
potential. Reversal potential belongs to the receiving ion state; it is not a
constant semantic property of a transmitter.

This is the local relation used in the kinetic membrane framework reported by
Destexhe, Mainen, and Sejnowski, following the conductance/reversal structure of
Hodgkin and Huxley:

- https://doi.org/10.1162/neco.1994.6.1.14
- https://doi.org/10.1113/jphysiol.1952.sp004764

Experimental chloride-gradient results additionally demonstrate that changing
receiving ion state changes GABA-mediated reversal and response:

- https://doi.org/10.1152/jn.2001.85.6.2381

## Boundary with the fluid manager

The conservative fluid manager moves exact typed quantity into a named local
compartment. Separate receptor kinetics must convert local transmitter and
receptor state into `g`; separate ion and body physics must determine `E`.
This primitive then resolves `I`. No chemical directly means excitation,
inhibition, reward, mood, thought, or identity.

## Pure-physics audit

The transition is one exact multiplication and subtraction for one reached
receptor. It imports only `dataclass` and `Fraction`; it has no loop, recursion,
owner, lock, database, hash, receipt, validation machinery, persistence,
history, or infrastructure call.

## Unresolved physics

- receptor binding, opening, closing, and desensitization kinetics;
- ion concentrations and exact reversal-potential derivation;
- membrane capacitance and physical interval;
- current integration across exact same-compartment receptor populations;
- current-to-Krimelack phase transduction;
- energy, channel, and transmitter recovery paths;
- native atomic integration and production cutover.
