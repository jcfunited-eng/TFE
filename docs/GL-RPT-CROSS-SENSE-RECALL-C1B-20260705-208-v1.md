# GL-RPT-CROSS-SENSE-RECALL-C1B-20260705-208-v1

doc_id: GL-RPT-CROSS-SENSE-RECALL-C1B-20260705-208-v1
From: c1b | To: Eve, Joe, c1a | Responds to:
`GL-CMD-CROSS-SENSE-RECALL-EVE-20260705-208-v1` (filed as -207,
renumbered on rebase — see that doc's numbering note).
Vehicle: `dsf_ai_service/loom_model/{resonant_chi,binding_atlas,neuron,brain}.py`
+ `tests/test_cognition_path.py`. Built and verified in an isolated
worktree (`c1b/cross-sense-recall-207`) — c1a had live uncommitted
edits in `gualaloom_v5_engine.py` (the `-205` root-cause fix) at build
time; this dispatch's scope never touches that file, zero collision.

## URGENT, READ BEFORE STARTING -207/WAVE-MEMORY (c1a, this is for you)

On rebase, found `GL-CMD-ORGANISM-WAVE-MEMORY-EVE-20260705-207-v1`
already on origin (Eve → c1a): it replaces `binding_atlas.py`'s entire
`BindingAtlas` (list-of-dict append log) with a wave-cell store. Its
own W2 accuracy gate lists `test_t7_cross_modal` as a STILL-ALLOWED
pre-existing failure — that dispatch was cut before this one landed,
so it doesn't know T7 is now a real, passing capability (0% → 100%/
100%/60-70% at 5/3/1 lanes), not a documented gap anymore.

**The wave-cell store MUST preserve per-lane matching or this
capability regresses silently** — your own gate wouldn't catch it,
since it still treats T7 failing as allowed. Concretely:
`BindingAtlas.record(concept, state_vec, tick)` now accepts EITHER a
flat 1-D array (grandurun/event_count, unchanged) OR a
`Dict[str, np.ndarray]` of per-modality lane sub-vectors
(resonant_spectral — production's default observable, `embryo.py:132`).
`recall_best()` branches on that: dict in → masked, lane-normalized
cosine over the intersection of query/binding lanes out (see
`_lane_match_score` in `binding_atlas.py`). If W1's wave-cell rewrite
keys cells only by a single fused chi per neuron (one cell store, one
address space per concept-occurrence), that fusion is exactly the bug
this dispatch just fixed — re-introduced one layer down. The wave-cell
KEY needs to preserve which LANE each cell was written from, and W2's
recall needs to mask to the query's present lanes the same way, or
gate T7 explicitly (not just "same 3 allowed") before calling W2 done.
Flagging this now, in writing, before you build — not after.

Also: `recall_fast()` (`brain.py`) now dispatches on `self.observable`
and has a `resonant_spectral` branch (`_recall_fast_resonant_spectral`)
that calls `neuron.encode_state()`/`binding_atlas.recall_best()`
directly, non-vectorized. If W1 changes what `encode_state()` returns
or what `binding_atlas.recall_best()` expects, that branch needs to
move in lockstep or recall_fast() breaks again (this file was crash-
on-every-call before this dispatch — see below — don't let history
repeat one layer down).

---

## Root cause, confirmed against the running (pre-fix) code

Reproduced Eve's numbers directly before touching anything:
`test_t7_cross_modal` measured **0.0% at a genuine 3-lane partial cue**,
**100.0% at "5 sensory"** (visual/auditory/tactile/olfactory/gustatory —
which is NOT a partial cue, it's the full array-valued signal; language
never contributes a lane either way, so this number was never evidence
partial cues worked). Root cause, in `resonant_chi.py`:
`spectral_features()` concatenates every PRESENT modality's spectrum into
ONE vector, then `neuron.encode_state()` projects that concatenation
through a matrix keyed by `(neuron_id, feat_dim)`. A partial cue has a
shorter concatenation than the full teach-time signal, so it gets
projected through a DIFFERENT, unrelated random matrix — landing in an
address space with no geometric relationship to where the concept was
taught. By construction, not by degree.

## The fix

`resonant_chi.lane_features()` (new): per-modality resonant spectrum kept
SEPARATE, never concatenated. `neuron.encode_state()`'s resonant_spectral
branch now projects each lane through its OWN per-(neuron_id, modality)
fixed matrix — a lane's shape depends only on `N_RECEPTORS`, never on
which other lanes are present — and returns `Dict[str, ndarray]` instead
of one flat vector. `BindingAtlas.record()`/`recall_best()` now handle
this dict form: recall does a MASKED, LANE-NORMALIZED cosine — averaged
per-lane cosine over the intersection of the query's present lanes and
each binding's present lanes — the same honest-absence convention `-191`
set at teach time (missing ≠ zero-filled noise), now applied at match
time too. The original flat-vector path (grandurun/event_count
observable) is completely untouched — verified byte-for-byte unchanged
behavior via `probe_177_end_to_end_parity.py` (15/15 parity at every
teaching depth, unaffected since that probe pins `observable="event_count"`
explicitly).

Measured after the fix (50 concepts, `test_t7_cross_modal`, stable
across repeated runs — `resonant_response`/`ternary_chi` have no RNG,
only `_build_multi_modal_signals`'s own signal generation is
hash()-salted per `GL-CMD-CAPACITY-PROBE-REPRODUCIBILITY`):
- 3-lane partial cue: **0.0% → 100.0%**
- single-lane (auditory only) cue: **100.0%** (not separately measured
  before the fix, since the old code had no honest single-lane case —
  a 1-modality query's concatenation is just that modality's own
  spectrum, so it hit the same wrong-projection-matrix bug) **→ measured
  60-70% across repeated runs post-fix** (real: less evidence than a
  3-lane cue among 50 concepts, chance is 2%). T7's floor set at 45% with
  margin below the observed range, not at it.
- 5-lane / language-only: unchanged (100% / 0% — language contributes no
  spectral lane by construction, a word string has no waveform; this
  was never the bug).

T10 (determinism) broke as a direct, expected consequence of the
representation change (`np.array_equal` can't compare the new dict
state_vec) — fixed the comparison to go lane-by-lane rather than loosen
what the test actually checks.

## Second bug, found live while building this, not in the dispatch

`brain.py`'s `recall_fast()` — the function `gualaloom_v5_engine.py`
actually calls at all 4 live organism-recall call sites — unconditionally
builds a grandurun R⁶ query vector and hands it to
`binding_atlas.recall_best()`, **regardless of `self.observable`**.
Production's `Embryo` defaults to `observable="resonant_spectral"`
(`embryo.py:132`), whose bindings are per-lane dicts / 128-dim ternary
chi — not R⁶. Reproduced directly against the untouched, pre-fix code:

```
brain.recall_fast({'language': 'bell'})
→ ValueError: matmul: ... size 6 is different from 128
```

This is not a squashed-but-present capability — it's a hard crash, on
every call, today. Of the 4 live call sites: 3
(`_association_from_organism`/candidate-recall seams and the fallback
association path) are wrapped in `try/except`, logging and returning an
"honest empty" — so cross-sense/word recall via those seams has been
silently returning nothing since `resonant_spectral` became the
default. The 4th, `_recognition_from_organism` (line 1840,
familiarity/surprise signal), has **no try/except at all** — that
`ValueError` propagates uncaught on every call.

Fixed by dispatching `recall_fast()` on `self.observable`: for
`resonant_spectral`, delegate to a new `_recall_fast_resonant_spectral()`
that calls the SAME `neuron.encode_state()` the write path
(`experience_moment`) uses — provably non-mutating (resonant_spectral
never touches krimelack state, unlike the event_count path, so no
snapshot/restore is needed) and therefore provably in parity with
`recall()` by construction, not by a separate proof. Verified: exact
`Counter` equality against `recall()` for both a language-only query
(the live organism's actual query shape) and an auditory-only query (the
shape a fixed live query path would need) — see new
`test_t13_recall_fast_resonant_spectral_parity`. The proven
event_count-vectorized branch (probe_177's scope) is untouched.

## Verification

- `test_cognition_path.py` (T1-T13): 11 passed, 2 failed
  (`test_t8_noise_robustness`, `test_t11_substrate_true`) — both
  confirmed pre-existing (same 2 of the session's documented 3 baseline
  failures; the third, T7, is the one this dispatch fixes).
- Rest of `loom_model/tests/` (`test_brain`, `test_neuron`,
  `test_cluster`, `test_contact_inhibition`, `test_couplings_carry`,
  `test_folding`, `test_folding_engaged`, `test_mosaic`,
  `test_substrate_dna`, `test_tapestry`): 78 passed, 2 failed
  (`test_folding_engaged.py::test_t3_corpus_growth`,
  `::test_t8_substrate_true`) — both reproduced identically against the
  UNTOUCHED pre-fix code (byte-for-byte same failure output), confirming
  pre-existing, unrelated to this change (folding/growth physics and a
  stale "no production imports" invariant, not cognition encoding).
- `probe_177_end_to_end_parity.py` (explicit `observable="event_count"`,
  the real `Embryo`/`_organism_signal` construction): 15/15 parity at
  every teaching depth, INV-1 pass — confirms zero regression to the
  path this dispatch doesn't touch. Its own INV-2 finding (0/30 changed)
  is `-191`'s already-documented, pre-existing language-only/event_count
  characteristic, unrelated to this fix.

## EXIT — what's outstanding, named plainly

Eve's dispatch names a live test as the exit condition: "bells
auditory-only cue... retrieved concept beats shuffled-cue chance;
seat-visible: the bound picture surfaces while the sound plays."
**Not yet built.** Checked before assuming it existed: today, live
recall queries (`_organism_signal`, all 4 call sites) are LANGUAGE-ONLY
by design (`-191`'s own N-item: "queries still ask 'what do you
associate with this word in general'... correctly stay language-only").
There is currently no live call path that queries with a sensory-only
signal at all — the fix above makes it POSSIBLE (recall_fast no longer
crashes and correctly does masked partial-cue matching for whatever
signal it's given), but nothing today constructs and sends that
sensory-only query live. Building the bells test needs a new query path
in `gualaloom_v5_engine.py` (or an atlas/organ hook that surfaces a
recalled picture from it) — that file has c1a's live uncommitted `-205`
root-cause fix in it right now. Sequencing that piece next: pull latest
origin, build in the same isolated-worktree pattern, avoid c1a's
coherence-gain/tick_rate hunks, deploy once verified — full cycle, not
deferred.

### Changelog
- v1 (2026-07-05, c1b): squash bug root-caused and fixed (per-lane
  binding + masked lane-normalized recall); second bug found live
  (recall_fast/resonant_spectral crash, 3 of 4 call sites silently
  swallowing it, 1 uncaught) and fixed in the same window; T7 rewritten
  to gate the real measured capability; T10's dict-comparison break
  fixed; T13 added (recall_fast/recall parity, permanent regression
  guard). Full local verification clean. Live bells test still open,
  named as the next piece, not silently dropped.
