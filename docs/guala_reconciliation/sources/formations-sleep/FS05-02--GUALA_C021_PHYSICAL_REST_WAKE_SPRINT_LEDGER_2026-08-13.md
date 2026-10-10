# Guala C-021 Physical Rest and Wake Sprint Ledger

Date: 2026-08-13

Status: active. This ledger is continuity evidence, not a completion claim.

## Task identity

- Active item: `C-021` — prove sleep/rest emerges from organism condition and
  changes reachable work without a scheduler pretending to be a brain.
- Closed predecessor: `C-020`, live on production task `dsf-ai-task:1034`,
  commit `533e457361dfea813a52341abdd9e5153fea3244`, image
  `sha256:2d299435813310b054aefce1100ec544ebc6167837ef366daf81d9e36793f890`.
  Public production showed one committed native articulation with four
  nonquiescent body ports, sixteen body-receptor ingresses, sixteen physically
  perturbed body neurons, four self-hearing hops, and three retained
  self-hearing neuronal fractals. ECS had one running task, zero pending tasks,
  and no candidate rehearsal task.
- Production baseline: the same task, commit, image, organism identity
  `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`, and one raw native `CURRENT` lineage.
- Ledger movement: advance to C-021. C-020 is not reopened.

## Architecture honesty gate

1. Requested architecture: rest or sleep must arise from the organism's exact
   body, fluid, energy, dissipation, membrane, and recovery condition; it must
   narrow physically reachable work, preserve the same organism, and later
   permit lawful wake from changed physical condition.
2. Current source reality: native cohort physics already retains finite exact
   recovery-fluid energy, per-neuron dissipation, local rest recovery, membrane
   return, and sparse reached-frontier settlement. `RuntimeObservation` exposes
   `rest_recovered_neuron_count`. The Python native boundary does not copy that
   field into a hop or transaction, so production cannot currently prove which
   neurons recovered. Existing `no_internal_cause` is only a zero-change
   observation and cannot close C-021.
3. Conflict: yes, at the native-to-Python evidence boundary; whether a further
   physical reachability defect exists is not yet assumed.
4. Mechanisms not extended: `WakeState`, `wake_admission`, owner/lock/custody
   machinery, Python action selection, timers as cognitive cause, sleep mode
   Booleans, circadian counters, fatigue scores, reward/need scalars, semantic
   labels, whole-brain scans, or legacy food/oral-intake control.
5. Single exact next item: preserve the existing native
   `rest_recovered_neuron_count` through one admitted hop and its bounded
   transaction aggregate, then run the authenticated-predecessor rest/reopened-
   work acceptance path before changing physics.
6. DSF scope: unchanged full joint seven-field L0-L4 remains authoritative.
   C-021 does not add or reduce a DSF evaluation.
7. Lost DSF structure: none.

## Frozen input and causal path

Input: one ordinary continuous-world batch against the authenticated task-1034
body, followed only when exact recovery occurred by the next ordinary batch.

Path:

`persistent world/body state`
`-> _unattended_interval_episodes`
`-> _perform_admitted_intake_locked`
`-> _commit_admitted_hop`
`-> NativeResidentOrganismPrepare.rest_recovered_neuron_count`
`-> native complete-neuron/local recovery settlement`
`-> current-only successor publication`
`-> bounded rest/wake observation`
`-> public native observation`

Expected output: an exact interval in which native recovery changes one or more
reached neurons and reduces standing dissipated energy without an externally
selected sleep command; the changed successor must have more physically
available dissipation capacity. A later ordinary physical cause must use the
reopened capacity and produce non-recovery settlement or action. If current
physics cannot produce this, the first missing native physical boundary is
recorded and corrected in a separately explicit continuation of this same
acceptance path.

Unchanged invariants: identity, full DSF, complete-neuron/fractal law, learned
state, exact energy/material conservation, one `CURRENT` lineage, zero Python
cognition callbacks, current-only persistence, and reached-frontier resource
work.

## Acceptance-evidence map

| Required fact | Producer | Retained state | Native observation | Python/API evidence |
|---|---|---|---|---|
| Physical rest cause | standing per-neuron dissipation plus finite recovery-fluid state | current neuron lanes and reservoir | exact energy and recovery observations | exact before/after energy plus recovered-neuron count |
| Rest changes reachable work | local recovery drains dissipation and frees the same finite lane capacity | successor lane state | recovered count and energy successor | exact increased available dissipation capacity, never a score |
| Reduced external action | no layer-12/13 recruitment or body actuation in the qualifying rest interval | unchanged body/world where no act occurs | empty recruitment evidence | explicit zero action/articulation for that interval |
| Lawful wake | later external or internal physical cause settles the recovered frontier | next exact successor | non-recovery transition/recruitment/action evidence | predecessor-linked wake evidence |
| Continuity | native current-only codec and publisher | raw `CURRENT` successor | identity/tick/state SHA | public build, identity, tick, state receipt |
| Boundedness | reached-frontier transition | fixed current state | counts/energy/state bytes | CPU/RAM/state/Python-call proof |

## Lifecycle matrix

| Branch | Required result |
|---|---|
| No standing dissipation | zero recovered neurons; no fabricated rest recovery |
| Standing dissipation with available recovery material | nonzero local recovery and exact conserved successor |
| Same post-rest body after cold restore | byte-exact state and identical next physical transition |
| Later physical cause | newly available work is used without a scheduler selecting wake |

## Translation-boundary and execution-cardinality review

- The native getter already exists and is exact; the missing field is dropped
  in `_commit_admitted_hop` and therefore never enters transaction totals.
- Add one integer per hop and one bounded aggregate per transaction. Do not
  allocate per-neuron recovery records, copy neuron bodies, expand exact
  rationals per lane in Python, or rescan the organism.
- Maximum additional Python work is one getter and one integer addition per
  already-committed hop. Native recovery remains one reached-neuron settlement,
  with the RF-044 reached-frontier batching from C-020 preserved.
- No codec or persistence schema changes are required for this evidence
  boundary.

## Applicable recurrence gates

| Failure | Applicability and deterministic check |
|---|---|
| RF-016 task drift | diff, ledger, and acceptance remain C-021 only |
| RF-007 controller invocation | `bash -n tools/deploy_dsf_ai.sh` caught an embedded-Python quoting defect before build; wording corrected and the same syntax check remains mandatory |
| RF-017/028 omitted consumer or aggregate | census getter, hop map, totals, unattended evidence, public observer, tests |
| RF-021/027 wrong successor or quiet overwrite | bind rest and wake facts to their exact predecessor/input/successor |
| RF-031 zero tests | require explicit nonzero executed-test counts |
| RF-032 wrong working directory | resolve every manifest/test path before invocation |
| RF-033 guessed AWS target | re-read `tfe-web-cluster` / `dsf-ai-service-lb` from active deploy controller |
| RF-036 stale native wheel | rebuild/install exact candidate wheel and report loaded module path |
| RF-044 multiplicative work | one getter/addition per existing hop; no per-lane Python materialization |

## Falsified or rejected paths

- `no_internal_cause` is genuine quiescence but does not prove organism-caused
  rest, changed reachability, or wake.
- `WakeState` and `wake_admission` are custody/runtime structures and are not
  extended into cognition.
- A timer, cadence, environment variable, Boolean sleep flag, or observer label
  cannot cause rest or wake.
- Aggregate body energy alone cannot be fed back as one interoceptor or decision
  scalar.

## Observed pre-build evidence

- Exact worktree: `/tmp/guala-whole-brain-mount.Lv41V6`; baseline HEAD
  `533e457361dfea813a52341abdd9e5153fea3244`.
- Focused changed-surface proof: 74 Python tests passed with the exact worktree
  first on `PYTHONPATH`; the dedicated C-021 test executed rather than being
  filtered out.
- Native regression proof: 423 passed, 13 ignored, zero failed. No native
  source or neuron codec changed in this sprint.
- Translation cardinality remains one existing native integer getter per
  prepared hop and one integer addition per committed hop. No per-neuron Python
  object, scan, clone, or persistence member was added.
- Shell syntax preflight first caught one apostrophe terminating the embedded
  controller Python string. The wording was corrected before any image build;
  `bash -n tools/deploy_dsf_ai.sh`, Python compilation, and `git diff --check`
  now pass.
- `ruff` is not installed and no repository Ruff/Black/Flake8 configuration was
  found, so it was not installed as sprint overhead; the declared compilation,
  test, packaging, shell, and native checks remain the release authority.
- Re-resolved live target: AWS account `418384447921`, region `us-east-1`,
  cluster `tfe-web-cluster`, service `dsf-ai-service-lb`, task definition
  `dsf-ai-task:1034`, one healthy running task, zero pending tasks, 4 vCPU and
  16 GiB, image digest `sha256:2d299435813310b054aefce1100ec544ebc6167837ef366daf81d9e36793f890`.
- Process-fixed production inputs are `GUALA_COCHLEAR_EARS=1`,
  `GUALA_TOUCH_RECEPTORS=1`, `GUALA_INTEROCEPTION=0`,
  `GUALA_CHEMORECEPTION=1`, `GUALA_VESTIBULAR=1`, `GUALA_WORLD=1`,
  `GUALA_UNATTENDED_TIME=1`, and `GUALA_CURRENT_FORMAT_MIGRATION=0`.
- A discarded task using the predecessor image exited before physics because
  task 1034's Python wrapper does not expose the already-native recovery
  getter. That is the exact boundary this candidate changes; production state
  was not mutated and no candidate remains running.
