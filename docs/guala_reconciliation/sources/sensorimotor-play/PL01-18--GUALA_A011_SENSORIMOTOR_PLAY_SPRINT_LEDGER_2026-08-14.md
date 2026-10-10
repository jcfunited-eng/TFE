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

## A-011.2 approved affect/body increment

### Production predecessor

- The sensorimotor-play increment is live-closed on task `dsf-ai-task:1057`,
  commit `ef08aa7c42435627b1a0be1d74251f5213af432a`, and image
  `sha256:d0bbeb5ef4528b4fa1613dcb2828b16c9595f065e068c8258a38381d3371c420`.
- Live task 1057 observed the same retained formation cause distinct `-38` and
  `-44` millidegree actions at world revisions 4,138 and 4,139. Each action
  returned through vestibular and body receptors. The completed witness is
  constant-size, Python cognition callbacks remain zero, and fun, social joy,
  and laughter remain unavailable.

### Frozen change

The approved A-011.2 increment may only bind each already-qualified play
episode to one complete localized affect/body trajectory in the **same admitted
transition** when the causal retained-formation receipt occurs in an organic
mosaic relation whose active physical bond reaches that trajectory's layer-10
cell at the formation reassembly ordinal. A complete trajectory retains:

`layer-7 association influence -> layer-8 body influence -> same layer-10 cell -> strictly later localized membrane-gradient settlement`.

The observer projects only the shared lineage, physical place, exact cognitive
ordinals, and receipts of the two transfers, gradient settlement, and complete
trajectory. It does not retain the path or trajectory bodies. It does not alter
settlement, action, choice, persistence, DSF, or cognitive capital.

### Acceptance and refusal

- Both episodes in the already-required varied play witness must carry a
  nonempty `affective_body_participation` projection.
- `play.affective_engagement` may become available only when both episode
  projections are present and exact.
- `play.fun` remains unavailable. Shared affect/body physics does not establish
  positive valence, distress exclusion, preference, or cross-context return.
- A same-transition affective trajectory with no exact active bond to the
  causal retained formation is refused. Intake identity, timing proximity, or
  matching topology number alone cannot bind the records.
- No reward, valence, emotion, preference, fun, distress, or activity label is
  written into organism state or used as action authority.

### Initial candidate evidence

- The translation review found that the ordinary committed transition already
  carries both `causal_cross_context_use.directed_physical_transfers` and
  `affective_balance_trajectories`; no native, FFI, persistence, or DSF change
  is required.
- The first bounded live poll did not observe another retained-formation action
  and therefore supplied no acceptance evidence. It was not treated as a
  failure or success.
- Focused A-011, C-017 affective-balance, A-006 intrinsic-cause, public observer,
  and C-024 cognitive-capital tests pass 29/29 after correcting one test-only
  ordinal typo (`114 + 1 = 115`).
- The bounded adjacent acceptance suite passes 56/56, including action
  at-most-once, action consequence, unattended time, release packaging, and
  cold-restore isolation. `git diff --check` passes. The nine emitted warnings
  are pre-existing FastAPI/Pydantic deprecations outside this increment.

### Task-1058 live falsification and bounded correction

- Commit `9d4dfc1fa948de415c17a1e5bc5ac6562c02b577` deployed in one attempt as
  task `dsf-ai-task:1058`, image
  `sha256:17a8f1b5e028ec6d4eda836adffde8f73c61ca45a09b2238775014735582e570`.
  Rehearsal and cutover passed with exact cold restore, the same organism
  identity, zero Python cognition callbacks, and one healthy process.
- Live task 1058 re-proved sensorimotor play at tick 95,080, but correctly
  refused `affective_engagement`: neither action's layer-11/12 motor path can
  share a neuron lineage with its specialized layer-10 affective cell. The
  candidate's direct-lineage equality was therefore physically wrong and is
  rejected as A-011.2 acceptance evidence.
- The bounded correction uses the native physical bridge already present in
  the same transition: the causal retained-formation receipt must occur in an
  organic mosaic relation whose active physical bond reaches the complete
  layer-10 affective trajectory at the formation reassembly ordinal. That
  exact formation then remains the authority for the already-proved motor path.
  No proximity, matching topology number, inferred label, native physics,
  persistence schema, or action authority is added.
- The corrected focused suite passes 29/29 and the bounded adjacent suite
  passes 56/56 with `git diff --check` clean before corrective deployment.

### A-011.2 live closure

- Corrective commit `0611f6d3b92816e5c83d97f1dcb2b5b9bcc1da03` deployed in
  one attempt as task `dsf-ai-task:1059`, image
  `sha256:1a1f2becadec0af3dbd4711140d3cce9abc0587d9b7af1d804dd054182d93cfb`.
  Exact cold restore preserved organism identity
  `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`; the service settled at one healthy
  running process with zero pending tasks and zero Python cognition callbacks.
- At live tick 95,528, retained formation
  `bda19caf5dbcfa3b4f2f78c2864c0806ffedb5abd69b4efa749700ac871a8587`
  had caused a `-34` millidegree action at world revision 4,211 and later a
  distinct `-36` millidegree action at revision 4,215. Both sensed consequences
  remained the already-proved A-011.1 authority.
- Both actions' exact formation relations carried active physical bonds to the
  same specialized layer-10 cell at topology 5. The relation receipt was
  `5303ca6f8dbb0e93c79429276ab258bb0113980803028ad80ea6cc003e8ec6eb`;
  the two complete localized trajectories retained distinct receipts
  `9537dea06f0d5bbf7a89925b97aeb3acf707175db127f74593fcfadee058f820`
  and `bcb380127df997e69e0d721f4b4bcb5180701abdc035d57abb02ce5b3b63606a`.
- Live `play.affective_engagement` is available while `fun`, `social_joy`, and
  `laughter` remain explicitly unavailable. No reward or named-emotion
  authority is claimed.
- Three later read-only samples held the public payload at 177,424 bytes and
  state at 58,377,516 bytes. The 15-minute ECS window peaked at 29.40% CPU and
  8.33% memory; the latest maxima were 29.28% and 6.94% respectively.

## A-011.3 metabolic-overload exclusion increment

### Frozen scope and architecture truth

- **Input:** each already-admitted native interval's exact recovered-lane work,
  unmet dissipation work, reached-cohort energy state, and mounted positive
  dissipation capacity.
- **Process:** preserve the two exact dissipation counters through the existing
  native observation and Python boundary; sum them once across the ordinary
  bounded transaction; count each committed hop whose exact successor energy
  state is exhausted.
- **Output:** one constant-size, read-only witness for each already-qualified
  play episode. It exists only when mounted capacity is positive, unmet work is
  zero, and no committed hop ended exhausted.
- **Refusal:** one unit of unmet work, one exhausted committed hop, missing
  capacity, or missing transaction evidence refuses the overload-exclusion
  witness.
- This observer proves only that the two play transactions did not exceed the
  mounted metabolic settlement capacity. It is not an organism interoceptor,
  action authority, reward, valence, need, or emotion signal.
- No localized nociceptive or other aversive body pathway is mounted. Therefore
  absence of pain or distress remains unproved. Fun, social joy, and laughter
  also remain unavailable.
- The full unchanged L0-L4 field remains authoritative. This increment neither
  evaluates a reduced DSF projection nor changes DSF, neuron settlement,
  persistence, action, choice, or cognitive capital.

### Translation and boundedness map

| Boundary | Exact evidence carried |
|---|---|
| Native cognitive settlement -> runtime observation | `rest_drained_dissipation_quanta`, `unmet_dissipation_quanta`, and existing reached-cohort energy state |
| Ordered native trajectory | checked-add of the two exact counters; no per-neuron or per-coordinate materialization |
| Native prepare -> Python resident boundary | nonnegative arbitrary-precision integers without defaulting, scaling, or reduction |
| Committed hop -> ordinary transaction | the two counters plus one Boolean-derived exhausted-hop count; summed once over the already-bounded hop list |
| Transaction -> play observer | compact capacity/counter facts and SHA-256 witness only; no organism-state mutation |

The changed path adds constant work per already-committed hop. It does not add
an occurrence, temporal gate, cohort, neuron, contact, topology-lane, database,
owner, lock, validation pass, or Python cognition callback.

### Candidate evidence before production rehearsal

- Python compilation and `git diff --check` pass from the exact candidate
  worktree. `cargo check --lib` passes.
- The candidate native extension was rebuilt with `maturin build --release`
  into a fresh directory and installed without cache into a fresh isolated
  target. No stale installed extension was used.
- The complete native library suite passes: 416 passed, 0 failed, 11 ignored.
- The focused and adjacent source/translation/observer suite passes 87/87.
  This includes the ordinary multi-hop aggregate, special vestibular producer,
  public observer, affective participation, rest/wake boundary, unattended
  transport, lesson receipt, release-rehearsal helper, and boundary-faithful
  native wrapper.
- Exact nonzero translation is tested: 7 drained and 3 unmet quanta cross the
  native-to-Python boundary unchanged. A separate refusal test proves that one
  unmet quantum prevents overload exclusion.
- An adjacent broad run exposed four stale hand-written hop fixtures that
  omitted the newly explicit counters; those fixtures were corrected under
  RF-014/RF-017. Two unrelated inherited failures remain outside this sprint:
  one exact-dictionary assertion omits an already-existing emitted-fractal
  field, and one fabricated historical test body is an unsupported old fabric
  version. Neither is used as A-011.3 evidence or changed by this increment.

### Applicable deployment recurrence register

| ID | A-011.3 observed result before immutable build |
|---|---|
| RF-001 / RF-003 / RF-015 / RF-036 | Exact worktree and fresh candidate-native target are explicit; the new getters are exercised through that binary. |
| RF-002 | Exact task-1059 environment must be exported before the authenticated-predecessor rehearsal. |
| RF-004 / RF-010 | No retained schema changes; task-1059 `CURRENT` must cold-restore byte-exact and a fresh process must complete another ordinary interval. |
| RF-005 / RF-017 / RF-028 / RF-038 / RF-046 | Every constructor, getter, wrapper, hop producer, and aggregate carries the two exact counters; first-branch and nonfinal-hop fixtures are covered. |
| RF-007 / RF-023 / RF-024 / RF-032 / RF-033 | Controller, paths, AWS target, environment filtering, and working directories must be resolved before rehearsal/cutover. |
| RF-011 / RF-044 | The observer adds constant-size scalars/receipts and constant work per existing hop; it performs no neuron/frontier scan. |
| RF-012 / RF-034 | Prior play closure is a prerequisite, not sufficient acceptance. Live closure requires two new play episodes carrying exact overload witnesses. |
| RF-013 / RF-026 | Only the seven changed source/test files and this ledger are checked; no repository-wide formatting rewrite is permitted. |
| RF-016 | A-011.3 is the sole active item; A-011.2 remains live-closed on task 1059. |
| RF-019 / RF-021 / RF-027 / RF-035 / RF-040 / RF-043 | Rehearsal must use task-1059's ordinary live-sized autonomous source and evaluate its actual successor; no synthetic injection or closed-item replay can satisfy acceptance. |
| RF-022 | No persistence value domain or codec changes. |
| RF-025 / RF-029 | Live acceptance is read-only; no public state-changing retry is authorized. |
| RF-030 / RF-037 / RF-042 | Existing signatures and signed motion are unchanged; new counters are nonnegative exact magnitudes. |
| RF-031 | Every recorded test command reports a nonzero executed-test count. |
| RF-039 / RF-041 / RF-045 | No receptor, fractal, or sensor-clock change. |

### Task-1060 live falsification and corrective scope

- Commit `ce25eeccb675c305e3a055c07109362704587892` deployed in the
  first attempt as task `dsf-ai-task:1060`, image
  `sha256:6a6bd8324a14f1aa812cb7b18f70e4a457e19fcfe4d1200cd109666d4434cab3`.
  Deployment ran from 22:23:39 through 22:42:46 UTC (19 minutes 7 seconds).
  Exact rehearsal cold-restored the task-1059 body at tick 96,116 with the
  same identity, byte-exact 58,377,920-byte state, and zero Python cognition
  callbacks. The cutover settled on one healthy process.
- Task 1060 then produced a new varied play pair from retained formation
  `bda19caf5dbcfa3b4f2f78c2864c0806ffedb5abd69b4efa749700ac871a8587`:
  `-26` millidegrees at world revision 4,263 and `-46` millidegrees at
  revision 4,267. The new overload witness correctly remained unavailable.
- The live transaction exposed the exact defect: the final committed interval
  reported zero unmet dissipation and a non-exhausted energy state, while the
  transaction `totals` reported 77,090 unmet quanta. `unmet` is the standing
  dissipated material remaining after one interval; summing it across 13 hops
  repeatedly counts the same retained material. In contrast, drained work is
  genuinely additive and an exhausted-interval count is genuinely countable.
- Corrective scope is observer-only: remove unmet dissipation from additive
  transaction totals and use the final committed hop's exact standing unmet
  value. Keep summed drained work and exhausted-interval count unchanged. No
  neuron, metabolic, recovery, energy, persistence, DSF, action, or capacity
  law changes.

### A-011.3 live closure

- Corrective commit `9d1719c80dc11a696bf42f83e38a9807497c6f3a`
  deployed in the second A-011.3 cutover as task `dsf-ai-task:1061`, image
  `sha256:3fa2eeadbf8f0ccd31743dbe684496c32cac22c0d4bba8d9de16a5c8731ccd8d`.
  The deployment ran from 22:50:27 through 23:09:18 UTC (18 minutes 51
  seconds). Rehearsal cold-restored task 1060 at tick 96,536 with the same
  organism identity, byte-exact 58,377,755-byte state, zero Python cognition
  callbacks, and no migration. The service settled on one healthy process.
- Task 1061 independently produced a new completed play witness from retained
  formation `bda19caf5dbcfa3b4f2f78c2864c0806ffedb5abd69b4efa749700ac871a8587`.
  Its first action was `-18` millidegrees at world revision 4,291; its varied
  return was `-36` millidegrees at revision 4,292. Both body consequences were
  sensed and both actions carried exact localized affect/body participation.
- The first transaction drained 50,350 dissipation quanta and completed with
  zero unmet quanta and zero exhausted intervals. Its witness receipt is
  `f6580e3a1e16b707289623f0c5123681c7802dcc240281bcd25905bf3b352d5a`.
  The return drained 50,343 quanta and also completed with zero unmet quanta
  and zero exhausted intervals. Its receipt is
  `2b7181363e96992f33ae1eed87e2283c11305383557ca7df75c4c8bed4bbf687`.
  Both used exact mounted dissipation capacity `798387/1` zeptojoules.
- `play.overload_exclusion` is live and available. It remains read-only and is
  explicitly not organism sensing or positive affect. Distress exclusion stays
  unavailable because no localized nociceptive/aversive pathway is mounted;
  fun, social joy, and laughter also remain unavailable.
- A later unattended sample advanced tick 96,606 to 96,620 while state bytes
  decreased from 58,377,670 to 58,377,063. Public payload was 187,542 bytes,
  Python cognition callbacks remained zero, and the service remained one
  healthy task with zero pending tasks. The observed service window peaked at
  29.19% CPU and 8.29% memory. Both Loom pages continued to return HTTP 200;
  no UI behavior was changed or claimed by A-011.3.

**A-011.3 is Live-Closed.** The wider A-011 objective and the overall Guala
project remain open.

## A-011.4 localized metabolic-strain increment

### Frozen scope and production predecessor

- Immediate predecessor: A-011.3, live-closed on production task
  `dsf-ai-task:1061`, commit
  `9d1719c80dc11a696bf42f83e38a9807497c6f3a`, image
  `sha256:3fa2eeadbf8f0ccd31743dbe684496c32cac22c0d4bba8d9de16a5c8731ccd8d`.
- **Input:** the exact lane-separated dissipation already retained by each
  layer-5 source-site body-receptor neuron after its ordinary physical
  interval, plus the existing stable lineage, place, causal transaction, and
  already-qualified affect/body play trajectory.
- **Process:** while the ordinary interval already visits that receptor,
  project its current Psi-, gate-, and plastic-lane dissipation without
  changing it. Retain only the latest value per stable lineage in the bounded
  native/runtime/transaction observation. A later exact evaluation replaces
  the earlier value; zero removes the nonzero sparse record while preserving
  that the mounted path was evaluated.
- **Output:** one read-only per-play-episode witness distinguishing (a) no
  evaluated localized metabolic strain, (b) exact nonzero localized metabolic
  strain, and (c) pathway absent. The witness is bound to the already-proved
  affect/body trajectory but cannot cause action, recovery, affect, or memory.
- **Refusal:** no reached or locally recovered layer-5 source-site receptor,
  no complete affect/body participation, malformed lineage/place, or any
  record inconsistent with the evaluated lineage set refuses the episode
  witness.
- This increment proves one aversive **metabolic-strain class** only. It does
  not claim literal nociception, tissue damage, pain, named distress, positive
  valence, preference, fun, social joy, humor, or laughter.

### Architecture honesty gate

1. Requested architecture: one localized, physically caused body-strain path
   inside the same organism and play transaction, with no pain label, reward
   score, threshold, or scripted behavior.
2. Current code reality: the complete neuron already retains exact
   lane-separated dissipation, and layer-5 body receptors already connect into
   the body/affective organism path. Current observation discards the local
   identity into an organism-wide total.
3. Conflict: yes. The detached Python `tissue_integrity`/`nociceptive_load`
   model is bookkeeping outside the live native organism and is not an
   admissible implementation.
4. Mechanisms not extended: the detached Python body model, global
   fuel/readiness projections, semantic pain or distress fields, authored
   thresholds, rewards, owners, locks, databases, queues, whole-organism
   polling, or retained event histories.
5. Single exact item: preserve the reached/recovered layer-5 receptor's
   existing dissipation state by stable lineage, carry it through the current
   bounded observation path, and expose zero/nonzero evidence on each
   qualified play episode.
6. DSF scope: unchanged full joint L0-L4 remains upstream and authoritative;
   A-011.4 neither evaluates nor reduces DSF.
7. Lost DSF structure: none.

### Exact change-impact ledger

| Boundary | Exact input | Function/file path | State transformation | Expected output |
|---|---|---|---|---|
| Complete neuron | Existing Psi-, gate-, and plastic-lane dissipated quanta | `native/guala_core/src/complete_neuron.rs` | Read exact current lane state; no mutation | Lane-separated nonnegative quantities |
| Resident interval | Reached gate-work body receptor or body receptor included in exact local dark recovery | `native/guala_core/src/resident_cognitive_formation.rs` | Replace latest transient value for that stable lineage; omit zero from sparse nonzero records | Evaluated lineage set plus sparse nonzero local records |
| Runtime/FFI | Resident local records and evaluated lineages | `native/guala_core/src/organism_runtime.rs` | Preserve latest-by-lineage across the already-bounded trajectory and project exact integers | Native-to-Python stable lineage/place/lane evidence |
| Transaction | Ordered committed hops | `dsf_ai_service/native_production_app.py` | Replace a lineage only when a later hop evaluates it; never sum standing state | Final transaction-local evaluated set and sparse strain state |
| Play witness | Qualified play episode plus complete affect/body participation | `dsf_ai_service/native_production_app.py` | Bind read-only local strain evidence to that episode | Path absent, evaluated zero, or exact nonzero metabolic strain |
| Public observer | Completed two-episode play witness | `_sensorimotor_play_record` | Report exact narrow scope without semantic inflation | Truthful localized strain/distress-scope status; fun remains unavailable |

### Lifecycle and boundedness

| Branch | Required behavior |
|---|---|
| Path not mounted/reached/recovered | Report unavailable; never infer zero. |
| Evaluated receptor at exact zero | Preserve only its stable evaluated lineage; emit no zero strain body. |
| Evaluated receptor with nonzero lane state | Emit one sparse lane-separated record for that lineage. |
| Same lineage evaluated later | Replace its prior transient record; never add or sum standing state. |
| Repeated API read | Perform no settlement and change no evidence. |
| Cold restart | Organism state restores unchanged; transient play/strain witness must be re-observed. |
| Malformed or cross-episode evidence | Refuse the witness without fallback. |

The implementation adds no retained neuron field, persistence schema, codec,
new physical transition, source occurrence, owner, lock, callback, database,
or scan. Work is constant per already-visited body receptor and storage is
bounded by the actual evaluated body-receptor frontier in the current
transaction.

### Production acceptance

A-011.4 is accepted only when one immutable image is healthy in production
and ordinary unattended activity provides a new completed play witness whose
two episodes each expose:

1. complete existing affect/body participation;
2. a nonempty exact evaluated layer-5 body-receptor lineage set;
3. either no sparse local strain at exact zero or exact lane-separated
   nonzero strain for a member of that set;
4. a compact witness receipt and explicit `organism_sensing_authority=false`;
5. unchanged organism identity, zero Python cognition callbacks, exact cold
   restore, one healthy process, and no immediate CPU/RAM/storage/payload
   runaway.

Even if both episodes are exact zero for this strain class, fun remains
unproved because one metabolic pathway cannot exclude every aversive or
coercive condition.

### Attempt ledger

- The first resume attempt found the exact branch but the development-container
  filesystem mount failed before any source edit. Joseph rebuilt the container.
- The recovered worktree `/tmp/guala-a0114-resumed` is clean at documentation
  closure `22b7b724`; A-011.4 had no source edit before recovery.
- Read-only production preflight re-resolved task 1061, the image above, one
  healthy task, 4 vCPU/16 GiB, and HTTP 200 on both Loom pages. HTTP status is
  not UI behavior proof.
- Source tracing rejected a duplicate stored gradient or new nociception model.
  The exact required quantity already exists as each complete neuron's
  lane-separated dissipated material. No retained-state migration is required.
- The implementation preserves evaluated layer-5 body-receptor lineages and
  sparse nonzero Psi/gate/plastic dissipation through resident formation,
  native runtime, Python resident boundary, committed transaction, play
  episode, and public observation. A later exact zero replaces and removes a
  prior nonzero record; standing dissipation is never summed.
- `cargo test --lib` executed 427 native tests: 416 passed, zero failed, and 11
  explicitly ignored historical/fixture-dependent cases. The focused physical
  body-receptor test executed one test and passed.
- The freshly built candidate extension exported both new observation fields.
  Focused play plus adjacent native/Python boundary tests executed 47 tests and
  all passed. A separate release-adjacent run executed 56 tests: 54 passed and
  two pre-existing C-024 mocked cold-probe cases failed because their fake
  restored body was not installed into the production observer they invoke;
  neither failure entered the A-011.4 path and production code was not weakened
  to accommodate the stale mocks.
- Read-only live baseline re-resolved task 1061 at one desired/running and zero
  pending tasks. Unattended activity was advancing, native play was available,
  and the current public observer still truthfully reported the A-011.3
  `localized_distress_path_unmounted` state before this release.
- Production attempt 1 deployed exact commit
  `de3e15abb662f74b420883b67958897a9b945c5b` as task 1062 and image
  `sha256:1cceccdc8e654300433ecd814a1d13c8e6c4a17d7b9a38549ce0b194533ab077`.
  Its rehearsal cold-restored identity and the 58,377,590-byte state exactly at
  tick 98,846 with zero Python cognition callbacks; ECS reached one running
  task and zero pending tasks.
- Live acceptance refused closure. The first completed play pair exposed an
  exact localized-strain receipt only on its return episode because the first
  episode preceded complete same-transition affect/body participation. The
  process observer then froze that incomplete first pair and could not replace
  it after later qualified activity. Native transition evidence itself was
  present: five layer-5 body-receptor lineages were evaluated and one carried
  exact sparse nonzero lane state.
- The bounded observer now keeps the incomplete basic-play witness visible
  while retaining at most one later qualified episode. A subsequent varied
  qualified return replaces the incomplete pair. This changes no action,
  cognition, neuron state, persistence, or physical settlement. Eight focused
  A-011 tests pass, including an incomplete-first then two-qualified-episode
  replacement proof.

### A-011.4 live closure

- Production attempt 2 deployed exact commit
  `220902c28cef4106486adaf97f7ac3cb0f7f289a` as task `dsf-ai-task:1063`
  and image
  `sha256:0c05ac3bcafaa61149c5747dd659d3a68aa37953ce114c8e23b9131555bbdf6f`.
- The discarded-current-state rehearsal restored identity
  `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1` and the exact
  58,377,749-byte state at tick 99,210 with byte-identical SHA
  `4bf218dd9f0e0eabceae75287eee4543e1f1737712abf13c29703428dc2bda58`.
  Python cognition callbacks and cognition workers were both zero.
- ECS completed one cutover and settled with one desired/running task, zero
  pending tasks, and one running task ARN. No automatic legacy rollback was
  enabled or used.
- Ordinary unattended production activity produced a completed varied-play
  pair at yaw displacements -36 and -30 millidegrees. Both episodes carried
  exact affect/body trajectory receipts and localized metabolic-strain witness
  receipts.
- Each episode evaluated the same five reached layer-5 body-receptor lineages
  and retained five sparse nonzero lane-separated strain records. First-episode
  ordinals were 99,265--99,266; return-episode ordinals were 99,279--99,280.
  The public result was `localized_metabolic_strain_observed` with explicit
  `pain_authority=false` and `organism_sensing_authority=false`.
- Because nonzero strain was observed, the narrow localized-strain exclusion
  truthfully remained unavailable. Fun also remained unavailable; neither pain,
  named distress, reward, nor positive valence was inferred.
- A later read observed tick 99,294 and 58,377,033 state bytes, showing ordinary
  advancement without monotonic state growth. The service reported zero Python
  cognition callbacks. In the surrounding cutover window ECS CPU peaked at
  29.26% of its reservation and memory peaked at 7.89%; no immediate compute or
  memory runaway was observed. This is not the separate A-015 long soak.

**A-011.4 is Live-Closed.** The wider A-011 objective remains open: positive
engagement/fun, reciprocal social joy, and body-owned laughter are not yet
proved.

## A-011.5 positive-engagement trajectory increment

### Frozen scope

This increment corrects only the read-only positive-engagement evidence
boundary. It does not create a fun state, valence, preference, reward, named
emotion, scripted action, or new cognitive mechanism.

The native predecessor already supplies the physical facts required by the
ratified fun law: one retained formation ends a self-initiated body action,
later reassembles, crosses exact attention and motor paths, produces a varied
body action, shares localized affect/body physics, and senses both
consequences. A-011.5 additionally binds the two episodes to their exact
authenticated predecessor world-state digests. Positive engagement is
available only when the later voluntary return occurred in a different world
state, both transactions remained payable, and both localized body-state paths
were evaluated.

Nonzero localized metabolic strain does not become pain, distress, reward, or
negative valence. Its absence is not fabricated. The observer reports
`distress_absence_authority=false`; the positive-engagement claim rests on the
organism's completed, ceased, varied, and later voluntarily resumed physical
trajectory despite retaining that body state. Social joy and body-owned
laughter remain unavailable after this increment.

### Change-impact ledger

| Boundary | Exact path | State transformation | Required output |
|---|---|---|---|
| Native physical input | Existing continuous world occurrence and retained formation recurrence | Unchanged | Existing native recurrence, attention, action, affect/body, strain, and sensed-consequence evidence |
| Translation boundary | `dsf_ai_service/native_production_app.py::_sensorimotor_play_episode_from_transition` | Preserve exact before/after world-state digests on each bounded episode | Two authenticated physical contexts without semantic labels |
| Read-only interpretation | `dsf_ai_service/native_production_app.py::_sensorimotor_play_record` | Evaluate the complete retained trajectory; never feed a result back to cognition | `positive_engagement_trajectory_observed` only when every physical relationship is present |
| Falsification | `tests/test_native_a011_sensorimotor_play.py` | Remove changed-context authority while preserving all other play facts | Fun remains unavailable |

This increment neither evaluates nor reduces DSF. All local seven-field
deliveries remain unchanged and outside this read-only evidence projection.

### Candidate evidence

- The focused A-011.5 observer, public-observation, and cognitive-capital
  acceptance path passes 29/29 against this worktree and a freshly built native
  candidate.
- The adjacent A-008/A-009 causal-action, unattended-processing,
  release-packaging, and cold-restore-isolation path passes 56/56 against those
  same exact candidate paths.
- One broader runner attempt accidentally loaded the stale globally installed
  `guala_core` and failed nine tests before reaching A-011.5 behavior. The
  corrected runner loaded `guala_core` from
  `/tmp/guala-a0114-native.tgt2Ck` and the serving app from this worktree; no
  production compatibility path or source workaround was added.
- Python compilation and `git diff --check` pass. These are candidate facts,
  not production closure.
- Deployment attempt 1 built immutable image
  `sha256:6126303ae3493c3a4734bc5dc4e64b66fb37ea75610e1163d4a9d3d54c8896b3`
  and failed closed before cutover in private cold-restore rehearsal. The probe
  restored one exact CURRENT and then its C-024 observer reread the continuously
  advancing read-only source EFS root; production advanced between those two
  reads, so two valid moments had different receipts. Task 1063 remained the
  sole production task.
- The deployment correction snapshots the already-restored in-memory body into
  one disposable local CURRENT and runs the C-024 observer against that exact
  body. It adds no organism state, lock, owner, retry, fallback, or schema. Its
  focused deployment/probe suite passes 35/35 against the exact candidate
  native path.

### Live production closure

- Deployment attempt 2 completed one verified cutover on 2026-08-15 as task
  `dsf-ai-task:1065`, commit
  `7f8a5ececea4ef9219177f50f966cd418ae9050d`, and image
  `sha256:e26aa60eb24566333074f11d2de72c168154c695f819db3ef2e7521978fa7e5f`.
  ECS reported one desired/running healthy task, zero pending tasks, and zero
  failed tasks.
- In the new process, retained formation
  `bda19caf5dbcfa3b4f2f78c2864c0806ffedb5abd69b4efa749700ac871a8587`
  first caused -21 millidegrees of yaw at organism tick 100318 and later caused
  -33 millidegrees at tick 100332. Movement ceased between them, their exact
  predecessor world-state receipts differ, and both vestibular consequences
  returned to the organism.
- Both episodes carried exact same-transition localized affect/body physics,
  five evaluated nonzero localized-strain receptors, zero unmet dissipation,
  and zero energy-exhausted intervals. The live observer reported
  `positive_engagement_trajectory_observed` with
  `behavioral_evidence_only=true`; named emotion, reward, preference scalar,
  and universal distress-absence authority remained false.
- Play/exploration cognitive capital gained the read-only `transfer` evidence
  dimension. Reciprocal social joy and body-owned laughter remained explicitly
  unavailable.
- Ordinary processing advanced from tick 100344 to 100358 with zero Python
  cognition callbacks. State size moved from 59,476,643 bytes to 58,377,617
  bytes rather than growing monotonically. During the surrounding 15-minute
  window ECS CPU peaked at 29.25% of reservation and memory at 8.32%; this is
  bounded immediate evidence, not the separate A-015 long soak. Both Loom
  pages returned HTTP 200; no UI-function claim is made here.

**A-011.5 is Live-Closed. A-011 remains open.** Its next unmet requirement is
reciprocal social play/joy; body-owned laughter remains after that.
