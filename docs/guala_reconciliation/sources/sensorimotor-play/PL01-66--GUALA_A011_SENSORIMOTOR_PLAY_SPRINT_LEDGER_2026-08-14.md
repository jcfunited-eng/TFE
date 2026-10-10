# Guala A-011 sensorimotor-play sprint ledger

## Frozen scope

- Active item: `A-011` — prove genuine self-selected play, fun, social joy,
  and body-owned laughter rather than a scripted animation or response.
- Immediate predecessor: `A-010`, live-closed on production task
  `dsf-ai-task:1056`. It is not reopened.
- Production baseline: task `dsf-ai-task:1056`, commit
  `f0e60e339eb18845a938ba83ccb7de1754a846f0`, image
  `sha256:f98648c097158ecec2e941130c1b2872983c7a419c7d4a54a8cb178b88fa5d2e`.
- This sprint's single input is an unattended native transition in which an
  internally reassembled retained formation physically reaches layer 12,
  moves the body, and returns through vestibular/body receptors.
- This first A-011 increment proves only **self-initiated sensorimotor play**:
  completed movement, cessation, and later varied return through retained
  formation activity. It does not close A-011 or claim fun, social joy,
  humor, or laughter.

## Architecture honesty gate

1. Requested architecture: one organism initiates, varies, stops, and later
   returns to low-stakes body/world activity through its own retained physical
   formations and action/consequence loop.
2. Current code reality: task 1056 has native retained-formation recurrence,
   opposed motor discharge, exact yaw, persistent world consequence, and
   vestibular/body re-entry. The public observation exposes only the latest
   action and does not assemble a bounded multi-episode play witness.
3. Conflict: yes. The autonomous effector bridge currently maps all layer-12
   motor recruitment to yaw; no object, locomotor, or social effector anatomy
   is mounted. Yaw remains sufficient for a first sensorimotor-play proof but
   not for the rest of A-011.
4. Mechanisms not extended: legacy autonomous-play engines, timers, random
   selectors, activity labels as cognition, reward/joy scores, semantic goals,
   canned laughter, TTS laughter, animation authority, owners, locks, queues,
   databases, retained event histories, or Python action selection.
5. Single exact next item: add a constant-size read-only witness for two
   internally caused retained-formation yaw episodes with distinct action
   receipts and displacements, where the first one ended before the later one
   began and both returned sensed body consequences.
6. DSF scope: every reached occurrence retains unchanged full joint L0-L4.
   This observer neither reevaluates nor reduces DSF.
7. Lost field structure: none.

## Exact path and field map

| Boundary | File/function | Required upstream facts | Downstream facts |
|---|---|---|---|
| Retained formation recurrence | `native/guala_core/src/resident_cognitive_formation.rs` formation recurrence | formation receipt, internally perturbed cue lineages, organism tick | `internally_reassembled_formation_cues` |
| Formation-to-motor propagation | `dsf_ai_service/native_production_app.py::_advance_causal_motor_traces` | cue lineages, exact directed carrier transfers, layer-12 recruitment | retained-formation motor path |
| Body action | `native_production_app.py::_prepare_motor_yaw_action` and `native/guala_core/src/virtual_body_yaw_motion.rs` | topology-indexed outward carriers | signed exact yaw trajectory and causal intent receipt |
| World consequence | `native_production_app.py::_perform_admitted_intake_locked` and `substrate/embodiment_world.py` | prepared at-most-once move | predecessor/successor world revision and state receipts |
| Sensed return | `_action_consequence_episode` and native vestibular/body receptor commit | exact yaw trajectory and successor world state | vestibular tick and perturbed body-receptor evidence |
| Physical choice | `_physical_choice_evidence_from_transition` | retained-formation path, changed reached/foregone routes, opposed motor discharge | one internally caused physical continuation receipt |
| Play observation | new bounded observer in `native_production_app.py` | two complete episodes and exact ordering | one compact non-causal sensorimotor-play witness |
| Public evidence | `_build_public_observation` | bounded play witness or exact unavailability | `play` observation section |
| Cognitive capital | `_cognitive_capital_record` | only an available play witness | read-only `Play and exploration` evidence credits |

The observer may keep at most one first episode and one completed witness in
process memory. Each episode keeps compact ticks, state/action/world/formation
receipts, signed yaw, body-return counts, physical-choice receipt, and a digest
of shared internal cue lineages. It never keeps a field body, neuron delta,
formation body, transfer graph, raw sensory material, or cross-restart archive.

## Translation-boundary review

- Native formation cues, motor recruitment, directed carrier transfers, exact
  yaw, world commit, vestibular return, and physical-choice evidence already
  cross native -> FFI -> Python without a new causative field.
- `MotorUnitRecruitment` contains lineage, topology index, outward carriers,
  and exact layer-11 preparation transfers. It contains no effector kind.
  Therefore mapping topology to object, locomotor, or social actions in Python
  would invent body anatomy and is forbidden in this sprint.
- Layer-12 topology parity lawfully supplies opposed yaw direction and carrier
  magnitude supplies displacement. No gain, threshold, target, or play
  coefficient is introduced.
- The play witness is observation only. It is never read by settlement,
  attention, choice, motor preparation, world action, persistence, sleep, or
  curriculum code.
- The public projection carries receipts and scalar physical facts, not the
  repeated preparation or formation graphs.
- Conservation is unchanged: the observer moves no energy, material,
  carriers, identity, neuron state, formation state, or world state.

## Lifecycle branch matrix

| Branch | Required behavior |
|---|---|
| No qualifying episode | Report unavailable; retain no invented play fact. |
| First qualifying episode | Keep one compact candidate; do not claim play. |
| Repeated API read | Make no transition and do not advance the candidate. |
| Same action receipt again | Ignore it; a cached observation is not a second episode. |
| Later non-retained or externally caused action | Do not complete play; leave the first candidate bounded. |
| Later retained-formation action with no shared cue or no physical variation | Do not complete play. |
| Later qualifying varied return | Publish one compact play witness; keep action ordering and both sensed consequences. |
| Cold restart | Observer resets; organism identity/state restore unchanged; ordinary live activity must re-prove the witness. |

## Acceptance evidence map

| Fact | Producer -> public path | Acceptance |
|---|---|---|
| Endogenous initiation | internal metabolic cue -> retained formation -> exact transfers -> motor discharge -> `play.first_episode` | intake is unattended, no tutor/external chooser, physical-choice receipt present |
| Completed movement and cessation | one-ms native yaw trajectory -> committed world revision -> later organism tick | first action has one completed consequence and return begins strictly later |
| Flexible variation | second exact motor discharge -> second yaw trajectory | distinct causal-intent receipt and different signed displacement |
| Voluntary return | same retained formation or shared internal formation cue -> later motor path | later internally reassembled retained-formation episode after the first ended |
| Body consequence | world successor -> vestibular/body occurrence -> persisted organism | both episodes have nonzero vestibular and body-receptor return |
| No scripted authority | code/source review and public authority fields | no play selector, score, random/timer chooser, or semantic action mapping |
| Boundedness | constant-size observer plus production process/state measurements | no event list, brain copy, growing cache, or Python cognition callback |

## Live baseline evidence and falsified hypotheses

- Read-only production sampling on task 1056 observed retained formation
  `bda19caf5dbcfa3b4f2f78c2864c0806ffedb5abd69b4efa749700ac871a8587`
  cause a `-58` millidegree yaw at generation 93,808/world revision 4,092.
  The next completed unattended episode reached generation 93,822/world
  revision 4,093 and the same retained formation caused a distinct `-40`
  millidegree yaw. The action receipts were different. The first one-ms body
  action had ended before the later recurrence began. A subsequent new-
  impression action reached generation 93,836/world revision 4,094.
- The existing organism therefore already supplies the minimum physical
  mechanism for **sensorimotor play**. The code change is limited to truthful,
  bounded assembly and exposure of that evidence.
- Falsified: repeated yaw alone proves play. It does not establish retained
  formation return or variation.
- Falsified: the world's `Move`, `Touch`, `Pick`, `Place`, and `Vocalize`
  command surfaces are autonomous effectors. Only yaw is connected to native
  layer-12 discharge.
- Rejected: extend `substrate/autonomous_causal_play.py`. It is a legacy
  label/controller surface and is not the live native causal path.
- Rejected: infer fun from affective-balance availability. Current layer-10
  evidence proves association/body perturbation followed by local gradient
  recovery, not positive valence, enjoyment, or absence of distress.
- Rejected: call the current articulation laughter. Its body-owned pressure
  and self-hearing path is real, but no learned playful/social formation has
  yet caused a laugh-like breath/larynx/mouth/face/body trajectory.

## Production acceptance

The release is accepted for this A-011 increment only when the immutable image
is healthy in production and a read-only live observation reports:

1. one bounded `sensorimotor_play_observed` record;
2. two distinct unattended retained-formation action receipts;
3. strict tick and world-revision ordering;
4. different signed yaw displacement;
5. one shared retained-formation receipt or nonempty shared internal cue;
6. a nonzero sensed vestibular/body consequence for each episode;
7. one compact cognitive-capital reference for `Play and exploration`;
8. unchanged organism identity, zero Python cognition callbacks, one healthy
   serving process, and no immediate RAM/storage/public-payload runaway.

A-011 remains open after this increment. Fun, social reciprocity/joy, and
body-owned laughter require their own later physical evidence and must remain
explicitly unavailable.

## Attempt ledger

- First focused command: `git diff --check`, Python compilation, and the two
  focused pytest modules. Diff and compilation passed. Pytest stopped during
  collection because the isolated worktree was not on Python's import path
  (`ModuleNotFoundError: dsf_ai_service`). This is a test-process environment
  failure, not behavioral evidence. Disposition: every subsequent local,
  rehearsal, and packaging test must explicitly load this candidate worktree;
  do not rediscover or reinterpret this failure.
- The corrected candidate-path run loaded the worktree and passed all three
  new A-011 tests. Four C-024 observer tests then exposed a stale mock record
  that omitted the already-live `intrinsic_curiosity` and `choice` sections
  required by `_cognitive_capital_record`. No production mechanism failed.
  Disposition: update that fixture to the current observation shape and rerun
  the same focused path; do not add compatibility defaults to production.
- Focused rerun after correcting only the stale fixture: 8 passed in 0.88
  seconds. This is local candidate evidence, not production proof.
- Adding the public API mapping test exposed one further stale test organism:
  all 15 tests in `test_native_public_observation.py` stopped before A-011 at
  its absent `observe_reached_source_site_count` method, which the already-live
  articulatory-body observation calls. Disposition: add the zero-result method
  to the mock organism only; do not add a production fallback or widen A-011.
- Corrected public fixture plus A-011 and C-024 focused acceptance: 23 passed.
- Exact candidate native provenance was rebuilt from this worktree with
  `maturin build --release`, installed into a fresh temporary target, and
  confirmed to export `internally_reassembled_formation_cues`. The installed
  global extension and checked-in wheel were stale and were not used as
  candidate evidence.
- A broad command that put both the candidate-native target and worktree on
  `PYTHONPATH` passed 29 tests and failed three. Two failures exposed an
  inherited default-world fixture containing 66 objects against a 64-object
  capacity; production has 15 objects and A-011 neither constructs nor changes
  the world inventory. The third failure was the probe-isolation test correctly
  rejecting two `PYTHONPATH` entries. Disposition: record the default-world
  defect for the later world/curriculum item; do not alter world capacity in
  A-011. Invoke the candidate as `PYTHONPATH=<fresh-native-target> python -m
  pytest ...`, allowing the interpreter's current directory to supply this
  exact worktree without a second path entry.
- The corrected adjacent acceptance run covered A-008 action consequence,
  A-009 causal return, unattended production processing, release packaging,
  and cold-restore isolation: 27 passed in 73.62 seconds. No Python cognition
  callback or candidate-native provenance failure was observed.
- Final pre-package run loaded `guala_core` only from the fresh candidate
  target and the serving app only from this worktree, then exercised A-011,
  C-024, the public observer, A-008, A-009, unattended processing, release
  packaging, and cold-restore isolation: 50 passed in 74.92 seconds. Python
  compilation and `git diff --check` also passed.
- Canonical production preflight on 2026-08-14 re-resolved one healthy task
  1056, commit `f0e60e339eb18845a938ba83ccb7de1754a846f0`, image
  `sha256:f98648c097158ecec2e941130c1b2872983c7a419c7d4a54a8cb178b88fa5d2e`,
  4 vCPU/16 GiB, and HTTP 200 for both Loom pages. No release mutation occurred.

## Applicable deployment recurrence register

| ID | A-011 observed result before immutable build |
|---|---|
| RF-001 | Exact worktree and loaded module/native paths are explicit; the first missing-path collection failure is recorded above. |
| RF-002 | Task 1056 environment was read before candidate import; mounted ears, touch, chemoreception, vestibular, and world are enabled, interoception is disabled, and migration is disabled. |
| RF-003 / RF-015 / RF-036 | Candidate native wheel was built into a fresh directory and force-installed into a fresh target; the exported retained-formation field and loaded path were checked. |
| RF-004 | Pristine focused branches pass; authenticated-predecessor cold restore remains the next rehearsal gate. |
| RF-005 / RF-018 / RF-028 / RF-038 / RF-046 | The evidence map above traces the complete multi-hop transaction, special vestibular consequence, final aggregate, public observer, and cognitive-capital consumer. Focused public-boundary tests pass. |
| RF-007 / RF-023 / RF-024 / RF-032 / RF-033 | Controller is executable, accepts only `--rehearse-only`, AWS targets were inventoried rather than inferred, task environment was filtered with `jq`, and every focused test path was resolved before invocation. |
| RF-010 | Candidate changes no persistence state. Rehearsal must still cold-restore the exact task-1056 CURRENT before cutover. |
| RF-011 / RF-044 | The witness is two constant-size dictionaries containing only compact receipts/scalars; no per-neuron, coordinate, route, or formation body crosses the API. |
| RF-012 | HTTP and tests do not close this increment; acceptance requires a live `sensorimotor_play_observed` record after cutover. |
| RF-013 / RF-026 | Only changed files are checked; no repository-wide formatter is authorized. |
| RF-014 / RF-017 | Stale mocks were corrected only to the already-live interface. No native type, constructor, or FFI shape changes in A-011. |
| RF-016 / RF-034 | A-011 is the sole active item; A-010 and C-023/C-024 transient witnesses are not reopened or replayed as A-011 authority. |
| RF-019 / RF-021 / RF-027 / RF-035 / RF-040 / RF-043 | Rehearsal assertions are limited to restored continuity and the active observer boundary. The causative play episodes must arise through ordinary live unattended activity after cutover, not a substituted diagnostic source. |
| RF-022 | No retained-state domain or codec changes. |
| RF-025 / RF-029 | A-011 live acceptance is read-only; no state-changing public request or retry is permitted. |
| RF-030 / RF-037 / RF-042 | No signature, boundary-handle method, interval horizon, or signed-motion validator changes. Both yaw directions are lawful; only zero is rejected by the observer. |
| RF-039 / RF-041 / RF-045 | No receptor population, fractal composition, sensor clock, or occurrence transport changes. |
