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
