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
- `native/guala_core/src/root_yaw_terminal.rs`
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
| RF-057 | Pass world consequence and root proprioception as separate top-level intake items, never a nested compound item. | First copied-live replay exposed and refused the nested shape after world commit; corrected replay returned HTTP 200, changed heading by exactly 1 millidegree, changed 197 receptor lanes, and completed 78 causal hops. |

The first final-candidate native library gate executed 506 tests: 501 passed,
five failed, and ten were ignored. Each failure was reproduced at the exact
deployed predecessor commit `eedc9e4268f98ba7a9b86edc954d0be4c98cee0b`.
The release gate was repaired instead of bypassed: stale whole-body/scheduler
expectations now describe the causal-frontier law; different persistence
histories are no longer mislabeled as different organism physics; and one real
defect that collapsed distinct three-sense assemblies sharing two members was
corrected to require exact assembly equality. The complete native gate now
passes 658 executed tests across the library and integration targets with zero
failures. The focused Python action/consequence gate passes five tests.

The first controller attempt stopped before rehearsal because the standalone
yaw proof crate inherited an articulated-body dependency from the new terminal
types. Fixed root terminal anatomy now has its own production owner while yaw
trajectory settlement remains an independent mechanical primitive; the narrow
proof crate passes 94 tests. The Python boundary also now admits the native
one-time 74-port whole-body initialization source exactly once and continues
to refuse any other unrequested source.

The production preflight at candidate commit `4e3b1bdb` observed one healthy
owner on task definition `1266`, image digest
`sha256:c68fa7b99dc61b027b29539baf95316164c3bf05a1346b023c22c53e6aa0b3a4`,
and HTTP 200 from both public pages. Those facts establish the target only;
they are not A-013 behavior evidence.

## Copied-live-body replay

The candidate native wheel was built in release mode and loaded from the fresh
isolated path `/tmp/guala-a013-wheel-install.AZycjqXo/guala_core/__init__.py`;
the new root-source symbol was present. The latest available copied production
body/world restored identity `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`, tick
`186598`, state `3f284090...e1`, world revision `13156`, and heading `341565`.

The first replay found RF-057: the world committed a one-millidegree turn but
the nested admission shape made cognition refuse the consequence. After the
source correction, a fresh replay from the same predecessor returned HTTP 200,
changed the world heading exactly `341565 -> 341566`, changed 197 receptor
lanes across body, sight, smell, sound, taste, and touch, and completed 78
native causal hops with no Python cognition callback.

The exact successor was then sealed and cold-restored. After 24 unattended
lived moments it reached tick `187391` and state
`a735cfa24af48a237af2d257689ad1d030ea0ca4d8fc7e750b2491413f4f3c34`.
An opposite two-millidegree physical turn then returned through the same path;
four more unattended moments sealed at tick `187532` and state
`183ed5149e4ed039a0250a71bad4785d8639183edce048a5575c06e524efe6bc`.
No unattended root discharge occurred in those 28 sampled moments. This proves
the typed action/consequence and cold-restore pathway on a mature copied body,
but it does not satisfy the A-013 autonomous-action acceptance condition.

## Live root-reflex correction — 2026-08-27

- **Active item:** A-013 remains reopened; A-009 remains live-closed because
  task `1272` continued native articulated actions and returned their exact
  proprioceptive and multisensory consequences without pausing cognition.
- **Production baseline:** task `dsf-ai-task:1272`, source commit
  `c024a6feaf823c5c6dea6eae7f575c15f976ad46`, one desired/running task,
  zero pending tasks, one completed PRIMARY deployment, organism identity
  `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`.
- **Live contradiction:** after one tutor-authored signed turn, twelve passive
  samples from 18:42:12 through 18:53:23 UTC advanced the most recent native
  transition tick `199347 -> 199843` and world revision `14964 -> 14997`.
  Articulated motor activity varied, but pose remained `(2300,3500,0)` at
  heading `341565`; every sample reported zero root-yaw recruitments.
- **First causal source defect:** the guided turn mounts the exact paired
  layer-8 regulation -> layer-12 root-motor contact, but ordinary recruitment
  calls `exact_motor_preparation_transfers` with an empty permitted layer-8
  set for root motors. The filter consequently rejects the exact reflex
  transfer it was built to carry. Articulated motors pass their exact reacted-
  load regulation lineages through this same boundary.
- **Frozen correction:** derive each root motor's permitted layer-8 lineage
  only from its mounted motor -> regulation -> integration -> typed root-yaw
  proprioceptor path, require that receptor's paired effector terminal to equal
  the motor terminal, and pass only those exact lineages to the existing
  preparation filter. No new contact, selector, threshold, timer, score,
  semantic label, or DSF change is authorized.
- **Exit evidence:** the focused falsifier must prove that the paired root
  regulation transfer is accepted and a different layer-8 transfer is refused;
  live acceptance remains an unattended root discharge followed by changed
  world heading and returned signed visual/vestibular/body consequences.
- **Focused source result:** the production path derives reacted-load and
  directional-root permissions from one shared physical-path traversal per
  reached motor. Release-mode test
  `moved_root_terminal_mounts_only_its_paired_sensorimotor_reflex` passed
  `1/1`: the terminal-paired regulation was admitted and the mounted opposite
  antagonist was refused. `git diff --check` and the deployment shell syntax
  check passed.
- **Cutover correction:** hot deployment now installs the candidate as the
  sole completed ECS deployment while desired count is zero, then starts that
  already-selected candidate without `force-new-deployment`. This prevents an
  older retained deployment from becoming a writer again after cutover.
- **Separate later defect:** direct grounded-world audio requests timed out and
  left no new native transition evidence even for a 250 ms sample. It does not
  block the frozen root-yaw correction and is not being folded into this edit.

## First cutover result and causal-arrival correction — 2026-08-27

- Commit `a5a82cb62c196c6ab5a1db67322087f8d2ffe0b6` deployed as the sole
  live task `dsf-ai-task:1273`; identity and state continuity verified at or
  beyond tick `200268`. The corrected zero-writer registration removed task
  `1272` before starting `1273`, so no rejected deployment remained eligible.
- The first correction was necessary but insufficient. Unattended samples at
  ticks `200640` and `200702` still reported zero root recruitments and heading
  `341565`. A read-only cold view of CURRENT at tick `200919` proved exactly
  74 layer-12 intrinsic motors—the articulated-body terminal count—and no
  additional retained root motor.
- One tutor-caused physical turn (`chose_to_go=false`) then settled heading
  `341565 -> 341566`, world revision `15072`, 13 causal hops and successor tick
  `201043`. Its sensory delivery was accepted, but CURRENT still contained
  exactly 74 layer-12 motors. Therefore the earlier guided turn was not merely
  lost during a prior restart: the mounted root-motor boundary was impossible.
- **Exact second defect:** directional root evidence and layer-8 arrival were
  required in the same interval even though the ratified electrical frontier
  advances one contact per physical interval. The root receptor -> layer-6
  integration transfer and the later integration -> layer-8 regulation
  transfer can never occupy the same causal window.
- **Exact correction:** terminal identity now comes from the mounted root
  receptor on an exact two-interval directed path: predecessor frontier
  receptor -> integration, then current whole-carrier integration ->
  physically transitioned regulation. Same-interval coincidence is refused;
  no current-source label, timer, score, command or widened motor authority is
  admitted. The existing paired regulation -> motor reflex remains the only
  developed contact.
- Release-mode focused proof passed `1/1`, including explicit refusal without
  the predecessor hop and exact acceptance with the consecutive physical path.
  Live acceptance remains open until CURRENT retains the new motor and an
  unattended discharge changes heading with returned sensory consequences.

## Causal orientation correction — 2026-08-27

- Commit `0d40506f89b7f216cca52943334e0b71b9848d66` deployed as sole
  task `dsf-ai-task:1274`, continuity verified at or beyond tick `201446`.
  A fresh tutor-caused root turn settled at tick `201570`; by tick `201671`,
  CURRENT still held only the 74 articulated layer-12 motors.
- Read-only CURRENT neuron evidence identified the two retained root chains.
  Their moved receptor membranes were negative (`-2140`, `-3588` elementary
  charges), their layer-6 integrations were `-544` and `-494`, and their
  layer-8 regulations were positive (`12`, `18`). Thus whole carriers lawfully
  flowed toward the more-negative receptor while the receptor's potential
  perturbation causally advanced away from it.
- The second correction wrongly equated carrier sender/receiver with causal
  frontier direction. The existing `frontier_lineage` field already preserves
  the advancing endpoint separately for exactly this case.
- **Exact correction:** require the predecessor entry's advancing frontier to
  be the mounted layer-6 integration, verify its other physical endpoint is the
  typed root receptor, then accept a nonzero current layer-6/layer-8 transfer
  in either carrier direction only when the layer-8 regulation is the newly
  causal endpoint. No causal direction is inferred from current sign.

## Current-frontier authority correction — 2026-08-27

- Commit `f3b11a5b7e0b6839cb2e1497df07c821d6d52e75` is live as sole task
  `dsf-ai-task:1275`, with identity continuity preserved. A tutor-caused turn
  settled the world at heading `341569`, but CURRENT still retained exactly
  the 74 articulated layer-12 motors and no root motor.
- A bounded read-only restore at tick `202865` found no current frontier entry
  advancing from the six mounted root receptor/integration/regulation cells.
  This observation is expected after later autonomous intervals and cannot by
  itself identify the interval-local break.
- **Exact remaining source defect:** `next_active_frontier` correctly marks the
  previously unseeded contact endpoint as the causal advance independently of
  carrier sign. The root continuation nevertheless received
  `causally_transitioned_lineages`, whose construction still admits a far
  endpoint only when carriers move away from the seed. On the measured live
  root anatomy, carriers move back toward the negative receptor, so the exact
  layer-8 arrival was discarded before motor development.
- **Frozen correction:** join the predecessor receptor-to-integration entry to
  the current integration-to-regulation entry by exact bond, directed carrier
  transfer, and explicit `frontier_lineage == regulation`. Admit that same
  regulation into root motor development from this joined causal fact, not
  from the carrier-oriented transition list. No observer data, timer, score,
  label, new contact law, or DSF value enters the transition.
- **Translation/conservation review:** both inputs are native transient
  `ActiveElectricalFrontierEntry` values already produced by the one contact
  settlement. The join copies no state, changes no charge/work/heat, and adds
  no Python/native field. A missing predecessor entry, missing current entry,
  mismatched transfer, wrong frontier endpoint, untyped receptor, or opposite
  terminal still authors nothing. The focused falsifier must prove reverse
  carrier direction succeeds only with both exact causal frontier entries.
- **Focused result:** release-mode library test
  `moved_root_terminal_mounts_only_its_paired_sensorimotor_reflex` executed
  `1/1` and passed. Its current transfer carries charge from regulation back
  toward integration while the explicit frontier advances to regulation; the
  paired root motor is mounted only when both consecutive frontier entries are
  present. `git diff --check` passed.
- **Live result — rejected:** commit
  `93b235874a3ea7a8ce0df0180975ae0a84055b17` deployed as the sole production
  task `dsf-ai-task:1276`, image
  `sha256:8132d732bb413904f7d50de4476f04ade1fa2f6d1a26cb01459513977a8fae5b`,
  with identity continuity verified at or beyond tick `203609`. A physical
  one-millidegree tutor turn settled heading `341569 -> 341570`, returned HTTP
  200, completed eight causal hops, and reported successor tick `203764`.
  A later exact CURRENT restore at tick `203865` still contained only 74
  layer-12 neurons. No root motor was retained; A-013 remains open and this
  candidate's current-frontier requirement is falsified by live production.
- The immutable generation named by the move response had already left the
  bounded local generation set before the read-only inspection, so its exact
  transient root frontier could not be recovered after the fact. No further
  causal condition is being inferred from the later CURRENT head.

## Exact frozen-body frontier result and direct anatomy correction — 2026-08-27

- Commit `968c1a47bd32753fcc5dd456ba33b49cd782cdd8` deployed as sole
  production task `dsf-ai-task:1277`, image
  `sha256:0edcb9dadf6b72a65a74ea0f98588a3d5355ddaa2afb687f643ddbeaa36e2234`.
  Independent ECS and `/ready/guala` reads proved one healthy task, the exact
  commit and digest, the same organism identity, and continuity beyond tick
  `204958`.
- One tutor-authored one-millidegree turn settled heading `341571 -> 341572`,
  returned HTTP 200, delivered all six mounted sense families through seven
  hops, and published exact generation `c74621fb...b7abe0` at tick `205082`.
  A read-only cold inventory of that exact CURRENT still contained 74 layer-12
  neurons: no root motor was retained, so the candidate was live-rejected.
- The exact 76,203,478-byte generation was recovered from immutable custody
  and decoded locally. Its older, preceding, and active electrical frontiers
  contained 958, 1,713, and 958 entries respectively, but **zero** entries
  involved either root receptor, integration, or regulation chain. Therefore
  the two-interval frontier certificate required evidence production never
  emitted; extending that certificate again is prohibited.
- The governing A-013 contract already supplies the direct physical authority:
  a typed directional root proprioceptor whose value actually changed and its
  topology-paired reached regulation. The replacement derives only that exact
  receptor -> local integration -> regulation anatomy, validates both contacts,
  and mounts the paired root motor after settlement. Anatomy alone, a changed
  receptor without its reached regulation, an opposite terminal, labels,
  observers, scores, timers, or Python cannot authorize the motor.
- Focused release proof
  `moved_root_terminal_mounts_only_its_paired_sensorimotor_reflex` passed `1/1`.
  It explicitly refuses anatomy without a changed receptor, refuses a changed
  receptor without its reached regulation, mounts exactly the paired terminal
  when both physical facts exist, and continues to refuse the opposite
  antagonist during later motor preparation. Full joint seven-field DSF and
  every charge/work/heat settlement remain unchanged.
- Commit `5098e6b39cd6f5cd4bc2af40ad32d39ac90e3b14` deployed as sole
  production task `dsf-ai-task:1278`. Its first tutor turn moved and persisted
  the world, but the sensory transaction returned HTTP 503 and CURRENT stayed
  at 74 layer-12 neurons.
- Exact frozen-body reproduction proved the native sequence itself was lawful:
  vestibular settlement succeeded, root proprioception grew the resident body
  from 1,373 to 1,374 neurons, and its returned body consequence also settled.
  Only the final canonical seal failed with `resident neuron lineage authority
  changed` and caused the service wrapper to roll the valid growth back.
- The seal validator was stale: it required every layer-12 neuron to carry an
  articulated-joint terminal. It now accepts exactly one typed articulated or
  root-yaw effector terminal and still rejects missing, mixed, or duplicate
  authority. The same exact sequence now seals at 1,374 neurons; focused root
  development proof remains `1/1`. Live task-1278 is not credited with the
  correction; a new cutover and live retained-root witness are still required.

## Retained root motor and membrane-discharge correction — 2026-08-27

- Commit `a2424e23643a8999753cdf50947bd59039c55fd6` is live as sole task
  `dsf-ai-task:1279`, image
  `sha256:320f42ac179e736ffd5e60faca4ae9400db975e47922ded5f7a41d4dec92672d`.
  One tutor-authored one-millidegree turn returned HTTP 200, moved heading
  `341573 -> 341574`, delivered all six mounted sense families through seven
  hops, and retained 1,374 neurons. Exact CURRENT cold restore proved 75
  layer-12 neurons, so the typed root motor now survives seal and restart.
- A second tutor turn moved heading `341574 -> 341575` and again returned the
  complete sensory occurrence. Later unattended transitions emitted local
  articulated actions but no root action; the world heading remained
  `341575`.
- **Exact remaining physics defect:** motor preparation requires contact
  transport arriving at the motor. Recruitment nevertheless reused that same
  contact's net outward transport as the motor's supposed membrane discharge.
  A root motor has one regulation contact, so incoming preparation necessarily
  made its contact-net outward value negative while recruitment required it to
  be positive. The retained root motor could therefore never emit.
- **Frozen correction:** `complete_neuron.rs` now carries the already-settled
  local membrane whole-carrier transport as a transient interval fact;
  `reached_neuron_cohort.rs` carries it only for reached resident neurons; and
  `resident_cognitive_formation.rs` uses a positive local membrane discharge
  plus the independently exact incoming preparation transfer for articulated,
  root-yaw, and articulatory effectors. Contact transport is no longer
  relabelled as efferent output. No carrier, energy, state, DSF field, owner,
  observer, selector, threshold, timer, or persistent byte is added.
- The exact membrane fact requires adding `native/guala_core/src/complete_neuron.rs`
  to this sprint's source boundary; it is the existing physical settlement
  owner and no duplicate membrane calculation is introduced elsewhere.
