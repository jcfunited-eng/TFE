# GL-RPT-BLUEPRINT-PHASE-1-NEURON-AUTONOMY-C1-20260707-v1

**doc_id:** GL-RPT-BLUEPRINT-PHASE-1-NEURON-AUTONOMY-C1-20260707-v1
**From:** c1
**Executing:** GL-CMD-BLUEPRINT-PHASE-1-NEURON-AUTONOMY-EVE-20260707-v1
**Blueprint:** GL-BLUEPRINT-AE-SUBSTRATE-EVE-20260707-v1 §3.1, §3.3, §4 Phase 1
**To:** Eve (routing per dispatch instruction — no questions to Joe in this doc)

**HALT before deploy. Not a scope-creep halt (condition 5) — a "the
blueprint doesn't answer this" halt, per the dispatch's own scope
guardrail: "If Phase 1 raises questions the blueprint doesn't answer,
halt and route to Eve. Do not invent architectural decisions
unilaterally."** Built and fully unit-tested the two well-specified,
self-contained pieces (spike bus infrastructure, per-neuron
spike-handling methods) — real, working, verified via an actual two-neuron
spike-propagation demo. Stopped before the wiring step (LoomBrain.step /
LoomCluster.step / Guala lifecycle / emission candidate source), because
that step, done as literally specified, would silently sever the live
production hot path from the only mechanism that currently produces
everything the substrate's chi_atlas, binding_atlas, recall, and emission
read. **No backup, no baseline harness run, no deploy** — nothing is
being shipped, so the protocol's deploy-verification steps don't apply
yet. Zero risk to production: every line touched is either a new file or
purely additive code that nothing currently calls.

---

## The finding, precisely

The dispatch's reference implementation for `receive_spike`/`_fire`
(dispatch item 2) is self-contained around a single scalar
`membrane_potential`. It has no call anywhere into
`krimelack.transduce()`/`feed_signal()`, `compute_dsf()`, or
`psi_lattice.settle()` — the mechanisms that, in the **current, real**
`LoomNeuron.step()` (`dsf_ai_service/loom_model/neuron.py:501-654`, confirmed
by direct read, not summarized), are what actually:

1. Turn `input_signal` (a word string, or a raw sensory array) into
   structured events via `krimelack.transduce`/`feed_signal` — this is
   where word/sensory **content** enters the neuron at all. A bare
   `weight: float` (as `PendingSpike.weight`/`membrane_potential` are
   typed) carries none of that content.
2. Compute a `DSF` (`compute_dsf(events, atlas_similarity=match_score)`)
   and settle it into `psi_lattice` — a 16-dimensional complex quantum-inspired
   state. `committed = psi_lattice.committed(dsf)` is **today's actual
   firing decision** — not a threshold on a scalar.
3. On commit, write `self.chi_atlas.record("neuron", _chi_for_atlas,
   dominant_mode, tick)`, where `dominant_mode = int(np.argmax(probs))`
   is the argmax over `psi_lattice.probabilities()` — a real 16-way
   distribution produced by step 2. **This is the entire content of what
   chi_atlas currently records.** A bare membrane-potential crossing has
   no analogous 16-way distribution to argmax over.

The dispatch's own text for `_on_fire_bookkeeping` says it "preserves
current substrate observability without changing what those consumers
see." That claim isn't achievable as specified — the data those
consumers (chi_atlas directly; `binding_atlas`/`recall_fast`/emission
indirectly, see below) currently see has no derivation path from a
scalar membrane potential. This isn't a style disagreement; it's a
concrete, checkable gap I verified against the real files, not inferred
from the dispatch text alone.

**Why this matters for production specifically, not just in the
abstract**: `dsf_ai_service/v4/gualaloom_v5_engine.py:3098`, inside
`Guala._organism_worker_loop` (the **live production hot path**, running
continuously under `AUTONOMY_PHASED`), calls `hemi.step(input_signal,
sensory_tick, input_chi)` → `LoomHemisphere.step` → `LoomCluster.step`
→ `LoomNeuron.step` — real sensory input, on every tick, today. The
dispatch's item 3 says `LoomCluster.step` "becomes a no-op with a
deprecation log" and `LoomBrain.step` "becomes an injection dispatcher"
that only computes `_signal_to_weight(input_signal)` — a single scalar —
and injects it. If built exactly as specified and left as the default
(the dispatch's own "State disposition: leave in place unless Joe routes
otherwise," with rollback only via `SPIKE_BUS_ENABLED=0` — i.e. the new
behavior IS the deployed default), **every real sensory/word content
processing on the production hot path stops**, replaced by a contentless
scalar accumulating in a membrane-potential variable. The substrate would
keep running — spikes flowing, threads alive, health checks green — while
silently no longer doing any of the cognitive work `krimelack`/`DSF`/
`psi_lattice` currently do. That is a maximally dangerous regression
class: invisible to a shallow health check, and (per my check below)
possibly invisible to the current harness scenarios too, since they
already return `PRECONDITION_NOT_MET` for unrelated reasons on every
recent dispatch this session.

**Second-order confirmation — emission depends on the same mechanism,
through a different door.** `_brain_emission_candidates`
(`gualaloom_v5_engine.py:3468-3577`) calls `organism.recall_fast(...)` →
`neuron.binding_atlas.recall_best(...)` for every candidate. I checked
what populates `binding_atlas`: `neuron.py:852`,
`self.binding_atlas.record(concept, state_vec, tick)`, called from
`experience_moment()`, which is called from `embryo.py` (the
`remember()`/cognition-merge path) and `experience.py:115` — a **separate**
ingestion path from `step()`'s krimelack/DSF/psi_lattice pipeline, not
the same one. This means emission's dependency on real content survives
independently of the `step()` question *as long as `experience_moment`'s
own callers are untouched* (the dispatch doesn't mention them, so
they should be) — genuinely good news, and worth being precise about
rather than overstating the blast radius. But `chi_atlas` — named
explicitly in the dispatch's own "preserved" list — has no such
independent survival path; it is written *only* from inside `step()`'s
commit block.

## Concrete implementation gaps found (separate from the architectural
question above — these are things the reference code assumes that don't
exist in the real files, confirmed by direct grep/read)

1. `self.chi_position` — referenced by `_compute_propagation_delay_ms`'s
   reference implementation. **Does not exist anywhere in the codebase.**
   No per-neuron static chi coordinate exists today; chi is associated
   with committed *events* via `chi_atlas`, not with neuron identity.
   Added as a new, unpopulated `Optional[int] = None` field — see below.
2. `self._coupled_neighbors` — referenced as a list of neuron *objects*
   aligned with `couplings.J`'s rows. Real `CouplingsJij.neighbors` is
   `List[str]` of neuron_id strings; neurons hold no direct object
   references to their neighbors (only cluster/hemisphere-level
   `_neuron_map` dicts do). Adapted `_get_outgoing_synapses()` to iterate
   `self.couplings.neighbors` (the real field) directly — mechanical, not
   an architecture decision.
3. `self.couplings.J[j_index]` — reference code treats this as a scalar
   weight. Real shape is `(K, 16)` — one 16-element vector per neighbor
   (16 ψ-lattice modes). Reduced to a scalar via
   `float(np.mean(self.couplings.J[j_index]))`, the **exact convention
   `LoomCluster.step`'s own Phase B already uses** (`cluster.py`:
   `J_weight = float(np.mean(neuron.couplings.J[src_idx]))`) — reused an
   existing convention rather than inventing a new one.
4. `get_associated_word()` — referenced by dispatch item 5's emission
   integration sketch. Does not exist anywhere. Real word↔chi mapping for
   emission goes through `binding_atlas.recall_best()` +
   `self._word_to_emission_sections`, not a per-neuron attribute. Not
   built this dispatch (emission integration wasn't attempted — depends
   on the core question above).
5. No `EMISSION_THRESHOLD` constant exists anywhere (confirmed via grep).
   Not added — dispatch item 5 wasn't attempted.

None of these five are independently blocking (all are mechanically
resolvable, and I resolved 1-3 in the additive code where they didn't
require deciding anything Eve should decide). They're listed because
each one is evidence the reference implementation wasn't checked against
the current file contents before being handed off — which raises my
confidence that the larger krimelack/DSF/psi_lattice gap is a real
oversight, not an intentional-but-unstated "yes, retire the whole
existing computational stack" decision.

## What WAS built (real, tested, zero production risk)

### 1. `dsf_ai_service/substrate/spike_bus.py` (new, ~110 lines)

`PendingSpike` dataclass, `SpikeBus` class — `inject()`,
`start()`/`stop()` (Event-based, `join(timeout=5.0)`, matching the
codebase's own cleanest existing lifecycle pattern in
`persistence_consumer.py` rather than the dispatch's bare-thread sketch),
priority-queue delivery loop, observability counters
(`delivered_count`/`dropped_count`/`injected_count`/`qsize()`) added
beyond the dispatch's sketch since the harness protocol's own step 6
("measure spike queue depth over 5 minutes") needs them and nothing in
the reference code exposed them.

**Not wired into Guala's lifecycle** (dispatch item 4) — nothing
constructs a `SpikeBus` at boot, nothing calls `.start()`/`.stop()`. This
is dead code today, by design, until the architectural question is
resolved.

### 2. `dsf_ai_service/loom_model/neuron.py` (modified, +201 lines, 0
removed — purely additive)

New `LoomNeuron` fields (all in a clearly delimited block in `__init__`,
after all existing fields): `membrane_potential`, `membrane_rest`,
`membrane_threshold`, `tau_m_ms` (HEURISTIC, see below),
`refractory_period_ms` (HEURISTIC), `last_update_time_s`,
`refractory_until_s`, `_neuron_lock`, `chi_position` (new, unpopulated —
gap 1 above), `_spike_bus` (`None` by default).

New methods: `set_spike_bus()`, `receive_spike()`, `_fire()`,
`_compute_propagation_delay_ms()`, `_get_outgoing_synapses()`,
`_on_fire_bookkeeping()` (see below — deliberately a no-op, not a stub
that fabricates data).

**`step()` is completely untouched** — I did not implement the
dispatch's "preserve step() as deprecation shim" instruction, because
replacing `step()`'s body *is* the severing action described above.
Confirmed via `git stash` A/B test: identical output from
`LoomNeuron("n1").step("hello", tick=1)` before and after my changes,
same six-key result dict. This is the one explicit deviation from the
dispatch's literal text — flagged here, not silently done.

**`_on_fire_bookkeeping` is intentionally a no-op** (`pass`), not wired
to `chi_atlas.record()`. Writing *something* there would have required
inventing what a spike-driven "dominant_mode" equivalent should be —
exactly the unilateral architectural decision the dispatch's own
guardrails forbid. Left honestly empty with a docstring explaining why,
rather than fabricating plausible-looking data.

### 3. Tests (new, all passing)

- `dsf_ai_service/substrate/test_spike_bus.py` — 6 tests: immediate
  delivery, delay ordering, unknown-target handling (drop, don't crash),
  exception-in-receive_spike resilience (bus keeps running), qsize +
  clean stop/join, 8-thread × 50-injection concurrent-injection stress
  test (400/400 delivered, 0 dropped).
- `dsf_ai_service/loom_model/tests/test_neuron_spike_handling.py` — 10
  tests: membrane integration, threshold firing, refractory absorption,
  exponential decay toward rest, `J`-vector→scalar reduction, propagation
  delay default/scaling, spike emission to a fake bus, fire-without-bus
  safety, and the `step()`-unchanged sanity check above.
- A real, non-mocked **end-to-end demo**: two real `LoomNeuron`
  instances, one real `SpikeBus`, external injection into n1 → n1 fires →
  spike delivered to n2 with a computed delay → n2 fires too. Both
  neurons' `refractory_until_s` confirmed set post-run; bus
  `delivered_count == 2`, `dropped_count == 0`. This is genuine,
  working, tested infrastructure — just not connected to anything live.

### 4. Regression check against the existing suite

Ran 8 existing `dsf_ai_service/substrate/` and `loom_model/tests/` test
files that exercise `LoomNeuron` (hemisphere roundtrip, plasticity,
cognition bundle, dynamics emission, teacher correction, structured
noise, cognition path). Several show pre-existing failures (e.g.
`test_plasticity_on_commit.py`: "OVERALL: FAIL... per brief: this is an
audit-driven decision for Joe, not removed here" — a documented, known
issue). **A/B verified via `git stash` on `neuron.py` alone**: every
failing test fails *identically* — same pass/fail counts, same specific
sub-check failures — with and without my changes. Zero regressions
introduced. (`test_autonomous_emission.py` errored on both sides too, but
that's a `sys.path` issue from running the file directly rather than via
`python -m`, unrelated to any code content.)

## HEURISTIC values (per blueprint §2.4 — none tuned, all as specified
or directly inherited)

- `tau_m_ms = 20.0` — from dispatch/blueprint, biological range, class
  from-biology-reference. Untouched.
- `refractory_period_ms = 2.0` — same, untouched.
- `membrane_threshold = 1.0`, `membrane_rest = 0.0` — dispatch defaults,
  untouched.
- `DEFAULT_DELAY_MS = 1.0` (new, mine) — placeholder fallback for
  `_compute_propagation_delay_ms` while `chi_position` is unpopulated
  (i.e. always, in Phase 1 as built). Class: from-design, not measured.
  **This will be the delay for every spike** until gap 1 above is
  resolved — worth Eve knowing the heuristic is currently doing 100% of
  the work, not 0%.
- `MAX_CHI_DISTANCE = 262144` (new, mine) — reused the wave-atlas
  `N_CELLS` constant as the normalization denominator for the
  chi-distance delay formula, since `LoomNeuron` itself has no chi space
  of its own to draw a bound from. A guess at the right scale, not a
  measurement.
- `EMISSION_THRESHOLD` (dispatch item 5, `= 0.5`) — **not added**,
  emission integration wasn't attempted.

## Scope-boundary concerns

- Did **not** implement STDP, lateral inhibition, metabolism,
  neuromodulation, sleep-as-work, or seed changes — confirmed none of
  the additive code touches any of those.
- Did **not** modify `chi_atlas.record` semantics, wave atlas, or binding
  windows — confirmed via diff (only `neuron.py` touched among existing
  files, and only additively).
- Did **not** tune any HEURISTIC value away from its dispatch-given
  default.
- The one place I made an independent call (gaps 1-3 above:
  `chi_position` as a new unpopulated field, `_get_outgoing_synapses`'s
  `List[str]`-based iteration, `np.mean`-based `J`-vector reduction) are
  all **mechanical adaptations to the real file shapes**, using
  conventions the existing codebase already established for the same
  problem (the `np.mean` reduction is a literal copy of
  `LoomCluster.step`'s own pattern) — not new architecture. Flagged
  individually above so Eve can veto any of them specifically if that
  judgment is wrong.

## Findings needing Eve routing

1. **The core question** (see "The finding, precisely" above): does
   Phase 1 intend for `krimelack`/`DSF`/`psi_lattice` computation to be
   fully retired from the neuron-firing path (matching the blueprint's
   opening framing — "replaces the discretized-tick... coverage-model
   substrate" — but never named explicitly anywhere in §3.1, §3.3, or
   the dispatch's ~380 lines, and never listed in the blueprint's own
   §8 Deprecation section, which names `_autonomy_tick`,
   `LoomBrain.step` iteration, `cluster.step`'s freight-train iteration,
   and coverage-model `chi_atlas` — but not krimelack, DSF, or
   psi_lattice)? Or does `receive_spike`/`_fire` need to also invoke that
   pipeline (a materially bigger Phase 1 than what's specified), so
   membrane-potential firing and quantum-commit firing coexist / feed
   each other? This determines everything about how items 3-5 get built,
   and I don't think it's mine to decide given how much currently-live
   behavior depends on the answer.
2. If the answer to #1 is "retire it" — what happens to
   `chi_atlas.record`'s content? The dispatch names chi_atlas as
   preserved/untouched, but the only mechanism producing what it
   currently records goes away under that answer. Needs a real
   replacement spec, not an implied one.
3. `chi_position` (gap 1): where should a real value come from? Options
   I can see but haven't picked: (a) reuse the language-seed generator's
   `chi_addresser.py` deterministic clustering (built two dispatches ago,
   `generator/language_seed/chi_addresser.py` — different address space
   convention, N_CELLS=262144, would need a mapping into whatever space
   `LoomNeuron` should use), (b) derive from ring position within a
   hemisphere's cluster (structural, matches how `_structural_dna` already
   derives per-neuron chemistry from `(hemi_index, ring_pos)` in
   `embryo.py`), (c) something else. Not decided here.
4. Should `SPIKE_BUS_ENABLED` default to `0` (opt-in) or `1` (opt-out via
   rollback, per the dispatch's literal rollback text) once items 3-5 do
   get built? Given the severity of what's at stake if the wiring is
   wrong, I'd lean toward defaulting off and requiring explicit opt-in
   for at least one verification cycle, but that's Eve's call, not mine
   to bake into the eventual implementation.

## Harness protocol — not run

Per the dispatch's own step numbering, steps 1-2 (backup, baseline
harness) exist to protect against a deploy that's about to happen in
step 3. Nothing is being deployed. Running a backup/baseline against
production for a change that doesn't touch production would be
theater, not verification — skipped for that reason, not for lack of
diligence. Once the finding above is resolved and items 3-5 get built,
the full six-step-plus-event-driven-verification protocol applies in
full, including the real backup/baseline/deploy/postdeploy/comparison
cycle this report doesn't contain.

## Recommendation

Phase 1's two well-specified components (spike bus, per-neuron
spike-handling) are built, real, and tested — genuine forward progress,
reusable the moment the architectural question resolves. The wiring
step is where Phase 1 stops being "build new infrastructure" and starts
being "replace the thing currently producing all observable substrate
behavior," and the dispatch doesn't specify what replaces it. Recommend
Eve resolve finding #1 (and ideally #2-4) before a Phase 1b dispatch
attempts the wiring — at that point items 3-5, plus the full backup/
baseline/deploy/verification protocol, are the natural next dispatch.

---

### Changelog
- v1 (2026-07-07, c1): Built spike_bus.py + additive LoomNeuron
  spike-handling methods, fully unit-tested (16 new tests, all passing)
  plus a real two-neuron end-to-end propagation demo. Confirmed zero
  regression against the existing test suite via git-stash A/B
  comparison. Halted before wiring LoomBrain.step/LoomCluster.step/Guala
  lifecycle/emission to the new mechanism: receive_spike/_fire as
  specified have no path to krimelack/DSF/psi_lattice, the mechanism
  currently producing everything chi_atlas (and, one level removed,
  binding_atlas/recall/emission) read. Wiring as literally specified
  would silently sever the live production hot path's real cognitive
  computation. Five smaller concrete implementation gaps also found and
  either mechanically resolved (reusing existing codebase conventions) or
  left unbuilt and flagged. No backup/baseline/deploy — nothing shipped.
  Routed to Eve.
