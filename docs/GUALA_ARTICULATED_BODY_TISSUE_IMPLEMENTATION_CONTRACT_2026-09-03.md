# Guala bounded antagonist-tissue implementation contract — 2026-09-03

## Status and one item

This is the source-freeze contract for one correction only: replace the
Phase-1 virtual articulated body's permanent position accumulator with bounded
antagonist activation and passive overdamped return. It authorizes a source
candidate and copied-production-body proof. It does not authorize deployment
or claim autonomous action.

Production remains task 1425 while this candidate is built. The mature proof
input is the read-only task-1425 body at tick 408275, raw SHA-256
`27555e9d78511e28a956cec3dca282a2509fbc92b8e7c83f1aa16ea63825e8e2`.
The task-1420 body at tick 391305, raw SHA-256
`207ced0a3d0d2253a7520e05bf18eeebcf3caf25fd2b83c6450bcaf08ee86e3b`,
remains an independent historical control.

## Architecture honesty gate

1. **Requested architecture:** one organism-owned deterministic motor event
   excites bounded body tissue, changes physical pose, relaxes, and returns its
   actual proprioceptive/load consequence through the same organism.
2. **Current code reality:** motor terminals work, but carrier count is added
   permanently to joint position. Seven copied positions are non-neutral hard
   stops and ordinary retained traffic still pushes into them.
3. **Conflict:** yes. The current plant is an undamped accumulator, not tissue.
4. **Mechanisms not extended:** the accumulator equation; reset-to-neutral;
   timer or shell pose control; passive symmetric L11-L12 coupling; broad motor
   fan-out; neuronal reservoir as vigor; altered L0-L4 or flattened DSF.
5. **Single item:** implement and copied-body-falsify the bounded 32-ms
   antagonist-tissue plant defined below.
6. **DSF scope:** body mechanics is downstream of complete neuronal delivery;
   it neither evaluates nor changes DSF.
7. **Field loss:** none.

## Ratified Phase-1 energy boundary

`GUALA_A013_PHYSICAL_BODY_PART_SELECTION_SPEC_2026-08-16.md` already declares
the Phase-1 virtual body's carrier-to-lattice-displacement relation as its own
constitutive physics. Detailed motor torque, ATP, transmission efficiency and
mechanical-work conversion are explicitly deferred until a physical body is
selected. Therefore this correction must not duplicate the motor neuron's
released electrical work into a second invented body-energy reservoir.

The existing terminal settlement and recovery-fluid thermal return remain
unchanged and conserve the motor neuron's electrical work. The body receives
the same typed terminal and whole-carrier count it receives now. Carrier count
creates bounded virtual tissue activation rather than permanent position.

## Material preparation and exact law

The fixed body clock is 1 ms. One uniform Phase-1 virtual antagonist-tissue
preparation is declared for the existing generic 45-axis body:

- activation lifetime: 32 ms;
- overdamped response time: 32 ms;
- carrier coupling: one whole admitted carrier to one whole activation;
- per-direction activation capacity: that direction's declared neutral-to-stop
  span multiplied by 32 activation units.

The 32-ms preparation is not selected from a pleasing output. It lies inside
the copied-body accepting region and is anchored to measured laryngeal muscle
physics: canine PCA/LCA/IA posturing muscles have approximately 30-33 ms mean
twitch contraction times and approximately 19-29 ms half-relaxation times;
vocalis measurements span 22-32 ms contraction and 17-37 ms half relaxation.
The current virtual body has no per-axis material classes, so one declared
generic tissue is used rather than invented action-specific constants.

For each antagonist terminal `d`, retain fixed integer activation `a_d`.
For one represented millisecond:

1. Opposed newly discharged carriers cancel locally and become reacted load.
2. Each remaining carrier admits 32 activation units, limited by
   `directional_span * 32`; excess carriers are stalled load.
3. `ceil(a_d / 32)` is that terminal's current whole activation.
4. The axis equilibrium is
   `clamp(neutral + activation_max - activation_min, minimum, maximum)`.
5. Position advances toward equilibrium by
   `ceil(abs(equilibrium - position) / 32)` lattice quanta and never crosses it.
6. Each activation loses `ceil(a_d / 32)` units.

New discharge is admitted once at the beginning of the supplied elapsed span.
The six steps then repeat once per exact 1-ms body clock. Elapsed duration must
be a positive multiple of 1 ms and cannot exceed the existing represented
250-ms causal-interval ceiling in one call. Running 64 ms followed by 186 ms
must produce the same successor as running 250 ms once.

The law has no target pose, action name, motor table, score, controller,
history, floating point, stochastic term, or coefficient chosen by sound.

## Inputs and outputs

Input:

- one validated `ArticulatedBodyState`;
- at most one discharge count for each of the 90 already-typed antagonist
  terminals;
- exact elapsed body time in microseconds.

Output:

- one successor body with the same 45 position axes, lung, proprioception flag,
  acoustic state, and 90 bounded activation integers;
- at most one sparse `BodyProprioceptiveConsequence` per changed or reached
  axis;
- exact reached-terminal count.

The consequence tuple keeps its current fixed representation. Its meanings are
made explicit:

- `toward_minimum_carriers` and `toward_maximum_carriers` are new terminal
  discharges in this interval;
- `opposed_carriers_per_terminal` is their exact local cancellation;
- `applied_displacement_quanta` is absolute total position displacement,
  whether active, passive, or both;
- `stalled_carriers` is unopposed new discharge not admitted because the fixed
  activation capacity was full or the declared directional span was zero.

The old accidental identity
`applied_displacement_quanta + stalled_carriers == net discharged carriers`
is retired. The invariant becomes `stalled_carriers <= net discharged
carriers`, while applied displacement remains exactly
`abs(successor_position - predecessor_position)`.

Passive return has zero motor discharge, zero opposed load and zero stall. Its
position change enters ordinary proprioception but can never be returned by
`exact_moved_effector_terminal` as a motor cause. A motor terminal is returned
as a same-interval moved cause only when non-stalled activation was admitted
and position changed in that terminal's direction.

## Mutation, commit, refusal, and crash order

`settle_body_effector_drives` prepares all additions, capacity results,
positions, activation decay, and consequences in local fixed state. Any bad
duration or arithmetic width refuses before the caller publishes a successor.
The predecessor is never mutated.

The existing runtime then performs its unchanged atomic order:

1. settle cognition and obtain typed motor recruitments;
2. settle the body candidate from the predecessor body;
3. create sparse body-sense source bytes from the actual consequences;
4. encode the cognitive and body successor into one pending fabric;
5. seal/commit through the existing current-only transaction.

Abort or crash before head advance retains the predecessor. Restore never
replays a discharge. No activation or passive step exists outside the encoded
body candidate.

## Persistence and one-way migration

Body V8 appends exactly 90 `u32` activation values to the fixed body state.
Maximum directional span is bounded by declared anatomy; multiplied by 32 it
fits `u32`. Current V7 decode preserves every position, lung value,
proprioception flag, and acoustic byte and initializes only the nonexistent
activation array to zero. No position is reset or rewritten during decode.

V8 encode/decode preserves positions and activations exactly. The outer fabric
already asks the nested body header for its encoded length, so no duplicate
fabric version or fallback decoder is added. The first lawful successor is V8;
V7 remains decode-only migration input and can never be emitted again.

## Work and resource bounds

Settlement scans the fixed 45 body axes once per reached native interval and
per exact elapsed millisecond. This is `O(45 * elapsed_ms)` with a fixed maximum
of 90 input terminals and at most 45 consequences. Normal production calls
carry one 1-ms step. State grows by exactly 360 bytes and never with organism
age, event count, motor count, or history.

No rational activation, event queue, expiry record, sample history, neuron
scan, world scan, dynamic body topology, callback, thread, or process is added.
When position is neutral and all activation is zero, the fixed scan emits no
consequence and changes no state.

## Authorized source slice

Production mechanism:

- `native/guala_core/src/virtual_articulated_body.rs`
- `native/guala_core/src/articulated_body_joint_source_builder.rs`
- `native/guala_core/src/proprioceptive_receptor_work.rs`
- `native/guala_core/src/virtual_articulatory_body.rs`
- `native/guala_core/src/organism_runtime.rs`
- `native/guala_core/src/resident_cognitive_formation.rs` only where the exact
  moved-terminal evidence is consumed or its native tests construct the fixed
  consequence type
- `dsf_ai_service/glew_runtime/native_resident_organism.py`
- `dsf_ai_service/native_production_app.py`

The articulatory source is inside the boundary because its inherited spectral
path incorrectly bounded respiratory excitation by same-interval visible
displacement. Under damped tissue, multiple admitted closing carriers can
lawfully produce one first-millisecond lattice step. Spectral excitation must
therefore use the unopposed, unstalled new closing activation (capped by the
existing acoustic-organ capacity) while the actual persisted glottal position
continues to govern airway conductance. Direction-opposed, fully stalled, and
passive return motion supply no new respiratory work.

Falsification and history:

- the focused native tests colocated with those modules;
- `native/guala_core/src/resident_cognitive_formation/reservoir_probe.rs`;
- test-only call-site adaptation in `neuron_source_anchor.rs`;
- focused Python boundary tests only where the unchanged 11-field consequence
  tuple is validated, including `tests/test_native_a007_physical_choice.py`;
- `tests/test_native_a009_action_consequence.py`, solely to falsify passive
  tissue being misclassified as grasp/release or refused for lacking a new
  motor discharge;
- the three 2026-09-03 motor-tissue documents.

No other file is authorized. A required additional production file is an
architectural finding and rejects this contract before compilation.

## Predecessor paths retired

- direct permanent `q[n+1] = clamp(q[n] + u_max - u_min)` settlement;
- quiescence defined as exact preservation of an off-neutral unpowered pose;
- inference that total displacement must equal same-interval net discharge;
- inference that any observed passive position change names a motor cause;
- decode-time neutralization as recovery;
- rational activation fractions whose denominator grows with lifetime.

V7 decode remains solely for current-state migration. No old accumulator may
remain production reachable after V8 settlement is compiled.

## Predeclared copied-body acceptance

The unchanged exact copied body must fail the predecessor by retaining all
seven pins and must pass the candidate only when all of the following hold:

1. V7 decode preserves all current bytes represented by body fields and adds
   only zero activation; V8 cold restore is exact.
2. With no reset, all seven pathological stops begin monotonic release on the
   first 1-ms interval and return to neutral without crossing it.
3. The one-carrier learned section-0 and section-7 discharges each create one
   bounded 32-ms movement and later return to neutral.
4. Connected L11-to-L12 test transduction produces only the two learned motor
   lineages; severing produces neither and leaves reflex traffic unchanged.
5. Passive movement returns through position receptors but creates no learned
   moved-terminal cause. Active same-direction movement returns its exact
   terminal cause. Stop pressure remains exact load evidence.
6. Equal new antagonists do not move the axis. One carrier/ms sustained drive
   remains interior. Higher drive saturates activation and creates bounded
   stall without counter growth.
7. `64 + 186 == 250` ms exactly for position and activation.
8. L0-L4, full DSF fields, neurons, sensory residues, formations, mosaics,
   learned contacts, world bytes, identity, and predecessor custody are
   unchanged except for causally returned body experience.
9. The next ordinary interval after cold restore continues from the exact V8
   tissue state; it neither resets nor repeats a motor discharge.
10. Peak memory, runtime, encoded size, allocations, process count, file count,
    and storage slope remain bounded; the harness leaves no process.
11. Read-only AWS snapshots immediately before and after the mature harness
    show the exact live task/image and classify every alarm and CPU/memory
    window without touching production.
12. Passive or retained-activation body travel returns through ordinary
    proprioception and advances world time, but cannot be labeled a new motor
    act or authorize grasp, release, or page advance without same-direction
    newly admitted grip activation.

Only after source freeze, one source-only review, compilation, focused tests,
and this complete mature copied-body proof may a deployment candidate exist.
The upstream intrinsic L11-to-L12 excitability defect remains separate: this
plant makes valid motor discharge move; it does not manufacture the discharge
or prove autonomous initiation.

## Active delivery and recurrence gate

Stable delivery ID: `MOTOR-TISSUE-V8-01`. The closed predecessor is live task
1425 at commit `ae260276a8bbf3afd018c149871b21fa8ba185e2`. Acceptance is one
newest authenticated production body whose existing motor discharge produces
bounded tissue movement and truthful sensory return, whose unpowered displaced
tissue releases without reset, and whose exact successor survives persistence,
cold restore, and another ordinary interval with flat resources. No speech or
autonomy claim is part of this release.

The following previously observed recurrence failures are active preflight
gates. `closed` means direct evidence already exists on this candidate;
`pre-artifact` and `live` must close at those later gates.

| ID | State | Required evidence for this release |
|---|---|---|
| RF-001 | closed | Exact worktree is first on `PYTHONPATH`; 37 focused shell tests executed. |
| RF-002 | pre-artifact | Export the observed task-1425 environment before first candidate-image import. |
| RF-003 | pre-artifact | Build/install one exact wheel and print its loaded extension path and provenance. |
| RF-004 | closed | Pristine fixtures and two authenticated production bodies pass; cold repeats are byte-identical. |
| RF-005 | closed | Exact motor, body, receptor, DSF, severance, and passive-return evidence is enumerated in this contract. |
| RF-006 | closed | Probe ceilings are 3 GiB/300 s; fixed V8 growth is 360 bytes; no runner survives. |
| RF-007 | closed | Missing `/usr/bin/time` attempt is recorded; available `prlimit`/`timeout` invocation passes. |
| RF-010 | pre-artifact | Candidate successor must become exact `CURRENT`; cold restore then advances one ordinary interval. |
| RF-012 | live | Require actual body release/movement/sensory evidence, not health counters. |
| RF-013 | closed | Changed-file formatting only; inherited formatting is not a release gate. |
| RF-015 | pre-artifact | Detect environment and use an explicit freshly built wheel, never assumed `maturin develop`. |
| RF-016 | closed | One item, one exact live baseline, complete diff reconciled above. |
| RF-017 | closed | Every constructor, codec, wrapper, body-source consumer, observer, and world-action caller was enumerated; the missed passive shell caller was corrected before packaging. |
| RF-019 | pre-artifact | Map every candidate-rehearsal assertion to this item and remove no valid assertion to force passage. |
| RF-021 | pre-artifact | Evaluate the exact successor produced by the declared motor/body input. |
| RF-022 | closed | V7 preserves every old field; V8 activation encodes, restores, and remains bounded. |
| RF-023 | pre-artifact | Fetch task environment unfiltered, validate names, then filter locally. |
| RF-024 | closed | All focused targets were resolved in this exact worktree and executed nonzero. |
| RF-026 | closed | Rust formatter expansion was detected and removed; disposable reformat proves semantic identity. |
| RF-027 | pre-artifact | Bind evidence to its satisfying interval and cold-replay that same predecessor/input. |
| RF-028 | pre-artifact | Ordinary multi-interval aggregation must retain body/action evidence after interval one. |
| RF-029 | live | Read the moving predecessor immediately before any bounded acceptance action; never blind-retry. |
| RF-030 | pre-artifact | Validate full V8 body/consequence shapes through controller and observer boundaries. |
| RF-031 | closed | Focused native/Python outputs report nonzero test counts; zero-match is failure. |
| RF-032 | closed | Rust and Python commands use their proven manifest/repository roots. |
| RF-033 | pre-artifact | Re-enumerate account, region, cluster, service, task, ECR, bucket, and distribution before release. |
| RF-034 | pre-artifact | Historical speech/autonomy witnesses are reported only; they cannot gate this tissue item. |
| RF-035 | closed | Mature proof uses the exact task-1425 body and its own retained motor frontier, zero synthetic seeds. |
| RF-036 | pre-artifact | Fresh wheel directory plus `--no-cache-dir --force-reinstall`; assert candidate symbol/path. |
| RF-037 | pre-artifact | Rehearsal must use only the factory production boundary handle. |
| RF-038 | pre-artifact | Decisive body event in a special first branch must survive later ordinary hops. |
| RF-041 | pre-artifact | Multi-boundary returned neuron lineages remain unique with signed deltas composed. |
| RF-042 | closed | Both signed motor directions and zero/cancellation are directly falsified. |
| RF-043 | closed | Equal antagonists and retained-opposition cases do not become false movement causes. |
| RF-044 | closed | Settlement is fixed 45 axes x at most 250 ms, 90 terminals, 45 consequences, and 360 persistent bytes. |
| RF-046 | pre-artifact | Applied action, sensed consequence, cold restore, and one later real interval all pass. |
| RF-047 | pre-artifact | Require exact ECR digest manifest pullability before one rehearsal task. |
| RF-050 | pre-artifact | Mixed body/world/vestibular continuation appends to one unsealed trajectory and seals once. |
| RF-053 | pre-artifact | One-seal parity, later-dark fractal, and non-simultaneous no-effector invariants remain unchanged. |
| RF-054 | pre-artifact | Mixed moved plus stalled-zero body rows retain only actual displacement. |
| RF-055 | pre-artifact | Action/consequence replay preserves one contact owner and lawful next wake. |
| RF-056 | live | Same identity and restored tick at or beyond the exact predecessor before image pinning. |
| RF-057 | pre-artifact | Compound world/body consequence remains top-level and produces both world and organism successors. |
| RF-058 | source/test gate passed | Normal non-hot controller path now rehearses and then cuts over the same digest/task definition in one invocation; `bash -n` and the cutover-order contract pass. |

## Release attempt 1 — cloud rehearsal refused before cutover

Candidate commit `379895010b67094e61abe072c244abf9d33a7021` built once as
image digest
`sha256:c14dbc301f50a7fb1a13e829aea65faecdfb15277df4dd74d00582225c27c2af`
and task definition `dsf-ai-task:1426`. Its discarded-state task
`25da617a160c4d0ca592e150eb44d1ad` exited before cutover. Production
remained unchanged and healthy on task 1425.

The exact refusal was `CURRENT has no retained matched world association`.
The native motor-tissue candidate did not execute and did not fail. Initial
triage attributed the mismatch to recursively copying a changing EFS root.
That diagnosis was withdrawn before code changed: the actual causal order is
stronger and directly reachable even from a coherent copy.

Task 1425 carries a V7 body and a matched world association keyed by that V7
body receipt. Candidate startup publishes the exact V8 current-format body
first. The migration changes the body receipt, but it does not publish an
association from the unchanged world bytes to that V8 receipt. Startup then
reconciles against V8 `CURRENT` and correctly refuses because only the V7
receipt has a matched world. The earlier local two-process motor proof had no
world-recovery marker, so it exercised the permitted bootstrap path and could
not expose this migration-order defect.

The correction belongs in the existing paired-persistence order: before the
body-format migration publishes V8 `CURRENT`, read the exact world paired to
the V7 predecessor and durably publish the same world bytes under the already
rehearsed V8 body receipt. Then publish V8 `CURRENT`, reconcile, and cold-run
the next ordinary interval. A pre-body crash leaves an unreferenced immutable
world pair that the next cold reconciliation can retire; it never changes
body authority. The production mount remains read-only during rehearsal. No
motor, neuron, DSF, authored-world, or live-state law may change to satisfy
this release gate.

## Corrected exact-pair proof

The corrected path was tested locally against one same-instant read-only copy
of task 1425, not a body-only or reconstructed-world substitute:

- identity `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`;
- V7 tick `413543`, state SHA-256
  `e5f1460431719deb5cc4df5a61a973368b7b6c27c490cbf70db4d686aec01aca`,
  `112687318` raw bytes;
- retained predecessor
  `ad0abe21d7de60580c86cbbf26ad14445b070cdff56484df7e9820df4b036774`;
- matched world SHA-256
  `4be74017c1fe5956f9aa96c5ce7c0009a70a6a3ea913a9d7e0d1f35f1b3e1094`,
  `63395` bytes, with the production world-recovery marker present.

One V8 preparation published the unchanged world under the rehearsed V8
receipt before publishing body `CURRENT`; the migration was not computed a
second time. The first fresh process advanced `413543 -> 413546`, moved the
body, returned all `90` articulated-body receptors, retained `164` formation
reassemblies, and persisted exact body/world successors. That process exited.
The second fresh process restored those exact successors, advanced
`413546 -> 413549`, moved the body, returned all `90` receptors, retained `168`
reassemblies, and persisted another exact body/world pair. The canonical proof
file is `/tmp/guala-task1425-full-exact-pair-proof.json`, SHA-256
`6ea88c72dbac2d0ae3a1b7b28ba9a45890b3cc031880c9c4692c7ddd4d547eaa`.

Two harness refusals preceded the accepted run and remain part of the attempt
history: a task-1413 world was rejected because its declared thermal authority
predated the current home; the exact task-1425 pair was then rejected when the
local child omitted `GUALA_NATIVE_ORGANISM_IDENTITY`, which correctly changed
the deterministic world-authentication key. Neither refusal changed source or
production. The accepted run used the exact task-1425 identity and pair.

## Release attempt 2 — healthy proof from two different predecessors rejected

Candidate commit `cec2047c145e5ea37a457c21e9b7d3c3adb3a76a` built once as
image digest
`sha256:9530fb87d1b8b914fc5c87c9e1d07e7bfda9830d8283dc8d694a51e2d217f85e`
and task definition `dsf-ai-task:1427`. Its isolated rehearsal task
`2c2d27b1fd54476d9af807fe925fe8b8` exited zero. The candidate migrated the
body and matched world successfully, ran both fresh processes, moved the body
twice, returned all 90 receptors twice, persisted both body/world successors,
and retained 155 then 171 formation reassemblies. Production remained
unchanged and healthy on task 1425.

The outer validator correctly rejected the otherwise healthy proof because it
combined two live predecessors. The primary authenticated restore observed
tick `414087`; `_rehearse_a011_ordinary_interval` later recursively copied the
still-advancing source and began at tick `414093`. Its first successor was
`414096` and its cold-next successor was `414099`. The validator requires the
A-011 predecessor to be the primary authenticated restore, so it refused with
`native candidate proof changed`.

This attempt retires the second traversal of the live source. The already
authenticated in-memory organism and the world paired to its exact source
receipt must be used to construct one disposable coherent store. Both fresh
A-011 processes then operate only on that store. A validator must never accept
healthy evidence assembled from two different moments merely because each
moment is individually valid.

## 2026-09-04 complete attempt accounting and final shell gate

The operator reports seven AWS build/rehearsal invocations during this day's
delivery work. That aggregate is part of the failed-attempt history even though
only two immutable candidate artifacts remain recoverable from this worktree:
task 1426/digest `c14dbc...c2af` and task 1427/digest `9530fb...7f85e` above.
The other five invocations have no surviving controller log here, so their
coordinates must not be invented or silently collapsed out of the count. No
new cloud invocation is permitted merely to reconstruct those missing logs.

The attempt-2 correction deletes the recursive second copy of the advancing
live source. `_rehearse_a011_ordinary_interval` now receives the one already
authenticated in-memory organism and its exact matched world, publishes that
pair once into a disposable local store, and starts both fresh proof processes
only from that store. The proof emits its first predecessor body SHA as well as
its tick. The outer validator requires both to equal the primary authenticated
restore and requires the source world-recovery marker. Widening the validator
to accept a later live tick remains prohibited.

Two focused anti-recurrence tests pass: one proves that the helper stages the
authenticated organism and matched world exactly once, and one rejects a
different predecessor tick, different predecessor SHA, or missing world
marker. A broader inherited probe-test invocation also ran and failed five
stale mocks that refer to retired helpers or old native method shapes:
`test_probe_reads_saves_and_reobserves_without_advancing_state`,
`test_l005_rehearsal_batches_both_lessons_into_one_native_trajectory`,
`test_articulation_rehearsal_reads_tick_through_native_observation`,
`test_physical_rest_reopens_work_and_cold_replays_exactly`, and
`test_internal_consolidation_changes_one_formation_and_cold_replays`. Those
tests do not reach the changed A-011 pair constructor and are not repaired or
misreported as candidate failures in this bounded release.
