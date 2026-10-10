# GL-RPT-C2-REBUILD-C1-20260704-168-v1

doc_id: GL-RPT-C2-REBUILD-C1-20260704-168-v1
From: c1a | To: Eve, Joe
Responds to: GL-CMD-C2-REBUILD-EVE-20260704-168-v2 (v1 RETAINED, not executed).
Vehicle: model/harness only, as instructed. Zero live-path changes.

**Part A did not reproduce. Filing now and stopping, per G-168-1 and the
CMD's own instruction ("Any large deviation → STOP, report, Eve re-rules").
Part B (B1–B5) was not started — there is no baseline to measure additions
against yet.**

---

## Failures first

**1. Fresh measurement of the "standing champion" (event_count observable)
gives ~4% accuracy, not ~67%.** Ran the on-origin loom suite's own T5
methodology (`test_cognition_path.py::test_t5_brain_25`'s exact teach/query
loop: 3 reps, `brain.recall()`, synthetic `concept_NN` labels) with
`LoomBrain(..., observable="event_count")` explicit — the only way to get
event_count today, since a later "capacity solve" commit made
`resonant_spectral` the default (`brain.py:53`). Confirmed
`neuron.observable == "event_count"` on every neuron before measuring.

```
event_count, synthetic concepts, n=25: 4/100 = 4.0%   (perturbation-loop query, matches test_t5's own protocol)
event_count, real-word (STEMS) corpus, n=25, single query: 1/25 = 4.0%
```
Both corpora agree: ~4%, near chance for n=25 (chance ≈ 1/25 = 4.0%). This
is not a marginal miss of "~67% within noise" — it is a collapse to
no-discrimination. Per G-168-1 ("Part A baseline reproduced before any Part
B commit") and the CMD's own STOP instruction, B1–B5 are not attempted.

**2. The literal requested cell (n=100, 64 neurons) could not be safely
completed.** I started it in the background; at ~2 minutes it had already
grown to 7.6GB resident and was still climbing, with no sign of finishing.
I killed it rather than risk the shared machine (see Failure 4 below for
the confirmed cause — an unbounded list, not a slow-but-finite computation).
So the exact "T5 @ 100×64" number the CMD asks for is **NOT MEASURED**,
cause stated, not inferred from the n=25 result.

**3. Root cause, confirmed by direct inspection — three independent,
pre-existing defects in the on-origin `event_count` path, none introduced
by me this session (see Gate G-168-6: `git status --short` shows zero
production files touched):**

**BUG 1 — three of six modality dimensions are permanently zero.**
`TactileKrimelack`, `OlfactoryKrimelack`, `GustatoryKrimelack`
(`dsf_ai_service/loom_model/substrate_dna.py:79-80, 136-137, 187-188`) all
define `n_events` as `self._inner.n_events if hasattr(self._inner,
'n_events') else 0`. Their backing class, `OscillatorKrimelack`
(`dsf_ai_service/sensory_krimelacks.py:24-60`), never defines `.n_events` —
only `.events` (a list) and `.winding` (a signed int). So the `hasattr`
check always fails and these three adapters report `n_events == 0` forever,
regardless of how much real activity occurred. Demonstrated directly:
```
k = TactileKrimelack(); k.feed_signal([0.9]*200)
k.n_events            -> 0
len(k.events)          -> 550
len(k._inner.events)   -> 550
k._inner.winding       -> 550
hasattr(k._inner, 'n_events') -> False
```
550 real winding events occurred; the observable that `_unwrapped_deltas`
(`neuron.py:846,858`) actually reads (`krim.n_events`) reports zero. This
silently zeroes tactile/olfactory/gustatory for every neuron, every query,
in production — confirmed in the stored state vectors below (visual,
auditory, language nonzero; tactile, olfactory, gustatory always exactly
0.0 across 15 bindings, 5 concepts × 3 reps):
```
concept_00 [   4. 1125.    0.    0.    0.   36.]   (visual, auditory, tactile, olfactory, gustatory, language)
concept_01 [   8. 1424.    0.    0.    0.   36.]
...
```

**BUG 2 — `brain.recall()`'s "must not pollute training" guarantee does not
hold for this observable.** `LoomBrain.recall()` (`brain.py:190-213`)
snapshots and restores each neuron's krimelack `.phase`/`.winding` around
the query specifically so recall doesn't corrupt future recall or training.
It does **not** snapshot/restore `.n_events` or the underlying `.events`
list. Demonstrated: querying the identical word three times in a row with
**zero teaching in between** produces three different deltas:
```
d1 {'visual': 4.0,  'auditory': 1125.0, ...}
d2 {'visual': 9.0,  'auditory': 1125.0, ...}
d3 {'visual': 13.0, 'auditory': 1125.0, ...}
```
Visual climbs every time it is merely *asked about* — the "read" is not
read-only. Every recall call in a measurement run leaves state behind that
contaminates the next one, on top of Bug 1's dead dimensions.

**BUG 3 — the sensory adapters' event lists are unbounded.** GL-CMD-138 put
a bounded `deque(maxlen=1024)` on the *language* krimelack specifically
because unbounded accumulation under no-reset teaching was already a known
risk (comment at `sweep_137_scaling_probe.py:84-90`). That fix was never
extended to the touch/smell/taste adapters — `OscillatorKrimelack.events`
(`sensory_krimelacks.py:38`) is a plain list. Demonstrated: 20 feeds of 200
samples each (one neuron, one modality) produced 6111 stored event dicts,
still growing linearly, no cap. At 100 concepts × 3 reps × 64 neurons × 3
affected modalities this is what drove the n=100 run to 7.6GB in two
minutes (Failure 2) — a real memory/performance risk independent of Bug 1's
correctness problem, and the reason I couldn't just "let it finish slower."

**4. The champion's own historical validation harness is itself stale and
does not run today.** `sweep_137_scaling_probe.py` — the file neuron.py's
own docstring (`neuron.py:817-819`) cites as the source of "67% T5 at
n=100," and which GL-CMD-140 says was "ported verbatim" into production —
crashes if you simply run it unmodified against today's origin:
```
ValueError: matmul: Input operand 1 has a mismatch in its core dimension 0,
(size 6 is different from 128)
```
Cause: its own `LoomBrain(...)` call passes no `observable` argument, so it
now silently gets the current default (`resonant_spectral`, added by a
later "capacity solve" commit) instead of the `event_count` it was written
to force via its `_unwrapped_deltas` monkeypatch. `encode_state()` never
calls `_unwrapped_deltas` on the resonant_spectral branch, so the
monkeypatch is dead code today, and the probe's own diagnostic section
(which does call `_unwrapped_deltas` directly to build a 6-dim query
vector) collides with a 128-dim resonant atlas. **Nobody has actually
re-run this harness successfully since the default moved away from
event_count** — the "~67% T5 @ 100×64 VALIDATED" ground-truth line in the
CMD is a claim from June 23, never re-checked against the code as it exists
today, and the code has moved (GL-CMD-138's `n_events` switch, at minimum)
since then without a passing re-validation.

---

## What I ruled out (my own harness is not the explanation)

- Cross-checked my teach/recall loop against the actual, unmodified
  `test_cognition_path.py::test_t5_brain_25` — ran it via pytest with no
  changes: `100/100 = 100.0%` (its default, `resonant_spectral`). My
  harness reproduces that number exactly when I don't override the
  observable, so the pipeline/brain/recall wiring in my script is sound;
  the divergence is specifically the `event_count` path.
- Confirmed `LoomBrain(brain_seed=42, observable="event_count")` correctly
  sets `neuron.observable == "event_count"` on every neuron (constructor
  arg wins per `brain.py`'s own documented precedence) before measuring
  anything, so this is not a routing mistake on my part.
- Tried both a real-word corpus (`sweep_137`'s own `STEMS`/`generate_concepts`)
  and the exact synthetic-label corpus `test_t5_brain_25` uses — same ~4%
  result either way, so it isn't a corpus-choice artifact.

---

## Gates

- **G-168-1** (Part A baseline reproduced before any Part B commit): **NOT
  SATISFIED.** Correctly gates off B1–B5 — none attempted.
- **G-168-2** (STOP if degraded-cue score >95%): N/A — opposite problem,
  scores are far too low, not suspiciously high.
- **G-168-3** (no RNG in neuron identity): honored. No RNG touched neuron
  identity anywhere in this session's diagnostics; `rebuild_168.py` (below)
  scaffolds cue-noise-only RNG helpers for the B-parts but they were never
  exercised, since B-parts are correctly gated off.
- **G-168-4** (exp(1j·Δ) binding prohibited): honored, and independently
  verified irrelevant to this failure — `grandurun.py:1-25`'s
  `grandurun_state` is a real R⁶ vector (`STATE_DIM=6`, no complex
  exponential anywhere in the file); the champion's own representation was
  never the prohibited encoding, so this collapse is unrelated to the 6/22
  arc's dead encoding.
- **G-168-5** (one addition per run, same table format): N/A, Part B not
  started.
- **G-168-6** (diff proves scope: model/harness only): confirmed —
  `git status --short` at time of writing shows zero modifications to any
  file under `dsf_ai_service/loom_model/` or `dsf_ai_service/v4/`. The only
  new files are this report, the harness below, and two files this report
  cites (`docs/c2_model_v1.py`, `docs/c2_model_v2.py` — Eve's testbed,
  already referenced by `GL-RPT-C2-Q1-POPULATION-VALIDATED-EVE-20260704-v1`
  but not yet on origin; filed alongside this report for durability so the
  citations above are checkable from origin, not just my working tree).

---

## Harness filed

`dsf_ai_service/loom_model/tests/rebuild_168.py` — Part A runner
(`part_a()`, the exact measurement quoted in Failure 1) plus scaffolding
for the B1 degraded-cue population table (`_degrade_signals`,
`_per_neuron_predict`, `_population_table`) that this report does **not**
use, since B1 depends on a baseline that doesn't hold yet. Left in place,
committed, so whoever re-scopes this doesn't start from zero.

---

## Recommendation (not mine to decide)

Two different repairs are tangled together here and only Eve/Joe can pick:

1. **Fix the three bugs above and re-run Part A.** This is production
   `loom_model` code (`substrate_dna.py`, `sensory_krimelacks.py`,
   `brain.py`'s `recall()`), not model/harness work — outside this CMD's
   own vehicle ("model/harness only"). Would need its own dispatch.
2. **Retract or downgrade the "standing champion" claim** and re-scope the
   rebuild around whatever representation Eve/Joe actually want compared
   against — `resonant_spectral` (today's real default, itself already
   flagged by the 6/22 audit as degenerate/unanimous) or Eve's own toy-model
   mechanism ported directly, bypassing this broken observable rather than
   repairing it first.

Filing plainly rather than picking one myself, since "no results-tuned
constants" cuts both ways: I'm not going to quietly patch the bugs to make
Part A pass and call that a rebuild, and I'm not going to guess which repair
Eve wants funded before B-work resumes.

---

## Status

Filed, not FILED-on-origin until pushed (doing that now, alongside
`docs/c2_model_v1.py`, `docs/c2_model_v2.py`, and
`dsf_ai_service/loom_model/tests/rebuild_168.py`). Part A: **STOP, as
measured.** Part B1–B5: **NOT STARTED**, correctly gated by G-168-1.
