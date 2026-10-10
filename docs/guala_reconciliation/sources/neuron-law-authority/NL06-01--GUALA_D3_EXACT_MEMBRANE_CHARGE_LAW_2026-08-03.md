# Guala D3 Exact Membrane Charge Law — 2026-08-03

## Status

The exact membrane charge relation is accepted as a local physical primitive.
It is not yet native, runtime-reachable, deployed, a complete membrane model,
a Krimelack transduction law, or D3 completion.

## Architecture honesty gate

1. **Requested architecture:** receiving-neuron state changes through local
   physical current, body/fluid condition, and exact causal time.
2. **Current code reality:** production D2 has no membrane charge transition.
3. **Conflict with requested architecture:** yes.
4. **Mechanisms not extended:** native float membrane/energy placeholders,
   generation timers, thresholds, clamps, guessed time constants, stored
   polarity, global polling, or Python body authority.
5. **Single exact next item:** derive the membrane-to-Krimelack phase
   transduction and its units without a fitted or arbitrary coefficient.
6. **Full field or reduced approximation:** this transition does not evaluate
   DSF. Frozen L0-L4 and every explicit DSF field remain unchanged upstream.
7. **Declared loss:** membrane charge is not a projection of DSF and does not
   replace the neuronal fractal.

## Physical law

For outward-positive local current `I`, exact physical interval `Δt`, mounted
membrane capacitance `C`, prior charge `Q`, and potential `V`:

```text
ΔQ = -I * Δt
V_next = V + ΔQ / C
C * (V_next - V) = ΔQ
```

The implementation uses exact rational arithmetic. Capacitance and interval are
explicit inputs, not hidden constants. It performs no thresholding, clamping,
decay, recovery, or phase conversion. Zero current or zero interval is exact
quiescence.

The charge/capacitance relationship is the membrane balance used by the
Hodgkin-Huxley framework:

- https://doi.org/10.1113/jphysiol.1952.sp004764

## Boundary with receptor and fluid physics

The current primitive supplies `I` from local open conductance and reversal
state. The fluid manager changes typed compartment quantities that can later
change receptor, ion, metabolic, and recovery state. This charge transition
advances only the reached membrane compartment over its admitted physical
interval.

## Pure-physics audit

The transition is exact subtraction, multiplication, and division for one
reached compartment. It imports only `dataclass` and `Fraction`; it has no loop,
recursion, owner, lock, database, hash, receipt, validator, persistence,
history, timer, or infrastructure call.

## Unresolved physics

- mounted virtual-organism capacitance units and anatomy;
- ion concentrations and reversal-potential evolution;
- receptor opening, closing, and desensitization kinetics;
- combination of simultaneous same-compartment currents;
- membrane-potential-to-Krimelack phase/frequency transduction;
- local channel, energy, and terminal recovery;
- native atomic integration and production cutover.
