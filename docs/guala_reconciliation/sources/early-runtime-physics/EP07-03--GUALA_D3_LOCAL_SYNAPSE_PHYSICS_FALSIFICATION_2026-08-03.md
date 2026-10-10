# Guala D3 Local-Synapse Physics Falsification — 2026-08-03

## Status

The isolated one-terminal candidate survived its local depletion and code-shape
tests. Its endpoint-phase geometry remains a hypothesis. It is not D3, not an
accepted `J_ij` law, and not deployed.

## Architecture honesty gate

1. **Requested architecture:** sparse, locality-governed neuronal coupling in
   which activity is physically supplied at each reached terminal and cannot be
   copied through free or unbounded fan-out.
2. **Current code reality:** production D2 has no synaptic state or arrival law.
   The one-component candidate exists only as committed falsification evidence.
3. **Conflict with requested architecture:** yes. One terminal cannot establish
   conservative recurrence, fan-out, fan-in, or mosaic formation.
4. **Mechanisms not extended:** owners, locks, databases, authority chains,
   learned weights, stored polarity, scalar DSF maps, legacy ring/clique wiring,
   fixed timers, frequency caps, and cumulative event histories.
5. **Single exact next item:** apply locally powered terminals to a synchronous
   three-neuron directed cycle, then falsify the same law on four neurons.
6. **Full field or reduced approximation:** this model does not evaluate DSF.
   Full typed DSF authority remains upstream of neuronal locality.
7. **Declared loss:** a momentary source winding and one target phase step are
   compact physical test events, not the full field. No DSF coordinate is
   replaced by them.

## Candidate law

A terminal retains one physical quantity: whether one local transmitter release
is available. Its anatomy retains its source and target Krimelack phase-node
locations. The centered triadic separation of those endpoints determines the
target orientation:

```text
separation = (target_node - source_node) mod 3
local orientation = 0, +1, or -1 for separation 0, 1, or 2
target phase step = source winding * local orientation
```

A source winding releases only when local transmitter is available. The release
consumes that availability. A later explicit local fluid recovery can restore
one release; repeated recovery saturates rather than accumulating a count.

This follows the biological fan-out principle being tested: each physical axon
terminal has its own locally maintained release resource. A source event does
not create free transmission quantity; each reached terminal expends its own
physical supply.

## Pure-physics audit

The implementation is 70 lines and imports only `dataclass`. Its transition
function contains no loop, recursion, exception path, validator, external call,
owner, lock, database, hash, receipt, authority object, persistence, or history.
The only calls in the transition are construction of its physical successor and
momentary result.

Runtime profiling records exactly one physics call for each reached terminal:

```text
1,000 terminal events  -> 1,000 transition calls
10,000 terminal events -> 10,000 transition calls
```

The candidate passes 8/8 focused properties and 27/27 together with the local
component and rejected cumulative-phase evidence. In the longest local test,
100,000 repeated source events produce one release and 99,999 truthfully blocked
attempts without recovery or state growth.

## Unresolved physics

- The equation that makes endpoint phase-node separation sufficient to govern a
  biological synaptic effect is not yet canonical. Receptor kind, dendritic
  compartment, and fluid chemistry may require additional physical locality.
- Same-node release currently consumes transmitter and produces zero target
  phase displacement. This is truthful in the candidate but not yet established
  as the organism's physical law.
- Boolean transmitter availability is the smallest depletion test, not a final
  vesicle quantity, concentration, or recovery-rate law.
- No fluid/body mechanism yet earns the recovery event.
- No synchronous multi-neuron run, fan-in combination, recurrence, inhibition,
  topology growth, native resource proof, or cold restoration has passed.

The endpoint-locality hypothesis must therefore be tested in three- and
four-neuron configurations before any promotion decision.
