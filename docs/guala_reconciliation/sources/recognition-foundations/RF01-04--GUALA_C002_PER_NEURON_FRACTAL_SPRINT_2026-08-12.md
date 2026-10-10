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
  parts, and the four permitted retained coordinate families.
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
- Transient membrane, carrier, receptor-residue, dissipation, fuel, spent,
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
