# Guala A-013 native root-yaw sprint ledger

Date: 2026-08-27  
Active item: A-013, reopened by contradictory live production evidence  
Predecessor retained closed: A-009 continuous native action/consequence re-entry  
Production baseline: task `dsf-ai-task:1266`, commit
`eedc9e4268f98ba7a9b86edc954d0be4c98cee0b`, organism
`1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`

## Frozen input and acceptance

Input is one positive whole-carrier discharge from an internally reached,
explicitly mounted root-yaw layer-12 effector. Output is one signed virtual
yaw actuation of the sole persistent world body, followed immediately by the
exact visual, vestibular, proprioceptive, auditory, tactile, chemical,
thermal, and internal consequences physically applicable to that action in
the same resident organism. Cognition continues; no action selector, tutor,
observer, or semantic command participates.

Live acceptance requires an unattended retained or newly formed physical
cause to discharge a root-yaw terminal, change the persistent world's heading,
change at least one physically applicable receptor lane, return the signed yaw
trajectory through the mounted canal, retain the successor under the same
identity, and later produce at least one distinct unattended root-yaw action.
One tutor-authored turn may develop the afferent/efferent route but cannot
satisfy acceptance.

## Architecture honesty gate

1. Requested architecture: one continuously living organism can physically
   turn toward different sensory fields and learn from returned consequences.
2. Current code reality: native action settles only the 37 local articulated
   axes. `native_production_app.py` submits `AdvancePhysicalTimeCommand` on the
   environment port, supplies four zero root-displacement coordinates, and
   writes `root_motion=false`.
3. Conflict: yes.
4. Not extended: the retired topology-parity motor-to-yaw bridge, Python action
   selection, semantic destinations, local-neck-to-root inference, timers,
   random choice, observer causation, duplicate root pose, or external action
   APIs presented as autonomy.
5. Single next item: mount one explicit paired native root-yaw effector and its
   paired directional consequence receptors through the existing exact yaw
   and world action/consequence law.
6. DSF: unchanged full joint seven-field delivery.
7. Lost field structure: none.

## Implementation contract

- **Physical input authority:** positive whole-carrier outward discharge from
  a layer-12 neuron whose retained mount names exactly one root-yaw antagonist
  terminal.
- **Direction authority:** the retained terminal, developed only from a typed
  directional root-yaw proprioceptive ending whose value actually changed.
  Neuron index, topology parity, labels, and Python cannot choose direction.
- **Magnitude:** opposing terminal carriers cancel exactly; remaining whole
  carriers are signed millidegrees because one millidegree is the declared
  virtual yaw lattice quantum. No gain or threshold is introduced.
- **World authority:** `EmbodimentWorld` remains the sole root heading owner.
  The existing native minimum-jerk yaw law supplies the exact signed path;
  `MoveCommand` changes heading at the current root position.
- **Conservation:** no neuronal carrier is copied. Discharged carrier counts
  are consumed once as effector work; signed yaw sums exactly to the net whole
  carrier count. Root pose exists only in the world.
- **Preparation/commit:** native cognition and root drive are prepared first;
  the world successor and complete consequence occurrence are prepared before
  either world or organism becomes visible. Commit preserves the existing
  at-most-once world/organism ordering; refusal discards both preparations.
- **Rollback/crash:** a committed world successor is rolled back to its exact
  predecessor if organism persistence fails. An uncommitted preparation is
  dropped. Restart reads the single persisted world and organism successors.
- **Cold restore:** old source and neuron codecs decode with no root terminal.
  New codecs persist typed root afferent and efferent terminals; no old byte is
  reinterpreted as root anatomy.
- **Work bound:** O(R) over reached root-yaw recruitments plus the already-fixed
  one-millisecond yaw trajectory and applicable receptor roster; invariant
  under unrelated neurons, contacts, formations, and objects.
- **Retired path:** native action may no longer hard-code zero root displacement
  when a root terminal discharged. The external `/world/move` endpoint remains
  tutor/person-authored and cannot prove autonomy.

## Current evidence and rejected paths

- Passive live samples advanced tick `192926 -> 193050` in 15 seconds with no
  stimulus. Both observations repeated the same 14 local-axis set and the same
  emitted pressure digest. Root motion remained false; choice and curiosity
  remained awaiting witness; native thought remained unmounted.
- The world held pose `(2300,3500,0)` with no held object. The latest internal
  retained-formation path caused a local cheek effector and returned body
  consequences, proving A-009 remains live while A-013 root action is absent.
- Rejected permanently: restoring `_prepare_motor_yaw_action` or any equivalent
  rule that maps arbitrary motor topology or parity to yaw.

## Authorized source boundary

The initial root-yaw slice may change only the exact typed source/mount/runtime
and existing world handoff files needed for this path:

- `native/guala_core/src/virtual_body_yaw_motion.rs`
- `native/guala_core/src/root_yaw_joint_source_builder.rs`
- `native/guala_core/src/proprioceptive_receptor_work.rs`
- `native/guala_core/src/joint_source_episode.rs`
- `native/guala_core/src/neuron_source_anchor.rs`
- `native/guala_core/src/reached_neuron_cohort.rs`
- `native/guala_core/src/resident_cognitive_formation.rs`
- `native/guala_core/src/organism_runtime.rs`
- `native/guala_core/src/lib.rs`
- `dsf_ai_service/glew_runtime/native_resident_organism.py`
- `dsf_ai_service/native_production_app.py`
- focused tests for this exact path

Existing receptor fixture files may receive only the explicit `None` value for
the new typed root terminal field; they gain no new production behavior.

No deployment or completion claim exists yet.

## Candidate proof before cutover

- `cargo check --lib`: passed.
- Root directional receptor work: 2 focused Rust proofs passed, including a
  sign-tampered physical-evidence refusal.
- Native action/world handoff and existing physical-choice observation: 26
  focused Python proofs passed.
- `python -m py_compile` for both changed Python owners: passed.
- `git diff --check`: passed.

These are candidate proofs only. A-013 remains open until the deployed resident
organism develops the route from one tutor-authored physical turn and later
produces a distinct unattended root action with returned consequences.

## Deployment recurrence table

Only checks that can affect this root-action release are carried here. A pass
means the named boundary was directly observed; `pending` forbids packaging or
cutover until it becomes an exact result.

| ID | Applicability and earliest check | Observed evidence |
|---|---|---|
| RF-001/002 | Exact worktree and live task environment precede every Python import. | Production task/environment census passed; candidate-native provenance remains pending. |
| RF-003/036 | Build and force-install one fresh candidate wheel, then print its path and root-yaw symbol. | Pending before end-to-end replay. |
| RF-004 | Run the root source-to-consequence path on pristine state and the authenticated production predecessor. | Pristine focused proof passed; production-predecessor replay pending. |
| RF-005/018/028/038/046/050 | Trace root evidence through every ordinary and specialized-hop aggregation boundary. | Focused Python aggregate proof passed; immutable mixed-hop replay pending. |
| RF-006 | Reuse the exact 4-vCPU/16-GiB task envelope and validate all strict resource relations before restore. | Live task definition `1266` re-read as 4096 CPU/16384 MiB; restored probe pending. |
| RF-007/023/033 | Resolve controller, interpreter, account, region, cluster, service, task, and image from observed inventory. | Preflight passed for account `418384447921`, `us-east-1`, `tfe-web-cluster`, `dsf-ai-service-lb`, task `1266`. |
| RF-010/022/056 | Cold-restore old bytes, persist the root-capable successor, re-read `CURRENT`, then start one further interval under the same identity/tick lineage. | Pending. |
| RF-012/020/021 | Require the real resident source to create root discharge and observe the exact resulting world/body successor; counters or injection do not pass. | Backend conversion proved only; live source-to-consequence remains the A-013 acceptance gate. |
| RF-016 | Bind the release to A-013 and retain A-009 as its live-closed predecessor. | Reconciled in this ledger; candidate diff contains only root source/mount/handoff plus release evidence. |
| RF-017/030/037 | Census constructors, wrappers, aggregators, equality projections, and boundary-handle methods for each changed native type. | Rust crate and focused Python consumers compile/pass; exact candidate boundary replay pending. |
| RF-024/031/032 | Resolve test paths/names and working directories; require nonzero executed tests. | Root Rust proof executed 2 tests; Python proof executed 26 tests. |
| RF-025/029 | Derive the live tutor action from the current predecessor in one operator session; inspect successor before any retry. | Pending live cutover action. |
| RF-035/042/054 | Use a production-sized signed yaw, prove positive/negative/zero semantics, and tolerate consistent stalled rows while retaining actual displacement. | Signed native source proves positive and negative direction plus tamper refusal; production-sized replay pending. |
| RF-048 | Cold-restore the exact production world under candidate limits and exercise the live read-only world path. | Pending before immutable build. |
| RF-056 | Authenticate identity/tick before draining and require the candidate to restore the same identity at or beyond that tick. | Baseline identity `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`; cutover proof pending. |

The production preflight at candidate commit `4e3b1bdb` observed one healthy
owner on task definition `1266`, image digest
`sha256:c68fa7b99dc61b027b29539baf95316164c3bf05a1346b023c22c53e6aa0b3a4`,
and HTTP 200 from both public pages. Those facts establish the target only;
they are not A-013 behavior evidence.
