# GL-RPT-SENSE-REPAIR-C1-20260704-v1

doc_id: GL-RPT-SENSE-REPAIR-C1-20260704-v1
From: c1a | To: Eve, Joe
Responds to: Joe's direct dispatch, 2026-07-04 ("SENSE REPAIR, prerequisite
to the whole-brain run... model module only, zero live-path changes"),
itself Eve's ruling on Option 1 of GL-RPT-C2-REBUILD-C1-20260704-168-v1.
Follow-up dispatch ("one gate before filing... too-good protocol") answered
inline below, not as a separate report.
Vehicle: model module only (`dsf_ai_service/loom_model/`,
`dsf_ai_service/sensory_krimelacks.py`). Zero live-path changes — verified,
with one nuance stated plainly in Gate 6.

**All 4 items shipped and independently re-verified by a separate
adversarial workflow that did not see my own test runs and tried to break
each fix. All gates the dispatch named: PASS. One additional gate the
dispatch asked for after seeing this go strong — the too-good check on the
95% cell — is answered in full below, and it is NOT clean: real but narrow
population disagreement, not a hash artifact, but overstated by the
headline number. Filing that plainly rather than only reporting the win.**

---

## Failures first

**1. The too-good check Joe asked for, before anything else: the 95% cell
is real but its disagreement is thin — 8 distinct voter types, not 64.**
Per-neuron instrumentation (`_per_neuron_predict`/direct argmax per neuron,
not the aggregate `brain.recall()` Counter) on the exact n=25 synthetic-
concept cell that scored 95%:

```
total queries: 100 (25 concepts × 4 draws)
plurality (brain.recall-equivalent) accuracy: 95/100 = 95.0%
unanimity rate: 92/100 = 92.0%
per-neuron accuracy: mean=94.0% best=96.0% worst=88.0% std=2.7pp
distinct per-neuron accuracy values: {88.0, 92.0, 93.0, 95.0, 96.0} — exactly
  8 neurons at each level (8 groups × 8 hemispheres = 64)
```

**92% unanimity is high** — in 92 of 100 queries every one of the 64
neurons voted identically. That is much closer to the 6/22 audit's
"degenerate population" pattern than to Eve's own testbed's "population
beats best single neuron" pattern (which showed unanimity near 0). It is
**not** a hash bug in the sense G-168-2 warns about (I did not find a
constant, or a single query short-circuiting every neuron to the same
wrong shortcut — see below), and it is not literally >95%, so it does not
trip that STOP as written. But it is not "real 64-way population
disagreement" either. The actual structure: `signal_attenuation(ring_pos,
ring_N, modality_index)` (`neuron.py:74-85`) is computed per-HEMISPHERE
ring position, and `ring_N=8` (`cluster.py:105`, `SEED_SIZE_PER_HEMISPHERE=
8`) — so there are only 8 distinct attenuation profiles across the 64
neurons, each replicated 8× (once per hemisphere). Plurality voting (95%)
is not even beating the single best voter-type (96%) here — it's just
diluted slightly by the worst voter-type (88%) in the 8% of queries where
neurons disagree. **This is not new** — it is exactly the "~7 distinct
voters" ceiling the CMD's own ground truth section and Eve's testbed
already named, now confirmed on the real (not toy) substrate. For contrast,
I also ran the literal n=100/64-neuron cell requested by -168 (72%
accuracy): unanimity there is lower (61%), per-neuron spread wider
(58%–96%→80% max, std=7.3pp), and plurality (72%) clears the worst
voter-type (58%) by 14pp — a healthier, if still only-8-distinct-voter-type,
disagreement pattern. **Conclusion: the sense-repair fix itself is real
(verified independently, below) — the underlying population code's
diversity is genuinely thin (8 effective voters, not 64), which is a
substrate fact this fix exposes rather than one it introduces or hides.**
This is exactly what -168's own Part B4 ("real-state voter diversity vs N")
was written to interrogate, and it's now interrogable on real numbers
instead of a broken observable.

**2. A newly-discovered, NOT-fixed, out-of-scope bug: the "language"
modality dimension still saturates to zero after ~4 words, for a different
reason than the three sensory adapters.** `LanguageKrimelack`
(`dsf_ai_service/v4/gualaloom_v4_krimelack_dna.py`) has **no `n_events`
attribute at all** — a completely separate class hierarchy from
`OscillatorKrimelack`, unaffected by this dispatch's fix. `_unwrapped_deltas`
falls back to `len(krim.events)` for language, and `.events` is a
`deque(maxlen=256)` (`Krimelack.reset()`, same file). Because `deliver_word()`
feeds the language krimelack twice per word (once via `step()`, once via
`experience_moment`), the deque saturates within ~3-4 taught words, after
which `len()` stays pinned and the per-delivery delta collapses to 0 —
confirmed directly: `state_vec[5]` (language) reads 36, 36, 36, 4, 0, 0, 0...
even post-fix, at n=10. **Not fixed here** — the dispatch named "the three
sensory adapters" specifically, and this is a distinct class with no
shared code path to the fix. Flagging it because it means the current 72%
(n=100) / 95% (n=25) numbers are being carried almost entirely by
visual+auditory+tactile+olfactory+gustatory, with language contributing
real signal only for the first handful of words in any teaching run — worth
its own dispatch if Eve wants it closed before the whole-brain run.

**3. The diff/scope reviewer's own two findings, both addressed:**
- **Closed**: `brain.py`'s restore only touched the sensory adapters'
  `._inner` oscillator, never the adapter's OWN mirrored `.events`/`.winding`
  attributes (set in `feed_signal()`). Currently inert (only reader is the
  rejected `rank_order` branch, which re-syncs before reading anyway) but a
  real asymmetry against "reads are truly read-only." Extended the
  snapshot/restore to cover it — see Gate 3 below, re-verified after.
- **Closed**: a pre-existing, never-my-comment claim inside
  `sweep_137_scaling_probe.py`'s monkeypatch said the deque bound was
  "maxlen=1024." The real number (both before and after this fix) is 256.
  Fixed the stale figure since I was already touching this file for the
  same repair.
- **Not closed, flagged for the record**: `dsf_ai_service/organ_brain_service.py`
  is a separately-deployed, genuinely live process (port 8090, its own
  process, reached by `substrate_runner.py` only over HTTP — never
  Python-imported, so outside this dispatch's literal "app.py/
  substrate_runner.py import graph" scope) that DOES import `embryo.py` →
  `brain.py` (`LoomBrain`) and `substrate_dna.py`, instantiating every
  `KRIMELACK_PRIMITIVES` type. It is safe from this diff **today** only
  because `Embryo()` hardcodes `observable="resonant_spectral"` (bypasses
  `krimelack_bank` entirely) and `loom_voice.py` only ever calls the
  untouched `Embryo.recall_op()`, never `Embryo.recall()` (which wraps the
  modified `LoomBrain.recall()`). That is **config-dependent inertness, not
  structural non-reachability** — a future change to that service (passing
  `observable="event_count"`, or a non-language `hemisphere_primary_modality`)
  would make this diff's changed code live-executing there without anyone
  touching this diff again. Not something I fixed or should fix under this
  dispatch's vehicle — recording it so nobody is surprised later.

---

## The four fixes, as dispatched

**(1) n_events on the three sensory adapters.** Root cause was one level
deeper than the adapters themselves: `TactileKrimelack`/`OlfactoryKrimelack`/
`GustatoryKrimelack` (`substrate_dna.py`) all correctly delegate
`n_events` to `self._inner.n_events` — but `self._inner` is
`OscillatorKrimelack` (`sensory_krimelacks.py`), which never defined
`n_events` at all. Fixed at the source: `OscillatorKrimelack` now sets
`self.n_events = 0` once in `__init__` (before `reset()`, so it survives
resets exactly as the existing code comments already assumed) and
increments it on every winding transition in `step()`. The three adapters
needed zero changes — their existing delegation now resolves correctly.

**(2) Bound their event lists like -138 bounded language.** Also fixed at
`OscillatorKrimelack`: `.events` is now `deque(maxlen=256)`. Note: the
dispatch said "maxlen 1024" — the actual, current value in the language
path (`gualaloom_v4_krimelack_dna.py`'s `_EVENTS_MAXLEN`) is **256**, not
1024 (that figure traces to a stale comment in `sweep_137_scaling_probe.py`,
itself fixed under item 4 below). Matched 256 exactly rather than
introducing a second, different bound — flagging the discrepancy rather
than silently picking one number.

**(3) `brain.recall()` truly read-only.** `LoomBrain.recall()` now
snapshots and restores `phase`, `t`, `winding`, `n_events`, and `events` —
not just `phase`/`winding` as before — around each neuron's query, for
both the real state-holder (`krim._inner` for adapters, `krim` itself for
`LanguageKrimelack`/`VisualKrimelack`/`CochlearBankKrimelack`) and, after
the reviewer's finding, the adapter's own mirrored copy too. Required
adding `@n_events.setter` to `VisualKrimelack`/`CochlearBankKrimelack`
(`substrate_dna.py`) — their `n_events` was read-only, which the restore
now needs to write.

**(4) The stale June harness: repaired, not retired.** Root cause:
`sweep_137_scaling_probe.py`'s own `LoomBrain(...)` call passes no
`observable` arg, so it silently picked up whatever the current default is
— which moved to `resonant_spectral` sometime after this probe was
written (a later "capacity solve" commit). Its own `_unwrapped_deltas`
monkeypatch became dead code as a result (`encode_state()` never reaches
it under resonant_spectral), and its diagnostic section crashed on a
dimension mismatch. Fixed with one explicit arg
(`observable="event_count"`) plus a comment explaining why it's required,
so this doesn't silently rot again. Chose repair over retirement: the
monkeypatch still has genuine value the native path lacks (the `mask`
parameter, used for single-channel isolation testing in axis C).

---

## Gate results — independently re-verified, not self-graded

After implementing, I ran my own checks, then spawned a separate
adversarial verification workflow (5 agents, no shared context with my own
test runs, explicitly told not to trust my claims and to try to break each
one) before filing. All results below are the **independent** re-runs.

**Gate: Bug-1 demo (n_events real, not 0).** PASS for all three adapters —
not just Tactile (the originally-cited case). `n_events` now equals
`winding` exactly for each: Tactile 550/550, Olfactory 631/631, Gustatory
618/618 (different absolute counts because each modality has its own
`omega_0`/`kappa` tuning in `MODAL_TUNING` — expected). `len(events)`
correctly capped at 256. Deterministic across repeated runs.

**Gate: triple-identical-query stability.** PASS, and the verifier went
further than the original repro: 10 consecutive identical queries stay
identical; interleaving different words produces stable per-word results
with zero cross-contamination; both `resonant_spectral` (default) and
`rank_order` (opt-in) stay stable too; interleaving `recall()` with new
*training* leaves both the new and original concepts' recall reproducible.
A full phase/t/winding/n_events/events snapshot diff across 5 recall calls
showed **0 diffs post-fix**. To confirm the test itself was sensitive (not
vacuously passing), the verifier re-ran the identical diff test against
the pre-fix code via `git stash`: **384 state diffs**, and the repeated
"identical" query actually returned a **wrong answer** (`concept_04`
instead of `concept_00`) — proof the bug was real, not hypothetical.

**Gate: n=100 completes in bounded memory.** PASS. Completed in 63.5s
(teach 47.8s + recall 15.7s), peak RSS **0.088GB**, polled independently
every ~18s — nowhere near the pre-fix 7.6GB-and-climbing, and nowhere near
even a generous 1GB sanity bound. T5 accuracy printed: 72.0% (reported by
the verifier as a fact, not a value judgment — see Failure 1 for the
honest read on what that number means).

**Gate: no regressions.** PASS. Independently ran the full 12-test
`test_cognition_path.py` suite with the diff in place (nothing stashed):
9 passed, 3 failed — and the failing set is **exactly** `test_t7_cross_modal`,
`test_t8_noise_robustness`, `test_t11_substrate_true`, matching what I'd
already confirmed pre-existing on unmodified origin via `git stash` earlier
in this same investigation. No new failures, no fewer.

**Gate: diff scope (model module only, zero live-path changes).**
`live_path_clean: true` from the independent reviewer, with the two
nuances already folded into Failures 2-3 above (the `loom_model/__init__.py`
partial-import detail is pre-existing and inert; `organ_brain_service.py`
is config-dependent-safe, not structurally unreachable). No crash paths
found across any of the 6 `KRIMELACK_PRIMITIVES` types for the new restore
logic. `deque(maxlen=256)` doesn't break any real caller — every
consumption site converts via `list()`/`.copy()` before indexing.

---

## Status

Committing and pushing now: `dsf_ai_service/sensory_krimelacks.py`,
`dsf_ai_service/loom_model/substrate_dna.py`,
`dsf_ai_service/loom_model/brain.py`,
`dsf_ai_service/loom_model/tests/sweep_137_scaling_probe.py`, and this
report. Live path: unaffected (Gate 6, with the `organ_brain_service.py`
caveat recorded above for whoever touches that service next). Open,
unauthorized item for Eve's future ruling: language-dimension saturation
(Failure 2) — a real, distinct bug, not fixed here.

Per Joe's hand-off: 168-v3 (whole-brain command) is next, held by Joe.
Not starting it until it arrives.
