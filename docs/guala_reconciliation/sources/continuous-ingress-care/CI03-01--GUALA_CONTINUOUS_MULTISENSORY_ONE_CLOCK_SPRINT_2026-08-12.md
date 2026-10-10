# C-001 Continuous Multisensory One-Clock Sprint

## Task identity

- Active ledger item: **C-001**.
- Acceptance: all already-mounted external, body, and fluid senses continuously
  feed one organism clock while unattended; no mouse click is required.
- Closed predecessor: **S-020**, live-proven on production task 984.
- Production baseline: task `dsf-ai-task:984`, commit `0e320fe19829fac1ce3c96fb5ee1509be646de28`,
  image `sha256:8d4bc7d7d1eef3b2efe167f7fd0c60828a6384ec5e207dc75dac2fd40ea52e6c`.
- This sprint advances from S-020 to C-001. It does not reopen S-019 or S-020.

## Frozen input and path

One unattended interval begins at
`native_production_app.py::_attempt_unattended_interval`, samples the persistent
world once in `_unattended_interval_episodes`, constructs eight ordered 250 ms
joint sensorium hops in `_whole_roster_hop_episode`, and passes each admitted hop
through `_commit_admitted_hop` to native `prepare_admitted` and `commit`.

The mounted hop contains, on one exact source-time sequence:

- retinal light;
- both legacy ear places and both mounted cochlear banks, including lawful
  silence;
- the mounted contact sheet, including lawful released contact;
- olfactory chemistry;
- gustatory chemistry, including lawful no oral contact;
- mounted body displacement, including lawful stillness.

Localized recovery-fluid/body afference is not a Python sensor or organism-wide
bookkeeping projection. It settles inside the same native admitted transition
and is reported only when a local layer-5 membrane consequence occurs.

## Translation-boundary map

Native `NativeResidentOrganismPrepare` already emits:

- `receptor_ingress_sense_counts` in canonical order
  `(sight, sound, touch, smell, taste, body)`;
- `receptor_ingress_changing_count`;
- `receptor_ingress_quiescent_count`; and
- `metabolically_perturbed_body_receptor_count`.

Before this sprint, `native_resident_organism.py::ResidentPrepareEvidence`
discarded the three receptor-ingress fields, and
`native_production_app.py::_commit_admitted_hop` therefore could not carry them
to live observation. The underlying sensory physics was not missing; the
Python/native evidence handoff was incomplete. The correction carries the
existing fixed-size native observation through the wrapper and current
transition receipt. It adds no cognitive state, persistence field, source scan,
owner, lock, database, timer, or semantic rule.

## Expected output and invariants

- Each unattended source hop reports a nonzero exact ingress count for every
  mounted external/body sense in production.
- The sum of changing and quiescent ingress ports equals the sum of the six
  sense counts for every hop.
- Eight hops advance one organism by eight ordered ticks; any native motor yaw
  consequence may add its own separately reported vestibular tick.
- At least one live interval must report local metabolic layer-5 consequence,
  without inventing an aggregate interoceptor.
- Identity, learned state, neuron/contact counts, full joint L0-L4/DSF delivery,
  zero Python cognition callbacks, and bounded CPU/RAM/storage remain intact.

## Live acceptance

On the exact production successor, observe multiple unattended intervals with
no browser or lesson request. Require:

1. intake prefix `continuous-environment:` and eight source hops;
2. exact nonzero ingress counts for all six canonical sense classes;
3. ingress arithmetic conservation;
4. advancing organism ticks and authenticated state receipts;
5. a local metabolic body-receptor consequence in at least one interval;
6. zero Python cognition callbacks and stable bounded resources; and
7. current-only cold restore followed by another ordinary unattended interval.

## Production result

C-001 is live-proven on 2026-08-12.

- Commit: `c5468c045c9c65568ad5781d8b9ebe53cb5f1df2`.
- ECS task definition: `dsf-ai-task:986`.
- Running task: `ee8275385001475ea4fc4a651ae6d366`, healthy, with one
  desired and one running task and no pending task.
- Image: `sha256:114b01c2aac279a7cb34d3c0062895cbdbe394f54d6cc5152b71cb94b1c9a0c7`.
- The release controller rehearsed the exact production predecessor before
  cutover. The candidate cold-restored the same organism and then completed
  eight source hops plus one vestibular consequence with zero Python cognition
  callbacks, no reached-neuron growth, and no state-byte growth.
- Public observations without a browser, lesson, or mouse action advanced
  distinct organism ticks `48,349 -> 48,358 -> 48,367`. Each interval reported
  eight ordered source hops and the same exact receptor ingress:
  `sight=216`, `sound=272`, `touch=216`, `smell=64`, `taste=40`, `body=32`,
  `total=840`. All 840 ports were truthfully quiescent within their individual
  hop; quiescent means an unchanged physical condition, not an absent sense.
- Every observed interval reported nine local metabolic body-receptor
  consequences, full DSF delivery, zero Python cognition callbacks, and an
  ordinary motor-yaw/vestibular consequence.
- Authenticated state size remained exactly `30,591,023` bytes across the
  distinct observations. Reached/resting identity and current-only restore
  remained intact.
- Post-cutover CloudWatch maxima were 27.72% CPU of the four-vCPU service
  reservation and 6.68% memory of 16 GiB. The new task logged one server start
  and no traceback, error, exception, current-mismatch, or restore-failure
  signature.

This proves continuous one-clock participation of the senses already mounted
in production. It does not claim autonomous attention, thought, language,
learning, active object contact, or neuronally transduced proprioception.

## Falsified or rejected paths

- **Rejected:** add a second interoception port. Local fluid afference already
  arises in native neuron/recovery-contact physics; an aggregate Python port
  would sense bookkeeping rather than the body.
- **Falsified:** the unattended builder omits mounted external senses. Source
  trace shows all authorized external/body ports share the same hop clock.
- **Confirmed defect:** exact native ingress evidence was dropped at the Python
  translation boundary. Correct that handoff; do not redesign the neuron or
  sensor physics.
- **Rejected acceptance specimen:** a newly generated body with every sense
  authorized simultaneously refused its first unattended interval with native
  `MaterialConservation`. Production task 984 is not a newborn and already
  carries the complete reached roster, so this does not test C-001's frozen
  input. Record it for a separate genesis investigation; do not replace the
  required authenticated production-predecessor rehearsal with it.
- **Command-shape failure:** the first focused pytest invocation omitted the
  isolated worktree from `PYTHONPATH` and failed during collection. No test or
  organism transition ran. All later commands bind `PYTHONPATH=$PWD`.
- **Existing deployment-fixture debt:** the packaging/rehearsal group passed 28
  tests and failed four historical fixtures. Three construct task definitions
  without the now-mandatory live organism root/baseline fields; one pins an
  obsolete newborn transition count (`420`, current measured fixture `973`).
  They do not exercise the C-001 handoff. The real controller rehearsal against
  the authenticated production predecessor remains the release authority.
