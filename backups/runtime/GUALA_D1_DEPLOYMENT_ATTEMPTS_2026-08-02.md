# Guala D1 deployment attempt ledger

Date: 2026-08-02 UTC

## Estimate checkpoint

- Revised D1 estimate stated in chat: 90 minutes total, approximately 30
  minutes remaining at the checkpoint.
- The exact initial D1 start timestamp is held by the chat record, not by the
  deployment shell. This ledger does not invent it.
- Exact artifact-release window measured below: 17 minutes 30 seconds from
  the first attempt's image tag time through verified image/task completion.
  That window did not establish operational D1 completion.

## Artifact release attempt 1

- Deploy image tag time: 22:29:59 UTC
- CodeBuild start: 22:30:14.079 UTC
- CodeBuild end: 22:32:32.932 UTC
- Build ID: `dsf-ai-image-build:1fb69960-c5df-4fac-a18f-aa79f512b591`
- Commit: `df9975b2a87c2d3962db549dd7ccd45b44feb0fe`
- Result: failed before ECS cutover; production task 844 remained unchanged.
- Cause: the nested CodeBuild Docker sandbox denied `openat2` and did not
  expose the host cgroup hierarchy required by 34 environment-bound platform
  tests.
- Correction: production code remained fail-closed and unchanged. The image
  builder was changed to compile the complete crate, run every environment-
  independent native test, and skip only the two environment-bound test
  modules. The complete 291-test suite remained required and passed in the
  capable development container.

## Artifact release attempt 2

- Deploy start/image tag time: 22:34:33 UTC
- CodeBuild start: 22:34:48.603 UTC
- CodeBuild end: 22:38:50.752 UTC
- CodeBuild duration: 4 minutes 2.149 seconds
- Build ID: `dsf-ai-image-build:be0133dd-982b-4447-b8bc-cb91680949ef`
- Commit: `b55ba9061b6658501cfecd2bbae3aa7f22333b03`
- Candidate task definition: `dsf-ai-task:845`
- Old task stopped: 22:39:19.371 UTC
- New task started: 22:42:45.706 UTC
- Stop-to-start interval: 3 minutes 26.335 seconds
- New target registered: 22:43:26.874 UTC
- Verified deployment completion: 22:47:29 UTC
- Attempt duration: 12 minutes 56 seconds
- Result: image/task deployed and independently verified; operational D1 was
  not yet proven.

## Artifact live proof

- ECS desired/running/pending: 1/1/0
- ECS deployment count: 1
- ECS rollout: COMPLETED
- ECS task health: HEALTHY
- Task definition: `dsf-ai-task:845`
- Image digest:
  `sha256:c4fd3f83fd8a0cc04ebc7cfec4d7d0b3926a48dd1471f2e3d13d945edd2e87ca`
- ECR tag `production-current` resolves to the same digest.
- Authenticated production readiness reports `ready=true`, `owner=true`, the
  exact task definition, digest, commit, and continuous organism identity
  `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`.
- CodeBuild executed all ten `joint_field_l0_l4` D1 contracts successfully in
  the exact image build.

## Honest boundary

This proves the D1 native joint-field and neuronal-fractal implementation was
included in the exact image build now serving production. It does not prove a
live sensory episode invoked that law or persisted a new neuronal fractal; the
current readiness response did not expose a D1 transition receipt and reported
no tick value. That operational mount requires separate production evidence.

## Operational deployment attempt

### Attempt 1

- Deploy start: 2026-08-02T23:49:38Z
- Deploy finish: 2026-08-03T00:02:45Z
- Deploy duration: 13 minutes 7 seconds
- Commit: `5a5a99c1adbf49587e72625a5a48ccb7741926a1`
- Task definition: `dsf-ai-task:846`
- Image digest:
  `sha256:292be3973f63e7150109534bc906239bc31554793ac37c111429807cf117025d`
- Image/task/owner result: passed with one healthy owner and continuous identity.
- Live A-card settlement result at 2026-08-03T00:09:25.451Z: failed and
  atomically rolled back before tutoring progression or D1 state mutation.
- Exact cause: the D1 field derived an 86,457,797-byte transient working set,
  but the implementation incorrectly reused the 67,108,864-byte persistent
  state ceiling as its transient working-memory admission.
- Correction: keep the persistent-state ceiling unchanged and admit transient
  field work against exact currently unoccupied finite cgroup memory. No fixed
  larger cap or guessed coefficient replaces the failed boundary.

Completion still requires a live physical sensory settlement, authenticated
persisted D1 receipt, cold restart continuity, recurrence, and bounded resource
evidence.

### Attempt 2

- Deploy start/image tag time: 2026-08-03T00:18:41Z
- ECS rollout start: 2026-08-03T00:23:02.837Z
- Running task start: 2026-08-03T00:27:27.305Z
- ECS rollout completion: 2026-08-03T00:31:31.591Z
- Attempt duration: 12 minutes 50.591 seconds from image tag through rollout
  completion.
- Commit: `1227faa33a82b77b2358d78c23c05f98a66f12bb`
- Task definition: `dsf-ai-task:847`
- Image digest:
  `sha256:b0f75be270c33382dffa3e1bcb99a73b40132a57b7cb67ea6758cd9316f438e9`
- Image/task result: passed; task 847 remains the single healthy production
  task as of 2026-08-03.
- Operational D1 result: failed acceptance. The real 64-retina/32-cochlear
  shape settled locally in about 71.13 seconds because one transition replayed
  complete joint-field physics redundantly (`2P + 4N` executions for prior
  fields `P` and current fields `N`). That exceeds the 45-second browser
  boundary. The two unequal exact clocks also lacked one compact persisted
  relationship candidate. No subsequent code is deployed yet.

## Current candidate proof before deployment attempt 3

- Production remains unchanged on task 847 and commit `1227faa3`.
- Redundant physics execution is reduced to `P + N`: prior persisted fields
  are replay-verified once, and each current field is computed once.
- Real five-second audiovisual first occurrence: 15.978 seconds; 2 exact-clock
  fields; 96 stable neuron lineages; 96 transitioned fractals; 0 recurrent;
  one `co_observed_capture_occurrence` candidate; 0 mosaics; 438,102 bytes.
- Real five-second audiovisual recurrence: 30.063 seconds; the same 2 fields
  and 96 lineages; 96 transitioned; 96 predecessor-aware recurrent; one new
  candidate referencing prior topology; 0 mosaics; 441,206 bytes.
- Genuine task-847 v1 state migration: all 4 test lineages retained and
  recurrent, inner wire upgraded from `GLJNFT01` to `GLJNFT02`, candidate
  retained, and 0 mosaics.
- Native verification: 292 unit tests plus 14 codec tests passed.
- Focused native/Python persistence and readiness verification: 70 passed.

These are candidate facts, not deployment completion. Attempt 3 begins only
after the reviewed source is committed and the exact release is built.

### Attempt 3

- Deploy start: 2026-08-03T01:56:57Z
- Deploy finish: 2026-08-03T02:10:24Z
- Deploy duration: 13 minutes 27 seconds
- Commit: `95314263b86351bf29b076b83a905d418dad2908`
- Task definition: `dsf-ai-task:848`
- Image digest:
  `sha256:66f93e714b9a0e47cee311285b491e42226eb05876f054212b138325bcbd3869`
- Image/task result: passed; one running healthy task, no pending task, and a
  completed rollout.
- No owner, lock, UI, curriculum, card, database, service, autonomy, or L0-L4
  mechanism was changed by this candidate.

## Attempt 3 live neuronal proof

- The first authenticated five-second production occurrence observed sight
  and sound across two exact clocks and persisted 96 receptor-neuron
  fractals: 64 canonical retinal perspectives and 32 auditory perspectives.
- First native result: 2 joint fields, 96 neurons, 96 transitioned fractals,
  0 recurrent fractals, one episode-relation candidate, and 0 mosaics.
- A probe-harness error sent sequence 1 on a separate new PCM stream. The
  request was rejected with `ValueError` in 0.001280 seconds before settlement
  or native-state mutation. This was not a deployment or organism failure.
- One corrected distinct five-second occurrence used sequence 0 in its own
  bounded PCM stream. Production returned `ok=true`, observed sight and sound,
  established an audiovisual causal boundary, authenticated continuous PCM,
  and closed the stream with a terminal receipt.
- Second native result: the same 2 fields and 96 neurons, 96 transitioned
  fractals, 96 recurrent fractals, a successor episode-relation candidate,
  and 0 mosaics.
- Native persisted state changed from 4,146,901 to 4,148,843 bytes: growth of
  1,942 bytes for the recurrent episode relationship. No sensory media was
  copied into this native state.
- Zero mosaics is intentional at D1: recurrence establishes durable neuronal
  evidence and a cross-clock relationship candidate but does not manufacture
  collective recognition authority.

## Attempt 3 cold-restart proof

- The same task-848 artifact was restarted without rebuilding or changing
  code. ECS replaced task `c13e017ca6a94c46ae203908725c6610` with task
  `26dd91fcd5c14fba95e5c3dd60725e04`.
- Restart rollout completed at 2026-08-03T02:32:08.172Z with the same task
  definition, commit, and image digest.
- After cold restore, state SHA-256
  `b1f538e25d0bf59584266172ccb473b2b2db6ad7ddf1fc1f7ffa542bd2cc7e14`,
  byte count 4,148,843, 96-neuron count, 96 recurrent count, joint-transition
  receipt, and episode-relation receipt all matched the pre-restart values.
  Only `last_transition` truthfully changed to `cold_restore`.

## Attempt 3 resource and latency evidence

- Across build cutover, two settled sensory occurrences, and cold restart,
  ECS CPU peaked at 49.239% of the four-vCPU task and the latest average was
  1.749%.
- ECS memory peaked at 15.314% of the 16-GiB task and the latest average was
  8.661%.
- Production storage declares one 5-GiB unique-regular-file logical-byte
  ceiling; the retired flat full-copy producer remains retired.
- The corrected production recurrence spent 0.016 seconds in visual work,
  0.668 seconds in sound work, 73.196 seconds in settlement, and 2.653 seconds
  in the terminal, for 79.124 seconds end to end.
- The settlement overlapped a separately logged 44.31-second hot checkpoint.
  This is consistent with the locally measured approximately 30-second native
  recurrence plus existing checkpoint serialization. Therefore the native D1
  transition meets the modeled browser computation boundary, but the complete
  production HTTP interaction does not yet meet 45 seconds when it overlaps
  the pre-existing checkpoint path.
- The persisted native transition proves `python_callback_count == 0`; the
  verification boundary rejects a nonzero count before persistence. Thus the
  live 96-fractal D1 transition made zero Python callbacks internally and the
  targeted 80--87-million-call ownership/control transition is eliminated at
  this production boundary. Ordinary FastAPI request handling is outside that
  eliminated transition and is not expected to have a zero interpreter-call
  count.
