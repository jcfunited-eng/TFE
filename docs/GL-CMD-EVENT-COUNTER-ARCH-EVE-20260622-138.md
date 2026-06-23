# GL-CMD-EVENT-COUNTER-ARCH-EVE-20260622-138

**doc_id:** GL-CMD-EVENT-COUNTER-ARCH-EVE-20260622-138
**To:** c1
**From:** Eve
**Date:** 2026-06-22
**Re:** Event counter + bounded events buffer. Unblocks scaling tests.
**Status:** Operational fix. Independent of GL-CMD-139.

---

## Why

GL-CMD-137 V5 hit 24GB OOM at 100 concepts × 64 neurons. Cause: `krim.events` list accumulates unbounded across no-reset feeds. The cognition write path reads only `len(krim.events) - ev0` (a count, not the events themselves). We're paying O(N events × ~6KB Python dict overhead) to compute an integer.

Memory scales as O(neurons × deliveries × events_per_delivery). At Guala migration scale (~3,591 vocab × 64 neurons): ~750GB just for events. Won't fit.

The fix is two-part: separate the counter from the storage, and bound the storage. The events list IS consumed by production code paths (spike-triggering, atlas writes); we cannot just delete it. We can make it cheap.

## V1 — Audit before patching

**V1.a:** Identify every read site of `krim.events` in the codebase. Categorize each as:
- "Consumes events" (reads dicts, does something with their content)
- "Counts events" (only uses `len(krim.events)`)
- "Iterates recent events" (reads a sliding window)

Report file:line and category for each. Production paths (v4/, app.py, substrate_runner.py) must be enumerated explicitly — we cannot break them.

**V1.b:** Identify all writers of `krim.events.append(...)`. These need to also increment the new counter.

**V1.c:** Verify that the cognition write path (`_unwrapped_deltas` in neuron.py) and the brain.recall query path are the only sites doing the `len(krim.events) - ev0` pattern. If other sites use this pattern, report them.

## V2 — Implementation

### V2.1 — Add n_events counter to OscillatorKrimelack base

In `dsf_ai_service/v4/gualaloom_v4_krimelack_dna.py`:

```python
# In OscillatorKrimelack.__init__
self.n_events = 0  # monotonic counter, never reset, never bounded
```

At every site that appends to `self.events`, also increment `self.n_events`. The counter is O(1) per event regardless of list size.

### V2.2 — Adapter passthrough

Each sensory adapter (TactileKrimelack, OlfactoryKrimelack, etc. in `substrate_dna.py`) needs an `n_events` `@property` forwarding to `self._inner.n_events`. Mirror the pattern of the `.phase` property.

CochlearBankKrimelack has multiple internal krimelacks — its `n_events` should sum across them.

### V2.3 — Switch cognition path to counter

In `LoomNeuron._unwrapped_deltas` (neuron.py), replace:

```python
ev0 = len(krim.events) if hasattr(krim, 'events') else 0
# ... feed ...
ev1 = len(krim.events)
event_count = ev1 - ev0
```

with:

```python
ev0 = krim.n_events if hasattr(krim, 'n_events') else 0
# ... feed ...
ev1 = krim.n_events
event_count = ev1 - ev0
```

Same change in `brain.recall` query path.

### V2.4 — Bounded events buffer

The `events` list itself still accumulates for consumers. Bound it with a ring buffer:

```python
import collections
# In OscillatorKrimelack.__init__
self.events = collections.deque(maxlen=EVENTS_BUFFER_SIZE)
```

`EVENTS_BUFFER_SIZE = 1024` to start. Sized so 64 neurons × 6 krimelacks × 1024 events × 6KB ≈ 2.4GB total — fits, doesn't bound consumers unrealistically.

V1.a will tell us if any consumer reads events older than 1024 entries. If yes, surface that — we'll spec a different eviction policy.

### V2.5 — Verify n_events doesn't get reset

The `events.clear()` call in `_repeat_consolidation` (and any other clear sites V1 turns up) must NOT reset `n_events`. The counter is monotonic across the krimelack's lifetime; the list is bounded but the count keeps going. This is the whole point — count and storage decoupled.

## V3 — Validation

**V3.a:** Re-run the 38-test core regression suite. All must pass. If any test depended on `events` list growing unbounded, surface it — that's a test that was implicitly assuming the bug.

**V3.b:** Re-run the production tests (v4/, substrate_runner.py if it has a test suite). Confirm spike path still functions.

**V3.c:** Re-run sweep_137 cells A_n200, A_n400, B_ss16, B_ss32 — the cells that OOM-killed previously. They should now complete. Report T5 for each. We finally get the scaling curve.

**V3.d:** Memory probe. After teaching 100 concepts × 3 reps × 64 neurons, print:
- `sys.getsizeof(krim.events)` for one krimelack (should be small)
- Total RSS via `psutil.Process().memory_info().rss`

The new RSS should be a fraction of the old. Report the ratio.

## V4 — STOPs

- **STOP if V1 turns up a consumer reading events older than the buffer size.** Surface immediately; we'll spec a smarter eviction (e.g., LRU on event recency, or per-event TTL).
- **STOP if any of the 38 regression tests fail.**
- **STOP if V3.c results show T5 jumping or collapsing dramatically vs the 100-concept baseline.** Counter and list-length should produce identical event counts; if they don't, something is off in V2.5 (probably a reset path).

## V5 — Report

V5 report must include:

1. V1 inventory of all `krim.events` read/write sites with categories
2. V2 line counts per file
3. V3.a regression status (38/38 or failures)
4. V3.b production-path test status
5. V3.c sweep_137 scaling cells now complete: T5 at n_concepts = {25, 50, 100, 200, 400} and at seed_size = {4, 8, 16, 32}
6. V3.d RSS memory before vs after the patch
7. Honest assessment: did this fix the operational blocker for migration?

— Eve, 2026-06-22
