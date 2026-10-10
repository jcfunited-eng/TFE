# C-002 Per-Neuron Post-Quiescence Fractal Sprint

## Task identity

- Active ledger item: **C-002**.
- Acceptance: prove each participating neuron retains its own exact sparse
  post-quiescence physical fractal at the expected settlement rate.
- Closed predecessor: **C-001**, live-proven on production task 986.
- Production baseline: commit
  `c5468c045c9c65568ad5781d8b9ebe53cb5f1df2`, task
  `dsf-ai-task:986`, image
  `sha256:114b01c2aac279a7cb34d3c0062895cbdbe394f54d6cc5152b71cb94b1c9a0c7`.
- This sprint advances from C-001. It does not reopen C-001 or any S item.

## Frozen input and scope

Use one production-equivalent unattended whole-roster interval. Its eight
ordered source hops already truthfully carry sight, sound, touch, smell, taste,
and body input on one organism clock. C-002 changes neither those sources nor
their transduction, neuron anatomy, complete L0-L4/DSF delivery, or formation
law.

The one exact question is whether every neuronal value reported as a fractal
is the nonzero retained-coordinate delta between that complete neuron's
pre-experience quiescence and its next post-experience quiescence, and whether
the reached settlement work remains commensurate with the sparse causal
frontier.

## Source-to-output path

1. `native_production_app.py::_unattended_interval_episodes` constructs the
   ordered physical source hops.
2. `native_production_app.py::_commit_admitted_hop` calls
   `NativeResidentOrganism.prepare_admitted`.
3. `native_resident_organism.py::NativeResidentOrganism.prepare_admitted`
   invokes native `NativeResidentOrganismRuntime::prepare_admitted`.
4. `organism_runtime.rs::ResidentOrganismRuntime::prepare_typed` advances the
   resident cognitive formation state and creates `RuntimeObservation`.
5. `resident_cognitive_formation.rs` settles the reached cohort intervals,
   compares neuron physical states, and creates `EmittedNeuronFractal` values.
6. `complete_neuron.rs::sparse_retained_physical_state_delta` permits only
   `PsiWinding`, `GateOpenPopulation`, `PlasticRestLength`, and
   `DnaExpressedProduct` coordinates.
7. Native `RuntimeObservation`, the PyO3 prepare object, the Python wrapper,
   and the public observation carry the claimed result.

## Translation-boundary map

The cognitive transition currently creates each `EmittedNeuronFractal` as:

- exact stable `neuron_lineage`; and
- one canonical nonempty `SparsePhysicalStateDelta`.

Production task 986 retains only `complete_neuron_fractal_count` at this
boundary and drops the emitted per-neuron vector. The C-002 candidate carries
the exact vector through `RuntimeObservation`, PyO3,
`ResidentPrepareEvidence`, production transport, and the public observation.

This is a real evidence-handoff omission. It is not yet the first correction:
the producer must first be proved to emit only after genuine post-experience
quiescence.

## Current producer conflict

The admitted-occurrence path compares each cohort neuron at occurrence entry
and occurrence exit and emits every nonzero retained-coordinate difference.
That outer emission is not presently conditioned on the cohort's or neuron's
post-experience quiescence evidence. A separate pending-experience path tracks
retentive settlement across later intervals, but its completion currently
governs formation retention rather than the outer per-occurrence emission.

Therefore the live aggregate count is not sufficient C-002 evidence and may
include a retained-coordinate change observed before the required next
post-experience quiescence. That must be falsified on the production-equivalent
path before any observation-only correction.

The same bypass existed in the cross-cohort electrical consequence path. It
directly emitted the interval's sparse difference instead of joining the
neuron's unresolved physical experience. Both emitters must obey one law.

## Implemented candidate correction

- Removed the admitted-occurrence exit emitter.
- Removed direct cross-cohort interval emission.
- A neuron now emits once only after it previously acquired a retained
  coordinate change and then completes one exact causal interval with no
  further retained-coordinate change.
- Cross-cohort electrical consequences join that same pending physical
  evidence rather than receiving a second fractal rule.
- The transient observation now carries the stable neuron lineage and every
  exact sparse retained entry. The Python boundary validates one unique
  lineage per emitted fractal, nonempty deltas, canonical exact rational
  parts, and the permitted retained coordinate families.
- Production transport binds each emitted lineage and delta to its exact
  predecessor and successor organism ticks. The public observation exposes
  that same evidence rather than only its count.

Here “post-quiescence” means quiescence of the persistent coordinates being
measured. It does not require membrane, electrical, fluid, or metabolic life
to stop. That distinction is required by a continuously operating organism.

## Expected output and invariants

- A nonzero neuronal fractal is emitted exactly once for one stable lineage
  only after the changed retained coordinates have reached their next physical
  quiescence.
- Each emitted delta contains only exact retained-coordinate entries and is
  independently attributable to one participating neuron.
- Transient membrane charge, carrier transfer, dissipation, fuel, spent,
  heat, and field-delivery changes never become fractal entries.
- A participating neuron with no retained post-quiescence change emits no
  fractal.
- Internal gate intervals never become separate experiences or duplicate one
  neuronal fractal.
- Settlement evidence reports exact causal intervals/reached work; no timeout,
  iteration cap, or wall-clock threshold defines quiescence.
- The predecessor is retained only while the experience is unresolved; after
  closure, only current neuron state and the sparse retained delta remain.
- Identity, neuron/contact state, C-001 one-clock ingress, full joint DSF,
  zero Python cognition callbacks, and bounded CPU/RAM/storage remain intact.

## Production acceptance

On the exact production successor, observe an unattended physical change and
its subsequent settlement without a browser or lesson request. Require:

1. exact participating-neuron and reached-contact counts;
2. exact causal intervals until retained settlement for each emitted lineage;
3. one canonical nonempty sparse retained delta per emitted lineage;
4. no duplicate lineage and no transient coordinate in any delta;
5. aggregate fractal count equal to the per-neuron evidence count;
6. later quiet/equivalent input emit no fabricated duplicate fractal;
7. current-only cold restore preserve the retained neuron state and permit the
   next ordinary interval; and
8. bounded calls, CPU, RAM, state bytes, and durable growth with zero Python
   cognition callbacks.

## Evidence and rejected paths

- Live task 986 at tick 48,439 reported 840 source-port ingresses, 1,952
  physically transitioned neuron-events, four aggregate fractals, nine local
  metabolic body-receptor consequences, and zero Python cognition callbacks.
  The public API supplied no per-neuron fractal bodies or settlement evidence,
  so this is a baseline contradiction, not C-002 proof.
- **Rejected:** treat the aggregate count as proof of individual retention.
- **Rejected:** expose the existing vector before proving its producer's
  post-quiescence boundary.
- **Rejected:** call every persisted physical-coordinate change memory merely
  because it survives serialization.
- **Rejected:** add a polling scan over all resident or developmental neurons.
- **Rejected hypothesis:** require `ReachedCohortIntervalSettlement`'s full
  `locally_quiescent` flag before a fractal can close. That made a continuously
  active but persistently settled cell wait for total cellular inactivity and
  contradicted the definitive `Theta-ret(q+) - Theta-ret(q-)` law.
- **Recorded command failure:** the first formatter invocation ran from
  `native/`, which has no `Cargo.toml`; no test executed. All subsequent Cargo
  commands use `native/guala_core/Cargo.toml` explicitly.
- **Recorded translation failure:** invoking Pytest without the repository on
  `PYTHONPATH` could not import `dsf_ai_service`; no test ran. The corrected
  command is now part of this sprint's executable evidence and passed.
- Candidate native result: 405 library tests pass, zero fail, and 12 are
  explicitly retired/deferred. The prior stale two-versus-three expectation
  is corrected and the complete suite has rerun cleanly.
- Candidate Python result: 23 focused boundary/production tests pass. A
  disposable production-path experience emitted 54 exact causal lineage
  records; its aggregate count, response evidence, and public observation
  were identical. This is local candidate proof, not live-production proof.

## First production increment and remaining defect

The evidence-boundary increment is live on 2026-08-12 as commit
`74888b559d734cbb24102fad4169a23d7aa2c0f5`, task `dsf-ai-task:987`, image
`sha256:4d7ff9c09e37f1a0b5eb6bd502e8a3abd4cf95d3e8bd1a8d5f94605eebd2cabe`.
The service has one healthy running task, zero pending tasks, exact identity
continuity, zero Python cognition callbacks, and the live public observation
now carries `formed_evidence_in_last_experience` rather than only a count.

One previously unused Q-card presentation committed 11 hops and 2,618
physical neuron-events at tick 49,288. It emitted zero neuronal fractals both
during the presentation and in the following continuous interval. That is a
failed positive C-002 acceptance, not evidence that Q was learned. The exact
remaining defect is that a cohort holding an older `retained_experience` is
excluded from opening a new pending physical experience, so its neurons cannot
emit a later post-quiescence fractal. C-002 remains open until recurrent lived
experience can retain new per-neuron physical deltas without replacing the
older retained formation or inventing a second formation law.

## Recurrent-lifecycle correction in progress

The governing preflight now requires the same stateful path to be proved from
both a pristine participant and a participant carrying prior retained
experience or restored state. First-use success alone cannot authorize
packaging.

The candidate uses the wire format's existing independent
`retained_experience` and `pending_experience` carriers. It permits an
experienced cohort to open one new bounded pending physical experience,
accumulate exact retained-coordinate changes, emit each newly quiescent sparse
neuron delta once, and discard only that completed pending evidence. It does
not overwrite the prior retained formation, add a schema, or change mosaic
admission.

Focused native evidence:

- `experienced_neurons_emit_one_new_bounded_fractal_after_later_quiescence`
  passes;
- retained plus pending evidence encodes, decodes, and re-encodes byte-exactly;
- the prior retained formation remains identical after the later experience;
- the later quiescent interval emits nonempty sparse deltas; and
- a following quiet interval emits no duplicate.

This is local evidence only. The next gate is the same recurrent path against
the authenticated task-987 production predecessor; C-002 remains open.

That exact predecessor gate first falsified the candidate: Z physically moved
218 neurons but produced no retained fractal. The first absent boundary was
the retained-coordinate projection. It excluded the neuron's persistent
receptor-quantum accumulator even though the definitive neuron model admits
exact retained channel or receptor material. The candidate now includes that
existing rational coordinate under the truthful sense-agnostic name
`receptor-quantum-residue`; its existing wire tag remains 24, so no body or
mosaic schema changes.

Against the SHA-verified task-987 body at tick 49,540, a discarded Z lesson
plus exact quiet tail now proves:

- identity remains `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`;
- 216 unique recurrent neuronal fractals are emitted;
- their exact entries contain 215 receptor-residue and 46 winding deltas;
- four later quiet hops emit zero duplicates;
- reached neurons move 221 to 222 and mosaics 1 to 2 through existing physics;
- state growth is 221,259 bytes; and
- Python cognition callbacks remain zero.

The full native suite passes 572 tests with zero failures and 12 explicit
ignored tests. The frozen C-002 Python boundary set passes 23/23. A mistakenly
broadened Python command also exposed 17 stale production-fixture failures:
those mocks lack the already-existing `mosaic_of_mosaics_count` field. They are
recorded as out-of-scope fixture debt and were not repaired in C-002.

## Live production closure

The candidate was deployed once on 2026-08-12 as commit
`d49cc0c22993f6ebae3009f7dee917ae0392a464`, task `dsf-ai-task:988`, and image
`sha256:47dc20e80b144008b10c69354001255cdb033fcf43d0ac09d193443bf570912b`.
The single controller run lasted 17 minutes 59 seconds. Before cutover, the
digest-pinned candidate cold-restored the exact 31,688,948-byte task-987 body
at tick 49,900 with byte-identical SHA-256, stable identity, and a read-only
source mount. ECS then settled at one healthy running task and zero pending
tasks before the image was pinned as `production-current`.

One previously unused live Z-card presentation was admitted exactly once. It
committed at tick 49,992 and durably persisted 30,922,280 bytes. The transition
physically moved 218 neurons and exposed 216 per-neuron evidence records with
216 distinct `(predecessor tick, successor tick, neuron lineage)` identities.
Those records contain 215 exact `receptor-quantum-residue` entries and 46 exact
`psi-winding` entries. Existing developmental physics moved the body from 221
to 222 complete neurons and from one to two mosaics; this is physical formation
evidence, not a claim that the word "Z" was learned.

Two subsequent unattended production intervals advanced independently to
ticks 50,001 and 50,010. They exposed 163/163 and 189/189 unique causal
fractal records with zero duplicate identities, preserved the same organism
identity, held complete-neuron and mosaic counts at 222 and two, and retained
zero Python cognition callbacks. At tick 50,010 the persisted body measured
32,021,476 bytes. During deployment and live proof, observed ECS maxima were
39.5 percent CPU and 10.0 percent memory; the service remained one healthy
task with no pending task.

C-002 is therefore closed in live production. It proves bounded recurrent
per-neuron post-quiescence physical evidence. It does not prove word learning,
semantic identity, general recognition, or the multisensory mosaic law assigned
to C-003.
