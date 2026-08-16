# Guala A-013 truthful persistent embodiment sprint ledger

Date: 2026-08-16

Status: Active architecture boundary. A-013 is not Live-Closed.

## Task identity

- Active item: `A-013` — complete truthful persistent embodiment: pose, gaze,
  eyes, blinking, face, mouth, breath, voice, locomotion, manipulation, and
  body state.
- Dependency: A-012 is Live-Closed by the already-live physical rest/wake,
  consolidation, later causal-use, unattended interaction, and changed-world
  exploration circuit. Complete locomotion and manipulation remain A-013.
- Predecessor update: A-011.6 and A-011.7 are Live-Closed. A-011.7 closed on
  task 1095 by body-owned laughter receipt `8d1b7bfe...de32aa`.
- Production baseline remains task `dsf-ai-task:1095`, commit `d0a1956b`, one
  healthy organism process, the same organism identity, and zero Python
  cognition callbacks.

## Architecture honesty gate

1. Requested architecture: one persistent physical body with explicit
   effector anatomy must turn native layer-12/layer-13 discharge into bounded
   pose, gaze, eye, eyelid, face, mouth, breath, voice, locomotor, and
   manipulation transitions; each consequence must return through the same
   organism's physical receptors.
2. Current code reality: the authenticated world retains a root position,
   wrapped heading, circular collision radius, reach, held object, receptor
   offsets, and active contact. Native motor discharge drives only yaw by
   interpreting every layer-12 topology as one member of an even/odd yaw
   antagonist pair. Native layer 13 already drives breath, glottis, mouth,
   perioral movement, pressure, self-hearing, and four articulatory body
   receptor returns. Pick/place world mechanics exist only behind externally
   supplied typed commands. There is no persistent gaze, eyelid, facial pose,
   posture/joint anatomy, locomotor muscle, or manipulation effector binding.
3. Conflict with requested architecture: yes. A layer-12 cell currently
   retains its physical layer-8 body-regulation and layer-11 ordering contacts,
   but its mount contains only `(layer, topology_index)`. The transient
   recruitment therefore carries no physical effector site. Applying all such
   discharge to yaw collapses distinct future body routes onto one actuator.
4. Mechanisms not extended: arbitrary topology-number-to-action tables,
   Python action selection, semantic action names as authority, the retired
   Python taxis/stride controller, copied native/world body position, a second
   body-state codec, owner/lock/database state, whole-organism scans, scores,
   reward, random selection, or scripted movement.
5. Single exact next item: preserve and expose the already-existing sparse
   layer-12 -> layer-8 -> layer-6 -> physical body-receptor ancestry at motor
   recruitment, then determine whether that physical ancestry declares a real
   effector site. If it does not, add explicit body effector anatomy before
   any non-yaw actuation.
6. DSF scope: unchanged full joint seven-field L0-L4 remains authoritative at
   every reached occurrence. Embodiment mechanics neither evaluate a reduced
   projection nor change DSF.
7. Lost field structure: none.

## Current truthful capability matrix

| Required body capability | Current physical mechanism | Truth status |
|---|---|---|
| Root position | authenticated world `PoseMM.position` | persistent, but not autonomously actuated |
| Root heading | native exact yaw trajectory -> at-most-once world move -> vestibular return | live |
| Gaze and eye pose | retinal offset follows root heading | no independent gaze anatomy |
| Blinking/eyelids | none | absent |
| Face | layer-13 perioral area displacement | partial, transient |
| Mouth/breath/glottis | native articulatory body | live physical actuation |
| Voice/self-hearing | radiated pressure -> cochlear return | live physical actuation |
| Articulatory proprioception | four mounted body receptors | live |
| Posture/limbs/joints | none | absent |
| Locomotion | world can accept external position commands; native motor cannot address them | absent |
| Manipulation | authenticated pick/place mechanics accept external commands | not organism-actuated |
| Sleep posture/eye closure | none | absent |

## First rejected candidate

An isolated two-axis minimum-jerk helper was compiled and passed exact
conservation, symmetry, bounds, restart, and yaw-regression tests, then removed
before commit. It duplicated body position in native state, added an unused
Python bridge, and could not identify which physical motor site authorized
translation. Keeping it would have added correct arithmetic around the wrong
wiring boundary. The worktree returned to clean without changing existing yaw
or production code.

## First retained increment: exact motor/body ancestry receipt

The missing bookkeeping receipt is now implemented locally and remains
pre-production:

- native layer-12 recruitment carries the exact mounted sparse path
  `motor layer 12 -> body-regulation layer 8 -> local-integration layer 6 ->
  named physical receptor layer 5`;
- the path is derived only after an actual motor recruitment, from the contact
  edges already enumerated by that transition; quiet and non-motor intervals
  allocate no A-013 adjacency structure;
- the path is transient observation only and adds zero retained organism
  fields, codec bytes, owners, locks, tables, action labels, or Python
  cognition;
- the Python/native boundary rejects a motor with absent, malformed,
  duplicated, unordered, or non-layer-5 ancestry;
- the at-most-once motor action receipt binds the exact ancestry, while the
  existing yaw physics remains unchanged;
- the body receptor is truthfully classified as an afferent site. It is not
  relabeled as an effector. Explicit effector anatomy remains the next A-013
  implementation boundary.

Verification on the fresh wheel
`ec9b3542761dbae499043d50d6b5c85f0fcf77673eb5ce51d94ec039a081fc3d`:

- focused native sparse-ancestry proof: 1 passed, 0 failed;
- affected native/Python causal, physical-choice, yaw, cold-replay, and play
  boundaries: 84 passed, 0 failed;
- complete native suite after the allocation deferral: 577 passed, 0 failed,
  11 intentionally ignored;
- repository-wide Python collection is not a release result: it contains an
  unavailable Playwright dependency and retired modules that no longer
  import. The maintained `tests/` run reached 537 passes before stopping on
  30 inherited legacy-world/L6 fixture failures unrelated to this increment.

## Required acceptance

A-013 can become Live-Closed only after the production body persistently and
truthfully exposes every listed body part/state, native organism discharge
causes each implemented effector without semantic or Python selection,
at-most-once world/body consequences re-enter the corresponding senses, cold
restore is exact, identity and learned state remain unchanged, one process and
zero Python cognition callbacks remain true, and measured CPU/RAM/storage do
not grow without a reached physical cause.
