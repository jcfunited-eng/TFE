# GL-RPT-BRAIN-STEP-CHI-DISPATCH-C1-20260707-v2

**doc_id:** GL-RPT-BRAIN-STEP-CHI-DISPATCH-C1-20260707-v2
**From:** c1
**Executing:** GL-CMD-BRAIN-STEP-CHI-DISPATCH-EVE-20260707-v2 (supersedes v1)
**To:** Eve (routing per dispatch instruction — no questions to Joe in this doc)

**HALT at protocol step 6 (learning verification) — the dispatch's own named
halt condition, confirmed empirically with an exact root cause, not just a
symptom.** Built exactly as specified across the files the real code
structure actually required (6, not 3 — details below), verified no crash
and no other-caller breakage, then ran the dispatch's own step-6 test
(same word, 10 iterations, track firing counts) **before touching
production**. The firing count does not decrease after iteration 1 — it
flatlines. Root cause found and demonstrated with concrete numbers: `input_chi`
and the values `chi_atlas.entries` are actually keyed by live on two
incompatible numeric scales that happen to share a name ("chi") but nothing
else. Not deployed. Production untouched. Code committed so the diagnosis
and the fix-in-waiting aren't lost.

---

## What was built

**Files touched: 6, not the dispatch's stated 3.** The extra three are
mechanical pass-throughs the actual call chain requires — not a scope
expansion I chose, a fact about the code:

1. **`dsf_ai_service/loom_model/cluster.py`** — as specified. Added
   `FAMILIARITY_THRESHOLD = 0.1` (module constant, untouched value).
   `LoomCluster.step` gained `input_chi: Optional[int] = None`. Phase A now
   selects `stepping_neurons = self._select_by_chi_familiarity(input_chi)`
   and only steps those. Phase B is **unchanged** in the sense that matters
   (still iterates every neuron, still checks every neighbor's `committed`
   flag) — its existing `.get(src_id, {}).get("committed")` pattern already
   defaults safely to "did not spike" for any neuron `results` no longer
   contains, so no structural edit was needed there. One necessary,
   minimal exception: a **dead, unused** line right above Phase B —
   `spiking_neurons = [n for n in self.neurons if results[n.neuron_id]["committed"]]`
   — used direct dict indexing that assumed every neuron has a `results`
   entry, true before this change (Phase A used to step everyone) and false
   after it. Left as-is it would `KeyError` on the first tick where any
   neuron doesn't step. Changed the indexing to `.get()`, mirroring the
   exact defensive pattern two lines below it. This is inert dead code
   (computed, never read) — the fix changes zero actual behavior, only
   prevents a crash my own Phase A change would otherwise introduce.
   Phase C now refreshes only `stepping_neurons`, per spec. Added
   `_select_by_chi_familiarity` exactly per spec: `None` → all neurons;
   else neurons with `chi_atlas.match_score(input_chi, "neuron") >
   FAMILIARITY_THRESHOLD`; if none, the 2 lowest-total-chi_atlas-entry-count
   neurons (novelty pool, size untouched).

2. **`dsf_ai_service/loom_model/brain.py`** — as specified. `LoomBrain.step`
   gained `input_chi`, passed through unchanged to each `hemi.step(...)`. No
   filtering at brain level.

3. **`dsf_ai_service/loom_model/hemisphere.py` — not in the dispatch's file
   list, but required.** `LoomBrain.step` does not call `cluster.step`
   directly — it calls `hemi.step(input_signal, tick)`
   (`LoomHemisphere.step`), which is the actual, only layer between brain
   and cluster (confirmed by reading it — no further layers). Threading
   `input_chi` from brain to cluster is impossible without this file. Pure
   pass-through, one line changed, no new logic.

4. **Upstream callers — the dispatch names `experience_word`, "sensory
   delivery", and `_process_sensory_work`.** Investigated all three
   directly against the real code before writing anything:
   - **`experience_word`** (`dsf_ai_service/loom_model/embryo.py`) is real,
     but never calls `brain.step` — its actual chain is `experience_word` →
     `_experience_core` → `_feed_and_fold`, and `_feed_and_fold` calls
     `hemi.cluster.step(...)` **directly**, two layers below where the
     dispatch's own text implies. Added `_compute_input_chi(signal)` (new
     helper on `Embryo`) and call it once per `_feed_and_fold` invocation
     (before its ticks loop, not per-tick), threading the result into every
     `hemi.cluster.step(...)` call inside that loop.
   - **"Sensory delivery"** — two candidates exist under that description.
     `ExperiencePipeline.deliver_word` (`experience.py`) matches the phrase
     and does call `brain.step`, but it's test/demo-only scaffolding, never
     instantiated in production. The live path is
     `push_wave_summary_to_organism` (`wave_summary.py`) →
     `Guala._enqueue_organism_sensory` → `_organism_worker_loop`'s sensory
     branch → `hemi.step(...)` directly (one layer below `brain.step`, not
     through it). Wired `input_chi` through all three of those: reused the
     highest-strength chi already sitting in `top_chis` (computed once,
     nothing re-derived) rather than calling anything fresh.
   - **`_process_sensory_work`** does not exist anywhere in the repo, under
     any name, in any file, on any branch checked out locally — confirmed
     by direct grep across the full tree including worktrees. Not invented;
     the two live callers above are the actual "callers that generate
     input_signal" this codebase has.

## Where `input_chi` actually comes from

`_compute_input_chi` (new, `embryo.py`) uses
`dsf_ai_service/substrate/krimelack.py`'s `Krimelack` class — confirmed to
be the same module `event_stream_to_vector` (the literal "shared krimelack
that already produces phase_vec for wave atlas") lives in, so "the shared
krimelack" is this module, not a bespoke mechanism. `feed_signal()` +
`winding % 100` matches the exact convention `sensory_generators.
transduce_sensory_signals` already uses elsewhere in this codebase for
turning a raw signal into a chi int. Returns `None` (not a fabricated 0) on
an empty/all-zero signal, so the existing backward-compat fallback handles
it rather than inventing a chi for no real input.

## Correctness / no-crash verification

Syntax-checked all 6 files (clean). Grepped every call site of the four
modified signatures (`LoomBrain.step`, `LoomHemisphere.step`,
`LoomCluster.step`, `_enqueue_organism_sensory`) across the whole repo:
every other caller (test files, `mosaic.py`, the dead `experience.py`
scaffolding) calls with the old argument count — since `input_chi` is
`Optional[...] = None` throughout, none of them break. Ran a real `Embryo`
(8 hemispheres) through `experience_word` repeatedly with no exceptions —
matches "None fallback preserved" and "no crash" directly, not just by
code inspection.

## Learning verification (protocol step 6) — this is where it halts

Ran the dispatch's own test locally, before any deploy: same word, 10
iterations, tracked total stepping-neuron count per iteration (summed
across all `cluster.step` calls that one `experience_word` call makes,
across the em→cascade→gp organ sequence):

| Iteration | Stepping-neuron count |
|---|---|
| 1 | 83 |
| 2 | 72 |
| 3 | 72 |
| 4 | 72 |
| 5 | 72 |
| 6 | 72 |
| 7 | 72 |
| 8 | 72 |
| 9 | 72 |
| 10 | 72 |

One drop after iteration 1 (likely an early-organ-activation artifact, not
familiarity), then **completely flat**. Nowhere near the dispatch's own
expectation ("novelty pool ~16 neurons total" at iteration 1, "familiar-only
~1-2 neurons total" by iteration 5+). This is the dispatch's own named halt
condition #2, confirmed directly, not inferred.

**Root cause, demonstrated with concrete numbers, not just theorized:**
`chi_atlas.entries` (`gualaloom_v4_chi_atlas_l6.py`) is written exclusively
by `LoomNeuron.step` (`neuron.py:619`) with `dominant_mode = int(np.argmax(
psi_lattice.probabilities()))` — an index into a `PSI_DIM = 16`-sized
array, so entries live at small integers `0-15`, replicated across
`CHI_BAND = 2` on each side. `input_chi` (`_compute_input_chi`, per this
dispatch's own instruction to use "the shared krimelack") is a
`Krimelack().winding % 100` value — a completely different, unrelated
numeric space. Direct test on a real neuron after 3 real `experience_word`
calls on the same word: `input_chi = 17`; that neuron's own
`chi_atlas.entries` keys were `[4, 5, 6, 7, 8]` (its `dominant_mode = 6`, ±2
band); `match_score(17, "neuron") = 0.0`; `match_score(6, "neuron") = 0.5`
for direct comparison — the neuron genuinely *has* built familiarity with
its own repeated dominant mode, but `input_chi` as specified can never see
it, because it's drawn from a different, unrelated 0-99-ish space that only
overlaps the 0-15 `dominant_mode` space by chance. This isn't a bug in this
implementation — the wiring is exactly what was specified, using the exact
krimelack module named. It's a pre-existing, genuine mismatch between two
different "chi" concepts that already coexist in this codebase
(`LoomNeuron.step` itself computes both: `chi = abs(self.krimelack.winding)`
at neuron.py:585 for map-injection, *and* `dominant_mode` for chi_atlas
recording — two different values, never reconciled, both just called
"chi").

## Why this halts here rather than being patched in-flight

`FAMILIARITY_THRESHOLD` and novelty pool size are explicitly protected
("DO NOT: Tune"), and `match_score` semantics are explicitly protected
("DO NOT: Change"). The actual fix here is neither of those — it's a
decision about which chi space `input_chi` and `chi_atlas.entries` should
share (make `input_chi` land in the `dominant_mode`/PSI_DIM space instead
of the krimelack/wave-atlas space, or start recording chi_atlas entries in
the krimelack space instead of `dominant_mode`, or something else entirely)
— a real design call with real tradeoffs for other consumers of
`dominant_mode`/`chi_atlas` (e.g. `_last_commit_chi` feeds `MapInject` and
`familiarity.update` elsewhere in `neuron.step`), squarely the kind of
decision this session's standing practice reserves for Eve, not mine to
make unilaterally under "route to Eve."

## Contention measurement — not run

Skipped per the dispatch's own protocol ordering: contention measurement
is listed alongside the harness runs (steps 2-4, after backup, before
learning verification closes the loop), but given a confirmed halt
condition at step 6, deploying to production to gather step-3/4/contention
data would mean shipping code already known to not do what it's for. Not
done, not needed to make this call.

## Backup / baseline harness — not run

Per this session's established pattern for a confirmed halt (matching
wave-atlas-decay v1/v2, sensory-organism-queue): the local, non-production
verification already available was sufficient to confirm the named halt
condition before any production-touching step. No backup was taken because
nothing was deployed; no baseline/post-deploy harness comparison was run
because there is no "post-deploy" — production never changed.

## Recommendation

Not a rejection of the mechanism's goal (this session's whole thread
tonight — the two C-port investigations and the no-GIL test — has been
converging on "fewer neurons doing work per input" as a real, worthwhile
direction). The filtering logic itself, novelty-pool fallback, and Phase
B/C interaction are all correctly built and crash-free. What's missing is
a decision on chi-space reconciliation before this can actually deliver
the learning curve it's meant to. Worth a fast, narrowly-scoped follow-up
dispatch once Eve decides which chi space should be canonical — the rest
of this implementation (all 6 files) shouldn't need to change, only the
one line inside `_compute_input_chi` that decides what number to return.

## Scope compliance

`FAMILIARITY_THRESHOLD` (0.1) and novelty pool size (2) untouched.
`match_score` semantics untouched. Phase B/C structure untouched beyond
the one dead-code crash-prevention fix, documented above. None fallback
preserved and verified (every non-`input_chi`-aware caller still works).
No hemisphere-modality routing added. No production deploy attempted.

---

### Changelog
- v2 (2026-07-07, c1): Built across the 6 files the real call chain
  requires (3 named + 3 necessary pass-throughs). No crash, no other-caller
  breakage, backward compat verified. Halted at the dispatch's own named
  learning-verification condition: firing count flatlines instead of
  converging, root-caused with concrete numbers to a genuine scale mismatch
  between krimelack-derived `input_chi` and the `dominant_mode`-keyed
  `chi_atlas.entries` it's compared against. Not deployed; code committed
  for the diagnosis and as a base for a future, correctly-scoped fix.
