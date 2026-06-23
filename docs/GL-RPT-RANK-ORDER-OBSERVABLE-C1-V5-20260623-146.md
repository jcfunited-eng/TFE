# GL-RPT-RANK-ORDER-OBSERVABLE-C1-V5-20260623-146

doc_id: GL-RPT-RANK-ORDER-OBSERVABLE-C1-V5-20260623-146
To: Eve (via Joe)
From: c1
Re: V5 — rank-order observable, opt-in + validation against event_count (GL-CMD-146)
Date: 2026-06-23

**Headline: rank-order does NOT transfer to the substrate. It is below event_count at
EVERY n (32% vs 96% at n=25; 4% vs 19% at n=200), because the substrate's first-wrap
ORDER is fixed by per-modality krimelack structure, not concept phase — rank vectors are
largely degenerate (4 of 6 concepts share one ordering). The toy's uniform-LIF regime
made timing concept-specific; the heterogeneous substrate does not. Implemented as
opt-in; event_count stays default and is byte-identical. Parity exact (0.0pp).**

## V1 audit

- **V1.a — PASS.** krim.events entries carry a `t` field. Real payload:
  `{'t': 3.84, 'dw': 1, 's': 0.6519}` (language); every modality's events have `t`.
  Caveat documented: `t` is *cumulative* for oscillator krimelacks
  (language/tactile/olfactory/gustatory) and *reset-per-feed* for Visual/Cochlear, and
  the cumulative scales differ wildly across modalities (language 3.84 vs olfactory 144).
  So I extract a per-modality *relative* first-wrap (first new-event `t` minus the
  krimelack's pre-feed `t`, which is 0 for the reset-type adapters). No V4.a STOP.
- **V1.b — PASS.** `krim.n_events` before/after delta extracts this feed's new events
  (same slice the event_count path uses). Confirmed.
- **V1.c — PASS.** Single switch preserved: `LoomBrain(observable=...)` (constructor
  opt-in, Eve's preferred pattern) threaded brain→hemisphere→cluster→neuron (incl.
  daughter neurons), plus a `COGNITION_OBSERVABLE` env fallback. Both `experience_moment`
  (write) and `brain.recall` (query) read `neuron.observable`, so they flip together —
  the GL-CMD-140 V1.b asymmetry-impossible property holds.

## V2 — implementation (opt-in, default unchanged)

| File | change |
|---|---|
| neuron.py | `observable` param on `LoomNeuron`; `_unwrapped_deltas` branches event_count / rank_order; `_krim_time` helper. Feed side identical for both. |
| cluster.py | `observable` param; passed to neurons + daughters |
| hemisphere.py | `observable` param → cluster |
| brain.py | `observable` param (None→env→"event_count"); → hemispheres |

No edits to krimelack internals, signal_attenuation, topology, or test_cognition_path.
**event_count default verified byte-identical** (standalone -144 helper and -146 helper
both return 100.0% at n=25 seed=42 — MATCH).

## V3 — validation

**V3.a — 38/38 core PASS under default (event_count).** Opt-in does not touch default.

**V3.b/c — Capacity curve (seed_size=8, 3 seeds, production brain.recall):**

| n | event_count | rank_order |
|---|---|---|
| 25 | 96.0% (sd 0) | 32.0% (sd 0) |
| 50 | 98.0% (sd 0) | 10.0% (sd 0) |
| 100 | 73.0% (sd 0) | 8.0% (sd 0) |
| 200 | 19.0% (sd 0) | 4.0% (sd 0) |
| 400 | 3.0% (sd 0) | 2.2% (sd 0) |

Per **V4.b** (rank-order regresses below event_count — it does, at the very first point),
I did NOT run the full 11-point 4h sweep. The 5 toy-comparison points + diagnostics below
fully characterize it. rank-order doesn't just regress; it collapses *faster* (already 10%
by n=50). (event_count here differs ≤4pp from GL-CMD-144's 100/98/73/17/4 — see V4.e.)

**V3.d — Per-neuron distribution at n=200 (seed 42), both observables:**

| concept | event_count winner / win / correct / uniq | rank_order winner / win / correct / uniq |
|---|---|---|
| beacon | canyoncopper / 48 / **0** / 2 | castle / 16 / **8** / 6 |
| golden | anchorfeather / 64 / **0** / 1 | pavilion / 16 / **16** / 5 |
| river | reedstone / 32 / **0** / 4 | beacon / 40 / **16** / 3 |
| feather | gardenpepper / 40 / **0** / 2 | river / 16 / **8** / 6 |
| saffron | cottage / 64 / **0** / 1 | cottage / 16 / **8** / 7 |

**V3.e — Parity (rank_order, production vs independent harness reimplementation):**

| n | production | harness | Δ |
|---|---|---|---|
| 25 | 32.0% | 32.0% | **0.0pp** |
| 50 | 10.0% | 10.0% | **0.0pp** |
| 100 | 8.0% | 8.0% | **0.0pp** |

0.0pp at every point — no V4.d STOP. The implementation is faithful; rank-order's failure
is the mechanism, not a port bug.

**V3.f — test_cognition_path under rank_order (`COGNITION_OBSERVABLE=rank_order`):**

| test | event_count (default) | rank_order | Δ |
|---|---|---|---|
| T4 hemisphere recall | PASS | **FAIL** | regressed |
| T5 brain 25 | PASS | **FAIL** | regressed |
| T6 vocab 50 | PASS | **FAIL** (6%) | regressed |
| T7 cross-modal | FAIL (5-sens 94%) | FAIL (5-sens **8%**) | much worse |
| T8 noise 0.30 | FAIL (12%) | FAIL (**0%**) | worse |
| T1–T3, T9–T12 | PASS | PASS | unchanged |

Result: **5 failed / 7 passed** under rank_order vs **2 failed / 10 passed** under
event_count. rank-order is worse on every recall test, including catastrophic on
cross-modal (5-sensory 94%→8%).

## V4 — STOP handling

- V4.a (no `t` field): not tripped — `t` present.
- **V4.b (rank-order < event_count): TRIPPED at every n.** Surfaced; did not run the full
  11-point sweep.
- V4.c (rank-order ≥95% at n=400): not tripped — it's 2.2%, near chance.
- V4.d (parity >0.5pp): not tripped — 0.0pp.
- **V4.e ("that can't be right"): event_count read 96% in-probe vs 100% standalone at
  n=25.** Root-caused (not self-cleared): signal seeding uses `hash(word)` /
  `hash((word, modality))` in experience.py + sensory_transducer.py, and Python salts
  string/tuple hashing per process (PYTHONHASHSEED) — confirmed: `hash('rabbit')` differs
  across processes. So clean-cue signals differ across runs → T5 wobbles ±few pp
  *across* processes while staying deterministic *within* a process (hence sd=0.0 in both
  -144 and -146). Pre-existing, not introduced here; does not change any conclusion (the
  rank-order gap is 60+pp). Recommend `PYTHONHASHSEED=0` for reproducible capacity probes,
  or replacing salted `hash()` with a stable hash in the seeding path.

## Plain-language reads (no default recommendation — Joe's call)

**1. Does rank-order delay / eliminate / move the cliff? NONE — it deepens it.**
rank-order is below event_count at every n and collapses sooner (10% by n=50 vs 98%).
It does not move the capacity cliff; it starts far lower and falls faster. On this
substrate, rank-order is not a viable cognition observable.

**2. Does rank-order change the failure mode? YES — collision → scatter.**
At n=200, event_count fails by *confident collision*: the population converges (unique
1-4) on a wrong winner, correct concept gets **0 votes**. rank-order fails by *diffuse
scatter*: higher disagreement (unique 5-7), and the correct concept gets a **weak nonzero
signal (8-16 of 64 votes)** — but a wrong concept still wins the plurality (16-40 votes).
So rank-order spreads the vote and surfaces a faint correct signal where event_count gives
none, but the 6-value coarse permutation cannot separate 200 concepts, so net accuracy is
lower. The root cause (shown in V1 probing): substrate first-wrap *ordering* is dominated
by fixed per-modality krimelack structure (heterogeneous dt + language-transduce vs
sensory-feed paths), so rank vectors are largely degenerate — 4 of 6 concepts produced the
identical ordering `(2,4,6,1,3,5)`. The toy's uniform LIF made first-wrap concept-driven;
the substrate's heterogeneous krimelacks make it modality-driven. This is precisely the
"production has homogenization the toy doesn't capture" the toy's own caveat predicted.

**3. Does rank-order preserve the -140 parity property? YES.** 0.0pp production-vs-harness
at every point; single-switch (constructor + env) flips write and recall together.

## Net

event_count remains the better observable on the substrate by a wide margin and stays the
default (unchanged, verified). rank-order is implemented and retained as opt-in for the
record and for the regime where it might help (sparse-modality concepts — untested here,
flagged by the toy as a separate future question), but on dense-6-modality stimuli at
substrate it is strictly worse. The specific learning: the substrate does not encode
concept identity in cross-modal first-wrap *timing*; it encodes it (weakly, capacity-bound)
in wrap *counts*. Whatever lifts the n=200 cliff will not be a timing-rank observable in
the current krimelack regime.

No recommendation on making rank-order default — the table is the decision input.

— c1, 2026-06-23
