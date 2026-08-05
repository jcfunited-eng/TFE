> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-RPT-T5T9-F1F2-STATUS-C1-20260703-v1

doc_id: GL-RPT-T5T9-F1F2-STATUS-C1-20260703-v1
From: c1a | To: Eve
Re: Eve's ruling on GL-CMD-ATTEND-GROOVE-EVE-20260703-107 follow-up —
   Ruling (2) suite repair + T5-T9 fresh run with v7 A5 discipline;
   plan v7 A2 carried item (F1/F2 status). S2a is a separate,
   still-pending item (see chat).

---

## Failures first

- T7 (cross-modal partial recall): **CRASHES**, not just a threshold
  miss. `resonant_chi.ternary_chi` does a fixed-shape matmul that
  assumes all modalities present; dropping modalities changes the
  feature-vector length and the projection matrix no longer matches.
  This is a live bug in the DEFAULT (`resonant_spectral`) observable's
  partial-cue handling, currently uncaught by anything except this test.
- T8 (noise robustness): FAILS its provisional floor — 40.0% at noise
  0.30 vs the GL-CMD-140 floor of ≥45.0%.
- T11 (no stray production imports): FAILS, but the assertion itself is
  stale/over-broad — see below. Does not contradict the dormancy
  finding.
- T5 and T6 both landed at 100.0% — the too-good STOP. Investigated,
  not celebrated (below): it's the same degenerate population
  collapse the 6/22 audit already named, still present today.

---

## Ruling (2) — suite repair, done

`dsf_ai_service/substrate/sensory_transducer.py` copied verbatim from
`codex/persistent-etl-update-20260326` (`bfdad9a`) with a provenance
header, own commit (`596e366`). This unblocked
`test_cognition_path.py`'s collection — it went from "cannot import" to
12/12 collecting and running.

## T5-T9, fresh, today (v7 A5 discipline: report what lands, force nothing)

```
T5  brain 25 concepts:        100/100 = 100.0%   PASS  (too-good STOP — see below)
T6  vocab 50:                 200/200 = 100.0%   PASS  (same pattern, see below)
T7  cross-modal partial:      CRASH (ValueError, dimension mismatch)   FAIL
T8  noise robustness:         30%: 40.0%  50%: 16.0%  80%: 10.0%       FAIL (floor 45.0%)
T9  linear scaling 128→256:   100.0% / 100.0%; teach 25.9s→50.4s;
                              recall 140.8ms→284.4ms/query             PASS
```
(T1-T4, T10, T12 also ran clean; not gated by this dispatch, omitted
for brevity — full output available on request.)

### The too-good STOP, investigated (T5 and T6 both)

Per the ruling: "a suspiciously high T5 gets a per-neuron prediction
distribution, not a celebration." Instrumented `brain.recall()` directly
(it already returns the full per-neuron vote `Counter` before
`.most_common(1)` truncates it) and checked the actual distribution
across the population (64 neurons: 8 hemispheres × 8/hemi at this
seed_size) for both T5's and T6's concept sets:

```
concept_00: total_votes=64, n_distinct_concepts_voted=1, top3=[('concept_00', 64)]
concept_01: total_votes=64, n_distinct_concepts_voted=1, top3=[('concept_01', 64)]
concept_02: total_votes=64, n_distinct_concepts_voted=1, top3=[('concept_02', 64)]
concept_03: total_votes=64, n_distinct_concepts_voted=1, top3=[('concept_03', 64)]
concept_04: total_votes=64, n_distinct_concepts_voted=1, top3=[('concept_04', 64)]

word_000: total_votes=64, n_distinct_concepts_voted=1, top1=[('word_000', 64)]
word_001: total_votes=64, n_distinct_concepts_voted=1, top1=[('word_001', 64)]
word_002: total_votes=64, n_distinct_concepts_voted=1, top1=[('word_002', 64)]
```

**64/64 unanimous, every query, both tests.** This is exactly the
degeneracy the 6/22 V1.a audit named ("one unique prediction per query
across all neurons; the population is degenerate") — not fixed,
unchanged, reproduced today on the current default observable
(`resonant_spectral`). T5/T6's 100% is single-neuron-ceiling behavior
replicated identically across every neuron, not population
discrimination. Filing this as confirmation-of-standing-finding, not a
new result — Q1 (per-neuron differentiation from real per-neuron state)
remains fully open and is exactly what today's numbers show is still
missing.

### T11, precisely

The test asserts no `dsf_ai_service.app`/`substrate_runner` import
matches `import.*binding_atlas|import.*grandurun|from.*loom_model`. It
fails — but the actual matches are `loom_model.guala_migration`,
`loom_model.lookup_grounding`, `loom_model.world_feeds`,
`loom_model.curriculum_scheduler` — none of which are the cognition
path (`binding_atlas`/`grandurun`/`brain`). The third alternative in
the regex (`from.*loom_model`) is too broad; it catches any submodule
import from the package, not just the cognition modules the test name
implies. This does **not** contradict the dormancy finding
(`LoomBrain`/`Embryo` still appear nowhere in `app.py`,
`substrate_runner.py`, or the v5 engine) — it's a stale assertion in
the test itself, not new evidence of live wiring.

---

## Plan v7 A2 carried item — F1/F2 status, file:line

**F1 (language krimelack positional phase offset gated out by no-reset)
— STANDS, unfixed, but the mechanism is more precisely: dead, not
gated.**
- `dsf_ai_service/loom_model/neuron.py:436` —
  `self._positional_phase_offset: float = 0.0` (comment: "ring position
  → krimelack phase"). This is the **only** assignment in the file —
  grepped exhaustively, no other write site exists.
- `neuron.py:487` and `:499` — the only two reads, both passed straight
  into `krimelack.transduce(..., phase_offset=self._positional_phase_offset,
  no_reset=True)`.
- `dsf_ai_service/v4/gualaloom_v4_krimelack_dna.py:377` —
  `LanguageKrimelack.transduce`'s `self.phase = float(phase_offset)`
  runs **unconditionally**, regardless of `no_reset` — so the offset
  isn't being gated out by the no-reset flag at the point I can see it.
  The practical effect is the same as "gated out" for a different
  reason: the value it's always given is `0.0`. Nothing in `neuron.py`
  ever assigns each neuron's actual ring position to
  `_positional_phase_offset`, so the mechanism is wired end-to-end but
  permanently inert. This is Q1's blocker in concrete form: no
  per-neuron positional signal reaches the krimelack today.

**F2 (Stage-3 sensory adapters instantiate fresh oscillator krimelacks
per transduce() call, stateless) — DOES NOT APPLY to either current
cognition-path observable. Looks fixed, or bypassed, depending on
which path.**
- `dsf_ai_service/loom_model/substrate_dna.py` — the "Stage-3" adapter
  classes (`TactileKrimelack` and siblings for smell/taste/visual/
  auditory) DO reset unconditionally inside `.transduce()` (e.g.
  `substrate_dna.py:98`, `self.reset()` at the top of the method,
  matching F2's description exactly) — but `.transduce()` is not what
  the cognition path calls.
- `substrate_dna.py:86-90` — the same classes expose `feed_signal()`,
  explicitly documented "Feed raw signal without reset (cognition
  path, GL-CMD-125)".
- `neuron.py:845-848` (`_unwrapped_deltas`, the event_count/rank_order
  observable's shared write+recall path) calls `krim.feed_signal(...)`
  on `self.krimelack_bank.get(m)` — the neuron's own persisted
  instance, no reset. Sensory state accumulates for this observable.
- `dsf_ai_service/loom_model/resonant_chi.py:39`
  (`spectral_features`, the production-default `resonant_spectral`
  path) doesn't reference any Krimelack/adapter object at all — pure
  array/spectral math on the raw signal, no oscillator state involved
  either way.
- I have not exhaustively enumerated every remaining caller of the
  adapters' `.transduce()` method outside the cognition path — it
  still exists in the file and may still be used elsewhere (e.g. non-
  cognition sensory delivery). Flagging that as the one open edge of
  this answer, not asserting it's fully dead code.

---

## Status

Ruling (2) complete: suite repaired, T5-T9 run fresh, STOP discipline
applied and resolved (still-degenerate, matches 6/22, not a new
finding), F1/F2 carried item answered with file:line. S2a (her actual
live recall, cold+taught, probe set + method to be declared and
committed before measuring) is separate, in progress, not in this
filing.
