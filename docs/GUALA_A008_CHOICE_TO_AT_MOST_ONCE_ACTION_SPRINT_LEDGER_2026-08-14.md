# Guala A-008 choice-to-at-most-once-action sprint ledger

## Frozen scope

- Active item: `A-008` — prove that choice reaches layer 12 and causes one
  real world/body action at most once.
- Immediate predecessor: `A-007`, live-closed on production task 1054. It is
  not reopened.
- This sprint adds no action selector, command meaning, scheduler, retry,
  owner, cognitive lock, database record, score, or retained proof object.
- The single question is whether the already-live physical choice and the
  already-live world/body successor are the same event and whether that event
  can commit no more than once.

## Architecture honesty gate

1. Requested architecture: one internally caused physical choice must reach
   the mounted layer-12 motor population and may cause one real persistent
   body/world successor, never duplicated execution.
2. Current code reality: task 1054 already carries one choice witness, native
   layer-12 recruitments, one prepared motor capability, one applied world
   revision, and one sensed consequence under the same causal receipt.
3. Conflict: no conflict in the A-008 mechanism. One stale top-level observer
   sentence still says autonomous thought/action are not mounted; that is a
   separate truthful-observation defect and is not used as A-008 evidence.
4. Mechanisms not extended: motor physics, world geometry, retry loops,
   schedulers, semantic commands, Python cognition, owner/lock/database
   cognition, or persistent action evidence.
5. Single exact next item: verify and live-record the existing
   choice -> layer-12 preparation -> consumed prepared capability -> one world
   revision -> body consequence path.
6. DSF scope: unchanged full joint L0-L4 remains authoritative inside reached
   neurons; A-008 neither reevaluates nor reduces it.
7. Lost field structure: none.

## Durable change-impact ledger

| Boundary | Exact value |
|---|---|
| Input | One committed unattended transaction whose A-007 witness contains one causal-intent receipt, one internally caused motor lineage, exact antagonist settlement, and one nonzero prepared yaw. |
| Function/file path | `dsf_ai_service/native_production_app.py::_prepare_motor_yaw_action` derives one prepared body intent from exact layer-12 recruitments; `_perform_admitted_intake_locked` commits it once inside the organism/world publication transaction; `dsf_ai_service/substrate/embodiment_world.py::prepare_port_command` and `commit_prepared_action` enforce one revision and consume the unique prepared capability. |
| State transformation | Preparation leaves live world bytes unchanged. Commit replaces the exact prior world state with its single candidate, advances revision by one, clears the prepared capability, admits vestibular/body consequence, persists the world candidate, and publishes the organism successor. Any later commit of the consumed capability is refused. |
| Expected output | The choice and action carry the same causal-intent receipt and signed yaw; the action reports layer 12, `disposition=applied`, one lifecycle ending in `applied`, `result_revision = expected_revision + 1`, distinct before/after world receipts, and a sensed body successor. |
| Production acceptance | One live unattended task-1054 snapshot satisfies every expected-output equality, while ECS has one healthy process and no pending or failed rollout. |
| Non-claim | A-008 does not claim all sensory consequences in A-009, recurrent loop closure in A-010, or completed autonomy/curriculum/UI work. |
| Persistence | No new schema or retained organism field. The world candidate and organism successor use their existing atomic persistence path. |
| Resource bound | One prepared capability at a time; one linear pass over already-reached motor recruitments; no whole-neuron scan, replay queue, action history, or Python cognition callback. |

## Translation and acceptance-evidence map

| Fact | Producer -> consumer | Required equality |
|---|---|---|
| Internal physical choice | A-007 sparse attention/motor settlement -> public `choice` | `available=true`, internally caused lineage, one prepared intent |
| Layer-12 reach | native motor recruitment -> `_prepare_motor_yaw_action` | every prepared recruitment is explicitly projected as motor layer 12 |
| Same causal event | prepared capability -> execution receipt -> public action | choice receipt equals action receipt |
| Same physical direction | antagonist settlement -> exact yaw trajectory -> action | choice signed yaw equals action signed yaw and is nonzero |
| At-most-once execution | `prepare_port_command` -> `commit_prepared_action` | one live capability; commit consumes it; reuse fails; revision advances exactly one |
| Real world/body successor | committed world candidate -> persisted world/body -> vestibular admission | distinct before/after world receipts, one revision, moved body, sensed successor |

No field is defaulted or recomputed from a weaker proxy at these boundaries.

## Lifecycle and failure register

- Pristine preparation is physically pure: it changes neither live world bytes
  nor public world observation.
- A second simultaneous preparation is refused while the first capability is
  live.
- Successful commit consumes the capability. Reusing or copying it is refused.
- A stale world revision is rejected without mutation.
- A commit interruption restores the exact prior world and leaves the original
  capability discardable.
- If organism publication fails after world commit, the existing rollback
  transaction restores and persists the predecessor world; no duplicate
  successor remains visible.
- Rejected hypothesis: action merely followed choice in nearby time. Live
  evidence carries the exact same causal-intent receipt and signed yaw.
- Rejected hypothesis: layer-12 eligibility alone proves action. Acceptance
  additionally requires the applied world revision and sensed body successor.
- Rejected path: add an A-008 action ledger or retry queue. The consumed
  prepared capability and monotonic exact world revision already provide the
  at-most-once law.
- The first focused run executed 16 tests: seven passed and nine default-world
  fixtures stopped before action settlement because fresh construction now
  supplies 66 curriculum/world objects to a 64-object capacity. This is a
  pre-existing fresh-genesis inconsistency, not evidence about task 1054's
  restored 15-object world. It is recorded for its own delivery item and was
  not hidden by changing world capacity inside A-008.

## Production baseline and observed evidence

- Current production task: `dsf-ai-task:1054`.
- Runtime commit: `a4ae22e36331138213be585c534abd865bd3dfca`.
- Immutable image digest:
  `sha256:947615882ac4631ac40d37560ab37c2a85310cb25c1b9a88ca39e40f7bb1dda5`.
- Organism identity: `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`.
- Live snapshot tick/state: `91992` /
  `4d6e0938180ea2a9a43a9c257ca328a98ebfc26f2a1c0645b4fb95f4e95db5dd`.
- Choice causal-intent receipt:
  `f05978db9ba99939eadd59bec3ddba2023c315a535c52c9938cc94b526342319`.
- The action carries that exact receipt. Its settled/action yaw is `-126`
  millidegrees, based on 144 layer-12 motor recruitments.
- The world accepted expected revision `3957`, observed the same revision,
  produced revision `3958`, and changed world receipt from
  `d5e51131e69144d19d6380385448d3eff3cb7b1ad050847481d8bd2cfbedc118`
  to
  `09f7a3d72c1f860316fdc6db0c6439e0415290f558d4c21012f4a553aed08c35`.
- The applied lifecycle is `received -> port_validated -> command_decoded ->
  geometry_validated -> applied`.
- The same causal record reports one vestibular tick and one externally
  perturbed body receptor in successor tick `91992`.
- ECS reports desired/running/pending `1/1/0`, zero failed rollout tasks, and
  a completed primary deployment.

## Focused execution and closure

- The A-007 choice projection, native motor-yaw preparation, and dedicated
  A-008 at-most-once path pass 8/8 against this exact worktree.
- The dedicated proof uses an explicit finite world fixture, proves preparation
  is physically pure, commits one layer-12-derived capability, observes exactly
  one revision and one changed state receipt, then proves reusing the consumed
  capability is refused and cannot advance the revision again.
- No runtime code changed. The acceptance mechanism was already live on task
  1054, and the direct production snapshot above proves the same event rather
  than a local substitute.

Status: **Live-Closed 2026-08-14**. A-009 is next and is not claimed.
