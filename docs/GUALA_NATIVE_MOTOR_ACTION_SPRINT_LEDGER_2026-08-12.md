# Guala C-019 Motor Preparation and Action Sprint Ledger

Date resumed: 2026-08-13

Status: **Live-Closed 2026-08-13**. The exact behavior was directly observed on
public production Guala; evidence is recorded below.

## Task identity

- Active delivery-ledger item: `C-019`.
- Acceptance condition: prove motor preparation reaches layer 12 and can cause
  one at-most-once body actuation whose consequences return through the senses.
- Immediate predecessor: `C-018`, live-closed on public task
  `dsf-ai-task:1018`, release commit `b9d85da3`, image
  `sha256:09116ddafe48cd71955e78d28b9afd8316c40645babea683557a44f90719ee15`.
- Production baseline: organism identity
  `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`, public task 1018, with live
  layer-12-discharge yaw and vestibular return already observed.
- Ledger movement: advance to C-019. C-018 is not reopened.

## Architecture honesty gate

1. Requested architecture: one exact layer-11 physical preparation influences
   a mounted layer-12 motor neuron through their direct contact; that prepared physical continuation can emit
   one motor recruitment, execute one body actuation at most once, and return
   its body consequence through mounted sensory mechanics.
2. Current code reality: layer-12 discharge already crosses the native/Python
   transport boundary, prepares one exact yaw, commits one world revision, and
   returns through the native vestibular path. Its transient recruitment did
   not carry the exact current across its direct layer-11/layer-12 contact, so
   the action could not be attributed to physical preparation.
3. Conflict: yes, confined to the missing preparation-to-recruitment causal
   binding and its public observation.
4. Not extended: Python choice or planning, semantic intent, action labels as
   authority, score selection, timer-authored action, owner, lock, queue,
   database, UI animation, dense scan, persistent command, or C-018 fluid law.
5. Single exact item: bind the complete exact layer-11/layer-12 contact-transfer
   set to the transient layer-12 recruitment and carry it unchanged
   through the already-mounted at-most-once yaw and vestibular return path.
6. DSF: every participating neuron continues to receive the full unchanged
   joint seven-field L0-L4 result.
7. Field loss: none. No DSF projection, scalar, score, or reduced field is
   introduced.

## Frozen scope and change-impact path

- Exact input: the present native interval's settled current across a direct
  contact between a mounted layer-11 cell and the mounted layer-12 motor cell.
  The endpoint potentials jointly cause the transfer; its actual signed
  direction is preserved.
- Native path:
  `ResidentCognitiveFormationState::prepare_*`
  -> `settle_internal_contact_interval`
  -> `MotorUnitRecruitment`
  -> `ResidentPrepareReceipt`
  -> `NativeResidentOrganismPrepare::motor_unit_recruitments`.
- Python/actuator path:
  `NativeResidentOrganismBoundary.prepare`
  -> `_commit_admitted_hop`
  -> `_perform_admitted_intake_locked`
  -> `_prepare_motor_yaw_action`
  -> `EmbodimentWorldAuthority.prepare_port_command`
  -> `commit_prepared_action`
  -> `_commit_vestibular_trajectory`
  -> one organism/world publication
  -> public native observation.
- State transformation: a positive whole-carrier layer-12 discharge is
  eligible for actuation only when the same settlement also contains nonzero
  current across that motor's direct contact with layer 11. The evidence is
  transient and changes no retained cognition, neuron, or world state.
- Expected output: one prepared motor recruitment with exact layer-11 sender,
  layer-12 receiver, stable bond, transferred whole carriers, layer-12
  topology, and outward motor carriers; one exact yaw action; one world
  revision; one vestibular trajectory; one persisted organism/world successor.
- Unchanged invariants: organism identity, complete-neuron state law, full DSF,
  existing contacts, current-only persistence, zero Python cognition callbacks,
  sparse reached-frontier work, and all C-018 conservation evidence.

## Acceptance-evidence map

| Required fact | Producer | Retained/runtime state | Boundary | Public proof |
|---|---|---|---|---|
| layer-11 preparation influences layer 12 | exact signed current across their direct physical contact | present settlement only | motor recruitment projection | exact sender/receiver directions, layer 11 and layer 12 endpoints, bond, and carriers |
| prepared motor cell discharges | complete-neuron/contact settlement | transient motor recruitment | PyO3 and Python tuple unchanged | exact motor lineage/topology/outward carriers |
| action executes at most once | prepared world command bound to predecessor state and revision | one committed world successor | coupled world/organism publication | one revision and exact signed yaw for one intent |
| consequence returns through senses | body yaw trajectory | native vestibular successor | ordinary intake aggregate | nonzero vestibular tick count and returned body/sensory evidence |
| continuity and bounds hold | native runtime and current-only persistence | exact successor | public observation/resource surfaces | same identity, cold restore, one process, zero Python cognition callbacks, bounded bytes/CPU/RAM |

## Stateful branch matrix

| Branch | Required result |
|---|---|
| pristine focused body | real current across a direct layer-11/layer-12 contact can qualify a motor discharge for one sensed action |
| authenticated task-1018 predecessor | the ordinary unattended source-to-consequence path produces a new bounded successor without replacing prior neurons, contacts, mosaics, or identity |
| cold-restored successor | the exact committed body/world pair restores and completes one later ordinary interval without replaying the prior action |

## Applicable deployment recurrence checks

| IDs | Earliest check for this sprint |
|---|---|
| RF-001, RF-002 | exact worktree first on `PYTHONPATH`; import only after exporting the exact task-1018 environment |
| RF-003 | rebuild the candidate wheel and print the loaded native module path/provenance before end-to-end proof |
| RF-004, RF-022 | run pristine and task-1018 restored branches; no persisted schema changes are expected |
| RF-005, RF-017, RF-018, RF-028, RF-030 | census every native constructor/getter, PyO3 tuple, Python parser, multi-hop aggregate, observer, signature, and controller consumer before compile |
| RF-007, RF-033 | resolve the real AWS account/region/service/task and controller invocation before the deployment clock |
| RF-010, RF-021, RF-027 | keep assertions bound to the exact successor; compare persisted `CURRENT`, cold-start it, and run the next ordinary interval |
| RF-012, RF-020 | source must be the real production predecessor; mounted layer 12 or synthetic recruitment is insufficient |
| RF-016, RF-034 | candidate diff and rehearsal assertions belong only to C-019; closed witnesses are not recurring requirements |
| RF-025, RF-029 | on timeout/refusal, read the successor before any retry; never duplicate an action |
| RF-031, RF-032 | resolve test names, working directories, and nonzero executed-test counts before interpreting results |
| RF-035 | rehearsal input must match the ordinary live unattended producer in magnitude, duration, and provenance |

## Failed and rejected paths retained

- Synthetic motor recruitment proves only the downstream yaw helper; it cannot
  satisfy C-019 source-to-consequence acceptance.
- A layer-12 discharge without simultaneous current across its direct layer-11 contact proves an
  efferent event, not motor preparation.
- Public task 1018 already proves discharge, one yaw, and vestibular return; it
  does not by itself close C-019 because those facts are not causally bound to
  layer-11 preparation.
- A semantic action name, planner, score winner, or Python selection is not an
  acceptable replacement for the missing physical link.

## Translation-boundary review before first compile

- Native producer census: `MotorUnitRecruitment` is constructed only in
  `settle_internal_contact_interval`; empty observations are constructed at the
  quiescent/no-frontier branches and in test-only cognitive-capital fixtures.
- Native consumers: cognitive observation, multi-interval runtime aggregate,
  prepare receipt, PyO3 getter, and the read-only reservoir probe. The motor
  evidence is transient; no neuron, cognitive, world, or outer-state codec
  serializes it, so this sprint requires no schema reinterpretation or state
  migration.
- Boundary field map:
  `settled layer-11/layer-12 ElectricalContactTransition`
  -> exact directed `(sender, receiver, stable bond, carriers)`
  -> native recruitment `(motor lineage, topology, outward carriers,
  preparation transfers)`
  -> PyO3 nested tuple
  -> Python immutable tuple
  -> action-intent bytes and public prepared-recruitment record.
- Multi-hop behavior: the ordinary intake aggregate appends each sparse
  recruitment and preserves its preparation transfers. The later vestibular
  hop cannot overwrite them; the public motor-action record is built from the
  complete admitted transaction.
- Causal scope: only a positive layer-12 whole-carrier discharge accompanied
  by nonzero exact current across that motor's direct layer-11 contact can reach
  the actuator. The transfer direction remains the physical direction produced
  by the endpoint potentials. An unprepared discharge remains ordinary neuronal physics and
  produces no action event.
- Conservation: this change moves no additional carrier or energy and creates
  no retained state. The existing motor discharge supplies the action amount;
  the preparation transfer is exact causal evidence and is not added to that
  amount a second time.
- Added control/data structures: one sparse transient transfer vector per
  emitted motor recruitment. No Boolean gate, threshold, counter, owner, lock,
  database, cache, Python callback, or persistent object is added.
- Test/runtime provenance remains pending until the candidate native wheel is
  rebuilt and loaded under the exact task-1018 environment.
- First focused native compile failed before tests because the test-only
  `reservoir_probe` directly called `settle_internal_contact_interval` and the
  initial census searched only the parent Rust file. Disposition: the probe was
  updated with the same narrowed signature, and constructor/caller census
  commands must include the complete `native/guala_core/src` tree (RF-017). No
  runtime or production state changed.
- The immediately preceding-frontier hypothesis was falsified: the exact
  layer-11/layer-12 current was not there when the motor discharged.
- The same-interval one-way layer-11-to-layer-12 hypothesis was also falsified:
  the direct contact carried current in the opposite signed direction. The
  retained physics is an undirected dissipative contact whose two endpoint
  potentials jointly determine current. The implementation therefore binds
  the exact signed current across the direct layer-11/layer-12 contact and does
  not rewrite its direction into a fictional excitatory transmission.

## Live completion rule

`C-019` becomes **Live-Closed** only when the public production observation on
`dsf-ai.com` directly exposes one exact signed layer-11/layer-12 contact transfer bound
to the layer-12 recruitment that caused one committed body yaw, shows the
vestibular/sensory return from that same action, and preserves identity, cold
continuity, zero Python cognition callbacks, one live organism process, and
bounded resources. Local, candidate, rehearsal, ECS, HTTP, or source evidence
alone cannot close it.

## Public production closure evidence

- Release commit: `e0c39feac34d673baf753a2331b2478833a781dd`.
- Image: `sha256:5fc3d2848b0d6145cf4ae129a3b9da39b9e9d01d65c30d04fad1babc86c30205`.
- ECS task definition: `dsf-ai-task:1019`; one desired, one running, zero
  pending, one completed deployment, and one healthy container.
- Identity: `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`, restored from the same raw
  native CURRENT lineage.
- The public action record exposed eight prepared recruitments containing 32
  exact contact transfers. Every transfer had layer 11 and layer 12 as its two
  endpoints; both signed directions occurred and were preserved.
- One observed prepared action had disposition `applied`, expected and observed
  world revision 2310, resulting revision 2311, 75 millidegrees of exact yaw,
  one vestibular return tick, distinct before/after world-state receipts, and a
  causal-intent receipt that included the preparation transfers.
- Public organism tick advanced 71,879 to 71,897 with changing native state
  receipts, the same identity, and zero Python cognition callbacks.
- The cold candidate rehearsal restored production tick 71,789 byte-exact and
  preserved C-017/C-018 evidence. The live candidate then ordinary-restored the
  same current organism and continued it.
- Runtime bounds: task 1019 is hard-bounded to 4 vCPU and 16 GiB. CloudWatch
  service maxima sampled during cutover were 29.2477% CPU and 7.2998% memory.
  Public native state measured 43,432,378 bytes and then 43,432,033 bytes; it
  did not exhibit monotonic per-tick accumulation in the two closure samples.

This closes only C-019. It does not claim native choice, thought, autonomy,
speech, or C-020 articulation closure.
