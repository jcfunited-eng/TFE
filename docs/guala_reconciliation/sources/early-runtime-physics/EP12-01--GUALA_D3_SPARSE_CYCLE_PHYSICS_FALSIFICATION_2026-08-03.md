# Guala D3 Sparse-Cycle Physics Falsification — 2026-08-03

## Status

The one-, three-, and four-neuron unpowered-cycle cases quiesce under the local
component and terminal candidates. This is supporting evidence, not a complete
D3 law, architecture promotion, native implementation, or deployment.

## Architecture honesty gate

1. **Requested architecture:** sparse recurrent neuronal coupling with locally
   supplied activity, bounded causal work, and no free fan-out amplification.
2. **Current code reality:** production D2 has no persistent Krimelack coupling,
   synaptic resource, delayed neuronal arrival, or D3 recurrence.
3. **Conflict with requested architecture:** yes. The tested directed cycles
   have one incoming and one outgoing edge per neuron and do not solve fan-in.
4. **Mechanisms not extended:** dense matrices, rings as production anatomy,
   learned weights, stored polarity, owner graphs, locks, databases, authority
   recursion, cumulative winding, global polling, timers, and frequency caps.
5. **Single exact next item:** determine whether coincident local arrivals can
   combine through physical target locality without becoming an untyped sum.
6. **Full field or reduced approximation:** no DSF evaluation occurs in this
   model. Full typed DSF remains authoritative upstream.
7. **Declared loss:** local phase steps and momentary windings do not reproduce
   the full field and are not represented as doing so.

## Test arrangement

Every neuron begins with two local sub-winding steps and one available firing
expenditure. Every directed terminal begins with one available local release.
One initial local step reaches neuron zero. No channel recovery, energy supply,
or transmitter recovery is supplied after genesis.

Only the reached neuron transitions. A winding reaches only that neuron's one
outgoing terminal. A successful release becomes the next reached neuron's local
step. No test runner polls all neurons or all possible edges.

## Results

```text
configuration        windings  releases  neuron calls  terminal calls  outcome
one-neuron self-loop      1        1           2              1         quiescent
three-neuron cycle        3        3           4              3         quiescent
four-neuron cycle         4        4           5              4         quiescent
```

The final arrival returns to a neuron whose phase was reset by its earlier
winding. One step is sub-threshold, so no new winding or release occurs. Every
used neuron has expended its local firing availability and every used terminal
has expended its local transmitter availability.

A separate four-terminal fan-out test produces four first releases because four
physical terminals each begin with one local resource. Re-presenting the same
source winding produces zero second releases and four depleted attempts. Fan-out
therefore consumes `O(reached terminals)` local supply; the source event does not
create an unaccounted reusable release quantity.

The combined relevant suite passes 31/31 tests.

## Pure-physics audit

No new cognitive transition was added for this test. The runner calls only the
previously audited 87-line component transition and 70-line terminal transition.
It retains test observations outside organism state. For an `N`-neuron directed
cycle its exact causal work is:

```text
component transitions = N + 1
terminal transitions  = N
```

This work is derived from the reached path, not total possible neuron count,
history, authority objects, or database rows.

## What remains unresolved

- The directed cycle is a falsification fixture, not proposed organism anatomy.
- Endpoint phase-node separation as the complete local synaptic orientation law
  remains a hypothesis.
- The test does not combine two or more simultaneous arrivals at one target.
- It does not prove inhibition, excitation, transmitter quantity, fluid recovery,
  recurrent activity with explicit energy supply, topology growth, cold restore,
  native byte bounds, or mature mosaic recurrence.
- Stored genesis resources explain the finite path; no claim is made that those
  resources regenerate themselves.

The next candidate must solve fan-in at one physical target without summing
heterogeneous DSF positions, inventing a scalar weight, or adding validation and
custody machinery to the physics path.
