# FB-01 — Functional pre-embodiment body

Owner: A1. Authorized by Joe on 2026-09-25. Base: `guala-live` commit
`8f8b6b83a`. Worktree: `/workspaces/guala-functional-body`, branch
`a1/guala-functional-body`. This is implementation in progress, NOT a release.

## One deliverable and boundary

Provide a functional articulated bipedal body and its physical sensory return,
separate from Guala's cognition and from the environment. Do not supply climbing,
cabinet-opening, feeding, escape, or other semantic action sequences. Hands,
fingers, feet, toes and major joints are required in the eventual body, not
labels on a root-position controller. Initial reference morphology is stable
and child-sized; capacity is declared mechanically, never inferred from a
purported cognitive age. This document does not invent its numeric anatomy.

The active scope is **FB-01g: authorized motor/sensory and world integration**.
Its measured internal-heat (FB-01h) and native sight-geometry (FB-01i) components
are proven offline; ordinary sensory/motor consumption and live delivery remain
open. Next bounded boundary: native scene hits into the existing optical light
calculation without upright-root reconstruction. FB-01a through FB-01f below
are retained implementation/proof history, not the current next item. None alone
constitutes the whole deliverable.
Opening work block budget: 90 minutes for source mapping, implementation, focused
proof and a truthful handoff. Do not spend the block expanding cognition or UI.
No background operation or completion date is implied by this budget.

Preserve unchanged L0-L4, learning state, and G1's sensory-admission repair.
G1 owns `lean_actor.py`, `lean_production_app.py`, `lean_sensory_occurrence.py`
and `static/gualaloom.html`. Do not merge, revert, build or deploy their moving
worktree. Integration uses its reviewed successor, not an old copied checkpoint.

## Inspected source-to-consequence map

| Boundary | Existing source and actual state | FB-01 disposition |
| --- | --- | --- |
| Motor choice | `guala_functional_organism.py:decide`, `candidates` | Named choices are not general joint motor control; do not extend them with `climb` or `open`. |
| World call | `guala_functional_loop.py:settle`, `_apply` | One ordinary world authority; preserve transaction and occurrence semantics. |
| Body storage | `substrate/embodiment_world.py:EmbodiedBody` | Pose, radius, reach, held item and contact; no articulated inertia state. Requires an explicit future schema migration. |
| Collision | `native/guala_core/src/kinematics.rs:disc_in_region` | Root z must equal floor z. Not a 3-D support/gravity solver; do not disguise a bypass as climbing. |
| Body axes | `guala_functional_organism.py:body_axes` | Neck/eyes/lids vary; other declared axes are not demonstrated actuated limbs. |
| Contact | `substrate/body_surface_contact.py` | Reuse exact vectors and bounded arithmetic; linear, opposed, aligned rectangular contacts only. Arbitrary finger contact is not yet supported by this solver. |
| Existing motor return | `guala_motor_world.py:prepare_motor_world_consequence` and `guala_physical_return.py` | Root translation/yaw proprioception and limited yaw vestibular return exist. Presence does not establish mounting in the functional runtime. |
| Active sensory ingress | `guala_functional_loop.py` constructing `Sensed` | Carries vision, sound and coarse skin evidence; full limb/inertial return is not mounted. No zero-fill or scalar 'balance' stand-in. |
| Kernel consumer | `guala_functional_organism.py:_kernel` | Current runtime reduces output to signatures. This is not certification of full-field neuron authority; do not route new signals through that reduction by stealth. |

The future complete path is real motor output -> joint/load settlement ->
world contact and object consequence -> actual limb/site motion and physical
sensory return -> existing lawful receptor/organism input -> one persisted
successor -> truthful observation. Every still-missing mounting boundary stays
explicit. Pure mechanics tests do not demonstrate learning or autonomous motion.

## FB-01a implementation contract

New source: `dsf_ai_service/substrate/functional_body_kinematics.py`.
New proof: `tests/test_functional_body_kinematics.py` (standalone unittest;
no caretaker import, world creation, network, production state or test fixtures).

Use the existing contact module's `ExactVector3`, fraction validation and
256-bit scalar admission boundary. No new vector library, solver, cache,
history, receipt tree, thread, clock, random source or cognitive owner.
Admit an exactly orthonormal right-handed basis and instantaneous rigid motion.
Require explicit metres, seconds, radians and gravity; do not infer acceleration
from endpoints or treat a teleport as a physically continuous motion.

For basis R, world origin p, origin velocity v, origin acceleration a, angular
velocity w and angular acceleration alpha, a fixed local site r has:

    x = p + R r
    x_dot = v + w cross (R r)
    x_ddot = a + alpha cross (R r) + w cross (w cross (R r))

Its ideal inertial evidence in the link frame is:

    specific_force = transpose(R) (x_ddot - gravity)
    angular_rate   = transpose(R) w

Specific force is not a gravity sensor or a 'balanced' Boolean. Free fall
produces zero specific force; supported rest in gravity does not. An angular
rate reading is not an inner-ear physiology model.

For parent motion P and child-relative motion C, use exact rigid-frame
composition including relative translation and Coriolis acceleration:

    r = R_P p_C
    v_rel = R_P v_C
    R = R_P R_C
    p = p_P + r
    v = v_P + w_P cross r + v_rel
    w = w_P + R_P w_C
    a = a_P + alpha_P cross r + w_P cross (w_P cross r)
        + 2 w_P cross v_rel + R_P a_C
    alpha = alpha_P + R_P alpha_C + w_P cross (R_P w_C)

All outputs are exact for the admitted rational instantaneous state. This does
not claim exact representation of arbitrary real angles, continuous dynamics,
or the full biological body. Irrational rotations need a separately declared
numerical representation at the future dynamics boundary, not silent rounding.
Inputs and outputs crossing the existing scalar bound refuse before publication;
do not silently clamp or call this a proof of whole-organism resource bounds.

The functions do no state mutation. Cost is a fixed number of operations per
requested frame/site, with bounded admitted scalar size. Process only affected
chains when mounted; no whole-world/brain scan. Persist primary mechanical state
once when that schema is implemented, not duplicate computed site evidence.

## Acceptance and falsifiers

FB-01a: exact identity and rational rotation, parent-child order, velocity,
angular transport, centripetal and Coriolis terms, rest versus free fall,
orientation-dependent gravity, invalid/reflected bases, scalar overflow,
unchanged immutable input, and repeated bounded stateless evaluation. Same
input must return identical exact values. No integration or production claim.

Whole FB-01: on an isolated authenticated copy, real motor output operates a
jointed hand against a hinged panel; resistance and actual contact return to
the same organism; persisted body/world restore and continue; capacity and
resource bounds hold. No supplied 'open' action or semantic sequence. An
externally applied mechanical test may prove body mechanics but must not be
called learned opening. Observational learning is a separate demonstrated gate.

## Remaining mechanical work, not hidden completion

Numeric reference anatomy and force/energy law; general 3-D contact/support;
joint actuator/effort and proprioception; mounting into the actual live motor
and sensory call paths; body/world schema and cold continuation; display of
actual geometry; copied mature-body performance and production release. Do not
add detailed muscles, growth simulation, a new physics service or a learning
controller to this scope. Do not add fields to G1's ingress contract unilaterally.

## Entry evidence / prior failures / coordination

- G1 owns the active lane repair; A1's earlier chair audit remains separate.
  G1's reported task 1543 restored feeding; live baseline is rechecked below.
- Prior chair restriction removed motor choices by object name; not reusable as
  a physical restraint law. Prior release retained stale contacts; never migrate
  a pose while retaining an incompatible contact patch.
- Available skill bootstrap paths `scripts/require-guala-root.sh` and several
  August authority documents are absent in this checkout. Verified root by
  Git worktree/branch, full AGENTS.md and actual source. Do not invent outputs.
- The shared ledger's tail at entry ends on Sept 24 task 1535, despite later
  receipts in conversation. Use live/source evidence, not the stale tail, for
  current status; report this drift to G1.
- No production process, marker, test, API write or deployment is part of this
  opening block. Independent review and full integration remain release gates.

## 2026-09-25 opening-block result

Source-only formula review completed before execution: rotation columns,
right-handedness, derivative reference frames, Coriolis factor two, angular
transport term, gravity subtraction and immutable refusal behavior checked.
This was A1 self-review, NOT independent release approval. The source and test
were frozen by SHA-256 before running the standalone suite (the historical
fingerprint helper is absent here).

- Source SHA-256: `3d3116c6dbac09bcb38751be3ddcbf1a15d88792abc9078c392044dd01a711ba`.
- Test SHA-256: `195f873d4c59dd250702391047f8d28efb691854da2c91d0c44a12022f21acf0`.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. timeout 30s python3 tests/test_functional_body_kinematics.py -v`:
  **12 passed in 0.010 s**, exit 0. No fixture or application import.
- Bounded local microcheck: 500 single-edge compositions plus inertial samples
  in 0.154486 s (0.308971 ms each). Separate 100-evaluation tracemalloc window:
  current 488 B, peak 3,720 B; whole-process max RSS 12,792 KiB. These are
  small-rational local measurements, NOT whole-body/production timing or a
  claim that every input reaches this cost.
- No worker, background test process, runtime import or production writer was
  created. No existing source file was edited in either worktree.
- Read-only AWS envelope: 14:34 UTC resolved task 1543, desired/running/pending
  1/1/0. During local proof G1's separate deployment stopped predecessor
  `0ced705eba704130b21dd43090686bb3` and staged task definition 1544 at 0/0/0.
  Therefore this is NOT an uninterrupted production-health proof and no
  production performance comparison can be drawn from it. Predecessor digest
  matched G1's `1706d543dc87...`; historical `guala-clock-stalled` remained
  ALARM. CloudWatch 14:15 average CPU 53.32%, max 54.57%; average memory 5.765%,
  max 5.811%. The 14:30 window spans the other agent's cutover; do not attribute
  that window's lower utilization to this unmounted code.

Next implementation boundary: declared joint/segment mechanics with force,
energy, position and actual support/contact, feeding this same frame law. Do
not replace that work with calling this module on desired poses or mounting an
ideal inertial sample as a biological/neural experience by itself. No new
semantic action, score, logging hierarchy or neuron law is authorized.

## FB-01b — Force transmission and mechanical energy (active)

Joe resumed the bounded functional-body goal. FB-01a stays locally verified,
not live; this advances its next mechanical dependency, not cognition. G1's
main-tree transport changes remain excluded. Authorized new files are
`substrate/functional_body_dynamics.py` and its standalone test only.

The biological function is load-bearing segments transmitting contact forces
and opposing joint torques; its reduced mechanical equivalent is rigid-link
Newton-Euler dynamics. Use mass and principal inertia supplied as morphology,
not an age multiplier or guessed strength. No microscopic muscle kinetics,
deformable link modes or chemical efficiency are claimed. Principal-axis
coordinates retain the complete rigid-link inertia, not a scalar DSF proxy.

Physical contract: a force/torque pair at a declared origin shifts to another
origin by `tau_new = tau_old + (old_origin-new_origin) cross force`.
Power is `force dot velocity + torque dot angular_velocity`. Opposing joint
torques transfer power according to relative angular velocity, not an action
name. For a link whose origin is its centre of mass and axes its principal
axes, `force = mass * acceleration` and
`torque_body = I * alpha_body + omega_body cross (I * omega_body)`.
Forward acceleration inverts this same law; all force/torque arguments include
gravity and contacts explicitly. Kinetic energy is
`(mass * v dot v + omega_body dot (I * omega_body))/2`.
The gyroscopic term must remain: it changes angular acceleration without doing
work. Positive principal inertias must satisfy the mass-distribution triangle
inequalities. No full population/world scan or dense joint matrix is introduced.

Impact/evidence path for this slice: external physical load + declared segment
mass/inertia + actual current motion -> exact instantaneous force/acceleration
and power -> FB-01a site acceleration/inertial evidence. This stops at a local
mechanical return. No native observation, Sensed input, API, codec or UI changes;
every output remains backend-only and unmounted. It supplies a necessary
primitive for the whole-FB panel/contact acceptance, not a replacement for it.
It does not yet solve coupled joints, integrate orientations, enforce strength,
consume metabolic reserves or claim finite-interval energy conservation.

Inputs are immutable; outputs are prepared completely before return. Arithmetic
uses the existing Fraction/vector 256-bit boundary; overflow refuses without
mutation. No stored record, secondary clock, identity, cache or new persistence
schema. Fixed operation count per reached segment or load; no recurrence growth.
First-use and repeated calls obey the same pure contract; restart means no
module state to reconstruct, NOT proof of organism cold continuation.

Exit proofs: exact Newton-Euler round trip, non-principal spin/gyroscopic term,
power versus kinetic-energy derivative, origin-shift power invariance, rational
frame covariance, equal/opposite joint torque power, supported rest versus
gravity-only fall through existing inertial evidence, invalid inertia, overflow
and deterministic input immutability. Freeze source for independent review
before executing tests; no world, caretaker, network or application test fixture.

Derivation checked against the primary Modern Robotics rigid-body chapter:
https://modernrobotics.northwestern.edu/nu-gm-book-resource/8-2-dynamics-of-a-single-rigid-body-part-1-of-2/
This is standard mechanics, not a new DSF or neuronal learning law.

### FB-01b result — 2026-09-25 14:55Z

Independent source-only review by `body_force_review` passed with no required
corrections. The reviewer verified both file hashes before/after; this is a
file-hash-scoped review, not a whole-worktree freeze or release approval. The
historical root validator again requires a handoff absent in this branch;
review explicitly used the verified git worktree and named dependencies.

- Source SHA-256: `2ba1a8c671e749b39fe1b28781a391d593dcc6a99321b4990bb52a9c81544ddb`.
- Test SHA-256: `5b859533cb044eaad53f0326ccd146e48c1b170222706a73fb529b31db174659`.
- Standalone `test_functional_body_dynamics.py -v`: 12 passed, 0.015 s.
  Includes 54 exact round-trip regimes, off-centre force -> segment
  acceleration -> site inertial reading, and the falsifiers specified above.
- Existing standalone kinematics: 12 passed, 0.010 s. Both used
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. timeout 30s python3`; no pytest,
  application/world/caretaker imports, live requests or retained test state.
- Test process completed synchronously; post-run census has no test/timeout
  child. One pre-existing python3 process remains untouched. Candidate hashes
  match pre-review values; `git diff --check` passes.
- Read-only AWS before/after: service desired/running/pending 1/1/0, task1544
  `3a19bd326e5d4ae0aae0bb1c7c8c64e1` RUNNING/HEALTHY, digest
  `23122cdde859e3de1480d3703396dd5ddd388d48a6858608520c487e0737457a`.
  14:50 CloudWatch bucket after test: CPU average50.72%, maximum51.21%; memory
  average4.734%, maximum4.944%. Historical clock-stalled alarm remains ALARM;
  CPU, memory, EFS and refusal-loop alarms are OK. Aggregate metrics are
  coarse operational context, not a local-mechanics performance comparison.

FB-01b is locally exercised/unmounted. No strength limit, finite-time energy
transfer, body schema, contact support, live sensory mounting or autonomous
movement has been certified. The next exact dependency is coupled joint
constraints: do not apply isolated-segment accelerations independently to
connected limbs. Existing EmbodiedBody has no mass/inertia fields; its 250-mm
radius and 800-mm reach do not determine anatomy or strength. Carry this known
missing morphology boundary forward rather than inferring cognitive age.

## FB-01c — Coupled hinge-tree acceleration (active)

Previous turn: progress, commit ff1c28f26 and local force proofs. This advances
coupling, not a reopening of those laws. Requested architecture: one physical
articulated body, no independently accelerated disconnected limbs. Current
reality: kinematics and isolated segment forces exist; coupling is missing.
Conflict: yes, the requested full body is not implemented. Do not extend
semantic motor choice, G1 ingress, floor-disc collision, or kernel code. Next
item: exact instantaneous acceleration/reaction of a free or explicitly
supported tree of massive segments connected by physical revolute hinges.
This is reduced rigid mechanics; no DSF field is consumed or compressed.
Deformable tissue, friction, joint limits and finite-time integration remain
outside this slice and are not silently approximated by this solver.

Files: new `substrate/functional_body_articulation.py` and standalone test.
Reuse mass, motion, basis, wrench and vector laws from FB-01a/b. Each child's
COM pose follows coincident physical joint anchors; its actual relative basis
must map the child hinge axis onto the parent hinge axis exactly. Parent
indices precede children, defining one acyclic tree rooted at the actual base.
No object labels, cognitive command names, desired-pose controller, motion
script, phantom mass or joint-strength constants. Multiple finger/limb branches
use the same law. This first joint type is a hinge, not a full shoulder/hip.

Use spatial columns [angular acceleration; COM acceleration] in WORLD axes,
not DSF fields. For parent-to-child COM displacement r and child hinge-to-COM
lever l, axis s, relative angular rate qd:

    X * [alpha; a] = [alpha; a + alpha cross r]
    S = [s; s cross l]
    omega_child = omega_parent + s * qd
    v_child = v_parent + omega_parent cross r + (s cross l) * qd
    c_angular = omega_parent cross (s * qd)
    c_linear = omega_parent cross (omega_parent cross r)
               + 2 * omega_parent cross ((s cross l) * qd)
               + s cross (s cross l) * qd^2
    A_child = X A_parent + S qdd + c

At each COM, I is the 6x6 rigid inertia (rotational tensor in world axes and
mass times identity), p = [omega cross I_rot omega; 0] - external_load.
Leaf-to-root articulated elimination:

    U = I_A S; d = S^T U; u = effort - S^T p_A
    I_reduced = I_A - U U^T/d
    p_reduced = p_A + I_reduced c + U u/d
    I_parent += X^T I_reduced X; p_parent += X^T p_reduced

Solve the floating root's six equations once, or use explicitly supplied
physical base acceleration and return its required support wrench. Then
root-to-leaf qdd=(u-U^T(X A_parent+c))/d. This is the standard articulated-body
elimination derived from Newton-Euler, implemented independently; no external
source code copied. Fixed-size (6x6) blocks per segment, linear tree passes,
no n-by-n joint matrix, dense world scan, timestep loop or persistent cache.
Primary algorithm reference: https://royfeatherstone.org/papers/icra00.pdf

Return actual COM motion and bearing wrenches through the existing force law.
These are reusable physical proprioceptive/contact inputs, not new receptors.
Root and child state remain immutable; prepare the complete result before
return. Input/operation/result rationals retain the existing bit bound, with
explicit side-effect-free refusal on overflow. Repeated calls retain no state.
Neither this module nor its tests boot any organism or world. No new persistence
format or production call path is mounted in this slice.

Acceptance: coupled two-link off-centre force accelerates the parent (unlike
isolated segments); joint anchors match position, velocity and acceleration;
free-body total momentum and power obey applied loads; explicit support reports
its reaction; asymmetric spin, nonzero joint rates and rotated axes work;
branches preserve reactions and power; malformed graph/axes and overflow refuse
without mutation. Cross-check the returned whole-tree motion by independent
Newton-Euler back-substitution and energy-rate balance. Existing a/b proofs
remain. Only after the new module passes independent frozen-source review may
the bounded standalone tests run. Whole-FB mounting and live acceptance stay
open; no coupled limb motion is to be claimed from this source-only milestone.

### FB-01c result — 2026-09-25 15:08Z

Independent file-hash-scoped source review by `body_force_review` passed with
no required corrections. Derivation rechecked world-coordinate acceleration
conventions, hinge anchor constraints, elimination, support reaction and power.
The historical missing root-handoff/whole-tree-freeze limitation remains.
Source SHA `f2ff14ffc73976e592c7fef506367129814bb1beabe0b2004c5e5b0f6ba2a6cc`;
test SHA `e05616d7f5eac7e91f40f8a97193f5a6a679391cd51eafebddc5a358b16b43ef`.
Both unchanged after review and test.

Standalone articulation tests: **10 passed in0.029s**. Existing force tests:
12 passed in0.017s; kinematics:12 passed in0.011s. Commands used
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. timeout 30s python3 <test>`, no pytest
or application/world import. Off-centre unit-force proof produced parent
acceleration1/4 and child3/4 m/s^2, with equal joint-anchor acceleration;
isolated-body solution differs. Moving asymmetric branches satisfy Cartesian
Newton-Euler, anchor position/velocity/acceleration, actual effort projection
and instantaneous energy-rate balance. Free fall produces no fake joint motion.

Bounded local resource probe, same unit-mass/inertia straight chain with
1rad/s at each joint and a unit tip force: 1 hinge1.57ms,3 hinges2.96ms,
12 hinges13.02ms,24 hinges22.11ms. One separate tracemalloc24-hinge call:
current88,816B,peak201,777B, process maxRSS14,080KiB. This does not establish
worst-case input cost or full-body production latency; numerical size, contacts,
finite-time integration and neural return remain outside the measurement.
Stored/admitted scalars are checked at256bits; fixed-depth temporary Fraction
expressions can be wider. No claim that every intermediate is256bits.

No harness child/timeout remains in the post-run census. Git whitespace check
clean. Read-only AWS service stayed1/1/0 on1544, task
3a19bd326e5d4ae0aae0bb1c7c8c64e1 RUNNING/HEALTHY, unchanged digest23122cdd...
Before test,15:00 CPU average51.30%,max53.57%,memory average/max4.749%.
Historical clock-stalled remainsALARM, resource/refusal alarmsOK. No live writes.

Next boundary: finite-time evolution with geometry, energy and limit/contact
handling. Do not simply add accelerations to poses and claim that joints,
support, collision avoidance or energy remain exact. Current rational bases
represent instantaneous orientations; arbitrary finite rotations need an
explicit numerical/physical representation, not silently rounded coordinates.
FB-01 remains active and NOT deployed; this is not learned locomotion.

## FB-01d — Finite-time representation boundary (active)

Previous turn was progress: coupled-mechanics commit32fb1353e, source review,
34 passing mechanical tests. Before authoring time integration, probe whether
the admitted exact rational orientation can actually recur within its fixed
storage bound. Source reality: existing world poses are millimetre positions
and millidegree headings; native kinematics enforces a floor disc. Existing
rounding/trigonometry in unrelated sky/path code is NOT authority for a new
whole-body integration accuracy or energy law. No relevant finite-time
articulated integrator was found in the inspected slice.

Authorized diagnostic: `tools/probe_functional_body_rotation_bounds.py`, outside
the production path. It uses FB-01a RigidBasis only; zero world/caretaker/API
construction, writes or subprocesses. Sweep declared angular rates1/10,1,10
rad/s and nominal durations1/1000,1/100,1/4s, each at most128 compositions.
Each Cayley step is exactly rational and orthogonal, using
`c=(1-h^2)/(1+h^2), s=2h/(1+h^2), h=rate*dt/2`.
Its actual rotation angle is2atan(h), not rate*dt: this is solely a storage
growth probe, not a proposed accepted integrator. It stops only on the existing
specific256-bit refusal; every other exception propagates. Output records
accepted/rejected composition counts and the nominal elapsed interval.

Independent read-only source review by body_force_review passed without defect
on SHA0e9e29b45b8993275faf317f5b3f21fa9bb1288dc1cef001a431fcd6181c5cc3,
unchanged before/after. It can refute indefinite recurrence of these sequences,
not prove impossibility of all numerical representations. No rounding, bound
increase, new body state or force-law change is authorized by the probe itself.

One read-only search incorrectly named absent embodiment_kinematics.py and
embodiment_commands.py paths; rg reported both missing, with no mutation. Do
not repeat those guessed paths. Verified actual world/native source instead.

### FB-01d diagnostic result and bounded corrective proposal

Standalone command, exit0:
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. timeout 10s python3 tools/probe_functional_body_rotation_bounds.py`.
Reviewed source hash remained unchanged. All nine cases hit the existing
256-bit admission bound. Accepted compositions before refusal:

| nominal rate rad/s | dt=0.001s | dt=0.01s | dt=0.25s |
| --- | --- | --- | --- |
| 0.1 | 8 | 11 | 20 |
| 1 | 11 | 16 | 42 |
| 10 | 16 | 29 | 47 |

These are representation failures, not observed physical instability. For the
1rad/s,0.01s case the seventeenth composition refuses after0.16 nominal seconds.
The Cayley-angle qualification above still applies. No claim that this proves
all exact representations impossible; it rejects repeatedly composing this
rational basis as the sustained-motion representation. Raising the bound is
not the proposed correction. Existing instantaneous mechanics remain accepted.

Recommended correction: explicitly allow deterministic bounded-error numerical
integration for the simulated mechanical body/environment only. Keep immutable
anatomy and finite current generalized position/velocity state; derive limb
poses from the connected joint geometry, not independent unconstrained endpoint
updates. Carry no motion-history store. Specify spatial/angular accuracy from
the actual supported contact/joint geometry, fixed execution order, bounded
step work, and energy/momentum error acceptance before implementation. Test
convergence, long recurrence, cold restart and collision-boundary cases. Do not
convert integration error into invented heat or metabolic intake; do not call
numerical conservation exact. An unresolved numerical contact must not be
reported as verified collision-free motion.

This is a proposed numerical body law, not a completed solver or approved
accuracy budget. It does not touch DSF, neuron arithmetic, cognition, semantic
action selection, G1 transport, or live state. Joe authorized minimal functional
approximations, but the existing body contract explicitly deferred this
numerical-law decision. A1 requests the narrow numerical-approximation exception
before changing that contract. The quantitative error budget and integration
implementation remain A1's engineering responsibility, not a task for Joe.

Health qualification: pre-probe task1544 service1/1/0 was recorded. At15:16Z
post-probe AWS service was0/0/0 on1544 and task list empty; another agent's
`tools/deploy_guala_retention_release.py --execute` was active (PID33806).
A1 performed no production mutation. Do not call this a healthy before/after
production envelope or attribute the cutover to the pure local diagnostic.
Process census contains no remaining rotation-probe or timeout child.

FB-01 remains incomplete and not deployed. No numerical integration source
has been authored under the proposed exception. The immediate next item is
ratification of that one body-only representation change, not new diagnostics,
kernel changes or biological micro-simulation.

### 15:19Z ratification and FB-01d implementation contract

Joe explicitly answered "Approve body-only numerical approximation
(recommended)". The exact-rational recurrence proposal is retired. The pure
instantaneous exact reference remains; the numerical approximation is confined
to the mechanical body and cannot become a DSF/neuron/cognitive reduction.

Single candidate: factor the existing joint-tree elimination into one shared
arithmetic core in functional_body_articulation.py. Keep its exact public
inputs/results and previous proofs unchanged. New functional_body_evolution.py
uses binary64 vectors/quaternions and generalized hinge angles/rates to feed
that same core, never a second dynamics law. New standalone
test_functional_body_evolution.py exercises finite motion only.

Immutable anatomy is mass/inertia, parent order, anchors, hinge axes and rest
orientation. Current state is exact integer microsecond time, root position,
unit quaternion, root linear/angular velocity, joint angles/rates. Child poses
are derived from hinge constraints; no independent drifting endpoints and no
history, world identity, memory, semantic controller or cache. Applied loads
are held constant in world axes about each COM for the requested interval;
joint efforts are constant. Root is free: no hidden floor/support. Contact,
limits, capacity/metabolic supply and changing-load event detection are not
implemented by this free-motion seam and cannot be claimed on its evidence.

Classical fourth-order Runge-Kutta integrates this finite smooth free-motion
interval. Quaternion derivative is 1/2 times [0,omega_world] * q; normalize
orientations for frame evaluation and the final state. Fixed caller-declared
subdivision count, no adaptive retry loop; run N and 2N subdivisions to expose
step-refinement differences. Caller supplies maximum subdivision budget and
physical tolerances explicitly; no production tolerance is invented. Refuse
non-finite/invalid state, budget exhaustion, excessive pose/rate difference or
energy-work residual before returning any successor. Step-refinement is an
error indicator, NOT a certified universal error bound or contact guarantee.
Mechanical work is integrated with the same RK stages; energy error is reported
and checked, never converted to heat or hidden by rescaling velocities.

Determinism claim is bit-repeatability on the same arithmetic/runtime, including
after reconstructing identical serialized current state. Cross-platform libm
identity and world-authority cold restore remain unproven. No new standalone
persistent store or codec: actual world-schema integration remains later.

Verification: zero-load rest/free drift, gravity and loaded analytic cases,
joint-constraint closure, torque-driven two-body momentum/energy, exact-reference
instantaneous comparisons, timestep refinement for asymmetric tumbling, long
recurrence without fraction growth, replay from copied serialized state,
non-finite/budget/error refusal and unchanged predecessor. All proof values are
test mechanics, not invented Guala anatomy or production accuracy thresholds.
Complexity O(links * subdivisions), fixed binary64 scalar width and O(links)
temporary storage, no retained timestep history. Independent frozen source
review precedes all execution. No production integration or deployment gate
is waived by this mechanical-only proof.

### FB-01d frozen source review / execution admission

Independent body_force_review found one localized precision defect before any
execution: at position2^60m, velocity1m/s, coarse and fine integration could both
lose the one-metre displacement because binary64 spacing is256m. Added necessary
ULP-resolution admission against caller SI tolerances at every RK stage and
endpoint, including unwrapped hinge angles and derived body-site geometry.
This is not a rigorous accumulated-error enclosure. Added those exact refusal
tests and a rotated nonparallel-hinge comparison with the exact reference.

Final review also caught a test-only ordering mismatch: its1e-15 angular-rate
tolerance was below the initial omega=(2,3,4) combined spacing1.088e-15.
The test's angular-rate tolerance alone is now1e-12; its energy/angle1e-15
acceptance remains strict. Reviewer verified that exact correction and final
hashes, with PASS to focused tests and no outstanding source finding.
No architecture/review loop or execution was used to discover the force law.

Frozen source SHA: articulation
`d1fc865c0d688adedd384ed00bf133409862df473737a9cb7e40ccf70d559351`;
evolution `0230b14043c24491aaf56c68f8613009a43d542bbfebb1cde878a7e770d79884`;
test `00fece4ce590632f524a9f7ff1d953d02b6e4b3927c060fb9d3a604cb8174fbb`.
Review is file-hash scoped; absent historical whole-tree helper remains disclosed.
One tooling failure occurred before edits: apply_patch rejected delete-and-add
of the same path in one patch. No source changed in that failed operation;
subsequent replacements used one full-file Update patch instead. Do not repeat.

Before execution: at15:37Z task1547 `772d1e4f5096497e879f12a4cba2bcb4`
RUNNING/HEALTHY, service1/1/0, digest
`d180f16cd50a1089365cfccd648560ab7bda14a65e2886c09c1fc93d7e5c3d93`.
15:35 CPU average51.59%,max52.91%;memory average4.643%,max4.724%.
Historical clock alarm remainsALARM; resource/refusal alarmsOK. G1's cutover
is separate. Current process census shows its caretaker PID37677; no A1 test
process or orphan. Standalone tests import no application/world/network fixture.

### FB-01d local result — 15:41Z

13 evolution tests passed in0.549s. Exact articulation10 tests in0.028s,
forces12 in0.016s and kinematics12 in0.011s all pass unchanged. Total47 focused
mechanical tests, not47 organism/production tests. Standalone commands used
PYTHONDONTWRITEBYTECODE=1, PYTHONPATH=. and timeout60s (evolution) or30s
(foundations); no pytest, world, caretaker or API fixture import.
Final reviewed hashes unchanged after all execution. Same-runtime JSON
round-trip of the numerical state reproduces the exact next result; this does
not prove existing world-authority migration/cold restore or cross-platform libm.

Bounded local resource sample used unit-mass/inertia straight chains with
root angular rate0.1rad/s and every hinge rate0.1rad/s, zero external/joint
loads. Physical interval1000us, one coarse/two fine RK4 subdivisions, explicit
1e-7 SI test tolerances (NOT production defaults):

| hinges | elapsed ms | position refinement m | energy/work residual J |
| --- | --- | --- | --- |
| 1 | 4.370493 | 3.312e-22 | 0 |
| 3 | 9.592924 | 2.168e-19 | -4.441e-16 |
| 12 | 36.755156 | 3.990e-17 | 3.411e-13 |
| 24 | 71.702919 | 1.804e-15 | 5.457e-12 |

Separate24-hinge traced call: current96,720B,peak211,744B; process maxRSS
14,880KiB. No retained trajectory, checkpoints or raw sensory data. These are
one-call local measurements, not worst-case,1000Hz real-time, full-body250ms
or production latency evidence. Actual anatomy, contact events and required
subdivision cost remain to be measured before mounting.

Lean closure: one shared elimination, no parallel dynamics owner, history,
cache, registry, worker, codec or network boundary. Numeric inertia and immutable
anatomy conversion happen once; stage work follows the physically coupled tree.
Known residual work to handle in the body mounting slice, not as a second
optimization sprint: all-zero free-body rest currently runs RK stages despite
an exact zero derivative, and diagnostic endpoint kinematics computes transform
blocks it does not use. Do not claim zero-work quiescence/full cost closure yet.
Retire this unnecessary work when mounting recurrent body settlement, with the
same successor and resource proof; do not hide it behind a cache or new thread.

Post-run process census: only G1 caretaker python PID37677, no test/timeout
survivor. AWS remained1547, task772d1e4f5096497e879f12a4cba2bcb4,
RUNNING/HEALTHY, service1/1/0, unchanged d180f16c... image.15:39 CPU
average51.58%,max53.70%;memory average/max4.651%. Historical clock alarm still
ALARM; resource/refusal alarmsOK. No A1 production mutation.

Finite-time free-motion candidate is locally verified, NOT live and NOT a
complete body. Next mechanical boundary is joint stops and physical support/
contact; numeric integration cannot be used to cross a floor, hand-object
surface or anatomical limit merely because free-motion tests pass. Keep the
remaining strength, sensory mounting, world migration and production proofs
in the original FB-01 objective; no cognition or G1 ingress expansion.

## FB-01e — Contact/support boundary, 2026-09-25 15:52Z

This continues FB-01 after locally accepted finite free motion at a81d2d306.
No test, production, dependency or mechanical source change in this block.
Joe's body-only numerical approximation approval remains ratified; it does
not automatically ratify a different contact constitutive law.

Independent source-only contact review found the precise missing boundary:
body_surface_contact.py settles prescribed linear trajectories between opposed,
aligned rectangular patches. Its normal spring and viscous tangential law is

    K = area * series_normal_stiffness
    D = area * series_tangential_damping
    delta = max(-gap, 0)
    F = K*delta*n - D*v_t
    U = K*delta^2/2

At zero slip, tangential force is zero; the existing law cannot sustain a
frictional pinch grip or friction-dependent stance. Normal support requires
K*delta=mg AND torque balance, and no normal damping currently establishes
settling. General rotating footprints, pressure moments and collision events
are absent. These are body mechanics gaps, not absent cognitive intentions.

The contact receipt also lacks a work-conjugate contact application point or
couples. Applying opposite forces at separated site centres creates a net
moment (x_B-x_A) cross F. A lawful coupling needs common interaction geometry,
reciprocal COM wrenches and stage-consistent motion/force evaluation. Merely
feeding endpoint forces into free RK4 is rejected: contact onset, containment
and alignment can change inside an interval. Refinement alone does not certify
absence of those events. No such partial coupling was implemented.

### Recommended single decision: native body mechanics backend

Ask Joe to authorize MuJoCo as the body-only numerical mechanics backend for
joints, collisions and friction. This is a proposed replacement of the custom
motion execution path, not a second clock, service, controller or cognitive
authority. No installation or dependency edit has occurred. The existing
instantaneous exact mechanics may serve as offline reference evidence, never
as a second concurrently executing body solver.

This recommendation avoids developing a new general collision/friction engine.
It is NOT a claim of contact-law equivalence: MuJoCo documents a soft convex
contact model, not the existing aligned spring/viscous skin law or a strict
hard-contact complementarity model. Numerical optimization of mechanical
constraints is not learned action selection. Contact parameters, penetration,
slip and energy residuals must be explicit and verified; default parameters
may not be represented as measured Guala material properties.

Primary references inspected:
- https://mujoco.readthedocs.io/en/stable/computation/index.html
- https://mujoco.readthedocs.io/en/stable/programming/simulation.html

Version must be pinned before implementation; stable documentation is not a
version guarantee. The package is not installed in this environment. No native
performance or body/world integration proof exists yet.

If approved, one bounded native body/contact candidate must prove a loaded
articulated hand physically transfers force to a hinged panel, contact
reciprocity and support, declared joint/capacity limits, error-budget refusal,
and exact same-runtime restart from the complete integration state (including
solver warm-start state if used). No supplied open/climb routine, position
servo impersonating cognition, automatic reset to default pose, or dropping
contacts on resource overflow. One world mechanical authority and no retained
step history. Existing thermal mechanics and full DSF/neuron/cognition remain
unchanged; any unavailable general thermal contact mapping stays explicit.

The decisive complete FB-01 live acceptance above is unchanged. This proposal
does not close the motor/receptor mounting, authority migration, strength,
resource or production gates. Dependency choice and approximation authority
are the only question now; Joe is not being asked to design equations.

Process/command honesty: a preliminary source search included nonexistent root
pyproject.toml and requirements.txt and returned path errors. Corrected to the
actual native Cargo manifest, service lock and substrate paths; no matches for
an existing MuJoCo/PyBullet/Rapier/PhysX integration in that bounded slice.
Do not repeat guessed paths. pip show reported MuJoCo absent. No harness,
installation, background process, test or AWS mutation occurred in this block.

## FB-01e authorized native implementation contract

Joe explicitly approved everything needed within this pre-embodiment scope;
the contact/backend decision is cleared. No DSF, cognitive or semantic-policy
change follows from that authorization. Resume implementation, not another
approval loop. Native dependency pinned to MuJoCo3.3.7 (not an unpinned latest).
Local isolated venv: /tmp/guala-body-native.pnUH8P. No caretaker package altered.

One native settlement authority replaces functional_body_evolution.py and its
standalone test. Prior accepted commit preserves that superseded implementation;
exact instantaneous kinematic/force references remain offline differential
oracles, never parallel runtime solvers. New functional_body_native.py and
test_functional_body_native.py are the only mechanical candidate files.

Input: trusted immutable MJCF anatomy/environment, direct bounded scalar joint
efforts, integer elapsed microseconds, a caller-supplied mechanical-work budget,
and the complete preceding native integration state. Output: immutable next
integration state plus SI joint/pose/inertial/contact observations and actual
numerically integrated actuator work. No target pose, behavior names, action
sequence, reward, optimization of cognition, second clock or background worker.
Motor law is ideal effort-limited actuation, not microscopic muscle metabolism;
mechanical work is not a claim of isometric metabolic expenditure.

Use one MjModel and reusable MjData scratch. The caller retains the authoritative
state, not the workspace. Restore full mjSTATE_INTEGRATION before each candidate;
return a successor only after all fallible checks. Exceptions publish nothing,
and the next call restores its explicit predecessor. Cold replay uses the same
version/model/runtime and complete state including solver warm-start. Compiled
model digest distinguishes anatomy; no full-brain serialization. No external
XML assets/plugins/mocap/controllers. Motor transmission is unit-gear direct
hinge/slide effort with no actuator dynamics or bias; require finite limits.
Explicit solver timestep, iteration limit, arena and tolerance are anatomy/
numerical configuration, not learning rules.

Native numerical approximation is soft contact/friction and finite timestep
collision sampling, not existing exact rectangular skin-contact equivalence.
Fixed caller-declared maximum substeps, penetration, joint-limit overrun and
surface travel per substep; refuse native warnings/non-finite states/automatic
reset, excess work or mechanical-resolution breach. No retries, resets, invented
heat or energy rescaling. Endpoint travel checks and refinement tests are
numerical checks, not continuous collision certificates. Per-substep positive
actuator-work quadrature is an approximation; compare resolution and report it
as mechanical work, not exact biochemical intake.

State has bounded O(body+joint) size; contact scratch is constrained by compiled
arena and warning rejection, solver iterations and interval substeps. Store no
history. Contacts are native instantaneous geometric patches and force/torque
in the declared contact frame; observations are backend-only physical evidence,
not neural sensing until existing receptor and world mount is verified. Surface
temperature/conduction is untouched, not supplied by this new contact solver.

Frozen acceptance: hand effort -> physical panel hinge displacement with contact
force; no effort/no contact controls; gravity support versus free-fall inertial
return; finite joint limits; effort/work/penetration/substep refusal preserves
predecessor; cold contact restart gives identical next state; repeated stepping
does not grow state. Measure bounded native compute and memory. Model fixture
is declared bench geometry/material, NOT invented production Guala anatomy.
Production body/world migration, force supply accounting, receptor mapping and
deployment remain required FB-01 work, not waived by local acceptance.

### FB-01e source review and local execution — 16:29Z

Independent frozen source review found localized admission/evidence omissions:
joint force caps, actuator group disabling and gravity compensation could
invalidate requested-effort work; callbacks could alter unretained dynamics;
deformable models exceeded rigid refresh; derived evidence needed finite
checks. Corrected as one batch, added admission/refusal/grip falsifiers and
identified actual hand/panel contacts. Reviewer passed the final candidate.
Pinned upstream3.3.7 source confirmed mj_forward does not overwrite warm-start
or advance time, and collision refresh is safe here because forces are exposed
only after a subsequent full forward evaluation.

First test run:1 passed,11 errors, all at the same restore binding before any
motion. Python mj_setState requires writable float64 storage although its C
input is const; np.frombuffer(bytes) is readonly. Local correction reuses the
already allocated state buffer, preserving all input bytes and adding no
allocation. Independently confirmed before rerun. This was an interface error,
not11 independent physical failures. One earlier tool orchestration call had a
JavaScript syntax error before executing anything; no file changed in that
failed call. Both failures are retained here, not omitted from the receipt.

Frozen final source SHA256:
- native: d82a5312c264aa1602aec795d56554ffd3b5eff24332c41cb9535c005a7396f0
- tests: 98c319ac98086aad0d67b0a98236a19d2af8f69e4c0b8abcc89b8790014208b2
- requirements: 323480714843c153d25b88090bdeac9a4176e0e7412d64b9641b6444c458e5b7
- installed libmujoco.so.3.3.7:
  23841520ecf60ad648405674a757f260949f7cf6b44deb284398b9851b3f061d

Executed the complete panel/contact/restart acceptance first:1 passed0.149s.
Then12 native tests passed1.224s with no assertion relaxed or expected failure.
Exact-reference articulation10 passed0.030s, dynamics12 passed0.017s,
kinematics12 passed0.011s.46 retained/current mechanical tests total; the
superseded13 free-integrator tests were removed with their execution module,
recoverable at a81d2d306. This is not46 organism or production tests.

Commands used standalone unittest modules under PYTHONDONTWRITEBYTECODE=1,
PYTHONPATH=. and timeout60s (native) or30s (references). No pytest/conftest,
world authority, caretaker, live API write or simulated cognitive loop.

Evidence:
- Jointed hand effort physically moves the separate hinged panel; no-effort
  control does not. Removing the panel removes its resistance.
- Current contact state restored into a fresh engine gives an identical
  complete next result, not merely matching joint position.
- Supported rest reports weight/specific force; free fall reports zero specific
  force. Analytic free-fall position/energy error is bounded by the expected
  timestep error and halves under timestep refinement.
- Joint stops, motor capacity, mechanical supply, interval budget, penetration,
  surface travel, altered motor authorities and installed callbacks refuse as
  declared. Refusal leaves the caller's predecessor usable and unchanged.
- Two opposed jaws hold an independent free mass through friction. After0.5s,
  initial object height0.5m: squeeze1N/jaw and friction0.8 =>0.498532987m;
  friction0 =>-0.728682660m; squeeze0 =>-0.652939644m. No weld, held flag,
  kinematic object pose or hidden support. All three states remain512bytes.
  This is finite-time approximate grip with1.47mm vertical compliance/slip,
  NOT zero-slip permanence or biological muscle efficiency. Ideal static
  effort has nearly zero positive mechanical work; metabolic tone is absent.

Bounded local timing sample: five identical250ms intervals per chain,1ms fixed
native steps,0.0001Nm on each hinge,0.1kg per link, gravity0,2MiB native arena.
This is declared test anatomy, NOT Guala's eventual reference body or worst-case.

| joints | median ms | max ms | current state bytes | Python allocation peak bytes |
| --- | --- | --- | --- | --- |
| 1 | 40.953 | 42.817 | 176 | 2867 |
| 3 | 44.708 | 52.204 | 352 | 3171 |
| 12 | 46.424 | 50.582 | 1144 | 5282 |
| 24 | 45.360 | 51.054 | 2200 | 9354 |

Process maxRSS56,908KiB; Python tracemalloc does not measure native allocations.
Native compiled arena fixed2MiB per fixture. Isolated venv161MiB includes SDK
and dependencies; no change to caretaker's installed environment. Only MuJoCo
is pinned in the new requirements input; full transitive artifact locking and
release packaging remain required before deployment. No GPU/rendering/controller
was used. Source hashes unchanged after execution; no harness/timeout survivor.

Before16:25Z and after16:28Z AWS task1547
772d1e4f5096497e879f12a4cba2bcb4 remained RUNNING/HEALTHY, service1/1/0, image
d180f16cd50a1089365cfccd648560ab7bda14a65e2886c09c1fc93d7e5c3d93.
16:26/27 CPU average50.759/50.780%,max51.267/51.237%;memory average
4.175/4.156%,max4.181%. Earlier16:15 CPU51.482%,memory4.317%.
Clock-stalled alarm remainsALARM; CPU/memory/storage/refusal alarmsOK. This
is a read-only envelope, not a new whole-organism health or latency claim.
Caretaker PID37677 remained; no production mutation by A1.

Lean/integration disposition: no parallel body solver, retained trajectory,
worker, controller or cognition. The new module does not import the exact
reference modules. Those remain offline evidence and must not become a second
production body authority. Per-step Python geometry/limit checks and observation
copies are bounded but are not a proved minimum-cost full-body mount; quiescent
analytical advancement remains an explicit mounting obligation, not a hidden
claim of zero work. Step sampling is not continuous collision certification.
Contact dissipation/thermal transfer, metabolic supply and complete body/world
custody are NOT closed by this proof.

Next bounded item: declare reference articulated biped/hands/feet morphology
and map the existing world's actuator and receptor boundaries into this one
mechanical authority. The source map already shows functional Decision carries
named world commands, body_axes only moves head/eyes/lids, and EmbodiedBody has
no articulated state. No 'climb/open' command, prerecorded movement or fake
neuronal return may be introduced to hide those mounting gaps. Numeric body
parameters are declared engineering anatomy, never derived from cognitive age.
Full FB-01 and live delivery remain incomplete; approved work continues.

## FB-01f — Reference morphology and physical addresses

Goal resumed ACTIVE; previous status-only turn was no progress, not a verified
wait. FB-01e remains locally proven at23d097282 and is not reopened. The one
next dependency is declared reference anatomy assembled into the same native
world model. No runtime/body-state migration or cognitive output rewrite in
this candidate. Whole FB-01 acceptance remains unchanged and incomplete.

Implementation owner A1; frozen new files functional_body_anatomy.py and
test_functional_body_anatomy.py only. Contract was stated in working discussion
before implementation; this durable transcription follows source creation and
precedes independent review/any execution. This ordering is disclosed, not
represented as a pre-code ledger receipt. One failed source search used an
absent guala_body*.py glob; source symbols were found in the already recorded
files. Do not repeat that glob.

Reference: roughly1m neutral-standing biped, geometry in SI units, xforward,
yleft,zup; one unactuated free root,64 independently effort-limited hinge axes,
two arms/hands with five two-link digits including opposed thumb axis each,
two legs/feet with five independent toe axes each, trunk and head. Individual
bones, deforming flesh, muscular chemistry, growth and age-specific anatomy are
not modeled. Rigid link geometry is the sole mass/inertia source with declared
uniform virtual density1000kg/m3. Capacity is declared engineering material:
200000Pa effective actuator stress * pi*segment_radius^2 * radius/2 lever arm.
These parameters are choices of virtual material, not derived cognitive age,
claimed human muscle measurements, optimized behavior scores or strength proof.

One append_reference_biped call adds geometry, motors and sensor sites to the
caller's existing MJCF world/actuator/sensor elements. It creates no engine,
clock, physics owner, controller or alternate persistent state. It requires
caller-declared radian compiler, solver/contact configuration and world poses.
NativeBody continues to be sole dynamic authority; authoritative integration
bytes stay caller-owned. XML assembly is pre-runtime trusted anatomy, not live
world mutation. Reject duplicate anatomy before mutation. No cached history,
keyframes, equality welds, mocap, root movement servo or semantic actions.
Current state persistence/restart uses the already proved native encoding.

Physical output:64joint angle/rate/actual actuator-force channels and six
inertial sites (pelvis, head, both palms, both feet); contact geometry/forces
remain NativeBody evidence. No Boolean balance/grasp or fabricated receptor
signal. These are mechanical channels ONLY, not mounted sensory/neural return.
Required production mapping still spans actual motor output -> effort command
-> same world settlement -> Sensed/receptor input -> current-only persistence.
The current functional runtime has no general joint-effort output. Do not hide
that gap with authored motor sequences or map named intentions to choreography.

Frozen acceptance: shape count and geometry-derived inertia/capacity; unpowered
free fall and zero specific force (no hidden balance); independent digit effort
changes its real joint readings with body reaction; exact next successor after
cold restart; ground contact supplies force; duplicate assembly side-effect-free
refusal. No standalone test creates an organism or imports project fixtures.
Source-only review before execution, then decisive physical trajectory first.
Reference anatomy has no live import; no production-shaped interpretation.

Numerics: inherited authorized soft contacts/finite stepping, no new solver.
The8MiB bench arena and1ms step are declared test resources, not final release
bounds. No steady standing/walking, whole-body learning, fatigue, thermal
closure, complete integration or real-time production claim from these proofs.

Pre-review source hashes:
a6443833da7168df2d6142e37acf7f8f272fda602c02e70c19c7d032f4cb8851 anatomy
e7e555a57b87aab1ec9d4590a0a4a5a66b17657d3b5720b3442168f5aba5fd29 tests

### FB-01f source review and first physical failure

Independent review identified a localized three-axis singularity: co-located
XYZ hinges with middle pitch crossing pi/2 lose rank. Corrected hip pitch to
[-1.4,.6] and shoulder pitch to[-1.4,1.4], with explicit reduced-workspace
disclosure. An added test checks entire permitted interval plus.03rad overrun
excludes the interior singularity and checks Jacobian rank at extrema/zero.
Final source review passed. Finger response/cold continuation passed0.042s.
Full run stopped at floor support:2 passed,1error at46ms; eight proximal finger
angles -.242..-.247rad violated the -.2 lower limit by more than.03rad.
No error was hidden and no limit/expectation relaxed. Native regression did not
execute because the preceding command failed.

One diagnostic regime sequence (not source edits): stop response2/4/8/20ms at
1/.5ms steps all refuse around46–49.5ms. Stronger impedance.999 plus2/4ms
response at.25/.1/.05ms still refuses46.5–49.6ms. At2ms/.1ms, distal finger
q=-.03090rad,velocity-23.56rad/s,braking acceleration+34044rad/s². The reference
had wholly undamped tiny links: foot landing excited them. Finer timestep alone
did not resolve the declared stop requirement. No controller was introduced.

Contract amendment BEFORE passive-law source change: add explicitly selected
virtual Newtonian bearing material viscosity100Pa*s, not a measured biological
coefficient or uniquely derived value. For segment radius r, bearing ri=r/2,
ro=.55r,L=r, use analytical concentric-cylinder drag:
B=4*pi*mu*L*ri²*ro²/(ro²-ri²), torque=-B*qdot, dissipated power=B*qdot²>=0.
Ideal constitutive reduction omits fluid inertia/end effects; no new fluid
state or fluid solver. This is declared virtual-body material, no static
holding torque, no target angle, no anatomy mass duplication. Native damping
uses relative generalized velocity with reciprocal parent reactions. Its
thermal energy sink must be connected in the whole-world integration gate;
no complete thermal/metabolic claim from this model.

Diagnostic mu1/10/100Pa*s at1/.5ms:1and10 refuse46–51ms;100 admits100ms with
root heights.534926638/.534927261m. This supports only the tested material/load,
not whole-body stability or biological fidelity. Independent reviewer accepts
this as localized passive-mechanics addition, requires formula/passivity proof,
native opposing damping force and peak joint overrun at both resolutions.
Retain all prior acceptance assertions. No more threshold sweep or silent
relaxation; add one declared law, review narrow diff and run acceptance.

All diagnostics were standalone no-network processes, terminal with no children.
AWS1547 same task/image still healthy17:14Z; G1 caretaker37677 untouched.

### FB-01f final source review and local proof — 17:17Z

Reviewer classified viscous bearing addition as localized, confirmed analytic
law, reviewed amended source and passivity test, and released focused testing.
Final frozen hashes unchanged after execution:
- anatomy881c52d2fa32e4d51b87f468a2a0da69ea60bf4ab73434e170ba4d02d369923c
- tests26c48b279466b3a491ee3f99f3584e6629c2cf58fa780ff830d43ed4f3051840
- NativeBody unchanged d82a5312c264aa1602aec795d56554ffd3b5eff24332c41cb9535c005a7396f0

Ran the exact previously failing floor-contact test first:passed0.078s.
Then7 anatomy tests passed0.171s and12 unchanged native tests passed1.258s.
Standalone unittest, PYTHONDONTWRITEBYTECODE=1, isolated pinned venv, timeout45s;
no pytest, caretaker imports, live writes or cognitive fixture. Execution session
55995 exited0. Diagnostic resolution session75476 and later probes exited0.
No further assertion or stop tolerance changed.

Observed body:64 hinge effort axes,1free root,45moving rigidlinks,71qpos/70qvel,
204named sensors (joint angle/rate/effort and six3-axis inertial sites).
Geometry-derived mass11.99773211069814kg, authoritative native state5008bytes.
Engineering geometry approximately1.03m tall at nominal placement. This is a
declared roughly12kg virtual body, not a cognitive-age-to-strength prescription.

Material/refinement witness,100ms initial gravity/ground contact sampled at every
physical substep via ordinary immutable NativeBody advances:
-1ms: maximum joint overrun.010860422358rad; final root z.534926637999m.
-.5ms: maximum joint overrun.011303697735rad; final root z.534927260585m.
Both below unchanged.03rad limit. Peak difference.000443275377rad; root difference
.000000622586m. This is local resolution evidence for this trajectory, not a
global stability/convergence certificate. Neither threshold nor motion chosen
to fabricate balancing. Unpowered free fall returns zero specific force;
floor force derives from native contact; joint motor effort changes real angle,
rate and measured force; full cold next successor matches. Native damping
opposes actual velocity, dissipates rather than creates mechanical power, and
does not damp the free root. No learned motion is proved. Body reaction was not
separately asserted and is not claimed as an independent test result.

Probe process maxRSS57752KiB; state remains5008bytes.8MiB native arena is declared.
Sampling every1/.5ms incurred197/373ms walltime for100ms physical because each
sample restores/observes/encodes the complete body; this is NOT a production
performance benchmark or intended runtime call pattern. Do not import that
probe loop into production. Wholebody performance remains unqualified.

Read-only AWS envelope17:04–17:17Z: unchanged1547,task
772d1e4f5096497e879f12a4cba2bcb4,image d180f16c...5c3d93,
RUNNING/HEALTHY,service1/1/0.17:03CPUavg50.757%,max51.185%,memory4.663%;
17:15CPUavg51.787%,max53.224%,memoryavg4.679%,max4.681%. Historical clock
alarmALARM persists; CPU/memory/storage/refusal alarmsOK. No A1 productionchange.
Main-tree G1 pytest58248 completed independently; new G1python63689 under
parent760/mainworktree and caretaker37677 remain. No A1 harness child survives.

Primary implementation reference: pinned MuJoCo3.3.7 XMLreference
https://mujoco.readthedocs.io/en/3.3.7/XMLreference.html
(native geometry-derived inertia, viscous passive joint force). Bearing law
follows laminar concentric-cylinder Couette shear with declared constitutive
assumptions, not a fitted cognitive or behavioral rule.

The anatomy assembler is reachable only from its mechanical tests so far.
Not packaged, mounted, deployed or claimed as Guala's actual body. Canonical
DSF/cognition unchanged. Main world mounting must consume this anatomy once
rather than duplicate it in another body controller.

Next FB-01 boundary is the authoritative body/world transaction and its actual
motor/sensory ports, not more isolated morphology refinements. Revalidated:
lean_production_app._restore_production_actor mounts FunctionalOrganism and
FunctionalPhysicalLoop. Decision carries named commands; body_axes changes
head/eyes/lids only. Old guala_motor_world.prepare_motor_consequence reads
native recruitment evidence then produces root MoveCommand/grip/oral commands;
it is not a mounted64-joint effort producer. A new native solver cannot supply
missing cognitive motor authority. Do not silently revive the old native
organism, turn intent names into choreography, or describe generic sensors as
neural experience. Establish the smallest lawful mounting contract; disclose
any material authority gap before touching cognition. No production release
until the original FB-01 integration, restart, safety and resource gates pass.

## FB-01g — Confirmed motor/sensory authority boundary (first escalation)

Previous goal turn was progress:686c804a7 added/tested reference morphology.
This turn continues the requested full integration gate, not another helper.
A1 worktree clean at entry. Current G1 main source at62a71e2f5 was inspected
read-only; no moving G1 file changed. AWS task1547 still uses lean_production_app,
oneuvicorn worker,2048CPU/8192MiB. No production writes or test execution.

Concrete causal map, current main source:
- lean_production_app._restore_production_actor:201–266 mounts FunctionalOrganism
  plus FunctionalPhysicalLoop, not NativeResidentOrganism.
- guala_functional_organism.Sensed:381: vision/acoustic/skin fields; no limb joint
  angle/rate/effort or3-axis inertial/contact field input.
- Decision:403,decide:1773/2044,candidates:1094: action names,world commands and
  voice drive. A step constructs MoveCommand with target root pose. Grasp uses
  GraspContactCommand. No articulated effort vector or physical motor supply.
- body_axes:1480 overlays head/eyes/lids on constant anatomical declarations;
  declared shoulder/hip names are not actuated joint states.
- guala_functional_loop._advance:318–602 creates Sensed, calls decide, applies
  world command, commits world then organism, publishes result to lean actor.
  Body_consequence_count and physically_transitioned_neuron_count are both0
  in this functional reporting path.
- EmbodimentWorldAuthority.prepare_port_command:6607 dispatches existing command
  union. EmbodiedBody/_body_from:1435/2954 have no articulated primary state.
  Commit/persistence at6947/7472/7512 authenticate world state under existing
  authority. No separate body owner may be inserted alongside that custody.
- ThermallyCoupledEmbodimentWorldAuthority.prepare_port_command:630 prepares
  thermal successor against same world revision; adding mechanics must include
  measured work, supply and dissipation in that same prepared transaction.
- Old guala_motor_world.prepare_motor_consequence:212 consumes native recruitment
  evidence but translates it into root Move/grip/oral commands. It is not the
  mounted functional loop or a ready64-joint effort producer. Reinstating it
  would not supply the missing active motor-learning interface.

Source fingerprints:
functional_organism b98c1e36c9b50a966b16c283518db3e0464486f09df2023258e5cbd9eeed146a
functional_loop 8e725716d3e55757cb33745c9cad587ea66da4ebba1ba8861399d28814797424
lean_app 8131709b6ec6782533f4bd63cbbbd197be75930b4ea3210367686961be8fcef7
motor_world a9a49fe6acda630ecc6db15ce40d57c639afdb2d1e74d3e2b7b2d0ea7c680682

Live GET observation, identity1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1,
tick2247663,persisted2247654,availabletrue,checkpointerrornull:
last_occurrence.organism_kind=functional,physically_transitioned_neuron_count=0,
body_consequence_count=0,her_act=step. This supports live functional-runtime
classification, not a claim all cognition is absent. First GET selected wrong
nesting and returned no occurrence fields; inspected ActorObservation.record
then used last_occurrence. No retry/write/organism action performed.

Material boundary: preserving the existing cognitive interface literally cannot
produce generalized joint effort or consume new proprioceptive/inertial evidence.
A physics solver cannot invent either side. Translating named step/grasp into
prewritten limb motion would violate the no-script condition; silently mounting
the old neuron runtime would replace cognition and jeopardize learned continuity.
Do neither. Full FB-01 acceptance remains unachieved.

Recommended exact scope decision: authorize a bounded general somatic
motor/sensory INTERFACE extension to the current learning runtime, retaining
identity, memory and learning laws, rather than freezing its old input/action
vocabulary. Mechanical motor addresses and forces are permitted; semantic climb,
walk/open/escape routines, canned motion, reward shaping, new speech/curriculum,
or alternative cognitive owners remain prohibited. This requires an executable
interface/learning contract before code—not assurance that writing a port alone
creates learned motor control. If preserving current cognitive mechanisms also
means no such interface extension, production integration is blocked; preserve
the working organism and existing mechanics branch.

Request Joe/G1 decision on this narrow boundary. General permission for body
numerical approximation is not silently treated as permission to replace or
rewrite cognition. This is the first explicit boundary escalation after the
resumed run, not enough to mark goal blocked. No new code/migration/deploy.
Next action after ratification: freeze one complete motor output -> force/contact
-> sensory return -> same-world/body custody contract, then implement that path.
Do not create more unmounted helper components while this authority is unresolved.

## FB-01g — Joe authorizes narrow motor/sensory interface extension

2026-09-25 17:30Z. Joe's explicit instruction: "I authorize the narrow
motor/sensory interface extension". This clears the preceding scope blocker;
the goal is ACTIVE. No further approval is required for this same extension.
The reference mechanics/anatomy evidence remains closed at686c804a7; this
continues integration, not a new morphology or cognitive redesign.

Authorized boundary: extend the current organism's motor and sensory interface
with anatomical joint effort and physically measured limb/contact/inertial
feedback. Preserve identity, retained experience, existing learning laws and
canonical L0-L4. The body-only numerical approximation is already approved.
No action-name-to-gait translator, prerecorded climbing/grasping, new reward
law, replacement brain, semantic controller or speech/curriculum expansion.

Current implementation classification remains locally exercised, unmounted.
The approved body mechanics are a reduced numerical model, not full neuronal
or seven-field DSF evaluation. Authorizing ports does not demonstrate learned
coordination, balance, climbing or observational imitation.

One next contract: current organism motor output -> existing world authority's
single prepared mechanical successor -> actual contact and energetic effects
-> same-organism sensory return -> atomic paired persistence and cold restart.
The native integration bytes remain world-owned; no independent state owner,
clock or live shadow body. Anatomical identifiers name actuators/receptors,
not behavioral goals. Missing body feedback cannot be fabricated as zeros.
Old root-displacement commands may not remain an alternative movement authority
once the articulated body is mounted. Historical experience must remain intact,
but it cannot be relabeled as newly executed joint-motion experience.

Motor output and sensory input must have actual executable consumers. Merely
adding fields to Decision/Sensed is insufficient. Before edits, finish the
existing caller/migration/thermal transaction map, including the real motor
supply and dissipative heat destination. Acceptance is one copied-body ordinary
interval with applied effort, measured joint/contact/inertial return, unchanged
identity/retained memories, cold restore and the next identical successor;
then the original resource/package/live gates. No claim of production delivery
is made by this authorization record.

Read-only source check this turn located existing generic action history and
selection at _choose/commit, and the auditory-specific sensorimotor mesh import
at dsf_ai_service/substrate/guala_sensorimotor_mesh.py. An attempted display of
dsf_ai_service/guala_sensorimotor_mesh.py failed (wrong directory); do not retry
that path. No mesh extension or learning-law alteration is authorized by this
record. Source is not frozen for implementation until the complete boundary
contract is settled; no tests, production writes or process control this turn.

## FB-01g — Executable interface and custody source map, 2026-09-25 17:42Z

This continuation completes new source analysis; it does not repeat the scope
request. Joe's authorization remains effective. Independent read-only review by
body_force_review agrees that anatomical motor vocabulary can use the current
learner without a new selection/reward equation. No source candidate or test
was run this block. The full body delivery remains ACTIVE and incomplete.

### Concrete motor/feedback connection

1. Each distinguishable anatomical effort needs its own action identity.
   decide deduplicates options by option[0]; putting every effort under one
   `motor` label would silently alias different joints and their experience.
   Use a mechanical address plus signed effort, never a semantic climb/open/
   escape label. The existing _choose, pending_act, _settle and _credit path
   accepts arbitrary action identifiers; its equations need not be rewritten.
   Preserve the successful identifier in applied_action: commit currently
   treats `body` as passive time and excludes it from motor-transition trials.
2. The world motor contract must accept a full bounded effort vector in native
   actuator order. Do not restrict the physical interface to single-joint
   motion. The review's minimal signed-capacity candidates are sufficient to
   prove individual action availability, but alone do not supply simultaneous
   recruitment or prove locomotion. Do not freeze that narrower candidate set
   as satisfaction of the functional-biped objective. No canned coordinated
   vectors, gait library or hidden posture servo may fill the gap.
3. Afferent evidence is the actual native joint angle/rate/effort and site-frame
   specific force/angular rate, plus locality-resolved contact points/wrenches.
   Native MechanicalObservation also contains whole-model qpos/qvel and geom
   IDs. These are world diagnostic/custody evidence, NOT organism senses.
   Passing that object wholesale would expose other objects' hidden state.
   Project only self-body receptors; preserve contact sign and local frame,
   and exclude external simulator identity from sensory recognition authority.
4. Actual somatic predecessor/successor evidence must accompany the performed
   motor trial. It cannot be synthesized from the requested command. Missing
   receptors are unavailable, not zero. The native mechanical state is the
   source of body axes and inertial evidence; static BODY_AXES is not a second
   pose authority after mounting.

### Memory and input-domain continuity

The reviewer found a concrete migration deletion hazard: migrate() compares
stored regimes through choice_key and deletes acts entries when their key
differs. Before appending channels, retain today's entire STREAMS tuple as a
recognized historical schema in _streams_for. Initialize only new windows
empty; preserve old history and records byte-for-byte. Do not relabel root-step
experience as joint practice. Preserve CONSOLIDATED_STREAMS and sleep equations;
their existing coarse consolidation does not retain all posture distinctions.

Adding body channels to decision context changes which sensed situations match,
and hence the existing novelty/uncertainty/exploration response, even without
changing any learning equation. This is an explicit effect of the authorized
sensory-interface extension, not evidence that learning is unchanged in output.
Keeping all body channels out of context would instead leave the learner blind
to posture; transport alone is not an acceptable integration claim.

Further source check: uf_core/layer0.py:97–146 uses log(F_raw+1e-8).
Raw signed angular rates, forces or accelerations cannot simply be appended to
the present positive-input streams. Do not take absolute value (loses direction)
or guess an offset/clip range. A lossless candidate adapter is a signed pair,
F+=(max(x,0)/u), F-=(max(-x,0)/u), retaining the original SI sample and its
declared unit u, with the existing positive stream floor applied only at the
kernel input. x=u(F+-F-) establishes its information boundary. This is a
candidate input-coordinate mapping, not a biological receptor law or a change
to L0-L4. Its channel cost and actual caller must be checked before adoption.
Current per-stream regime/sign projection remains reduced cognition; do not
claim full joint DSF/neuron delivery. No new scalar body/balance score.

### World, thermal and persistence ownership

Existing prepare_port_command validates the opaque command, runs _transition,
constructs the single _AuthorityState candidate and signs its observation.
commit_prepared_action publishes that candidate. Its rollback transaction
restores _prior_state. Native integration bytes must therefore belong to the
same world's canonical state and predecessor/successor, not an attribute held
only on a Python adapter. The native MjData remains reusable scratch.

ThermallyCoupledEmbodimentWorldAuthority already stages _PendingThermal under
thermal-lock -> world-lock order; discard, commit and rollback share the world
candidate. Mechanical supply/work/heat must join that same transaction. Do not
commit motion and later mutate reserves/temperature as a second authority.
FunctionalPhysicalLoop currently commits world before organism.commit and
relies on PhysicalSettlementFailure + paired-checkpoint recovery. The new
candidate must prepare all fallible body/thermal/organism outputs before
publication, retaining the existing actor's one paired checkpoint path.

The current world validates every body as a floor disc and every held object
as a reciprocal one-object relation. Do not bypass these checks and call it
articulation. Mounted mechanics must replace the corresponding movement/contact
authority, with native root/object poses being the sole source of legacy UI
projections. Old Move/Grasp/Release placement cannot secretly act alongside
native contact. This includes caregiver transport and world mutations, not
just Guala's own step command. The old source remains live until safe cutover.

Camera consequence is also on this causal path: w1_physical_receptors currently
uses a fixed receptor offset plus root yaw and separate head yaw/pitch. A tilted
native head cannot truthfully return the old upright view. The new receptor
origin/basis must come from actual head mechanics. This is body-frame mounting,
not authority to redesign vision, increase pixel counts, or alter learning.

### Energy contract: reuse existing units, do not fabricate heat

embodiment_world.py:832 declares nutrition extraction density 1.7e19 zJ/ug,
equivalent to 17,000 uJ/ug = 0.017 J/ug. Reuse this conversion rather than a
new stamina reservoir. Existing integer reserve and any sub-microgram work
remainder must represent one supply, never two independently spendable stores.
For mounted joint effort, replace action-name effort burn with measured motor
work while preserving the separately declared basal cost; do not charge both
the old movement multiplier and physical work. Refusal cannot debit unperformed
work. Negative mechanical motor work is not automatically food replenishment.

Bearing dissipation is measurable from the already-declared law B*qdot^2.
The native work quadrature currently reports only positive and signed motor
work. Do not call signed work, positive work, energy error and thermal heat the
same quantity. In particular, MuJoCo3.3.7 mj_energyPos accounts for gravity and
joint/tendon/flex springs, not a retained soft-contact elastic-energy state.
Thus W_motor - delta(K+U) cannot simply be poured into a thermal node as exact
contact heat. Contact work, passive dissipation, braking and numerical residual
need explicit separation/error treatment at this boundary. This is necessary
body-energy integration, not permission to invent heat or rewrite neuron physics.

Primary implementation evidence for this last distinction:
https://github.com/google-deepmind/mujoco/blob/3.3.7/src/engine/engine_sensor.c
(mj_energyPos/mj_energyVel). The pinned documentation URL was unavailable via
the web reader; the pinned official source was inspected read-only instead.

### Acceptance / next implementation boundary

The full acceptance stays: same authenticated copied organism; a genuine motor
selection -> one native world interval -> actual body/object consequence ->
local self-body feedback consumed by that organism -> retained motor trial ->
paired save/cold restore -> identical next successor, under bounded resources.
Severing effort must remove its force contribution without removing gravity or
contact; severing feedback must not pass as sensed movement. Historical memory
must survive channel migration. Passive/sleep intervals still obey mechanics.
No deployment before the original mature-body, restart and live safety gates.

Next implementation contract must resolve simultaneous effort representation,
signed channel admission and the mechanical-to-thermal work split together;
these are now exact source boundaries, not renewed permission questions. Do
not run old passing anatomy suites or add more disconnected mechanical helpers.

Source fingerprints at this mapping:
- functional_organism b98c1e36c9b50a966b16c283518db3e0464486f09df2023258e5cbd9eeed146a
- functional_loop 8e725716d3e55757cb33745c9cad587ea66da4ebba1ba8861399d28814797424
- embodiment_world c9534a4c30fe6b9dc66b2aebd5751906d78a64697777ff99b1f2ae5b3bbe80ac
- thermally_coupled_world b048c39e50030e4f22f04a122b7d976d8b769c24d82a2323d3080d5514fb968b
- functional_body_native d82a5312c264aa1602aec795d56554ffd3b5eff24332c41cb9535c005a7396f0

One read command incorrectly included uf_core/sev.py; actual import points to
uf_core/layer0.py and that source was read. No source file, process or production
state was changed by the read failure. Do not repeat the guessed path.

### FB-01g native interface candidate — 2026-09-25 (awaiting source review)

This is implementation progress toward the authorized interface, not mounted
organism integration or a production candidate. Changes stay in the existing
native adapter and its standalone proof, with no new solver, state owner,
reservoir, decision equation, or cognitive authority.

- Full-vector effort remains supported. Sparse anatomical updates change
  distinct components of native ctrl, already retained in mjSTATE_INTEGRATION;
  None explicitly holds that vector. Explicit zero releases a component.
  Thus sequential anatomical inputs can coexist without authored coordination
  arrays or an exponential action catalogue. This zero-order hold is a declared
  mechanical input approximation, not muscle physiology or an automatic posture
  controller. Existing caller must explicitly release effort for sleep/depletion;
  its integration remains pending. No isometric metabolic cost is claimed.
- Only the declared self-body subtree contributes joint angle/rate, actual
  effort and site-frame IMU channels. Contact point, force and couple return in
  each contacted link's own axes with the correct opposing-side sign. External
  object identities, global frame sensors and whole-world qpos remain diagnostic
  only. No self-body declaration means absent feedback, not fabricated zeros.
- Positive/signed motor work, motor braking and viscous bearing dissipation
  are separate trapezoidal power quadratures. The unresolved energy exchange
  is reported separately: native energy omits retained soft-contact elasticity,
  so the remainder is NOT asserted to be heat or a pure numerical error.
  No reserve debit or thermal-state mutation is implemented by this adapter.
  The existing world/thermal transaction remains the sole intended mount.
- Model binding now includes sensory-root declaration. These native snapshots
  are offline only; no live predecessor uses this adapter. Same candidate
  model/root restores identically; prior native bench states require regeneration,
  not a silent runtime fallback.
- Static sensor membership is compiled once. Native state extent and sole
  physics clock are unchanged. Per-step new work is motor/bearing power
  quadrature; local sensory projection occurs only on observation.

Frozen source:
native 4b3cba586627d42c434182bc581b03eaff6d9322576400499b7dddb2698ef8b6
test df5f453031c4d44afb7bc52068b8a5dec5096cccfd92cd389f4f009a56ceaa6e

Named checks: incremental/full-vector equivalence, simultaneous effort after
fresh-engine restore, explicit release, bounded/refused command immutability,
no unobserved-object/global-pose leakage, rotated contact-frame sign, separate
bearing/braking work and numerical refinement on an isolated viscous joint.
Existing native mechanics and anatomical regression tests protect their direct
caller against changed return/state semantics. No pytest or production actions.
Independent source-only review precedes execution.

Still required: actual world/thermal transaction mount, old movement authority
replacement, learner motor vocabulary and signed sensory inputs with memory
migration, head receptor frame, copied-body full-loop proof and production gates.
These tests cannot close those requirements.

### FB-01g native interface verification — 2026-09-25 17:57Z

Independent source review found one localized afference leak: inactive native
margin/gap proximity contacts were projected as touch. Corrected in one batch:
diagnostics retain them, but self-body tactile return excludes efc_address<0
and exactly zero six-component wrenches. No pressure threshold added. Added
inactive-gap falsifier and equal/opposite geom1/geom2 contact proofs.

Verified standalone, not pytest and not a live world:
- native mechanics/interface: 19 passed in 1.533s; process elapsed1.776s,
  peak RSS58,212KiB, user3.245s/system0.133s; PID74868 exited.
- anatomy regressions: 7 passed in0.175s; process elapsed0.348s,
  peak RSS59,040KiB, user1.958s/system0.024s; PID74977 exited.
- Existing anatomy test/source unchanged. git diff --check clean.
- No A1 harness survives. G1-owned pytest74602 (parent760) and caretaker37677
  remain untouched. These short shared-host checks are not production latency
  or long-run resource certification.
- /usr/bin/time is absent (preflight caught this before invocation). Use the
  retained session handle and resource.getrusage for these standalone processes;
  do not retry the absent executable.

Read-only AWS before/after: task1547 unchanged; desired/running/pending1/1/0.
Identity1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1; live tick2249167->2249341,
persisted2249158->2249318; availabletrue, checkpoint/cleanup errorsnull,
durability_blockedfalse. Five-minute CPU samples ~51–52.4% average/<54% peak,
memory4.76–4.785%; overlapping reporting windows are not causal performance
measurements. Historical guala-clock-stalled alarm remainsALARM sinceSep8;
resource/refusal alarmsOK. No production write, restart or deployment.

Verified candidate fingerprints:
native 0a331541db25d5dbbc604c9d19e4a224b7607d5c1be99febdc95cf8974865f78
test 7db78acaedad3ad4e4d083ab2dd2e009004780d7229d91ee03b5d29a83fd59e5

This closes only the native input/local-feedback/work-reporting seam. It does
not close world mounting, energetic transaction, memory-safe learner connection,
actual head optics, copied-body proof or production delivery. Goal ACTIVE.

### FB-01g existing-reserve integration — 2026-09-25 18:11Z

Previous turn was concrete progress (1683d4ff7). This turn implements the
chemical-energy preparation boundary in the existing FunctionalOrganism, not
another stamina pool. Whole-world native mounting is still incomplete.

Requested architecture: native positive work spends the existing reserve,
prepared before the world's successor is published. Current source now has
BodyEnergyTransition, available_motor_work_j and prepare_body_energy. commit
accepts the prepared successor and preserves fractional expenditure. Conflict
remaining: ordinary world/loop still uses root commands and does not call this
interface yet. No kernel, new reward, native-brain revival or scripted motor
sequence is added. This is body-only numerical/chemical accounting; existing
reduced functional cognition remains reduced, not full-field neuronal delivery.

Law and scope:
- Reuse digestion's17,000,000nJ/ug. E=reserve_ug*unit-spent_nJ, with
  0<=spent<unit; reserve_ug is the ceiling projection, not another energy stock.
- Available native work excludes min(E,3ug*unit) basal consumption and future
  intake. Binary64 supply rounds downward. Numerical positive work rounds
  upward to whole nJ (less than1nJ excess debit per interval).
- Prepared successor satisfies E_after=E_before-basal-positive_work+intake*unit.
  Negative motor work/braking never regenerates food; bearing heat is not
  charged a second time. This is an ideal mechanical supply conversion, not
  human muscle efficiency/isometric metabolism.
- Body-energy publication verifies current tick, reserve and actual intake.
  Once activated, omission of measured energy fails closed instead of silently
  restoring named-action effort costs. Old bodies retain old encoding/costs
  until explicit cutover; no default new field is inserted by migration.
- The existing learning cost/capacity equation gets measured nJ cost, with no
  new shaping coefficient. Existing learner rounding and contextual reduction
  remain; this is not proof of learned control. Pending legacy costs are unit-
  converted, not fabricated into new joint trials.
- Independent source review caught pending-cost conversion after mutation.
  One localized correction validates new retained costs at restore and computes
  accumulated cost before mutation. Invalid-cost refusal now preserves bytes.

Standalone test_functional_body_energy.py:8/8 passed in0.083s
(processelapsed0.569s, peakRSS133,264KiB, user2.147s/system0.094s).
Uses actual native mechanics and actual FunctionalOrganism commit/restore;
controlled bench effort is not autonomous choice. No world genesis, pytest,
network calls, production replay or field-learning claim. TestPID78958 exited.
System Python provides pandas3.0.5; isolated native site-packages supplies pinned
MuJoCo3.3.7/numpy2.4.6. No package installation or shared environment mutation.

Before/after readonly AWS: task1547, desired/running/pending1/1/0;
identityunchanged; live2249919->2250042, persisted2249894->2250022,
availabletrue, no checkpoint/cleanup error or durabilityblock. CPU~50.76%,
memory~4.79%; CloudWatch window lag means these are envelope observations, not
local-test causality or end-to-end latency proof. Caretaker37677 untouched.

Joe reports G1's reach_hand/toward_person/toward_door caregiver following work.
Current main has uncommitted organism/episodic/caretaker changes and is10commits
ahead of origin; A1 does not overwrite or cherry-pick across that moving lane.
The integration must preserve history but retire root-displacement authority at
the articulated cutover, not compile semantic affordances into a scripted gait.
Reconcile G1's actual final source before release. No extra approval requested.

Source d5e028aa4e28b26664f6552328dca66e964690219a1319b91088d2f3c43881c4
Test d91d119fc8a2663971aa3d01c329362b2d36023c14364e25ee6bb4934e6a4b7a
Full objective remainsACTIVE. Next: existing world/thermal prepare/commit mount,
with native state canonical custody, actual root/head/object projection and
no competing old movement/contact authority. No production delivery claimed.

### FB-01g G1 following compatibility boundary — 2026-09-25 18:22Z

Joe's FYI does not pause or widen this sprint. Source-only coordination completed;
no production, caretaker, learning, or mechanical source was changed this turn.
G1's main tree remains moving and dirty on HEAD62a71e2f5, not a reviewed release.
Observed organism hash6bd5bd0ad0926c7648e0610419a02b80822051bee36fd8011e207722d4ad96a9.

Exact candidate producers in current main guala_functional_organism.py:
- candidates:1218 toward_person calls move_commands_toward with the sensed
  person's position. It requests a root pose; it does not issue joint effort.
- candidates:1220-1224 reach_hand emits BodySurfaceContactCommand for declared
  palm sites. It is a contact/compression request, NOT a locomotion command.
- candidates:1237-1239 toward_door calls door_crossing_commands or
  move_commands_toward. The source does not by itself establish that Guala
  infers or follows a caregiver heading vector across rooms.

Cutover consequence: these requests cannot remain independent position/contact
authorities beside articulated mechanics, and their historical successful trials
cannot be relabeled as experienced anatomical effort trials. Preserve histories;
do not synthesize a gait, interpret an external heading as proprioception, or
claim palm contact unless the mounted body actually reaches the other surface.
G1 may continue the present runtime; this is a release compatibility boundary,
not a request to stop or rewrite his lane.

Main's current uncommitted organism diff also changes moment capacity8192->128,
motor-trial admission, gaze retention and action scoring. Those are separate
from following and from A1's approved body-only interface. They are not adopted,
reverted, or certified here. Require G1's final immutable revision for the merge;
do not wholesale-replace his file with A1's older baseline.

World-mount source boundary reconfirmed without reopening native mechanics:
_WorldState and its canonical decoder contain floor-disc bodies/objects only;
_validate_world requires floor-level positions; root/held-object commands
publish through prepare_port_command. The thermal subclass already stages its
successor over that same prepared world. Native integration state belongs in
this canonical transaction, not an adapter-side retained body. Home objects
currently have masses and visual parts but no authored anchoring/joint model;
optics currently supports yaw/pitch, not the native head's full orientation.
These are the remaining mount interfaces, not evidence that mounting is done.
No test or harness was started, and no deployment claim is made. GoalACTIVE.

### FB-01g current-world custody candidate — 2026-09-25, in progress

Continuing the same world-mount item, not reopening the native mechanics or
existing-reserve proofs. Parent owns native world-frame projection, thermal
transaction wrapper and standalone tests. body_force_review owns only
embodiment_world.py. No candidate tests/imports/compilation before the owner
finishes and one source-only frozen review passes. Production is untouched.

Implementation contract for this offline custody boundary:
- Existing EmbodimentWorldAuthority remains sole publisher. _WorldState holds
  one immutable model declaration and current native integration bytes. Native
  solver scratch is not a second retained body. Historical observations carry
  signed model/state digests, rigid transforms and local feedback, not another
  integration-state copy. Restore regenerates current evidence from real bytes;
  historical observations are not decoded into fabricated native worlds.
- NativeWorldMount binds every declared body/object to a named native body and
  binds actuators to their physical body. In this first bench all driven motors
  belong to self; other participants are explicitly fixed/passive. Aggregate
  motor work must not debit Guala for another participant. This does NOT yet
  simulate caregiver articulation or convert the live home geometry.
- AnatomicalEffortCommand carries addressed efforts and an elapsed interval.
  NativeBody advances caller-owned bytes once, returns actual local joint,
  inertial and contact evidence, measured work, and full world rigid transforms.
  WorldFrame maps local points as position+rotation@point; it is world/optical
  geometry, never an omniscient sensory channel. No yaw-only reconstruction.
- All fallible native settlement, projection, validation, receipt and capacity
  work precedes publication. Failed preparation or discard leaves the exact
  predecessor bytes. Existing committed rollback restores those same bytes.
  Fresh restore must reproduce the next actual effort successor byte-for-byte.
- Legacy root movement, held-object teleportation, prescribed surface contact
  and authored body transport cannot independently mutate a mounted native body.
  Retained historical learning is not reclassified as learned joint effort.
- Zero-time mount stages under the existing thermal-then-world lock order,
  preserves temperatures and fractional heat, and retires only the obsolete
  latest transition receipt. Rollback restores the prior receipt and state.
  Timed native settlement on the thermal wrapper is explicitly UNAVAILABLE
  until motor/bearing/contact dissipation has a physical node mapping. Neither
  numerical residual nor unspecified losses may be relabeled skin heat. This
  guard means the candidate is not production-releasable.

Acceptance/evidence map (all backend-only, not UI/live evidence):
1. Actual native xpos/xmat -> immutable WorldFrame -> world observation/receipt
   -> current encoded custody -> fresh observation and equal next successor.
2. Actual joint effort/rate and site signals -> BodyFeedback -> signed native
   observation. No external identity/global frame injected into self feedback.
3. Prepared native state/work -> existing prepared capability -> atomic publish
   or discard/rollback. No current-state mutation during preparation.
4. Prior thermal transition -> zero-time mount -> unchanged heat/new world
   receipt -> exact rollback and fresh authority restoration.
Learner integration, head optics consumer, timed thermal work, actual home and
caregiver conversion, mature copied-body proof and live delivery remain OPEN.

Named source-only tests authored (not run): two native rigid-frame tests and
seven tests in test_functional_body_world.py. The latter use the real biped and
authority with explicitly declared zero-gravity bench, fixed external entities
and a five-node thermal bench. They do not prove home collisions, autonomous
motion, food supply, full field cognition or production safety. Tests cover
first installation and retained/rollback/fresh-cold continuation branches.

Pre-execution correction/recurrence record:
- Parent's text assembly malformed the thermal mount method declaration and
  placed a duplicate port-command header ahead of it. Source diff caught this
  before any import/test. Rebuilt the complete file with explicit method
  boundaries and inspected the resulting declaration/lock/guard ordering.
- apply_patch rejected delete+add of one path in one patch; no edit occurred.
  Full-file Update is the supported replacement form; do not repeat that form.
- Guessed existing thermal test filename and test glob were absent. Do not
  repeat those guesses; the declared standalone test is now the exact target.
- Renamed the insufficient-work test so its title does not claim a future-food
  experiment it does not execute. Future-intake exclusion remains covered by
  the already closed existing-reserve energy tests, not this world bench.

No unit-suite counts, production identity, steady-state resource or delivery
claims follow from this unexecuted source. Goal remains ACTIVE.

### FB-01g mount contract correction — source review, before execution

Rejected the first mount candidate before import/compile/test. Exact rejected
diff (including the new test) is retained in
GUALA_FUNCTIONAL_BODY_MOUNT_REJECTED_2026-09-25.patch; all five executable/test
files were restored to their accepted HEAD before beginning the corrected
candidate. This is A1-owned work only; no G1 or production file was reverted.

Architectural failure: public mounted-to-unmounted restore correctly refuses
silent reversion to floor-disc mechanics. The thermal decoder previously used
that same public restore to undo an inner-world success followed by outer
thermal rejection. A fresh-authority restore could therefore retain half of a
rejected pair. The corrected contract performs ONE rollback at the outermost
thermal/world lock boundary, restoring the exact immutable predecessor world,
recorded declaration, thermal state/residue, revision/receipt, latest transition,
physical return and pending/committed thermal references. No decoding or
re-encoding is needed to undo a rejected private transaction. Native engine
scratch is not custody; subsequent native calls restore authoritative bytes.
The inner decoder no longer recursively invokes public restore for rollback.

Localized source findings included a malformed constructor insertion in the
world file (before any import) and a bench other-body orientation that did not
preserve its actual predecessor yaw. Correct the constructor layout and give
the bench body its existing pi yaw; do not relax pose preservation. Add the
decisive fresh-authority failure falsifier: authenticated mounted inner world,
mismatched outer thermal revision -> rejection -> exact predecessor encoding
and next lawful unmounted interval. Recheck both ordinary and mounted cold
restore. Existing chemical/sensory physics and timed thermal unavailability
are unchanged. Parent now owns the complete corrected candidate; prior owner
has stopped editing. No production health or completion claim.

Corrected source freeze (manual exact hashes; fingerprint script remains
unavailable as previously recorded). Independent source-only review assigned
to mount_custody_review; parent will not edit these files during review:
world 7c323c1b430896007f33763dbba98575d051c47bb881f4ca7ccef8aa5b9f1aec
thermal 9ec9464cbc6ebd9d269fb2e3583741ff0c7537437e53651fb0dad206b0f68e35
native 1034f386e7f180051ee132504c5c5007d1714b683c9ea2a71ed51208ac1b96b5
native-test 2a6e77106880821d3c925f156dd2a655cf0ccb0431ca4275d950d39d1c8f0bda
world-test b762ad46a5a0f12dea2ffa9e3f180646f9152fd27bd88433f05c22d03860a1ed

Readonly pre-execution envelope at18:50Z: actual service dsf-ai-service-lb in
tfe-web-cluster/us-east-1, desired/running/pending1/1/0, task1547 and running
task772d1e4f5096497e879f12a4cba2bcb4. Observer identity unchanged,
live2251921/persisted2251910, availabletrue, checkpoint/cleanupnull and
durability_blockedfalse. CPU five-minute averages51.44/51.84%, RAM4.69%; old
clock-stalled alarm remainsALARM sinceSep8, resource/refusal alarmsOK. This is
an operational envelope, not a body integration or benchmark result.
Preflight mistake: omitted -lb from service name, yielding no described service
and ServiceNotFound on task listing. Resolved using readonly list-services;
record exact dsf-ai-service-lb for later envelopes, never retry guessed name.
No test or native import has run on this candidate yet.

### FB-01g offline world custody verified — 2026-09-25 18:54Z

Independent source-only review passed the corrected frozen candidate with no
blocking findings; all five hashes matched before/after review and execution.
The reviewer did not import, test, edit or touch production.

Focused standalone checks (no pytest/conftest, no live requests from tests):
- test_functional_body_world.py:8/8 passed in0.506s. Whole process1.128s,
  peakRSS143,852KiB, user1.065s/system0.080s; PID89226 exited.
- Native frame/mechanics plus unchanged anatomy/energy consumers:36/36 passed
  in2.233s. Whole process2.632s, peakRSS142,800KiB,
  user2.610s/system0.036s; PID89327 exited.
- Source imported from this worktree using systemPython and pinned existing
  MuJoCo3.3.7 environment, bytecode writes disabled, numerical thread count1.
  No package install, new daemon, production-body import or network test call.
- Process census after both checks shows no A1 harness survivor; G1 caretaker
  PID37677(parent760) remains unchanged. git diff --check passes.

This closes OFFLINE native state custody/transaction/cold continuation only:
real articulated effort -> existing world prepare -> immutable fullframe/local
feedback/work receipt -> commit -> cold restore -> equal next native successor.
Failed preparation/discard/committed rollback and failed coupled restore preserve
the exact predecessor. The additional test verifies the corrected fresh-restore
failure and its next normal interval, not merely a dictionary comparison.

Readonly AWS after: same task1547/772d1e4f5096497e879f12a4cba2bcb4,
RUNNING/HEALTHY, desired/running/pending1/1/0; digest
d180f16cd50a1089365cfccd648560ab7bda14a65e2886c09c1fc93d7e5c3d93.
Observer identity unchanged; live2251921->2252078 and
persisted2251910->2252070, availabletrue, errorsnull, durability_blockedfalse.
CPU reporting-window average51.33%, RAM4.699%; old clock-stalledALARM remains
separate from current advancing ticks. Shared-host short-test timing is NOT
production body latency or long-run compute certification.

Remaining required next boundary: physically located native dissipation in the
existing thermal transaction (timed mounted thermal calls currently refuse).
Actual home/caregiver conversion, learner effector and signed feedback interface,
head optics, copied mature body, packaging, restart and live acceptance remain
open. No production delivery, autonomous following, gait or climbing is claimed.
G1's affordance/curriculum work is untouched. Full goal remains ACTIVE.

### FB-01h measured internal heat coupling — contract, 2026-09-25

Previous turn is PROGRESS:3bb09d322 closes offline world custody, not delivery.
Single next item: permit timed articulated settlement to feed measured internal
work into the existing thermal circuit without another heat store or energy
source. Preserve current body state, chemical reserve law, L0-L4 and cognition.
Main/G1 ledger has no new entry beyond the A1 custody handoff at this check.

Source facts: current native work includes global bearing losses, whereas a
passive external object may also have damping; those losses must not heat Guala.
The existing home core has a fixed41.5W power source, independent of the current
organism's3ug-per-interval chemical debit. In articulated mode this source must
receive the actual basal debit plus measured self bearing/braking heat instead
of also injecting its fixed value. Existing body thermal mass/core/skin stores
remain intact. Neither mechanical residual nor positive motor work is heat.

Frozen intended causal contract (source edits not yet tested):
- NativeBody partitions bearing power by actual dof_bodyid descendant membership
  of the mounted self root. Integrate the same B*qdot^2 trapezoidal rule during
  existing substeps. Keep total bearing and residual diagnostics; expose exact
  measured self_bearing_dissipation_j separately (None with no declared self).
  All mounted actuators already belong to self, so existing motor braking is
  self-owned. Solver, controls, integration bytes and cognitive inputs unchanged.
- NativeMechanicalWork transports this field in its signed work receipt. No
  guessed heat ownership, actuator name parsing or second reserve.
- Existing bounded thermal source transfer accepts optional per-source measured
  energy (integer nJ), replacing power*elapsed_time for that interval. Keep its
  existing fixed-denominator residue and thermal state: nJ*1000 enters the
  numerator whose denominator is1,000,000 per microjoule. No new retained
  accumulator. Unsupplied sources keep their declared physical power.
- In mounted mode require exactly one existing power source at the core node;
  replace that source input with basal_debit_nJ+round((self_bearing+braking)*1e9).
  The latter is body-only numerical quadrature with at most0.5nJ rounding error per
  interval; basal debit is integer exact. Caller must supply the actually
  prepared existing-reserve basal debit; missing input fails before preparation.
  No fallback to the fixed heater after a mount. External power sources unchanged.
- Keep heat in the existing core/skin bulk approximation: heat is internally
  generated in Guala, not on a touched surface. Joint-local temperature gradients
  are not represented by this two-node model; do not claim they are. Contact
  friction/constraint losses and object/body thermal contact still need their
  own physically located law. Report unresolved mechanical exchange; NEVER
  relabel its residual or spring work as heat. This step is not that contact law.
- Native thermal receipts explicitly separate basal input and measured internal
  dissipation; both already enter powered-node transfers, never add them again
  to conservation totals. Current thermal state encoding needs no added stock.
- Full existing prepare/commit/discard/rollback/fresh restore boundary applies.
  All conversion, source validation and heat preparation precede publication.
  Cold-restored source residues and next interval must match exactly.

Ownership: body_force_review owns only native adapter, world work projection and
native tests. Parent owns bounded thermal transfer, coupled wrapper and focused
thermal tests. No review until both owners freeze. No production/caretaker work.
Acceptance: actual native joint work + actual FunctionalOrganism basal/work
preparation -> existing thermal source replacement -> exact heat/residue and
reserve successor -> cold next interval. Falsify missing basal, external-bearing
attribution, fixed-heater double count, positive-work double count, thermal
overflow, discard/rollback and paired restore. These remain offline until the
full ordinary learner/world call path and production gates are completed.

Reference boundary: MuJoCo3.3.7 computation/modeling docs distinguish soft
constraint behavior from exact hard contact; no documented native total-energy
residual is a localized heat observable. Consulted official docs only:
https://mujoco.readthedocs.io/en/3.3.7/computation/index.html
https://mujoco.readthedocs.io/en/3.3.7/modeling.html#solver-parameters
Read-only glob mistake: substrate/home* does not exist in this worktree; actual
home thermal anatomy is in guala_home_world.py:1220 onward. Do not retry the glob.

### FB-01h candidate frozen for source-only review — 2026-09-25

Acceptance-evidence map (all backend/offline-only):
native actual body-descendant DOFs -> same substep B*qdot^2 quadrature ->
MechanicalSuccessor.self_bearing_dissipation_j -> NativeMechanicalWork ->
signed native execution v2 -> existing coupled thermal source override ->
existing core energy/power residue -> signed thermal transition v3 ->
coupled current-state encoding -> fresh authority restore -> equal next interval.
FunctionalOrganism existing prepare_body_energy supplies basal input and measured
positive-work debit; no new organism memory, energy reservoir or learning law.
The ordinary production FunctionalLoop caller is not mounted yet. This test does
not prove its outer organism/world publication path or UI/receptor delivery.

Source-only changes:4 focused native tests and4 heat/cold/rollback/source tests
added; prior8 custody tests retained, obsolete blanket heat-refusal assertion now
checks actual missing basal input refusal. Existing constant-power default has
an exact equality test; source residue has explicit subquantum accumulation.
Caller-provided efforts are test interventions, not learned behavior. Full
reference biped tested in a fixed offline bench, not the lived home.

First-use and recurrence branches: unmounted legacy state unchanged; explicit
zero-time native mount preserves thermal stocks; timed effort prepares heat
before publication; discard/error/rollback preserve predecessor; cold restored
native work and heat then produce the same next braking interval. Source bounds
and overflow fail before publication. External damped-body exclusion tested
separately at the native ownership boundary. No residual-to-heat conversion.

Lean closure: no new retained accumulator, anatomy, source scan per interval,
solver invocation, cognitive selector, process, daemon or network writer.
Core-source indices compile once with immutable thermal anatomy. Existing
per-source residue carries nJ remainder. New thermal receipt fields are evidence
of distinct admitted input, never additional energy. Native current-state bytes
unchanged by self-dissipation reporting. Contact friction/conduction remains
unimplemented in this slice and blocks any whole-body thermal-completion claim.

Frozen source hashes:
- functional_body_native.py d132e5d1a04765f2201a4be8f6ee48b3ddd7def53a0ef7a8c0bcef77c0ae36ed
- embodiment_world.py 022c835038b2d226d304d1f495f616c29b2968dd68e4f243eaaccb9026932b62
- bounded_home_thermal_physics.py fb2a975f9fa3d26b79ce23324edd6586d36457ccf718945944a41aa813f4e03d
- thermally_coupled_embodiment_world.py abc37a278483b860dda0b8c1c99b8990ccf3ef4e7a711d454d388a65e8a34832
- test_functional_body_native.py 66986ad905b4dd9c514634ae87415f971ad0203689f61f5ed02ab3006661595f
- test_functional_body_world.py dfd1d8ae96a41e8b5c37f97520a5e49e45fe887a2812ad6b4799a8bfe2996476

No tests/imports/compile run on this candidate. Both implementation owners stopped.
Known absent fingerprint script not retried; explicit file hashes and clean diff
used as previously recorded. Remaining ordinary-loop/caregiver/home integration,
copied-body, resource and production gates remain open; goal ACTIVE.

### FB-01h offline measured-heat proof — 2026-09-25 19:12Z

Independent source-only review passed with no architectural or localized blocking
findings. All six frozen source hashes matched before and after review and tests.
No implementation edits were needed after freeze.

- Focused native world+heat tests12/12 passed in0.861s; full standalone process
  1.805s, peakRSS144632KiB, user1.729s/system0.084s, PID94706 exited.
- Native/anatomy/energy regressions40/40 passed in1.767s; process2.159s,
  peakRSS143808KiB, user2.120s/system0.056s, PID94805 exited.
- SystemPython with existing pinnedMuJoCo3.3.7, numerical threads1 and bytecode
  writes disabled. No pytest/conftest, package install, production body or network
  call in either harness. Postrun census has no A1 test survivor.
- Both first-use and retained next braking interval physically exercised. Actual
  native work feeds actual reserve preparation and measured internal heat replaces
  fixed power exactly through existing subquantum residues. Positive work is not
  also deposited as heat. External passive bearings stay external.
- Error, discarded prepare, hidden committed rollback and failed fresh restore
  retain prior body/thermal custody. Default unmounted thermal law unchanged.
- These tests are offline causal component evidence only: external effort input,
  fixed bench surroundings, existing bulk core/skin thermal approximation.

Read-only AWS pre/post envelope differed from prior turn because G1's release
operator PID93278 was actively cutting over. At19:09 and19:11 service definition
1547 had desired/running/pending0/0/0; no service task; observationHTTP503.
Old task772d1e4f5096497e879f12a4cba2bcb4 stopped19:10:28.630Z, same old digest
d180f16cd50a1089365cfccd648560ab7bda14a65e2886c09c1fc93d7e5c3d93.
Its retained health label is not current availability. CPU previous5min average
49.657%,max53.765%; memory4.749%,max4.755%. Resource/refusal alarmsOK and
historical clock-stalledALARM remains. No current production-parity claim is
permitted from this cutover window. G1 caretakerPID37677(parent760) remains.
A1 made no production/process/control change; coordination recorded main ledger.

This closes only measured internal-heat coupling. Still required: physical contact
friction/conduction, live home/caregiver geometry conversion, ordinary learner
effort and local afference mapping, head optics, single outer organism/world
publication, copied mature-body/restart/resource and production gates. No new
approval needed within ratified body/interface scope. No gait/climbing/speech
claim and no deployment; full objective remains ACTIVE.


### FB-01i — native read-only sight geometry contract — 2026-09-25 19:28Z

Continuing the approved body/interface objective after offline FB-01h, not
reopening heat, learning, kernel, or G1's caregiver-following changes. Current
baseline is 26a516c37. This slice closes physical ray geometry only; it does
NOT close retinal radiometry, body/learner integration, or live delivery.

Exact defect: mounted motion retains a full head rotation, while the ordinary
retina uses rounded upright root geometry plus legacy neck offsets. Updating
only yaw/pitch would discard roll; updating the Python focal rays alone would
leave native rays, portal rectangles and spherical texture coordinates wrong.
No speculative roll correction or second geometric authority will be added.

Input -> output: authenticated current native world bytes and exact revision ->
one existing NativeBody scratch restored from those bytes -> declared link-local
optical origin and bounded local ray directions -> complete native rigid
transform -> pinned MuJoCo 3.3.7 mj_multiRay -> nearest native visible surface
index and distance, or explicit miss. Native geometry indices are internal
world optical evidence, never object-recognition or cognitive input.

Scope: functional_body_native.py, embodiment_world.py, and the existing
standalone test_functional_body_world.py. One implementation owner, A1.
NativeBody.ray_geometry supplies a typed transient batch; the existing world
authority exposes native_ray_geometry under its existing lock and revision
check. The origin's frame must belong to the organism's actual native subtree.
The optical origin is declared input, not a new anatomical location silently
inferred from a rounded root pose. No new eye anatomy is claimed in this slice.

Each direction is finite and nonzero, normalized without overflow and transformed
by the complete link rotation. The caller supplies the finite ray-count bound
from its optical sampling contract. Arrays are packed float64/int32 batches,
not per-pixel records. One native call per batch; all static/dynamic visible
native geoms are included, with no body, group or semantic exclusion. Native
opaque geometric intersection only: no radiance interpolation, texture
reconstruction, aperture integration, clipped-light inference or DSF reduction.

Read-only lifecycle: no integration step, elapsed time, effort, world mutation,
thermal mutation, receipt or persistent cache. Results own their storage and
cannot alias native scratch. Wrong revision/unmounted/wrong frame/malformed or
over-capacity rays fail without a world successor. Fresh restore must return
identical geometry and the same next actual motor successor, including after
intervening queries. Immutable mount and current integration bytes remain the
sole geometry authority. Existing codecs and model identities are unchanged.

Acceptance: existing authority mounts the full reference body; actual head effort
changes the batch rays through measured full head geometry; analytical scene hits
and physical occlusion agree; self geometry is not masked; zero-time world bytes
are unchanged; fresh-authority restart reproduces the ray result and the next
motor interval. Include invalid-input and stale-revision refusal, bulk19335-ray
resource evidence, and no retained-state growth. This is an offline geometric
component test, not an ordinary learner, copied production or live vision proof.
Optical radiance/material mapping and ordinary-loop consumption remain named
unclosed boundaries; helpers cannot authorize deployment.

Lean closure: reuse the admitted native collision scene, no second ray mesh,
native model, motion state, contact solver, eye tracker, cognition selector,
process, receipt schema, per-ray hash/tuple or retained frame history. Temporary
memory scales linearly with the declared ray count, native scene with admitted
anatomy. Query work cannot be represented as zero cost; measure batch cost.

Coordination: G1's main tree and live cutover untouched. His root-level following
commands do not become joint experience. Main ledger still has no newer immutable
handoff after A1 19:13Z. Source-only inspection found that optics.rs does not exist;
actual native legacy ray source is optical_raycast.rs. Absent path not retried.
Pinned local mujoco.h confirms 3.3.7 multiRay signature; latest-version normal-output
signatures are not used. No candidate tests/imports have run before this contract.

### FB-01i frozen review correction batch — 2026-09-25 19:35Z

Independent reviewer found two localized omissions, no architecture replacement:
(1) reuse existing public-visibility guard during hidden world publication;
(2) mjMAXVAL is finite1e10, not an infinite optical reach. Both corrected together
before imports/tests. Added hidden committed read refusal + rollback proof and
finite out-of-domain query refusal. No broader redesign.

Range contract: every native geom centre must lie inside the L-infinity cube
of radius mjMAXVAL/sqrt(3) around the ray origin. This sufficient envelope puts
all centres within the pinned engine's range-culling distance. Otherwise the
query refuses rather than presenting engine range culling as a physical miss.
No new scene cache or clipping threshold enters cognition. Pinned3.3.7
engine_ray.c mju_multiRayPrepare uses centre distance > cutoff+geom_rbound.
This conservative numerical-domain guard is disclosed, not a claim of an
unbounded optical engine.

Translation review: local origin + directions carry full measured head rotation;
origin/world unit rays and packed hit/distance arrays carry every queried
geometric quantity. Hit identity is world-internal; no new organism sensory
field is asserted. Native world/revision and existing visibility transaction
remain authoritative. Observing a prepared/hidden state is forbidden even if
the caller knows its revision. Authenticated current-state and all codecs
remain unchanged. Scene and ray batches remain bounded; no integration calls
are added by the query.

Frozen hashes after the single batch:
native078ec2f4025e3742614907e42982e9bdbd8c3bbb654406b9a27045d783395d47
world58883b34009f712b8f09d6fe232cc70bd27acfefe09e02a2bf996787a790cf5d
testsda5bc5647dc303e5f69a6721626a91bb2d8d7a719c322eea7c3c118951a9a12a

Tool-only failure preserved: first full-file construction used JS index instead
of indexOf and threw before any source write. Corrected operator code, no
partial file or tested candidate resulted. All source edits use full-file
apply_patch replacements. No tests, imports or compilation run yet.

### FB-01i offline geometry proof — 2026-09-25 19:38Z

Independent frozen source review passed after one batch of two localized
corrections. Production source stayed unchanged through all tests:
native078ec2f4025e3742614907e42982e9bdbd8c3bbb654406b9a27045d783395d47
world58883b34009f712b8f09d6fe232cc70bd27acfefe09e02a2bf996787a790cf5d.

First focused run:4pass/1error. The test supplied head effort addresses in
roll,pitch,yaw order; the existing command codec correctly refused this
noncanonical ordering before physical action. No physics assertion failed.
Corrected test ordering to pitch,roll,yaw without changing values/duration,
then independent source-only reviewer verified the fixture-only change.
Final testSHAea87f7004e494ac650200f692307a5789628499ab6e8aa553122e9dac34dc210.
Failed run0.815s, peakRSS143580KiB, PID2080 exited; failure preserved here.

Final focused5/5 passed in0.333s, then52 body/world/heat/anatomy/energy regressions
passed in3.373s. Entire standalone process4.349s, user4.286s/system0.076s,
peakRSS147672KiB, PID2443 exited. No pytest/conftest/network or production body.
Existing pinnedMuJoCo3.3.7, systemPython, numericalthreads1, bytecodewritesoff.
Postrun census shows no A1 harness/orphan. All frozen source hashes matched.

Physical evidence: actual externally applied head effort rotates the full native
head frame (including roll); analytic target-sphere/self-head distances and
misses agree; native state query never hides self geometry. Hidden committed
world reads refuse under existing publication guard, then rollback preserves
exact predecessor. Fresh authority restore reproduces geometry arrays exactly,
and intervening queries preserve the same next actual motor successor.
This is external bench effort, not learned action or mounted vision.

Batch19335 rays (current sample-count envelope) produces696060 bytes of transient
packed results. Three measured full query calls5.906ms/5.580ms/5.421ms, including
this test's observation/revision acquisition. No state-byte growth, retained
ray history, new geometry mesh, per-ray Python FFI call, persistent hash, clock,
or cognitive record. This small scene benchmark is NOT live retina latency or
a proof of performance at larger home-scene complexity.

AWS read-only health envelope:
-19:29:45 service1548 was1/1/0, sole taskc548cf988ab14687aa19f7636a1df029
 RUNNING/HEALTHY; digest55fd046f41d22b26d84fa01fe34ba2fdc7f6f1b01a3ded702d79dbbe56577179;
 identity1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1; observedlive2254716/persisted2254710,
 availabletrue/errorsnull/durabilityfalse.
-Immediately pretest19:35 and between/posttest19:36/19:37, G1's
 deploy_guala_turn_taking.py --execute PID1016(parent760) was cutting over:
 service1548 desired/running/pending0/0/0, no service task, old1548
 DEACTIVATING then STOPPED. Historical HEALTHY is not live availability.
-CPU matching service windows19:30 avg51.494%,max52.461%;19:35 avg51.216%,
 max51.324%; memoryavg3.663%/3.687%,max3.674%/3.687%. Cutover metrics are not
 a healthy-running-task proof. Resource/refusalalarmsOK; oldclockalarmALARM
 sinceSep8. G1 caretaker95907/supervisor80744 left untouched.
-A1 made no production, process, teaching marker or main-source change.
 Offline tests have no production-parity/deployment interpretation.

This closes native geometric querying only. The actual optical origin/ray grid
must still be bound in the ordinary receptor caller, and radiance, material
coordinates, aperture integration and organism consumption must use this same
physical scene without claiming old upright rays are correct. Existing source
sampling/learning/kernel remain unchanged. Full functional-body goalACTIVE;
contact thermal coupling, home/caregiver conversion, ordinary afference/effort,
outer atomic publication, mature-body and production acceptance remain open.
No additional user approval is requested for the already-ratified boundary.


### FB-01j — reconcile immutable G1 handoff before sensory integration — 2026-09-25 19:48Z

Previous goal turn PROGRESS:0b7bbe162,57 offline checks and checked Slack receipt.
No body mechanism is live. No-progress/block counter does not apply.

New authoritative dependency: G1 posted the stable source baseline5f3300a46
and source-identical ledger successor d7580460f at19:42Z. The handoff reports
task1549, imagec883967dae9703796245db6408d12ec03a7591dbb48c8c0c4188bdc2d1a837b8.
This entry is source reconciliation, NOT independent acceptance of that release's
behavioral claims. The new source must be preserved before ordinary body-loop
integration rather than overwritten with this branch's older functional runtime.

Source-only inspection also confirms the next optical consumer is not merely
a yaw/roll parameter: existing spherical material charts and portal aperture
rectangles depend on upright geometry. No radiance law or sampling approximation
is introduced here. The geometric query remains closed; optical material/
aperture coupling is open. Do not create a second scene or silently replace
finite aperture integration by centre-ray sampling.

One bounded item: integrate exact Guala-only immutable handoff files into this
isolated branch, preserving A1's already-reviewed mechanics and energy patch.
Common ancestor8f8b6b83ab74095eebc43389cb602ddc5fb1e547; current A1 HEAD0b7bbe162.
Git's source-only merge-tree6e3eca3f8252f6558e746f8b6707e17b715aeed6 has no
text conflicts. Exclude unrelated docs/CH2_PROFIT_TAKE_20260925.md, docs/TODO.md,
and tools/deploy_after_close_once.sh. Do not merge or mutate the moving main tree.

Authorized files from that immutable merge tree:
collaborative_todo.md;
dsf_ai_service/episodic_binding_engine.py;
dsf_ai_service/guala_caretaker_hand.py;
dsf_ai_service/guala_functional_organism.py;
dsf_ai_service/lean_actor.py;
dsf_ai_service/lean_production_app.py;
dsf_ai_service/lean_sensory_occurrence.py;
dsf_ai_service/static/gualaloom.html;
guala_caretaker/caretaker.py;
tests/test_conversational_turn_taking.py;
tests/test_high_chair_lifecycle.py;
tests/test_sensory_lane_separation.py;
tools/deploy_guala_curiosity_escort.py;
tools/deploy_guala_retention_release.py;
tools/deploy_guala_turn_taking.py;
tools/guala_retention_actor_proof.py.

All above files except functional organism must equal G1 byte-for-byte.
Functional organism's only difference from G1 must be the previously accepted
body-energy patch (constant units, typed prepared debit, same chemical reserve,
fractional debit, existing cost law). Preserve all G1 selection/speech/following
changes without relabeling them as A1-approved emergence. Native anatomy,
mechanics, world, thermal law, current state, codecs and kernel remain unchanged.
This is not a body deployment or an authorization to run imported release tools.

Acceptance: one frozen source-only overlap review; all immutable G1 blobs match
the declared source, all A1 body source blobs remain unchanged, L0-L4 unchanged,
excluded TFE files unchanged/absent; then existing standalone57 body tests with
the reconciled organism import. No pytest/conftest, live test endpoints,
caretaker start/stop or application startup. These tests check body integration
compatibility, not the validity of G1's speech or cognitive claims. No production
body is loaded or migrated. A copied production/startup/restart proof is still
required before eventual release.

Mutation/custody: full-file replacements only in clean A1 worktree, no running
organism mutation. Git ancestry retains both exact immutable baselines; no state
schema, persistent cache, new mechanism, controller or duplicate authority is
introduced. Temporary merge-tree objects only, no live branch checkout/reset.
No numerical coefficient or physical law changes; no regime sweep needed.
Offline test work is wrapped in read-only AWS health snapshots as before.

#### FB-01j acceptance — 2026-09-25 19:57Z

Frozen independent source review (mount_custody_review): PASS, no localized or
architectural finding. The only organism delta from G1 is the accepted A1 energy
patch; reciprocal comparison preserves G1's changes. This does not endorse G1's
cognitive claims or prove production compatibility of the new body.

Exact post-test source checks: all selected non-organism files equal d7580460f;
A1 native anatomy/mechanics/world/thermal/tests and uf_core equal 0b7bbe162.
Merged organism SHA256:
87e4f013f3eb405624dff2ffc28d51e54743a10699ba58c6261779e30dca960c.
Unrelated TFE files excluded. Git ancestry retains both immutable baselines.

Standalone runpy/unittest regression PID7432 (session63979): 57 passed in3.778s;
whole-process wall4.551s,user4.465s,system0.120s,peakRSS145808KiB. Existing pinned
MuJoCo3.3.7 and one-thread settings; no pytest/conftest, no copied live body or
network writes. Post-run census confirms PID7432 absent, no harness survivors.
This is component integration evidence only, not mature-body or live acceptance.

Read-only AWS envelope19:51:53/19:56:12: service1549 desired/running/pending1/1/0,
task478e055e5f0146789dd2ba0642bb578b RUNNING/HEALTHY,
digestc883967dae9703796245db6408d12ec03a7591dbb48c8c0c4188bdc2d1a837b8.
Identity1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1 unchanged;
live2256682->2257155,persisted2256671->2257151; availabletrue, checkpoint/cleanup
errorsnull,durabilityblockedfalse. CPU19:50 finalavg51.539%,max52.532%;
RAMavg3.123%,max3.149%. Resource/refusalalarmsOK; oldclockalarm remainsALARM,
so do not claim all alarms clear. Caretaker95907 remains active and untouched.
No A1 production write or restart.

Operator corrections: full-file restoration of the merge-only docs/TODO.md
change initially omitted a final blank line. Exact diff caught it; restored
that one file to clean premerge HEAD, with no user change discarded. Copied TFE
new files were excluded and remain recoverable in G1 history. Source whitespace
checks pass; exact upstream collaborative_todo.md retains its existing extra
EOF blank line, which blanket git diff --check reports. Do not silently rewrite
the immutable shared evidence to suppress that warning.

Source reconciliation is closed. Full-body goal remains ACTIVE and not live.
Next is native geometry -> existing optical material/radiance/aperture consumer,
within the approved motor/sensory interface. No new cognitive law or behavior.

### FB-01k — optical-law boundary and proposed correction — 2026-09-25 20:00Z

Previous goal turn PROGRESS: immutable integration69e43bf31 pushed,57 standalone
checks passed, checked Slack receipt19:57:19. Current branch clean on entry.
This continues the sensory consumer, not reopening native hit geometry or G1's
caregiving. No source edits, imports, tests, deployment or process interference
in this investigation. Scope authority for motor/sensory ports remains approved.

Architecture honesty gate: requested actual articulated-head sight; current
consumer only accepts root pose plus yaw/pitch and combines several incompatible
optical projections; conflict YES for mounting that consumer unchanged. Do not
extend the upright projection with a cosmetic roll, hide self geometry, retain
a second collision scene, or route native body poses through rounded root yaw.
Single next decision is the optical approximation below. This is reduced virtual
optics, not full DSF evaluation; no DSF field or cognitive law is being changed.

Exact evidence:
- guala_functional_loop.py:_world_retina_u8 calls retinal_carriage then the old
  retinal_irradiance_field. Native observation exists but this caller does not
  consume its complete head transform or the native ray query.
- w1_physical_receptors.py:_lit_surfaces_focal constructs directions from
  horizontal/vertical angles only. Its box normals and texture chart use yaw
  alone. A physical roll with unchanged root heading cannot rotate this view.
- _portal_aperture_background forms horizontal/vertical angular rectangles and
  blends their rectangular overlap. This is an approximation of doorway light,
  not integration over actual native geometry. It cannot be carried unchanged
  through arbitrary head rotation.
- _retinal_projection's patterned sphere uses pixel offsets from its projected
  centre to select material cells. Thus the texture is camera-facing: the same
  native surface point has no persistent material-cell binding. ObjectOpticalSurface
  declares a palette grid, not the missing sphere surface chart.
- NativeWorldMount declares body/object frame ownership but no optical material
  chart or eye mount. Reference anatomy has a head inertial site, not an optical
  aperture. Passing the inertial-site origin as an eye would start inside the
  opaque head. The prior query deliberately takes an explicit local origin.
- The current 135 coarse sites use finite aperture blending; the19200 focal
  sites mostly use centre rays/discs. Replacing every site with one ray would
  silently delete the coarse receptor's area response. The count alone is not
  evidence of equivalent sight.

Recommended bounded correction, PROPOSAL NOT IMPLEMENTED:
Use one explicitly declared head-mounted optical aperture with the retained
native head transform, and the existing native scene for visibility/self-occlusion.
Bind current six-band reflectance/emission data to that scene's material frames;
declare fixed local surface coordinates instead of camera-facing texture charts.
Keep the same19335 output sites, six-band input material units, external camera
contract, pupil/eyelid/quantization/saturation transport and cognitive consumer.
Numerically integrate each declared receptor aperture rather than silently
shrinking coarse apertures to point samples. The numerical optical error and
work bound must be declared and verified before selecting a production sampler;
neither a guessed supersampling count nor a favorable image is a proof.

The actual optical changes are explicit: actual geometric occlusion replaces
billboard/portal rectangle compositing; fixed material charts replace view-facing
charts; aperture integration replaces the current mixed approximations. These
cannot be claimed byte-equivalent to the old renderer. Do not describe them as
merely a motor-port extension or as exact human optics. No increased acuity,
recognition engine, object-ID cognition, gaze targeting or new learning rule.
No general renderer framework, GPU dependency or second scene is requested.

Acceptance for this correction: real head effort changes retinal light through
the same native geometry; stationary material markings stay attached to their
surfaces across viewpoints; hand/head self-occlusion is retained; a common rigid
transform of scene, light and eye preserves the image within the declared
numerical error; aperture-edge cases measure that error; fresh restore gives the
same image and next physical successor; current-only state and bounded work are
preserved. Then exercise the same path through the ordinary loop on a copied
production body. Isolated ray tests cannot substitute for those gates.

Authority status: the prior narrow exception explicitly permits numerical body
motion. This correction changes the optical sampling/material law as well, so
seek that exact extension rather than stretching the body-only exception. All
existing body/interface approvals stand; no reapproval requested for them.
First occurrence of this distinct authority blocker, not a three-turn blocked
condition. Goal stays ACTIVE and incomplete. No claim of a new live capability.

### FB-01k authorization and optical regime measurement — 2026-09-25 20:08Z

Joe explicitly approved: "I approve bounded numerical optics". The goal has
resumed ACTIVE. The preceding authority blocker is closed; do not ask again.
Prior numerical body and motor/sensory approvals remain effective. The renderer
may change the declared numerical optical approximation, but not retinal count,
DSF, cognition, learning law or source identity. No production change yet.

One immediate measurement: aperture quadrature on the actual native scene,
using analytically known luminous edges/strips, the existing reference body,
and the current135 coarse +19200 focal angular apertures. This determines the
error/cost relation before a production sample count is chosen; it is not a
second renderer to retain in the organism. Authorized diagnostic file:
tools/guala_body_optical_regime.py. Runtime source remains unchanged this step.

Contract: native accepted geometry/state -> existing batched ray query -> fixed
six-band emissive material of the struck surface -> solid-angle aperture mean.
Use h and mu=sin(v) coordinates, since dOmega=dh*dmu. Midpoint quadrature has
equal solid-angle weights within each aperture. World geometry IDs address
physical material inside this offline renderer only, never cognitive identities.
No anatomy replica, collision solver, mutable observer state or world authority.

Physical cases: a planar bright half-field with known angular edge and a narrow
bright strip with known angular width. Their exact solid-angle means provide
independent error truth; comparing only two numerical levels is insufficient
because both may miss the same strip. Sweep fixed deterministic edge phases and
sample counts, including subpixel features. The current full retinal grid is
exercised at bounded counts; coarse error is measured independently at finer
counts. Report max/mean six-band error, eight-bit discrepancy both before gain
and at existing maximum16x gain, rays, calls, elapsed time and process peakRAM.
Report convergence estimates separately from true analytic error; do not call
agreement between two sample levels a guaranteed error bound.

Transient rays are chunked by an explicit8MiB logical working allocation at
256bytes/ray=32768 rays; allocator/native peak is separately measured, not claimed
bounded by that estimate. Total declared work is finite. No imports of tests,
functional loop, caretaker, pytest, live endpoints or production state.
Fresh native restore must return identical light; querying must leave the next
motor successor unchanged. Native self geometry remains visible.

Freeze and independent source-only review precede running. Read-only AWS health
envelopes surround execution. No ordinary-loop or deployment claim is possible
from this diagnostic. The next production optical contract will use the measured
error/cost and preserve the full material/light/visibility path; no fixed sample
count is accepted in advance merely because it renders quickly.

Pre-run independent review found one localized reference defect: native panels
have finite depth/extent, but the initial analytic reference treated them as
infinitely thin/unbounded. No run occurred. Corrected in one batch: use all
front/back horizontal silhouette corners and report a separate bounded far-z
angular sliver. Native self AABBs certify that the initial diagnostic FOV has
no body occlusion; all body geometry still participates in ray queries. Analytic
bounds are float64 evaluations, not a formal directed-rounding certificate.
Also moved the immutable count-array conversion out of the chunk loop. No
production optical law or body physics changed. Re-freeze/review before run.

### FB-01k measured aperture error/cost — 2026-09-25 20:20Z

Independent corrected frozen source review passed before execution; fingerprint
0cd714ab4e9920ffbe6c6f4fc4e0d84f726d359bb7daa84b15dddd8990e88737
also matched after. Diagnostic SHA256:
66dd7060b6ed368808ff669408e4efe876bfb0cd0b3b11a59674cc39223d030d.

Run PID17577/session54787, exit0. All32 declared regimes completed;
cold optical outputs and next actual motor successors match, no non-panel hits.
Wall4.779776s,user4.888849s,system0.036065s,peakRSS211340KiB. Postrun PID/process
census has no diagnostic survivor. Peak includes native models/scratch, not
just the8MiB logical batch budget. No package install, pytest, production body,
live write or engine/cognitive source modification.

Decisive finding: uniform midpoint supersampling is NOT accepted. In the narrow
strip,1x1,2x2 and4x4 full-field samples all miss the same feature: true maximum
error0.053608389,14 byte levels before gain,219 at16x. Equal successive samples
therefore cannot establish convergence. The135 coarse sites still miss that
strip at64x64 (~173ms), then overshoot at128x128 (~690ms,24 byte error at16x).
More rays alone are not the proposed solution. Full-grid4x4 costs100–121ms on
this two-panel/reference-body scene and still misses the strip. These timings
are not production/home performance or a250ms acceptance receipt.

Record of measured regimes (error bounds use analytic float64 interval; interval
width for half-fields <=5.7295782e-7, strip0; not formally rounded arithmetic).
Gain1/16 are the uncloaked eight-bit discrepancy, without eyelid attenuation.
High sample counts measure135 coarse apertures only, not the19200 focal sites.

| case / lower edge deg | n per axis | sites | rays | ms | maximum error bound | byte error gain1/16 | coarse change from prior |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| edge 0.117 | 1 | 19335 | 19335 | 11.668 | 0.49418017 | 126/255 | — |
| edge 0.117 | 2 | 19335 | 77340 | 27.223 | 0.18960907 | 48/51 | 0.5 |
| edge 0.117 | 4 | 19335 | 309360 | 105.483 | 0.060390928 | 15/2 | 0 |
| edge 0.117 | 8 | 135 | 8640 | 3.945 | 0.011639660 | 3/2 | 0 |
| edge 0.117 | 16 | 135 | 34560 | 11.875 | 0.011639660 | 3/2 | 0 |
| edge 0.117 | 32 | 135 | 138240 | 50.613 | 0.011639660 | 3/2 | 0 |
| edge 0.117 | 64 | 135 | 552960 | 185.413 | 0.0058198299 | 2/2 | 0.015625 |
| edge 0.117 | 128 | 135 | 2211840 | 723.015 | 0.0038271598 | 1/1 | 0.0078125 |
| edge 0.499 | 1 | 19335 | 19335 | 7.410 | 0.47517867 | 121/255 | — |
| edge 0.499 | 2 | 19335 | 77340 | 25.797 | 0.17619563 | 44/51 | 0.5 |
| edge 0.499 | 4 | 19335 | 309360 | 106.751 | 0.073804367 | 19/10 | 0 |
| edge 0.499 | 8 | 135 | 8640 | 3.230 | 0.049642664 | 13/10 | 0 |
| edge 0.499 | 16 | 135 | 34560 | 15.649 | 0.024821332 | 7/10 | 0.0625 |
| edge 0.499 | 32 | 135 | 138240 | 43.007 | 0.012857336 | 3/3 | 0.03125 |
| edge 0.499 | 64 | 135 | 552960 | 170.095 | 0.0064286681 | 1/3 | 0.015625 |
| edge 0.499 | 128 | 135 | 2211840 | 710.642 | 0.0027676638 | 1/0 | 0.0078125 |
| edge 4.999 | 1 | 19335 | 19335 | 6.456 | 0.49733483 | 127/255 | — |
| edge 4.999 | 2 | 19335 | 77340 | 25.642 | 0.24866742 | 64/101 | 0.5 |
| edge 4.999 | 4 | 19335 | 309360 | 100.243 | 0.012262149 | 3/1 | 0.25 |
| edge 4.999 | 8 | 135 | 8640 | 3.294 | 0.0026651694 | 1/1 | 0 |
| edge 4.999 | 16 | 135 | 34560 | 12.113 | 0.0026651694 | 1/1 | 0 |
| edge 4.999 | 32 | 135 | 138240 | 43.833 | 0.0026651694 | 1/1 | 0 |
| edge 4.999 | 64 | 135 | 552960 | 174.382 | 0.0026651694 | 1/1 | 0 |
| edge 4.999 | 128 | 135 | 2211840 | 823.160 | 0.0026651694 | 1/1 | 0 |
| strip 0.02 | 1 | 19335 | 19335 | 11.163 | 0.053608389 | 14/219 | — |
| strip 0.02 | 2 | 19335 | 77340 | 39.037 | 0.053608389 | 14/219 | 0 |
| strip 0.02 | 4 | 19335 | 309360 | 121.231 | 0.053608389 | 14/219 | 0 |
| strip 0.02 | 8 | 135 | 8640 | 3.982 | 0.0020103146 | 1/8 | 0 |
| strip 0.02 | 16 | 135 | 34560 | 14.917 | 0.0020103146 | 1/8 | 0 |
| strip 0.02 | 32 | 135 | 138240 | 53.425 | 0.0020103146 | 1/8 | 0 |
| strip 0.02 | 64 | 135 | 552960 | 172.983 | 0.0020103146 | 1/8 | 0 |
| strip 0.02 | 128 | 135 | 2211840 | 690.332 | 0.0058021854 | 2/24 | 0.0078125 |

Read-only AWS pre20:18:10/post20:19:04: task1549,
478e055e5f0146789dd2ba0642bb578b, digest
c883967dae9703796245db6408d12ec03a7591dbb48c8c0c4188bdc2d1a837b8,
RUNNING/HEALTHY, service1/1/0, sole listed task. Same organism identity
1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1; live2259506->2259603,
persisted2259487->2259583; availabletrue, checkpoint/cleanupnull,
durabilityblockedfalse. CPU20:15 avg51.419%,max52.513%; RAMavg3.162%,max3.198%.
Resource/refusalalarmsOK; oldclockalarmALARM unchanged. Caretaker95907 active.
A1 did not modify live serving or controls.

Next exact optical item: account for actual geometric/material boundaries in
aperture integration, retaining native visibility and fixed surface coordinates.
Use the recorded edge/strip failures as falsifiers; do not install the diagnostic
midpoint sampler or invent a sample-agreement threshold as production truth.
No new user approval needed. Whole-body objective ACTIVE, still not delivered.

### FB-01l — convex physical-surface aperture integration contract

Previous turn PROGRESS:48d3e8ef3 supplied32 measured regimes and ruled out uniform
supersampling/sample-agreement as an optical error guarantee. This is the next
necessary numerical optical operation, not another sampler-count sweep.

Requested architecture: integrate actual projected surface area, including
subsample-width strips, under arbitrary head-frame rotations. Current reality:
native rays give actual hit geometry but no aperture area; uniform midpoint
coverage aliases. Conflict YES if that rejected sampler were promoted. No DSF,
cognition, anatomy, live runtime or physical state is changed by this slice.
The body/optics are reduced numerical models, not full-field cognitive evidence.

Scope: dsf_ai_service/substrate/functional_body_optics.py,
tests/test_functional_body_optics.py and this ledger. Existing diagnostic scene
is reused by offline tests, not copied into a new world. One owner A1; frozen
independent source review before imports/tests. No new native package/build.

Input: a convex surface's directed spherical halfspaces n dot d>=0, expressed
in the actual eye frame, and the unchanged rectangular angular receptor apertures
(h_lo,h_hi,mu_lo,mu_hi), mu=sin(v). Output: each aperture's covered solid angle.
This operation neither chooses visibility nor assigns a material/object identity.
World/native visibility and fixed material charts must still supply and compose
the surfaces before this becomes a complete renderer. It must never be used to
sum mutually occluded surfaces or call a convex cone a recognized object.

For each halfspace set A(h)=n_x*cos(h)+n_y*sin(h). If n_z>0 the lower boundary
is mu>=-A/sqrt(A*A+n_z*n_z); if n_z<0 it is the upper boundary with the opposite
sign; n_z=0 gives a horizontal angular interval. Split at actual great-circle
intersections and crossings with the receptor's constant-mu edges. Between those
events the active upper/lower boundaries cannot change. Integrate analytically:
F(h)=-sign(n_z)*asin(R*sin(h-phi)/sqrt(R*R+n_z*n_z)),
R=hypot(n_x,n_y),phi=atan2(n_y,n_x). Use stable angle differences to avoid
subtracting near-equal inverse-trig values. Constant boundaries integrate as
mu*delta_h. dOmega=dh*dmu, so no ignored angular Jacobian.

Cheap exact-domain extrema of each halfspace over a receptor classify wholly
inside/outside cells; only intersected boundary cells need subdivision. These
are geometric inequalities, not salience/distance scores or guessed similarity
thresholds. All operations use approved float64 optical numerics; this is not
formal exact-real interval arithmetic. Reject non-finite/malformed domains.

Work: caller supplies max_cells for temporary interval work. Derive the finite
per-aperture event ceiling from the supplied plane count before allocation;
chunk affected apertures within that explicit limit. No retained scene, cache,
ray image, history, physical update or global authority. O(site_count*planes)
classification followed by work on boundary cells; source has no runtime caller
until full material/visibility integration is implemented and verified.

Acceptance: reuse the actual finite native luminous boxes and all19335 apertures
from the prior failure. Sum only the analytically disjoint visible faces of each
convex emissive box (not arbitrary overlapping objects), compare to independent
finite-box bounds, and require the strip's nonzero response. Test arbitrary
rotations of face coordinates, native ray coverage of known interior directions,
complement partitions, full/empty aperture cases, input/work refusal and no
source-state mutation. Measure work/time/RAM; do not claim complete optics or
250ms production from this component. Preserve all prior failure data unchanged.

#### FB-01l verification — 2026-09-25 20:37Z

Independent frozen source review found two localized issues, corrected in one
batch: centroid winding did not prove convexity; native interior-ray witnesses
were absent. Nonincident-vertex halfspace validation now rejects the concave
face, and all four scenes verify independent bright/dark native hits. Final
review passed fingerprint
59de37e71767c6f7fa8c2f613b42d96fb1b2914bcb4fad6847c64cd60147bf22,
unchanged before/after execution. No architectural rejection or test-driven
candidate revisions. One tool-script syntax error before patch invocation made
no file changes; corrected before the one batch was applied.

Standalone unittest/runpy, no pytest/conftest/live writes: **5 passed** in0.444s.
PID22618/session73210 completed exit0; processwall0.615794s,user0.598258s,
system0.03638s,peakRSS87484KiB. Pinned existing MuJoCo3.3.7 and numpy2.4.6;
single-thread BLAS, no package installation or compiled rebuild. The test process
created no children; post-run PID census found no surviving harness process.

| Native scene | Apertures | Measured integration ms | Error outside independent finite-box reference |
|---|---:|---:|---:|
| edge0.117deg |19335|9.443599|5.35637312282e-10|
| edge0.499deg |19335|10.018189|2.83360113151e-10|
| edge4.999deg |19335|9.762063|5.05404496032e-10|
| strip0.02–0.04deg |19335|9.549199|1.62786450986e-14|

These timings cover one convex luminous box, not full scene visibility or
production latency. The strip now produces its physical nonzero aperture area.
Tests also prove complement/full/empty area, chunk-equivalent outputs, rotated
surface area against independent spherical-triangle formula, opposite winding,
concave/domain/work refusal, unchanged native observation, actual head-effort
light change, bit-identical fresh native reconstruction and next motor successor.
This is locally exercised numerical geometry, not a complete optical renderer,
recognition, full DSF evaluation, or production-body delivery.

SHA256:
- functional_body_optics.py:1c0c700e168af7c2adb4144b3fc2bceefa05c2914d3567fc108fbc0fa466cf43
- test_functional_body_optics.py:810ca36b3e86daf14782a83f3d493b5b5c3986c93355ee8ddcfad632d0383824

AWS read-only pre20:36:12/post20:37:18:1549 sole task
478e055e5f0146789dd2ba0642bb578b,service1/1/0,RUNNING/HEALTHY,digest
c883967dae9703796245db6408d12ec03a7591dbb48c8c0c4188bdc2d1a837b8.
Identity1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1 unchanged;
live2261394->2261502,persisted2261375->2261471,availabletrue,
checkpoint/cleanupnull,durabilityblockedfalse. CPU20:30avg51.444%,max52.387%;
20:35avg51.348%,max51.701%. RAM20:30avg3.110%,max3.180%;
20:35avg3.080%,max3.113%. Resource/refusalalarmsOK; historicalclockalarmALARM
unchanged. Caretaker95907 untouched. G1's separate pursuit pytest was visible
in the pre-run census; no heavy A1 workload or process interference occurred.

Next exact item: visible-surface/material composition using this aperture
primitive and authoritative native geometry. Occlusion, surface-attached
textures, curved surfaces and ordinary-loop optical mounting remain open. Do not
sum overlapping faces, substitute centre rays as area, revive rejected uniform
sampling, or claim the whole functional-body objective complete. GoalACTIVE.

### FB-01m — bounded planar visibility and material-coordinate continuity

Previous turn PROGRESS:2dac2bb39 closes convex aperture integration locally.
This continues the same approved optical correction; live1549 is unchanged.
Requested architecture: actual near-surface occlusion and surface-attached
material coordinates from authoritative body/world geometry. Current reality:
the accepted component integrates one projected region but does not remove
occluded overlap; the legacy renderer sorts by centre depth and contains
view-facing material charts. ConflictYES if those paths were used for native
body sight. Neither legacy path is extended. This is numerical optical
geometry, NOT full DSF evaluation or a change to DSF/cognition.

Single item: a transient planar visibility operator in
dsf_ai_service/substrate/functional_body_visibility.py, with standalone tests
in tests/test_functional_body_visibility.py. No native model, world state,
mechanical solver or production caller change in this component. Curved native
surfaces, complete shading/material law and ordinary-loop mounting remain open;
the component must not silently tessellate or drop those shapes.

Input: float64 planar patches in the actual eye frame: origin, two physical
surface axes, and an ordered convex UV boundary. The caller derives these from
native planar geometry. This represents each plane once, without splitting a
box face into coplanar triangles or adding a planarity-tolerance test. Explicit
transient work/residency limits bound each call. Output: disjoint visible convex
fragments, each carrying its source patch index and attached UV coordinates. These indices are temporary world-rendering
addresses, never afference, object recognition or cognition. Surface material
coordinates interpolate from the same original surface; moving an eye cannot
reassign a material cell to a different physical point.

For each source patch with plane n_s dot p=c_s, orient n_s so c_s>0.
Clip geometry to forward x>=0; a plane through the eye has zero angular area.
For blocker b, points on overlapping positive rays are nearer when
(c_s*n_b-c_b*n_s) dot d>0, derived from t=c/(n dot d).
Its occluding cone is the blocker boundary's directed edge halfspaces intersected
with this depth halfspace. Subtract that convex set by successively clipping
the source fragment: emit the outside piece, retain the inside piece for the
next boundary. This partitions rather than alpha-blends overlap, and handles
depth order that changes across intersecting planes. Exact coplanar overlapping
surfaces have no unique material owner and must refuse, not use array order.
No centre-distance ranking, minimum apparent size, salience or sampling law.

Clip vertices in source UV coordinates, with point=origin+u*axis0+v*axis1. Retain no scene/history/cache;
no source mutation, publication, rollback or checkpoint schema is introduced.
Reject malformed/nonfinite/degenerate geometry and resource exhaustion before
returning an image; never return a partially occluded approximation on overflow.
Finite per-call clipping work and resident fragment vertices are explicitly
bounded by caller limits, not hidden fixed counts. The unmounted consumer must
not expose stale successful data as this occurrence's light on a refusal.

Acceptance: near/far overlapping patches partition aperture area; input
permutation preserves material radiance; coplanar ambiguity refuses; native
box face fragments agree with independent native rays, including slanted
blockers and actual head effort. Attached UV coordinates reconstruct the original
surface point through rotation/translation; cold state yields the same light
and next physical successor. Test forward-plane crossing, empty/hidden faces,
resource refusal and immutable input. Use the existing aperture primitive to
check finite strip visibility, not point hits as an area estimate. Before any
execution, freeze and obtain one source-only independent review. AWS read-only
envelope and process/resource census remain required. Component evidence cannot
close complete optics, the ordinary copied-body path or production delivery.

#### FB-01m rejected after native execution — 2026-09-25 20:59Z

This candidate is NOT accepted or production-ready. Its two newly authored
source/test files were removed from executable paths; their complete final diff
is preserved in docs/evidence/FB01M_REJECTED_PLANAR_VISIBILITY_2026-09-25.diff.
Accepted runtime baseline remains2dac2bb39. No prior user's/G1 source removed.

Independent frozen review found three localized defects: potentially overflowing
clipping arithmetic; collinear UV corners incompatible with the downstream
strict cone validator; omitted preparation work charges. One correction batch
addressed all three, final source review passed166020de...c22be54. Execution then
falsified the complete numerical translation, despite that source review:

|Attempt|Frozen candidate|Actual result|
|---|---|---|
|1|166020de713cc9e8ffe693aa6fa40ebb6205e481e32533c60be9332fcf22be54|first common-rotation testERROR: planar boundary reverses along an edge|
|2|a62de9744e52f220586a027ea33db4f99fbd6b8dcb0478380894cc522e002f98|three testsPASS; native geometry testERROR: zero surface edges|
|3|2a3a69271bd683dee1bacfc546471a3243b57963dcdf44736692c03b0f157760|three testsPASS; native geometry testERROR: surface is degenerate or not ordered convex|

First diagnostic: a rotated adjacent-material clip returned exactly
UV[(0,0),(0,1),(0,1)]. Zero-area dismissal ran after edge-reversal validation.
The local correction moved the existing exact zero-area test before validation;
independent review confirmed it. No tolerance was introduced.
Second diagnostic: native side-face sliver at origin(1.934,.003939091417123564,0),
axes(.005,0,0)/(0,0,100000), UV u=-1 versus-.9999999999999963 produced
four corners but only two distinct float64 physical points, both x1.929.
Exact duplicate-point removal closed that reported translation defect and passed
source review, but the next native execution still failed cone convexity.
Therefore no more incremental exception/tolerance repairs are admitted to this
representation. The reconstructed UV->point->unit-direction->edge-plane round
trip is numerically unsuitable for this acceptance scene. It must be replaced,
not called verified because simpler tests pass. No performance claim is made.

Process receipts (all standalone, no pytest/conftest/application startup):
- attempt1 PID27474 exit1,wall.126526s,user.132676s,system.008041s,peak53564KiB.
- diagnostic1 PID27600 exit0 (captured failure, NOT acceptance),wall.193335s,
  user.150082s,system.04288s,peak54212KiB.
- attempt2 PID28133/session84370 exit1,wall.465367s,user.424556s,
  system.056073s,peak72880KiB.
- diagnostic2 PID28382 exit0 (captured failure),wall.410882s,user.399316s,
  system.016133s,peak70240KiB.
- attempt3 PID28930/session27108 exit1,wall.508981s,user.427126s,
  system.096707s,peak73160KiB.
All handles collected; post-census no A1 harness remains. Other observed pytest
children belong to G1 parent760 and were not interrupted. Caretaker95907 intact.
Final rejected source SHA147e7e1f3fbe4022dd2fc880f3bbf80ff654b51f44abe9872a7c2e237e2e9523;
test SHA87034e92e97523eb79bbc61d5168ad7796c336a2a50880685f107193fc8112d4.

Read-only AWS envelope: pre20:48:15, refreshed20:53:16,20:53:49,20:55:25,
20:56:43,20:58:03,post20:59:44. All observed service counts1/1/0 and same
task1549,478e055e5f0146789dd2ba0642bb578b,RUNNING/HEALTHY; sole task census
at20:48,20:53,20:55,20:59. Digestc883967dae9703796245db6408d12ec03a7591dbb48c8c0c4188bdc2d1a837b8.
Sameidentity1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1; live ticks
2262678,2263205,2263262,2263429,2263565,2263712,2263893; persisted
2262655,2263199,2263231,2263423,2263551,2263679,2263871.
Availabletrue,checkpoint/cleanupnull,durabilityblockedfalse throughout.
Resource/refusalalarmsOK; historicalclockalarmALARM unchanged.
CPU latest20:50avg51.562%,max52.392%;20:55avg51.713%,max52.393%.
RAM20:50avg3.054%,max3.125%;20:55avg3.089%,max3.143%.
These are a diagnostic health envelope, not a complete production health audit.

Joe's touch/proprioception comment adds no scope change. Actual contact/force,
joint/inertial feedback remain required body outputs; optical visibility cannot
substitute for grasp/contact success. Continue the optical seam as requested.

Next exact correction, NOT implemented or yet frozen: retain directed geometric
halfspaces through visibility subtraction and feed those same constraints to
aperture_solid_angles directly. Keep the original planar material chart once;
do not reconstruct visible corners and infer new edge planes from them.
Convex subtraction is A minus B = disjoint regions
(A intersect not b0), (A intersect b0 intersect not b1), ... .
Plane-depth order remains the physical t=c/(n dot d) inequality. Resource and
numerical error bounds, coplanar/zero-area treatment and actual native acceptance
must be closed in the replacement contract before freezing it. No guessed epsilon,
centre-depth painter, uniform supersampling or failed representation may return.
GoalACTIVE; optics/body integration and production delivery remain incomplete.

### FB-01n — direct homogeneous visibility and material charts

Previous turn PROGRESS:5279bfbba preserved the native falsifier and restored
accepted executable baseline2dac2bb39. This is a replacement contract, not a
further patch to rejected FB-01m. New files functional_body_visibility.py and
test_functional_body_visibility.py remain the scoped component; no live caller,
mechanical law, sensory anatomy, DSF or cognitive state changes.

Represent each original planar surface once with eye-frame origin O, axes U,V,
and a convex UV boundary. Form H=[O U V]. For a positive ray p=t*d,
H^-1*d=(1/t,u/t,v/t). Thus the original UV inequality a*u+b*v+c>=0 maps
directly to (a*row1+b*row2+c*row0) dot d>=0, along with row0 dot d>0.
Plane-depth order uses (row0_blocker-row0_source) dot d>0. H is computed once
per source surface. Reject singular/nonfinite input rather than inventing a
chart. Degenerate planar geometry is unavailable, not a new mechanical surface.

Carry these directed halfspaces through set subtraction, never reconstructing
UV or physical corner polygons. Feed the same constraints to the accepted
aperture_solid_angles primitive. A minus intersection(b_i) partitions into
A intersect(-b0), A intersect(b0,-b1), ... . Area-zero pieces under the declared
numerical integrator do not contribute. No epsilon, size filter, average-depth
sorting or sample-agreement threshold. Coplanar overlapping geometry refuses;
materials are not separate occluders. Different material cells of one physical
surface are UV constraints integrated AFTER geometric visibility.

Output is transient source-surface index + owned directed constraint array,
valid only within the caller's declared enclosing angular aperture. Material
addresses remain world-only. They cannot enter afference or cognition. No
retained scene, secondary mechanical model, history, checkpoint state or partial
image publication. On work/storage/conditioning refusal, return no image.

Bounds: explicitly limit retained halfspace rows, integrated event-work and
temporary integration cells. Charge the known event ceiling K*(K-1)+6*K+2 for
each one-domain area query before execution. Count input preparation and pair
depth work too. Storage is O(max_halfspaces) plus the explicitly capped
integrator scratch and immutable input. No observer process or new dependency.
This component does not yet render curved shapes, full shading or a home world;
these are still required before ordinary-body/cold/production acceptance.

Acceptance: repeat the rejected native slanted-box/head-effort/cold-state scene
without relaxing its native ray witness; independent near/far area partition,
crossing depth order, input permutation, common rotation, source-fixed two-cell
material division, resource refusal and nonfinite/singular inputs. Actual source
chart coordinates and six-band materials must survive visibility unchanged.
Measure the native scene work/time/RAM honestly; helper timing is not production
cadence. Frozen source review precedes execution. Any failure in representation
again rejects this candidate rather than restarting the special-case loop.

#### FB-01n execution receipt — 2026-09-25 21:15Z

Independent source review of f5f53545985db3da17c0325750e1815762ada3c6deba66d29867bd0f1ff047ce
found one localized omission: material_halfspaces did not forward max_corners.
One correction batch forwarded that bound. Final source-only review PASS,
fingerprint f30a1ded9a396233a427c1b7eed95b549e330da34a9536f72dd0b1daa95ef834
verified before/after by reviewer and again before execution. No architectural
finding, no imports/tests before review, no changed acceptance assertions.

Standalone unittest/runpy process33005/session54619: exit0,4/4PASS in3.721s;
whole process wall3.840081s,user3.808173s,system.052002s,peak82376KiB.
Correctness evidence: independent near/far area partition and input permutation;
intersecting-plane depth selection; attached material-cell area partition and
original UV continuity under rotation; empty/forward-crossing/coplanar/invalid/
budget refusals. The exact prior rejected native slanted-box scene now passes:
80 interior rays agree with the full native scene, every witness covered once,
actual motor-driven head movement changes radiance, fresh native restoration
returns identical image bytes and next mechanical successor. All19335 existing
apertures and six material bands are evaluated. This is a planar component,
not the full home/body renderer or live receptor proof.

Performance is NOT accepted for deployment: five input surfaces yielded22visible
regions in.867981043s before head movement,17regions in.656413103s afterward.
Both exceed250ms before ordinary-loop/cognitive work. Correct numerical output
does not close the latency requirement. No claim of a production speedup.
Next exact item: isolate and remove repeated geometric/integration work on this
same accepted representation while preserving its native falsifier and material
partition. Do not add curved-scene features, weaken accuracy, enlarge queues,
or swap in centre sorting/uniform sampling to evade this measured cost.

Bounds clarification: original chart preparation is separately bounded by
max_corners (convexity O(max_corners^2)); visibility max_work charges prepared
input rows, pair operations and each integral's event ceiling. This is not a
claim that max_work counts every CPU instruction or constructor operation.
No persistent visibility cache, new scene authority, state schema or live caller.

Source SHA8407971c6e2ce7b71a7e4441651628b46ed57355e19c6aca21dc7f4f31bb4c01;
test SHA7825de7d1b3095630641889290d532d94ee3bc8961d0155316b082b0589e9d85.
Post-census21:14:34 and21:15 shows no harness33005 or A1 Python survivor;
only G1 caretaker95907 remains, untouched. No pytest/conftest/app startup or
live write, marker change, caretaker interruption, or deployment.

Read-only AWS envelope pre21:13:30/post21:14:34: us-east-1,tfe-web-cluster,
dsf-ai-service-lb,desired/running/pending1/1/0,sole1549 task
478e055e5f0146789dd2ba0642bb578b RUNNING/HEALTHY,image
c883967dae9703796245db6408d12ec03a7591dbb48c8c0c4188bdc2d1a837b8.
Same identity1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1;live2265242->2265338,
persisted2265215->2265311,availabletrue,checkpoint/cleanupnull,
durabilityblockedfalse. Resource/refusalalarmsOK;historicalclockalarmALARM.
Pre-window21:10CPUavg51.297766%,max52.533359%;RAMavg3.084988%,max3.161621%.
Post-window21:10CPUavg51.266329%,max52.533359%;RAMavg3.099060%,max3.192139%.
CloudWatch window still filling, not a before/after causal performance claim.
No new immutable G1 source/deployment receipt since1549; dirty staged main tree
and sleep-window plan left intact. GoalACTIVE; complete body not deployed.

### FB-01o — remove measured aperture-event execution waste

Continue optics latency after6c8324a5a; previous turnPROGRESS. Authorized scope:
functional_body_optics.py, existing visibility test, this ledger only. Preserve
all visibility/source chart laws and actual native acceptance; no anatomy,
material, world/cognition/persistence or production change. Numerical-optics
approval remains sufficient. Component-only, not full DSF evaluation.

Unchanged-source diagnostic34073/session16812 exit0,wall2.693573s,
user2.676489s,system.03215s,peak74056KiB. Initial imageSHA
d53a40d0d3e6d26ce2785e87cc6ff7b65bfcb3c807d3b443fcbdec094dbd1373,
movedSHA b446fa182e541c378feacf12c85deb8005498902ca09ab223e07f28da6b5a2e8.
Initial22regions with12,13,15,16,14,15,17,12,14,15,16,17,14,13,15,12,14,11,10,11,8,11
constraint rows; moved17regions with12,13,15,16,14,15,17,7,9,10,11,12,9,12,14,5,5.
Profiled(not baseline wall timing) initial2,390,145calls/1.470s;
moved1,686,745calls/1.002s. Initial220areaqueries(198visibility/22radiance),
18341tiny np.cross calls,.543s cumulative;60926np.clip calls;2822dot-extrema
calls,.347s cumulative. Moved162queries,12804cross,43187clip,2012extrema.

Waste register: pair intersection only needs x,y to compute longitude, but each
pair constructs a3-vector and invokes generic np.cross/moveaxis machinery.
Each fixed scalar event is separately converted, clipped and stacked for every
aperture batch. Every plane also recomputes identical aperture trig and checks
apertures already proved outside earlier constraints. None changes physics.

Replacement contract: retain exact input/normal order and equations. Compute
the two pair determinants directly with binary64 multiplications/subtraction
and original math.atan2/wrap. Fill one bounded event matrix; clip all fixed
events as a packed operation and sort in place. Reuse aperture endpoint trig
within each call and stop classification for already excluded apertures. The
same original boundary integral, event ceiling, root calculations and physical
constraints remain authoritative. No epsilon, feature cull, plane reduction,
new event law, field flattening or output quantization. Zero retained cache.

Input->output path: visible_planar_regions.area and caller radiance ->
aperture_solid_angles -> same normalized directed planes, analytic crossings,
boundary integral -> solid-angle values. New scratch is per-call only; no body,
thermal, material, sensory or native state mutation. Refusal remains before
publication; no new persistence/crash/restore branch. Scratch remains O(N)+
O(max_cells), not history. Preserve event-count refusal on original K. Exact
tested predecessor image bytes, native head/cold/next-state witness, all5prior
aperture tests and4visibility tests are frozen acceptance. Explicit additional
assertions pin the two measured image hashes. Source-only review before tests.
Performance must be measured unprofiled; passing hashes is not latency success.

FB-01o frozen source review03f0fcf486f4e70e298cb56653e6d76f6620c1ed03f0c54fbe96d8ecebab2ff5
passed with no findings. Verification35175/session39873 exit0,9/9PASS in2.700s;
wholewall2.874158s,user2.809699s,system.076154s,peak90436KiB. Both exact
predecessor image hashes match. Native5-surface scene .471428819s(initial),
.378948266s(moved), versus .867981043/.656413103 before. Four single-box
scenes8.27-9.61ms, same independent error bounds. Speed improved but250ms
remains unachieved, so no deployment. OpticsSHA91ae9d066814c3351c1898b416bc62e1151b32647b31a2ffa33a38ab81f77502;
testSHA67f89883ddbbb7568811c44a6e82dcaa01dd0980992187fddcce2919dff79184.

Diagnostic AWS pre21:17:09/post21:18:49, verificationpre21:21:30/post21:23:04:
sameus-east-1,tfe-web-cluster,dsf-ai-service-lb,sole1549 task478e055e5f0146789dd2ba0642bb578b,
RUNNING/HEALTHY,1/1/0,digestc883967dae9703796245db6408d12ec03a7591dbb48c8c0c4188bdc2d1a837b8.
Sameidentity1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1,availabletrue,
checkpoint/cleanupnull,durabilityblockedfalse. Diagnosticlive2265580->2265731,
persisted2265567->2265727; verificationprelive2265974,persisted2265951.
Resource/refusalalarmsOK,historicalclockalarmALARM. Diagnostic21:15CPUavg
52.095218->52.056995%,max52.573161->52.575919%;RAMavg3.031413->3.070747%,
max3.070068->3.204346%. Verificationpre21:15CPUavg51.638880%,max52.575919%,
RAMavg3.098551%,max3.204346%. Censuses show only caretaker95907, no34073 or
35175 survivor. No production mutations. Active candidate is local-only.

Verificationpost21:23:04live2266115,persisted2266111. Latest21:20CPUavg
51.731792%,max52.504170%;RAMavg3.151449%,max3.198242%. Diagnostic and
verification windows remain health observations, not causal AWSspeedup claims.

### FB-01p — bounded plane-by-aperture arithmetic

Continue same latency item after accepted FB-01o. Exact previous image hashes,
visibility/native/material tests remain unchanged. Only aperture numeric
evaluation and this ledger change. Body/DSF/cognition/world laws stay frozen.

Remaining source waste: every one-aperture visibility query constructs many
tiny array operations per plane; sliced events also evaluate every plane at
zero-width intervals created by clipped/duplicate boundaries. These intervals
provably have zero integral and were always discarded at final sum. No new
physical law is needed. Retain scalar math.hypot/atan2 per normal, compute them
once per call, and evaluate independent plane/aperture pairs in bounded arrays.
This replaces repeated Python dispatch, not equations or a numerical stencil.

Contract: same scalar formula/order for each pair, same normalized planes,
fixed roots, clip/sort order, strict lower/upper selection and first-plane tie
semantics. max_cells bounds each plane-by-aperture/interval matrix as well as
the original event matrices. Keep original K-derived event admission unchanged.
Only positive-width event intervals enter boundary selection; others retain
zero contribution. For positive/negative-nz planes take exact max/min geometric
boundaries; those extrema are the existing intersection law, not a DSF score
or heuristic selection. No semantic classification or posterior threshold.
All temporary arrays die with this read-only call. No extra observer, cache,
allocator dependency, state schema, live caller or startup/migration changes.

Acceptance remains9standalone geometry tests, exact two predecessor imageSHA,
same cold native observation/next-state bytes, actual slanted face/head movement,
independent area partition and resource refusals. Same pinned local numerical
runtime; unprofiled wall/RAM recorded. Independent frozen source review precedes
execution. No loose tolerance or scene simplification if byte witness fails.

FB-01p reviewPASS,b8c6d1e1c52525722a1943d11626abb77412d321b7eb4f74e48ed20a39d4769d,
no findings. PID36613/session26726exit0,9/9PASS,2.265stest,2.378142swall,
user2.350478s,system.039974s,peak80972KiB. Exactimagebytes preserved; initial
scene.382480028s,moved.288681361s. Singlebox7.37-8.39ms,sameerrors/coldproof.
This is still too slow for250ms totalclock; performancegate staysopen.

Remainder profile36990exit0,wall.658973s,user.658004s,system.016048s,
peak71852KiB,sameimageSHA. 412257calls,.513sprofileincludingretinal_apertures
construction(.064s,notpartofearlierframebenchmark); radiance.449s,
visibility.205s,220areaqueries. Dotextrema384calls/.199scumulative,mostof
retinal integration cost;17624clipsremain. First implementation's exclusion
short-circuit was replaced by full bounded plane blocks inFB-01p; cheap local
one-aperturequeries improved but the19k-aperture case computes planes on sites
alreadyexcluded. Preserve batched equation once, restore the smallercausal
frontier for multipleapertures. Rootcrossings still dispatch4callsperplaneper
batch despite sharing same aperture endpoints. These are next measured waste.

AWSpre21:26:38/post21:28:40(proof),pre21:28:40/post21:30:03(profile): same1549
solehealthy1/1/0,task478e055e5f0146789dd2ba0642bb578b,digestc883967dae9703796245db6408d12ec03a7591dbb48c8c0c4188bdc2d1a837b8.
Sameidentity,availabletrue,checkpoint/cleanupnull,durabilityblockedfalse;
live2266432->2266621,persisted2266399->2266591 atfirsttworeads.
Resource/refusalalarmsOK,historicalclockalarmALARM. Pre21:20CPUavg51.680055%,
max52.696888%;RAMavg3.153890%,max3.222656%;latest21:25RAMavg3.145345%,max3.186035%.
Post/profilingpre21:25CPUavg51.884236%,max52.618212%;RAMavg3.148736%,max3.186035%.
Censuses: no36613/36990 or A1survivor,caretaker95907untouched.

Profilepost21:30:03live2266745,persisted2266719;21:25CPUavg51.939882%,
max52.618212%;RAMavg3.158569%,max3.192139%. OpticssourceSHA
abf8513d2d628a7e3d1410a76dde3ea75ac150935b84a856a20d68c332273529.

### FB-01q — reached aperture frontier and packed latitude roots

One same local performance item; no new geometry law or body capability.
Restore exclusion short-circuiting for multi-aperture inputs while retaining
the single shared batched dot-extrema equation. A one-aperture domain has no
remaining-aperture frontier to compact, so all its planes use one matrix;
multiple apertures apply each plane to the surviving sites only. This is
execution layout, not a selection threshold. All matrices remain max_cells
bounded; original event admission remains fixed. Aperture endpoint trig computed
once per call. Selected indices preserve order. Scalar constants unchanged.

Compute all constant-latitude roots in one batch-by-plane-by-edge matrix.
Preserve n order, lower/uppermu order, negative/positive root order. Zero-radius
planes still emit aperture-start duplicates rather than roots; safe divide's
where mask avoids their undefined ratio. Same arccos/clipping/existence law,
same fixed-event/sort/integration arithmetic; no new epsilon or extrapolation.
Totalrootcells4*K*batch <= event_count*batch <= max_cells. Per-call only,
no output until completion, no state/retention/migration/live changes.

Authorization onlyoptics source+ledger; tests unchanged. Same9tests andexact
images/nonmutation/coldnext-state witnesses. Frozen review first, oneexecution
withhealthenvelope, measured cadence and residency. No production claim.

FB-01q source reviewPASS withno findings; fingerprint
032a9c82bad81e068e8111d06294811393141daf75c6c977d3d275b3de1b95b8
verifiedbyreviewerbefore/afterandbeforeexecution. PID38095/session28958exit0,
9/9PASSin1.996s,wholewall2.121008s,user2.072804s,system.064024s,peak89256KiB.
Both exactpredecessor imageSHAunchanged, retainednative/head/material/coldnext
proofsunchanged. Initial5-surface22-regionframe .297629732s; moved17-region
frame .242652590s. Original .867981043/.656413103s, so observed about2.7-2.9x
faster. Singlebox8.33-10.84ms remainswithinpreviousregime. Noimage/detail
reductionandnodeletedphysicalfeature. Slowestframe still>250msbeforewholebody,
so latencygateNOTclosed and fullbodyNOTdeployable. No further polishing claim.

OpticssourceSHA44b54e4f0da0ad6ad256b65dfc6b00a13665d93e6816d49b24ccc35520e466c0;
visibilitytestSHA67f89883ddbbb7568811c44a6e82dcaa01dd0980992187fddcce2919dff79184.
Preserved accepted commits814206710(FB-01o),bc258206d(FB-01p); all candidates
passedfrozenreviewandtheir unchangedgeometry/byteproofs, notexceptionpatches
toafailingrepresentation. No uncommittedworkfromG1wasmerged.

Read-onlyAWSpre21:32:31/post21:33:47: sole1549task478e055e5f0146789dd2ba0642bb578b,
RUNNING/HEALTHY,1/1/0,digestc883967dae9703796245db6408d12ec03a7591dbb48c8c0c4188bdc2d1a837b8;
sameidentity1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1,live2266975->2267092,
persisted2266943->2267071,availabletrue,checkpoint/cleanupnull,durabilityfalse.
Resource/refusalalarmsOK,historicalclockalarmALARM. Latest21:30CPUavg
51.024672->51.054786%,max51.443812->51.569362%;RAMavg3.163656->3.176541%,
max3.234863->3.240967%. Still-fillingmetricwindows,notcausalAWSspeedup.
NoA1harnesssurvivors;caretaker95907intact. No live writes or process interference.
No newG1immutablehandoffasof21:33; their sleep-windowplananddirtysourcepreserved.

Next exact action: measure remaining visibility-domain work versus full-retina
integration on this accepted code, then remove the dominant repeated work.
Do not call243msproof productionrealtime; do not broaden into newrendererfeatures,
alterbody/cognition,loosenbyte/accuracyacceptance, or startlivecutover. GoalACTIVE.

### FB-01r — share repeated boundary/aperture geometry within one frame

Previous turnPROGRESS,acceptedfea1260d9. Continue optics latency only. Existing
approved numerical optics is a body/environment approximation, not a reduced
DSF authority; canonical kernel/cognition untouched. No aperture/feature removal.

DiagnosticPID39560exit0,wall.821170s,user.795206s,system.039960s,peak73440KiB.
SameinitialnativeimageSHA d53a40d0d3e6d26ce2785e87cc6ff7b65bfcb3c807d3b443fcbdec094dbd1373.
Unprofiledvisibility.076058566s,retinalintegration.200721540s. Profiled
.117318238/.228339710s,168950calls,total.339sunderprofiler.220areaqueries;
493dot-extremaqueries,.120scumulative.22regionscarry295halfspacerows butonly
44distinctexactdirectedrows. Repeatedgeometricalqueriesacrossregionsaredominant
avoidablework. NewAPIbelow deletes those repeated computations rather than
retaining a cross-frame cache or changing numerical physics.

Contract/source map: `disjoint_surface_radiance` in functional_body_optics.py
accepts the already-derived tuple of disjoint directed plane arrays, one six-band
uniform radiance per region, and the existing receptor apertures. It normalizes
each row exactly as the old area call, interns identical normalized bit-patterns
for this call only, and retains each region's original row order/multiplicity.
Signed zeros remain distinct. Plane indices are transient geometric addresses,
not object identities, semantic descriptors, neural keys or memory.

For a bounded aperture block, compute each distinct plane's aperture extrema
once. Pack exact inside/outside booleans, combine them by geometric intersection
in each region, then call the SAME analytical boundary integrator for unresolved
apertures. Do not remove repeated constraints or events within that integrator:
event order and final summation order remain byte-comparable. Accumulate region
radiance in original order and divide by original aperture solid angle. No
clipping of image values or guessed ray samples. Old aperture_solid_angles API
delegates to the same internal preparation/classification/integration laws.

Bounds: max_halfspaces limits input/normalized rows and per-call plane addresses.
max_cells still limits each event/matrix buffer. Packed classification scratch
must be <=8*max_cells bytes (one float64 event-buffer equivalent); select an
aperture block by exact byte arithmetic 2*distinct_planes*ceil(block/8). With
more planes use smaller blocks, never remove a plane or site. Output is6*N
binary64 values; input/output/scratch are distinct. All local data die with the
call, no state schema/cache/checkpoint/world authority introduced. Refuse
invalid/nonfinite input or insufficient declared storage before image return.

Authorized files: optics source, existing visibility test/caller, sprintledger.
Standalone visibility test will use the new shared-radiance API so its same
native ray/head/coldnext-state and original image hashes cover the new path.
Add one bounded proof of shared-vs-independent area accumulation, small-block
equivalence and capacity refusal. All9existing geometric tests stay intact.
No ordinary/live caller yet; component timing never proves full-body cadence.
Independent frozen source review before imports/tests, sameAWS envelope/PID
accounting. No home/curved geometry, cognition or body/controller expansion.

FB-01r final source review passed at frozen candidate
3b7965c95d144aba2f9d80e2e7d98ef443327253bacc3a6d1c25e2f156286b39.
Initial review found one localized allocation-lifetime error: replacing packed
buffers can briefly retain old and new allocations. Corrected once, before any
candidate import/test: allocate both plane tables and both masks once, then fill
views in place. The literal packed-byte bound includes masks:
2*(distinct_planes+1)*ceil(block/8) <= 8*max_cells. No architecture findings.

PID42202/session49641 completed exit0:10/10 standalone tests passed in1.499s;
wholewall1.629923s,user1.573850s,system.071901s,peak93192KiB. No pytest or live
authority imports. Exact initial/moved image hashes remain unchanged:
d53a40d0d3e6d26ce2785e87cc6ff7b65bfcb3c807d3b443fcbdec094dbd1373,
b446fa182e541c378feacf12c85deb8005498902ca09ab223e07f28da6b5a2e8.
Same5-surface native frames now .144424262/.129808641s, versus predecessor
.297629732/.242652590s and original .867981043/.656413103s. New small-block
shared/independent array equality and bound/refusal checks pass. This measures
one optical component, not full-body or production cadence; no live deployment.
SourceSHA4b4685271b1d06123f3409b993c53f1675cb5f0435bf808cd2faa8af1590af4d;
testSHAf9839818f92afb5387de148a7c368ca2bcefa29fc137458460d078d8dea8434d.

Read-only AWS pre21:44:24/post21:48:04: sole1549task
478e055e5f0146789dd2ba0642bb578b RUNNING/HEALTHY,1/1/0,samec883967d...digest,
identity1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1. Live2268075->2268427,
persisted2268063->2268415,availabletrue,checkpoint/cleanupnull,durabilityfalse.
Resource/refusalalarmsOK; historicalclockalarm remainsALARM. Latest reported
windows21:39/21:43 CPUavg51.266595/51.856490%,max51.895673/52.579812%;
RAMavg3.234355/3.205872%,max3.289795/3.332520%. Not an AWS performance claim.
No A1 test/profile survivors; caretaker95907 and G1python39630 untouched.
Earlier diagnostic envelope21:36:24/21:39:13 also retained same1549 custody,
live2267330->2267590,persisted2267295->2267583,checkpoint/cleanupnull.

Goal ACTIVE. Optical component now fits250ms in this small scene, but complete
ordinary-loop/body/resource gate remains unproven. Next exact item: reconcile
the accepted optical primitive with the actual native-world surface/material
contract, keeping body mechanics and contact evidence authoritative. No claim
of full-home rendering, curved-surface correctness, cognition or live20/20.

### FB-01s — native primitive geometry transport for world optics

Previous turn PROGRESS: accepted7e403f6b6 preserves predecessor pixels and reduces
the measured component below250ms. Advance to native surface interface, not a
reopening of the closed planar integration law. Production baseline1549 remains
unchanged; G1's immutable5764bc8e0 is separate and not merged. Bootstrap still
rejects the absent historical HANDOFF_2026-07-31 file (known branch distinction,
not evidence of a new workspace): git verifies a1/guala-functional-body at the
explicit /workspaces/guala-functional-body root, with this sprint ledger.

Requested architecture: use actual native collision shapes and full head motion
for optical geometry, with no second world. Current reality: ray_geometry has
lawful revision-locked native queries; planar tests read selected box geometry
through private scratch. That selected test helper cannot become a complete
production scene. Conflict: no new conflicting mechanism will be extended;
full-world optical integration is incomplete. Canonical kernel/cognition and
ray collision laws remain unchanged. This is numerical geometry transport,
not DSF evaluation or a substituted field. No DSF structure is lost here.

Single next change/source map: NativeBody.optical_geometry authenticates current
native state through the existing restore, resolves the actual self-link frame
and local eye offset by the same helper used by ray_geometry, and returns packed
primitive types, native size parameters, centre positions and full rotations in
eye coordinates. Row index is a world-only transient native geometry address;
there are no semantic identifiers, colors, recognition flags or new sensation.
All native geometry participates, including self, static world and other actors.
Plane/sphere/capsule/ellipsoid/cylinder/box primitives are represented directly;
mesh/heightfield require their actual geometry and will refuse, never disappear.
Native plane size is retained as native metadata, not an invented finite plane.

EmbodimentWorldAuthority.native_optical_geometry holds the existing lock, rejects
hidden publication and stale revision, requires mounted state, then calls the
same scratch engine. No new owner, persistent schema, codec, migration, lock,
clock, motor policy or state commit. Failures can only alter reusable scratch;
authoritative native bytes/world revision stay unchanged. Fresh restore and
post-query next mechanical successor must be byte-identical. Outputs own their
buffers, are marked read-only, and never alias scratch. No retained frame cache.

Bounds: caller max_geoms admission precedes restore and output allocation;
packed output is N*(4+8*(3+3+9))=124*N bytes, plus fixed origin3 and rotation9
binary64 values. O(N) transform work and transient storage within that bound;
native fixed model and scratch remain the existing authority. No per-receptor
world copies, no per-ray wrapper calls. Entire primitive roster is necessary
geometry input at this boundary, not a brain/population scan. No approximation
to primitive shape introduced; binary64 transforms use approved body optics.

Acceptance: ordinary mounted-world query contains complete native roster;
geometry matches native witnesses before and after actual head effort; samples
do not mutate world or cold next successor; stale/missing/hidden/capacity and
unsupported-shape cases refuse; buffer bytes/ownership are explicit. Existing
geometry, body-custody and optics tests remain supporting gates. Backend-only
component, no API/UI or live vision claim. Later radiance consumer must retain
six-band world materials and handle curved surfaces; neither is asserted here.

Authorized source files: functional_body_native.py, embodiment_world.py;
test_functional_body_world.py and this ledger. Owner A1. Whole-file source
replacement, frozen independent review before import/test. No main-tree edits,
live actions or G1 process interference. Tests remain standalone, with read-only
AWS pre/post envelope, retained PID/session and terminal census.

FB-01s reviewed first at e381398b94968545a1b73303a77caf0d24ed6d223a5faca514ebe3c8363032c5.
No source architecture defect. Three localized proof gaps corrected in one
batch: call new API directly under hidden publication rather than failing in
the snapshot helper; compare mesh refusal with non-resetting _capture; check
moved geometry against actual native transforms as well as cold equality.
Final source review PASS at aef89143e90b0529e95077bb2858798596cf49a72cef302839ee9427b68d547f,
verified before/after review and before execution. No imports before review.

PID44952/session91971 exit0: all105 standalone checks passed in5.425s;
wholewall6.038159s,user5.939589s,system.112143s,peak170928KiB. Four decisive
new interface tests ran first. Existing native/body/energy/custody/optics and
earlier exact-physics supporting benches all passed. No test implies learned
locomotion, complete rendering or production integration. Native47-primitive
snapshot .000896519s,5828packedbytes plus96fixed numeric bytes; same19335ray
batch4.75–4.94ms, same exact optical scene images122–140ms. No comparison of
these component timings to complete live interval performance is warranted.

Native sourceSHA87fc3b65a9b8f105dd1a7dd8b244a67d90a314e37ba2618574816a2a183682bc;
worldSHA b170c502c4435240eeaf199e06bc1b605b872d39d2821bc78c363179186604ca;
testSHA ee31b72461edf5d359870cd970ef01340e3612f31eda61ef7bf22603a984da1f.

Read-only AWS pre21:56:58/post21:57:22: sole1549 task
478e055e5f0146789dd2ba0642bb578b,1/1/0,RUNNING/HEALTHY,digestc883967d...,
sameidentity1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1. Live2269255->2269296,
persisted2269247->2269279,availabletrue,checkpoint/cleanupnull,durabilityfalse.
Resource/refusalalarmsOK; historicalclockalarmALARM. Same latest21:52metric
window CPUavg51.277704%,max52.335438%;RAMavg3.356425%,max3.417969%.
NoA1harness survivors. G1python39630 andcaretaker95907 untouched. No live writes.

Next exact boundary: connect physical six-band materials and source charts to
this actual native geometry before ordinary retinal integration. Source trace
finds existing w1_physical_receptors._lit_surfaces_focal reconstructs yaw-only
legacy boxes/parts and a room-plane view; it cannot be reused as native geometry.
Its world reflectance/emission/ObjectOpticalSurface records remain physical
material inputs, not identities for cognition. Curved native surfaces must not
be omitted or replaced by centre samples. Full-home surface integration,
ordinary sensory/motor ports, coupled contact heat/feeding, paired commit,
copied-body/cold resource/rehearsal/live gates remain open. Goal ACTIVE.

### FB-01t — attach existing six-band material cells to physical planar charts

Previous turn PROGRESS:9966fa2d7,105 offline proofs. Continue the material
connection, not a new vision-resolution or cognition task. Requested architecture:
existing world reflectance/emission/palette cells remain fixed to actual surface
coordinates under head/object movement. Current reality: accepted visibility
preserves native planar charts, but integration caller supplies uniform bench
colors; ObjectOpticalSurface and source material fields exist in world custody.
Conflict: do not extend view-facing material reconstruction as native physics.
L0–L4, cognition, fixed actuator/body schema, production and G1 files unchanged.
This evaluates six-band optical geometry, not full DSF; no DSF projection is
substituted. Uniform illumination is an explicitly limited physical input, not
a claim that variable direct light, shadows or curved surfaces are completed.

Single change: functional_body_materials.planar_material_radiance accepts actual
PlanarSurface charts, transient PlanarMaterial declarations (six exact ppm
reflectance/emission bands, optional existing immutable ObjectOpticalSurface,
six nonnegative uniform incident irradiances), and the unchanged retinal angular
apertures. Printed rectangles use the physical chart [0,1]x[0,1], columns toward
+u and rows toward -v. Require that patterned surface really is that rectangle;
no guessing chart axes from viewpoint, texture dilation or shape labels.

Path: source material -> verified palette/physical chart -> existing complete
planar visibility partition -> intersect visible region with attached cell
halfspaces -> same disjoint_surface_radiance -> six-band mean radiance. For
cell c, L[c,b]=reflectance[c,b]/1e6*irradiance[b]+emission[b]/1e6. RLE merges only
consecutive identical palette indices within one physical row, an exact union;
never resample the pattern or pick a cell by receptor centre. Pattern cells are
not occluders. Visibility/depth executes once on original physical surfaces.
No color clipping/8-bit quantization here; receptor transduction remains later.

No state owner/cache or format migration. Inputs untouched, no world/organism
publication; failure yields no image. Cold repeat of same native chart/material
must return identical bytes and leave next mechanical state unchanged. Output
is N*6*8 bytes. Explicit max_sites,max_material_cells,max_halfspaces,max_work,
max_cells bound aperture count, declared texture inventory, expanded geometric
rows, visibility work and numeric matrices. Preflight texture count before
cell work; check halfspace count before allocating each intersection. Whole
work is bounded by declared source/pattern/aperture limits, never history.
No copied whole-image per cell, no persistent catalog or per-site Python codec.

Acceptance: use real ObjectOpticalSurface and native box full transforms;
nonuniform material survives head/object rotation with its original chart;
occluded marking is actually occluded; known constant/partition solid angles
agree; zero illumination removes reflection while emission survives; no scene
mutation and identical cold next mechanical successor; exact bounds refuse.
Full-scene curved optics and spatially varying illumination remain later gates,
not silently dropped features. Supporting component test cannot authorize live.

Authorized files: new functional_body_materials.py and standalone corresponding
test, this ledger only. A1 owner, independent frozen review before imports/tests,
AWS read-only envelope and process closure. Native/world source stays unchanged.

FB-01t source review PASS, no findings, frozen
37ad54fa745a939a813453154c0916933a89767d9cd2bea10702c4076bb6d3a6
verified before/after review and before execution. TestPID48104/session95388
completedexit0:14/14pass in2.389s;whole2.584878s,user2.540667s,system.060015s,
peak98336KiB. SourceSHA2b8a4b5e2bbb2277579bbfafb3d863b5003a3b67a44a1a8187c318afbb76ff91;
testSHA2c62f6bb44b2b845a11ed6d198f761d7da97f82f59ad25abe4dc58906c7e3a89.

Physical cell positions agree with independently placed planar cell extents;
opaque front surface hides the pattern; zero incident light removes reflection,
but emission remains. Exact repeated-column material representation yields the
same bytes after equal-index union. Full native head transforms, actual native
ray occlusion witnesses, nonmutation and fresh cold next-successor all pass.
Five-surface two-by-two pattern bench with19200focal apertures measured
.110813043s/.165914985s. This is NOT a dense-texture/full-home/full19335-site or
production timing proof. Existing optics exactimagehashes remain unchanged;
its original19335-site uniform-material frames .146254338/.132269421s.

AWS read-only pre22:08:30/post22:08:56: sole1549task
478e055e5f0146789dd2ba0642bb578b,RUNNING/HEALTHY,1/1/0,samec883967d...digest;
identity1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1,live2270387->2270436,
persisted2270367->2270431,availabletrue,checkpoint/cleanupnull,durabilityfalse.
Resource/refusalalarmsOK,historicalclockalarmALARM. Latest22:03CPUavg
50.709340->50.716908%,max51.218408->51.316790%;RAMavg3.259277->3.269450%,
max3.363037%. G1's caretaker nowPID47452(parent80744); G1 deployment script
tools/deploy_guala_her_room_layout.py PID47795 running at pre/post snapshots.
Neither was touched. A1 test terminal, no survivor. G1's deployment may change
the service after this snapshot; these samples are not a cutover completion.

GoalACTIVE. Next exact optical boundary is curved native geometry: existing
anatomy has spheres/capsules and cannot be rendered by omitting them, converting
them to billboards, or relabeling a centre sample as an aperture integral.
Use the accepted native primitive interface and approved bounded numerical
optics, with explicit error/work refusal. Native source/world material binding,
spatially varying lighting and full ordinary-body integration remain open;
no physical feature is deleted to fit the current component proof.

### FB-01u — curved-primitive numerical regime, outside production

Previous user-comment turn: no implementation progress; no scope change.
Continue FB-01g from accepted0f3a62d12. Single item: map conservative cone/depth
bounds for actual finite native primitives before selecting a curved-aperture
integration law. New file tools/guala_body_curved_optical_regime.py only, plus
this ledger. No native/body/cognition/schema edits, no new live interface.

Requested architecture: complete moving body geometry participates in sight,
under Joe's approved numerical optics, without centre-only sampling or omitted
self. Current reality: planar charts/materials proven; curved coverage is open.
Conflict: YES if planar-only or native point-ray misses were promoted as complete
retinal coverage. Do not extend those shortcuts. Full DSF is not evaluated here;
this is floating-point optical geometry, with no reduced DSF decision proxy.

Source-derived correction to the working hypothesis: MuJoCo3.3.7 engine_ray.c
ray_quad rejects discriminants below mjMINVAL; ray_plane uses its native
rendered rectangle and one-sided visibility. Thus mju_rayGeom misses cannot
serve as mathematical empty-cone certificates, and native ray witnesses do not
prove infinite collision-plane optical coverage. Exported plane sizes remain
unchanged; the eventual world-material binding must explicitly resolve physical
surface extent. This diagnostic handles finite primitives only and does not
silently discard a plane from a whole-scene claim.
Primary source: https://raw.githubusercontent.com/google-deepmind/mujoco/3.3.7/src/engine/engine_ray.c

Diagnostic law (float64 analytical bounds, NOT formal directed-rounding proof):
For aperture(hlo,hhi,mulo,muhi), dOmega=dh*dmu. d0 is its central unit direction;
epsilon is the maximum chord to its corners (dot is concave in mu and minimized
at a longitude edge). A primitive's possible hit distance is bounded by
T=norm(centre)+bounding_radius, tightened by each bounding-box slab whose ray
component keeps one sign over the aperture. Then delta=T*epsilon bounds ray
separation. Expanded primitive contains K+ball(delta); contracted primitive lies
inside K eroded by ball(delta). Central-ray solid entry into the expansion is
a lower first-hit bound; entry into a nonempty contraction before T is an
all-rays-hit upper bound. Sphere/capsule radii expand/contract; box half-extents
and cylinder radius/halfheight do likewise. Ellipsoid axes use homothety
1+/-delta/min_axis, NOT axes+/-delta (the latter is not a dilation enclosure).
Finite-shape ray intervals are derived from quadratic and slab inequalities;
no native miss/threshold becomes a certificate. Origin inside a solid explicitly
refuses this outside-eye diagnostic. Native point rays are independent sampled
witnesses only. Floating-point discrepancy is measured, not claimed impossible.

Bounded scene classification streams primitive bounds rather than retaining
Nsite*Ngeom results. A patch is resolved only when its all-hit upper depth is
strictly below all other possible lower depths; disjoint unknown patches remain
unknown. Constant six-band radiances are diagnostic emitters, not production
lighting. Unknown solid angle bounds radiance error; subdivision operates only
on unresolved patches. All patches of a receptor share one residual-error
budget. Explicit node/depth limits refuse, never omit geometry or publish a
partially converged image. No state, persistent cache, world mutation, cold
schema or downstream production consumer. Identical input repeats identically.

Regime: finite sphere/capsule/ellipsoid/cylinder/box, multiple sizes/rotations,
grazing apertures and sub-aperture silhouettes; compare interval classifications
to native sampled ray witnesses and independent analytic sphere coverage;
include the real articulated native roster, moved head and cold same state.
Measure rays/cells/time/peakRSS and interval error. This determines viability,
not a deployment gate. Source-only frozen review precedes execution; readonly
AWS envelope and process closure accompany run. Production optics not changed.

FB-01u first frozen review16b0014e6ebd32269b8b4687d834363747f3829db52258d7cb5112b18460a593:
three localized diagnostic findings, no architectural finding. One batch corrects
complete roster-array shapes (zip cannot truncate), confines optical-refusal
catch to integrate alone (cold/motor failures propagate), admits only finite
integer work/depth budgets and positive representable root/subpatch areas.
Four direct refusal checks added. No candidate execution before final review.
Native sampled witness tolerance1e-10m is explicitly diagnostic comparison only;
it is NOT adopted as a production accuracy guarantee or formal roundoff proof.

FB-01u final source review PASS, no remaining finding; frozen
789f9da389dd85115e6b33b26bed5a22670b9bf60602890a0ef4019b2ff58f5a
verified before/after review and before run. Diagnostic SHA256
9e841c64601622fbb56a6d54f8da6b44c8e947b2a0aa2ad11d370bdac146c679.
PID53712/session60008 terminalexit0;4.346007329s,peak201128KiB.
36,000 sampled native ray witnesses across5finite shapes,3distances,3rotations
showed0enclosure discrepancies at the disclosed comparison tolerance. Analytic
axis-centred sphere aperture fraction .19684288451874393 was bounded by computed
midpoint .19684600830078125 +/- .00115966796875;9893nodes,depth10. Four malformed
roster/budget/underflow requests refused as intended.

Full47-shape/19335-site scenes FAILED the declared resource acceptance: initial
refused after2.071052464s at149131visited +153600nextnodes,depth4; moved head
refused after2.115773669s at150491visited +145920nextnodes,depth4. Both exceed
262144node budget. These are correct refusal receipts, NOT passing renderer or
realtime proofs. Cold rendered-image/next-motor branch was NOT reached because
integration refused. No production law accepted from this measurement.

Bounded attribution probe (same reviewed source,PID54249/session32682,exit0):
initial dark-panel possible19335/all-hit14200/unresolved5135;
emissive-panel possible9675/all-hit0/unresolved9675; totalresolved7100,
unresolved12235. No other geometry had a possible forward hit in that initial
pose. Thus this full-roster scene does not prove a visible curved self-surface;
the independent shape sweep/sphere integral are the curved evidence. Neither
self exclusion nor an increased node budget is a remedy.

Exact next correction: the thin broad planar box faces are unnecessarily being
expanded/eroded as volumes. Use their existing native original PlanarSurface
charts, aperture halfspaces and inverse-depth plane: for each physical front
face, dot extrema bound t=1/(inverse[0] dot d); full-chart angular inclusion
proves all-hit, exclusion proves no hit. Stream their lower/all-hit upper depths
into the same visibility comparison. Reserve volumetric curved refinement for
curved primitives. No centre sampling, painter sort, new opacity threshold,
increased budget or law/state/cognition change. Next diagnostic must include a
native curved foreground object and small off-centre silhouette, not merely
the current body's out-of-view curved geometry. Preserve this unsuccessful
regime by commit before changing the diagnostic.

Read-only AWS pre22:28:19/post22:30:08/22:31:05: G1 now serves1551, sole task
99cf7c9e92e7480ea6e1fda7ab65d70b,1/1/0,RUNNING/HEALTHY,digest
05f9fe61d68a3a29077dd7b49c2434bc00e272bc68c7090f08fe057262fa9486.
Task1551 declares2048CPU/8192MiB,uvicorn lean_production_app single worker;
GUALA_PAIRED_ROOT=/app/guala/paired-current-gen2,maxworldbytes16777216.
Identityunchanged,live2272606->2272875->2273016,persisted2272591->2273007;
availabletrue,checkpoint/cleanupnull,durabilityfalse. Resource/refusalalarmsOK;
historicalclockalarmALARM. Latest22:26CPUavg51.476263878%,max52.169040561%;
RAMavg/max2.783203125%. Caretaker50841,G1retentionproof53618 andG1deploy54362
belong to main and were left untouched. Both A1 PIDs absent on final census.
This service observation is not A1 deployment approval or a G1 cutover audit.

GoalACTIVE. Curved optical integration remains open; accepted body/material
source unchanged. No contact/proprioceptive channel, live source or cognitive
mechanism changed. Full ordinary-loop, restart, performance and production
acceptance remain mandatory; diagnostic terminalexit0 is not their substitute.

### FB-01v — reuse planar settlement inside the finite-primitive regime

Previous turn PROGRESS:ab8b784b6 measured a failed full-scene work regime and
identified12235initial ambiguous apertures caused entirely by the two broad
thin box panels. Continue the same optical integration boundary. A1 edits only
the offline curved-regime tool and this ledger. Production source/state/schema,
native motion/contact, L0–L4 and cognition remain unchanged. This is reduced
numerical optical geometry only, not a DSF proxy or full-field cognition claim.

Contract: prepare each original visible box face using the accepted physical
PlanarSurface chart and full native transform, once per frame. Use existing
visible_planar_regions for planar-to-planar occlusion; no painter order or new
visibility engine. Existing disjoint_surface_radiance integrates the planar
field exactly under its accepted float64 law wherever curved-cone bounds prove
no curved primitive can participate. Else retain the reviewed curved-depth
comparison/refinement and error budget. Box-depth bounds use each original
face's inverse[0] dot d =1/t plus chart halfspace extrema, not expansion/erosion
of a thin volume. Partial faces give lower possible depth; a wholly included
face gives all-hit upper depth. Combine faces without semantic priority.

Prepare physical charts only once per optical call, not per refinement. Curved
primitives whose lower hit is infinite over the entire enclosing angular domain
cannot participate and need no per-site query; their geometric exclusion, not
an identity or arbitrary distance cap, is authoritative. Keep all originals
in admission and witness data. No cache, state, source identity or history is
retained between frames. Colours are still declared constant diagnostic emitters;
no material/lighting/production claim. No approximation of physical skin force.

Keep262144nodes/20depth,19335sites and1/510unit-radiance midpoint-error budget.
Reuse prior planar limits32768halfspaces/32768numericcells/1048576visibilitywork;
no enlarged bounds. New source cannot depend on a successful centre ray or
silently remove an unsupported shape. Cold/error branches unchanged. Failure
must still refuse, and cold/motor failures must still fail the whole harness.

Decisive measurement: original47-primitive frame must no longer spend refinement
on provably curve-free planar patches; compare its initial image to independent
analytic panel aperture coverage. Add actual native foreground sphere and a
sub-aperture off-centre sphere; prove native rays hit the former and the latter's
whole angular area is retained in a matching small-aperture analytic check.
Sweep previous shapes/rotations/distances, head movement and cold identical
image/next-mechanical-successor. Record per-frame time separately from cold.
No passing result alone authorizes production; full body integration staysopen.

FB-01v resumed after session interruption, frozen17fddeb8980e058f7a4c34ac2825e4e10dc42f0d573c8c48b3030e642240f187
verified before run. Source-only review passed. Session21741 exited1 at the
initial-panel analytic comparison; no cold/foreground results claimed. All
36000 sampled witnesses, sphere coverage and four refusal checks passed first.
The off-centre cap measured .02853393554687511 +/- .0016174316406249235 against
analytic .028495173787268745 (917 nodes). Original frame used19335nodes,depth0.

Read-only diagnosis:120 edge sites differed by at most5.356372012599309e-10.
Actual native panel edge .003939091417123564m differs from precompile ideal
.003939091423921181m by -6.797617156661939e-12m, due to representation of the
100000m finite panel. Actual corner angle .0020315038670628465 gives coverage
.6896090729407816, matching the renderer. This is a reference-scene mismatch,
not evidence permitting a looser rendering tolerance or changed geometry.

Requested architecture: keep the approved bounded numerical optical law.
Current code reality: the diagnostic compared compiled geometry to ideal input.
Conflict: yes, that reference compared different scenes. Single next correction:
derive independent analytic panel bounds from actual native box extents in this
tool only. Production renderer, body physics, cognitive ports and L0-L4 are not
extended. Reduced numerical optical geometry, not a DSF field evaluation;
six constant diagnostic radiances do not model variable physical illumination.
Keep the1e-10 comparison tolerance and every work/error limit unchanged.
The reference asserts its axis-aligned initial-bench domain, derives angular
coverage from original corners, and reports finite vertical-edge uncertainty.
No chart-solver reuse or image-derived expected values. Re-freeze and narrow
source-only review precede the same bounded run.

Readonly AWS00:48:52/00:51:00Z:1553,sole ec20ff084de54d48afab9a113647fa46,
1/1/0,RUNNING/HEALTHY,digest1d088eaaf195931a315e45c7ed456d4bb028210655e52eacad27e4445161612d.
Sameidentity,live2293574->2293940,persist2293545->2293929,availabletrue,
checkpoint/cleanupnull,durabilityfalse. Resource/refusalalarmsOK; historic
clockalarmALARM. CPUavg51.565219438/max52.063812315%,RAMavg2.779541015625%.
Unrelated caretaker35747 and nightly perception54872 left untouched. All A1
probe handles completed; no surviving A1 harness. Goal currentlyACTIVE per
fresh goal-tool read, no user approval outstanding. No production mutation.

Final narrow reference review PASS; fingerprint5c45fbfe671023df943bee90f09ea1b970a36e7ddd0a3785fba19cf28d186950
verified before/after source-only review and run. Tool SHA256
f1a98307c9f6165b17fc07f943da33c3321f7782f93b689c8efc1f12eb8dbf09.
Session75010 exited0,14.727781384s,peak159036KiB. Terminal0 means the regime
measurement completed, NOT that every scene passed. No A1 harness survivor.
Preflight found /usr/bin/time absent; used tool's existing monotonic time and
getrusage output, with no install or additional process. Native environment
/tmp/guala-body-native.pnUH8P/lib/python3.11/site-packages remains available.

36000 native sampled witnesses, analytic sphere and off-centre tiny cap, and
four malformed-request refusals passed. Original47geometry/19335site initial
and moved frames now finish with19335nodes,depth0,geometric residual0;
frame times .479088618/.757111240s. Independent native-extent panel comparison
passed. Both cold images/uncertainties are bit-identical and next native motor
successors match. No formal floating-point rounding certificate is claimed.

Actual49geometry foreground-sphere scenes STILL FAIL budget: initial
5.000668936s,165103visited+133264nextnodes,depth8; moved6.838832168s,
167111visited+124780nextnodes,depth8. No cold-image proof exists for refused
scenes. Even original-frame time exceeds250ms. This is not real-time or a
production-ready renderer; no body code or optical law was deployed.

Read-only AWS envelope00:57:42/00:59:44Z:1553 unchanged,sole task and digest
as above,1/1/0,RUNNING/HEALTHY,identity unchanged,live2295112->2295465,
persist2295081->2295433,availabletrue,checkpoint/cleanupnull,durabilityfalse.
Resource/refusalalarmsOK; pre-existing guala-clock-stalledALARM remains and is
not dismissed as proof of healthy clocking. Recent CPUavg51.28-51.60%,max52.10%;
RAMavg2.785-2.795%,max2.795%. Caretaker35747 untouched, no surviving A1harness.
These reads are observation only, not a production audit or cutover receipt.

Single next item stays the same curved optical work-bound failure. Source
review identifies exact sphere angular bounds as a tighter physical candidate:
a=dot(c,c)-r*r>0; q=c dot unitray; qmin/qmax from existing aperture dot extrema.
Forward hit iff q>=sqrt(a); entry t(q)=a/(q+sqrt(q*q-a)) decreases with q.
Use t(qmax) as possible lower entry and t(qmin) as all-ray upper entry, with
infinity when each respective hit condition fails. No radius-inflation loss,
new threshold, extra nodes or missing sub-aperture silhouette. Before claiming
this solves the measured case, instrument the last admitted frontier to count
which primitives remain ambiguous and how many patches this tightens. This is
the next diagnostic proposal, NOT a mounted physical law or measured fix.
Full body integration/restart/performance/live gates remain open; goalACTIVE.

### FB-01w — direct sphere angular bounds, same optical budget

Continue the same bounded numerical-optics failure, predecessor81ab0cf69
preserves FB-01v failure. Requested architecture: complete native geometry,
bounded optical integration without hidden surface omission. Current reality:
general cone radius inflation/erosion admits excess ambiguity for spheres;
full49primitive test still refuses. Conflict: yes, resource acceptance not met.
Do not extend budgets, tolerances, cognition, L0-L4, production renderer or
world custody. Single next item: the derived sphere entry extrema above.
Reduced numerical geometry with constant diagnostic radiances only; no DSF
field reduction/decision claim, no variable lighting claim.

Impact map is exclusively entry_bounds->prepare_scene/classify->integrate in
the offline tool. Same native geometry inputs; no persistent state, cache,
schema, new authority or production consumer. Sphere rotation has no effect
on sphere geometry; all other shapes preserve the reviewed law. Forward hit
threshold sqrt(a) is the sphere tangent, not an authored tolerance. Existing
outside-eye restriction applies. Low/high reciprocal entry bounds converge
with aperture refinement; no sampled hit declares an entire patch resolved.
Conservation role is unchanged aperture solid-angle radiance integration.
All fallible work is local; refusal returns no image and cannot mutate native
state. Cold image and next motor successor checks remain the same.

Before interpreting performance, compare admitted unresolved-frontier counts
against predecessor in the same scene. The ordinary diagnostic includes the
native sampled witness sweep, analytic full/tiny sphere area, native panel,
complete49shape scenes, moved eye and cold branch. Keep262144nodes/20depth,
1/510error and1e-10diagnostic comparison tolerance. Source-only review before
execution. A passing numerical regime is not live delivery or a proof of250ms.

FB-01w frozen source review PASS; fingerprint4a8b0759859148394969e6bff214d56e6b4bbd01404f75be58f053b2a717d82c
verified before/after review and both executions. Tool SHA256
146b532a56b85633128c748f5b3e8a4e428f5ee99e4d76a4a22982b11e2c6137.
Predecessor attribution session55264 exited0,8.945528106s,peak131708KiB.
Executed reviewed81ab0cf69 diagnostic from git in memory, observed classification
without changing its return values/physics; reproduced exactly165103visited+
133264nextnodes refusal atdepth8. At that last admitted frontier,35674patches
were unresolved; direct sphere bounds leave29982. Newly certified patches:
coarse76,wide146,focal5470. Every remaining patch has curved-foreground possible
but no all-hit certificate; dark-panel covers all29982, emissive-panel possibly
covers28240/all-hit28210. This isolates the actual silhouette rather than other
body geometry. No synthetic organism state or world authority was involved.

Same ordinary regime session6026 exited0,32.669127744s,peak187916KiB.
All36000sampled witnesses, analytic sphere/tiny-cap integrals and4refusals pass.
Analytic sphere .19684288451874393 is inside .19684600830078125 +/- .00196075439453125
(4197nodes,depth9); tinycap .028495173787268745 is inside .02865600585937509 +/-
.0014953613281249378 (821nodes). Original47shape initial/moved frames19335nodes,
depth0,times .528889714/.887187350s,geometric residual0.

Both49shape actual curved scenes NOW FINISH within unchanged262144node budget:
initial246963nodes,depth9,6.766402427s; moved238767nodes,depth9,8.394075765s;
maximum absolute six-band midpoint error bound .0019531250000000026 (<1/510).
Both complete cold bit-identical image/uncertainty and next native motor
successor proofs, as do original scenes. No native state mutation by rendering.
All four frame times still FAIL250ms; no real-time or deployment claim.

ReadonlyAWS01:24:27/01:27:25Z:1553sole1/1/0,RUNNING/HEALTHY,same task/digest/
identity,live2299779->2300288,persist2299753->2300265,availabletrue,
checkpoint/cleanupnull,durabilityfalse. CPUavg51.577->51.811%,max52.309%;
RAMavg2.795->2.812%,max2.820%. Resource/refusalalarmsOK, existingclockalarmALARM.
Caretaker35747 untouched; both A1 sessions exited and final census has no A1
harness. No AWS writes. GoalACTIVE, Joe explicitly pressed resume.

Next same optical boundary: settle the curved silhouette area without quadtree
growth along its entire perimeter. Investigate analytical intersection of the
sphere's angular cap with the existing aperture/planar halfspaces; preserve
front-to-back physical visibility, finite shapes, sub-aperture coverage and
declared numerical error. Do not increase limits or hide a slower full frame.
This remains offline numerical optics; body integration/live proof stays open.

### FB-01x — integrate spherical silhouettes by boundary events

Previous turn PROGRESS:dc769bbcd completes fixed-budget curved images/cold
continuation, but6.8-8.4s fails250ms. Continue, not reopen, same optical boundary.
Requested architecture: complete native geometry with bounded numerical optical
area, preserved physical visibility and unchanged error/work ceilings. Current
code uses quadtree area uncertainty along the entire sphere perimeter. Conflict:
yes, speed acceptance unmet. No production mechanism, body law, DSF, cognition,
persistent state, schema or deployment changes. Reduced numerical optics only;
constant diagnostic emitter bands still omit variable physical illumination.
Single next item: analytical cap/aperture intersection in the offline regime.

Authorized files: tools/guala_body_sphere_cap.py (new diagnostic helper),
tools/guala_body_curved_optical_regime.py and this ledger. One implementation
owner A1; mathematical source review agreed the primitive before code. Reuse
existing longitude-event integration, not reconstructed vertices or general
topology bookkeeping. For c/r, n=c/|c|,s=r/|c|,k=sqrt(1-s*s),sphere silhouette is
n dot d>=k. Prove horizontal A=nx cosh+ny sinh>0 across each admitted patch;
other cases retain existing conservative geometry, not a centre-ray estimate.
D=A*A+nz*nz, y=hypot(nx,ny)*sin(h-phi). Mu roots=(k*nz +/- A*sqrt(D-k*k))/D.
Concavity makes one allowed interval. Lower=-1 if nz<=-k; upper=1 if nz>=k,
otherwise use the respective roots (avoid extraneous squared roots).

With eta=s*s/(1+k), Q=sqrt((s-|y|)*(s+|y|)), primitive F+/-=k*alpha +/- J:
alpha=atan2(nz*sin(u),cos(u)); J=atan2(eta*y*Q,Q*Q+k*y*y)+eta*atan2(k*y,Q).
dF/dh is the corresponding mu boundary. Use angle differences for delta-alpha;
when both cap bounds own the slab use2*delta-J directly. Events cover existing
plane-plane/vertical/latitude crossings plus cap-plane, cap-latitude and cap
longitude tangencies. Midpoints select a proven unchanged boundary branch
between all events; they are NOT samples substituted for pixel integration.
No visibility epsilon. Event/float domain uncertainty refuses instead of
guessing topology. Exact-form float64, not a directed-rounding certificate.

Visibility: apply cap settlement only to a patch with exactly one possible
curved primitive, that primitive a sphere, and every possible box entry
strictly farther than sqrt(|c|^2-r^2), the maximum forward sphere entry.
The sphere need not hit the whole patch. Integrate sphere cap area, subtract
its intersections with existing disjoint visible planar regions, and add
sphere radiance on that same angular area. Other geometry retains the reviewed
depth/refinement path. Never add overlapping cap contributions or assume a
depth order. Pure-planar patches do not need box-depth tests a second time;
compute curved participation first and visit box depths only on reached sites.

No retained frame/cache/world identity. All arrays/work are local and bounded
by existing32768event-cell/halfspace and262144node/20depth limits. Same1/510
residual budget and numerical comparison tolerance. Any failure publishes no
image or native successor. Acceptance: independent analytic whole/half/tiny
cap, split-aperture additivity, former interval image containment, original and
curved native scenes, moved head, cold exact image/next motor, runtime/peakRAM.
Source-only frozen review then readonlyAWS-envelope execution; no live claim.

First frozen10520ca263ba1c2b7400b4d5d30b296c320125622eb34c20976aefae75a7f427
source review found three localized groups, no architectural defect. One batch:
admit normal count/event bound before allocating normalized planes; shared
sphere-parameter arithmetic admission before scene culling and direct cap
classification (finite squared distance/radius/offset,0<a<c²,0<s<1,0<k<1);
and replace predecessor overlap checks with actual interval-subset assertions.
Unrepresentable tangency refuses rather than inventing zero coverage. Add two
direct pre-cull refusal cases for under-resolved/overflow sphere geometry.
No comparison tolerance, physical budget, visibility law or production change.

Final source review PASS on d82fcff754d6be9f5f7ddc2104c22e1b38d02c82bee86dcb221ea6b41f894c7d,
verified before/after review and run. Session47804 exited1 at half-cap proof:
"cap event resolution exhausted". Prior36000 native witnesses/six admission
refusals pass; full sphere measured .19684288451874438 vs .19684288451874393,
tiny cap .02849517378726875 vs .028495173787268745, each settled in ONE node
with no residual geometric area. No full-scene/cold/performance claim yet.

Focused same-source read-only probe exited0: the tilted half-cap test computed
one vertical boundary at .07130746478529026 via its original normal and again
at .07130746478529033/.07130746478529035 via cap intersection 3-D points;
the tiny-cap half test similarly produced .04097704947678782/.040977049476787826.
These are duplicate mathematical longitudes, not distinct physical regions.
Correction deletes the redundant cap-plane longitude computation for vertical
planes (their original events already cover it), and skips plane-pair polar/
zero-vector intersections which have no longitude in this non-polar domain.
No merging epsilon or weakened resolution guard. Same exact event law, no
geometry approximation/visibility change. Narrow frozen source check precedes
the same run. This is the first causal test failure, not a new workstream.

Narrow vertical-event review PASS on7a1c2e3e800c89465dc90543e945fef4a6247e71f0214f22499a33419a90d025.
Session97627 exited0 as diagnostic measurement, not complete acceptance:
36000rays,sixrefusals,ninewhole/half/partitioncap laws pass. Original47shape
frames pass cold/nextmotor, .418846812/.527195396s. Curved initial refused
"cap area outside physical aperture"; moved refused event resolution.

Same-source probe session30936 exited0 and isolates two numerical/work-domain
issues. Initial plane-region overlap area=-6.61744490042422e-24sr for aperture
1.070912970647579e-05sr (relative -6.18e-19); all four computed spans are zero
except that signed cancellation. Adopt the SAME geometric range projection
already accepted in functional_body_optics._integrate_apertures, bounded by
zero and the physical support aperture area. No epsilon/error-budget change.
The independent predecessor containment gate stays mandatory and unchanged.

Moved tiny-cap support is[-.1815166871518814,-.18043641249286013]rad, while
the failing near-duplicate plane events are around-.227697675587192rad,
strictly outside that support. Intersect each partial aperture with its
analytically derived cap-longitude support BEFORE collecting/evaluating plane
events. A>0 proves the relevant branch; when s<R the support is phi+/-asin(s/R),
otherwise the whole admitted forward longitude domain. This deletes work
where the physical cap contributes identically zero; not an angular tolerance,
feature deletion or topology guess. Keep resolution refusal for relevant
events. Frozen source-only review before the same proof; no production edit.

d1c43de47dc3e1daf7e378de25c0e98a59d44df9200778902b1913044c977824 passed
source review. Diagnostic session27982 exited0,4.332886s,92176KiB peakRSS;
36000 sampled ray witnesses,6 refusals,9 cap laws pass. Original47shape
initial/moved .432785/.503143s,19335nodes/depth0,cold/nextmotor exact.
Curved49shape moved .737105s,19339nodes/depth1,cold/nextmotor exact; initial
still refuses cap-event resolution. Not full acceptance or250ms compliance.
Minimal initial probe: support[-.1770116369288958,-.17593128650107645],
endpoint slab[-.17593128650107648,-.17593128650107645] has no representable
midpoint. Its entire possible area is1.436734315421577e-17sr within a
.18068978015626763sr receptor. This is numerical resolution, not visibility.

Bounded numerical correction: return cap-area midpoint and explicit radius.
For an event span without a representable interior, enclose its contribution
in[0,width*(hi-lo)] and evaluate no guessed boundary owner. Carry positive
cap radiance AND subtracted overlap radiance uncertainties using absolute
coefficients; sum with existing unresolved geometric coverage in the SAME
1/510 receptor budget. Refuse if numerical uncertainty alone exceeds that
budget. No tolerance change, frame sampling, increased work budget, geometry
removal or production edit. Float64 analytic rounding remains covered only by
the unchanged comparison tolerance, not a directed-rounding proof claim.
The same cap laws, predecessor interval containment, cold/restart/nextmotor
checks remain. Source-only frozen review precedes isolated execution.
Read-only AWS envelope01:59:19Z: sole1553/ec20ff taskHEALTHY,live2305985,
persist2305961,no checkpoint/cleanup/block errors; clock-stalledALARM remains,
other Guala resource/refusal alarmsOK;CPU51.27%,RAM2.832%;caretaker35747.
No live writes/signals or diagnostic survivors; current goal remains active.

Frozen2f041c991715f2a05e60b7032731eab066ee3a9decb117a924899c75881c115d
passed independent source review. Session62549 exited1 at predecessor interval
subset assertion. All9cap laws/sixrefusals/36000native witnesses pass; original
frames .257505/.345162s,cold/nextmotor exact. Probe96399 finds only3 nonnested
roots(13,72,90),all with residual quadtree coverage. NO disjoint intervals
beyond1.44e-19 roundoff; e.g root72 new .7160729902+/-.001953125,
prior .7147684241+/-.001493454. Independent reviewer acknowledges earlier
subset recommendation assumed fully analytic results. Independently stopped
adaptive bounds need not nest. This failure is preserved, not called a pass.

Proof correction: expose existing unresolved area fraction (no new retained
state), preserve exact subset check wherever it is zero. For only nonnested
mixed roots, require an independent predecessor reference at error/16 to fit
INSIDE the candidate interval, unchanged node/depth ceilings. Mere overlap is
not accepted. Refusal or inconclusive comparison remains nonacceptance.
No reference participates in runtime decisions or modifies rendering output.

Same-source read-only profile of original scene: .377s including profiler,
classify .230s,prepare_scene .104s,visibility .088s. Apply reviewed strict
impossible-face exclusion before visibility pair work: all native geometry
and original face construction/admission retained; charge original halfspace
residency before filtering; retain boxes[i] for curved-depth work. Exclude a
face from optical pair work only when a physical halfspace's maximum dot over
the enclosing aperture is strictly negative. Such a face can neither emit nor
block any admitted ray. Preserve order/material indices. No tolerance, self
exclusion, geometry replacement, persistent cache or increased budget. Exact
next item remains this same isolated optics proof, not production deployment.
Read-only02:03:44/02:05:00Z: same1553solehealthy1/1/0,live2306787->2307015,
persist2306761->2306985,identityunchanged,errorsnull,durabilityfalse; existing
clockALARM/resourcealarmsOK. Caretaker35747 untouched. An unrelated existing
tools/ch3_recovery_engine.py process96993 appeared; not signaled or modified.

Frozen05a8fef6c7313393c3f0951aafb2f76625e4f2b9daf3fedfeb585875dd26dd00
passed independent source review and unchanged verification. Session99478
exited0 in8.967355s,180672KiB peakRSS INCLUDING independent predecessor and
cold copies. 36000native sampled witnesses,6refusals,9analyticcap laws pass.
Original47shape initial/moved:19335nodes,depth0,.253689/.316546s,zero geometric
bound. Curved49shape initial:19531nodes,depth6,.504229s,maxbound.001953125;
moved:19339nodes,depth1,.449104s,maxbound0. The3mixed reference intervals at
error/16 fit inside candidate intervals under unchanged work/depth ceilings.
Fully resolved analytic roots fit predecessor intervals. Every scene/pose
passes exact cold image,uncertainty,residual and next native motor successor.
This closes the diagnostic comparison failure, NOT250ms/performance/live
acceptance. All source bodies, eyes and native geometry remain admitted.

Next same optics speed item: current classifier still applies costly convex
solid equations to every aperture for every potentially participating curved
shape. Derive a conservative enclosing-sphere angular rejection BEFORE those
equations: any ray missing that sphere necessarily misses its contained native
solid. Strict geometric exclusion only; eye-inside/enclosure uncertainty must
retain original work. No source edit yet. Profile identified classifier .230s
of .377s; removed planar-pair work alone did not meet250ms. No larger work
limits, tolerance changes, semantic exclusions, learned-state or clock changes.
GoalACTIVE, same objective and full integration gates remain open.

FB-01x same-item speed correction, after accepted comparison commit2d932830d.
Requested architecture: same bounded numerical native optics/body precursor.
Current code reality: .45-.50s curved frames; full-aperture solid interval work
dominates classifier. Conflict with requested architecture:no;250ms gate unmet.
Will not extend: kernel/cognition,semantic exclusions,larger budgets,sampling,
persistent cache,production/world/body authority. Single next item: exact
enclosing-sphere angular rejection before expensive convex interval equations.
This is reduced numerical optics, not evaluation/flattening of DSF fields.

Existing radii() gives a containing sphere: capsule radius+halfshaft,cylinder
hypot(radius,halfheight),ellipsoid largest axis. For finite a=|c|²-R²>0,
a forward ray can intersect that sphere only if c dot d>=sqrt(a). Original
whole-aperture dot maximum<sqrt(a) therefore proves NO physical solid hit.
Preserve tangent/uncertain rows and original shape admission. Eye-inside or
nonfinite enclosing offset retains the original equations on all rows. Execute
unchanged expanded/contracted native interval bounds only on remaining rows;
scatter to original order with infinity for proven misses. No approximation
of the retained shape or new geometry. Same witnesses/cap/reference/cold gates,
same resource ceilings. Frozen source review required before the next run.

Frozen c41e170a0fa8f3b2c08ec421de177a61b788bbd052336576ff92c2d382e5c434
passed source review and unchanged verification. Session60924 exit0,7.041545s,
176628KiB peakRSS including reference/cold. All prior witnesses,analytic,
admission,3mixed independent reference and cold/nextmotor checks PASS.
Original frames .074787/.095600s; curved frames .281891/.224253s. Initial
curved case still misses250ms: not a complete speed or production gate pass.
Same-source profile isolates remaining cost in cap_solid_angles:48calls,
.303s of .479s instrumented; classifier .027s,prepare_scene .063s.

Next localized speed correction uses existing exact halfspace extrema, one
plane at a time to bound temporary arrays. Any original plane maximum<0 proves
empty intersection for that aperture. All minima>=0 proves ALL planar
constraints redundant there. Fullcap+admittedplanes returns aperture area;
partialcap+admittedplanes uses the same cap integral with empty plane list,
one-level recursion terminating at count0. Actual boundary-crossing apertures
retain existing event/ownership integration. No numerical threshold,sampling,
newcache,increased error/work budget,geometry substitution or cognition change.
This eliminates irrelevant plane events, not visible physical features. Same
independent geometry/cold/performance proof after frozen source review.

Frozen4bc9b533752011c0e2dead56983864349544ce82b87e83e281d6d16f0ff34584
source review PASS,unchanged verification. Session31483 exit0,6.947658s,
181396KiB peakRSS INCLUDING older independent reference/cold copies. All36000
sampledwitnesses,6refusals,9analyticlaws,analytic interval containment,3mixed
finer-reference proofs and exact cold image/radius/residual/nextmotor PASS.
Measured frames: original .087044/.110781s; curved .170814/.247080s.
The latter is near the250ms boundary; one sample is not a latency guarantee.

Bounded same-source repeat probe93754 exit0:5 renders each of the same4 native
scene/pose states,20total; no retained cache or state advance. Every repeated
image/radius/residual bit-identical. Original initial min/max .070683/.086267s,
moved .088368/.103656s. Curved initial .186660/.201550s,moved .169590/.189801s.
PeakRSS87472KiB without predecessor/cold copies. All20measured render samples
under250ms; this closes only the offline finite-geometry diagnostic latency
witness, not whole-body/live throughput, variable illumination or general-case
worst-time guarantee. No actor/world/cognition/kernel/production code changes.

Read-only02:16:11/02:18:04Z:same1553solehealthyec20ff,digest unchanged,1/1/0,
live2309031->2309367,persist2309001->2309353,identityunchanged,availabletrue,
checkpoint/cleanupnull,durabilityfalse;clock-stalledALARM remains disclosed,
resource/refusalalarmsOK,CPU51.4-51.5%,RAM2.832%;caretaker35747 untouched.
All A1 runs have terminal receipts; no surviving diagnostic or live mutation.

Progress classification: substantive bounded progress; FB-01x analytic curved
visibility now meets its offline comparison/restart/performance witness.
Next exact item: map this verified native visibility operator to the existing
body optical material/illumination boundary, preserving whole native geometry
and receptor aperture integration. Inspect that seam before an integration
edit; no new cognitive/perceptual identity model, no source exclusion shortcut.
Full native-home,contact/conduction/oral,sensory/motor,paired-state,cold/live
gates remain open. GoalACTIVE; Joe's bedtime message adds no missing approval.
