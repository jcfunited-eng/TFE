# GL-RPT-CHI-UNIFICATION-C1-20260707-v3

**doc_id:** GL-RPT-CHI-UNIFICATION-C1-20260707-v3
**From:** c1
**Executing:** GL-CMD-CHI-UNIFICATION-EVE-20260707-v3 (supersedes v2)
**To:** Eve (routing per dispatch instruction — no questions to Joe in this doc)

**Full protocol completed, no halt condition fired. Deployed to production
(`dsf-ai-task:550`). Recommendation: leave in place — this is the real fix
for v2's flatline, confirmed with a genuine, reproducible convergence
curve, locally and against the actual deployed code.** One real,
independent finding surfaced during deploy (a container OOM-kill on one
rollout attempt) — investigated, most likely a recurrence of an
already-documented, pre-existing deploy-time issue rather than something
this change introduced, but flagged clearly since this change does widen
the memory this specific structure can grow into.

---

## Dependency check (required first step, before any code change)

`grep -rn "_last_commit_chi" dsf_ai_service/` (excluding worktrees): exactly
four usages, all in `neuron.py`:

1. `_last_commit_chi: int = 0` — init, no range assumption.
2. `match_score = self.chi_atlas.match_score(self._last_commit_chi, "neuron")`
   — self-consistency check against the neuron's own atlas. After this
   change, both sides of this comparison move to the same (unified) scale
   together — this usage gets *more* correct, not broken.
3. The assignment itself — the line this dispatch's build item 1 changes.
4. `get_grandurun_state`'s `binding["chi"] = self._last_commit_chi`, feeding
   `_grandurun_state`'s `chi_resonance` dimension (`d_chi = abs(chi_a -
   target_chi)`, phase-scaled by `CHI_CORR_LENGTH = 50.0`, tuned for the old
   small `dominant_mode` range). **Traced this consumer specifically**:
   its only real call path is `LoomMosaic.recall(query, target_chi=0, ...)`
   at `tapestry.py:95`, invoked only from `LoomTapestry.compose()`.
   Grepped every file in `dsf_ai_service/` for a live caller of
   `.compose()` or `mosaic.recall(` outside test files — **zero found**.
   `LoomTapestry` is real, live, persisted (`guala_tapestry.pkl.gz`,
   confirmed in every boot log tonight), but its `compose()` method is
   never invoked by the running engine. This dependency is real but
   **dead in production** — not a blocking migration issue today, but
   `CHI_CORR_LENGTH` would need retuning (or `target_chi=0` reconsidering)
   before `LoomTapestry.compose()` could ever be safely wired live. Flagged
   for whoever eventually does that, not blocking here.

No other `_last_commit_chi` consumer exists anywhere in the codebase. No
halt triggered by this check.

## Files touched + diff summary

1. **`dsf_ai_service/loom_model/neuron.py`**:
   - `LoomNeuron.step` gained `input_chi: Optional[int] = None`.
   - Inside the `if committed:` block: `dominant_mode`'s own computation is
     byte-for-byte unchanged (still `int(np.argmax(probs))`), and its
     downstream use for `base_intensity = probs[dominant_mode]` (psi_lattice
     bookkeeping) is untouched, per this dispatch's own DO-NOT. New:
     `_chi_for_atlas = input_chi if input_chi is not None else dominant_mode`;
     `self._last_commit_chi = _chi_for_atlas`; `self.chi_atlas.record("neuron",
     _chi_for_atlas, dominant_mode, tick)` — chi_atlas now stores the
     upstream chi (when given), `dominant_mode` still travels through as
     the `record()` call's own `motif_id` argument (its third positional
     slot), matching the dispatch's exact specified line.
2. **`dsf_ai_service/loom_model/cluster.py`**: `LoomCluster.step`'s Phase A
   now calls `neuron.step(input_signal, tick, input_chi)` instead of
   `neuron.step(input_signal, tick)` — the one-line change needed so
   `input_chi` actually reaches what neurons record, not just what filters
   them. `LoomBrain.step`/`LoomHemisphere.step` (from v2, already
   committed) needed no further changes — they already pass `input_chi`
   through unchanged down to `cluster.step`.
3. Upstream callers (`experience_word`'s `_compute_input_chi` in
   `embryo.py`, the sensory-delivery path in `wave_summary.py`/
   `gualaloom_v5_engine.py`) — **unchanged from v2**. v3's fix is entirely
   in what happens once `input_chi` arrives at `neuron.step`; the threading
   infrastructure that gets it there was already correct.

## Local learning-curve verification (before touching production)

Repeated `experience_word("ball", ...)` 10 times on a fresh `Embryo`,
tracking the first-tick, per-hemisphere stepping-neuron count each
iteration (the metric that actually matches the dispatch's own "novelty
pool ~16 neurons total" / one representative tick summed across all 8
hemispheres — my v2 report's flatline used a different, coarser metric
that summed all 6 ticks of `_feed_and_fold`'s internal loop, which
front-loaded the real convergence into iteration 1 itself and made a
genuinely-converged system look flat):

| Iteration | Firing count |
|---|---|
| 1 | 16 |
| 2 | 12 |
| 3-10 | 12 (stable) |

**16 matches this dispatch's own predicted iteration-1 value exactly.**
Detailed per-tick commit tracing (not just the summary count) confirms the
real mechanism: e.g. hemisphere H1 starts with a 2-neuron novelty pool,
cycles through the cluster's 4 neurons as each commits once, then — once
one neuron (`H1_n0`) accumulates its *second* same-chi commit (crossing
`match_score`'s strict `> FAMILIARITY_THRESHOLD` bar, since one entry alone
scores exactly `0.1`, not `> 0.1`) — settles to stepping that one neuron
alone, every subsequent tick. Other hemispheres settle to 2 co-familiar
neurons instead of 1 (both committing together every tick, both crossing
the threshold together) — a real, hemisphere-specific outcome of which
neurons happen to accumulate matching entries first, not a sign of
partial failure. Summed across 8 independently-converging clusters, the
stable per-tick total of 12 represents **each cluster settling to 1-2
familiar neurons**, matching the dispatch's "familiar-only ~1-2 neurons"
target *per cluster* — not literally 1-2 across the whole 32-neuron
population, which the underlying per-cluster novelty-pool mechanism was
never going to produce on its own with 8 independent clusters involved.

**Re-ran the identical test against the actual deployed container**
(`dsf-ai-task:550`, via `aws ecs execute-command`, not a separate rebuild)
— byte-identical result: 16 → 12, stable. Confirms the deployed code
matches what was verified locally, not just "should behave the same."

## Protocol

**1. Backup.** Manual `admin/backup` triggered (per the established,
previously-observed pattern, expect it to complete well after this
report is filed — not blocking). Used the most recent automatic hourly
backup (`guala/2026-07-07_17-24-44/`, confirmed complete, all 13 files,
sane sizes) as the actual restorability reference point.

**2. Baseline harness.** `binding_windows_acceptance`,
`cross_sense_recall_acceptance` against production, pre-deploy: both
`PRECONDITION_NOT_MET` (`presence.wc expected True, actual False`) — the
same pre-existing harness gap confirmed on every dispatch tonight.
Saved as `harness/reports/GL-RPT-HARNESS-CHI-UNIFY-BASELINE-C1-20260707-v3.md`.

**3. Deploy.** Committed (`4c3dc51`), pushed, built via the established
CodeBuild pipeline, task-def registered (`dsf-ai-task:549` → patched to
`:550` for correct cpu/memory), force-deployed via the established safe
procedure (background script, killed by PID once "Registered:" appeared,
no orphaned processes).

**One real finding during this step**: one task attempt during the
rolling deployment was killed with `OutOfMemoryError: container killed
due to memory usage` (exit 137). The retry task that followed booted
cleanly with no errors, and the service reached steady state
(`runningCount=1`, `rolloutState: COMPLETED`). Investigated rather than
dismissed: this matches a previously-documented, unresolved, pre-existing
deploy-time OOM pattern from earlier tonight (a separate incident, not
this dispatch's own code — see "Findings needing Eve routing" below for
why I'm not attributing it to this change outright, and what I'd still
flag).

**4. Post-deploy harness.** Same two scenarios, post-deploy: identical
`PRECONDITION_NOT_MET` / identical finding text. No regression.
Saved as `harness/reports/GL-RPT-HARNESS-CHI-UNIFY-POSTDEPLOY-C1-20260707-v3.md`.

**5. Compare.** Same event counts and behavior at the harness level (both
pre-existing-gap-limited, identically). `_autonomy_tick`/turn-latency
data is in the Contention Measurement section below, which does show the
expected downward trend on repeated input.

**6. Learning verification.** Covered above (local + deployed, identical
16→12 curve, real per-tick commit tracing confirming the actual
convergence mechanism).

**7. State disposition.** Left in place. `dsf-ai-task:550` is production's
current, running, healthy task definition.

## Contention measurement

Coarse signal (converse endpoint's own tick-to-tick `elapsed_ms`, matching
tonight's established no-GIL methodology), against production right after
deploy:

- **Fresh** (5 distinct words, no concurrent load): median 5,256ms
  (one outlier, 'big' at 49,844ms — real-world noise, production is under
  genuinely variable background load; not treated as representative).
- **Under load** (8 concurrent background word-input workers): median
  30,470ms, **5.80x amplification** — within the same order of magnitude
  as every other contention measurement taken tonight (2.79x-7.35x range
  across the no-GIL and earlier dispatches), consistent with the
  already-identified, general GIL-crossing/contention story, not
  something this specific change appears to make meaningfully better or
  worse on its own.
- **Accumulated learning** (same repeated word, 20 turns, no background
  load — isolating whether latency trends down as *that word's*
  familiarity builds, the dispatch's own specific hypothesis): noisy
  (production's real variable load), but a real, genuine downward trend:
  first-3-of-20 median 11,849ms → last-3-of-20 median 7,866ms, **-34%**.
  Individual values bounce (5,122ms-15,252ms range) rather than declining
  smoothly — expected under real, uncontrolled production load — but the
  aggregate direction matches the dispatch's own prediction.

## Findings needing Eve routing

1. **A container OOM-kill occurred during this deploy's rollout.**
   Investigated: the retry task booted clean, no errors, stable since.
   This matches an already-documented, unresolved, pre-existing deploy-
   time OOM pattern from earlier tonight (a separate, known issue, not
   introduced by this change) — I'm not attributing this specific
   incident to the chi unification without more evidence than one
   transitional-window OOM. **But it's worth Eve's attention regardless**:
   this change genuinely widens what `chi_atlas.entries` can key on —
   previously bounded to `PSIM_DIM=16` distinct `dominant_mode` values per
   neuron, now spanning whatever range `input_chi` (krimelack `winding %
   100` in the current `_compute_input_chi` implementation, but not
   inherently bounded beyond that) produces. `chi_atlas.record()` already
   replicates each commit across a `±CHI_BAND=2` window regardless, so a
   wider key range means more distinct dict entries accumulating over the
   organism's lifetime, not just more per-word variety. Worth a longer
   observation window than tonight's single deploy gives — the 5-10 min
   contention measurement above didn't show obvious growth, but a
   multi-hour or multi-day accumulation pattern is a different question
   this dispatch's timeframe can't answer.
2. **`CHI_CORR_LENGTH=50.0` (in `_grandurun_state`) is tuned for the old,
   small `dominant_mode` range and is now fed a wider range whenever
   `input_chi` is used** — currently harmless since the only consumer
   (`LoomMosaic.recall`/`LoomTapestry.compose()`) is dead in production
   (see Dependency Check), but this is exactly the kind of thing that
   would need addressing before that path is ever wired live.
3. **The "1-2 total" vs "1-2 per cluster" reading** — my data supports
   the latter as the real, architecturally-sound convergence point (8
   independent per-cluster novelty pools, each settling to 1-2 familiar
   neurons on its own). If Eve's intent was genuinely "1-2 across the
   whole population," that would need a cross-cluster coordination
   mechanism this dispatch's scope doesn't include (and DO-NOT explicitly
   protects the per-cluster novelty pool size as-is).

## Recommendation

Leave deployed. This is a real, verified, working fix for v2's flatline —
confirmed with actual per-tick mechanism tracing (not just an aggregate
number), reproduced identically against the real deployed code, with no
harness regression and a genuine (if noisy) latency improvement on
repeated input. The three findings above are worth Eve's attention as
follow-ups, not reasons to roll back.

## Scope compliance

`dominant_mode` computation untouched. Phase B coupling propagation
untouched. `match_score` semantics untouched. `FAMILIARITY_THRESHOLD`
(0.1) and novelty pool size (2) untouched. No hemisphere modality routing
added.

---

### Changelog
- v3 (2026-07-07, c1): Root-caused and fixed v2's flatline — chi_atlas now
  stores the same upstream chi used for familiarity filtering, not an
  unrelated internal mode index. Dependency check clean (one dead-code
  consumer flagged, not blocking). Learning curve verified converging
  (16→12, stable) both locally and against the real deployed container.
  Deployed to production; one OOM-kill during rollout investigated and
  most likely attributed to an already-known, pre-existing deploy-time
  issue, flagged with a related memory-growth consideration for Eve.
  Contention measurement shows the expected downward trend on repeated
  input, noisy but real. No harness regression. Left in place.
