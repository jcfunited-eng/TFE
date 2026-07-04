# GL-RPT-GROWTH-CHART-C1-20260704-v1

doc_id: GL-RPT-GROWTH-CHART-C1-20260704-v1
From: c1a | To: Eve, Joe
Responds to: GL-CMD-C2-WHOLE-BRAIN-EVE-20260704-168-v3 ("the first GROWTH
CHART, failures first").
Vehicle: model work only (`dsf_ai_service/loom_model/`,
`dsf_ai_service/curriculum/`). Zero live-path changes (Gate G-4, verified
below).

**One organism (`Embryo`, the committed 8-hemisphere seed, all mechanisms
co-present from tick zero) raised on 3 compressed "days" of a real 30-
sentence story corpus with 3 sleep/replay cycles, all fifteen mechanism
slots read at every checkpoint. Eleven mechanisms have real code paths and
real curves below; four are ABSENT (no code path), named per A5. Two
findings tripped the >95% too-good STOP and were investigated, not
celebrated. One finding (folding actually fired) partially contradicts a
naive reading of this CMD's own A5 text and is reported first, not buried.**

---

## Failures first

**1. Folding fired — 64 → 120 neurons — through a DIFFERENT mechanism than
the one this CMD's A5 describes as blocked.** A5 says "folding-during-
experience remains blocked (n_eff 3.000 vs 2.943, hetero-krimelack attempt
failed) — the organism grows within seed capacity this run." That
specific mechanism — `LoomBrain.step()`'s `process_folds()`, keyed to
`L6_TCL.n_eff < n_start/e` — **did** stay blocked exactly as described:
`mean_n_eff` sat flat at **7.0** for every organ across all three days
(threshold is `n_start/e ≈ 2.94`, nowhere close). But `Embryo` has its
**own, separate** folding mechanism (`_charge_and_fold`, a q-charge
capacitor model: neurons accumulate charge from *coherent* bipolar
taste/smell experience, divide when `q > 1`, contact-inhibition and a
conservation-pool cap it) — and that one **did** fire, growing the
organism from the 64-neuron seed to **120 neurons within Day 0**, then
holding flat at 120 through Days 1-2 (the conservation pool drains to
zero once population exceeds `N_initial`, self-limiting — exactly as
`Embryo`'s own comments describe, and confirmed here, not just claimed).
Per-organ: em/pr/ep/sc/sf/sv/aff all doubled (8→16); `gp` (goals) alone
stayed at seed size — consistent with its documented slow-integrator
design (`quantum_scale=0.2`), not a bug. **This is not a violation of
anything I was asked to do** — A1 says "all mechanisms that exist in the
module run TOGETHER," and this fold mechanism does exist and is part of
the committed organism — but it means A5's own text, read literally,
describes only one of two live folding pathways in this organism, and I
did not silently reconcile the discrepancy myself. Reporting it plainly:
folding capacity is NOT fully contained to seed size in this run, via a
mechanism this CMD doesn't mention.

**2. Sequence (#9) hit the >95% STOP — investigated, and it's degenerate,
not a real result.** Raw number: pr-hemisphere next-word prediction =
**100%** (8/8) against an 11.1% chance floor. Per G-2's "STOPs: >95%
anywhere," I distributed per-neuron scores (era rule) rather than report
the headline number: **all 64 neurons agreed on every single prediction**
(8/8 queries, 100% unanimity). Root cause, confirmed directly: the test
sentence ("once upon a time there were four little rabbits") has **9
unique words with zero repeats**, so `perceive_sequence`'s word_t→word_t+1
binding is a collision-free lookup table — of course every neuron gets it
right, exact-cue, no competition. This is the same "single-neuron ceiling
replicated across the population" pattern the 6/22 audit named for a
different mechanism, now confirmed for Sequence too. **Not a hash bug,
not a fabricated result — a test that was too easy to mean anything.**
A real test needs a sentence with repeated words (ambiguous next-word
given a repeated cue) — not built here; flagged as the actual next step
for this gauge, not smoothed over as a win.

**3. The A4 comparison arm (resonant_spectral) is ALSO 100%/unanimous —
already known, re-confirmed, not new.** `recall` under `resonant_spectral`
held flat at 100% every checkpoint. Per-neuron check: 64/64 unanimous on
every query (confirmed directly on a fresh instance). This is the SAME
degeneracy the 6/22 audit's V1.a finding already documented for this exact
observable ("the population is degenerate... not a population code") —
citing it here as expected confirmation, not claiming it as a new result.

**4. A methodology bug I found and fixed mid-session: the first full run's
probe set was being resampled every day from a shared RNG stream, making
day-to-day recall numbers not truly comparable.** Caught before writing
this report (not after) by noticing recall dipped non-monotonically in a
way that didn't track any other signal. Fixed: the probe set is now drawn
**once**, before Day 0, and reused at every checkpoint. The numbers below
are from the corrected run.

**5. Four mechanisms genuinely have no code path in `loom_model` and are
marked ABSENT below — not simulated, per A5:**
- **#2 Composition** — `LoomTapestry`/`LoomMosaic` (the real composition
  mechanism, `dsf_ai_service/loom_model/tapestry.py`) exists but runs on a
  completely separate cluster/mosaic structure, never wired into
  `Embryo`/`LoomBrain`. Building a second, disconnected structure just to
  get a number would violate G-1 ("no mechanism reported from a separate
  bench").
- **#10 Imagination** — no generative/novel-combination code anywhere in
  the module (confirmed by search: no daydream/imagination-generation
  function exists).
- **#11 Reflection** — depends on an emission/self-hearing loop, which
  depends on Composition (absent). No independent code path.
- **#13 Theory of mind** — explicitly out of scope per the -103 table and
  this CMD's own "who-tags, etc." example.

**6. Cross-modal (#5) is flat at literal 0% for all three days — no
cross-modal transfer has emerged yet in this compressed run.** Named
honestly rather than averaged away; three days of a ~250-word/day corpus
each word seen ~1-2 times is not enough exposure for language-only cues to
retrieve senses bound in the same moment, at least not yet.

**7. Hemisphere integration (#12) is essentially flat/near-null across all
three days** — 8 of 9 tracked organ-pairs sit at exactly 0.0 throughout;
one (`ep`,`sf`) shows a nonzero but non-growing 0.0015. The consensus
mechanism exists and is wired (confirmed executing every tick), but this
run gives no evidence yet that hemispheres are actually shaping each
other — a real, unresolved immaturity, not a wiring failure (see Gate
review below for the distinction).

**8. Retention (#4) is nearly flat** — the Day-1 probe words' recall sits
at 0.111 (1/9) through Day 0, Day 1, and Day 2, ticking up to 0.222 (2/9)
only at the very last checkpoint (Day 2, post-sleep). Reporting the number
as measured, not rounding up to "improving" from one late data point.

**9. A pre-existing RNG usage in `Embryo`, flagged for Eve's ruling, not
decided by me.** `Embryo._seed_dna_diversity()` (not written by me — part
of "the committed organism" I was told to boot as-is) seeds each neuron's
chemical/metabolic differentiation (kappa, threshold, aff_gain, polarity)
from `np.random.default_rng(1000 + neuron_index)` — deterministic per
neuron index (same every run), not per-run-random, and used for receptor
sensitivity/excitability, not for the population-vote-diversity mechanism
the 6/22 STOP was written against (ring-position masks, subspace voting).
I did not touch this code and did not add any new RNG-seeded
differentiation myself (the harness's own RNG use — cue selection for
probes, degradation jitter, replay sampling, association controls — is
cue-noise-only, per G-2/G-3, and is documented in the harness's own
module docstring). Whether this pre-existing mechanism itself needs
scrutiny under the STOP's scope is Eve's call, not mine.

---

## What was built (all model-work, zero live-path changes)

1. **Ported `dsf_ai_service/curriculum/sensory_catalog.py` and
   `catalog_atlas_reader.py` verbatim from `codex/persistent-etl-
   update-20260326` (commit `31b9e8c`)** — these did not exist on
   guala-live at all. Discovered because `dsf_ai_service/loom_model/tests/
   test_folding_engaged.py` (a real, already-written test using the exact
   30-sentence Peter Rabbit corpus + a real catalog-backed atlas reader)
   has been **uncollectable** (`ModuleNotFoundError`) this whole time —
   these two files were referenced but never merged. Porting them fixes
   that test too (confirmed: `test_t1_plumbing`/`test_t2_multi_hemisphere`
   now pass; `test_t8_substrate_true` fails for the same pre-existing,
   unrelated `loom_model/__init__.py` partial-import reason already
   documented in the sense-repair report — not caused by this port).
   This is exactly what A2 asks for: "the sensory transducer on the codex
   branch" — a real, stateful `AtlasReader` so repeated exposure actually
   converges toward a stable percept, instead of every encounter being
   treated as the first (`NullAtlasReader`'s behavior, which every prior
   loom_model test has used).
2. **`Embryo.__init__` gained an `observable` constructor arg** (was
   hardcoded to `"resonant_spectral"`), defaulting to the same value —
   zero behavior change for any existing caller. This is what makes A4's
   twin-organism comparison possible.
3. **`dsf_ai_service/loom_model/tests/whole_brain_168v3.py`** — the
   harness: curriculum delivery (real catalog-backed signals, not
   fabricated), a sleep/replay cycle built fresh from real primitives (re-
   presents already-experienced words through the same `remember()` path
   — no native loom_model sleep/replay mechanism exists; confirmed by
   search before writing this, so this is SCAFFOLDING, not an emergent
   substrate property, and is labeled as such here), and eleven gauge
   functions, each reading the SAME running organism's real state.

---

## The growth chart

Two organisms, identical seed/curriculum/tick sequence, differing only in
`observable` (A4): **primary** = `event_count` (the sense-repaired
champion), **compare** = `resonant_spectral` (today's production default).
3 days × (242 word-tokens/day + 15-word sleep/replay), fixed 10-word probe
set. 64-neuron seed (8 hemispheres × 8), `brain_seed=42`.

| # | Mechanism | Status | Day 0 | Day 1 | Day 2 | Note |
|---|---|---|---|---|---|---|
| 1 | Recall | **MEASURED** | event_count 40% / resonant_spectral 100% | 30% / 100% | 50% / 100% | event_count noisy, not monotonic at this scale (10-word probe, ~1-2 exposures/word/day); resonant_spectral degenerate-100% (Failure 3) |
| 2 | Composition | **ABSENT** | — | — | — | LoomTapestry disconnected from Embryo (Failure 5) |
| 3 | Association | **MEASURED** | — | — | mean cosine: co-occurring 0.916 vs random-control 0.910 | one-shot, end of run. Barely above control — real substrate cosines are compressed near 1.0 at this scale (matches the "0.94-1.0 capacity wall" finding from the 6/22 arc); no meaningful discrimination yet |
| 4 | Retention | **MEASURED** | 11.1% | 11.1% | 11.1% → 22.2% (post-sleep) | flat, late uptick (Failure 8) |
| 5 | Cross-modal | **MEASURED** | 0.0% | 0.0% | 0.0% | flat zero (Failure 6) |
| 6 | Habituation | **MEASURED** | — | — | delta_eff: [0.1, 0.1, 0.1, 0.1, 0.1, 0.1] (6 exposures) | FLAT — `FamiliarityFeedback` is live and wired (confirmed via `neuron.step()`'s own `match_score` update) but shows no measurable habituation to "peter" repeated 6x in isolation; may need in-context (corpus-embedded) repetition, not isolated re-delivery, to show a curve |
| 7 | Recognition | **MEASURED** | 0.0% | 0.0% | 10.0% | late, small emergence under jitter=0.3 |
| 8 | Attention (translated) | **MEASURED** | 20% unanimous | 20% unanimous | 20% unanimous | flat, and NOT degenerate (80% of queries show real disagreement) — healthiest gauge in the set; engineering-judgment translation of the mechanism, flagged (loom_model has no literal "selection entropy/bypass-detector" test) |
| 9 | Sequence | **MEASURED, too-good** | — | — | 100% (8/8), 100% unanimous | degenerate — collision-free test sentence (Failure 2) |
| 10 | Imagination | **ABSENT** | — | — | — | no generative code path (Failure 5) |
| 11 | Reflection | **ABSENT** | — | — | — | depends on Composition, absent (Failure 5) |
| 12 | Hemisphere integration | **MEASURED** | ~0 (8/9 pairs) | ~0 (8/9 pairs) | ~0 (8/9 pairs) | flat/near-null (Failure 7) |
| 13 | Theory of mind | **ABSENT (out of scope)** | — | — | — | explicit, per -103 and this CMD |
| 14 | Affect modulation | **MEASURED** | arousal 0.1034 | 0.10343 | 0.10343 | converges to steady state within Day 0, stays there — bounded [0,1] synthesis/clearance working as designed, not a multi-day-developing curve |
| 15 | Meta-monitoring | **MEASURED** | strengths: em 15.2, pr 10.7, ep 35.6, sc 23.4, gp 0, sf 35.6, sv 40.0, aff 15.2 | em 16.4, pr 11.0, ep 63.6, sc 30.3, gp 0, sf 63.6, sv 79.8, aff 16.4 | em 16.6, pr 11.0, ep 85.4, sc 32.3, gp 0, sf 85.4, sv 119.6, aff 16.6 | real, clean development: `sf`/`sv`/`ep` grow strongly (sf nearly linear: 40→80→120), `gp` never activates (consistent with its slow-integrator design), arousal/population components of the self-vector already flat by Day 0 |

**11 measured, 4 ABSENT, matching A5's own explicit allowance** ("any
mechanism with no code path yet... appears on the chart as ABSENT, never
simulated").

---

## Folding status (A5 — named on this chart, not hidden)

`L6_TCL.n_eff` (the mechanism A5 describes): flat at **7.0** for every
organ, all 3 days. Threshold `n_start/e ≈ 2.94`. **Correctly blocked**,
exactly as A5 predicted.

`Embryo._charge_and_fold` (a separate mechanism, see Failure 1): fired
once, early — **64 → 120 neurons by end of Day 0**, held flat through
Days 1-2 (conservation-pool self-limiting, not a hardstop — the
`_POP_HARDSTOP=256` ceiling never came close to firing). Per-organ: em/
pr/ep/sc/sf/sv/aff doubled (8→16 each); `gp` stayed at 8.

---

## Gates

- **G-1** (one organism, one run, fifteen curves): honored — every
  measured gauge above reads the SAME two `Embryo` instances at the SAME
  checkpoints; nothing benched separately except the two standalone
  per-neuron "too-good" diagnostics (Failures 2-3), which are explicitly
  investigative follow-ups on results already produced by the main run,
  not alternate measurements of the mechanism itself.
- **G-2** (STOPs: >95% anywhere / RNG in neuron identity / exp(1j·Δ)):
  two >95% triggers, both investigated and reported as degenerate, not
  celebrated (Failures 2-3). RNG in neuron identity: none added by this
  harness; one pre-existing use flagged, not decided (Failure 9). No
  exp(1j·Δ) anywhere — `grandurun_state` (used by `event_count`) is a real
  R⁶ vector; `resonant_chi`'s ternary chi (used by `resonant_spectral` and
  the `sc` hemisphere's profile encoding) is also real-valued.
- **G-3** (scaffolding-vs-emergent label per -103): applied throughout —
  sleep/replay is explicitly scaffolding (built fresh, no native
  equivalent); Recall/Habituation/Sequence/Hemisphere-integration/Affect/
  Meta-monitoring are emergent substrate properties (pre-existing
  mechanisms, just read out); Association/Attention are engineering-
  judgment translations of the -103 test criteria to loom_model's actual
  architecture, flagged as such at each definition.
- **G-4** (diff proves scope: model only): new/changed files are
  `dsf_ai_service/curriculum/sensory_catalog.py` (new, ported),
  `dsf_ai_service/curriculum/catalog_atlas_reader.py` (new, ported),
  `dsf_ai_service/loom_model/embryo.py` (one backward-compatible
  constructor arg), `dsf_ai_service/loom_model/tests/whole_brain_168v3.py`
  (new harness). None touch `dsf_ai_service/app.py`,
  `dsf_ai_service/substrate_runner.py`, or any file under
  `dsf_ai_service/v4/`.

---

## Status

Filed and pushing now: this report, the two ported catalog files, the
`Embryo.observable` addition, and `whole_brain_168v3.py`. The first growth
chart is real, immature in most places (as A3 says to expect), degenerate
in two places that looked too good, and names one thing (folding) that
doesn't fit this CMD's own text as written. Joe's part, per this CMD:
none until this chart — recommending as next steps (not started, not
mine to schedule): a sequence test sentence with real word repetition (to
get a non-degenerate #9 number), a longer or repeated-exposure run to see
whether cross-modal/hemisphere-integration/retention curves actually bend
upward with more "childhood," and Eve's ruling on the Embryo DNA-diversity
RNG question (Failure 9).
