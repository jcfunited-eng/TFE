# Guala A-002 persistent world sprint ledger

## Frozen scope

- Active item: `A-002` — make the persistent virtual room/world continue
  independently of browser presence and retain exact body, object, and
  environment consequences.
- Immediate predecessor: `A-001`, live-closed in production task
  `dsf-ai-task:1050`, commit `e5b366c5`, image
  `sha256:31c7edeee93846dd5d87244f7e5499e0abdb88e76b0191d14d9751d0e4b67489`.
- Exact input: one authenticated current world body and one native motor
  consequence produced by the persistent organism.
- Exact path: native layer-12 motor discharge -> prepared world command ->
  world authority transaction -> atomic world-body persistence -> vestibular
  and body consequence re-entry.
- Exact output: one successor revision and pose that survive exact cold
  restoration and remain observable without a browser driving the world.
- This item does not claim continuous same-clock coverage of every sense,
  object manipulation, richer environments, curriculum, or completed Loom UI.

## Architecture honesty gate

1. Requested architecture: one persistent world and body whose physical
   consequences continue without a browser.
2. Current code reality: production constructs one exact four-room home,
   restores `world.glworld`, applies native motor consequences transactionally,
   persists the world atomically, and exposes a read-only projection.
3. Conflict: no production-path conflict was found. The missing artifact was a
   focused exact cold-restore regression and live recurrence record.
4. Mechanisms not extended: browser drivers, duplicate world authorities,
   curriculum inventories, owners, locks, database cognition, authored action
   selection, and arbitrary capacity changes.
5. Single exact item: prove action -> persistence -> exact cold restoration and
   live browser-independent recurrence.
6. DSF scope: A-002 neither evaluates nor reduces DSF; the world is upstream
   physical state and its sensed consequences use the existing native path.
7. Lost DSF structure: none.

## Change-impact and acceptance map

| Boundary | Required fact | Evidence |
|---|---|---|
| World authority | production mounts one exact world | `_world()` constructs four regions, 15 objects, two bodies, and restores the current authenticated file |
| Consequence | a native action changes exact physical state | focused test applies a `MoveCommand`, advances revision by one, and changes the state digest |
| Persistence | current world bytes are atomic and bounded | `_persist_world` stages then replaces `world.glworld`; focused proof compares persisted and authority bytes and enforces the 2 MiB bound |
| Cold restore | no body/object consequence is lost | a fresh production authority restores byte-identical state and an identical observation snapshot |
| Corruption | false state is never silently substituted | a one-byte-corrupt world is refused and remains untouched rather than being rebuilt from defaults |
| Observation | browser reads do not drive the world | focused proof shows `/world/observation` leaves encoded authority bytes unchanged |
| Live recurrence | the world changes without browser action | production revision 3789/heading 322211 advanced to revision 3790/heading 322564 through 136 native motor recruitments |
| Cold production history | current task did not rebuild the home | task 1050 started at 2026-08-14T15:31:46Z and served revision 3788+ with `place_rebuilt_reason=null`, rather than a revision-zero default |
| Production topology | one settled task | ECS desired/running/pending is 1/1/0, PRIMARY rollout completed, container healthy |

## Failed hypotheses retained

- The first focused run used `PYTHONPATH=backend/src`, which does not contain
  this repository's package. It failed at collection and exercised no runtime
  behavior. The correct repository import root is `PYTHONPATH=.`.
- The first cold-restore fixture omitted production's stable
  `GUALA_NATIVE_ORGANISM_IDENTITY`. The fallback correctly created a different
  newborn UUID and therefore a different HMAC key. The fixture was corrected
  to reproduce production; runtime authentication was not weakened or changed.
- A broad legacy world suite exposes a separate dormant-default inconsistency:
  its generic constructor now authors 66 curriculum objects against an older
  capacity of 64. Production never uses that default and supplies its exact
  15-object home. A-002 did not expand into curriculum-capacity redesign.

## Verification and live closure

- Focused production-path suite: 6 passed, 0 failed.
- Live task: `dsf-ai-task:1050`.
- Live commit/image: `e5b366c5` /
  `sha256:31c7edeee93846dd5d87244f7e5499e0abdb88e76b0191d14d9751d0e4b67489`.
- Live identity remains `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`.
- Public observation showed four regions, 15 objects, two bodies,
  `she_moves_herself=true`, and no rebuild reason.
- With observation reads only, revision 3789 advanced to 3790 and heading
  322211 advanced to 322564 millidegrees through 136 native motor
  recruitments. The last step was `applied` and moved the persistent body.
- No runtime change or redeployment was required: the exact mechanism is
  already the live task-1050 production path. Deploying unchanged runtime only
  to alter its commit label would add no behavior or production proof.

Status: **Live-Closed 2026-08-14**.
