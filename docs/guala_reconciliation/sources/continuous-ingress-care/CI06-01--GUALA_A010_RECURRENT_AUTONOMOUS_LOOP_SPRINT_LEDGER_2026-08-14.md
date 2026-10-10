# Guala A-010 recurrent autonomous-loop sprint ledger

## Frozen scope

- Active item: `A-010` — prove the closed attention -> choice -> action ->
  sensed-consequence loop repeats without external prompting, duplicated work,
  or runaway growth.
- Immediate predecessor: `A-009`, live-closed on production task 1056. It is
  not reopened.
- Production baseline: task `dsf-ai-task:1056`, deployed commit
  `f0e60e339eb18845a938ba83ccb7de1754a846f0`, image
  `sha256:f98648c097158ecec2e941130c1b2872983c7a419c7d4a54a8cb178b88fa5d2e`.

## Architecture honesty gate

1. Requested architecture: one persistent organism must repeatedly produce its
   own attention, physical choice, body/world action, and sensed consequence.
2. Current code reality: task 1056 has already produced multiple distinct
   unattended action receipts after restart, and each sampled consequence has
   re-entered the same organism. Repeated-operation and resource bounds are not
   yet recorded as one acceptance series.
3. Conflict: not established. No code change is authorized unless the live
   series exposes one exact blocking defect.
4. Mechanisms not extended: scheduler-selected actions, random choice, owners,
   locks, queues, databases, semantic goals, Python cognition, retained event
   archives, whole-brain polling, or heuristic resource caps.
5. Single exact next item: record a bounded live series of distinct autonomous
   action/consequence receipts and measure organism ticks, world revisions,
   public bytes, resident-state bytes, process count, Python callbacks, RAM,
   CPU, and persistent-root bytes over the same interval.
6. DSF scope: each reached occurrence continues through unchanged full joint
   L0-L4. A-010 does not reduce or reinterpret the field.
7. Lost field structure: none.

## Acceptance path

| Boundary | Required evidence |
|---|---|
| Wake cause | Unattended runtime active with no tutor or request causing the action |
| Attention and choice | Physical attention/choice evidence precedes each action; no authored goal or random selector |
| Action | At least three distinct causal-intent receipts and distinct world revisions |
| Consequence | Each receipt binds one 109-port sensory consequence and internal afference in the same organism |
| Continuity | Tick and state receipt advance monotonically; identity remains unchanged |
| No duplication | One applied world revision per action receipt; no repeated receipt or second process |
| Bounded observation | Public response remains compact and does not regain preparation/frontier graphs |
| Bounded runtime | One Python serving process, zero Python cognition callbacks, finite RAM/CPU/storage deltas, and no monotonic runaway unsupported by retained physical change |

## Initial live facts

- Task 1056 is healthy with one desired, one running, and zero pending tasks.
- One post-restart sample advanced from generation 93416 to 93430 and exposed
  two distinct autonomous action receipts without any stimulus request.
- The latest sampled action and consequence receipts matched exactly; the
  world observer exposed the same receipt. Every consequence carried all 109
  mounted sensory ports and five localized internal metabolic receptors.
- Public observation measured 169,240 bytes with preparation graphs absent and
  zero Python cognition callbacks.
- Direct container census found one Python Uvicorn process. The SSM diagnostic
  helpers were temporary observation infrastructure, not organism workers.
  PID 1 reported 914,352 KiB RSS and 1,177,844 KiB high-water RSS. The task
  cgroup reported 1,143,742,464 current bytes and 1,372,250,112 peak bytes
  inside its 16 GiB envelope. The persistent root measured 415,936 KiB.

## Live repeated-operation evidence

- Five distinct autonomous action/consequence receipts were directly observed
  after the task-1056 restart, with consecutive world revisions 4071, 4072,
  4073, 4074, and 4075. No POST, tutor, or action endpoint was called; the
  observation GET is a cached read-only projection and cannot advance the
  organism.
- Every sample reported `changing_sparse_physical_frontier_observed`, then
  `internally_caused_attention_settled_one_physical_continuation`, then one
  `native_causal_action_observed`. Each consequence receipt matched its
  causal-intent receipt. Direct world/organism comparison matched the latest
  receipt and world revision.
- Every consequence re-entered all 109 mounted sensory ports and five internal
  metabolic receptors. Receipts were unique and world revision advanced once
  per receipt; no duplicated action was observed.
- Organism generation advanced monotonically from 93500 through 93556 while
  identity remained `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`. The public
  projection remained between 155,610 and 179,820 bytes and never regained the
  removed preparation/frontier graph bodies. Python cognition callbacks stayed
  zero.
- Two direct runtime snapshots 62 seconds apart reported:

| Quantity | First | Second | Delta |
|---|---:|---:|---:|
| PID 1 user CPU ticks | 49,064 | 55,066 | +6,002 |
| PID 1 system CPU ticks | 2,820 | 3,144 | +324 |
| Cgroup CPU nanoseconds | 521,349,819,521 | 584,962,217,760 | +63,612,398,239 |
| PID 1 RSS KiB | 903,356 | 922,232 | +18,876 |
| Cgroup current bytes | 1,132,363,776 | 1,151,291,392 | +18,927,616 |
| Cgroup peak bytes | 1,410,412,544 | 1,410,412,544 | 0 |
| PID 1 threads | 10 | 10 | 0 |
| Persistent root KiB | 415,936 | 414,864 | -1,072 |

  The cgroup has four vCPUs and 16 GiB, so 63.6 CPU seconds over 62 seconds is
  about one utilized core rather than recursive or multiplied execution. The
  one Python Uvicorn process remained the only Python organism-serving process;
  temporary SSM diagnostic helpers were not organism workers.
- Resident-state bytes did not grow monotonically with actions: the first pair
  changed from 59,476,692 to 59,476,729 bytes, the next successor measured
  58,377,627 bytes, and its following action measured 58,377,669 bytes. This
  short repeated-loop proof shows no immediate duplicate/runaway mechanism; it
  does not replace A-015's required long soak.

Status: **Live-Closed 2026-08-14 on production task 1056. A-011 is next and is
not claimed by A-010 evidence.**
