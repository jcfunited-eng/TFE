# GL-RPT-RECALL-SPEED-C1-20260704-177-v1

doc_id: GL-RPT-RECALL-SPEED-C1-20260704-177-v1
From: c1a | To: Eve, Joe, c1b | Responds to:
`GL-CMD-RECALL-SPEED-INVESTIGATION-EVE-20260704-177-v1`.
Vehicle: model code (`dsf_ai_service/loom_model/`) only — no deploy
action taken, no live call site touched. c1b holds the deploy trigger
per the dispatch's own routing.

**I1 and I2 are built, combined into one path (`Brain.recall_fast()` /
`Embryo.recall_fast()`), proven numerically identical to the existing
`recall()` on the exact modality set the live organism taps, and
measured at ~5x faster per call at the live population (N=64), growing
to ~13x at N=1024. I3 is subsumed by the I1+I2 design (explained
below, not separately built). I4 was not built, per the dispatch.
Not wired into any live call site — that cutover is a separate,
unratified decision, scoped precisely at the end of this report.**

---

## Failures first

**A real correctness bug was caught before being reported as done, not
after.** My first working version of `recall_fast()` passed every
low-level unit test (scalar-vs-vectorized physics, many random seeds,
real words, past the language-krimelack's 256-event saturation point)
but **failed end-to-end Counter parity against the real `recall()`**
at intermediate teaching depths (5 and 20 words taught) while
passing at 0 and at 50+ words. Root cause, traced by direct
introspection of real constructed neurons, not assumed: `Embryo.
_seed_dna_diversity()` (`embryo.py:175`) mutates **each neuron's own**
language krimelack's `kappa` and `threshold` by ring position at
birth — a real, per-neuron heterogeneity, not a shared constant. My
first version read `kappa`/`threshold` from one "representative"
neuron and applied it to all 64, which is exactly correct for the
three sensory modalities (tactile/olfactory/gustatory — confirmed
uniform, `_seed_dna_diversity` never touches them) but wrong for
language. The reason it only failed at 5/20 words and not 0 or 50+:
language's event count saturates at the krimelack's 256-slot deque
(see finding 2 below) — once saturated, `ev1-ev0` is trivially 0
regardless of the underlying physics, which **masked the bug** at
higher teaching depths rather than proving correctness there. Fixed
by reading `kappa`/`threshold` per-neuron for language (sensory
modalities keep the single-representative read, now with that
scoping stated explicitly in code). Re-verified: 180/180 exact Counter
matches across 9 (brain_seed, seed_size) combinations spanning
N=32/64/256, plus the full end-to-end/INV suite, all green. This is
exactly the "measure before trusting" discipline the disproven
memoization fix established last session — restated here because it
caught a second, different bug the same way.

---

## What was actually measured (the profile, before touching anything)

`tests/probe_177_recall_speed.py`, cProfile on the real live-shaped
path (`Embryo(observable="event_count")`, real `_organism_signal`
multi-modal tap, 30 words taught, population N=64 — matching the live
organism's construction exactly, `gualaloom_v5_engine.py:1521`):

| cost center | share of `recall()` |
|---|---|
| `_unwrapped_deltas` → per-modality krimelack physics (the nested `while` loops, ~230K individual step calls for 10 queries) | ~84% |
| — of which: `LanguageKrimelack.fingerprint()`, computed but **never read** by the caller (`_unwrapped_deltas` discards `transduce()`'s return tuple) | ~26% |
| `brain.py`'s snapshot/restore machinery (I1's target) | ~5% |
| `binding_atlas.recall_best()` (per-neuron cosine search) | ~6% |

This reordered Eve's a-priori risk/win ranking with real numbers: I1
alone (snapshot/restore) is a small, safe, but minor lever (~5%); the
big levers are I2 (the physics loop itself) and a fourth, unlisted one
found by profiling — **I0: `LanguageKrimelack.transduce()` always
computes a fingerprint that `_unwrapped_deltas` throws away.** Not
separately built — `recall_fast()` never calls `transduce()`/
`fingerprint()` at all, so I0's win is folded into the combined result
below for free, at zero additional risk (it isn't computed, not
computed-then-discarded).

---

## I1 (peek-mode) + I2 (vectorize across neurons) — built, combined

**Why combined, not separate:** I1's whole benefit (no snapshot, no
restore) falls out for free once the computation is vectorized and
non-mutating by construction — there is nothing left to snapshot or
restore if the code path never writes to a neuron's krimelack in the
first place. Building them as one path avoided a redundant
intermediate "peek but still per-neuron-Python-loop" version.

**The physics fact this rests on** (`vectorized_oscillator.py`
docstring, verified directly — not just read off the docstring in
`embryo.py:177` that already states it): `dphi = (omega - omega_0) *
dt = kappa * s_t * dt` — `omega_0` cancels algebraically, so a
neuron's phase increment per sample depends only on the signal and
its own `kappa`, never on its accumulated state. That's what makes
batching the per-sample loop across the whole neuron population exact
rather than approximate: the per-sample wrap-and-count step (the
nested `while` loops) is reproduced as an exact integer floor
division, looping over **samples** (small: ~20-160 per query) and
vectorizing across **neurons** (large: population-sized) at each
step — not the other way around. A single closed-form over the whole
feed (summing all samples first, wrapping once) was considered and
rejected: language's per-character signal changes sign
(vowel/consonant), so a multi-sample direction reversal can cross the
threshold going up and back down within one feed call, and a
net-sum-then-wrap shortcut silently cancels those events out. Verified
this distinction matters, did not just assume it.

**Correctness proof, three layers, all green:**
1. `tests/probe_177_vectorized_parity.py` — the low-level primitive
   against the real scalar `Krimelack`/`OscillatorKrimelack` physics
   directly: (a) synthetic random signals, 30 trials, spot-checked
   across 200 neurons each; (b) real `LanguageKrimelack.transduce()`
   on real words, unsaturated AND forced past the 256-event
   saturation point, AND with heterogeneous per-neuron kappa/threshold
   (the regression case from the failure above, now covered
   permanently); (c) real `OscillatorKrimelack.feed_signal()`
   (touch/smell/taste) with per-neuron attenuation and divergent
   starting phases.
2. `tests/probe_177_end_to_end_parity.py` — real `Embryo`, real
   `_organism_signal`, `recall_fast()` vs `recall()` Counter equality
   at 6 teaching depths (0, 5, 20, 50, 120, 250 words) spanning
   unsaturated and saturated language state: **all match exactly.**
   Stress-tested further beyond this file: 9 (brain_seed, seed_size)
   combinations × 20 probe words = 180/180 exact matches, N=32/64/256.
3. **INV-1 (read-only):** `recall_fast(x)` twice, no teaching between
   → identical Counters. **PASS.**
   **INV-2 (teaching-sensitive):** `recall_fast(x)` → real `remember(y)`
   → `recall_fast(x)` again → 6/10 probe queries changed. **PASS** —
   not frozen, not stale, genuinely reads current state.

**Measured speed, `tests/probe_177_timing.py`, `recall()` vs
`recall_fast()`, wall-clock (not cProfile-inflated), 15-rep average:**

| population (N) | words taught | `recall()` | `recall_fast()` | speedup |
|---|---|---|---|---|
| 32 | 30 | 7.23ms | 3.66ms | 2.0x |
| **64 (live)** | 30 | **14.47ms** | **2.88ms** | **5.0x** |
| 256 | 30 | 60.07ms | 7.96ms | 7.5x |
| 1024 | 30 | 236.46ms | 18.39ms | 12.9x |

| population | teaching depth | `recall()` | `recall_fast()` | speedup |
|---|---|---|---|---|
| 64 (live) | 0 | 7.69ms | 2.20ms | 3.5x |
| 64 (live) | 10 | 12.33ms | 2.81ms | 4.4x |
| 64 (live) | 50 | 15.21ms | 2.92ms | 5.2x |
| 64 (live) | 150 | 18.16ms | 3.07ms | 5.9x |
| 64 (live) | 300 (past saturation) | 19.50ms | 3.60ms | 5.4x |

Speedup **grows** with population (2x at N=32 → 13x at N=1024) — this
is the headroom Eve's dispatch asked to have named: the vectorized
path's fixed per-sample Python loop overhead gets amortized across an
ever-larger neuron array, while the original path pays that overhead
once per neuron, linearly. At the live population (N=64), a
`recall_fast()` re-profile shows `binding_atlas.recall_best()` (the
per-neuron cosine search, genuinely O(each neuron's own atlas size),
not further optimized here) now at ~20% of the (much smaller) total —
consistent with c1b's original characterization of that piece as
"already reasonably well-built."

---

## I3 (parallel neurons) — not separately built, and here's why

Eve's framing was "with I1 landed, query-time neurons are independent
read-only units — pool them across cores." That's true of the
**original** per-neuron design, but I1+I2 together restructure the
computation so there is no longer a set of independent per-neuron
units to hand to a process pool — the whole population's physics for
a given modality is already one batched numpy call. Reaching for
multiprocessing on top of that would mean paying real IPC/process-pool
overhead to parallelize a workload that's already ~3ms end-to-end at
the live population; that overhead would very plausibly exceed the
work being parallelized. Not built, because I1+I2 pre-empted the need
it was meant to address, not because it was skipped under time
pressure.

## I4 (staged recall) — not built, as directed

Explicitly flagged, not attempted. It changes what the population vote
*is* (cluster-prefilter before full physics), which the dispatch
itself said needs Eve's honesty ruling before any build. Nothing here
should be read as an argument for or against it.

---

## Secondary findings surfaced along the way (not fixed, in scope for someone else's call)

**1. The organism's population is NOT currently growing live.**
`Embryo.remember()`/`Brain.recall()` never call `LoomBrain.step()`, so
`cluster.process_folds()` never fires on this path — verified directly
(`tests/probe_177_recall_speed.py` Part B: population stays at 64
across teaching + recalling every word in a 36-word probe). This is a
correction to the standing framing ("population grows via her own
charge-and-fold mechanism, no ceiling") **as applied to the organism
specifically** — the organism's cost growth over her life comes
entirely from each neuron's own `binding_atlas` growing (real, but
smaller and already-vectorized, per the profile above), not from
population count. If population growth is wanted for the organism,
something would need to call `brain.step()` on it, which nothing
currently does.

**2. Language's `event_count` delta has been structurally zero for
essentially the organism's entire operational life.** `LanguageKrimelack`
(unlike the sensory adapters) has no monotonic `n_events` counter —
`_unwrapped_deltas` falls back to `len(krim.events)`, a `deque(maxlen=
256)`. Once 256 events accumulate (empirically: well under 100 words
taught), `len()` is pegged at 256 forever after — appending anything
evicts an equal amount, so `ev1 - ev0 = 0` regardless of how many real
winding transitions occur during a query. Verified directly (`tests/
probe_177_vectorized_parity.py` test (b), 540 real teaches, deque
confirmed saturated, delta confirmed 0 for 8 different probe words).
This corroborates, with a precise mechanism, the old open thread
already carried in the standing handoff ("language-dimension
saturation... saturates within ~4 taught words") — not new, but now
root-caused precisely enough that `saturating_new_count()` had to
replicate this exact behavior (not fix it) to get parity right. Left
alone, per standing dispatch discipline — this is old open item #1,
not part of today's dispatch.

**3. Per-neuron language attenuation is inert, already known/documented
in the codebase** (`embryo.py:177`'s own comment: "RESONANT (omega_0)
is INERT in the current krimelack... omega_0 cancels"). Verified this
directly too (two `LanguageKrimelack` instances fed identical words
with different `omega_override` values produce byte-identical state
throughout) since `recall_fast()`'s correctness depends on getting this
exactly right, not just trusting the comment — it does hold. Not a new
finding, just independently re-confirmed because it had to be.

---

## What this interacts with: c1b's already-deployed frequency reduction

While this investigation was in progress, c1b built and deployed
(`task:466`, SHA `8cb18e0`, see `GL-RPT-RECALL-FREQUENCY-REDUCTION-
C1B-20260704-v1.md`) a **complementary, orthogonal** fix: calling
`organism.recall()` less *often* at the two hottest call sites
(`read_word`'s seam-2 recognition: every 3rd word instead of every
word; seam-4 habituation freshness: 3 samples instead of 10), reusing
`self._last_surprise` honestly in between. That is a call-*frequency*
fix; this report is a call-*cost* fix. They stack multiplicatively,
not redundantly: at seam 2, for example, (1/3 the calls) × (~1/5 the
cost per call at N=64) would be roughly 1/15th of the original seam's
total contribution, if `recall_fast()` were ever wired in on top of
the already-deployed frequency reduction. c1b's own report states
plainly that the per-call architecture cost "remains architecturally
unchanged" by their fix and "needs its own dedicated investigation" —
this report is that investigation.

---

## Deploy state vs. git state (per standing convention)

**Nothing here is live or wired to anything live.** `Brain.recall_fast()`
and `Embryo.recall_fast()` are new, additive methods — `Brain.recall()`
and `Embryo.recall()` (the originals) are byte-for-byte untouched
(`git diff` on `brain.py` shows insertions only). No existing test in
`dsf_ai_service/loom_model/tests/` regressed (`test_brain.py`, `test_
cognition_path.py`, `test_neuron.py` all re-run; the 3 pre-existing
failures in `test_cognition_path.py` — `test_t7_cross_modal`, `test_
t8_noise_robustness`, `test_t11_substrate_true` — reproduce identically
on a stash of this work, confirmed via direct A/B, unrelated to this
change). The three live call sites that would need to change to
actually use this (all in `gualaloom_v5_engine.py`, current line
numbers as of this report's HEAD): `_recognition_from_organism`
(seam 2, line 1738), `_recall_from_organism` (seam 1, line 3997),
`_association_from_organism` (seam 3, line 4032) — each currently
calls `self.organism.recall(...)`; swapping to `self.organism.
recall_fast(...)` is the entire cutover, once ratified. **Not done
here** — that crosses from model code into the live engine's actual
behavior, which is c1b's deploy call per this dispatch's own routing,
not mine to make unilaterally.

**Target assessment, stated honestly:** per-call, `recall_fast()`
measures 3-13x faster depending on population, ~5x at the live scale
today. Whether this alone reaches Eve's "single-digit seconds per
conversational turn" target depends on how many `recall()` calls a
real turn makes across all four call sites combined — a number this
report has not directly measured on the live process (that would need
live cProfile instrumentation during a real exchange, which c1b's
reports note is still pending for the frequency-reduction fix too).
Stating the honest range rather than a single confident number: if a
turn's `organism.recall()` calls dominate its cost roughly the way
c1b's read_word profiling suggests, a ~5x per-call reduction stacked
on the already-deployed ~3x frequency reduction at the two hottest
sites would be a substantial combined win — but the actual turn-level
number needs a real measurement, the same way every other number in
this investigation did.

---

## Files

- `dsf_ai_service/loom_model/vectorized_oscillator.py` — the physics
  primitive (`vectorized_wind_count`, `language_base_dphi_raw`,
  `saturating_new_count`, `monotonic_new_count`).
- `dsf_ai_service/loom_model/brain.py` — `LoomBrain.recall_fast()`
  (additive, after the existing `recall()`).
- `dsf_ai_service/loom_model/embryo.py` — `Embryo.recall_fast()`
  (thin wrapper, mirrors `Embryo.recall()`).
- `dsf_ai_service/loom_model/tests/probe_177_recall_speed.py` — cProfile
  breakdown + population-growth check (finding 1).
- `dsf_ai_service/loom_model/tests/probe_177_vectorized_parity.py` —
  low-level scalar-vs-vectorized proof, 3 levels.
- `dsf_ai_service/loom_model/tests/probe_177_end_to_end_parity.py` —
  real end-to-end Counter parity + INV-1/INV-2.
- `dsf_ai_service/loom_model/tests/probe_177_timing.py` — before/after
  wall-clock at multiple population sizes and teaching depths.

### Changelog
- v1 (2026-07-04, c1a): I1+I2 built and combined (`recall_fast()`),
  proven numerically identical to `recall()` (3-layer unit parity +
  end-to-end Counter parity + INV-1/INV-2), measured 3-13x faster
  depending on population (~5x at the live N=64). A real per-neuron
  kappa/threshold heterogeneity bug caught by end-to-end testing
  before being reported as done, root-caused, fixed, re-verified
  (180/180 across 9 seed/population combinations). I3 subsumed by the
  I1+I2 design, not separately needed. I4 not built, per dispatch.
  Two secondary findings surfaced (population not live-growing for the
  organism; language's event_count delta structurally zero since early
  saturation, corroborating the standing "language-dimension
  saturation" open item) — neither fixed, out of this dispatch's scope.
  Noted interaction with c1b's already-deployed (task:466) call-
  frequency reduction — complementary, stacking, not overlapping.
  Nothing wired into any live call site; that cutover is scoped
  precisely for whoever is ratified to make it.
