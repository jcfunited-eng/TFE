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

### FB-01y — one native visibility/material aperture operator

Previous turn PROGRESS:5b4815390,FB-01x diagnostic closed by source review,
analytic/native/cold proof and20renders below250ms. Advance the same optical
connection; do not reopen the accepted geometry law. Production baseline1553,
sameec20ff task remains independent. GoalACTIVE,whole body not complete.
Requested architecture: native geometry and fixed physical material charts
produce six-band receptor-aperture means under full head transforms. Current
reality: native visibility and planar material integration are separate tested
components; neither is ordinary-loop mounted. ConflictYES if old view-facing
textures/upright-root reconstruction were reused. Those are not extended.
Do not modify cognition,L0-L4,world/native schemas,body motion,UI or production.
Single exact item: join the accepted material-cell law to native visibility.
Reduced numerical optics only; uniform incident irradiance per declared
surface remains an explicit limitation. No DSF field projection/substitution.

Source/ownership: A1 alone edits functional_body_renderer.py and
functional_body_sphere_cap.py (move reviewed laws out of tools, not copies),
functional_body_materials.py (one shared post-visibility material composer),
tools/guala_body_curved_optical_regime.py (driver only), focused standalone
test and this ledger. Independent review has accepted the contract boundaries;
freeze/source review must precede any import/test. No retained optical state,
second scene,authority,receipt,cache,controller,or schema migration.

Input: complete authenticated native geometry snapshot,one typed existing
PlanarMaterial per native primitive,explicit optional box-face overrides
(native row,local axis,side,material),retinal apertures and finite work bounds.
Base/curved patterns refuse: no guessed sphere chart. Duplicate/invalid face
addresses and hidden oversized patterns refuse before culling. Fixed face UV
uses original box local axes and unitrectangle; it never follows gaze.
Physical radiance=L=rho*incident+emission without clipping. Black surfaces
remain opaque. Derived nonfinite values refuse. Existing palette/RLE law
executes ONCE after original surface visibility, shared with planar caller.
Resolved box patches use material-cell integration,not constant base color.
Curved-cap subtraction uses the same material cells. Every residual bound
includes palette/override/emission peaks; no base-only error understatement.

Output: existing bounded six-band midpoint,explicit uncertainty,local work and
unresolved fraction; no physical/cognitive state mutation. Failure returns no
image. Cold proof restores native geometry AND identical external material
inputs; native bytes alone do not serialize these inputs. Actual world-custody
material binding,spatially varying lighting,ordinary-loop mount and full paired
body/world publication remain required later gates,not claimed by this module.

Acceptance: retain existing geometry/refusal/independent-reference/cold proofs;
uniform-material path reproduces prior values; actual attached palette remains
on original native box under head and common rigid transforms; native sphere
occludes its patterned backdrop; zero illumination removes reflection while
emission survives; palette peaks enter bounds even above1; bad/duplicate/
curved/hidden oversized material requests refuse; next physical successor and
cold image/error unchanged; bounded timing/RAM and no process survivors.
No pytest/conftest/network writes or production authority construction.

Known bootstrap recurrence: require-guala-root expects removed historical
HANDOFF_2026-07-31 file and fails on this modern body branch,as FB-01s recorded.
The Sept05 parsimony document is also absent here. Do not retry those absent
paths or fabricate authority documents; use current user approvals,skills,
AGENTS.md,explicit git worktree/branch and this durable ledger. Preflight file
existence before optional historical reads. No architectural authority changed.

FB-01y verification receipt — 2026-09-26 02:49Z.
Frozen9b04bb review found one localized overflow-domain defect. Batched source
correction refuses nonfinite cap composition, accumulated radiance and final
image/radius; no clipping or relaxed error. Final source reviewe07b1e PASS.
Initial standalone session21620:7PASS/1fixtureERROR; ObjectOpticalSurface
correctly rejected unused palette colors before renderer invocation. Failure
retained; no renderer workaround. Test-only correction uses real white/black
halves and analytical incident*(.5-shadow)+emission*(1-shadow); all original
accuracy/resource assertions preserved. Narrow independent confirmation PASS.
Final exact fingerprint9fd3ef0f0c273c769c530bfc7ee1c95fd1c8c227a64b87f7df057c507b9aac3e
verified again after all executions, before releasing freeze for this receipt.

Standalone session86821 terminal0:8native-material checks PASS,1.675041s,
91584KiB peak;48nativegeoms,19335sites,painted/sphere frame.106221s. Fixed
physical-chart independent reference, real head torque/motion, common world
rigid transform, cold image/error/residual and nextmotor successor, darkness,
emission>1,no clipping, cylinder analytical shadow/residual palette peak,
hidden-invalid/budget refusal,finite-input intermediate overflow refusal PASS.
Existing planar material suite58763 terminal0:4PASS1.103s;frame.129/.187s.
Geometry diagnostic71196 terminal0:36000native sampled witnesses,6refusals,
9analytic cap laws,exact predecessor containment and3mixed finer-reference
roots,cold physical successor PASS;19335sites original47geom.0775/.0872s,
curved49geom.1913/.1582s. Full diagnostic7.397524s,183832KiB includes retained
predecessor reference and cold instances. No production timing claim.

Read-only before/after02:45:25/02:49:10Z same1553/ec20ff sole task,digest1d088e...
counts1/1/0,live2314314->2314991,persist2314281->2314985,identityunchanged,
availabletrue,checkpoint/cleanupnull,durabilityfalse. ExistingclockALARM still
raised;CPU/RAM/storage/refusalalarmsOK,CPUavg51.5%,RAM2.84%. Caretaker35747
untouched. Every A1 diagnostic session terminal,no survivors,no network writes.
G1 diagnostic processes were observed independently and never signalled.

Outcome: native material/visibility seam demonstrated offline,one composer/
one geometry law,no duplicate scene/state. Full goalACTIVE. Next exact item:
bind actual world-owned materials and illumination to this native operator;
inspect the existing authority boundary before authoring. Variable illumination,
actual native home/caregiver/object/contact/oral integration,ordinary motor/
sensory mount,paired publication and final restart/release gates remain open.
No interim Slack retry after prior denial; not overall task completion.

### FB-01z — current world material sources on mounted native geometry

Continue from accepted076e0a7c5; no reopening FB-01y. Single deliverable is
same-state source custody, not variable-light integration or a live renderer.
Production1553 is unchanged. One implementation owner A1. Authorized files:
new functional_body_optical_sources.py, NativeWorldMount/scratch/query seams in
embodiment_world.py, standalone test_functional_body_optical_sources.py, this
ledger. No cognition, kernel, motion, actor, caretaker or production changes.

Requested: existing world material state on actual native surfaces. Reality:
mount maps entity frames but no material source; renderer accepts external
material tuples. ConflictYES for guessed colors, view-facing charts, ambient
substitution or wall-clock sunlight. Those paths will not be extended. This is
approved numerical body optics/world-only I/O, not DSF evaluation/reduction.
Next exact change: explicit immutable native-geometry material source addresses
and a read-only source view paired under the existing world lock.

Contract: mount.v2 adds canonical geom->(object/part/region/body,source,index)
bindings and explicitly declared uniform six-band body coatings, stored once
per body. Existing v1 encoding remains byte-identical and cannot supply the new
source view. No default coating, material-name inference or inferred front face.
Compiled geometry addresses/subtree membership derive once from native anatomy;
all geometry including static/self must be covered, with no duplicate/wrong
owner. Object/part native primitive kind must agree with the authoritative
material source. Actual object box patterns apply to all six original local
faces, preserving existing box law; curved/assembled patterned charts refuse.
Region looks preserve original world-coordinate subrectangles and tuple order
(source is FIRST-match, not last-match); no stretching to a complete wall.

Input: published full world (not horizon-filtered observation), current native
integration bytes/mount, receptor frame/offset, expected revision, finite geom
and material-cell budgets. Output: transient native geometry plus immutable
references to current reflectance/emission/patterns/region looks, regions and
each emitting object ONCE. Source addresses never enter organism senses.
Material references are not a second retained scene, palette or color cache.
All fallible resolution/native projection precedes return; query never mutates
world state/time. Existing world HMAC/atomic prepare/commit/rollback/restore
covers mount.v2. Cold instances compile the same source addresses; each read
resolves successor materials anew. No optical receipts/digests/history.

Lighting boundary: solar_sun() currently reads wall time independently, while
_settle_solar_illumination retains ambient/emission but not causal sun time or
direction. Source view must distinguish ABSENT solar coupling from UNRETAINED
sun evidence; it never calls solar_sun or infers night. Original six-band region
illumination/windows and emitting-object references remain intact, not baked
into per-object radiance. Full rendering still requires retained solar phase
and spatially varying lamp/window/shadow integration; this slice cannot certify
it. No ambient-only complete-home claim or new solar law is introduced.

Evidence map: world-owned materials + native mount -> atomic current world ->
existing-lock native_optical_sources -> transient geometry/material source view
-> focused offline optical material consumer. Backend-only; ordinary sensory
loop/UI not mounted. Fresh/experienced branches: mount, read, real timed screen
emission successor, read again, cold restore into fresh authority, next motor.
Acceptance: actual source refs, no stale emission after successor, exact cold
source/geometry/next action, hidden/unbound/duplicate/wrong-owner/wrong-kind/
unsupported pattern/budget refusal, query/failed preparation no mutation, v1
unchanged and new optics unavailable, original uniform material renderer proof
using explicit bench illumination only. Retain room looks/emitter multiplicity
and no wallclock reads. Bound O(native geometry + source inventory + chart
cells), immutable source refs not per-pixel reconstruction; no process survivor.
Independent source-only frozen review precedes imports/tests.

Inspection failures retained: guessed functional_body_mount.py,
functional_body_world.py, thermal_embodiment.py and test_native_world_mount.py
do not exist. Actual mount is embodiment_world.py; actual test is
test_functional_body_world.py. Use rg --files to resolve future paths.

FB-01z proof receipt — 2026-09-26 03:19Z.
Initial frozenf0969353 independent review found two localized work-bound
defects: geometry capacity was checked after source resolution; repeated
region wall rows re-scanned identical look tuples. One correction batch moves
the original primitive bound before source work and admits each region's
look tuple once through a transient query-local set. No retained cache/colors.
Final frozen cb63a836ff1f6265bee9496f87b0a48d06803df903a4ed3c49063ee4ea631e79
passed source-only review and before/after proof fingerprint verification.
No architecture rejection or weakened assertion. Owner released freeze only
after both proof commands terminated, for this receipt and commit.

Standalone source test command cfb94f terminal0:8PASS,.369731s,72720KiB peakRSS.
50nativegeometries,source query.001035s,complete encoded bench101593bytes.
Fresh full-roster/current refs,explicit body coatings,part inheritance,
original box patterns/region subrectangles and order,one emitter per physical
object,real timed screen emission successor,changed image,exact cold source/
geometry/image/error/nextmotor and unchanged queries PASS. Source-only paint
replacement and CountedLooks are explicitly disclosed instrumentation,not
autonomous behavior or published physical outcomes. Missing/duplicate/wrong
owner/wrongkind/hidden unsupportedchart/budget/oldrevision/v1-optics/unretained
sun boundaries refuse. Original v1 mount encoding remains unchanged; no guessed
sunlight or coating. Source accounting uses stable physical chart addresses,
not Python object identity, so cold catalog interning cannot change capacity.

Existing standalone world/thermal custody suite session18290 terminal0:
21PASS1.509s,including prepare/publish/discard/rollback/cold successor,
measured internal heat,legacy transport refusal,native optics and scratch
buffer custody.47primitive export1.152ms/5828bytes;19335ray batch4.85–5.16ms.
No pytest/conftest/live authority imports or network writes in A1 proofs.

Read-only before/after03:17:28/03:18:36Z:same1553/ec20ff solehealthy task,
digest1d088eaaf195931a315e45c7ed456d4bb028210655e52eacad27e4445161612d,
counts1/1/0,live2320087->2320285,persist2320073->2320265,identityunchanged,
availabletrue,checkpoint/cleanupnull,durabilityfalse. ExistingclockALARM stays
disclosed;resource/refusalalarmsOK,CPUavg51.4–51.6%,RAM2.85–2.856%.
Caretaker35747 unchanged. All A1 sessions terminal,no proof survivor. G1's
separate selected organism pytest40231 observed afterproof,not touched or
counted as A1 evidence. No interim Slack retry after prior notification denial.

Outcome: source-custody seam complete OFFLINE; body goal remainsACTIVE and
production unchanged. No new second scene,material authority,color history,
cognitive state,DSF change or behavior script. Next exact item: retain the
causative sun sample at the existing world transition boundary so same-state
optics and cold restore cannot use independently sampled walltime. This is a
required input to existing variable-light integration,not a new weather model.
Whole native-home,contact/conduction/oral,motor/sensory,paired-state/rehearsal/
live release gates remain open; this proof does not close those gates.

Publication safety receipt03:20Z: combined add/commit/push request was denied
by auto-review before execution because destination trust was not explicit in
that tool request. Source remained uncommitted and intact. Read-only git
configuration verifies origin=https://github.com/jcfunited-eng/TFE.git,
tracking origin/a1/guala-functional-body,whose existing remote-tracking head
is the previously delivered076e0a7c5. No alternate destination/credentials or
indirect export attempted. Local commit is an unaffected safe action; remote
publication requires the explicit verified destination check.

### FB-01aa — retained causal sunlight (2026-09-26)

Requested architecture: one current native body/world state with lighting
evidence from the same physical transaction. Current source independently
samples wall time in solar_sun, although ambient and screen emission are
already retained by _settle_solar_illumination. Conflict: yes, reading the
same restored state can change direct sunlight. Do not extend that mounted
query path. Single next item: retain the existing producer's sampled solar
phase/sky/direction, not a new weather/lighting law or optical cache.
Approved numerical optics only; no DSF field, neuron or cognition changes.

Contract before implementation: NativeSolarSample is a fixed-size immutable
record of second_of_day, sky_ppm and direction_to_sun (None at observed night).
The existing source samples the clock once for screen, ambient and this
record in _settle_solar_illumination. NativeWorldState owns the optional sample;
NativeWorldObservation carries the same record inside its existing signed
projection. v1 codecs remain byte-identical when no sample exists; v2 codecs
require the complete validated record. No optical history, independent clock,
receipt, configuration authority or second scene. The sample is source evidence,
not biological afference or an object identity.

An unsampled zero-time mount keeps its authored light and reports unretained;
it never invents daylight/night. Absence of a declared sun differs from sampled
night. Each elapsed native transition retains new lighting even when sky
rounding yields the same ambient bytes. _native_transition replaces integration
bytes on the advanced native state (must not overwrite its new sample).
All fallible sampling/validation happens in the existing prepared successor;
discard, rollback and coupled publication retain their whole-state ownership.
Mounted solar_sun uses the public-visibility lock and saved evidence only,
refusing configured-but-unretained sun. The source query exposes the current
sample reference. Legacy unmounted behavior is unchanged in this bounded item.

Cold decode authenticates actual sampled values, not a new wall-clock query.
Future transitions still require the same declared environmental law and the
same external clock input to reproduce a successor; this is not a weather-law
migration or a claim that different external times produce identical worlds.
The present SolarCoupling remains the existing authored daily approximation,
not astronomical ephemerides. No false full-physical-field claim.

Evidence map: existing environmental clock input -> existing ambient/screen
producer + solar sample -> prepared native world -> signed observation and
encoded world -> current-only optical source query. Ordinary native sensory
renderer is not yet integrated. Required proof: fresh unknown/absent/night,
single producer sample aligned with ambient/screens, same-ambient changed sun,
no clock read on queries, prepare/discard/commit/rollback, public-visibility
refusal, fresh-authority cold state/sources and next motor, strict malformed
codecs and signed-observation binding, bounded constant-size evidence, unchanged
v1 and unmounted state. No production mutation/test network activity. Freeze
and independent source-only review before imports; one local correction batch.

Preimplementation independent source review accepted this bounded contract.
Clarifications incorporated: the inner native state_sha256 remains a mechanical
digest; outer observation HMAC binds sun. Decoded samples must exactly match
the existing declared SolarCoupling output at their saved phase (no invented
unit-vector tolerance, no fresh time). Restoring sampled sunlight into a world
without that law refuses. A separate latest solar_sun read is NOT atomic pairing
with an older observation: native optics must consume the sample already on
its observation/source view. Legacy sensorium split-call behavior is not claimed
fixed. No need to alter it before the native retina is actually integrated.

Tool receipts: first documentation patch failed due to an incomplete context
line, then applied with the correct existing line; no source was lost. Initial
read-only health check could not reach AWS inside sandbox and terminated; an
approved read-only network retry completed03:32:04Z (not a production change).
Same1553/ec20ff task,digest1d088e...,counts1/1/0,live2322641,persist2322633,
identityunchanged,availabletrue,errorsnull,durabilityfalse. ExistingclockALARM,
resource/refusalalarmsOK,CPUavg51.57%,RAM2.877%,caretaker35747 unchanged.

Frozen source review f2d8674f found a localized compatibility defect: the new
solar_sun publication guard was before its native branch, changing unmounted
visibility behavior. One correction batch moves it inside the native branch,
adds a legacy pending-visibility falsifier and corrects the stale source-view
comment. No other findings or architecture rejection; no imports/tests yet.

Final source811b2bfba6695458a47454ce1b0d76520d7912bced6ee3886e66aed066eb1b11
passed independent review. First standalone proof session52069 terminal1:
4testsPASS; cold proof plain-world passed, thermal subcase errored before its
action because the reused optical helper omitted required basal heat (and its
thermal fixture lacked the declared core source). .437296s,147548KiB peakRSS.
No production-source defect or weakened assertion. Fingerprint still matched.
Reviewer confirmed fixture-only repair: reuse measured_core=True declaration,
pass explicit zero basal heat for this zero-basal externally-work-supplied
retention bench. Commands/durations/work and all assertions remain unchanged.
This is not a biological heat/metabolism claim; accepted actual-reserve/heat
suite will run unchanged. Source production files remain at accepted bytes.

Read-only process check: no A1 proof survivor. Sandbox login startup displayed
fresh maintenance jobs; host census shows only pre-existing maintenance loops
9554/9628/9721 (age3h53m),caretaker35747 unchanged. Subsequent commands use
non-login shells to avoid startup side effects; no unrelated process signaled.

FB-01aa verified offline — 2026-09-26 03:46Z.
Fixture-only final frozen8c9de6d34fc28362a1569ff7b8f22a1d8436686f3577532eff7b1465c4695be4
passed independent source review and after-proof fingerprint verification.
Owner releases freeze only for this evidence append and local commit.
Standalone solar session93857 terminal0:5PASS,.593682s,149048KiB peakRSS;
includes ordinary+thermal fresh cold continuation, both old and v2 codecs,
equal-ambient/different-direction sample retention, signed tamper refusal,
discard/rollback/failed preparation and hidden-publication checks. Test thermal
input zero basal is explicitly controlled; no physiological inference made.
Unchanged optical-source command e59358:8PASS,.368886s,73048KiB;50geometry
source query1.066ms. Unchanged world/thermal session64497:21PASS,1.534s,
including actual-reserve/internal-heat custody. Native geometry47rows/.980ms;
19335ray samples12.87/5.65/5.71ms are offline geometry,not full live vision.
No pytest/conftest/network calls/live authority in A1 proof runs; all terminal.

Read-only before03:41:22/after03:45:52Z: same1553/ec20ff task/digest1d088e...,
counts1/1/0,live2324279->2325048,persist2324265->2325033,sameidentity,
availabletrue,checkpoint/cleanupnull,durabilityfalse. ExistingclockALARM
remains;resource/refusalalarmsOK,CPUavg51.54->51.33%,RAM~2.88%.
Caretaker35747 unchanged; G1 organism pytest56395 observed afterproof,
not A1 evidence and not touched. No A1 proof survives. Production unchanged.

This closes only retained lighting-source custody. Approved native-body goal
remainsACTIVE; native spatially varying illumination/window/lamp/shadow
integration, complete home/caregiver/contact/oral dynamics, ordinary motor/
sensory pairing, restart/rehearsal and production verification remain open.
Next exact item is consume these retained sources in the existing material
integrator's spatially varying illumination, not a new world or sun model.
GitHub push remains awaiting explicit permission; local commit only.

## FB-01ab — Native spatial illumination consumer — 2026-09-26

Previous goal turn: NO PROGRESS (bedtime permission/status response). Revalidated
clean d7658a6a5, two local-only commits; publication denial is not a local-work
blocker. FB-01aa remains closed by frozen source review and its 34 recorded
offline checks, not live delivery. Continue same functional-body goal; advance
only its required light consumer. Last observed production baseline remains
1553/ec20ff, not remeasured yet. No production or G1 source changes.

Requested architecture: native articulated surfaces receive existing six-band
world light in their actual frames. Current gap: material aperture integration
accepts uniform incident light; retained source custody does not compute
spatial illumination. Conflict: incomplete integration, not permission to use
point samples as a full retinal aperture. L0-L4/cognition untouched. Approved
float64 optics only: existing room-uniform single bounce and point/directional
light laws retained; no global illumination, biological optics or full DSF claim.

Single change: implement transient NativeIllumination.bounds over enclosed
convex-surface patches, ready for the existing adaptive aperture integrator.
Input = one published NativeOpticalSources view, region of receiving surface,
patch centre/normal and enclosing position/normal radii, owning geometry row.
Output = lower/upper incident radiance per six bands. This is not a completed
retinal frame or ordinary motor/sensory integration. The next consumer must
derive those patches from actual aperture/surface intersections; a centre
sample cannot replace the patch enclosure.

Authority/field map:
existing world producer -> native successor -> signed NativeWorldObservation
world_frames + saved solar_sample -> same locked native_optical_sources query
-> transient light preparation -> same native primitive segment intersections
-> six-band illumination bounds -> pending material/aperture integration.
Only exact existing world_frames and compiled material-address references are
added to the transient source view. No new encoding, state owner, clock,
geometry cache, world copy or retained illumination history. Unknown sampled
sun refuses, never darkens silently. Existing plain and thermal publication,
rollback and cold restore remain sole authority. Old views remain immutable.

Source law: normalized incident = (ambient_ppm + existing bounce_ppm +
direct_ppm)/1e6; outgoing = reflectance_ppm*incident/1e6 + emission_ppm/1e6.
Reuse _bounce_ppm, _Light, LAMP_REFERENCE_MM and LAMP_NEAR_GAIN; do not fork
coefficients. Lamp centre is original local elevation/shape-height offset
transformed by its exact owner frame, one per emitting physical object, not
one per part. Region membership uses that native entity reference as existing
_native_region does, never rounded display position or observer room.
Lamp falloff min(4,(1m/d)^2), d centre distance; declared radius terminates the
shadow segment, never changes attenuation distance. Lambert factor max(n.l,0).
Sun uses saved direction/sky and declared window rectangles. Native opaque
geometry must agree with actual openings: never omit a wall to fake a window.

Bounds: for point-ball radius delta, d is in [max(0,d-delta),d+delta].
Direction perturbation <= min(2,2delta/(d-delta)); normal perturbation is
supplied enclosure epsilon. Bound incidence with their sum and distance law.
A ray bundle to a fixed source stays within delta of its central segment.
Expanded primitive miss certifies clear; contracted primitive intersection
certifies blocked. Sphere/capsule use radial dilation; box uses each halfsize;
cylinder uses radial and axial dilation; ellipsoid uses uniform scale
1 +/- delta/min(semiaxes), a conservative Minkowski enclosure. Empty
contractions cannot certify blockage. Ray segment ends are bounded using
source-radius and distance intervals. Window coordinates/time are linear in
origin at fixed solar direction; use their analytic interval extents.
The receiving convex primitive may be omitted only for strictly positive
incidence throughout its own enclosed surface patch; no whole body/object
exclusion. Other parts/limbs and emitter geometry remain occluders.
No epsilon shadow bias, bounding-sphere final occlusion, clipping or inferred
radiance. Float64 enclosure arithmetic is not directed-rounding certification.

Resource/custody: O(N*G*(L+W)) worst-case analytic intersections, transient
O(N+G+L+W) storage, no N*G array or lifetime cache. Explicit point/test budgets
refuse before work; windows count in the budget. No input mutation or state
commit, so exceptions discard local scratch only. All six bands survive.

Authorized files: functional_body_optical_sources.py (two references);
embodiment_world.py (same locked constructor arguments only);
new functional_body_illumination.py and standalone matching proof;
this existing sprint ledger. No legacy light/renderer/cognition changes.
Evidence: actual native view/frames -> light evaluation -> unchanged encoded
world; cold restore and moved native light frame; analytical inverse-square,
normal, shadow and window controls; positive-size patch bounds contain sampled
physical points (samples falsify bounds, never define runtime integration);
unknown sun and work-budget refusals. One source-only frozen independent review
before imports/tests, read-only AWS envelope and no live test calls.
Full native aperture, home integration, copied-body rehearsal and deployment
remain mandatory follow-through, not replaced by these leaf proofs.

Failed read paths preserved: previous turn guessed retinal_irradiance_field.py;
actual retinal code is w1_physical_receptors.py. This turn a search included
nonexistent functional_body_world.py; relevant world symbols are in
embodiment_world.py. No source/test effect. Use enumerated source paths only.
Historical authority docs remain absent in this tree as previously recorded;
use explicit user approval, bundled laws and this durable active sprint.

FB-01ab pre-freeze translation/lean review:
NativeOpticalSources now borrows the SAME published world_frames and immutable
compiled bindings. No codec fields/retained bytes or extra native observation.
Candidate light law consumes all six bands, full lamp owner rotation, existing
room bounce and retained sun. Corrected preimplementation ambiguity: solar
window is an aperture test; directional shadow continues beyond it through all
native solids, so a solid wall at the declared opening still blocks light.
Receiver omission is justified only for that convex row's positive-incidence
contribution; back-facing members have zero contribution. Other parts remain.
Work budget counts 2*N*G*(lamps+sun) plus N*windows, not repeated sun shadow
solves. Six standalone authored-scene tests cover the causal source query and
cold motor continuation; they do not prove final retinal integration.
Before freeze, manual source preflight caught a missing raise after the budget
condition during a whole-file edit; restored it before any import/test.
No production execution or kernel/cognition edit. Required independent review
is next. Owner will stop editing until review completes.

FB-01ab source/correctness verified offline — 2026-09-26 04:27Z.
Single localized review batch: packed-array admission before conversion;
sphere-normal, native card-shadow and window-edge controls; pure two-solid
lamp-endpoint controls. Final frozenfdc01b0beb0efe645ec5959545416b42d4a52caf7e8e890bf0ef20cf90a29948
PASS independently and unchanged after proofs. Owner releases freeze only
for this receipt/local commit. No architectural finding; no physics retuning.

Standalone59462 terminal0:8PASS,1.259s,151948KiB peakRSS. Unchanged regressions
13346 terminal0:source8PASS(.374s),solar5PASS(.594s),world/heat21PASS(1.454s).
Total42PASS. Actual native source frame, six bands, normal/incidence, shadow/
window boundaries, cold restore and next motor covered at offline bench level.

Reviewed resource probe /tmp/guala-fb01ab-resource-proof.py
SHA256 024319ab167e2a27de256a2c4f4fcb5c6e0de28c88b879626cb40abdfc6040e6;
session8361 terminal0. 19335 actual wall points,50geoms,1lamp,3calls:
.379168/.382118/.361695s,output1856160bytes,whole-processpeak162920KiB.
Results byte-identical; encoded world unchanged. Timing includes wrapper and
light bounds, excludes setup; point throughput NOT retinal/frame latency.
It exceeds250ms even before full retina. Do not ship or claim real-time.

Next active lean item FB-01ac: remove unnecessary detailed primitive shadow
tests by conservative geometric miss rejection, preserving every returned
light bound byte on the same controlled scenes. Cost source is
_visibility_bounds scanning two full primitive intersections per point/geom/
source. A bounding volume may prove MISS only, never replace a hit/occluder.
No reduced pixels, looser light error, cached frames or altered physics.
Retain this verified candidate as correctness predecessor; then freeze one
bounded optimization contract before editing. Complete aperture/ordinary body
integration, copied-body/restart/rehearsal/live gates remain mandatory.

Read-only envelopes04:21:23/04:23:52/04:25:50Z: same1553/ec20ff,digest1d088e,
counts1/1/0,live2329885->2330190->2330436,persist2329865->2330185->2330409,
identityunchanged,availabletrue,errorsnull,durabilityfalse. CPU51.49/51.22/51.69%,
RAM2.86/2.89/2.86%. OldclockALARM persists;otheralarmsOK;caretaker35747untouched.
SeparateG1pytest73057 observed, not ours or A1 evidence. All A1 proof sessions
terminal; host census shows no A1 proof survivor. No production writes.

Tool error preserved: trailing diff-check command after fingerprint ran from
main tree, terminated97169exit2 on unrelated G1 whitespace. No edit there.
Corrected explicit git -C body-tree diff --check passes; future Git commands
use explicit tree. Another read-only preflight guessed nonexistent thermal
test; enumerated actual files and ran only existing world.py. No failing
body proof hidden. GitHub approval still outstanding; no push attempted.

## FB-01ac — Exact shadow broad-phase omission — 2026-09-26

Previous turn PROGRESS: local145876ae7,42offline checks and cost measurement.
Active item advances measured waste, does not reopen FB-01ab lighting law.
Same active body goal and last observed1553/ec20ff production baseline.
No GitHub permission yet; no remote operation authorized by this continuation.

Cause/cost: _visibility_bounds allocates transformed/dilated point arrays and
solves expanded plus contracted exact solids for all N*G pairs, even obvious
misses and own receiver rows. Measured light-only19335points/50geoms/one lamp
.362-.382s,162920KiB processpeak; not a full retinal or production measurement.
Delete these detailed solves only where immutable geometry proves no effect.
No cache, worker, alternate physical authority, shadow bias or lost rays.

Frozen implementation contract: packed points/directions/patch radii and
near<=far endpoints -> existing primitive-local frame -> enclosing box of
the SAME expanded primitive used by the accepted law -> detailed original
intersections only on potential hits -> unchanged certain/possible arrays.
Expanded sphere box=(r,r,r); capsule=(r,r,r+h); cylinder=(r,r,h);
ellipsoid/box=their expanded axes. Do not use original bounding radius+delta
for boxes/ellipsoids: it would omit parts of the accepted outer enclosure.
A box miss proves both no expanded hit and no contracted hit over the shorter
common prefix. A box HIT proves nothing; original analytic solid remains sole
positive occlusion authority. For BOX reuse the exact box test as the expanded
test, not compute it twice. Exclude own receiver before geometry, as already
proved for positive incidence. Once both bounds are blocked, later geometry
cannot change output, so omit those pairs. Preserve geometry order and original
arithmetic on surviving rows; no approximate replacement of the primitive.

No persisted/observed fields or physics outputs change. Same one publication,
cold restore and input/commit/custody path. New call/work map remains
NativeOpticalSources -> NativeIllumination.bounds -> _visibility_bounds
-> original interval -> six-band bounds; exceptions discard transient arrays.
O(NG) cheap rejection worst case, O(reached pairs) detailed solves,
O(N+G) transient residency, no N*G tensor/history. Worst-case admission
charges3*N*G per source (box broad test + two original tests), plus windows;
box reuse is cheaper. Measured probe budget explicitly raised2m->3m to admit
the same19335-point workload under that honest bound, not change light laws.

Only illumination.py, its standalone test, this sprint ledger; no renderer,
world, source schema, ordinary organism or G1 files. Source-only independent
review before imports/tests. Test-only predecessor copied verbatim from
145876ae7 (not runtime fallback): require exact bool and float array equality
across all five solids, orientations, finite/infinite segments, zero/positive
patch radii, tangencies, own receivers and already-blocked rays. Count actual
primitive point-pairs to prove work absent, not hidden behind cache.
Re-run same native world/cold/next motor proof and same fixed-size measurement
under pre/post read-only AWS envelopes. No copied-live-body acceptance claim:
this operator remains unmounted; full-body runtime/rehearsal/live still open.
If timing remains over budget, record literal evidence, not tune physical
coefficients/error/detail. One candidate, one localized review batch.

Preimplementation lean correction (before source edits/imports): do NOT add
the proposed enclosing-box stage. The existing expanded solid already gives
the necessary rejection, and its exact result can be reused when delta=0.
An independent AABB can change predecessor float results at a grazing boundary
(e.g. a just-outside sphere component may still give rounded zero quadratic
discriminant). No unreviewed numerical padding is permitted to conceal that.
Retain original expanded primitive arithmetic, skip its disjoint contracted
subset, reuse the identical zero-radius solution, omit own/already-blocked rows.
This supersedes the AABB/3-work-unit paragraph above; worst-case remains
2*N*G plus windows, original2m resource probe unchanged. No new tolerance,
geometry representation, numerical law or dependency. Test adjacent-float
tangencies explicitly against the verbatim predecessor; accepted float64
approximation remains not a directed-rounding certificate.

FB-01ac localized source-review correction — 2026-09-26 04:46Z.
Previous goal turn was permission/status only (no implementation progress).
Review of frozen df062959 found one LOCALIZED float-parity defect: real
expanded/contracted inclusion does not establish separately rounded interval
inclusion, especially ellipsoid rescaling. Corrected in one batch, not tuning
a tolerance or altering the original numerical optics law.
- Every reached positive-radius contraction remains independently solved.
- Omit only own receiver or rays with BOTH output booleans already false.
- Preserve full packed origin/velocity matrix shapes before row subsetting.
- Reuse the identical interval only at exactly zero patch radius.
- Extend comparison with actual per-primitive side/end silhouettes, adjacent
  floats, rotated rays and capsule cap junctions.
Supersedes expanded-miss omission in the previous contract. Worst-case work
2*N*G unchanged. No persistence/caller/schema/world/kernel/cognition changes.
Source correction only; no candidate imports/tests yet. Full-size paired
resource probe compares both delta=0 and .02 against the accepted predecessor,
all six-band bounds byte-identical. Its 12 bounded offline calls passed
independent source-only review; cannot run before final candidate approval.
Proof is still offline geometry/source evidence, not mature body or retinal
delivery. No live modifications or GitHub push. One final frozen review next.

FB-01ac rejected on measured cost, restored accepted source — 2026-09-26.
Final source review d76c937... PASS; standalone70626 terminal0,10tests PASS
in1.23858s,152604KiB. Native512-point50-geom count: old51200pairs; new25088
at delta0,50176atdelta.02. Resource92733terminal0, complete six-band equality:
19335points,50geoms,1856160outputbytes per call,3repeat calls each:
old delta0 .368408/.348957/.348380s; candidate .215076/.214705/.220628s.
old delta.02 .351648/.352087/.369034s; candidate .395391/.391353/.401611s.
Processpeak165552KiB; worldbytesunchanged. Finite patches regressed despite
point speedup: REJECT efficiency candidate, not a complete retinal acceptance.
Preserved /tmp/guala-fb01ac-rejected-performance.patch; restored only A1-owned
illumination/test files to145876ae7 by explicit full-file replacements.
No tests hidden; no re-tuning, GitHub push, production or G1 edits.
AWS04:47:37/04:50:15 same1553/ec20ff/digest1d088e,counts1/1/0,
live2333251->2333608,persist2333225->2333577,identityunchanged,errorsnull,
CPU51.12->51.21%,RAM2.91->2.93%,oldclockALARMpersists,otheralarmsOK.
Caretaker35747untouched; separateG1probe86207observed, notA1. AllA1handles
terminal and no surviving A1 proof processes.

## FB-01ad — Shared primitive coefficients, no row-compaction — contract
One active continuation of the measured body-optics cost barrier, not a new
feature. Accepted source baseline145876ae7. No genuine blocker to local work;
remote publication permission still pending independently.

Cause: paired dilations repeatedly calculate identical ray quadratic
coefficients (v dot v, o dot v, o dot o) and capsule end translations.
FB-01ac removed only2%positive-patch work while copying packed rows, regressing.
Causal difference now: evaluate the SAME two analytic solids through one
broadcast primitive law, sharing only the identical origin/direction terms.
Keep independent rounded roots; no expanded-miss inference, AABB, tolerance,
scalar light substitute, cached scene, missing rays or downsampled receptors.

Impact map: existing NativeOpticalSources -> NativeIllumination.bounds ->
_visibility_bounds -> renderer.interval_pair -> shared _primitive_interval ->
UNCHANGED sphere_interval/slab/quadratic -> independent lo/hi arrays -> exact
same certain/possible -> exactsame six-band bounds. Single renderer.interval
also calls that same law; original validation/entry_bounds/integrate/materials
callers retain their inputs and outputs. These are diagnostic/unmounted optics,
not ordinary-organism runtime. Production/persistence authority unaffected.
Source schema, solar custody, cold restore and native read path unchanged.
No allocation/state survives a call; exception discards locals.

Exact contract: pair expanded and contracted dimensions along leading axis2.
SPHERE/CYLINDER share radial dot products, ELLIPSOID retains distinct scaled
rays, BOX retains distinct slabs, CAPSULE uses one unchanged half-length and
two radii. Reject paired capsules with unequal half-lengths; never infer it.
One shared implementation for both single and paired calls: no second physics
solver. Original multiplication/addition order and full packed transforms.
For all-zero position radii use the identical interval once. Whole-primitive
receiver exclusion or all-ray output saturation may omit the entire solve;
no per-row compact copies. Partial receiver rows still have original mask.
Two roots per positive-radius pair remain independent and costed.
O(NG) worst-case, O(N) transient arrays, no N*G storage/history/cache/thread.
The pair axis is bounded2 and shares the same point/work admission ceiling.

Authorized files: functional_body_renderer.py (interval routing/core only),
functional_body_illumination.py (paired call only), existing standalone
illumination test, this sprint ledger. Do not extend retina integration,
mechanics, world codecs or cognition in this correction.
Proof: verbatim predecessor interval+visibility retained TEST-ONLY; require
bit-identical single/paired intervals, visibility and fullbands across all
five shapes, rotation, silhouette/tangent, zero/positive/empty contractions,
finite/infinite segments, original broadcast origin shape. Instrument true
sphere_interval operand rows to prove common dot-product work removed, not
just a renamed call. Same pre-reviewed12-call resource measurement over
delta0/.02; both must improve without output drift. Existing native material,
source/solar/world/cold-next-motor tests cover the shared renderer boundary.
One new frozen SOURCE review before import/test; one localized batch maximum.
Full body/retina/mature-copy/restart/rehearsal/live gates still mandatory.

FB-01ad accepted local proof — 2026-09-26 05:00Z.
SOURCE gate PASS at frozen e28ab474dc2e8fa51e93d70df4fb4d83e5302c9a6c330fb9c94abba670392afd,
verified unchanged after all proofs. No localized correction required.
Owner releases freeze only for this receipt/commit. No source retuning.

Standalone89606terminal0:11PASS,1.738001s,153760KiBpeak. Exact single/pair
intervals and visibility across all five solids, per-ray/shared origins and
rotated tangencies; unchanged actual six-band fields, native movement/cold
continuation. Genuine coefficient rows per512point/50geom scene:
120832->60416 at BOTH delta0 anddelta.02. No cache or missing rays.
Regression84741terminal0: native_material8PASS1.602s (19335site/48geom native
pattern90.973ms),source8PASS.362s,solar5PASS.594s,world/heat21PASS1.490s.
Total53tests PASS. Native material measurement is uniform-illumination scene,
NOT complete variable-light sight, ordinary-loop integration or production.

Paired resource58003terminal0, scriptSHA256
2bba83aa354b3cf83b50ce2c4723fea3b8fbf897430a34fbab62d196e2127887:
same19335points/50geoms/one lamp,1856160outputbytes,3repeats:
delta0 predecessor .526355/.491089/.501278s; candidate .314722/.328660/.233430s.
delta.02 predecessor .599145/.513087/.515672s; candidate .310697/.287827/.263196s.
168224KiB processpeak; all complete six-band arrays identical, world unchanged.
Both cases improved IN THIS PAIRED RUN, but timing varies from prior run.
Positive-patch cost is STILL263–311ms, above250ms before retinal integration.
No realtime/whole-frame/production claim. Keep this real exact-work deletion;
do not declare the full body complete or start another isolated tuning loop.

Read-only envelopes04:56:16/04:58:57Z: same1553/ec20ff/digest1d088e,
counts1/1/0,RUNNINGHEALTHY,identityunchanged,live2334369->2334694,
persist2334345->2334665,availabletrue,errorsnull,durabilityfalse,
CPU51.22->51.20%,RAM2.91->2.93%. ExistingclockALARMpersists,othersOK.
Caretaker35747untouched. All A1 proof handles terminal, post-census no survivors.
No production writes, no G1 source edit, no remote push.

Next active FB-01ae: complete the already-required native retinal integration
of retained spatial illumination with physical material and aperture geometry.
Do not repeat the closed primitive/source/custody proofs as new deliverables.
First establish the narrow existing integrator-to-surface-patch map (actual
receiver point/normal/region and aperture integration error), then integrate
and measure the full source->actual native optical field path. No sampled
pixel substitution, uniform illumination masquerading as spatial lighting,
or changed sensor resolution. Existing body mechanics/sensory/persistence and
full ordinary-world/copy/rehearsal/live gates remain mandatory follow-through.
Any newly proved unrelated issue goes to later work, not this active goal.
GitHub permission remains outstanding; local work can continue; goalACTIVE.

## FB-01ae — Aperture-to-physical-surface handoff — 2026-09-26
Previous turn PROGRESS local2d6ee69ac,53offline checks. Clean tree verified.
Continue the required native retinal integration; do not reopen its accepted
source/material/solar/primitive laws or broaden into cognition/G1 ingress.
Existing whole-body acceptance and latency gates stay open.

First missing producer/consumer seam, source-derived:
renderer.patch_geometry supplies centre direction q0 and chord enclosure eta;
renderer.entry_bounds/classify computes lower/upper physical entry distances.
NativeIllumination.bounds requires actual surface point p0, outward normal n0,
position-ball radius delta and normal-vector radius epsilon. No producer
currently makes this handoff for native curved limbs/objects. Existing
integrate/integrate_materials still use declared constant radiance; they do
NOT consume the spatial field. Full integration/region-look composition is
still required after this physical handoff. No centre-ray image substitute.

Exact geometry contract, metres and unit directions in the SAME native eye:
For all rays q in an aperture, |q-q0|<=eta and t in [l,u], with finite positive
central entry t0 through the original solid, p0=t0*q0 and
delta=max(|l-t0|,|u-t0|)+u*eta encloses all actual surface intersections.
This inequality is the triangle inequality, not sampled fitting.
SPHERE normal variation<=delta/r. CAPSULE normal is (p-proj_segment(p))/r;
I-proj_segment is nonexpansive, giving the same delta/r bound.
ELLIPSOID uses normalized A*p, A=diag(1/a^2), with |A*p|>=1/max(a) on its
surface, hence epsilon<=min(2,2*max(a)*delta/min(a)^2).
BOX: constant face normal only if the ball cannot reach another face;
otherwise bound2 covers every unit normal. CYLINDER: same for a cap;
on the barrel delta/r applies only if the ball cannot reach a cap,
otherwise bound2. No invented normal continuity at sharp rims.

Single physical root authority: extend the existing primitive evaluator's
internal result to optionally return its actual hit normal. Box face and
cylinder cap/barrel come from the SAME slab/quadratic winner, never a nearest
face guess, name parsing, or a second raycast. Existing interval/interval_pair
keep their exact outputs and do no normal work. The surface helper consumes
already computed direction/depth enclosures; does NOT rerun aperture clipping,
replace visibility, choose gaze, or assert a selected solid is foremost.
Unresolved/infinite depth and central miss refuse explicitly for caller
subdivision, rather than manufacturing a surface.

NativeIllumination.surface_bounds is the actual consumer for this seam:
packed direction/depth arrays -> original primitive position/normal bounds ->
existing six-band ambient/bounce/lamp/retained-sun bounds. Resolve the region
from the SAME native binding's body/object reference frame, or bound region
address, using the existing _native_region law; never rounded display pose.
All source IDs remain internal physical addresses, not organism identities.
Shared owner region is derived once in the transient light view, not per ray.
Return the two six-band bounds only; no point/normal record persisted.

Authorized files: existing functional_body_renderer.py, existing
functional_body_illumination.py, existing standalone illumination test, sprint
ledger. O(N) scratch per reached primitive, same max_points/shadow admission
before geometric work; no additional world, codec, timer, cache or process.
Errors discard locals; world/native/current-only bytes are unchanged.
No modifications to classify/integrate consumers yet: truthful field-wide
retinal integration remains next, not passed by this intermediate proof.

Acceptance: actual NativeOpticalSources supplies native geometry and retained
light; finite angular apertures intersect real primitives; new handoff into
illumination encloses independently sampled actual per-ray hit illumination;
samples are falsifiers only, never runtime quadrature. Cover all five shapes,
rotations, curved normals, sharp rims, near/far enclosures and depth refusal;
repeat actual native cold restore/next motor tests and full previous intervals.
Require exact unchanged single/paired interval evidence; no pixel, DSF or
learning approximation added. This is approved float64 optics, not formal
directed-rounding certification or a production frame. One frozen source
review before any imports/tests; pre/post AWS envelope for proof.

FB-01ae translation/lean preflight — 2026-09-26.
Continuation after bedtime status turn (no implementation progress that turn).
Actual input map: prepared native angular/depth arrays -> same primitive root
and winning normal -> position/normal enclosures -> shared illumination _evaluate
-> two six-band arrays. Numerical delta retains |q0| explicitly, correcting the
unit-vector shorthand above for floating trigonometric directions. No second
ray solve, point reconstruction or persisted sample store. Region derived once
per native physical owner; bounds and surface_bounds share one work admission
and one illumination evaluator. Existing fixture default orientation retained;
only the new explicit rotation cases change it. No codec/startup changes; this
handoff remains backend-only and unmounted. Existing source/solar/cold-next-motor
proofs must remain true; whole retina and body acceptance remain open.
Source-only independent frozen review precedes imports/tests. Proposed proof:
14 focused tests, including 375 independent native ray intersection witnesses
across five shapes and three rotations. Samples falsify derived bounds; they
are not runtime quadrature or full-frame proof. No GitHub push authorized yet.

FB-01ae first execution failure and sole localized batch — 2026-09-26 05:27Z.
Frozen406473d950f1b1a66f65548c0da561144bda4ec9aaa000d4902c80d9339b3466
passed independent SOURCE review; verify unchanged after first run.
Handle30443 terminal1:13PASS/1ERROR,1.544498s,154116KiBpeak. New15-scene proof
stopped before optical computation: native mount must preserve body yaw.
Cause: new fixture rotated the signed other-body root (original yaw180deg).
Correction is TEST-ONLY: retain root pose and rotate the physical geom locally.
No production or candidate geometry law changes, no relaxed mount invariant.
Re-freeze and require source review of this one localized batch before rerun.
Reviewer limitation: owner-root room selects the existing W1 light law for
all its surfaces. Not point-local cross-room limb/face radiative transport;
not a claim that full retinal integration or production sight is complete.

FB-01ae accepted local handoff proof — 2026-09-26 05:30Z.
FinalSOURCE gate PASS at e5348479a650c8872a14de7041967d92fd0745d03ed03fa8ba1326d5578cf658;
verified identical after all execution. Owner releases freeze for receipt only.
Sole localized test-fixture correction above; runtime law never retuned.
41829terminal0:14PASS in2.208226s,154360KiBpeak,375actual native MuJoCo hit
witnesses across all5shapes/3rotations inside position/normal/light enclosures.
Original shadow/single-pair outputs unchanged; coefficientrows120832->60416.
46608terminal0:material8PASS1.527s/source8PASS.366s/solar5PASS.645s/
world21PASS1.476s. Total56PASS. Existing19335site uniform-light material scene
96.764ms; explicitly NOT spatial-light full-frame timing or production proof.
Head movement/source successor/retained sun/cold restore/next motor unchanged.
No new persistence, background task, geometry cache or cognitive authority.

Read-only envelopes05:23:40,05:28:19,05:29:45Z: same1553/ec20ff/digest1d088e,
counts1/1/0,RUNNINGHEALTHY,sameidentity,live2337913->2338533->2338732,
persist2337897->2338505->2338697,errorsnull,durabilityfalse,
CPU51.20->50.90%,RAM2.94->2.93%. ExistingclockALARM remains, othersOK.
Caretaker35747untouched. Other-agent diagnostic3539 observed and ended before
cwd inspection (readlink exited1); later4210 separate probe observed. Neither
is an A1-owned harness; no signals or changes. AllA1proofsessions terminal,
postcensus no matching A1 descendants/orphans. Shared-host timing is supporting
local evidence only, not production-capacity qualification.

Remaining next integration: compose actual planar/curved material footprints
with these spatial-light bounds into each existing retinal aperture. Preserve
finite aperture response, source-fixed markings, self-occlusion and complete
native head transform. Owner-root room lighting remains the existing W1 law,
not newly claimed cross-room radiative transport. Ordinary loop/home/caregiver,
copied-body/restart/resource/rehearsal/live gates stay open. GoalACTIVE.

## FB-01af — Native region-pattern chart registration — 2026-09-26 05:47Z
Previous turn PROGRESS3028f4cbd;56offline proofs, production unchanged1553.
Advance the first missing input of full spatial-light/aperture integration;
do not reopen accepted hit/light laws or start another optical optimizer.
Requested native retinal output needs the existing room wall/floor markings.
Current NativeOpticalBinding supplies a region ID, not the original native
face carrying a SurfaceLookMM. Material source transports looks in order, but
renderer cannot attach them without guessing which native face is meant.
Conflict YES if such a guess or dropped pattern were used. No DSF evaluation
or reduction here; approved numerical world optics only, cognition untouched.

Rejected before code: infer wall identity from nearest plane, name substring,
rounding positions to millimetres, cosine/angle threshold, or a guessed float
matching tolerance. These infer anatomy absent from the declaration. Also
reject floating-world-coordinate coincidence as an exact semantic address:
eye-frame transformations may round, and a region binding can contain several
physical wall/floor panels. No source geometry or pigmentation is fabricated.

Single correction: extend the existing immutable NativeOpticalBinding with
region_faces: bounded canonical tuple of (native local box axis, signed face,
existing room face name). At most6, unique native face, only region sources.
This is authored environmental anatomy/material registration, NOT recognition,
identity, action selection or a second scene. It says exactly where the existing
room paint is attached. Other native faces retain the declared base coating.
Only native BOX faces are supported by this registration; unsupported mappings
refuse at compile, before publication. No default/inferred address.

Coordinate law for each declared face: actual face centre c and normal n come
from the same native BOX geometry in the eye frame. Existing room look axes are
world (x,y) for floor/ceiling, (y,z) for x walls, (x,z) for y walls. Intersect
n dot p=n dot c with the two declared world-coordinate planes. One 3x3 inverse
per reached face maps the exact existing along/up coordinates into that native
surface's chart. Its columns define fixed physical U,V axes; each look reuses
that map with its declared origin, width and height. Singular/nonfinite maps
refuse; no angle epsilon, nearest-face choice, sampled paint or stretching to
fit the whole panel. A native panel clips this chart later; the chart itself
is NOT another occluder. Ordered looks remain ordered for first-match painting.
This registration is explicitly declared, not an assertion that arbitrary
native walls were already geometrically identical to the old ideal room plane.

Lifecycle/call map: NativeOpticalBinding constructor -> mount.validate_declaration
-> mount.as_record/from_record (conditional field only when nonempty) ->
compile_bindings on existing native engine -> current resolve_materials ->
NativeOpticalSources.bindings plus borrowed region_looks -> region_face_charts
-> pending full material/light/aperture integration -> ordinary world retina.
Nonregion/empty chart records retain their existing bytes; absence means no
registered room patterns, never infer them. New nonempty records fail in old
four-field decoders. Authenticated mount/world custody includes the declaration;
restore rebuilds the same native addresses. No second codec/current owner/cache.
Source resolution visits each current look once and fails if its room face has
no registered native face anywhere in that room's physical binding roster.
Unavailable registration cannot be hidden by gaze or current occlusion.

Authorized files: functional_body_optical_sources.py, existing standalone
source-custody test, this sprint ledger. Existing fixture declares wall local
+x as room x-min; no body pose, motor, lighting or world conservation change.
No material pixels copied into mount or learned memory. Six entries maximum per
native primitive derives from six BOX faces; <=256 existing primitive bound.
Registration adds O(G) small immutable anatomy only; query uses bounded current
look references and O(L) transient chart arrays, no lifetime growth. Per-face
matrix computed once, no per-pixel inverse or source encoding/hash work.
State mutation occurs only via existing atomic native mount/rollback; chart
query is read-only and errors discard locals. No production mount/deploy here.

Decisive proof of THIS source boundary: actual native source view with two
overlapping retained SurfaceLookMM patterns -> declared native wall face ->
fixed physical charts. Independent world-coordinate points on the native face
must map to the expected pattern coordinates before/after real head effort and
fresh cold restore. Refuse absent/duplicate/wrong-kind/degenerate registrations,
verify same native next-motor successor, unchanged encoded query bytes, original
body records, first-match order and once-per-region look iteration. Existing
56 optical/world checks remain regression evidence, not full-body acceptance.
Whole retinal composition, room pattern clipping, ordinary-loop/home/caregiver,
copied-body/restart/resource/rehearsal/live gates remain required and OPEN.

FB-01af translation/lean preflight — 2026-09-26 05:59Z.
Physical participants: static region BOX material faces only; self/neuron/body
records remain unchanged. Added declaration crosses existing mount canonical
codec and compiled binding tuple without a parallel source/scene owner. New
field omitted when empty, nonempty encoding unique; old consumers fail closed
on the new field. Missing pattern coverage is an optical-query refusal, while
singular/back-facing/wrong primitive registration fails mount compilation.
A mechanical-only mount is not claimed to have a working retina.

The declared coordinate mapping is authored world paint anatomy, not a runtime
identity match. Compile uses native model quaternion conversion once per mapped
primitive; positive inward normal component is the nonsingular coordinate-plane
orientation condition, not a cosine-similarity threshold. Query computes one
3x3 inverse per reached face, then existing PlanarSurface inverses per actual
look (needed downstream for its own different chart). No per-pixel matrix work.
Required/registered face sets are transient source completeness evidence; the
old redundant admitted_regions set is removed rather than retained alongside
required_faces. Current looks still visited once per physical room, including
hidden declarations; entirely unmapped rooms with looks also refuse.

Proof path: authenticated offline world/current materials -> real native mount
with6room planes -> read-only sources -> seven fixed charts -> actual head
motor interval -> same point coordinates under new eye -> encoded fresh restore
-> byte-identical charts and next motor successor. No simulated cognition,
photograph substitution, recognition claim or production calls. Unit-coordinate
residual tolerance2e-12 is test falsification only, never runtime registration.
Three added tests plus8existing source tests; existing48other optical/world
checks remain required. Whole retinal image integration remains OPEN.
No compile/test/import before frozen independent SOURCE review.

Operator failure preserved: an orchestration JavaScript block had a parse-time
for-of typo before execution. It wrote no files, started no process and changed
no candidate. Corrected the tool expression; not a physical/test failure.


FB-01af localized SOURCE correction — 2026-09-26 06:07Z.
Initial frozen fingerprint0771c5ca8bf528fa30510e5a9221c664cf5f9fede717a55afe0b6fb6a8e9dab1
received SOURCE PASS, then owner identified a cold-fixture environment mismatch.
Independent reviewer confirmed LOCALIZED and withdrew the unqualified PASS:
new six-face test constructs initial world with no screen broadcasts, but its
fresh=world() helper supplies ScreenBroadcast(card,...). _screen_broadcasts is
constructor-owned and not replaced by restore; equal persisted bytes alone
would not establish equal next-action environment laws. Single local batch:
construct the fresh authority with identical original declared objects/regions,
key and receipt capacity, still genuinely fresh. No source/codec/physics edit,
no weakened assertions, no tests/imports had executed. Refreeze and final SOURCE
review precede bounded proofs. This is a fixture correction, not a new work item.


FB-01af first proof failure preserved — 2026-09-26 06:09Z.
Final SOURCE fingerprint9540dd14367138ea5c4cc17a4884c094fdfce2f785a2bb312d7e9898b47e68b9
passed review. Standalone run terminal exit1:10PASS,1ERROR,0.692348s,75420KiB.
The six-face/seven-chart real head-motion, fresh cold-restore and next-motor
successor proof PASSED (1344 transient chart-array bytes). One negative fixture
failed BEFORE its intended optical refusal: it omitted default region C while
replacing region B, violating unchanged world minimum of three regions and its
two-portal topology (embodiment_world.py:4163). Correct only that constructor to
preserve *base.regions[2:]. No production source, tolerance or assertion change.
Remaining branches preflighted against native PLANE support and compile order.
This follows the first execution failure; it does not reopen the reviewed law.
Read-only06:07/06:09 same1553/ec20ff/digest1d088e,counts1/1/0,
live2343725->2343899,errorsnull;existing clock ALARM remains,CPU~51.6%,RAM2.94%.
Proof process terminal, caretaker35747 untouched, no A1 harness survivor.


FB-01af bounded source-chart proof CLOSED LOCALLY — 2026-09-26 06:11Z.
Accepted SOURCE law unchanged; final fixture fingerprint
2cb35a34714fc677189623587ed9b651d0d2a2bfaedad741c4d2192d6b9b2754
verified unchanged after execution. Independent source-only reviewer confirmed
both localized fixture defects and remaining refusal-branch setup. Original
failures are preserved above; no assertions, tolerances or physical laws relaxed.
Standalone source test terminal0:11PASS,0.697613s,74248KiB peak. Six native room
faces/seven retained looks keep chart coordinates through actual three-axis
head effort, fresh cold restore, and byte-identical next motor/world successor.
1344 transient chart-array bytes, no persisted paint duplicate. Missing mapping,
singular/back-facing/PLANE registration and bounded work all refuse explicitly.
Other standalone tests (session78474 terminal0): illumination14PASS2.217644s,
native materials8PASS1.526767s, solar custody5PASS0.558440s, world21PASS1.635s.
Total59PASS. Highest observed process peak154072KiB.19335-site material timing
92.148ms is the existing UNIFORM-light path, not the unimplemented full spatial
illumination/material/aperture consumer. No full-frame realtime claim.

Read-only health envelope06:07:47 through06:10:47: us-east-1,
tfe-web-cluster/dsf-ai-service-lb,1553/taskec20ff084de54d48afab9a113647fa46,
image1d088eaaf195931a315e45c7ed456d4bb028210655e52eacad27e4445161612d,
counts1/1/0,RUNNING/HEALTHY,identity1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1,
live2343725->2344131,persist2343721->2344105,availabletrue,errorsnull,
durabilityfalse. CPU~51.5%,RAM~2.95%;existing guala-clock-stalled ALARM remains,
other four Guala alarmsOK. Caretaker35747 remained active, no A1 proof survivor.
No writes to live organism/service, no G1 source changes or process interference.

Next within SAME functional-body objective: compose registered pattern regions
with native surface illumination and finite-aperture material response. Do not
reopen source registration or use charts as occluders; clipping/first-match paint
remain consumer responsibilities. This seam is local backend-only evidence.
Ordinary body/home/caregiver/motor/sensory integration, copied-body restart,
resource/rehearsal/live acceptance remain OPEN. No new cognitive mechanism.
Goal ACTIVE; remote GitHub publication still permission-blocked, no retry.
Bedtime permission question sent for code/tests/engineering-ledger push only to
jcfunited-eng/TFE:a1/guala-functional-body, excluding credentials/checkpoints.
No answer as of this receipt; local work is not blocked by that external gate.

## FB-01ag — Current native sources to finite-aperture retinal light — 2026-09-26

Continue a3486d2b2 accepted source registration; previous goal turn PROGRESS.
Requested architecture: one native body/world geometry and current physical
materials/light produce six-band finite-aperture retinal evidence. No cognition,
identity inference, camera replacement or scripted motor change. Current reality:
uniform-light integrate_materials works; NativeOpticalSources, spatial lighting,
surface-patch geometry and room-chart registration are locally proved but not
yet composed. Conflict: missing consumer, not authority to substitute uniform
light. Approved float64 body optics only; no DSF evaluation/reduction. Existing
room-uniform ambient/single-bounce and point/directional-source approximation
remain explicit, not complete biological/global illumination.

Single correction: native_retinal_radiance(sources, apertures, error, bounds)
composes the existing physical laws. Source view comes from the one world
publication at expected_revision, full unfiltered native/material roster,
borrowed pattern objects, retained sun sample and original articulated frames.
One scene_geometry helper supplies existing native BOX faces, their original
primitive/axis/side addresses, curved primitives and planar visibility to both
the old uniform calibration operator and this actual-source consumer. No second
ray/visibility authority or retained scene.

Paint: retain native face ownership through existing disjoint planar regions.
Existing object patterns cover original unit BOX faces. Existing ordered room
looks attach only through explicit region_faces. Intersect each chart with the
actual visible panel, subtract its covered portion from subsequent looks, then
paint the remaining base coat. Reuse one convex-halfspace subtraction law with
visibility, and existing _material_regions for real cell boundaries. Paint is
never an occluding surface. Clip before summing; no overlapping double exposure.
Pattern palette values are reflectance coefficients; emission is the same
parent physical material emission, independent of paint. No pattern pixel
copy into the mount/organism, no silent registration fallback.

Integral law per surface contribution:
  mean_L = (1/Omega) integral_visible (R(q)*I(q) + E) dOmega.
The existing analytic halfspace integrator emits each region's area once via a
bounded transient generator; uniform radiance and real source composition share
that area law and packed plane classification. Native composition accumulates
reflectance-area and visible-area by actual face. On each reached patch the
existing illumination law supplies I_lower,I_upper, yielding lower/upper means
without losing paint/light correlation: R>=0, so integrated R times those
incident bounds encloses the true weighted contribution. No 2D point sampling,
invented clipped light or nominal camera preview.

Planar illumination patch: native face normal fixed. Its physical corner extent
bounds distance from face centre. Existing aperture dot extrema bound positive
plane entry; intersect with the actual finite face's radial extent. The central
plane intersection plus depth/chord bounds encloses every reached surface point,
even where the central ray misses the finite panel. If the enclosing whole-face
ball is tighter, use that ball and its own centre, not a mismatched smaller
radius. This is choosing between proved physical enclosures, not a heuristic
normal/identity threshold. Receiver row excludes only its own convex solid.

Curved resolved patches use the already-proved native surface_bounds with the
SAME classify entry enclosures and angular preparation. The sphere foreground
cap path retains analytic area and overlap uncertainty; conservative room/light
material bounds enclose unresolved cap surface lighting. Other unresolved
geometry uses [0, physical maximum radiance] and subdivides. No shape omitted.

Error/work: each receptor keeps an integral interval. Sum current frontier
intervals plus exact settled contributions; stop only when each six-band radius
is <= caller error. Otherwise split only uncertain remaining patches. Geometry
can remain partially unresolved only when its integrated physical contribution
fits that same error. Derive global maxima from material reflectance <=1,
declared emission, room ambient/bounce, lamp near-gain bound and retained sun.
No intensity clipping; overflow refuses. Float64 analytic bounds are NOT formal
directed-rounding certification; same approved numerical domain as predecessor.
Existing limits: <=256 primitives,19335 receptors,262144 total nodes,20 depths,
32768 halfspace/event scratch. Explicit shadow-work budget charged cumulatively
before each call, not reset every patch. Transient source/plane/area arrays only,
no persistent cache, extra clock, per-pixel decoding/hashing or lifetime growth.

Authorized files: functional_body_renderer.py (share scene/depth evidence),
functional_body_visibility.py (share existing convex difference),
functional_body_optics.py (share analytic region-area stream),
new functional_body_retinal.py (single physical consumer),
new standalone test_functional_body_retinal.py, this sprint ledger.
No functional organism, ordinary loop, neural kernel, anatomy, native state
schema, world mutation, caretaker, main G1 source or deployment change here.
Existing numerical primitives, lighting and material cell laws stay unchanged.
Uniform calibration is test-only explicit input, never fallback for unavailable
live native light. Production route must exclusively call actual-source consumer.

Lifecycle/field map: world.native_optical_sources(expected_revision) ->
immutable geometry/material/sun view -> transient geometry/paint/light integral ->
six-band image + radiance-error + work/depth evidence. Entire call read-only.
Refusal discards locals, world bytes unchanged. Fresh cold restore under SAME
declared environment reconstitutes view and must give byte-identical output and
next motor successor. Ordinary retinal RGB/pupil/motor wiring is not yet
connected; backend-only output must not be described as live sight.

Decisive offline path: real authenticated mechanical bench with complete native
biped, actual world lamp and retained materials -> finite-aperture image; real
head motor -> changed optical projection; cold fresh authority -> identical
image/error and next-motor successor. Independent analytic ambient-pattern
reference (including overlapping room paint and curved occlusion) and independent
MuJoCo ray intersections plus existing point lighting falsify variable-light
enclosures on small apertures; point samples are diagnostic only. Dark/emissive,
shadow, source-severed, unchanged bytes, hidden material admission, node/depth/
shadow-bound refusal covered. Regression uniform/native lighting/world/source
proofs stay mandatory. No pytest/network/production actions. Read-only AWS and
process envelope surrounds every proof block; retain exact handles to terminal.
Full19335 receptor timing is measured without claiming250ms in advance.

Translation/lean preflight: new source view contains no semantic sensory IDs;
primitive/face addresses remain internal world mechanics only. Six physical
bands retained to output, no DSF flattened. Share depth/angle calculations rather
than recompute. Share planar visibility and cell/solid-angle law; remove inlined
copies when extracting helper. Do not store diagnostic history. Nonblocking
findings stay ledger-only. Full native home/caregiver/motor/body-sensory,
copied-production-body/restart/resource/rehearsal/live gates remain OPEN.

FB-01ag completed implementation preflight — 2026-09-26 06:30Z.
One original geometry preparer now retains (primitive,axis,side) alongside native
faces; uniform calibrations and current-world consumer share it. classify exposes
its already-computed angular/depth enclosures without another solve. Existing
convex visibility difference extracted once and reused for paint precedence.
Analytic area stream reuses packed unique-plane classification, without storing
an all-region/all-pixel area matrix. Original uniform multiplication/sum order is
retained; division occurs after complete accumulation rather than per yielded
block, same float operation per output element.

New _CurrentLightIntegral is call-local physical operands only, not another
world owner or persistable scene. Ordered paint clips against actual native
panels; black zero-emission pieces are omitted only AFTER their physical geometry
has occluded the background. Current immutable pattern refs remain in world
custody; coefficient/halfspace arrays are bounded transient optical work. Planar
light groups by actual native face, only positive-reflectance rows request shadow
work; no reflected work for pure emission. Cap overlaps skip proven zero-area
pieces. Cumulative shadow count is a conservative primitive/source-row work
upper bound, not claimed walltime or exact native calls.

Added five standalone tests. The complete19,335-site ambient comparison reuses
the accepted explicit-uniform operator only as reference against a real no-lamp
world. Room paint has independent world-coordinate rectangles, overlap subtraction
and native ray occlusion witnesses. Variable light uses actual native ray distances
and the accepted point-light law, not injected sensation or body state. Applied
head motor, exact fresh constructor laws, cold image and next motor tested.
No runtime tests/imports/compiles executed before freeze. Existing world-source
proof helper is reused; no pytest/conftest. Whole ordinary-body acceptance stays
open. Independent frozen SOURCE gate is next; owner stops edits during review.

FB-01ag single localized SOURCE batch — 2026-09-26 06:39Z.
Independent review of frozen ce8f49eb625ca8352b2b18b4dfbf27a48912f848c772a0494ed67b6b9a7b436f
found no architectural defect. Corrections batched before any test/import:
(1) cheap packed shape/count/scalar/node admission BEFORE aperture value scans;
positive representable areas BEFORE scene/lighting construction. Added a no-scan
array sentinel and invalid-area-before-source-access falsifier, not a behavioral
mock. (2) Cold-image test targets were both black cells under row-down physical
paint, so small motion could truthfully leave the image zero. Target the two
actual white cells instead; preserve head effort and every cold/nextmotor check.
(3) Add actual zero-reflectance, positive-emission card in zero-ambient world,
with no other lamps and zero shadow-work budget. The card is itself a physical
emitter; neither it nor its light is invented/suppressed. Preserve world bytes.
Seven focused tests now; no new runtime law, authority or parameter adjustment.

Operator misses preserved: owner guessed absent test_functional_body_renderer.py;
reviewer guessed absent docs/guala_functional_body_sprint_impact_ledger.md.
Both read-only rg exit2; no tests or state changes. Actual paths resolved by
rg --files / git status before execution. A default sandbox ps exposed only its
PID namespace, not host processes; no host-terminal inference used. Corrected
with escalated read-only host census06:30 (only caretaker35747). Read-only
AWS06:29 same1553/ec20ff,live2346746,errorsnull,existingclockALARM.
Final freeze/source check next; owner stops after this one localized batch.

FB-01ag first focused execution — 2026-09-26 06:41–06:44Z.
Exact session15073 terminal exit1: seven tests, five PASS, two fixture ERRORs;
0.627s,161400KiB peak. Runtime source unchanged from frozen SOURCE gate
10db4bf79ad71797a6c59971531d840cfbd638d7782bee15d00f43479d5f7bdc.
(1) Ambient reference passed numpy.float64 values where PlanarMaterial requires
Python float/int. Explicitly convert the independent reference inputs to float.
(2) Ordered-room test declared a one-color one-cell ObjectOpticalSurface, but
existing world law requires >=2 unique colors, all used. Replace with actual
2-column RED/GREEN and GREEN/RED patterns; independent world-coordinate cell
rectangles compute ordered overlap. Admit exact8 unique source cells (card4+
looks2+2), no resource-law change. No acceptance assertion/tolerance weakened;
all source, optical, bodily, sleep/cognitive and production laws untouched.
These two fixture failures do NOT prove/refute the full-retina consumer yet.
Five already-executed source/severance/resource/head/cold checks passed.
Read-only AWS06:40/06:44 same1553/ec20ff/digest1d088e,live2348409->2348998,
persist2348393->2348969,errorsnull,counts1/1/0; CPU51.28%,RAM2.915%; existing
clockALARM persists. Caretaker35747 active; only observer/no A1 proof survivors.
Correct fixture declarations only, preserve failure, then rerun exact focused
suite before any broader proofs or integration.

FB-01ag second focused result and exact occlusion diagnostic — 06:47–06:49Z.
Session20426 terminal exit1:6PASS/1FAIL. Complete19335 ambient image agreed with
accepted physical integral in54.331ms,depth0,nodes19335,radius6.94e-17. Total
0.765s,peak173640KiB. Remaining failure was the independent native-ray guard:
room-look pencil hit the real nearer card, invalidating the unoccluded reference.
Bounded9ray diagnostic exit0 proved6/9 hits card/surface at0.419–0.427m rather
than wall-xmax. Eye(1.08,1,.96),cardfrontx1.49,y[.9,1.1]. Actual renderer
correctly included foreground-card light; no runtime error hidden by the guard.
Move the declared two room looks and their diagnostic targets/independent
rectangles exactly+2m in worldy, keeping dimensions/palette/overlap/aperture.
New minimum pencil azimuth atan(1.9/3.92)-.045 > .406rad, yielding card-plane
y > 1+.41*tan(.406) > 1.176m, strictly outside cardy<=1.1. Thus all pencil
rays clear that blocker without excluding/removing it. Native all-wall guard
remains unchanged; production occlusion and source files remain unchanged.
Read-only06:47:49 same1553/ec20ff,live2349474,persist2349449,errorsnull;
CPU50.87%,RAM2.956%;oldclockALARM;caretaker35747active,noA1survivors.
Other-agent short diagnostic37158 and publisher37203 appeared in preceding
06:47:13 census and ended before06:47:49; no signals sent or authority claimed.

FB-01ag accepted local source/physical consumer — 2026-09-26 06:53Z.
Final SOURCE check and post-proof freeze unchanged:
5eb7c53ba55dad57a64ab1effe189a8f4797c01a71e0b418e9dd8a338ce9cf5f.
Runtime source was not changed after first independent final SOURCE acceptance;
only the disclosed invalid proof declarations were corrected. Source retinal
SHA2561330e169e71713783e43c94d8f2bd58d4218c8918f8015c8dbe1de0ab91a570b;
test28fe6dedd2df7728f06943d540e0c0114465f0c987d0462a512005ea1f4d8859.

Focused session59206 exit0:7PASS/0FAIL,0.746s,173516KiB peak.
Complete actual-source ambient field19335sites48.948ms,19335nodes,depth0,
maxradiance-radius6.94e-17; independent accepted uniform reference agrees.
Ordered two-color overlapping room paint uses independent world rectangles;
all native wall-ray witnesses clear actual nearer objects. Actual lamp
witnesses, dark/emissive/source-severed cases, cheap admission, resource refusal,
real head effort, unchanged state, cold image and next motor all pass.
Existing standalone regressions session68609 exit0:73PASS (5optics+5visibility+
4materials+8native-material+14illumination+11sources+5solar+21world). Together80.
No pytest/conftest, network transport or live authority imported/executed.

One complete VARIABLE-light resource proof session94139 exit0:
actual bench(), query(), retinal_apertures(), draw(sources,apertures) with
default ERROR1/510,max_shadow_tests20000000,max_nodes262144,depth20; no altered
anatomy or uniform-light substitution. 50nativegeoms,1actualworldemitter,
19335receptors. 526.773ms,35383visitednodes,depth8,maxradius0.0019094197425,
zero unknown-geometry area,peak169720KiB. Six-bandmax0.7328170558, all finite
nonnegative; encoded world unchanged. This is NOT250ms, production latency,
a full-home benchmark or ordinary-organism integration proof. Bounded scratch
and work refusal observed; no retained frame/cache/state added.

Read-only AWS06:50:58/06:52:50 same1553/ec20ff/digest1d088e,counts1/1/0;
live2349944->2350221,persist2349929->2350217,errorsnull,availabletrue,
durabilityfalse; CPU51.19%,RAM2.94%; oldclockALARM remains. Caretaker35747
continues; all A1 handles terminal, no A1 proof survivors/signals/live writes.
Other-agent diagnostic39875 observed at postcheck; did not alter/interfere.
Measured timing is local shared-host evidence, not exclusive-core throughput.

Disposition: current-source optical consumer LOCALLY EXERCISED; ordinary-loop
mounting, actual complete home/caregiver/motor/body-sensory integration, copied
production body, restart/resource/rehearsal/live acceptance remain OPEN.
Next bounded FB-01ah: identify/remove proved non-causal work on this complete
spatial-light path and preserve exact physical interval output before ordinary
retinal-loop mounting. Do not reopen source custody/paint law or expand sight
anatomy/cognition. No weakening error/resource/occlusion to claim250ms.
GoalACTIVE; local commit only; remote push permission remains outstanding.

## FB-01ah — Compiled body-optics primitive evaluation — 2026-09-26

Previous turn PROGRESS:5b3900e06,80offline checks, complete variable-light
field526.773ms. Continue SAME body-optics latency boundary; no reopening
source custody, geometry, paint, lighting, error budgets or cognitive scope.
Current clean source verified. Requested unchanged physical output at lower
cost. Conflict: elapsed cost exceeds250ms, not a missing physical law.
No DSF is evaluated/reduced. Body-only float64 approximation already approved.

Measured diagnostic1730 exit0:303161calls,0.599profiled seconds,35383nodes/
8depths,170816KiB. NativeIllumination._visibility_bounds326ms, paired primitive
intervals266ms, sphere_interval201ms, NumPy reductions95ms. A second bounded
count12539 exit0 showed16887/16942 receiver rows have positive possible direct
light; dropping proven-dark rows removes55only. Do NOT repeat rejected FB-01ac
row compaction or add geometric culling tolerances. Both probes leave world
bytes unchanged; no live calls except read-only AWS envelope.

Exact correction: port the ALREADY ACCEPTED analytic convex primitive
interval/normal law to one pure bounded function in the EXISTING guala_core
compiled extension. No MuJoCo shadow-model mutation or second physics service.
NumPy still supplies the same full-shaped world-to-primitive transforms, so
matrix-rounding order stays unchanged. Only local root/normal arithmetic moves.
Sphere/capsule/cylinder paired radii share identical ray coefficients; ellipsoid
scaled rays remain distinct. Expanded and contracted roots computed separately;
no inclusion inference, AABB, epsilon, fast-math, fused multiply-add, or missing
intersections. Preserve np min/max NaN and tie/signed-zero semantics, source
operation order, cap union and cylinder/box normal ownership.

Impact path: NativeOpticalSources -> same NativeIllumination and renderer
entry/surface geometry -> interval/interval_pair -> packed-buffer body kernel
-> same interval arrays -> same shadow/retinal light/radius/node trajectory.
Single and paired optical callers use the SAME primitive law. Retire old Python
root/primitive implementation from runtime; retain exact predecessor ONLY in
standalone differential evidence. Original legacy optical_raycast and canonical
DSF/neuron functions are not reused or modified. Existing library registration
adds only the new body function.

FFI contract: one primitive kind, finite original local origins/velocities,
positive admitted dimensions, optional paired dimensions, optional exact
surface normal request. Native float64 contiguous buffers, shared1row or Nrow
origins/sizes; N<=262144, at most2intervals or1surface record per row. No
per-point Python tuple/float unpack, no array-to-list conversion. GIL retained
while borrowing input buffers (no concurrent pointer access or callbacks).
One immutable packed byte result; NumPy views it without a second data copy.
All temporary scalar state is per ray; no retained scene/cache/owner/threads.
Output bounded by2*N*2*8 orN*8*8bytes. Invalid input or allocation/normal failure
returns before any state publication; world/read side stays mutation-free.

Cold/persistence: no schema or law/state header changes. Source geometry and
body bytes unchanged; exact image, radiance intervals, refinement counts, cold
next motor and existing conservation proofs must remain equal. No production
fallback to Python if the compiled function is missing. Docker's existing
native-builder already copies/builds the complete native/guala_core tree;
only two registration statements in lib.rs may change. Build an isolated
temporary wheel/target; never overwrite G1's installed extension or task.
Existing published production code remains untouched.

Authorized files: new native/guala_core/src/body_optics.rs; src/lib.rs(module
and registration only); functional_body_renderer.py(retire interpreter root
dispatch/use packed kernel); tests-only predecessor reference; existing
standalone illumination proof(adapter for moved reference and work evidence);
new standalone native-kernel contract proof; this sprint ledger. No Cargo
dependency/kernel/DSF/law changes, no caretaker/organism/state/interface change.

Acceptance: frozen independent SOURCE gate before compile. Compile isolated
locked/offline existing Rust crate. Prove loaded extension path is that build.
Compare accepted Python intervals and normals bit-for-bit on all five shapes,
common/per-ray origins, paired radii, finite/parallel/missing/tangent and adjacent
float cases, capsule junctions, rotations, invalid buffer/shape/bound refusal.
One native batch per primitive; no per-ray Python dispatch or persistent work.
Run same actual-world head/cold/material/illumination/retinal proofs; paired
complete19335-site resource comparison with accepted5b3900e06 through its exact
test-only predecessor implementation. Require image/error/node/depth/unknown
arrays identical and improved total time, not just a microkernel result.
No250ms claim unless complete measured path passes. Full home/ordinary-body/
copied-production/restart/rehearsal/live gates remain OPEN.

Read-only06:56:22/06:56:57/07:01:33 same1553/ec20ff/digest1d088e,counts1/1/0,
live2350737->2350821->2351494,persist2351465last,errorsnull,CPU~51%,RAM~2.97%;
oldclockALARM persists. Caretaker35747 active, allA1probehandles terminal.
Other-agent small diagnostic40827/41922 observed and ended; not signalled.
Operator path miss preserved: guessed rootDockerfile/pyproject and historical
deploymanifest absent, rgexit2; stopped that path and resolved exact files via
rg--files. Actual closure dsf_ai_service/Dockerfile and native/guala_core/
pyproject.toml; do not reuse guesses. No networkwrites or GitHub push.

FB-01ah implementation preflight — 2026-09-26.
Pure compiled primitive source replaces107lines of interpreter interval/root
dispatch with one buffer adapter; old arithmetic lives only in tests reference.
Existing lib.rs diff is exactly module+registration; no dependency or canonical
function body changed. All world-to-local transforms, geometry/paint/light and
retinal area/subdivision code unchanged. Native borrows finite typed buffers
under held GIL, initializes bounded bytes, calls no Python, stores nothing.
All source/test callers of removed helpers resolved; illumination's independent
predecessor imports tests-only reference. Old dot-call count proof replaced by
actual packed-native-batch count and zero per-array Python primitive dispatch,
still requiring predecessor visibility equality. Native proof requires exact
candidate-extension path and byte equality including signed zero, not tolerance.
Full output/persistence/refinement equivalence and whole-path resource proof
remain mandatory. No candidate compile/import/test has occurred yet.

FB-01ah accepted locally — 2026-09-26 07:24Z.
Independent SOURCE review classified one LOCALIZED finding: normal admission
wrongly rejected infinite exit range despite finite positive entry. Preserved
the accepted law exactly; added finite-input overflow/NaN and infinite-exit
byte comparisons. One correction batch, final SOURCE PASS, no architecture
rejection or tolerance change. Final freeze and post-proof verify identical:
558261063e0e29b1a7a34c6116806944378b5d92c62131328ca07e7a1c06e621.

Isolated locked/offline release build session45295 exit0,19.00s,one Cargo job.
Root /tmp/guala-body-optics-native.U8I8en; no global/G1 extension overwrite.
Rust1.97.1,maturin1.14.1,CPython3.11,existing PyO3 0.23.5. Wheel SHA256
efc7cc445f18edef9cde9dcf57b2c91e4d16ac49954601866ed63e433da29fae;
loaded guala_core/guala_core.cpython-311-x86_64-linux-gnu.so SHA256
b3d1c01707bbbb9609486dbfe7a9516fa8336e3a5f627a81c4e69431469176bd.
Direct path printed from isolated extension, not prior installed candidate.
Build target78MiB retained for active integration recompilation; wheel368KiB,
installed candidate904KiB. No background compiler/proof survivors.

Native boundary5PASS/0FAIL,0.01489s:28800 primitive bound values byte-identical,
allfive normal laws, zero/parallel/tangent/missing/adjacent-float, finite overflow,
invalid buffers/resources. Whole actual-lamp paired comparison session65481 exit0:
same19335sites,50geoms,35383nodes,depth8,maxradius0.0019094197425049142,
zero unknown area. Accepted Python514.177ms; compiled288.646ms (1.78134x).
EVERY image/radius/unknown byte and refinement count identical; world bytes
unchanged. Peak172020KiB. This is a local shared-host measurement, NOT250ms
or full-home/ordinary-body/production timing. Error/resource limits unchanged.

Remaining standalone regression batch8022 exit0:80PASS
(14illumination+7retinal+5optics+5visibility+4materials+8native-materials+
11source+5solar+21world). Together85PASS including newnative5.375 independent
native ray witnesses, physical head movement, fresh cold image and next motor
remain valid. Illumination's paired512-row proof calls49 packed native batches
instead of120832 interpreted dot-row work; no per-ray Python dispatch.
Max measured regression peak175904KiB. No pytest/conftest/live test authority.

Read-only AWS07:18:46/07:21:17/07:22:09/07:23:03 same1553/ec20ff/digest1d088e,
counts1/1/0,RUNNINGHEALTHY;live2354025->2354662,persist2354633last,
identity unchanged,errorsnull,durabilityfalse;CPU~51%,RAM2.966%.
Existing clock-stalled ALARM remains; otherfouralarmsOK. Caretaker35747active.
All A1 handles terminal; host census shows no proof/compiler survivors.
No G1 source/process or live service change; remote push still permission-blocked.

Disposition: compiled same-law primitive execution LOCALLY EXERCISED and closed.
No further helper-only optimization pass. Next bounded FB-01ai is ordinary
native retinal consumption: preserve real head geometry/current sources and
existing pupil/gain/clipping/saturation contract, retire any upright-root
reconstruction for mounted bodies, prove the same ordinary sensory consumer.
The remaining latency gap stays OPEN in the full body acceptance; integration
does not grant production permission or erase it. Full home/body/caregiver,
motor/sensory, copied mature-body, restart, resource, rehearsal and live
acceptance remain required. No speech/cognition/retina expansion. GoalACTIVE.

## FB-01ai — Ordinary native retinal consumption — 2026-09-26 07:40Z

Previous turn PROGRESS:bfe525bb4,85standalone passes, exact complete-field
514.177->288.646ms. Continue authorized FB-01g body integration. No reopening
of optical source/paint/light/interval laws; no further helper optimization.
Requested architecture: actual articulated head pose -> current world light ->
existing ocular transducer -> existing sensory consumer, one world revision.
Current ordinary _world_retina_u8 still uses upright root plus legacy neck.
Conflict:YES for a mounted articulated body. Do not extend upright rendering
for native mounts or substitute a camera preview. Existing unmounted live body
keeps its current law. No cognitive selection, speech, caretaker or ingress edit.
This is approved bounded numerical body optics, NOT full joint DSF evaluation.
Six spectral bands still enter the existing pairwise RGB transducer; no new
DSF reduction. Fine geometry is the already-declared primitive/aperture model.

Exact seam and ownership:
- Add one fixed mono camera to reference anatomy XML on the actual head,
  local origin(.08,0,.03)m,10mm in front of its .07m head surface.
  This is declared virtual receptor placement, not human anatomical calibration.
  Fixed camera right/up/back basis maps to optical forward/left/up as
  [-C[:,2],-C[:,0],C[:,1]]. No rendered camera framebuffer is used.
- NativeBody resolves the unique self-subtree fixed/no-target camera once from
  immutable model anatomy. No new retained state, state schema, clock or owner.
  Current cam_xpos/cam_xmat come from the same mj_forward endpoint as geometry.
  Missing/multiple/tracking cameras explicitly refuse; never choose by name.
- Eye-relative typed yaw/pitch compose Rhead-camera*Rz(yaw)*Ry(-pitch).
  Existing neck axes MUST NOT be added again. retinal_carriage gains a typed
  include_neck option(defaultTrue keeps all existing callers unchanged).
  Lid validation/transmission and eye ranges remain the existing law.
- Existing native_optical_sources admits an explicit retinal-rotation request
  instead of diagnostic frame/origin. Shared source/query/publication lock,
  current world revision, full native geometry, current materials and retained
  solar sample; no new wall-clock sample, horizon roster or separate scene.
- Existing canonical UPGRADED_RETINAL_SITE_GEOMETRY supplies fixed readonly
  aperture anatomy once on native optical-module import. No new retinal sites
  or per-beat grid rebuild. Test-only historical grid remains independent witness.
- _world_retina_u8 branches ONLY on actual snapshot.native. Native requires
  the authoritative world and mounted camera, obtains six-band radiance from
  accepted native_retinal_radiance, then uses the SAME pupil/gain/pre_clip/
  transmission/rint/saturation packing code. Ordinary _advance selects this
  branch; legacy call signature and output remain unchanged.
- Native radiance can exceed1 before the real RGB saturation stage. Unlike
  old W1's intermediate clipped/quantized surface values, native input remains
  nonnegative float64 until existing RGB/pupil saturation. This is an explicit
  body-optical producer correction, not a claim of legacy-native image equality.
  1/510 six-band radiance error remains; pupil gain can amplify it, and gain
  thresholds are discontinuous. Do NOT claim half-bin/exact final-byte accuracy
  against an exact real optical field. Mask is producer-origin for the admitted
  numerical transducer value, not inferred from byte212 or claimed unclipped truth.
- Existing focal/ambient slicing, camera replacement and OpticalEvidence reach
  Sensed unchanged. Source geometry/camera addresses never become sensory labels.

Cold/rollback: XML identity changes with declared camera. Fresh camera-equipped
mounts restore exactly; camera-less old XML remains camera-less and refuses
native retinal use. Never rebind old integration bytes to new XML. World source
reads and transduction are read-only and finish before a result is exposed.
No new persistence record or cached image. Full ordinary MOTOR/energy/feedback
mounting remains separately required within FB-01g; this read path does not
certify a complete native ordinary beat or autonomous head/motor learning.

Authorized source: functional_body_anatomy.py, functional_body_native.py,
embodiment_world.py(native optical query only), functional_body_retinal.py
(fixed aperture anatomy only), guala_world_sensorium.py(retinal_carriage only),
guala_functional_loop.py(retinal producer and its call only).
One new standalone sensory-consumption proof and this existing ledger.
No organism-state/choice/memory/energy law changes; no production mutation.

Acceptance: independent SOURCE gate before import/tests. Actual mounted camera
after real multi-axis head effort must change ordinary RGB, with point origin/
basis agreeing with native transforms; eye-only turns compose once, changing
legacy neck values alone cannot steer native sight. Real current light/patterns
reach the existing Sensed/FunctionalOrganism.decide consumer; this is local
sensory use, not full native settle or cognition evidence. Cold world/camera/
pixel+mask equality and next motor remain exact. Missing/ambiguous/wrong-mode
camera, stale revision, mixed query modes and absent world fail closed.
Native oversaturation packs true producer bits; legacy pixels/evidence preserve
their prior law. Whole19335-site caller measured once including conversion;
resource limits unchanged. Source query cannot mutate world.
No pytest/conftest/network execution. Pre/post AWS/process envelopes required.
Copied mature-body, full-home/caregiver, joint-feedback/motor, paired restart,
package/rehearsal and live gates remainOPEN, as does250ms on the complete path.

Read-only preflight independent optical_reference_review confirmed camera basis,
self ownership, exact installed MuJoCo header fields and XML identity change.
Two owner path guesses failed before edits: functional_body_mount.py does not
exist (mount is in embodiment_world.py); thermally_coupled_world.py does not
exist (actual thermally_coupled_embodiment_world.py). Do not repeat guessed
reads; resolve unknown file names with rg--files before named-file commands.

### FB-01ai owner translation/preflight review — 2026-09-26

Previous goal turn was status-only (NO PROGRESS). Current exact baseline
bfe525bb4, a1/guala-functional-body. Source owner stops at freeze.
One repeated bootstrap mistake: require-guala-root returned65 for the known
absent July31 handoff. The existing FB-01y rule remains authoritative:
preflight existence, use explicit Git root/HEAD and this modern sprint ledger;
do not recreate old authority files. No runtime command ran from that failure.
An earlier JS patch-construction SyntaxError occurred before any file write;
corrected tool syntax only. Neither failure changes physical evidence.

Translation/evidence map: immutable head camera -> current mj_forward
cam_xpos/cam_xmat -> OpticalGeometry (world origin/basis, full primitive roster)
-> same-revision NativeOpticalSources (retained materials/light) -> accepted
six-band aperture mean -> existing pairwise RGB/pupil/pre_clip/mask -> unchanged
Sensed focal/ambient/evidence fields -> existing real decide consumer.
No camera/frame/primitive address enters cognitive identity. One static
19335x4x8=618720byte aperture anatomy, not repeated per beat. Native transform
restores scratch, does not write world. No persistent optical cache or schema.
Head motion proof supplies declared external motor effort; not learned motor
control. Test drives real producer/consumer, NOT a full ordinary native beat.
The ordinary _advance call now selects the native producer; full motor/energy/
feedback mounting is still required before end-to-end production proof.

First-use camera anatomy and fresh restore use XML-bound native identity.
Old camera-less bytes restore unchanged and refuse native retinal consumption.
Camera-less fallback, ambiguous/tracking cameras, stale revisions and mixed
query modes must fail without changing encoded world. Static resource ceilings
are the accepted consumer envelope, not proof of full-home admissibility.
Numerical interval radius is NOT final-byte/saturation certainty; no downstream
radius field invented. Existing evidence describes admitted numerical producer.
Pupil comment corrected to disclose native overrange clipping; law unchanged.

SOURCE review precedes all imports/tests. The native primitive binary is the
accepted bfe525bb4 isolated build, not the globally installed G1 extension.
Proof environment must identify its actual loaded file; full new caller timing
and peak RSS are local measurements. No live writes/pytest. Before/after AWS
and exact process census required. Remote push remains blocked; no bypass.

FB-01ai source/proof record before final execution:
- SOURCE gate8f9ddfb4 PASS, owner edits stopped during independent review.
- session44923:5PASS/1ERROR before head motion: test supplied roll,pitch instead
  of canonical pitch,roll addresses. Corrected test only; same efforts/duration.
  Final source confirmationc38a3b59 PASS. Removed unused import and relabeled
  printed58005 count as u8_values, not Python allocation bytes.
- session24683:5PASS/1FAIL. Actual multi-axis head motion changed retinal bytes;
  fresh cold image/evidence and current world bytes identical. Final raw Python
  receipt equality failed on lamp emission(0,0,0,0,0,0) versus().
  Established EmbodiedObject.as_record/_canonical_record omit all-zero emission;
  decoder restores(). Native source resolution expands both to identical zeros.
  No runtime or codec change. Use complete authenticated as_record equality,
  explicit only-zero-emission-alias assertion, exact native_work and next world
  bytes. Independent reviewer classified LOCALIZED proof equality mismatch.
- Diagnostic session48431 terminal0: complete receipt record equalityTRUE,
  native_workTRUE,cold world bytesTRUE,next entire world bytesTRUE; raw Python
  receipt equalityFALSE. No fields discarded and no physical law relaxed.
- Both failed sessions retained; no broad regressions ran after first failure.
  A read command also guessed absent tests/test_functional_body_mount.py.
  Resolved actual test_functional_body_world.py with rg--files; no such guessed
  path should recur. Runtime source remains identical to reviewed8f9ddfb4.

Host coordination: other-agent pytest64546 initially active. Actual capacity
20CPU,~24GiB available, no cgroup CPU/memory cap; focused3s/<218MiB correctness
run safely coexisted, not a production timing qualification. Other suite was
gone by07:55 census. No signaling. All A1proof handles terminal after runs.
Read-only07:53:49..07:57:40 live1553/ec20ff/digest1d088e unchanged,counts1/1/0,
live2359077->2359641,persist2359049->2359625,errorsnull. Caretaker35747 untouched.
OldclockALARM remains, other4alarmsOK. Fullbody and250ms gates stillOPEN.

### FB-01ai local verification — 2026-09-26 08:03Z

Final source/test fingerprint5058ba2f91323cf56393d33e5da11c58633bb994ba01c007cf6cdd76a5199d1a
independently confirmed, verified again after execution before this append.
Runtime source unchanged after initial source PASS. Both test-only failures
and their precise corrections are preserved above; no physics, codec or
acceptance boundary changed to hide a failure.

Standalone session83805 terminal0:82PASS in8.433355s,peak225160KiB:
6new sensory-consumption,25native mechanics/interface,7anatomy,21world/heat/
optical custody,11source custody,7retinal integration,5compiledprimitive.
Loaded exact isolated bfe525bb4 native binary
/tmp/guala-body-optics-native.U8I8en/python/guala_core/guala_core.cpython-311-x86_64-linux-gnu.so
SHA256b3d1c01707bbbb9609486dbfe7a9516fa8336e3a5f627a81c4e69431469176bd.
No pytest/conftest,network writes,global extension replacement or build.

Actual19335-site mounted world -> ordinary RGB/mask producer -> real existing
Sensed/decide path exercised. Complete producer292.892732ms,58005u8values,
static aperture618720bytes. Real multi-axis head effort changes pixels;
eye rotation applied once; old neck coordinates do not steer native camera;
cold image/mask and complete authenticated next receipt/native work/world
bytes identical. Missing/ambiguous/tracking camera/stale/mixed modes refuse.
Legacy pixels/gain/masks unchanged. Native overrange radiance clips only at
existing transducer. No local-preview substitution, output byte oracle or
new cognitive decision law.28800primitive bound comparisons remain exact.

292.9ms exceeds250ms: latency gateOPEN, not production/full-home timing or
whole-body interval. Body camera is SOURCE/runtime-reachable/LOCALLY EXERCISED;
no full native ordinary motor beat, learned gaze, autonomous climbing, full
DSF-neuronal delivery or live mount is claimed. Fixedcamera changes XML-bound
anatomy; old camera-less native snapshots are not silently migrated.

Final before/after readonly AWS08:01:12..08:02:04,us-east-1,
tfe-web-cluster/dsf-ai-service-lb,task1553/ec20ff084de54d48afab9a113647fa46,
image1d088eaaf195931a315e45c7ed456d4bb028210655e52eacad27e4445161612d,
counts1/1/0,RUNNINGHEALTHY,sameorganism1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1,
live2360157->2360285,persist2360137->2360265,errorsnull,durabilityfalse.
CPU51.07->51.23%,RAM2.979%;oldclockALARM persists,other4OK.
No A1test/compiler/diagnostic survivor in08:02:20 escalated census.
Caretaker35747 unchanged. No production or G1 source/process changes.

Disposition: close FB-01ai only. Next FB-01aj connects the approved existing
motor/feedback/energy seam through the ordinary functional loop. Reuse prior
FB-01g source map; do not re-open optical law or add another helper-only pass.
Acceptance remains authentic applied joint effort -> local measured afference
consumed by the same organism -> retained performed trial and energy/heat ->
paired cold successor. Preserve historical learned records, no aliasing root
acts into joint experience, no scripted gait/controller or separate brain.
Fullhome/caregiver/copied mature-body/resource/rehearsal/live gates required.
GoalACTIVE, remote publication permission still outstanding; no retry/bypass.
## FB-01aj — Ordinary anatomical motor/feedback integration contract — 2026-09-26

Previous goal response was NO PROGRESS (bedtime permission/status reply).
This resumes the approved FB-01g port extension from clean c2c7f219a.
FB-01ai remains closed by its 82 local checks; its 292.893ms optics result
does not meet 250ms. No further isolated optical tuning in this item.

SOURCE findings: FunctionalOrganism still has 22 fixed streams, a 64-choice
ceiling, old root-pose candidates, and migrate() deletes unfamiliar streams.
The native body already supplies 228 scalar self-sensor components, localized
contacts, and sparse absolute effort commands whose unmentioned settings persist.
Zero effort must therefore be available for every motor. No command is a gait.
Body numerical approximation and this interface are approved. Existing per-stream
regime/sign reduction and scalar learner remain explicitly reduced cognition;
neither is being certified as full joint DSF or neuronal learning.

Single implementation owner A1. Authorized source: functional_body_native.py,
one small functional_body_interface.py for typed anatomical coordinates,
embodiment_world.py (read-only mounted interface accessor), functional_organism.py
(port binding, streams, native candidate branch, preserved historical keys),
functional_loop.py (same-world feedback, measured supply/heat and commit order).
Focused standalone test plus the existing retinal consumer's required new Sensed
arguments. No kernel, learning equation, caretaker, ingest, UI or deployment edits.

Contract:
- Native compiler derives immutable sensor kind/unit/dimension, anatomical
  surface addresses and actual direct motor limits once. One bounded roster is
  retained by the organism to interpret its rolling windows after restart.
  Equal component counts do not establish anatomical identity. Changed rosters
  refuse; existing STREAMS and all historical choice keys remain unchanged.
- Actual signed SI samples enter paired nonnegative coordinates (positive and
  negative parts, unit scale one SI unit) before the unchanged positive-input
  kernel. No abs-only, clipping, guessed offsets, synthetic readings, or added
  sensory rounding. Legacy six-decimal rounding and sleep law remain unchanged.
- Contact input is a declared surface-level load approximation: each actual
  point force and moment about its link origin is split by sign before summing.
  Opposing pressures do not cancel. Raw point contacts remain in Sensed/native
  observation and pre/post trial evidence. This projection loses fine pressure
  distribution in the DSF context, not the raw physical evidence. It is NOT
  caregiver affection, material texture or a new emotion/reward scalar.
- Three direct absolute settings per motor (declared lower, zero, upper),
  each with a distinct anatomical action ID. Omitted settings persist, allowing
  multiple recruited joints across ordinary decisions; no sequence/composition
  controller. The bound is derived from actual motor count, not truncated at64.
  Old root Move/Grasp/Release candidates are absent on a mounted body. Existing
  oral/reflex world refusals stay truthful until their separate mount is lawful.
  Empty-command rest/sleep/voice preserves effort and is NOT claimed relaxed.
- Same prepared world/thermal authority advances exactly one existing beat,
  with available work and basal heat from the existing organism reserve.
  All fallible voice/energy/organism commit preparation occurs before world
  publication. The single actor publishes/checkpoints only successful results.
  Any failure is fatal to that in-memory pair; it is restored from its existing
  paired checkpoint, not continued or newly checkpointed. No per-beat brain copy
  or new transaction owner. Native scratch is reusable, never authoritative.
- If a new command is refused, its unchanged persistent motor settings may still
  do physical work during the passive interval. Account for that measured work,
  preserve the refusal, and do NOT record the refused command as executed.
- Actual predecessor/successor local feedback accompanies recorded transitions;
  no external geom IDs/global frames/hidden positions are new body senses.
  Current memory/sleep/admission/eviction equations remain unchanged. No automatic
  retention bonus or claim that mere movement learns balance/climbing.

Proof required before this seam is closed: ordinary unmodified decide/choose
selects distinct anatomical effort, actual mechanics/energy/heat advance, next
ordinary sense consumes measured local return, recorded performed action keeps
its identity; paired fresh cold restore yields identical next world/organism.
Also old memory keys/bytes survive admission; missing/stale/mismatched feedback
refuses; all zero choices exist; persistent other efforts survive; no legacy
root motion candidates; no full-field/neuron/gait claims. Quantify full roster,
encoded bytes, runtime/memory and mature-window cost rather than claiming250ms.
Use a real isolated declared world first, not mocked decisions. Production-copy,
complete home/caregiver/contact/oral/resource/rehearsal/live gates stay required.
No pytest/conftest/live-write imports. Freeze then independent source review,
then bounded proof under before/after read-only AWS/process health.

GitHub publishing remains permission-blocked. No retry or bypass.

### FB-01aj rejected by ordinary execution — 2026-09-26 08:55Z

Final SOURCE review passed frozen58de7561cd1438256c3c1dbfccf15dd9343bb323f007465175c6727e3c58fbb8
after one localized batch (finite moment check, linear exact hashes, compact
lossless raw evidence, ns timing proof, truthful requested motion and refusal proof).
That SOURCE result did NOT predict successful execution.

First decisive ordinary-loop test session50914 exit1,0.719s:
test_ordinary_motor_return_energy_trial_and_paired_cold_successor failed at
world_action_refusal:joint limit overrun exceeds declared resolution.
Actual ordinary selection:torso roll -28.627763055836986N m. No execution
assertion was weakened. Subsequent unchanged six-decision diagnostic78326 exit0:
roll−/zero/+ thenpitch−/zero/+; all nonzero refused, zero passed; actual motion
and motor work stayed zero; basal work remained real and debited.

Bounded unchanged-law endpoint census30463 exit0,1.233656643s,peak149056KiB:
64motors ×2actual capacity endpoints ×250ms, same pristine zero-gravity bench,
actual organism motor supply. All128 refused:120joint-limit,8penetration.
Earliest refusal1ms; latest81ms. Torso roll reaches-.532852257rad at27ms,
past-.5rad stop by.032852257rad (declared tolerance.03rad).
Complete measurements: docs/evidence/FB-01aj-endpoint-loads.json.
These are diagnostic refused candidates, NOT lived action evidence.

Disposition: reject FB-01aj as an executable integration candidate; preserve
complete source patch at docs/evidence/FB-01aj-rejected-source.patch and restore
ONLY A1 candidate executable files to accepted c2c7f219a. The two new candidate
files are removed from executable paths and recoverable from that patch.
No production/G1 source/process change. Do not promote the three-level
zero/full-strength vocabulary or simply lower forces/raise safety tolerances.

First cause to resolve inside the same body objective: declared direct effort,
held over250ms, is incompatible with current soft stop/contact response and
numerical resolution. ExistingFB-01f proof covered passive ground contact and
small digit effort only; it explicitly did not certify these active loads.
Its old2/4/8/20ms stop and .05–1ms floor tests are NOT repeated as new findings.
A source-only seam audit cannot certify a physical load domain.

Single next item: a bounded offline active-load response map, preserving forces,
mass,geometry,damping and error tolerances, varying only explicitly reported
joint/contact response and integration resolution. The default model must
reproduce the above refusals. No new gait, pulse policy, decision law, reordered
actions, cold schema or production mechanics until a derived numerical contract
and full end-to-end body proof exist. Body-only numerical approximation remains
authorized; no joint DSF/neuron/cognitive authority claim.

Read-only AWS08:45:38->08:51:53: same1553/ec20ff/digest1d088e,1/1/0HEALTHY,
live2366305->2367047,persist2366281->2367017,errorsnull,CPU~51.2%,RAM~2.98%.
OldclockALARM persists,other4OK; caretaker35747 untouched. All three A1test/
diagnostic handles terminal; health census found no proof/compiler survivor.
No general resource or production claim. GoalACTIVE; GitHubpush still blocked.

### FB-01aj numerical map and exact guard-execution correction — 2026-09-26

Previous goal turn was status only (no progress). Continue FB-01aj mechanics
load qualification, not another optics/cognition project. Baseline remains
c2c7f219a, live1553/ec20ff/digest1d088e. GitHub push still permission-blocked.

48-case offline diagnostic completed session94027 exit0. Baseline and
resolution-only:0/8 admitted, exactly reproducing archived predecessor.
250us/.5ms/defaultimpedance:4/8;250us/.5ms/.999:3/8.
100us/.2ms/.999 and50us/.1ms/.999 each8/8 admitted. Raw artifact:
docs/evidence/FB-01aj-active-load-map.json;135332KiB peak. Admissible does NOT
mean biologically calibrated, converged, full-load qualified or deployable.
100us intervals took1.3908–1.6262s;50us2.7066–3.0467s for250ms physical time.
Changing response with timestep is not same-law convergence.
Unresolved energy exchange remains explicit; NEVER relabel/deposit it as heat.

One100us torso-load cProfile34761 exit0:273746calls,1.514s total;
_check2502calls1.004s, mj_step2500calls.184s,collision.049s.
_check's warning/contact wrappers consumed.239/.174s, scalar joint loop
dominates its own.538s. This is repeated Python representation of exact native
arrays, not physical work. Native stepping, collision refresh, energy integration,
surface travel and every per-step refusal remain necessary and untouched.
Full profile preserved at docs/evidence/FB-01aj-guard-profile.txt.

Frozen correction contract: only NativeBody.__init__ and _check in
substrate/functional_body_native.py. Compile limited-joint qpos addresses and
exact lower/upper tolerance bounds from immutable model once; read warning.number
and contact.dist native arrays directly. The same checks, order, comparisons and
per-substep frequency remain. No reduced sampling/caching of evolving state.
No new runtime path/schema/controller, no changed force/solver/error coefficient.
Additional immutable storage O(limited joints), temporary comparisons bounded by
current arrays; eliminates Python joint/warning/contact object iteration.
Restore/initial/eachstep/final still call _check; failed preparation never commits
world/organism bytes. Model hash, state bytes, cold successor unchanged.

Proof: tests/test_functional_body_guard_equivalence.py keeps accepted scalar
checker ONLY as a test oracle. Compare every guard class, IEEE boundary and
precedence; real recurrent hand/panel contacts + fresh cold next interval;
all128 refused active endpoints at identical physical times and scratch bytes;
eight already recorded admissible diagnostic loads with exact complete successors,
observations, work/residual, cold observations and measured cost. Existing native
bench remains required. This is body-only numerical execution, NOT full joint
DSF/neuron/cognition or mature-body/live acceptance. Full ordinary-loop, coupled
energy, home/caregiver, copied-body, resource/rehearsal/live gates remain open.
Source-only independent freeze/review precedes execution; no pytest/conftest.

09:09:06Z post-map/profile AWS: same1553/ec20ff/digest1d088e,1/1/0 HEALTHY;
live2369285,persist2369257,errorsnull,CPU51.19%,RAM2.979%;oldclockALARM,
otherfourOK. Caretaker35747 untouched; no diagnostic/compiler orphan.
Read preflight miss: package has no _structs.pyi; stopped guessed path, enumerated
package and introspected actual pinned native class fields WITHOUT constructing a
body. _MjContactList.dist/_MjWarningStatList.number present; no future pyi guess.

FB-01aj exact guard execution proof — 2026-09-26 09:24Z.
One localized source-review batch preserved unordered-bound refusal through the
exact inclusive comparison. Final independent SOURCE PASS/frozen
61dc3ee39232a2256d4c6a85cd329a8fcdbd26f91d8f333a31ce07f501b1d8f4.
No edits during review/proof; fingerprint verified unchanged after execution.

Standalone22682 exit0:5 focused tests,14.512s,139492KiB peak. All128 refused
endpoints preserved exact error/time/scratch. Eight admitted diagnostic loads
preserved complete successor bytes, sensory output, work/residual and cold
observations. Real recurrent panel contact + fresh cold next interval identical.
NaN bounds, hinge/slide boundaries, warnings, finite state/time/coordinate and
penetration guards preserve exact refusal semantics and order.
Same eight loads: array2.937230348s vs scalar9.696179851s (3.30x). Mean body-only
interval367.15ms remains above250ms; NOT a realtime or whole-organism claim.
Standalone99971 exit0:53 existing native/anatomy/world tests passed in2.068s.
No predecessor test weakened/deleted. Raw proof/health:
docs/evidence/FB-01aj-guard-equivalence.json.

Pre/post09:21:48->09:23:25 same1553/ec20ff/digest1d088e,1/1/0HEALTHY,
live2370985->2371206,persist2370953->2371177,errorsnull,CPU51.30->50.90%,
RAM2.991%;oldclockALARM remains,otherfourOK. Caretaker35747 untouched.
All exact test/health handles terminal; post-census shows no proof child.

Disposition: accept only exact guard-execution correction. This is not another
helper-optimization cycle: return now to active-load numerical qualification.
The128-endpoint failure remains open. Next use the faster unchanged checks to
qualify the surviving numerical region at fixed response across timestep
refinement and all motors, without promoting eight diagnostic successes as a
body law. Preserve actual force/work, collision, cold and energy-residual
evidence. Do not change the learning/action vocabulary to conceal failures.
Full body goal ACTIVE; remote push blocked, no production modification.

### FB-01aj full active-load coverage and fixed-response refinement contract

Predecessor034cee249 exact guard correction is CLOSED with58local checks and
unchanged successors. This stage continues active-load qualification; it does
not reopen the guard, optics, learning or field laws. Production stays1553.

Only tools/guala_body_active_load_regime.py changes: named configuration selection
avoids rerunning rejected cases; final qpos/qvel and their model address roster
provide dimensional terminal convergence evidence. Add50us and25us fixed .2ms
response/.999 impedance cases alongside the existing100us control. Keep response,
force, mass, geometry, bearing material, solver convergence settings, error
bounds and250ms duration constant for this refinement (2h clamp not crossed).
All recorded representative control trajectories must reproduce exactly.

Stage1: all128 capacity endpoints at100us/.2ms/.999 from the same pristine body,
not an ordinary learner and not claimed sustained gait. Stage2: eight original
representatives at50us and25us, same response; quantify terminal hinge, root
position/rotation, velocity, work and residual differences with declared units.
Passing geometric safety is not yet conservation/physical convergence. Terminal
comparison does not establish a uniform whole-trajectory error bound. No numeric
coefficient is promoted into production anatomy/physics by this diagnostic.

One source-only frozen review before execution. Same bounded one-process env,
pre/post AWS health and terminal child census; no concurrent G1 benchmark.
This extends the existing regime map only, not runtime code or a second model.
All-motor results and refinement decide the next first failure; full gravity,
simultaneous/recurrent load, energetic/cold integration and live gates remain.

FB-01aj full-load/refinement evidence — 2026-09-26 09:35Z.
Final source-only gate PASS at unchanged
c6a85e07ef178aee724f1722e8e4f0d0a2bfd25d5d7ec54a5e381a9f77a3521c.
One localized correction compares ALL archived control keys except wall_seconds;
streamed JSON rows preserve raw evidence without terminal truncation. No runtime
physics change. Script SHA e0f1c06c705b9124485f219b4f6c3603e32010b87a9626f04e493964ef316b31.

Stage1 session42061 exit0:128/128 capacity endpoints geometrically admitted at
100us/.2ms/.999,42.4983s total trial time,135456KiB peak; perinterval
.298355–.553054s. Original baseline128/128 refused. Terminal maxima: joint
overrun5.85580618e-5rad,penetration4.08036580e-8m. These are TERMINAL maxima,
not whole-trajectory peaks; every substep still enforced original safety limits.
Do not conflate successful admission with convergence, calibration or learning.

Stage2 session88697 exit0:8/8 at50us and8/8 at25us, response held .2ms/.999,
135340KiB peak. Original controls exactly reproduced; no clamp change.
Terminal100->50us then50->25us differences:
- thigh: maximum hinge coordinate .0733693 then .0286758rad;
  root position .755348 then .370499mm.
- torso: hinge .0278736 then .0215585rad; work differences .0167963 then
  .0691196J (non-monotonic; do not claim numerical convergence).
- torso work14.53661/14.51981/14.45069J with residual10.12695/10.13528/10.13145J.
  Persistent residual is NOT proved numerical error or bodily heat. It contains
  unaccounted constraint exchange as already labeled by NativeBody.
All144 measured rows, joint/address roster, dimensional terminal comparisons
and pre/between/post-health in docs/evidence/FB-01aj-fixed-response-loads.json.

09:30:29->09:32:02->09:33:17 read-only same1553/ec20ff/digest1d088e,1/1/0
HEALTHY,live2372168->2372379->2372549,persist2372137->2372361->2372521,
errorsnull,CPU~51.1–51.3%,RAM~2.985–2.991%;oldclockALARM remains,other4OK.
Caretaker35747 untouched. Both diagnostic processes terminal, post-census
no proof child. Source fingerprint unchanged; no production mutation.

Disposition: load-domain feasibility now measured, NOT an accepted solver law.
Next exact causal item is constraint-work/elastic-storage accounting and numerical
error qualification on these same loads, before selecting response/resolution or
reinserting the rejected ordinary integration. Source-only force review requested
to identify missing work terms; it may not invent heat partitions or controllers.
No broader anatomy, optics, cognition or curriculum work. Full goal ACTIVE.

### FB-01aj next causal correction: signed constraint work (source-only finding)

Independent body-force review and pinned MuJoCo3.3.7 source agree:
NativeBody.advance presently integrates motor and viscous-bearing work only.
mj_energyPos counts gravity and declared springs, not soft-limit/contact storage.
Unresolved exchange therefore cannot be described solely as numerical error.

Measure Pc = v_pre dot qfrc_constraint = efc_vel dot efc_force per solved state,
grouped by constraint type and physical ID. Keep both positive and negative
signed work. In the current implicitfast path mj_step leaves force/efc fields
at the pre-integration solve while qvel has advanced. Capture immediately after
mj_step BEFORE NativeBody's kinematics/collision refresh, retaining pre-step
velocity; sampling after refresh pairs new contacts with old forces and is wrong.
Successive solve samples plus the already existing final mj_forward permit
endpoint quadrature without extra solves or altered warmstart history.
No diagnostic native callbacks/controller, no simulator timestep reordering.

Report signed motor work, braking, bearings, delta(K+U), Wconstraint and
epsilon = existing_residual + Wconstraint. Compare synchronized trajectories,
contact/limit event timing and work under the fixed response law. Per-step
absolute accounting imbalance can expose cancellation but is NOT a bound on
the continuous trajectory error. Constraint solver convergence must be separated
from time-integration/quadrature error. No heat partition or stored elastic
energy may be invented: solref stiffness is acceleration-level, so 1/2*k*r^2
and -Wconstraint are not justified constitutive heat/storage laws.

Pinned primary sources inspected:
https://github.com/google-deepmind/mujoco/blob/3.3.7/src/engine/engine_sensor.c#L1277
https://github.com/google-deepmind/mujoco/blob/3.3.7/src/engine/engine_forward.c#L1078
https://github.com/google-deepmind/mujoco/blob/3.3.7/src/engine/engine_core_constraint.c#L2056

Next work is this single non-perturbing diagnostic/physical-accounting boundary.
It must reproduce accepted native successor bytes and retain raw measured terms.
No runtime physics edit authorized by a mere diagnostic finding; existing
body-only numerical approval covers derivation/verification, not fabricated
heat, relaxed checks or a claim of 250ms. Live production remains untouched.

### FB-01aj signed constraint work: frozen diagnostic contract — 2026-09-26

Previous goal turn PROGRESS:034cee249 exact execution andf2a586d3e full-load map;
accepted sourceHEAD4aef50dae; one active FB-01aj physical acceptance. Continuing
the unresolved energy boundary, not changing optics/anatomy/cognition/production.

Authorized files: tools/guala_body_active_load_regime.py and new diagnostic-only
tools/guala_body_constraint_work.py. The ordinary native/world modules stay
unchanged. The wrapper calls original mj_step exactly once, retaining pre-step
qpos/qvel and sampling its solve before NativeBody's geometry refresh; no native
callback or extra forward/dynamics solve. Restore the original Python binding
in finally. Compare the complete MechanicalSuccessor with an uninstrumented
run from identical bytes; any mismatch aborts. One isolated process only.

Power equality witness: pre_v dot qfrc_constraint and sum(efc_vel*efc_force),
report raw disagreement without an invented tolerance. Group by actual constraint
type and physical joint/geometry IDs before contact-index refresh; preserve signed,
positive and negative exchange. Pyramidal rows are NOT declared pure friction.
Use successive solved samples and the existing final forward endpoint for
trapezoidal work; exactly reproduce ordinary motor/bearing reduction order.
Also measure other passive work and reject unexplained applied external forces.
epsilon = old residual + constraint work + other passive work. No heat deposition,
no solref-as-spring-energy guess, no continuous-error certification from algebra.

Keep every substep in work and absolute/signed discrete-imbalance accounting.
Retain10ms trajectory snapshots and exact sampled active-constraint event changes;
this is bounded diagnostic evidence, NOT sensory filtering or a new clock.
For each250ms trial at smallest25us:10001samples,26state snapshots,at most10001
event changes; no cumulative runtime/organism history. Group/work storage is
bounded by this immutable anatomy's joint and geometry-pair roster. Native solver
iteration count is reported separately, not mistaken for a KKT error bound.

Named execution: eight representatives ×100/50/25us at fixed .2ms/.999 response,
each compared to one unchanged run. Must preserve prior recorded controls,
full successors and exact motor/bearing work; inspect same-time trajectory,
constraint events, Wc and remaining closure before choosing any accepted law.
Per-step absolute accounting imbalance detects cancellation, not true-solution
error. Body thermal closure, copied-body/cold/home/live and real-time gates remain
open. Source-only independent freeze/review before execution; pre/post AWS/census.
No GitHub push authorized; no runtime changes; goalACTIVE.

Source review d7cc8d998:two localized findings, zero architectural findings.
One correction batch excludes conservative qfrc_spring from other passive work
(already in native potential energy); event output explicitly names active
constraint groups, not individual contact rows/manifolds. No dynamics changes.
Pinned mjdata.h confirms qfrc_spring. Final source-only review precedes execution.
Read-only path correction: functional_body_world.py does not exist; actual body
work projection is embodiment_world.py. Resolve file roster before reading.

### FB-01aj constraint-work measurement completed — 2026-09-26 10:02Z

Final frozen source331aa091e PASS after one localized batch. Diagnostic34846
exit0:24/24 paired full successors exact, original motor/bearing work exact,
unchanged controls reproduced. All100/50/25us cases numerically admitted;
143060KiB peak. Runtime source210996faa unchanged. No accepted-law edits.

Evidence in docs/evidence/FB-01aj-constraint-work.json:16 complete original
records +8 lossless zlib/base64 replay records, rawSHA256 verified. The first
stdout capture exceeded the tool's per-chunk token budget and truncated8records,
despite60000 requested tokens. Only those8cases were replayed unchanged with
compressed single-case output; all8exact. Command/output transport failure,
not physical failure. Future large trajectory evidence must use compressed,
single-case bounded capture, not several uncompressed JSON rows per poll.
Every proof process is terminal; no A1 child/orphan remains.

Measured Wconstraint = integral(v dot qfrc_constraint) agrees with summed
constraint-row power to max2.910383e-11W. Other passive work zero and no solver
sample hit its iteration cap (max9 iterations; this is NOT a KKT guarantee).
Constraint work is signed exchange, NOT assigned heat or spring storage.

Torso negative-capacity case, fixed response .2ms/impedance .999:
step_us | old residual J | signed constraint work J | remaining discrete closure J
100 | 10.126950621 | -23.886744948 | -13.759794327
50  | 10.135277169 | -14.631475365 | -4.496198196
25  | 10.131453962 | -11.887487903 | -1.756033942

Thigh remaining closure: -3.904605/-1.315257/-.566193J.
Upper arm: -.258019/-.084292/-.036095J.
Every case's absolute remaining closure falls with refinement, but this is
not a certified bound or permission to promote coefficients. Sum of absolute
per-step imbalance still3.534176J for torso25us: cancellation is disclosed.

The26 synchronized10ms snapshots are retained. Largest hinge differences shrink,
but root trajectory differences are not uniformly monotone: torso position
100->50us .186870mm,50->25us .187734mm; thigh root orientation .0046483 then
.0052422rad. These samples cannot certify unsampled peaks or global convergence.
Active-group events are retained; internal contact-manifold row churn absent.

Conclusion: measuring omitted constraint work does NOT close energy accuracy.
Do not apply the residual to a thermal source. Next source-derived check is the
actual implicitfast velocity/force update: distinguish continuous trapezoidal
force quadrature from the impulse work of the solver's actual discrete update.
No smaller timestep or altered constitutive law is selected merely to pass.

Read-only post09:59:44Z task1553/ec20ff/digest1d088e remains sole1/1/0HEALTHY,
live2376400,persist2376393,sameidentity,errorsnull,durabilityfalse;CPU51.20%,
RAM2.9785%. Prior clockALARM remains,other4alarmsOK. Caretaker35747 untouched;
unrelated heartbeat22563 owned by9628 was observed, not killed.
Production/cold/mature-body/interface/home gates remainOPEN. GitHub push still
permission-blocked; no bypass. GoalACTIVE. No completion or live-body claim.

### FB-01aj discrete-update accounting — bounded continuation contract

Predecessor22e70b53f closes signed-force measurement only. The measured force
trapezoid is not the integrator's applied impulse work. Source authority:
MuJoCo3.3.7 engine_forward.c:923-977 and engine_derivative.c:1287-1385.

One authorized diagnostic file: tools/guala_body_constraint_work.py. Runtime,
actuation, damping, numerical coefficients, caller schema and heat stay frozen.
For each real implicitfast step, measure
(M-hD)delta_v=h(qfrc_smooth+qfrc_constraint).
Verify this compiled bench D=-diag(B) and passive=-B*v exactly each step;
otherwise abort this scoped diagnostic, never silently assume a different law.

Measure actuator, constraint, passive and negative-bias impulse work with
h*(vpre+vpost)/2 dot each PRE-step force. Record h*vbar dot D*delta_v.
Read-only mj_mulM on existing pre-step inertia obtains Mpre*delta_v and
vpost^T*Mpre*vpost; no dense matrix, solve, callback or native state mutation.
Next existing forward sample supplies Kpost/Upost. Keep only one pendingstep.
Metric work=Kpost-.5*vpost^T*Mpre*vpost; do not invent gyroscopic dissipation.

Independent checks: per-DOF impulse residual maxima; sum absolute |vbar_i*r_i|;
sum/max absolute complete discrete energy closure. Compare existing bearing
quadrature to actual passive+implicit exchange, never substitute signed
accounting for nonnegative physical bearing heat. Retain former trapezoidal
constraint work and expose its difference from applied impulse work.

All successors and former motor/bearing sums must remain exactly unchanged.
No loss assigned to heat, no continuous-error bound claimed from algebra.
Contract scope is numerical-measurement correctness, not a new accepted bodylaw.
One frozen source-only review precedes paired8x3 execution. Evidence output
single-case compressed to avoid the proven terminal truncation. Pre/post
read-only AWS/census; zero runtime or G1 mutation. GoalACTIVE.

### FB-01aj discrete accounting closed; motion/thermal qualification open — 2026-09-26 10:13Z

Candidate56b82c901 source-only PASS, no findings. Session92793 exit0:
24/24 full native successors, every prior raw non-walltime record (including
trajectory, group events, old work) and existing motor/bearing witnesses exact.
Every substep verified actual compiled derivativeD=-B and passive=-B*v; no
assumption substituted for that check. Every compressed new record authenticated.

Discrete equation residual: maximum summed absolute energy closure2.2141342e-11J;
maximum single-step closure1.5781994e-13J; maximum summed absolute impulse-energy
residual bound2.2133979e-11J. The independent residual checks establish the
accounting identity to measured rounding, not continuous-solution accuracy.
Explanation_disagreement includes measured closure and is not an independent
physical accuracy test. Peak152172KiB; all handles terminal.

Torso negative-capacity results:
step_us | applied constraint impulse work J | motor+constraint-Qbearing-deltaE J
100 | -10.144237191 | -.017286570110
50  | -10.137249365 | -.001972195704
25  | -10.131405989 | +.000047972572

The old force trapezoid adds -13.742508/-4.494226/-1.756082J compared with the
actual applied constraint impulse: new braking force was being assigned to a
preceding interval where it was not applied. The remaining measured balance is
explicitly decomposed into bearing quadrature, negative bias, changing inertia,
potential change and tiny equation residual. No force/pose/energy stock changed.
Across all eight loads the largest |physical balance| is .01728657/.00197220/
.000383904J at100/50/25us. Do NOT declare that a chosen tolerance was passed.

Also disclosed: outward distal-stop cases have positive net numerical constraint
exchange16.53/4.45/.854microjoules. This is not proved released stored energy;
soft-constraint passivity/heat allocation remains unqualified. No residual,
positive constraint work, metric term or algorithmic correction enters heat.

Data: docs/evidence/FB-01aj-discrete-work.json stores all24 new compressed raw
records, script, source fingerprint, session and pre/post health. Prior full
trajectories are referenced once by exact-field comparison and artifact SHA256
d3da6a5047551f9cd9a1c591da94ffe80d070473482e3171af6e515101a9b3e7.
No need to repeat the bookkeeping investigation or blame the former13J gap on
unknown physical heat. Source helperd3e8f712... is offline only; runtime remains
210996faa... . Whole-body active numerical law is NOT promoted by this proof.

Next exact physical item: derive limit/contact numerical resolution from the
existing declared geometry and force/inertia envelope, and qualify same-law
trajectory error and passivity before selecting any timestep/constraint law.
Do not tune a coefficient merely until the ordinary-loop test passes. Existing
100/50/25us trajectories and full128load results remain the control evidence;
do not reopen their measured outcome or run the archived integration candidate.

Post10:10:34Z same1553/ec20ff/digest1d088e,counts1/1/0HEALTHY,sameidentity,
live2378051,persist2378025,errorsnull,durabilityfalse,CPU51.22%,RAM2.991%.
Prior clockALARM remains;other4alarmsOK. Caretaker35747 untouched; no diagnostic
orphan. Full functional-body goalACTIVE; no deployment, push or completion.

### FB-01aj load/release recurrence — bounded contract — 2026-09-26 10:29Z

Previous response-only goal turn made no implementation progress. Resume this
same mechanics gate from6246b3f65; discrete accounting is CLOSED, not reopened.
Read FB-01e authority again: Joe already approved native soft contact and body-only
numerical approximation, with unavailable general contact thermal mapping stated
explicitly. Do not expand this into microscopic contact biology or new permission.

Source-derived scalar reference (NOT a coupled-body bound): declared effort
T=sigma*pi*r^3/2 and bearing B=(121/21)*pi*mu*r^3 give isolated terminal rate
T/B=21*sigma/(242*mu)=173.55rad/s. For one scalar, constant-impedance, critically
damped stop, xddot+2*xdot/tau+x/tau^2=(1-d)*a_free. Entry response obeys
x_max <= (1-d)*a_free*tau^2+v_entry*tau/e while that scalar law is active.
At the isolated reference rate, .2ms gives .0128rad entry penetration;20ms
gives1.28rad. This explains the default-response failure, NOT a body-wide
speed, compliance, error or passivity certificate. Coupled inertia/contact
switching invalidate interpreting it as one. No physical constants promoted.

Single next artifact tools/guala_body_load_release.py: offline nine-case
recurrence using existing fixed .2ms/.999 diagnostic law,100/50/25us; torso-,
upper-arm-, distal-finger- full capacity. Per case load250ms, zero250ms,
reverse250ms, zero250ms; test-only mechanical challenge, not supplied cognition.
Same scene/anatomy/bearings/capacities/safety bounds; same approved approximation.

Each interval uses the already-reviewed observer, exact ordinary-successor
comparison, then fresh engine cold replay from that interval's predecessor.
Carry actual state and subtract positive work from a single finite bench budget;
never reset between phases, refill, lower effort, loosen safety or retry refusal.
First load must reproduce archived complete discrete report exactly. Failure
stops only its case and is retained. Current-only native state size must not grow.
Keep all per-interval work,10ms trajectories, group events, terminal nonzero
constraint counts/penetrations/energy, state fingerprints and costs. Compress
each complete case independently with raw SHA256 to prevent terminal truncation.

Interpretation: signed constraint exchange is not invented heat or spring
storage. Only a actually unloaded/released cycle can support a passivity
inference; contact/limit states and remaining energy stay exposed. No zero-error
or universal passivity claim, no runtime admission changes. Quantify fixed-law
cross-resolution differences and recurrent/cold validity. A refusal is a new
mechanical-domain boundary, not permission to change law until green.

Lean impact: one offline tool only; no new runtime state/import/callback/owner,
no duplicated live solver or body/cognitive authority. Existing helper reused;
no broad test suite or native rebuild. One source-only frozen review before
execution; pre/post read-only AWS plus host census. G1 source and caretaker,
canonical kernel and pending GitHub push restriction remain untouched.

### FB-01aj recurrence measured — 2026-09-26 10:44Z

Frozen91df0d7b7 independent source PASS; fingerprint verified unchanged after
execution. Probe e2a296bd856..., observer d3e8f712305..., runtime210996faa...
unchanged. Session86727exit0: all9 cases complete all4 phases;36 exact fresh-engine
cold successor comparisons and9 exact previous first-load discrete reports.
Native state5152bytes in every interval; one decreasing finite work budget.
No force reset between phases, no safety relaxation, and no live dynamics change.

All9complete raw records retained as compressed JSON with verified byte lengths/
SHA256 in docs/evidence/FB-01aj-load-release.json. Derived comparisons and their
read-only reproduction scripts are in FB-01aj-load-release-analysis.json.
Raw storage3,738,231B compresses to1,940,196base64characters; retained offline
evidence only, zero new runtime memory/history. All36time-aligned10ms trajectories
and per-step work/event records preserved. Output passed10000character acknowledged
chunks after each completed simulation to avoid the previous truncation hazard.

Established: recurrence safety/cold/non-growth in the tested domain. PeakRSS
141784KiB; summedabsolute equationenergyclosure percycle<=8.892354e-11J.
Signed total constraint exchange across fourphases remains negative in all9:
torso -28.494111/-28.486001/-28.405360J; upperarm -3.038811/-3.010600/-3.010314J;
finger -.001220437/-.001243705/-.001253786J at100/50/25us.
These are signed exchange, NOT inferred heat or certified passivity.

New quantitative boundary: positive outward finger stop/release exchange is
still present. Many torso/arm final states retain active constraints and kinetic
energy, so do not call those unloaded closed cycles. The full negative net
exchange does not excuse the positive local numerical work.

Fixed-law recurrent trajectory differences are materially larger than the
earlier single loaded interval:
max sampled hinge difference100->50us /50->25us:
torso .21278386/.11308071rad (right upperarm pitch, final release);
upperarm .18278827/.06781530rad (proximal fingers, reversal);
finger .000548706/.000275528rad (proximal finger, final release).
Torso rootposition3.30423/2.00595mm and rootorientation.0440226/.0158964rad.
Torso thumb-tip angular-rate difference50->25us reaches101.21069rad/s during
reverse160ms (12.3382vs113.5489rad/s); finer sampling does NOT uniformly reduce
velocity differences. These are pairwise discrete trajectories, not exact
solution errors or new acceptance tolerances. Do not promote this regime.

Ordinary cold advance costs .263–.529s at100us, .545–.915s at50us,
1.026–1.311s at25us per250ms interval. This candidate is NOT realtime.
No claim that numerical admission alone qualifies proprioception/motion.
The first new blocker is joint/contact event resolution under coupled reversal,
not missing cognition and not the closed force accounting seam.

Next bounded action: compare the same soft-constraint law using the native
full implicit integrator versus implicitfast, which omits the bias-force velocity
derivative. This is a numerical-causation test, NOT a proven diagnosis or
permission to change the constitutive law. Source-derived update/work contract
required before execution; retain exact fast controls. Do not lower force,
relax .03rad/.008m guards, add behaviors, or demand microscopic thermal biology.
If the integrator comparison cannot resolve accuracy/cost, record that boundary
rather than serially reducing timestep without a bounded operating target.

Read-only pre10:30:40/post10:37:49Z: task1553/ec20ff/digest1d088e sole1/1/0HEALTHY,
sameidentity; ticks2381110->2382202, persisted2381097->2382185; allcheckpoint/
cleanup errorsnull,durabilityfalse. CPU51.18->51.02%,RAM2.9785%.
Prior clockALARM remains,other4alarmsOK. Caretaker35747/supervisor831 untouched;
no A1 diagnostic child/orphan remains. No production-shaped interpretation.

Command recurrence notes: apply_patch rejects Delete+Add for the same path in
one patch; failed only in /tmp staging, then used complete-content Update.
Orchestrator store(undefined) rejected after test start; session86727 remained
live and was reattached, NOT restarted. Store nullable exit codes explicitly.
Neither command error changed source physics or lost measured evidence.

Complete functional-body goalACTIVE. This is a local qualification result, not
deployment; GitHub push remains permission-blocked. G1 main files untouched.

### FB-01aj fixed-law integrator comparison contract — 2026-09-26 10:49Z

Previous goal turn PROGRESS:ea874c88d closes tested recurrence/cold/non-growth,
not trajectory accuracy or production. Source and shared-ledger state rechecked;
G1 has no newer entry. No pending diagnostic handle. This continues the same
numerical mechanics gate, preserving all body/cognitive/thermal authority.

Pinned engine_forward.c:933–970 and engine_derivative.c:1370–1385 define:
(M-hD)dv=hF, F=qfrc_smooth+qfrc_constraint.
implicitfast usesD=-B on this verified bearing-only model.
implicit usesD=-B-d(qfrc_bias)/dv with nonsymmetric sparse LU.
Both use the same current constraint solve; neither implicitly resolves future
contact-force derivatives. Omitting that derivative is a hypothesis, not diagnosis.
Source:https://github.com/google-deepmind/mujoco/blob/3.3.7/src/engine/engine_forward.c
Source:https://github.com/google-deepmind/mujoco/blob/3.3.7/src/engine/engine_derivative.c

Authorized files only: tools/guala_body_constraint_work.py and
tools/guala_body_load_release.py; main owns full-file replacements.
NativeBody, anatomy, contactresponse.2ms/impedance.999, forces, bearings, finite
supply, guards, interval and initialphysicalstate remain unchanged.
No kernel/cognition/lived-body/production source edits.

Observer adds full implicit actual sparseD*dv, never symmetrizes it or solves
again. Retain the exact old fast arithmetic and report. Both branches still
require passive=-Bv every step. Full branch verifies no extra declared tendon/
fluid/activation effects, reads native derivative, records max/sumabsolute bias
derivative impulse h(D+B)dv by DOF and10ms samples. Same-state algebraic witness:
(M+hB)dv-hF-h(D+B)dv=0; report residual, not an independent counterfactual solve.
Use h*vbar^T*Ddv in existing discrete work identity. Metric/bias/constraint terms
remain signed accounting, never heat or invented stored energy.

Runner selects only implicitfast orimplicit at model creation; headers must stay
distinct. Compare initial integration payloads explicitly to the fast model
without transplanting bytes or changing either body. Within each integrator,
ordinary/observed and fresh-engine cold successors must remain exactly equal.
No full-implicit report is stamped with the old bearing-only derivative claim.
First-load prior match is asserted only for the fast controls, not falsely for
a physically identical body under a different integration algorithm.

Execute three archived100us fast recurrence controls first and require every
prior non-walltime field exact, then nine implicit cases (3loads x3timesteps,
4retained phases). Retain raw evidence bounded/lossless as in prior probe.
Stop a physical case on refusal; no retuning or retry. Parameter ranges frozen.
Compare fixed-law trajectory, work, event-group histories and cost. An energy-
damped quieter path is not proof of greater accuracy;10ms evidence cannot prove
substep first-cause chronology or internal contact-row churn.

Source-only freeze/review precedes execution; read-only AWS/census pre/post.
Runtimezero new work/state. No production claim or GitHub push authorized.

Source review ccde2faaa: mathematicsPASS, one localized execution-contract
clarification. Archived max_rss_kib is a process high-water cost, not physics.
Fast raw comparison excludes only max_rss_kib and per-phase elapsed-time fields;
every deterministic physical/state/work value stays exactly compared. New costs
are retained separately. No source change was needed; this is the single batch.

### FB-01aj full-implicit comparison measured — 2026-09-26 11:12Z

Frozen source fingerprint 7187bad6d48d2b0054e176b0e105bd29fa92439fd870e1dcb0f25302aac70efb
passed the final independent review and verified unchanged after execution.
Diagnostic-only source hashes: constraint observer 4ea3c15513fe697f...,
load/release probe fbe353a1a66c527c...; NativeBody remains 210996faa48c0508...
No runtime numerical law, anatomy, force, guard, cognition or production change.

Three 100us implicitfast controls reproduced EVERY archived deterministic
physical/state/work field exactly (only elapsed time and process peak RSS
excluded and retained separately). Full implicit then completed 9/9 cases,
36/36 intervals: ordinary-versus-observed complete successors exact, fresh
engine cold successors exact, initial physical integration payload equal across
integrators, state 5152 bytes throughout, finite decreasing motor budget.
Peak 147748 KiB; maximum summed absolute discrete energy closure 8.901033e-11 J.
This proves the named bench invariants, NOT real-time or trajectory accuracy.

Result: reject full implicit as the proposed accuracy/cost correction.
Torso max sampled hinge difference at 100->50 / 50->25us:
0.17623896 / 0.20036646 rad; finer sampling does not uniformly converge.
The 50->25us torso joint-rate difference remains 37.04455 rad/s.
Upper-arm hinge differences 0.18116675 / 0.06226318 rad;
finger 0.00304314 / 0.00066831 rad.
These are pairwise trajectories, not certified exact-solution errors.
Full implicit costs 0.4415–0.5182 / 0.8965–1.2752 / 1.6904–2.6946 seconds
per simulated 250ms at 100/50/25us: worse than implicitfast.

Actual native bias-derivative impulse is nonzero (torso100us reverse max
0.16546 generalized impulse); same-state algebraic witness residual <=6.90e-14
in that torso case. It changes the dynamics, but including it does not remove
the measured trajectory sensitivity. Constraint-group histories differ; counts
are not an internal contact-row first-cause proof. Full implicit torso100us
reverse physical balance -0.06347994 J is worse than prior fast -0.03160073 J.
Do not infer an improvement from a quieter trajectory or tiny equation closure.
Keep signed constraint work explicit; do not invent heat or contact passivity.

Complete 9-case raw evidence is retained once, compressed and SHA256-verified,
in docs/evidence/FB-01aj-integrator-comparison.json (3,012,954 bytes at creation).
It contains control receipts, analysis, exact collection/analysis scripts,
source hashes and health envelopes. The previous fast raw evidence is referenced
rather than duplicated. All uncompressed record lengths and hashes verified.

Collector failures are operational evidence, not hidden:
session23520 exited1 after one complete full-implicit record and three controls;
ACK transfer timed out after 260000/329843 characters of the second record.
Continuation78484 exited1 with five complete records retained, while transferring
the50us finger record (10000/326681 characters captured). That case's simulation
had completed before output began. No incomplete record was counted as evidence.
Only uncaptured cases reran; no coefficient or physical refusal was retried.
Final collector83862 wrote generated diagnostics into explicit /tmp artifacts,
finished exit0, and avoided interactive ACK coupling. Recurrence guard: never
make long diagnostic evidence depend on model/tool acknowledgement latency.
Use bounded local generated artifacts; report compact hashes and summaries.
No future harness should repeat this failed transfer protocol.

Read-only snapshots10:53/10:58/11:05/11:08Z preserve same task1553/ec20ff,
digest1d088e, sole1/1/0 HEALTHY; live ticks2384560->2386852,
persisted2384553->2386825, sameidentity, checkpoint/cleanupnull, durabilityfalse.
CPU~51%, RAM~2.98%; existing clock-stalled ALARM remains, other four alarmsOK.
Host census after83862 confirms no A1 proof child/orphan. Caretaker35747 and
supervisor831 untouched. No G1 source, marker, process, or production mutation.

Next bounded action: remove the already measured Python per-substep execution
overhead with one native interval path that preserves the accepted implicitfast
algorithm, guard/refusal ordering, state bytes, work terms and sensory return.
First trace/profile that exact path and freeze the contract; no new force law,
motor controller, timestep retuning or cognitive mechanism. This can enable
affordable qualification but DOES NOT resolve the still-open accuracy gate.
Do not blindly shrink timesteps or repeat this rejected integrator comparison.
Home/gravity/concurrent-motor, ordinary organism integration and live delivery
gates remain open. Full functional-body goal ACTIVE; no production qualification.
GitHub push remains permission-blocked; retain local commits, do not retry/bypass.

### FB-01aj remove duplicate substep work — contract 2026-09-26 11:20Z

Previous goal turn PROGRESS:9d8c778fe closes the full-implicit comparison with a
negative accuracy/cost result. Current branch clean at9d8c778fe; shared main
ledger has no newer G1 entry. Continue the same bounded execution-cost gate.

Current one-interval profile (session37662 exit0): 250ms body at100us needs
0.314024s unprofiled; 266126 calls/0.425s profiled. Native mj_step0.139s,
collision0.032s, existing exact checks0.071s; advance Python self0.092s.
The accepted runtime is already native for motion/contact. Reimplementing
NumPy's reductions and transcendental functions would risk changing energy/
guard results. Before a larger native port, delete the confirmed duplicate
endpoint calculation: end-of-step power is exactly next-step start power.
There is no intervening velocity, effort or damping mutation. No callback or
concurrent writer is allowed by this adapter. This is deletion of duplicate
work, not a cross-interval cache or altered sampling.

Requested architecture: identical bounded body mechanics with less execution
overhead. Current reality: repeated Python work and duplicate power/damping
evaluation. Conflict: yes, measured interval misses250ms; no proven physical-law
defect is being patched by this change. Do not extend fullimplicit trials,
cognition, substrate fields, behaviors, constitutive laws or relaxed tolerances.
Single next item: exact same-law duplicate-work deletion and equivalence proof.
No DSF evaluation: body-only previously approved numerical approximation;
all explicit DSF fields and cognitive mechanisms remain unchanged.

Authorized runtime edit: only NativeBody.advance in
dsf_ai_service/substrate/functional_body_native.py.
Compile motor index array locally once per interval, not on each advanced-index
lookup. Evaluate pre-step motor/bearing/self-bearing power once, then retain each
just-computed endpoint only through the next substep. Keep the exact same NumPy
multiply/dot/square operations and trapezoidal addition order. Move invariant
half-timestep outside the loop. Call ndarray.sum/max/clip directly instead of
generic np wrappers on known ndarray values; same reduction axes/dtypes/order.
No state format, model header, retained model anatomy, observation, or safety
predicate changes. No native solve, collision refresh, guard or sample omitted.

Causal map: existing world._native_transition supplies authenticated integration
bytes/effort/elapsed/supply -> NativeBody._restore -> same forward -> same steps
and poststep kinematics/collision/check -> same work+travel -> same finalforward/
check/observation/capture -> world materialtime/projected state -> existing
NativeMechanicalWork -> current-only coupled world/thermal/organism publication.
Failed advance still mutates only disposable scratch, never caller-owned bytes
or a published world. Retry starts from authenticated input via _restore.
No new physical data or observer field crosses a boundary; all successor fields
must match bit-for-bit, including heat/work and therefore thermal consumers.

Complexity: O(N*(nu+nv+geometry+native solve)) remains, no new retained bytes.
Bearing dot calls shrink4N->2(N+1) for a self body,2N->N+1 otherwise.
Motor pre-power reductions shrink2N->N+1 evaluations. This removes duplicate
allocations/evaluations; it does not merely move them behind a persistent cache.
All per-step guards and numerical uncertainty/accuracy gates remain intact.

Proof file: tests/test_functional_body_interval_equivalence.py contains the
9d8c778fe advance method as a TEST-ONLY oracle, not runtime fallback. Compare:
nine existing100/50/25us x3load four-phase trajectories, fullsuccessors and cold;
128 known baseline endpoint refusals including exact failuretime/scratchstate;
zero-actuator gravity/contact and ordinary gripper sequences; sparse retained
efforts and work exhaustion; countremoveddotcalls; existing constraint observer
compatibility. No mocked organism experiences or live occurrence calls.
Run standalone unittest, never pytest/conftest. Relevant native/energy/world
regressions only after source-only frozen independent review.
Pre/post read-only AWS and host census, bounded output artifacts. No interactive
ACK collection. Profile/runtime proof is not copied-mature-body deployment proof.

Lookup recurrence guard: pathuf_native and rootDockerfile glob do not exist;
use discovered native/guala_core and dsf_ai_service/Dockerfile. Failed read-only
queries caused no changes. No guessed path will be retried.

### FB-01aj duplicate endpoint work removed — 2026-09-26 11:29Z

Independent source-only review PASS, no findings, fingerprintbe06583c1a25...
verified unchanged before/after execution. New runtime SHA256f9c86b73c7c1ac46...
and proof623c77e26fe28022.... One runtime method changed; no new dependencies,
persistent cache, field/schema, dynamics/force/guard, or production writes.

Session82736exit0:6/6 standalone equivalence proofs in76.935s, peak147604KiB.
All36 recurrent fullsuccessors and freshcold successors exactly match9d8c778fe;
all128 original endpoint refusals match error, physicaltime and scratchstate.
Gravity, friction/gripper, sparse held commands, energy depletion, one-step and
bad-input recovery match. Existing discrete work observer remains exact; full
implicit adapter compatibility also checked without promoting that scheme.
State5152bytes unchanged. Dot-call falsifier confirms4N->2(N+1) with a self
subtree and2N->N+1 without; zero retained fields added by an advance.

Session56666exit0:61/61 existing native/energy/anatomy/world regressions in2.106s,
peak149660KiB. Includes coupled heat+reserve, prepare/discard/rollback, fresh
restart and next interval, contact ownership and actual head/world transforms.
This is source/isolated integration proof, not copied live-body qualification.

Measured paired recurrence costs (seconds per250ms):
100us meancandidate.269482 vs predecessor.335544; medianpaired speedup1.1881x.
50us mean.560283 vs.629047; median1.1295x.
25us mean1.138649 vs1.265405; median1.1348x.
Scheduler outliers retained, not hidden; totals/medians and every timing emitted
in docs/evidence/FB-01aj-interval-execution.json. The100us candidate range is
.221649–.293198s. NOT a250ms real-time pass, and unchanged trajectories retain
the previously measured accuracy limitations. No native whole-interval port
has been built or claimed by this change.

Read-only proofpre11:22:56 /post11:25:14 /regressionpost11:26:18Z:
same1553/ec20ff/digest1d088e,1/1/0HEALTHY,sameidentity,
live2388949->2389456,persist2388937->2389449; checkpoint/cleanupnull,
durabilityfalse; CPU~51%,RAM2.9907%; existing clockALARM,other4OK.
Host census confirms both harnesses terminal, no A1 child/orphan.
Caretaker35747/supervisor831 and G1 source/processes untouched.

One output parser expected RECURRENCE at line start, but unittest stderr's
unfinished progress prefix preceded it. Test had completed exit0 and full
output was preserved. Parsing the token position recovered all9 rows; no rerun.
This was an output parser failure, not a test failure or missing evidence.

Disposition: accept exact duplicate-work deletion; this seam is closed.
Next named action remains the native interval execution boundary, now based on
the leaner baseline. Preserve NumPy rounding/work/guard outcomes explicitly;
do not port/repeat deleted endpoint work, reopen constitutive laws, or claim
smaller timesteps/fullimplicit already solve accuracy. Full body integration,
home/caregiver/cold mature state, numerical qualification and live delivery
remain open. GoalACTIVE; GitHub push remains blocked and has not been retried.

### FB-01aj compiled interval contract — 2026-09-26 11:39Z

Previous turn PROGRESS:e2b328240. Revalidated clean body branch and current shared
ledger; no new G1 entry. Continue execution cost, not a new numerical/material
law. The prior duplicate-endpoint deletion and failed fullimplicit comparison
remain closed. Baseline100us mean269ms/250ms; finer steps still cost more.

Requested architecture: the same authenticated body interval with less Python
bytecode dispatch. Current reality: MuJoCo solves natively, but Python executes
the interval loop/scalar accumulators. Conflict: yes, real-time and complete
mechanical qualification remain unproved. Do not extend any force/controller,
contact law, solver settings, approximate reduction, cognition or kernel files.
Single next item: compiled same-law interval plus exact differential proof.
No DSF evaluation/reduction is performed here; approved numerical body mechanics
only, with no newly omitted physical structure.

Use a small Cython3.1.2 build-only extension (no compiler runtime dependency).
Preserve MuJoCo's public Python binding calls, including their native fatal-error
conversion, rather than introducing unsafe raw model/data pointers or a second
MuJoCo library. Preserve NumPy vector operations and reduction/transcendental
order, rather than reimplementing dot/sum/acos in a different native library.
Compile the control loop and float64 scalar accumulation with fast-math and
FMA contraction disabled. No solver change, SIMD/FMA shortcut or GIL worker.
Existing _check executes after every native step/kinematics/collision as before.
Cache only interval-local references to stable native arrays/functions and
halfstep. Geometry snapshots remain perstep; contact checks fetch current data.
No model/data ownership, persistent cache, history, callbacks or new clock.

Authorized files:
native/functional_body/interval.pyx, native/functional_body/build.py,
dsf_ai_service/substrate/functional_body_native.py (constructor binding and
advance dispatch only), tests/test_functional_body_native_interval.py.
Reuse accepted test_functional_body_interval_equivalence.py unchanged as the
exact predecessor oracle; it matches e2b328240 transitively through prior proof.
No native/guala_core/kernel edit or parallel cognition module.

Boundary: existing advance validates elapsed/supply/effort, restores input,
applies effort and runs initialforward/timecheck; one compiled call executes
the existing bounded substeps and returns positive/signed/braking/bearing/self-
bearing work and maximum surface travel. Existing expectedtime/finalforward/
_check/_observation/_capture/residual remain in Python adapter unchanged.
Compiled scalars are IEEE double; retain each multiplication/addition order.
A NaN travel maximum must preserve Python max semantics before the existing
non-finite-motion refusal. No native float fusion or reordered reductions.
Missing/wrong-ABI extension refuses at NativeBody construction, no Python
fallback. Unmounted world code retains its lazy NativeBody import boundary.

No schema/header migration: input and complete output must remain byte exact.
Exceptions propagate through the same caller; only scratch may have advanced.
World/thermal/organism publication, rollback and freshcold continuation unchanged.
Storage O(model-sized endpoint arrays), independent of lifetime/stepcount;
calls remain bounded by substeps. This compiles dispatch rather than claiming
all MuJoCo/NumPy calls disappear. No nanosecond or guaranteed speedup claim.

Build output goes only to an explicit /tmp build directory. Pin compiler3.1.2,
retain build command/compiler log/source+binary hashes. No generated C, object
files or binary artifacts committed into source. Preserve isolated NumPy/MuJoCo
3.3.7 runtime and existing optics extension; do not replace G1 packages.
Build may depend on setuptools and Cython, not new runtime libraries.

One frozen source-only review precedes compile. Then prove loaded extension
origin/ABI, missing/bad backend refusal, existing6 exact interval proofs
(36 recurrent/cold successors,128 refusals, work/observer/cost), and61 existing
native/energy/anatomy/world regressions. No pytest or production occurrence.
Copied-mature-body/production gates remain separate and open.
Read-only AWS/host census before and after build/proof; no orphan child.

Compiler reference (not a physical law):
https://cython.readthedocs.io/en/3.1.x/src/userguide/source_files_and_compilation.html
Pinned release:https://pypi.org/project/Cython/3.1.2/

### FB-01aj compiled interval verified — preserved 2026-09-26 12:42Z

Previous body work PROGRESS; Joe's intervening starvation audit produced separate
live evidence, not a body-source change. Resume the original bounded body goal.
Fingerprint58c85945c56bac32de1464361bb7f269ab46ff4e02c1d0df49a6e52138075675
reverified unchanged. The reviewed runtime/test candidate has not moved while
that audit ran. Independent body_force_review source review passed beforehand.

Build session69804exit0: pinned Cython3.1.2,2.3296s,151024KiB; output only under
/tmp/guala-body-interval.Hdyavt,18MiB at completion. Loaded extension SHA256
d1600acfdb04a9f8d04580fd7d9a288018e28b7d09ce6150146e95fb6bec3be0,
reverified now. No generated C/object/binary added to the repository.

Session74798exit0:9/9 loader/ABI/exact-Fraction/unchanged interval proofs in
79.172s,150944KiB. All36 recurrent and36 freshcold complete successors remain
byte-exact;128 original endpoint refusals match error/time/scratchstate.
Session27437exit0:61/61 unchanged native/energy/anatomy/world regressions in
1.950s (wrapper2.71966s),148988KiB. No production-shaped claim from these cases.

Direct immediate-e2b328240 comparison, session24532exit0:24 exact predecessor/
compiled successor pairs, alternating order,3 loads x4 recurrent phases x2.
100us step: compiled mean292.854527ms vsPython308.856910ms per250ms interval;
median paired speedup1.07350585x.14.5398s total,143420KiB. Scheduler outliers
retained. This is NOT a250ms throughput pass. The older9d8c778fe oracle ratios
also include the previously accepted duplicate-work deletion; they must NOT
be reported as the incremental Cython gain.

Evidence preserved in docs/evidence/FB-01aj-compiled-interval.json: exact command,
raw retained tool output, all paired rows, source/binary/frozen identifiers,
verification results and health identity. Before/after12:07/12:14/12:19Z health
remained1553/ec20ff/digest1d088e,1/1/0HEALTHY and unchanged organism identity,
advancing live/persisted ticks, checkpoint/cleanupnull,durabilityfalse. Zero
reserve remained an organism defect; AWS health never implied feeding success.
All referenced proof/build handles terminal. No A1 test child/orphan at census.

Accept this execution-only replacement; do not reopen its physics/byte-equivalence
gate. Numerical motion accuracy, soft-contact passivity/thermal interpretation,
home/gravity/concurrent loads, mature integration and live delivery remain OPEN.
Next bounded question: which joint/contact event first produces the recurrent
cross-timestep discrepancy? Use existing archived events first; only missing
same-solve row evidence justifies another focused offline measurement. No blind
timestep shrink, law retuning, force reduction, tolerance relaxation or cognitive
work. Existing diagnostic tools/guala_body_constraint_work.py is authoritative;
guessed tools/guala_body_discrete_work.py does not exist and will not be retried.

Authority helper still expects the absent July31 handoff; this known skill/repo
drift is unchanged, not a new worktree or permission blocker. Actual body branch,
HEAD,diff,source and sprint ledger were inspected directly. Push restriction
remains; no denied GitHub operation was retried.

### FB-01aj resumed after explicit goal restart — 2026-09-26 16:55Z

Joe resumed the bounded body goal and explicitly retains A1 help for G1.
The previous turn was coordination only, not body progress. AUT-01 retention
is separately committed/proven locally in a1/needs-fulfillment; G1 movement
correction and combined independent acquisition acceptance remain open.
Do not merge the moving main tree or abandon that bounded integration duty.

Recovered existing compiled-interval proof without rerunning it. Its binary
still hashes d1600acfdb04a9f8d04580fd7d9a288018e28b7d09ce6150146e95fb6bec3be0.
Prior reviewer recovered the PASS/fingerprint58c85945... and verified current
file hashes; the old receipt has whole-tree rather than per-file hashes, so
no stronger historical per-file comparison is claimed. No implementation or
test source changed during recovery. Preserve/commit accepted work and evidence.

New evidence uses only authenticated archived load/release records, no simulator
execution: docs/evidence/FB-01aj-first-contact-localization.json. Across100/50/
25us, first contact group[6,22,6] starts at21.5ms; solver max6iterations and
zero capped samples. At20ms,100->50/50->25us maximum hinge difference is
.00060984/.00030508rad. By30ms, joint-speed differences are46.0253/18.9341rad/s.
Joint-limit group churn precedes contact. This narrows the next diagnostic to
the first30ms of one torso load, NOT a new full recurrence/refinement sweep.
Archived group IDs lack same-solve contact rows/impulses, so they cannot yet
establish which physical contact or constitutive term causes the divergence.

No force reduction, tolerance relaxation, solver-law promotion or heat assignment.
Next contract: observe the existing same-solve contact rows only over this small
prefix, verify unchanged ordinary successor and archived10/20/30ms samples, and
identify contact geometry/normal/friction and joint-limit contributions. This
is a numerical-mechanics diagnostic, not a cognition or production experiment.

Recovery tooling errors preserved: guessed setup.py/guala_body_interval.pyx
were absent; actual discovered native/functional_body/build.py and interval.pyx
read instead. No build retried. An overlarge archived-event print was truncated;
all original data remained in authenticated files, then a bounded summary was
computed without rerunning physics. Default sandbox ps sees its own namespace,
not the host; do not treat it as a production/shared-host census. No simulation
or heavy process launched in this recovery block. Push restriction unchanged.

### FB-01aj first-contact localization measured — 2026-09-26 17:05Z

Native interval/evidence custody committed00b0a4e97 locally; no push. New source-
only observer tools/guala_body_contact_onset.py frozen db0859e8fad8f252cf315c590
68824de7cba8d0e873b91dbe73fd2c252c865d9, independent review PASS/no findings.
Whole-tree fingerprint unchanged before/after diagnostic. Script observes the
existing mj_step return before geometry refresh, never invokes another solve
or changes controls/state. No runtime source changed in this diagnostic.

Session58668exit0: three30ms torso prefixes at100/50/25us, 300/600/1200steps.
Each observed complete successor equals ordinary execution exactly; each prior
archive0/10/20/30ms position/velocity sample matches bit-for-bit. Native impulse
power row/DOF identity disagreement <=2.9104e-11W. PeakRSS144996KiB. Observed
loops .0446/.0854/.1696s; not a production throughput benchmark. Full raw evidence
authenticated in docs/evidence/FB-01aj-contact-onset.json, rawSHA41bf10d038bfb63c
bb736a371aaa4f370f7acce84e56161162c519e889c04725. No truncated evidence or rerun.

Physical localization: right forearm contacts torso at21.5ms at all resolutions;
peak native constraint-row force4625.94/4362.85/4231.22N. Left palm contacts left
thigh at21.8ms; peak1362.35/1295.80/1262.19N. Native row forces are not summed as
a resultant contact wrench. Fastest sampled joint is left digit4 distal flexion,
267.93/211.69/201.79rad/s around21.9–22.0ms; its own generalized constraint force
is zero at those samples. Coupled body motion matters: absence of a direct
constraint on that DOF is not absence of mechanical impulse through the body.
The right forearm/torso nonzero contact lasts one100us sampled step in coarse
execution but250–275us across finer resolutions. Group power integrals are
left-endpoint diagnostics only, not heat or integrator-consistent impulse work.

This narrows the accuracy investigation to resolved self-impact impulses and
their transmission to low-inertia digits. It does NOT certify a new law or prove
contact is the sole root cause. Next: derive a same-contact accuracy/step bound
using this impact window, preserving actual force capacities and joint geometry;
do not blindly shrink every step, add damping to force a pass, relax guards,
reclassify surfaces, or introduce body-motor decisions. General thermal mapping,
gravity/load integration and copied mature-body/live delivery remain OPEN.

Read-only AWS before17:00:48/after17:02:41Z: same1553/ec20ff/digest1d088e,
service1/1/0HEALTHY,sameidentity,live2432975->2433220,persist2432969->2433193,
checkpoint/cleanupnull,durabilityclear; CPU~51%,RAM~3.21%. Existing clockALARM
persists, otherfourOK. G1's prior15-step diagnosticPID34306 was terminal before
this run; no A1 diagnostic/timeout child remains at host census. No live writes.
G1 movement16:50 corrections reviewed and concrete remaining corrections filed
in shared ledger while body work continued; autonomy not abandoned or certified.
### FB-01aj bounded local refinement contract — 2026-09-26 17:19Z

Continue from232af24c0. Contact-onset localization, compiled equivalence and
discrete work accounting remain closed. G1's failed independent food acquisition
is reviewed separately in shared ledger17:14; no cognition work added here.

Independent source-only numerical recommendation: local dyadic step doubling
with unchanged implicitfast, NOT an XML-only RK4 switch. RK4 treats damping
explicitly and current wrapper does not check its internal stages. Implicitfast
omits future constraint-force derivatives, so reevaluation during shorter steps
addresses the measured seam without changing force law. Source:
https://mujoco.readthedocs.io/en/3.3.7/computation/index.html#integrators
https://mujoco.readthedocs.io/en/3.3.7/modeling.html#solver-parameters

This is an OFFLINE solution qualification, not runtime admission. New only:
tools/guala_body_local_refinement.py. No NativeBody/model/schema/cognitive edit.
One original30ms torso prefix from authenticated archive; maxcoarsestep100us,
fixed tau.2ms/impedance.999, implicitfast, same effort/capacity/supply/guards.
No step exceeds100us, so timeconst>=2h safeguard cannot retune the contact law.

At every candidate node restore identical complete native integration state;
compare one h step with two h/2 steps. Both use the existing compiled interval
law, including each actual step's guards and work. Retain the fine trajectory,
never extrapolate coordinates/velocities/warmstart. Disagreement bisects, at most
five levels below100us; finest performed step1.5625us. Count ALL trial steps:
three per node, at most3*(2^6-1)*300=56700 per prefix. Scratch O(depth*nstate),
no persistent history or separate physical authority. Any native, finite,
geometry or energy-supply refusal terminates the whole diagnostic case; it is
not retried at weaker limits. Rejected numerical branches debit no physical
work. Only accepted half-step receipts carry forward supply/heat diagnostics.

Accuracy measures remain separate SI quantities: free translation; root/joint
angular difference using native quaternion differentiation; linear and angular
velocity difference; each motor/bearing work component. No weighted score.
Two explicit diagnostic precision requests1e-4 and1e-5 in their respective SI
units map sensitivity/cost. These are NOT derived production accuracy limits,
biological thresholds or correctness certificates. Existing .03rad/.008m guards
are not repurposed as error budgets. Step disagreement is only a local indicator;
both paths can miss an event. Preserve archived25us comparisons at10ms samples
to disclose accumulated differences, not call that trajectory exact truth.

Preflight ordinary100us30ms control against archive exactly. Fresh-engine repeat
must reproduce every accepted integration state, work value, and subdivision
decision; no model-header substitution or published variable-step body bytes.
Only mjSTATE_INTEGRATION scratch arrays are restored within this offline model.
Runtime model timestep is restored on exit. Source freeze/review before run.
Two precision cases plus one fresh repeat each, CPU60s/wall90s/RAM1GiB cap;
one process, no pytest/conftest, no native rebuild, before/after read-only AWS
and host cleanup census. A finite failure is retained, not a tolerance-tuning
loop. No claimed real-time pass: minimum three native steps per comparison.

Lookup failures this turn: functional_body_sensory.py and
functional_body_world.py do not exist. Discovered actual world boundary in
embodiment_world.py; no guessed path retried. Printing receipt head reached a
large compressed payload and truncated; future reads select JSON metadata only.
### FB-01aj refinement result — 2026-09-26 17:29Z

Source review found two localized evidence defects before execution: abandoned
left-subtree stats could outrun the committed prefix, and the fresh-repeat trace
did not authenticate individual accepted receipts. Both corrected, including
clearing rollback markers after each complete chunk. Final source-only PASS,
fingerprint fc7fd02f3fb04aeba90bdc81cb5e84370215f8cca6f6d063be71e956225b1030
verified before/after run. Source6b152fef0338287e... . No runtime source changed.

Session52750exit0; authenticated archived100us control exact. Both precision
requests failed at the first100us chunk:18charged native steps,6rejected
comparisons, zero accepted prefix and zero work/heat debit. Refinement reached
the declared1.5625us fine-step floor without satisfying the requested precision.
Each fresh-engine repeat reproduced the complete failure/state/trace/evidence.
PeakRSS144920KiB. Trial loops.0027-.0050s, not a realtime mechanical qualification.
No parameter relaxation or heavier rerun made.

Max observed disagreement across each failed search:
translation5.57813129e-8m; angle1.5557702148e-5rad;
linear rate5.8007584973e-5m/s; angular rate.19160964180480722rad/s;
work1.4517324165e-7J.
Those are maxima across attempted nodes, NOT the finest-node error. Do not infer
the latter from this record. Both cases stopped BEFORE the21.5ms self-impact,
so this run DOES NOT test whether adaptation resolves that impact. It proves
only bounded refusal and exact replay for these explicit diagnostic requests.
It is not a successful numerical solution, and an exit0 receipt means the
experiment completed, not that body accuracy passed.

Full output2397bytes authenticated SHA
5f938822ee4bad3082719522f72391811dd204f8be1ef87ae2f0897d7554b42c
in docs/evidence/FB-01aj-local-refinement.json. Preserve this failure; do not
repeat it as new evidence or serially loosen experimental tolerances until green.

Next body boundary is the actual motion/feedback accuracy contract and the
initial joint-boundary response, before promoting variable steps or another
integrator. This does not reopen native solver accounting/byte-equivalence.
Declared collision/joint-overrun safety limits do not define permissible
trajectory or velocity error. The tested equal-SI precision probes were not
production requirements. Derive numerical resolution from supported mechanical
and sensory outputs, and distinguish discontinuous contact/limit activation
from smooth-phase error. No new cognition, damping, reduced force or surface
exemption is authorized by this result. Body goal ACTIVE, not complete.

AWS pre17:22:16/post17:26:27Z: same1553/ec20ff/digest1d088e,1/1/0HEALTHY,
sameidentity, live2435784->2436335,persist2435753->2436329,errorsnull,
durabilityfalse,CPU51.04->51.07%,RAM3.206%. Clock-stalledALARM remains,
otherfourOK. Host census has no diagnostic Python/timeout child. No live write.
Shared G1 ledger17:14 records acquisition failure, unaccepted stale movement
filter and small recommended correction; no autonomy or feeding closure claim.
### FB-01aj closed joint-stop boundary correction contract — 2026-09-26 17:49Z

Continue numerical-accuracy seam from b69c2ba69; accepted compiled interval,
work accounting and optics are not reopened. Production1553 remains untouched.
No new G1 receipt after shared17:14Z; its movement/intake findings remain open.

Exact upstream source was downloaded to isolated /tmp/guala-body-mujoco-3.3.7-f1d45bd,
commit f1d45bd5422c74beddfb0d1deb590a02583d21de. Pinned checkout, not web-rendered
line numbers, is authoritative: engine_core_constraint.c728/1737 use strict
dist<margin for hinge/slide instantiation/count. Initial closed lower limits
therefore have no constraint row for the first finite integration step.
Independent body_force_review confirms a closed <= boundary removes this
unconstrained startup; it changes the pointwise force map. It is a declared
closed-boundary extension of the existing APPROXIMATE soft law, not exact
continuous equivalence or a general impact solution. At scalar rest/outward
acceleration a0, impedance d yields a=(1-d)*a0 rather than a0. No attractive
force is introduced by row admission; the original unilateral solver chooses
reaction. Separating velocity, inward loading, upper/lower and dense/sparse
cases must all be measured, not assumed.

Single change: paired hinge/slide <= predicates and unique native version
3.3.7+guala.closed-limits.1. No margin epsilon, initial pose displacement,
motor capacity change, new damping, response-time/impedance retuning, timestep
relaxation, force override, action controller, DSF or cognitive edit.
Ball/tendon/contact predicates stay unchanged. Later between-step crossings
and21.5ms self-impact remain open. Safety bounds are NOT accuracy tolerances.

Complete closure: retained patch native/functional_body/closed_limits.patch,
isolated reproducible builder native/functional_body/build_engine.py,
NativeBody exact ENGINE_VERSION and existing model/header hashing bind the
new law, tools/guala_body_joint_boundary.py supplies bounded proof. No old
header rewrite/automatic migration; old-engine retained state must refuse.
No functional body is mounted in production, so this slice performs no live
migration. MjData remains scratch; caller bytes remain the one authority.
No XML/schema/cognitive source change or duplicate solver. Build uses pinned
upstream dependency commits and no installed shared-library replacement.

Build/review: freeze tracked patch/builder/adapter/proof before compile.
Builder validates clean exact upstream commit, applies only retained patch in
the isolated checkout, and builds only mujoco target. Native version string
is observable through existing Python binding and startup gate. Executable
library hash is recorded separately from numerical-law version. Build flags
disable fast-math/contraction; no global install. Two compiler jobs at most;
wall/CPU/memory/process census and read-only AWS envelope.

Proof: upstream wheel scalar control then patched scalar run; hinge/slide,
lower/upper/interior/penetration, both velocity signs/zero, both force signs/
zero, dense/sparse. Compare interior/penetrating scalar outputs exactly,
reaction nonnegative, stationary unloaded/inward load no spurious reaction,
outward rest response matches regularized equation, warnings zero and fresh
state replay exact. The unmodified stock control must show absent equality
rows; patched identity must be reported from the actually loaded library.
Body proof uses unchanged archived torso-load XML, efforts, physical initial
payload and100/50/25us100us prefixes; native cold successors exact; old header
rejected. Also report all six original dyadic startup discrepancies down to
1.5625us without selecting new tolerances. No full recurrence/suite rerun or
production accuracy claim. Failure retains evidence and stops promotion.

Tooling preflight found cmake/ninja absent. Install only pinned cmake3.31.6 in
isolated body venv; use existing make. No missing build command is retried.
Git download completed session8704exit0; no simulator ran during inspection.
### FB-01aj closed joint-stop correction measured — 2026-09-26 18:01Z

The versioned closed hinge/slide boundary is now compiled and LOCALLY PROVED.
It is NOT a complete body pass, production deployment, or accuracy certificate.
Frozen source review found one localized proof defect: post-step auto-reset
could compare equal. Added zero-warning/finite full-state assertions after both
ordinary/fresh steps; final PASS d35c1b91c2a13ae8b5cfb981b16710d76fee869078379
fea4271a429627d8504, verified unchanged after execution. Proof SHA8a0c9383... .

Build session1689exit0,58.511s wall,100.690s childCPU,394536KiB maximum childRSS
(not simultaneous aggregate allocator peak), two pinnedCPUcores. Exact library:
4425152fa68de19c39b0bacf433349c2e0679f066ccd5fec38f9c3d76517a5ff,
4,294,840bytes, /tmp/guala-body-closed-limits-build/lib/libmujoco.so.3.3.7.
Actual Python/native version3.3.7+guala.closed-limits.1 confirmed. Upstream
source164MiB + build78MiB; isolated build artifacts retained for next mechanical
qualification, not installed into stock package or deployed. No extra binary
copy or whole upstream source vendored into repository. Retained patch only.

Stock session19945exit0:180 scalar controls,55,820KiBRSS. Corrected session23922
exit0:180 scalar cases pass,108 non-boundary cases INCLUDING complete step
successor hashes EXACTLY equal stock. Lower/upper, hinge/slide, dense/sparse,
positive/negative/zero velocity and force tested. Reactions remain unilateral;
stationary inward/zero loads have zero reaction. Scalar unit outward effort
at a closed hinge changes acceleration -250 -> -.250rad/s²; slide -1 -> -.001
m/s². These agree with original .999 soft impedance, not a newly rigid stop.

Body100/50/25us startup prefixes preserve initial physical payload and exact
fresh-engine full successors. State remains5152bytes. Old-engine header is
rejected without mutation; no automatic header transplant/migration. Archived
XML, effort limits, initial pose, supply and guards unchanged.

Whole-body motion accuracy remains OPEN. Initial one-step/two-half-step
angular-rate differences at100/50/25/12.5/6.25/3.125us coarse steps are
.1501124/.0807243/.0417979/.0212515/.0107128/.0053777rad/s. At the finest pair,
angle difference9.232e-9rad, translation5.476e-11m, linear-rate2.825e-9m/s,
work7.229e-12J. No tolerance was changed. This correction removes the identified
unconstrained equality step but DOES NOT make the previous1e-4/1e-5 diagnostic
requests pass, prove global convergence, or resolve later self-impact. Do not
call the remaining full-body discrepancy this same closed-boundary defect.

Authenticated controls/results, build and before/afterAWS receipts preserved in
docs/evidence/FB-01aj-closed-joint-boundary.json. Corrected raw49,653bytes,
SHA b73bdf6f2ba1e72619fcb78aa0ec0294f319c2c222d28e0f7f9d633ad0b5cad8.
Corrected proofRSS152192KiB. No repeated broad suite or load/release matrix.

AWS17:52:27->17:58:34Z same1553/ec20ff/digest1d088e,1/1/0HEALTHY,sameidentity,
live2439756->2440562,persist2439721->2440553,errorsnull,durabilityfalse.
CPU~51.05->51.04%,RAM~3.23%. Existing clock-stalledALARM still explicit,
otherfourOK. Host census: no owned build/proof/compiler/timeout survivor.
No caregiver/control/live-body writes. G1 still has no newer shared receipt;
A1's requested small movement correction and existing-artifact review stand.

Tooling failure preserved: /usr/bin/time was absent; wrapper exited127 before
builder started. Replaced only that command wrapper with Python resource/
subprocess measurement. No missing-executable retry, source reset, law change
or extra build. The downloaded checkout is now intentionally patched; do not
rerun the clean-checkout builder against it. Reuse immutable built library or
a fresh authenticated checkout. Corrected source requires this exact variant;
stock wheel alone is no longer the body candidate runtime dependency.

Next exact item: bound motion/feedback error using the declared mechanical
outputs and resolve remaining contact-transition integration. Do not confuse
safety penetration/overrun guards with accuracy, or relax equal-SI diagnostic
requests into a claimed production requirement. No return to force reduction,
extra damping, geometry exemptions, scripted posture, or cognition. FB-01 ACTIVE.
### FB-01aj constraint/damping split contract — 2026-09-26 18:08Z

Previous turn is PROGRESS:444762c67 adds a proved closed-stop numerical law.
Do not reopen its180case proof. Body tree clean at that commit; shared G1 ledger
still ends with A1's18:01 support entry. Autonomy findings remain separately open.

Archived corrected100/50/25us prefixes identify largest startup rate differences
at DOFs26/24/22/20: left distal digits3/2/1/0. For DOF26 at100us elapsed,
rates are+.0368271/-.1132853/-.0342476rad/s. Sign changes alone do not prove a
constraint error: the approved soft stop allows finite penetration.

Pinned engine_forward.c reveals a distinct operator split: mj_fwdAcceleration
and mj_fwdConstraint solve against physical inertia M; mj_implicitSkip then
advances with H=M+hB against forces already selected using M. The official3.3.7
documentation explicitly omits constraint-force derivatives from implicit
integration. Independent source/math review confirms H^-1 M need not preserve
the solved constrained-coordinate response. Actual body causation still needs
a same-step residual witness, not inference from scalar speed differences.

New diagnostic only tools/guala_body_constraint_split.py. One existing100us
torso step, no changed law/coefficient/pose/effort/guard. Intercept return of the
single original mj_step before kinematics/collision refresh. Retain pre-velocity;
read same-solve J,R,aref,lambda and qacc; compare unilateral residuals using
(a) qacc and(b) actual delta-v/h. Verify physical impulse equation
M*delta-v+h*B*delta-v=h*(F+J^Tlambda), and derivative exactly-Diag(B).
Final full successor hash must equal the already authenticated closed-boundary
100us receipt. Zero warnings, finite rows/state, no extra solve or scratch
publication. Only this first causal step is missing from saved evidence.

Analytic control is an exactly representable two-coordinate system:
M=[[2,1],[1,1]],h=1,B=diag(0,1),F=(-2,-1),J=(1,0),R=1/999,aref=0.
Original force999/1000 gives solved acceleration(-1,-999)/1000. Applying
implicit damping afterward gives(-334,-333)/1000 and active residual-1/3.
Jointly choosing force against H gives999/667 and acceleration(-1,-333)/667;
residual exactly0. Fraction arithmetic here is a tiny bounded offline proof,
not restored rational-body dynamics. This does not assert the full body is a
two-coordinate system.

If actual body confirms the split, next numerical correction must use one
consistent discrete operator for smooth acceleration, constraints, warmstart/
islands and final integration, while preserving physical M for kinetic energy
and preserving R/reference/cones. Recomputing softness from H, double-applying
damping, or globally overwriting physical inertia is forbidden. No runtime
candidate is authorized by merely writing these equations; full native caller/
sensor/work/cold identity closure must be specified first. This is body-only
numerical integration, not new DSF/cognition or a motion controller.

Source freeze and independent review, one tiny process cappedCPU30s/wall45s/
addressspace1GiB, same immutable custom library, no rebuild/pytest/broad suites.
Read-only AWS pre/post and owned-process cleanup. Preserve raw per-row residuals
and exact algebra with authenticated hashes. No manufactured accuracy threshold
or claim of whole-body convergence. Existing first100us error requests remain
diagnostic only; production accuracy budget and later impacts remain open.

Diagnostic correction18:16Z: first one-step process exited1 in0.61s because my
analytic control mistakenly asserted split residual-1/3. Exact arithmetic is
-334/1000+(1/999)*(999/1000)=-333/1000. The body observation and full-successor
assertions had completed before this late analytic assertion; no artifact was
published, so these are not accepted numeric measurements. Correct the one
assertion and move analytic verification BEFORE body construction, preventing
lost body work on future algebra errors. Review this localized correction once;
rerun only the single100us step, not previous suites or build. No runtime edits.

### FB-01aj same-step split proved — 2026-09-26 18:30Z

Final source-only review PASS1840be26dc7c8f6479ebc6f1b017e11129e5b441c759ed9dcee628f074159382;
fingerprint verified after the diagnostic. Corrected one-step process exit0,
0.594s wall,148100KiB peakRSS. First failed assertion retained in evidence.
Full prior successor44782dea2b7a0092a57c53742c8e8a4d4fe4359f6e1911a2f34114b11be2f4df exact.
14joint-limit rows,7positive reactions, no contacts/warnings. D=-diag(B) and
passive force=-B*v exact. Maximum active residual before integration4.44e-16,
after integration378.275519rad/s^2; physical impulse residual2.17e-17.
The actual body's damping split is now demonstrated, not inferred from a
generic counterexample. Raw5040bytes SHAa497602033da1a4a6e834ee487abf5d63799529ec1a1964b7a1921dbb92f0fd0
in docs/evidence/FB-01aj-constraint-split.json. This is diagnostic evidence,
NOT a corrected runtime or whole-body trajectory qualification.

AWS1553/taskec20ff.../digest1d088e... unchanged; same identity,1/1/0 HEALTHY.
Pre18:17:20 live2442938/persist2442921; post18:18:22 live2443066/persist2443049.
CPU51.12->50.91%,RAM3.23->3.24%; errorsnull/durabilityfalse. Existing
clock-stalled ALARM remains; other four alarmsOK. Exact process handles exited;
host census confirms no diagnostic child/orphan. G1/TFE/IDE untouched.

Next solution seam mapped with independent source review, no implementation yet:
Newton's CGContext already centralizes inertia. Add explicit step-local
diagonal shift s=hB to its metric multiply and all dense/sparse Hessian
construction/reconstruction paths; map s through existing island DOF indices.
Form smooth acceleration with H=M+diag(s), evaluate warmstart under H, pass
same shift through constraint/island dispatch, then advance once with solved
acceleration. Preserve physical M/qLD/island inertia, physical stopping-scale
normalization, R,D,aref,friction cones, and standalone instantaneous mj_forward.
This avoids a second solver, duplicate anatomy and separate island factors.
Current interval calls mj_step; restore/final observation use mj_forward.
Work quadrature, sensory return, integration-state bytes and atomic caller
publication retain their existing roles; finite-step law needs a new identity.

Complete implementation contract must explicitly admit Newton/zero-noslip
and D=-B body profile; non-supported CG/PGS/fluid/tendon damping must refuse,
not silently use split dynamics. Close mj_step2/direct integrator/fwd-inverse
routes before coding. Dense/sparse and island variants need local equation
falsifiers before any longer impact replay. No production accuracy tolerance
is inferred from penetration safety guards or previous arbitrary SI probes.

Joe requested G1 audit during this work. Read-only original-pair inventory
found garden-apple and fruit-bowl already present; _is_food's semantic name
gate excludes both. Recorded exact evidence and bounded repair recommendation
in shared ledger18:30Z. No edits to G1's runtime files or new acquisition run.
FB-01 remains ACTIVE; no additional user approval is presently needed.

### FB-01aj coupled Newton step implementation contract — 2026-09-26 18:34Z

Continue, do not reopen closed joint-boundary proof. Previous turn PROGRESS:
d2a6c7a3a authenticates the exact body's split residual. Clean tree at entry;
G1 has the18:30 audit finding; no new requested body conflict in shared ledger.
Requested accurate bounded mechanics; current split acceleration is inconsistent
with solved constraints; conflict YES. Do not extend double settlement, adjust
strength/damping/softness, relax travel limits, or touch cognition/L0-L4.
Single item: a step-consistent Newton operator in the body-only native engine.
Approved reduction: rigid-body numerical mechanics, not full joint DSF or
microscopic muscle/skin biology; those domains are not evaluated or modified.

Law and source seam (new finite-step law, same h->0 physical equation):
F includes current bearing force-B*v. s_i=h*B_i, H=M+diag(s).
Solve a_smooth=H^-1 F, then minimize the existing constraint potential plus
0.5*(a-a_smooth)^T H*(a-a_smooth), keeping J,R,D,aref,friction and cones.
Advance v+=h*a and q with the existing mj_advance ONCE. No mj_implicit second
transform. Physical M remains kinetic-energy and stopping-normalization
authority. Step shift is an explicit internal argument, never a global mode,
physical inertia overwrite, new state field, controller, or parallel body.

Authorized repository files: new native/functional_body/coupled_step.patch,
build_engine.py, functional_body_native.py engine identity/profile admission,
one tools/guala_body_coupled_step.py focused witness, this ledger/evidence.
Vendor delta limited to engine_forward.c, engine_solver.c, engine_solver.h,
and engine_support.c version string; closed_limits.patch retained unchanged.
Builder authenticates all preimages and pinned commit before applying either
patch to a NEW isolated source checkout/build. No production install/mount.

engine_forward.c: split force accumulation from its physical acceleration
solve for reuse without duplicate solve. A step-only acceleration helper forms
s in existing bounded native stack, factors H in existing qH/qHDiagInv scratch,
and supplies a_smooth plus s to the existing constraint dispatch. warmstart's
Gauss cost adds s*x to M*x. Serial/threaded Newton calls carry s; all island
tasks join before stack release. Existing no-constraint and unconstrained-DOF
paths copy H-consistent a_smooth. Physical island inertia stays unchanged.

engine_solver.c: add nullable step shift and existing island DOF map to
CGContext. Central metric multiply supplies Ma and Mv including diag(s).
Add s to EVERY sparse/dense MakeHessian and FactorizeHessian reconstruction
diagonal. Incremental/cone updates inherit that base; no separate island
H factor or altered physical stopping scale. Existing CG/PGS wrappers pass
NULL; new internal shifted Newton entry invokes the SAME solver, not a clone.

Caller closure: mj_step uses a private forward implementation with explicit
step mode. Public mj_forward/mj_forwardSkip and NativeBody restore/final
observation remain instantaneous physical solves. mj_step2 uses the same
coupled helper and single advance. Direct mj_implicit[Skip] for implicitfast
must refuse rather than reapply the old split. Forward/inverse comparison is
not a supported discrete-step diagnostic and refuses before advancement.
NativeBody admits implicitfast/Newton/zero-noslip and diagonal bearing-only
velocity derivative: zero fluid density/viscosity, zero tendon damping;
existing direct motor/no-plugin/no-flex/no-callback restrictions remain.
Unused full-implicit/CG/PGS modes are explicitly unsupported for this candidate,
not silently relabeled corrected. The previous implicit-mode equivalence
probe is historical evidence, not authority to preserve an inaccurate path.

State/transaction closure: version3.3.7+guala.coupled-step.1 binds header to
new law; no new integration bytes or schema fields. All mutated MjData is
caller-owned scratch restored from input before each attempt. No successor
or supply debit is published before existing warning/geometry/work/time/
finite-state checks. Error leaves caller's bytes authoritative; fresh restore
must give the same next state. New scratch lifetime is one bounded step;
allocation/factor work replaces old implicit scratch/factor, with O(nv) shift
work only, no heap owner, copy of anatomy or second constraint solve.

Acceptance order: source-only frozen review first; isolated build once. Exact
two-slide control realizes M=[[2,1],[1,1]],B=diag(0,1),h=1,F=(-2,-1),R=1/999:
new acceleration(-1,-333)/667, solved/integrated acceleration equal. Dense/
sparse and island/monolithic variants, released/loaded boundaries, zero
bearing and warm/cold restore exercise the common operator. Supported current
body's archived100us input then must satisfy same-step constraint/impulse
equations and fresh-instance exact continuation; no predecessor hash equality
is expected across a declared new numerical law. Verify physical M and R
unchanged by integration against a pre-step physical forward observation.
The scalar control's error bound uses the declared solver tolerance and
binary64 roundoff, not a fabricated production trajectory tolerance.
Only after these pass run one bounded startup refinement/contact prefix to
test the diagnosed whole-body error. Whole-body accuracy, ordinary organism
mount, work conservation convergence, restart/safety and realtime remain open;
no deployment is authorized by a helper's green result. AWS/host envelopes
around execution and exact process cleanup remain required.

Candidate continuation: the latest user audit completed by checking the original
world/source without a rerun; food-name gate findings are already in shared
ledger18:30Z. Functional-body scope resumes unchanged. Previous goal work was
PROGRESS: the coupled source candidate was authored; no build was attempted.

Pre-freeze command failures preserved: one oversized inline shell argument was
rejected by the OS before execution. Source patch construction instead used
explicit temporary full-source files and a small read-only diff command. A
delete/add-same-file apply_patch transaction was rejected before mutation;
whole-file Update File replacement is the supported operation. Two guessed
engine_thread paths were absent; the known thread/thread_pool.cc contains the
public pool implementation. No rerun, runtime mutation or lost proof resulted.
The final patch removes the unused implicit-path nC local; no dead implicitfast
split remains. Existing full-implicit compatibility diagnostics are historical
and cannot qualify the newly admitted Newton/implicitfast-only wrapper.

Focused witness now authored in tools/guala_body_coupled_step.py. Analytic pairs
straddle an unconstrained global DOF to exercise nonidentity island indexing;
dense/sparse, island/monolithic, loaded/released/free, zero-bearing, retained
warmstart, cold and step1/step2 variants share the exact equation assertions.
One two-worker public native pool case checks the threaded argument lifetime.
Constructor and native refusals check unsupported modes without advancing
integration state. Existing100us body input checks physical M/R unchanged,
constraint residual, impulse equation, cold equality and old-law refusal.
No new trajectory accuracy tolerance or physical parameter is introduced.
The declared solver tolerance bounds the local equation falsifiers only.
No compile/test has occurred. Candidate proceeds to one frozen source review.

Frozen review1e9c992b...: one LOCALIZED finding, no architectural defect on
admitted body path. Raw native mj_step could disable bearing force while the
step metric retained hB. Native fwdCoupledStep now refuses mjDSBL_DAMPER;
focused witness proves integration state unchanged on that refusal. Wrapper
already refused disableflags. Both physical operator and coefficients stay
unchanged. One final source-only review, no test/build before its result.

### FB-01aj coupled step proved locally — 2026-09-26 19:04Z

Final source review PASS fd07996e...; source fingerprint verified immediately
before build/proof. Isolated library d3787b131b2532168dfff52c226ba07fa0de4ffc4b57bc40b7a87b73a2cc1801
compiled once in59.48s wall/103.57s CPU/394372KiB peakRSS, two cores. No install.
Coupled numerical law version3.3.7+guala.coupled-step.1. Native build output and
patch/source hashes retained in docs/evidence/FB-01aj-coupled-step.json.

Focused proof exit0 in0.894s wall/0.891s CPU/151288KiB peakRSS.16 exact control
variants, mapped two-island threaded/serial exact equality, ordinary/two-phase
stepping and fresh integration-state equality all pass. Eight unsupported
wrapper profiles and five raw-native routes refuse without integration advance.
The SAME body100us input has7 active rows: integrated constraint residual
4.44e-16 (previous378.275519), physical impulse residual5.01e-17; physical M/R
unchanged. Entire cold successor exact20973b5e574ef34e67b4069ad7346228e857bc1b6110680a833a989e4876b829,
5152statebytes, old-law header refused. Raw10753bytes authenticated as
b8bb13a6106172cd459e029fd83bb2b7fc672c7681058d3a726339f5003c1746.
No coefficients, anatomy, kernel, cognition or physical supply were changed.

Health envelopes in same evidence: AWS1553 same identity/task/image,1/1/0HEALTHY,
advancing ticks, checkpoint/cleanupnull and durabilityfalse; existing
clock-stalled ALARM remains. Host census confirms buildPID6997 and proofPID12999
exited with no compiler/test worker orphan. TFE/G1/IDE unchanged. G1 received
bounded source audit support in shared ledger18:59Z; autonomy not declared fixed.

The diagnosed force/integration mismatch is CLOSED locally. Whole-body motion
accuracy is NOT closed. Next contracted item: compare the same body startup
and30ms first-contact prefix at100/50/25us under this new law. No arbitrary
precision threshold will be promoted to production and no old adaptive replay
or broad test suite will be repeated. Production remains untouched.

### FB-01aj post-correction motion witness contract — 2026-09-26 19:07Z

c882904b6 commits the corrected operator and equation proof. That seam remains
closed; this is its authorized next motion diagnostic, not another solver edit.
Only tools/guala_body_coupled_step.py gains --motion-prefix plus this ledger.
The exact same model XML and original initial physical payload are authenticated
against existing controls; the new law header is never transplanted into old
state. Same torque, supply, stiffness, damping and numerical safety guards.

First record six startup dyadic comparisons using existing difference/restore
helpers. Then30ms at100/50/25us with samples at10/20/30ms. Measure active contact
wrenches with force/couple kept separately, first contact times, penetration,
work quadrature/unresolved exchange, motion disagreement and native time/cost.
The observer calls each native step exactly once and must match a fresh ordinary
unobserved cold successor at each resolution. Failure propagates immediately;
no force reduction, threshold adjustment, automatic retry or state publication.
Scalar/control/refusal proof mode is NOT rerun. No new production accuracy
claim: dyadic agreement is not an error enclosure. Same CPU30s/wall45s/1GiB
bound, AWS pre/post, exact process cleanup. One source-only frozen review before
this diagnostic, no rebuild. Non-goals: long replay, whole suite, cognition,
body/world mounting and production cutover until mechanical gates actually pass.

Frozen motion review db339f37... returned one localized measurement correction,
no architectural finding. Wrench components, contact separation and their norms
now must be finite before filtering or max/min aggregation. Grouped force/couple
peaks are explicitly named peak_point_force_n/peak_point_couple_nm: maximum
single contact-point wrenches, never summed geom-pair resultants. No runtime or
solver change. Final source-only review precedes the one bounded diagnostic.
Three temporary C source drafts (101KB) were removed after the committed patch
and built source preserved their complete changes; reconstructible from upstream
and c882904b6. No user/runtime state removed.

### FB-01aj motion diagnostic retained — 2026-09-26 19:23Z

Final source-only review PASS eeafa6ba...; unchanged library d3787b13... .
Bounded30ms diagnostic complete,1.395s wall/1.394s CPU/147428KiB RSS,2cores,
no warnings, no cold mismatch,5152statebytes at every resolution. No engine
rebuild or equation/regression-suite repetition. Exact compressed measurement,
run receipt, source review and AWS envelopes in
docs/evidence/FB-01aj-coupled-motion.json.

Startup dyadic100/50/25/12.5/6.25/3.125us disagreements decrease monotonically:
joint angle7.616e-6 ->9.233e-9rad; joint speed.023719 ->.00004667rad/s.
Pre-impact20ms angle differences100vs50=.00060985 and50vs25=.00030508rad,
consistent with first-order refinement. Same-step consistency remains closed.
After contact30ms differences100vs50=.017388rad/45.652rad/s;50vs25=.0070164rad/
19.118rad/s. Root translation difference is not monotonic (27.96 then39.78um).
Right forearm/torso onset21.5ms and left palm/thigh21.8ms agree at all steps;
digit4/palm onset26.2/26.2/26.075ms. Maximum single-point forearm contact force
7502/7088/6881N; these are not total pair forces or joint-row reactions.

Signed work14.1488/14.1814/14.2452J; bearing quadrature3.4045/3.4097/3.4004J;
unresolved exchange9.9317/9.9951/10.0520J. Unresolved exchange is NOT certified
heat or numerical error. This receipt does not justify a production timestep
or claim continuous body accuracy. Next causal item: resolve contact/limit
energy and rapidly changing impact velocities under the unchanged law before
choosing a bounded accuracy/performance contract. No force/damping tuning.

Reporting failure disclosed: first child exited0 but the outer wrapper read
the compressed envelope as plain result and raised KeyError(engine_version)
before printing the raw receipt. That unretained run is not accepted evidence.
Repeated this short diagnostic ONCE with raw receipt printed before decoding;
no source/physical parameters changed. Durable recurrence: decode/authenticate
encode()'s raw_bytes/raw_sha256/payload_zlib_base64 outside the execution wrapper;
print raw execution receipt before optional interpretation. Never rerun merely
because analysis of an already retained artifact fails.

AWS1553 task/image/identity unchanged,1/1/0HEALTHY, ticks2450724->2450898,
checkpoint/cleanupnull, durabilityfalse. Existing clock-stalled ALARM remains;
CPU51.06%, RAM3.24%. Proof ran in sandbox PID141, handle56646 terminal; host
process census has no guala_body_coupled_step worker. No production writes.
G1's separate food-boundary audit recorded at19:15 in shared ledger; no takeover
of cognition or duplicate autonomous-acquisition trial.

### FB-01aj coupled work attribution contract — 2026-09-26 19:31Z

Previous goal turn PROGRESS96480fb8c. Continue the same mechanical acceptance
path, not a new body/controller or an accuracy claim. Current30ms residual
includes intentionally unaccounted constraints; it cannot be called energy
loss, heat or integration error before separation. Full DSF/cognition untouched.
The exact next item is one25us/30ms read-only work attribution using existing
tools/guala_body_constraint_work.py from tools/guala_body_coupled_step.py.

For the admitted coupled law, M*dv = h*(actuator + constraint - bias - B*v_next).
Dot with(v_pre+v_next)/2 and add the measured inertia-metric change to obtain
the exact discrete kinetic-energy identity. Keep positional potential and
ordinary trapezoidal bearing quadrature separate. Native qDeriv is not updated
by this coupled path, so the old implicitfast qDeriv assertion is inapplicable;
check solved acceleration equals dv/h instead, retaining the impulse residual.
Aggregate constraint work h*(J*v_mean)[i]*lambda[i] by actual constraint type
and physical joint/contact identity from THAT solve. No new solve or heat law.
Compare row sum with generalized constraint work and report finite residuals.

Only these two offline tools plus evidence/ledger change. Existing advance,
operator, coefficients, state format, anatomy, supply and safety guards stay
byte-identical. The observer invokes mj_step once per original substep and
must equal the whole ordinary successor; its state SHA must match the already
retained25us motion prefix40511baa... . No startup sweep, equation suite or
other loads are repeated. Source-only frozen review,1GiB/30CPU-second/45wall-
second bound, raw receipt before decoding, AWS pre/post and process cleanup.
No production or borrowed live state. A failed first causal check stops this
diagnostic without changing the physical law. Continuous accuracy and thermal
interpretation remain unqualified until evidence supports them.

Recurrence lapse recorded: attempted to read nonexistent
tools/guala_body_discrete_work.py despite the prior no-retry note; no execution
or state change resulted. All current paths are now validated from rg output;
reuse only tools/guala_body_constraint_work.py. Do not repeat that lookup.

Frozen work review1ce87b6c... found two localized reporting/dispatch issues,
no architectural finding. Coupled-path selection now requires both known version
and implicitfast (does not double-select historical fullimplicit diagnostics).
The old trapezoidal constraint/remaining-closure fields are explicitly labelled
hybrid estimates pairing coupled step-start forces with the adapter's final
instantaneous physical forward sample. Only discrete_update is used for work
attribution. No operator/source law or additional runtime call introduced.

### FB-01aj discrete work attribution measured — 2026-09-26 19:38Z

Final review PASS7b404ca4... verified unchanged before run. One25us/30ms trace,
1200substeps,1.112s wall/1.111s CPU/150184KiB RSS,2cores, no timeout/error.
Whole ordinary and observed successors match, as does the previously committed
motion prefix state40511baa... . Exact raw envelope/health/process receipts in
docs/evidence/FB-01aj-coupled-work.json. No engine rebuild or broad tests.

Discrete measured work: actuator14.24522345J; constraint-10.05181170J;
passive-3.39989309J; implicit bearing increment-0.00019647J;
negative bias-1.05439282J; changing inertia metric+1.05386526J;
kinetic change+0.79279464J. Ordinary bearing quadrature3.40042717J.
Sum absolute per-step discrete closure2.0532e-11J; peak1.2643e-13J.
Peak impulse residual4.1757e-15; peak row/generalized work disagreement1.11e-16J.
The prior10.05200165J unassigned remainder is almost entirely constraint work,
NOT10J of lost energy or evidence of thermal dissipation. Including measured
constraint work leaves.00018995J from already separated quadrature/bias/metric
terms; their algebra explains it within3.10e-15J. No heat is assigned.

Constraint attribution: torso roll limit-9.17631906J; left palm/thigh contact
-.51695544J; right forearm/torso-.31957696J; left palm roll limit-.03557543J;
remaining groups are in artifact. Solver max5iterations, never at cap. Thus
joint/contact exchange, not an unresolved force-solve residual, owns the energy
gap. Hybrid endpoint-force constraint quadrature differs by-1.7432J and is NOT
used as attribution. Its scope label prevents false heat/error interpretation.

Body numerical accuracy and lawful heat/storage partition remain open. The next
motion task stays at the resolved21.5–22ms self-impact and low-inertia digit
response: derive a bounded contact-aware accuracy method without force/anatomy
tuning, a blind global timestep decrease or promotion of arbitrary equal-SI
probe tolerances. The energy finding does not require reopening the coupled
operator or changing the kernel, and it does not authorize production.

AWS pre19:34:44/post19:35:36Z same1553 task/image/identity,1/1/0HEALTHY,
ticks2452421->2452519,errorsnull,durabilityfalse; existing clockALARM remains.
Diagnostic sandbox PID137/session72149 terminal, no host body-worker orphan.
No live write, caretaking change or repeat acquisition witness.

### FB-01aj matched impact-resolution contract — 2026-09-26 19:52Z

Previous turn PROGRESS: closed work attribution committed39f2862c9; separate
G1 audit updated shared ledger without touching G1 source or production.
Continue mechanical-accuracy gate. Requested: a force/energy-limited body with
truthful feedback and bounded numerical error. Current coupled step is internally
consistent, but post-impact trajectory accuracy is unqualified; conflict remains
with any claim of completed body delivery. No runtime, force, anatomy, cognition,
kernel, heat law or production settings will be extended in this diagnostic.
Reduced numerical rigid-body approximation; no continuum or full-DSF claim.

One exact next item: tools/guala_body_impact_resolution.py reconstructs the
same25us trajectory only to20ms, verifying qpos/qvel against authenticated
FB-01aj-coupled-motion evidence. It saves the complete integration scratch once.
Five subsequent2ms windows start from that IDENTICAL retained state at steps
25/12.5/6.25/3.125/1.5625us. This separates local contact-resolution differences
from inherited global errors. It is not a blind global timestep shrink or a
production tolerance selection. No equal-SI thresholds are promoted.

Impact map: archived model/load/supply -> existing NativeBody.advance prefix ->
full integration array -> unchanged compiled interval/coupled solver/guards ->
same-solve contact evidence -> endpoint kinematics/sensors -> compact offline
receipt. Each window is repeated in fresh native model/data and must have
identical whole integration bytes, work, sensors and geometric output. No
serialized state headers are rewritten or published; fractional-microsecond
timesteps exist ONLY in unpublished diagnostic scratch. No world is constructed.

Per-pair force impulses sum all contact points in world axes from the same solve,
before collision refresh. Intrinsic couples are labelled separately from torque
about an origin. Contact times, joint angle/rate, geom-center displacement/rate,
geom orientation/spin and work differences remain distinct SI quantities. No
heat/storage claim. Finite checks precede all reductions. Error indicators are
not certified accumulated/continuum bounds. Native calls are bounded at5760
(800prefix +2*(80+160+320+640+1280)); arena1GiB, CPU30s, wall45s, two cores.
Source-only frozen independent review precedes this one diagnostic. Preserve
raw output before decoding; AWS read-only health before/after and exact child
cleanup required. No equation suite, prior motion sweep or G1 witness repeated.

Lookup mistake: an rg command included nonexistent functional_body.py; no file
or runtime was changed. Actual body paths were subsequently resolved using
rg --files. Do not retry that nonexistent path or print compressed evidence
payloads to inspect metadata; decode the existing envelope directly.

### FB-01aj local impact-resolution evidence — 2026-09-26 19:55Z

Frozen source review PASS e635ae33..., unchanged before/after execution. One
run1.580s wall/1.580s CPU/145588KiB, no warnings/errors, 5760 native steps.
Authenticated raw8114bytes SHA987c2776... retained with full measurements and
health envelope in docs/evidence/FB-01aj-matched-impact.json. Common20ms full
integration predecessor SHA17247548..., archived pose/rate exact. Each schedule
matched fresh-model replay in entire5120-byte integration state, work, sensors
and geometric endpoint. These scratch records do not replace caller headers.

Pairwise joint-angle differences25vs12.5 ->12.5vs6.25 ->6.25vs3.125 ->
3.125vs1.5625us: .00142661/.00071723/.00019148/.00018165rad.
Joint-rate differences2.71155/1.40481/.98750/.35679rad/s. Maximum geom-center
differences21.82/10.63/1.04/2.62um and center-rate39.17/19.32/3.25/4.92mm/s
are NOT fully monotonic. Right forearm/torso impulse differences
.007342/.008687/.008055/.003654Ns; left palm/thigh
.001929/.000927/.000610/.000204Ns. Each impulse is the sum of pair forces on
its SECOND native geom, in world axes, sampled from the original solve.
Intrinsic couple impulses exclude moment-arm torque. Right contact onset
21500/21487.5/21481.25/21478.125/21478.125us; left onset
21800/21800/21800/21796.875/21796.875us. No coefficient was tuned.

Conclusion: impact-timing resolution contributes, but smaller steps alone do
not yet qualify accuracy. Low-inertia digit-rate disagreement contracts while
right contact impulse and some geometry observations vary non-monotonically.
Do not select an arbitrary acceptable step, call a pairwise difference an
error enclosure, or repeat the global load sweep. Next mechanical analysis is
the existing contact-manifold/active-row transition and its local error estimate
under the same law, using this retained measurement. No body integration or
release is authorized by this result. No heat/storage partition is asserted.

Production safety exception disclosed: pre19:51:54 same1553 running1/desired1;
post19:53:34 desired/running/pending0/0/0, no active tasks. AWS events record
taskec20ff... stopped19:53:28 and draining19:53:37. The sampled endpoint still
reported tick2454570 at the boundary, which is NOT evidence of a running task
after drain. Existing clockALARM persisted. No production-write command was
executed by this work. Stable live health cannot be certified; flagged to Joe
and G1 ledger without interfering with a possible independent cutover. Worker
139/session36727 terminal0; host process census shows no body diagnostic orphan.
No new heavy work while this external lifecycle transition is unresolved.

### FB-01aj contact-manifold isolation contract — 2026-09-26 (pre-run)

Previous goal turn PROGRESS: reported new live1554 and measured continuing
zero reserves; no body claim or production intervention. Body branch remains
e05dc974a. Continue FB-01aj; coupled equation/work/restart evidence remains
closed. Requested: accurate force-limited articulated mechanics and truthful
self-sensory return. Current reality: local impact refinement leaves nonmonotonic
impulse/geometry disagreement. Conflict: YES with completed body accuracy, not
with the already-proved coupled algebra. No body law, force, anatomy, thermal
assignment, cognition, kernel, production code or settings will be extended.
Single next item: isolate same-solve contact geometry and friction-row states
in the two already-measured finest windows. Reduced rigid-body/contact mechanics;
no continuous tissue, neuronal or full seven-field evaluation is claimed.

Source inspection: native capsule/box collision emits up to two sphere/box
contacts based on the closest segment/face/edge feature. The contact tangent
frame generator chooses a seed according to normal.y within(-.5,.5); the
pyramidal constraint uses that frame. These are candidate causes, NOT a proved
diagnosis. Retain the current law; do not switch friction cones or retune
impedance merely to obtain agreement.

Reuse tools/guala_body_impact_resolution.py with --manifold rather than adding
another harness. Same authenticated20ms predecessor, unchanged3.125us and
1.5625us2ms windows. Add read-only samples immediately after mj_step and before
collision refresh: all right-forearm/torso contact points, including zero forces,
box-local point positions, full world contact frames, signed separation,
contact wrench, friction and efc_state. Native point indices are NOT persistent
physical identities. Fractional steps remain unpublished scratch. Preserve all
guards and the existing full integration/work/sensor/geometry fresh-repeat proof.
Compare resulting state/work/impulses to the prior retained evidence so observer
instrumentation cannot silently alter dynamics. No default resolution sweep.

Bound:800prefix+2*(640+1280)=4640 native calls;1920 contact-frame records for
one pair, at most2 points each. Same2cores/1GiB/30CPU/45wall envelope. Retain raw
output before analysis; freeze and independent source-only review before run.
Only offline analysis may summarize these samples; no diagnostic enters runtime.
AWS pre/post and host cleanup census required. No new accuracy tolerance.

Production transition now resolved observationally:1554 task94aceb29... is
RUNNING/HEALTHY1/1/0 at20:03:51, digestc7e7bd50..., same identity, tick2455628,
errorsnull,durabilityfalse. This does not certify feeding or code changes; live
reserves remain0, recorded in shared ledger20:04. Clock alarm remainsALARM.
The earlier GET503 is retained as transitional failure, not ignored. A sandbox
process census exposed only its own namespace; use host-scoped read-only census
for actual concurrency rather than treating that empty list as cleanup evidence.

### FB-01aj contact-manifold cause isolation — 2026-09-26 20:15Z

Source-only independent review PASS f9df4ac4..., verified unchanged before and
after run. Required older-window comparison performed OFFLINE after raw stdout
was retained: both complete integration state hashes, work, every contact pair's
impulse/separation/time record, and pairwise comparisons are EXACTLY equal to
FB-01aj-matched-impact. New observer does not change physical trajectory.
One run1.43082s wall/1.42624CPU/146288KiB;4640 native calls; no warnings/errors.
Raw measurement273334bytes SHAcefe49b347331f4ad644b58be3c391862df22cebeb0641db01e514a87ce3b927
retained ONCE in docs/evidence/FB-01aj-contact-manifold.json. Source SHA
ac60c887b2a177861072cef084f354c38512dc81b577fd1a5b164c1752fec021.

Ruled out in this window: capsule-box manifold switching and tangent-frame seed
switching. The right forearm/torso has exactly ONE contact point throughout its
contact portion at both resolutions. Normal.y stays.999761–.999844; no crossing
of the native+.5/-.5 tangent-seed boundary. Largest successive normal change
contracts2.92759e-5->1.46515e-5rad, local point displacement2.120->1.077um.
Do NOT change contact shape, friction cone, solver impedance or body anatomy on
the disproved feature-switch hypothesis.

Both schedules first detect this contact at21478.125us. The reaction jumps from
zero to4872.889/4868.467N. First friction-edge deactivation is21812.5/21814.0625us;
second21815.625/21817.1875; all edges inactive21865.625/21867.1875us. Most impulse
disagreement is already in the all-four-active segment, so attributing it solely
to late friction-state switches would be wrong. This is a rapidly varying
onset transient with finite-step state and force-integration disagreement.

Exact discrete-sum identity (coarse3.125us minus fine1.5625us):
deltaI = h*sum(Fcoarse(t)-Ffine(t))
       + h/2*sum(Ffine(t)-Ffine(t+h/2)).
Total world components[.00007588981,-.00098287490,.00351865750]Ns;
same-time force-state term[.00086415880,-.00456721782,.00383042225]Ns;
fine within-step variation[-.00078826899,.00358434292,-.00031176475]Ns.
Closure max2.25e-16Ns. Terms partly cancel: nonmonotonic totals alone do NOT prove
a geometry defect. This decomposition is not a continuum error bound, nor a
counterfactual proving that aligning onset alone repairs the whole trajectory.

Next mechanical item: derive bounded contact-onset/time-integration refinement
using the existing signed geometry, physical relative motion and unchanged
coupled law. Qualify that narrow correction against this retained transient;
do not repeat the global sweep or select an arbitrary acceptable timestep.
Body motion accuracy, contact heat/storage, ordinary organism integration,
performance and production release remain OPEN. No live body deployment.

AWS pre20:09:38/post20:11:20 same1554 task94aceb29..., digestc7e7bd50...,
1/1/0HEALTHY, ticks2456714->2457040, errorsnull,durabilityfalse. Existing clock
ALARM remains; all four other queried alarmsOK. Local caretaker PID49571 in
the main Guala tree was identified and untouched. Worker146/session32112
terminal0, host census no body diagnostic child/orphan. No live writes.
The pre-run contract's originally typed20:14 timestamp was clerical and has
been replaced with a date-only header; actual receipt UTCs are authoritative.
An eight-line artifact preview exposed part of the compressed payload; no
evidence was lost, and subsequent inspection used decoded retained data only.
Push and Slack restrictions remain; neither was retried or bypassed.

### FB-01aj event-aligned numerical witness contract — 2026-09-26 20:25Z

Previous turn PROGRESS, local477424d4a. Continue the same open body-accuracy
gate; coupled algebra/work and the disproved manifold-switch hypothesis remain
closed. Requested: force/energy-limited mechanics with bounded numerical error.
Current reality: rapid impact onset gives finite-step force/state disagreement.
Conflict: YES with a qualified production body, not with the declared force law.
No anatomy, friction, impedance, forces, kernel, cognition, thermal law, live
controls or production code changes. Single next item: test event-aligned
subdivision on the retained20–22ms mechanical witness. Reduced numerical rigid
body approximation; continuous tissue/full DSF and exact trajectories unavailable.

Physics/numerical contract: signed separation g is queried by mj_geomDistance.
Source engine_support.c:447 dispatches capsule/box to the SAME analytic primitive
used for contact generation, with a query cutoff derived from centers/radii.
No second geometry approximation, changed contact margin or force is introduced.
For a proposed step with g(start)>=0 and g(end)<0, bisect the native one-step
trial flow from one unchanged full integration predecessor. Use absolute native
clock coordinates; stop only at adjacent representable binary64 times with
the two observed signs. At most53 binary bisections within one exponent bin.
This brackets that NUMERICAL trial-flow crossing, not an exact continuous root
or a general first-impact/continuous-collision guarantee.

Commit the crossing-side trial's full native state, work and impulses ONCE;
discard all other trial successors. Settle the remaining original step duration
with the same engine. No force clipping, changed body time, fabricated contact,
or second settlement authority. The existing compiled interval checks every
trial for warnings, finite state/work, supply, travel, penetration and limits.
An unsafe trial terminates the witness; no catch-and-relax retry. Retained supply
is debited only for accepted mechanical pieces; all computational trials count
against the diagnostic resource bound. Full integration restore is checked
byte-exact; no serialized header is transplanted and no state is published.

Scope is ONLY the two measured, separated capsule/box onsets. Simultaneous or
more than two onsets refuse. No body-wide collision policy is claimed. Source
tools/guala_body_event_resolution.py imports existing prefix/endpoint/geometry/
work helpers. One ordinary25us single-step control must exactly reproduce the
prior whole state, work and contact integrals before interpreting new output.
Then25/12.5/6.25/3.125/1.5625us schedules compare impulse, pose/rate, geometry and
work; every schedule repeats in fresh native model/data including full retained
state, sensors, event brackets and receipts. Preserve failures without rerun.
One shadow comparison alone will not certify full-body accuracy or a timestep.

Bound800prefix+80control+2*sum(80*2^level+2*(53+3))=6960 native calls;
two cores,1GiB,30CPU seconds,45wall seconds. Raw child stdout retained before
decoding; pre/post AWS and exact host process cleanup required. Frozen source
review precedes all imports/compilation/execution. Initial unexecuted source
draft preceded this durable contract entry; no execution occurred in that gap.
Do not repeat that ordering: subsequent implementation contracts must be logged
before creating their source. No broad suite, engine build or organism trial.

Source review d2056100... found no architectural defect; one localized batch:
preserve native contact-point addition order, require exactly both distinct
onsets, retain structured failure context before re-raising and emit completed
control/case frames, and compare union-of-contact groups with finite impulse
norms. Main and independent findings were batched before execution. No physical
law, scope or acceptance weakening. Re-freeze once for final source verification.

### FB-01aj event-aligned witness retained — 2026-09-26 20:44Z

Final frozen independent source review PASS a35e2ea0..., verified unchanged
before/after execution. New evidence retained once in
docs/evidence/FB-01aj-event-resolution.json. Raw final measurement9184bytes,
SHAa498db53e982ddc8d27a281284e69426be407eeb93b1584982c862f3cf6ede30.
Source SHAd8a9cdcad00009f36934bb6e0c45668b79406b2d3ad2594b735788a50c48e89c.
One run2.209013s wall/2.208278CPU/148144KiB;6696native calls<=6960.
Ordinary control reproduces the accepted predecessor exactly. Five aligned
schedules each repeat exactly in fresh native state. Session2955/PID137 exit0;
host census after completion found no diagnostic child/orphan. No broad tests,
engine rebuild, copied production body, process signals or production mutation.

Adjacent-clock brackets measure the numerical trial flow, NOT exact physical
collision time. Right-onset estimates21.4761664->21.4766379ms converge across
25/12.5/6.25/3.125/1.5625us schedules. Pairwise right-contact impulse differences
.0563918,.0227857,.00762294,.00375299Ns now decrease monotonically. Geometry
differences21.4178,10.4567,5.2551,2.6514um; joint-rate differences2.46976,
1.29106,.694253,.365422rad/s also decrease. Coarse right-contact disagreement
is LARGER than the prior unaligned witness: previous cancellation concealed
some differences. This is not proof of uniform improvement or a continuum
error bound. No production timestep or general collision policy is accepted.
Body accuracy/performance, heat/storage partition and live integration stay OPEN.

Operational mistake: immediate pre20:32:31 AWS snapshot had service0/0/0,
task1554/no running task and HTTP503; post20:34:35 had1555/0/0/0 and HTTP503.
The launch wrapper checked shell exit0, not the partial-safe health contents,
and incorrectly started the isolated diagnostic. User informed. Keep its local
mechanics evidence but exclude production-health qualification. No production
change was made by A1. The retained execution wrapper now requires explicit
GUALA_BODY_HEALTH_SNAPSHOT content and checks service counts, one running healthy
task/image, available observation, identity/tick and absence of durability/
checkpoint errors before spawning. Its exact executable function is retained
in the evidence artifact. Pure JSON checks: recovered snapshot admitted;
both actual0/503 snapshots, missing and partial evidence REFUSED. No mechanics
rerun. A fresh immediate snapshot is still required for every future launch;
this service-readiness check does not certify cognition or clear existing alarms.

Read-only follow-up20:40:35:1555 task45ffe3b7..., digestabcd2845...,1/1/0HEALTHY,
same organism identity, tick2462069. At20:41:29 tick2462223 still reserves0/500000,
deficit[1,1], current nutrition0. G1 deployment recovery is not autonomous feeding.
Existing clock ALARM persists; four other queried alarmsOK. No handoff claim
of nutrition closure accepted. G1 retains AUT-ORAL/AUT-01 ownership.

Known bootstrap mistake repeated read-only: legacy root validator expects
absent HANDOFF_2026-07-31. It exited65 without state change. Exact git root and
HEAD477424d4a resolved the already-documented branch distinction. Future root
preflight must test that legacy authority file exists before invoking the old
validator; otherwise use this explicit git root and sprint authority. Do not
repeat the known missing-file path. Process census unnecessarily included
unrelated agent command arguments; future cleanup queries must select only the
owned diagnostic executable and emit PID/PPID, not unrelated command strings.

Next body item remains deriving bounded numerical accuracy/performance from
this retained transient, not another global sweep or production release.
Push and Slack restrictions remain; neither was retried or bypassed.

### FB-01aj numerical acceptance requirement — 2026-09-26 20:51Z

Previous turn PROGRESS: a1ee7c6f1 retained reviewed event-resolution source,
authenticated evidence and the diagnosed launch-preflight failure. Continue
FB-01aj; do not reopen coupled settlement/work or the closed optical seams.
Requested: bounded numerical body motion and truthful physical feedback.
Current: safety guards and converging local diagnostics exist, but no finite
output-accuracy requirement. Conflict:YES with claiming production accuracy.
Do not extend cognition, DSF, anatomy/force retuning, sensory quantization, or
the diagnostic's two-pair event handling into a general controller. Single
next item: ratify a body-only engineering accuracy contract before timestep
selection. Reduced rigid-body numerical mechanics; continuous tissue detail
and a mathematically enclosed continuous trajectory remain unavailable.

Source-only review independently confirmed no hidden accuracy contract:
functional_body_native.py:36 limits admission/travel/penetration, not solution
error; :393-420 forwards raw nonzero contact force and native sensor floats;
functional_body_anatomy.py:74 declares channels, not bandwidth/resolution.
embodiment_world.py:2616-2720 preserves these values without quantization.
Native _native_transition(:4654) executes the fixed-step interval and carries
work into world custody. Organism prepare_body_energy(:1634) rounds a measured
work debit upward to nanojoules, but that serialization quantum is NOT an
accuracy allowance for dynamics or quadrature. No biological precision inferred.

Smallest proposed correction is a VERIFICATION contract, not new runtime state:
one 250ms commanded interval; SI surface-position/orientation and rate errors;
separate instantaneous contact force/onset timing and world-frame integrated
impulse; separate positive motor work, signed work and bearing-loss errors.
Require resource/refusal bounds and whole-state cold continuation as already
specified. Integrated impulse agreement may not conceal a missed contact or
different instantaneous tactile sample. No rounding, clipping or weakening of
BodyFeedback is authorized by this proposal. Step-doubling remains an indicator,
not a rigorous global enclosure. Numerical values cannot be manufactured from
the observed differences or existing safety guards.

Asked Joe one physical-fidelity choice: recommend explicit engineering targets
for submillimetre handling with separately published force/energy error limits,
or use his specific physical accuracy requirements. This is the first turn
waiting on this requirement; goal remains ACTIVE, not paused/complete/blocked.
No mechanical test/build or AWS mutation in this turn. Further resolution sweeps
cannot determine the absent acceptance requirement and will not be run for that
purpose. Independent source reviewer completed; no diagnostic job running.

Read-only lookup error: a command guessed functional_body_native/anatomy/world
at the service root. Actual body modules are under substrate, and world custody
is in substrate/embodiment_world.py. The failed command made no changes; exact
paths were resolved through rg --files before continuing. Retain those resolved
paths rather than reconstructing basenames from memory.

### FB-01aj concrete engineering accuracy proposal — 2026-09-26 20:56Z

Previous turn PROGRESS6116d6cf8. Same active accuracy contract; no solver,
anatomy, receptor, cognition, kernel, thermal or production change. Required
architecture is unchanged; current conflict is an unspecified acceptance
requirement, not permission to redefine physical success. Numerical rigid-body
approximation remains explicit. The single next item is the physical-fidelity
choice already asked of Joe; this automatic continuation is not his approval.

Recommended PROPOSAL ONLY, not ratified constants or a biological claim:

| Physical quantity | Proposed verification error ceiling |
| --- | --- |
| Material surface position, including rotation | 0.1 mm |
| Link/camera orientation | 0.01 degree, geodesic rotation angle |
| Linear rate | 0.001 m/s + 0.1% of reference magnitude |
| Joint/angular rate | 0.01 rad/s + 0.1% of reference magnitude |
| Inertial specific force | 0.01 m/s^2 + 0.1% of reference magnitude |
| Contact force | 0.01 N + 0.1% of reference magnitude |
| Contact couple | 0.00001 N m + 0.1% of reference magnitude |
| World-frame contact impulse | 0.000001 N s + 0.1% of reference integral of force magnitude |
| Each motor-work/bearing-loss quantity | 0.000001 J + 0.1% of its corresponding gross-work integral |
| Contact event-time uncertainty | 1 microsecond |

These are proposed engineering fidelity requirements, NOT values derived as
unique consequences of anatomy and NOT selected as passing thresholds. The
smallest declared digit radius is4mm; 0.1mm is submillimetre handling relative
to that represented geometry, not a claim to reproduce skin microstructure.
Numerical accuracy is distinct from morphology/material-model accuracy.

Define metrics before applying them: for a primitive enclosed within radius r
of its reference frame, translation difference plus2*r*sin(rotation_error/2)
is a conservative bound on corresponding material-point displacement. Report
each primitive separately; centre displacement alone does not prove surface
accuracy. Use body/world vector frames consistently and rotation angles, not
quaternion-component differences. Rate/specific-force components and local
contact wrenches remain separately observable; do not flatten them into a
cognitive score. Work signs, positive input, braking and dissipation are not
interchangeable; energy residual is never relabelled heat.

At an onset/discontinuous force transition, finite event-time uncertainty can
prevent a pointwise force comparison from being meaningful. Retain the event
bracket, both one-sided loads and impulse; report the force range inside that
bracket as unresolved rather than passing it by time-warping, averaging away a
peak or emitting invented zero. The force-error ceiling applies outside those
explicit brackets. This is verification evidence only: no new runtime filter,
deadband, dropped sensory samples or alternate sensory values are proposed.
Missed contact sequences or unbounded event brackets fail the proposed gate.

Scope must cover the WHOLE250ms requested interval with real gravity, reachable
contacts, load/release and retained state, not only the20-22ms witness. Cold
continuation must remain byte-exact for a fixed numerical law. Actual resource
qualification concerns the complete organism/world/sensory path on the target
allocation;250ms is not independently available to each component. Reference
comparison and mesh disagreement must be labeled numerical estimates unless
a separate continuum bound is established. No finite comparison proves every
possible future body trajectory. No new sweep is authorized merely to decide
the proposed numbers.

Offline authenticated existing-data read only: finest-pair centre discrepancy
0.002651mm does not establish the surface limit; angular discrepancy0.010565deg
is larger than the proposed orientation ceiling. Joint-rate disagreement is
0.365422rad/s and right-contact impulse disagreement0.00375299Ns. Required
reference magnitudes/whole-interval evidence are not all present, so do not
infer other passes. This proposal does not convert the existing witness into
acceptance and does not weaken a failed assertion. No mechanical run occurred.

Same missing fidelity decision remains for a second consecutive goal turn;
this turn makes its recommended requirements explicit rather than repeating
tests or treating lack of a reply as authorization. No source or deploy is
blocked on a worker; there is no active diagnostic process. Goal remains
ACTIVE pending the reply/third-turn blocker audit. Push/Slack restrictions
remain respected. No notification retry or remote publication.

### FB-01aj current-world nutrition compatibility contract — 2026-09-26

Previous turn PROGRESS83f9dd99e. Numerical accuracy remains UNRATIFIED/open.
The third-turn blocker audit found safe required integration work: this branch
predates G1's committed material schema, so a blanket goal-block would be false.
Continue the required world/body custody path inside FB-01aj; do not mark
numerical acceptance closed or run another resolution sweep.

Requested: preserve the same body's real material and metabolic state through
the future native mount. Current branch lacks digestible_mass_micrograms and
transferred_digestible_micrograms, rejects their positive encoded records,
and still sums tasted material as nutrition in loop._oral_intake_micrograms.
Conflict:YES. Single next correction: carry G1's material/receipt/consumer
separation into the isolated body branch, with exact retained-state proof.
No kernel/cognition/behavior/controller/precision change; reduced body/world
model, not biological digestion or full DSF verification. No G1 source edits.

Donor is immutablefb9e54f3525d77bfe87ef938f87548e885b80716, not a moving worktree.
Authorized changes only: substrate/embodiment_world.py (typed material/contact
fields, canonical codecs, existing geometric oral mass transfer),
guala_functional_loop.py (intake reader), guala_home_world.py (the donor's
initial material declarations only), and a focused offline body-custody test.
Do not port donor housekeeping/custody auto-repair, cognitive suppression,
caretaker, curriculum, or deployment changes. No bare compatibility getattr:
current typed records own the new field; absent serialized zero remains the
donor's explicit canonical encoding. Never infer calories from a taste signal.

Causal map: declared material -> existing oral patch fraction -> source debit
and BodyContactState receipt -> applied-bite-only loop intake -> unchanged
metabolic law. Material/contact as_record and strict decoders carry quantities
through observation, authenticated encoded world, retained receipt, cold
restore. _native_project_world uses dataclass replace for poses and therefore
must preserve material quantities; _advance_material_time must likewise retain
them. Native mount/effort does not authorize oral contact or create nutrition.
Publication remains the existing prepared world transaction; no second owner,
state cache, material copy, retry or new persisted authority. Constant two
integer fields per existing material/contact; snapshot byte caps unchanged.

Localized donor defect to correct in this port and report to G1:
BodyContactState.verify checks transferred mass only under value>0. Negative
values and False can otherwise vanish in as_record. Validate integer/range
unconditionally, then reject nonzero transfer on non-oral contact. No widening
of valid records. Canonical zero omission must reproduce predecessor bytes;
positive values must survive physical debit, public receipt and cold restore.

Acceptance before wider integration: real world Pick/Oral/Place command
receipts conserve declared nutrient mass; tasted non-nutrient gives0 intake;
the native mount, one ordinary native interval, encoded cold restore and next
same interval preserve remaining material exactly. These are explicitly driven
mechanical/custody trials, not autonomous acquisition, mature-body proof or a
resolution-accuracy qualification. Malformed/negative/noninteger masses refuse.
Read-only fixtures only; no pytest/conftest, network writes or live checkpoint.
Source freeze and independent review precede execution; reuse installed engine
and existing bench, no compilation or broad regression. Preserve any failure.

Read-only command errors: one guessed test_tfe_embodiment_world.py path was
absent; another sed range used a nonexistent end-symbol and over-read source.
Neither changed state. Exact paths and both range endpoints must be discovered
before bounded display; no repeated guessed tests or open-ended range reads.

### FB-01aj nutrition translation review and acceptance map — 2026-09-26

Resumed at83f9dd99e with the four earlier uncommitted port files intact.
Previous user-audit turn produced new live/G1 evidence; it did not close this
body slice. No numerical approval has arrived. Scope and donor remain unchanged.

Owner source review: ObjectMaterialState -> EmbodiedObject material record ->
_material_from; oral geometric debit -> BodyContactState -> _contact_from;
prepared execution.after -> loop._oral_intake_micrograms ONLY when _apply
reports applied bite. No nutrient-specific input reaches L0–L4 or selection.
Pick and Place preserve material via dataclass replacement; _advance_material_time
changes only odorant reservoirs; _native_project_world replaces poses, not
material. _native_observation_for carries the same object record; native cold
restore decodes it with _world_from_compact_record and authenticates the current
envelope plus bounded retained receipts. commit_prepared_action reinstates the
prior state on failure; discard and committed rollback reuse existing custody.

Evidence map (backend-only, no new UI/API fields):
- declared source/debit -> material.digestible_mass_micrograms -> receipt's
  before/after objects -> canonical records/decoder -> identical cold world;
- removed nutrient -> active_contact.transferred_digestible_micrograms ->
  applied oral execution.after -> unchanged intake reader caller;
- sensory taste -> dissolved_tastant_micrograms remains separate even when
  nutrients are zero; zero taste also cannot erase positive nutrient transfer;
- mount/interval -> unchanged material on projected native world -> signed
  observation -> native envelope -> next same interval after fresh restore;
- failure/discard -> exact predecessor envelope, not a second nutrient debit.
No browser assertion or whole-organism feeding claim is part of this proof.

New focused unittest file reuses the existing world-custody native anatomy and
its effort command. Source preflight caught that the generic legacy oral radius
250mm would consume the100mm specimen wholly. The bench explicitly uses the
home's already-declared60mm mouth (home_world_authority), giving patch3600mm^2
and a first nutrient transfer4320ug from12000ug, leaving7680ug for recurrence
and mounting. This is disclosed fixture anatomy, not a runtime parameter tune.
All placement/holding/contact changes occur through real prepared commands.
There is no manual reserve, memory, source refill, or production checkpoint.

Four bounded checks: canonical malformed/zero/positive fields; three physical
material cases (taste-only, nutrient+taste, nutrient-only) with subsequent
restored bite; positive bitten material across mount/native interval/restore;
and prepared bite discard/rollback. Native work is three10ms low-effort bench
intervals, not a250ms loaded-motion accuracy proof. Gross rigid mass/inertia
and digestive chemistry are not coupled by this port; conserved quantities
here are declared nutrient/tastant ledgers and the exact transfer receipt.
The generic unmounted oral law is not a claim of articulated jaw mechanics.

Waste/closure: two scalar integer material/contact fields on existing records,
no per-tick data structure or new owner/call; existing decoder and command paths
only. No full world producer rebuild, learned-state migration, native compile,
housekeeping/custody auto-repair, or broad pytest run. Empty legacy nutrient
fields remain zero, not calories inferred from names or taste. This preserves
format compatibility, not missing old-world nutritional provenance; G1's
AUT-01 migration/material issue remains separately owned.

Candidate now freezes for one independent source-only review before importing
or executing the new proof. Execution budget: existing single-thread native
runtime,2 affinity CPUs,1GiB address space,30s CPU and45s wall; exact test process
tracked to exit with child census. These are harness containment ceilings, not
runtime physics/precision choices. Fresh read-only AWS service/task/observation
content must pass immediately before launch; take the same envelope after.
Do not infer launch permission from wrapper exit0 or an earlier healthy read.

Frozen source review bda4b32bf66784a47d14d4c672badeb874acdc82c6ba9cd10edf78fa548bbcf8
completed with one LOCALIZED finding, no architectural findings. Existing
migrate_declared_material_transport compared live digestive mass against the
initial declaration instead of preserving it alongside depleted odor/taste.
This would reject a lawful partially consumed object when the hook is used.
The single batch adds the field to that comparison's existing replacement and
asserts the hook is a byte-preserving no-op after both unmounted and native
depleted-state restore in the existing four-test suite. It adds no mutation,
refill, prior-checkpoint nutrient inference or new migration owner. Owner impact
map now explicitly includes this existing declaration-comparison branch.
Full-file source/test replacements applied; no imports or test execution yet.
Final source confirmation uses a newly frozen candidate. G1 should receive the
same preservation finding for its independently owned nutrient port.

Final source confirmation of591183c9e59afd93a150b934579d927bd59b9e0e8619895f030c55b332bf0be5
accepted the nutrient-preservation law and exposed one localized TEST expectation:
mounted native topology deliberately refuses the legacy migration hook. Correct
the preceding ledger's 'no-op after native restore' assertion: unmounted restore
requires a no-op; native restore requires the existing explicit topology refusal
and byte-identical retained state. Production guard is unchanged. The fixture
now asserts that precise ValueError then unchanged saved bytes. No new law,
topology allowance, mechanism, test case, import or execution was added. This
finishes the review correction batch; source fingerprint is refreshed before
the existing four-test proof, not a third architectural redesign/review cycle.

### FB-01aj nutrient custody verified locally — 2026-09-26 21:39Z

Final localized-correction confirmation PASS from body_force_review; source
fingerprint946520f7279bcc87d423cca8bb09e967a5ea2f88047b2b732ced4c8e0bc3f38a
verified before/after review and proof. No production/kernel/cognitive edits.
Existing custom engine3.3.7+guala.coupled-step.1 loaded from the previously
reviewed interval/native environment; immutable libmujoco SHA256
d3787b131b2532168dfff52c226ba07fa0de4ffc4b57bc40b7a87b73a2cc1801.
Both loaded world source and test module were verified inside this worktree.

Standalone offline unittest:4/4 PASS in0.338s; total child wall1.584983772s.
Three real-contact material variants: taste without nutrient gives zero intake;
nutrient with taste and nutrient without taste give the declared geometric
debit. Remaining material plus successive oral transfers conserves the original
quantity, including after fresh restore. Native mount and three10ms effort
intervals preserve depleted material; a fresh successor repeats the exact next
native receipt/state. Migration remains a no-op only while unmounted; mounted
topology refuses unchanged. Prepare/discard and committed rollback consume no
material. Canonical omitted zero and positive mass round-trip; malformed and
nonoral nutrient transfer refuse. No tests rerun, new build or broad pytest.

Contained proof PID16398, session2873, exit0, affinity[0,1], CPU ceiling30s,
address-space ceiling1GiB, wall ceiling45s. Network connects/sendto prohibited
inside the proof. No surviving process-group members after completion. Peak
RUSAGE_CHILDREN154220KiB includes read-only preflight children and must not be
represented as exact isolated test peak. The logical added state is still only
one nutrient integer per material and one transfer integer per contact.

Read-only AWS envelope21:39:25.458737Z ->21:39:30.183501Z:
us-east-1/tfe-web-cluster/dsf-ai-service-lb, counts1/1/0 both;
task1556 /5cb1fece1cac4f32b6d2f9b53b61b9ab RUNNING/HEALTHY unchanged;
image sha256:dc9ba00725d886110346c59ccdb36d1856d9cb316ea4f074a5bc88d9c9c794f7;
identity1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1 unchanged;
ticks2472483 ->2472498, persisted2472473 both; available true,
checkpoint_error/cleanup_error null, durability_blocked false.
Latest CloudWatch21:37 average CPU51.2469538%, max51.8305663%; memory2.6489258%.
Clock-stalled alarm was ALARM before/after; CPU/memory/storage/refusal alarms OK.
Clock alarm is unresolved external evidence, not hidden behind healthy HTTP.
Only read-only describe/list/metric/observation calls were used.

This closes the LOCAL nutrient-custody prerequisite, not FB-01aj numerical
accuracy, articulated oral mechanics, mature-world integration, biological
digestion, autonomous foraging, or live body delivery. Native anatomy and loaded
solver unchanged. The material-migration correction and G1 audit recommendations
are shared in collaborative_todo.md:23447; no overlapping main source edit.
Numerical accuracy proposal remains unratified; no timestep/force tolerances
were selected to pass these tests. Publication/Slack restrictions still apply.

### FB-01 authority revalidation after nutrient closure — 2026-09-26

Previous goal turn was PROGRESS:7715bf25e, four executed custody tests and
read-only pre/post health. Current source and clean branch revalidated; G1 main
remains4e0a64842 and has no newer coordinating ledger request. No test or build
is running; sessions2873 and16942 completed normally. This is not a worker wait.

The numerical fidelity choice recorded20:51Z and20:56Z remains unanswered,
was retained explicitly through the nutrition turn, and is unchanged now.
Safe independent nutrient integration is complete. Source confirms the joint
consumer is still not mounted: prepare_body_energy has no ordinary-loop caller;
native self feedback is exposed by the world but not consumed as the complete
anatomical port in FunctionalPhysicalLoop. This agrees with the existing FB-01g
contract, not a newly discovered cognition defect. Do not substitute passing
custody/retinal tests for the required complete motion and feedback interval.

No new numeric requirement, solver, sensory reduction, semantic motion policy,
test suite, anatomy or production action is authorized by automatic continuation.
The existing accuracy proposal remains PROPOSAL, not a derived biological law.
Same authority gap has persisted across the recorded goal turns; with the safe
independent work exhausted, request goal BLOCKED rather than loop on status,
rerun diagnostics, or fill time with another audit. Required unblock: Joe's
physical-fidelity choice for the proposed body-only verification contract.
This does not revoke the already approved numerical approximation or narrow
motor/sensory extension. It does not mark any deployment gate complete.

### FB-01aj accuracy contract RATIFIED — 2026-09-26

Joe explicitly approved use of the preceding accuracy contract: 'you have me
permission to use that contract>>>'. The goal is ACTIVE; the numerical-fidelity
authority blocker is cleared. All numeric ceilings, distinct physical measures,
event-bracket disclosures and full250ms/restart/resource requirements in the
20:56 proposal now govern verification. They are engineering requirements,
not biological facts. No need to seek that same approval again.

Requested architecture: accurate, bounded numerical body and sensory mechanics.
Current evidence: local two-contact convergence, not whole-interval qualification.
Conflict:YES with declaring accuracy passed; no conflict with continuing this
approved qualification. No kernel, cognition, anatomy, material coefficients,
contact force law, solver or production source is changed in the next slice.
Single next item: apply the ratified measures to the existing retained first
impact before paying for a full interval. Reduced rigid-body numerical mechanics;
continuous tissue microstructure and a rigorous continuum enclosure remain absent.

Authenticated archived finest comparison3.125/1.5625us: angular-coordinate
disagreement0.00018438972974027523rad (~0.010565deg) exceeds0.01deg;
geometry centres differ2.6513740806um but surface/orientation combination was
not recorded. Joint-rate difference0.3654221317rad/s lacks the corresponding
reference magnitudes. Right-pair impulse difference0.0037529872Ns lacks its
gross force-path integral. Do not pretend these missing quantities pass/fail.

Bounded diagnostic contract: extend ONLY tools/guala_body_event_resolution.py
with an explicit accuracy mode. Reuse the exact archived20ms predecessor and
unchanged two-contact2ms trial. Verify the1.5625us archived successor/work again
as the mode's instrumentation parity check; no repeat of earlier coarse maps.
Measure schedules1.5625,.78125,.390625,.1953125us in one fixed bounded batch,
plus one fresh finest repeat. No tuning in response to outputs. These are
local diagnostic resolutions, not a production timestep choice; their range
extends the existing dyadic map only to measure the ratified first-impact gate.

Retain all self-geometry surface-displacement/rotation and rate comparisons,
actual self accelerometer/gyro samples, each work/loss quantity, event times,
contact impulse with the integral of corresponding resultant force magnitude,
and local point wrenches. Match tactile points only when same anatomical surface
and the approved position bound give an unambiguous one-to-one correspondence;
otherwise label point-force evidence unresolved, never select a convenient
nearest point or flatten it into total force. No time-warping of sensory samples.
All measures remain separate; verification ratios never enter DSF or selection.
Native pair-onset brackets remain numerical-trial brackets, not exact collision
times. An endpoint comparison cannot establish the entire250ms or force history.

Existing normal mode must remain byte-equivalent apart from elapsed/resource
diagnostics. Optional instrumentation sums only actual selected substep receipts;
rejected bisection proposals never contribute accepted impulse/work. No runtime
state, sensor rounding, new anatomy, motor policy, new test suite or native build.
Frozen independent source review before execution. Offline proof process bounded
to2 CPUs/1GiB/60CPU seconds/90wall seconds; count all prefix/trial/repeat native
calls, retain exact handle and child census, and require immediate read-only AWS
health content before/after. A failed local measure is preserved; no automatic
coefficient, tolerance or further-resolution retry is authorized by this batch.

Translation preflight before freeze: LocalContact's actual members are
position_m/force_n/couple_nm in link axes. Draft qualification names incorrectly
included an extra '_link' suffix; corrected against the defining dataclass
before import/execution. Actual endpoint sensors and local point wrenches are
retained in each bounded diagnostic row for audit, not only pass Booleans.
Native state, contact solver and the ordinary diagnostic path remain untouched.

Frozen source review68d3382d7f9c54f2ada29e132cf62226049d88e451ba4dc1e6fe7054b301cfeb
completed unchanged before/after. One LOCALIZED evidence finding: measure_limit
kept only the worst comparison, preventing audit of each primitive/channel.
Corrected in one batch: every label now retains its disagreement, allowance,
ratio, pass result and, for relative limits, the finer-reference magnitude.
Native observations, mechanics, schedules and accepted limits are unchanged.
Removed unused couple-impulse allowance calculation; that diagnostic still has
no invented pass criterion. Independent review found no other defect, confirmed
observer parity and selected-only accumulation; complete native-call ceiling30800.
Single next action: final frozen source confirmation, then one bounded offline
accuracy batch with live read-only pre/post health. No production changes.

### FB-01aj ratified first-impact measurement — 2026-09-26 22:10Z

Final independent source confirmation PASSED, frozen fingerprint
6ee49704d478ae447a9cfaf60f8cd51cc91d92bc48abf78e6db9275fd38905e3.
Native library unchanged:d3787b131b2532168dfff52c226ba07fa0de4ffc4b57bc40b7a87b73a2cc1801.
Four fixed schedules and finest fresh repeat completed. Archived1.5625us control
and complete finest successor/repeat match exactly.30632native calls <=30800.
Retained once in docs/evidence/FB-01aj-ratified-accuracy.json; decoded raw207922B,
SHA7acb987a237e15c49b55cbb44f8195b0ee3c88a592c59ca8dd287dfeba462f97.

Finest comparison0.390625/0.1953125us: surface bound0.843587um <=100um;
rotation0.00159727deg <=0.01deg; every measured linear/angular/joint rate,
gyro, work/bearing quantity, resultant impulse and onset-time comparison passes.
Unqualified measures are NOT silently included among passes.
FAIL: left-palm point force disagreement1.680884N >0.7482499N allowance (2.2464x).
FAIL: left-foot specific-force disagreement0.5658626m/s2 >0.1693049m/s2
allowance (3.3423x). These are the largest normalized discrepancies, not
necessarily the largest raw values. All per-channel comparisons and actual
endpoint sensory/contact samples remain in the artifact. Tactile correspondence
is complete and unambiguous for both endpoint points. Couple impulse has no
separate ratified ceiling and stays unqualified. First-order-like reduction
across this fixed map is observed, not a continuum error certificate.

This is a necessary2ms endpoint/contact-window check, NOT a full250ms or gravity
proof. Surface/rotation/work success does not excuse force/specific-force failure.
No runtime timestep, tolerances, contact coefficients, anatomy, DSF or cognition
were altered. Do not launch further blanket timestep refinements or a broad
suite in response; next bounded analysis is the existing contact-integration
boundary that produces these two failed observables.

Execution: session83295, child36566, exit0, wall8.208585s, CPU8.079603s,
peak145372KiB,2CPU affinity,1GiB address bound,60CPU/90wall ceilings. No child
or process-group survivor. Source fingerprint/native binary verified unchanged
after execution, before adding this immutable evidence.

Capture defect disclosed: initial identical batch(session24979/child34687,
exit0,6.988975wall/6.895587CPU seconds) completed, but its wrapper expected an
unpacked schema although existing encode() produces packed JSON. Fallback
printing exceeded tool output and truncated raw evidence. No physical failure
was inferred. One identical batch was repeated with envelope SHA/size validation
and direct apply_patch retention; no source/limits/schedules changed. Its
complete evidence is above; the damaged first artifact is not claimed usable.
Recurrence: inspect the existing encode contract and decode/validate its envelope
before schema selection; never fallback-print bulky proof stdout. No test
framework or production code was added to solve this reporting defect.

Read-only production envelope22:09:53.520413Z->22:10:05.712107Z:
task1556/5cb1fece1cac4f32b6d2f9b53b61b9ab, same immutable image
dc9ba00725d886110346c59ccdb36d1856d9cb316ea4f074a5bc88d9c9c794f7;
counts1/1/0, RUNNING/HEALTHY, same identity1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1,
ticks2478372->2478411, persisted2478361->2478393, available true, checkpoint/
cleanup errors null, durability false. CPU22:08mean51.168866%/max51.664530%,
memory2.648926%; clock-stalled ALARM persists, other four alarms OK.
No live write, deploy, feeding, restart or cognitive source mutation.
Joe reiterated no overengineering: reuse the existing diagnostic and narrow
failed seam; no new subsystem, framework or scope expansion. Goal remains active.

### FB-01aj midpoint correction contract — 2026-09-26

Continue the same contact-accuracy defect, not a new body/cognition project.
The existing endpoint mj_forward recomputes physical force and accelerometers;
the failing convergence is not stale sensor transport. First-order integration
is the current source cause. No new material constants, anatomy or tolerances.

Owner A1; authorized delta: coupled_step.patch, interval.pyx, native adapter
engine/ABI identity, and one bounded offline equation/accuracy witness. Builder
continues using the existing pinned upstream plus the same two patch files.
No changes to G1 source or production. Preserve archived first-order evidence.

One midpoint law: vm=v0+h*a/2; qm=IntegratePos(q0,vm,h/2); rebuild native
position/contact/inertia/reference/velocity/actuation at that same stage.
Retain the actual physical smooth force and evaluate the native constraint law
at jar=Jm*a-arefm. Accept ONLY if norm(Mm*a-Fphysical-Jm.T*lambda) divided by
meaninertia*max(1,nv) meets the existing positive finite native tolerance.
The native Newton small-cost-improvement exit is not outer convergence.
If not converged, use the existing shifted Newton operator with shift=h*B/2
and smooth RHS corrected by B*(vm-v0) to propose the next acceleration.
This yields the physical equation Mm*a=Fnonbearing-B*vm+Jm.T*lambda at
convergence. No extra contact solver or contact law. Zero constraints means
zero constraint force. Nonfinite stage/residual or opt.iterations exhaustion
refuses. Outer and inner bounds multiply; record cost rather than claiming
the predecessor's work count. Second order in smooth regimes is not a
discontinuity or continuum-error certificate.

On convergence retain matching midpoint forces, restore q0/v0/time0, and
advance once with accepted a and explicit vm. mj_step and mj_step1/mj_step2
must use the same law; direct split implicitfast remains rejected. A new engine
version and compiled interval ABI reject old integration envelopes/old heat
accounting; there is no implicit live migration. State bytes remain caller-owned.
Errors may leave native scratch invalid; NativeBody publishes no successor,
and its next call restores authenticated predecessor bytes. No warmstart or
extra persistent state is added. Endpoint observation remains mj_forward.

Constant-effort signed work is h*tau.vm. Bearing loss is h*vm.T*B*vm, not
the old trapezoidal endpoint loss (which adds h*delta_v.T*B*delta_v/4).
Positive/braking motor work retains endpoint split accounting as a separately
declared supply bound; no extra thermal energy is invented from quadrature.
Joint stops/soft contacts still have unresolved energetic exchange, reported
explicitly rather than called tissue heat. Existing native geometry/supply
guards and cold body/world transaction boundaries are unchanged.

Independent source/math review confirmed the residual and midpoint equations;
no executable change was reviewed or run yet. Freeze one implementation,
source-only review, one localized correction batch, then bounded native build
and analytical equation/caller/refusal proof. Only after that passes, reuse
the existing per-channel accuracy observer on the common impact. Whole250ms,
gravity, mature-world and production qualification remain OPEN. Do not run
broad tests or repeat the closed first-order diagnostic.

Read-only lookup mistakes this slice: nonexistent functional_body_model.py,
guala_body_discrete_work.py, native/functional_body/build_interval.py, and
worktree scripts directory were queried. Correct existing builder is build.py;
skill scripts require their actual skill directory. No execution/state damage.
An attempted whole sprint-ledger read exceeded its output budget; discarded,
using the already-known tail rather than rereading a large closed history.
These are tooling mistakes, not physics failures; verify paths before access.

### FB-01aj rejected candidate and exact heat-boundary correction

Frozen129369969b2066c6569a039e4a826d8639c286037235f605330317527c3ad3a8
was ARCHITECTURALLY REJECTED before any compile/test. Native stage, residual,
step1/step2 and scratch custody review found no additional defect. The contract
incorrectly treated motor_braking_work_j as a conservative supply quadrature:
thermally_coupled_embodiment_world.prepare_port_command already deposits this
field together with self_bearing_dissipation_j as native internal heat. At a
within-step power sign reversal, the old endpoint split overstates midpoint
braking and would feed extra heat. This is a missed existing consumer, not a
reason to invent a second heat authority or loosen conservation.

Rejected diff (including new proof) retained once as
docs/evidence/FB-01aj-midpoint-rejected.patch. All three executable source files
restored exactly to ce83797a3; new proof removed, recoverable in that diff.
No native build or test was run on the rejected candidate.

Corrected contract supersedes ONLY the prior positive/braking paragraph:
for each actuator p_mid=tau*(v0+v1)/2, signed work=h*sum(p_mid), positive
work=h*sum(max(p_mid,0)), braking loss=h*sum(max(-p_mid,0)). All work and
bearing loss use the same midpoint quadrature as the discrete motion. This is
body numerical approximation, not a certified integral across unresolved
continuous sign changes. Existing per-work accuracy limits still apply.
The existing reserve and thermal callers remain unchanged: positive work debits
supply; measured self-bearing plus measured braking enters the heat receipt,
with the existing single bounded nanojoule rounding. Neither diagnostic bounds
nor error estimates enter heat, reserve or cognition. Add one sign-reversal
control and verify the existing mounted heat-receipt boundary before claiming
this closure. Retain the approved source residual/caller contract unchanged.

Additional read-only path mistakes: deploy and functional_body_world.py do not
exist in this tree; actual world/heat callers are embodiment_world.py and
thermally_coupled_embodiment_world.py. Existing ABI1/predecessor equivalence
tests explicitly target the former numerical law; they are not passing evidence
for ABI2. Do not launch that heavy suite to rediscover known law differences.

Corrected8e39741012408b810ffaa6d6c0f770a1edf8b466fd7b88d778beb124b9af7d12
source review found the work/heat architecture sound. Two LOCALIZED findings
batched before any build: the single-joint calorimetry fixture needed its
physical self-surface name for the existing sensory-membership guard; the
MechanicalSuccessor comment still called the new work rule trapezoidal.
Named the actual surface and corrected the comment. No other native-law edit,
new guard, constraint relaxation or fixture bypass. Final frozen confirmation
precedes one bounded build and focused equation/caller/heat proof.

### FB-01aj first native build and profiling-boundary refusal

Final source review c06830bf2bd313ba2b26606d28b6170b9aa5141e9afc34c75879143c9d0bf298
PASSED. Build succeeded in62.315s; interval compilation2.286s. The focused
proof then refused on its first scalar call, before body advancement. Exact
cause: upstream Python MjDataWrapper installs mjcb_time=GetTime automatically
(structs_wrappers.cc:568-574). The new native callback prohibition incorrectly
classified that ordinary profiling clock as a force/control callback. Python's
existing no-user-callback guard correctly reports no installed user callback.

One localized platform-boundary correction: remove only mjcb_time from the
native physical-callback prohibition. Do not clear or override the installed
clock. All force, actuation, sensory and contact callbacks remain refused;
Python's user-callback prohibition remains untouched. Numerical equations,
models, tolerances, heat, persistence and proof assertions remain unchanged.
Reuse the fresh compiled build and recompile only the changed native object;
do not clone/rebuild all dependencies or launch another test suite.

Receipt retained docs/evidence/FB-01aj-midpoint-equations.json. Session97785,
owned PID62133, exit1,66.827wall seconds, no survivor. Build directory
/tmp/guala-body-midpoint.igj32n8c. Failed native library SHA
b7f9b4a5bd9dddf881bf3d8e66dbd21c2724004f1d6ff7fc976fb6fb84f77c61;
compiled ABI2 SHAa137418386a8288ac9e99324f0f7176674d14c0eb4b66d47ddc4104e589f2caf.
Pre/post AWS22:48:21Z->22:49:31Z retained task1556, counts1/1/0,
same organism and image; ticks2485829->2486054, no checkpoint/cleanup error,
no durability block. CPU~51.2%, RAM2.65%; existing clock-stalled ALARM remains.
No production write. Build preflight also located the already-installed Cython
at /tmp/guala-body-interval.Hdyavt/build-deps after rejecting two wrong paths;
no dependency reinstall or compilation occurred before that correction.


### FB-01aj actual outer contact-cycle cause and bounded globalization

Previous goal turn classified PROGRESS: new compilation/refusal evidence and
the requested AUT-01 audit changed the next action; no body test was running
during that audit. Continue FB-01aj, not upstream cognition or food finding.

Timer-only corrected candidate63763f7d built successfully in30.522s but its
first dense/no-island negative-force scalar control refused convergence.
Session70956/PID68583 terminated, no survivor. Retained immutable receipt
FB-01aj-midpoint-equations-timer-corrected.json; native SHA
92a3437b373d0d1107b277a93a8357d1441db4705fe4d32df961bc929743d566.
No later control/body/heat case ran; no equation-pass claim.

One source-reviewed scalar scratch diagnostic(session70251/PID77087) now
isolates the cause, retained in FB-01aj-midpoint-stall.json. No build, model
change, tolerance change or second physical interval. Inner shifted residual
1.0520552e-16 is below1e-10; the reconstructed actual midpoint residual is
149.9464473. The previous inner-small-improvement hypothesis is falsified in
this case. The native frozen-stage proposal crosses q_mid=0, alternately
creating/removing the joint-limit row and changing its reference force.
Last stage a=(-1,0,.999995,.0248125,-.5248099); proposal
(.049625,-1.0496197,.999995,-.5,0). Both accurately solve their respective
frozen subproblems, not the complete stage equation. Initial q/v/time/warmstart
restore is byte-exact on refusal. Diagnostic5.16ms, whole child.533s,
143864KiB peak, no survivor. Do not rerun this diagnostic to rediscover it.

Read-only AWS23:09:09Z->23:09:12Z retained task1556, one healthy running task,
same image/identity, ticks2489810->2489819, checkpoint/cleanup null,
durability false. CPU51.49%avg/52.02%max, RAM2.648926%; existing clock-stalled
ALARM remains. No live write. A resumed read used a guessed nonexistent
PRECURSOR_SPRINT filename; actual ledger resolved from git status. Future
reads use this exact tracked path; no new parallel ledger was created.

Correction is confined to the numerical iteration of the already-ratified
midpoint equation. Source reviewer independently recommends deterministic
residual backtracking, not altered contact physics or another contact solver:
retain accepted acceleration and its actual residual; compute the existing
shifted native Newton proposal; try its direction at alpha1,1/2,1/4,...,
rebuilding complete geometry/contact/inertia/reference/force every time.
Accept a numerical iterate only on strict actual-residual decrease or existing
tolerance satisfaction. ONLY tolerance satisfaction permits mj_advance.
Binary subdivision is numerical search, not physical damping or a fitted
coefficient. No residual, diagnostic bound or rejected stage becomes heat.

Use existing opt.iterations for proposal count and opt.ls_iterations for
backtracking count. The corrected bound is1+iterations*ls_iterations physical
stage evaluations, plus at most iterations native Newton proposals (each
already bounded by iterations per reached island). Retain no extra persistent
state: two temporary nv-vectors hold trial/direction. Nonfinite values,
unrepresentable motion, no improving trial or exhausted bounds refuse with no
successor. This is not a universal convergence proof; no descent means explicit
failure, never relaxed acceptance or fallback dynamics.

Authorized delta: existing coupled_step.patch numerical loop and its existing
equation proof (invalid line-search bound and truthful work-count metadata).
Same midpoint work/thermal law, caller paths, numerical limits, body anatomy,
engine/ABI candidate identity, integration schema, DSF and cognition unchanged.
Existing small analytical controls, split/cold/refusal and heat-custody witness
remain the exit proof; run them once after frozen source review. Only after
they pass may the original per-channel impact accuracy test advance.
Full250ms, gravity, mature-world and production qualification remain OPEN.

### FB-01aj midpoint equation proof passed; unchanged impact acceptance next

Frozen a659d78cea99dd52d4b6c6aaa66a2e14268077f4c172fda195e910d0f45b3f8e
passed independent source-only review. Incremental native build and focused
proof completed in session37991/PID83929, exit0,31.708wall seconds, no survivor.
Eight analytical controls, four refusal cases, fresh cold continuation and
work/heat reversal passed. Proof itself1.091166s; aggregate build/proof child
CPU59.056309s (two parallel compiler processes, not a45s aggregate claim);
peak150724KiB. Evidence: FB-01aj-midpoint-equations-backtracking.json.
Native SHAde96a1766223905d26b1df0e68ce7bc97608cf2c6238acef8dcf8b344a3fd48f.
ABI2 SHAa137418386a8288ac9e99324f0f7176674d14c0eb4b66d47ddc4104e589f2caf.
Body signed work.0002480251495884925J; bearing2.3448356969093268e-7J;
unresolved exchange5.355779288632913e-11J. Reversal heat0nJ is actual
midpoint braking, not the rejected endpoint positive-work bound. State5152
bytes, fresh thermal/world continuation exact; old-law restore refused.

Read-only AWS23:19:39Z->23:20:15Z: task1556 unchanged, counts1/1/0,
same identity, ticks2491849->2491966, checkpoint/cleanup null, durabilityfalse.
CPU~51.12%, RAM2.66%. Existing clock-stalled ALARM remains; not resolved here.
No production writes. Duplicate Delete/Add apply_patch was refused without
writes; full-file Update hunk succeeded. Do not repeat duplicate target patches.
A resumed rg included guessed guala_body_coupled_motion.py (absent); actual
motion capture is motion_prefix in guala_body_coupled_step.py. No rerun needed.

Next is the ORIGINAL2ms two-contact accuracy comparison, same anatomical model,
material law and ratified per-channel limits. Extend only the existing offline
event-resolution observer with a midpoint mode. A separately pinned accepted
first-order process regenerates the archived20ms predecessor once (800steps),
checks archived pose/rate, and transports raw integration bytes through a
bounded pipe. Candidate verifies the FULL existing predecessor hash
1724754864379da92fea0d65cdee9798f4116ba413ca04e7f9c739804aa60ee1,
unchanged XMLhash and retained supply. No serialized runtime-header rewriting;
this is an explicitly cross-law numerical initial-condition comparison, not
cold migration or live body replacement.

Reuse four existing resolutions1.5625/.78125/.390625/.1953125us and one finest
repeat. Native midpoint version/ABI and source/library hashes are required.
Do not require new-law successors to match the rejected first-order trajectory;
archive matching remains unchanged in the old mode. Every accuracy ceiling,
contact-point correspondence rule, sample/work path and event bracket stays
unchanged. Capture failures too; first refusal terminates this batch. No broad
suite, rebuild, new material parameter or runtime timestep policy. Per-process
CPU60s,1GiB address-space,2CPU affinity,90s wall; retain exact handles and
post-run census plus read-only AWS envelope. Native numerical iterations remain
bounded by the already-reviewed current solver. Scope remains local numerical
resolution evidence; full250ms/gravity/mature/production are still OPEN.

### FB-01aj midpoint local impact comparison PASSED (not global closure)

Frozen observer274b334afa09183f101223eb3ca9c3bb186ff5e7f34718fa13f407ccdfb92651
passed independent source-only review. Session85741 completed exit0, with
old-input producerPID92000 (800steps,.809532CPU/1.15135wall seconds) and
candidatePID92010 (29829native calls,12.286127CPU/12.29226wall seconds),
no survivors. Evidence FB-01aj-midpoint-impact-accuracy.json preserves exact
old input, both native identities, all channels and pre/post read-only AWS.
No rebuild. All three paired-resolution comparisons pass all ratified local
limits; finest fresh repeat is exact. At.390625 vs.1953125us, worst tactile
force disagreement.000702853N vs.749928N allowed (old first-order1.680884N
failed); left-foot specific-force disagreement.000252662m/s2 vs.169868m/s2
allowed (old.565863 failed). These are numerical-resolution disagreements,
not continuum error enclosures. Other position/rate/work/impulse/onset limits
passed. Separate couple-impulse requirement remains unqualified as before.
Full250ms/gravity/load/mature integration/production acceptance remain OPEN.

AWS23:30:32Z->23:30:48Z remained same task1556/image/identity,counts1/1/0;
ticks2493980->2494032, checkpoint/cleanup null, durabilityfalse; CPU~51.15%,
RAM2.648926%. Existing clock-stalled ALARM remains. No production writes.
Other Python processes85505/85641/86277 belonged to G1's main worktree and
were not signalled. New user receipt6d2fdea61 interrupted after this bounded
proof launched. Completed the source-only AUT34 review and recorded it in
shared ledger23:34Z; no further body test/build started during that audit.
Next body exit item is the existing longer load/release/gravity accuracy and
bounded cost qualification, not repetition of the now-passing local impact.

### FB-01aj longer-interval feasibility and cost gate

Previous goal turn PROGRESS: local impact evidence passed; AUT34 audit delivered.
Reviewed midpoint implementation/evidence committed locallyea9b82054; no push or
deployment. ContinueFB-01aj; short impact and analytical controls stay closed.

Requested: bounded articulated mechanics with truthful sensory return over the
whole250ms command. Current reality: midpoint local impact meets ratified
limits, but longer loaded motion and end-to-end cost remain unproved. Conflict:
YES with completion claims, not with this bounded next test. No cognition,
L0-L4, body anatomy/material, runtime solver, optical policy or production edit.
Single next item: establish longer loaded motion feasibility BEFORE expensive
whole-history/gravity verification. Reduced numerical rigid-body mechanics;
no micro-tissue model or full DSF evaluation.

Extend ONLY existing tools/guala_body_midpoint.py with motion-intervals mode.
Reuse authenticated existing complete biped and maximum torso load at fixed
100/50/25us, each250ms load followed by250ms effort release. Unchanged existing
200us contact response and.999 impedance. This is the existing zero-gravity
bench, not a new world or gravity proof. Three independent rates form one fixed
regime map; no rate/tolerance/material retry in response to results. Stop each
case at its first refusal and retain exact unpublished failure input. Fresh
native instance repeats each successful phase from its authentic same-law
predecessor; compare complete receipt/state. No failed numerical state is
published or transplanted into world custody.

Measure uninstrumented ordinary advance time separately from cold repeat;
actual endpoint pose, rates, contacts, sensors, work/bearing/braking, unresolved
exchange and remaining physical supply. Release must have zero motor work.
Retain native-call ceiling70000 across all three rates/load/release/repeats,
unchanged5152-byte-state requirement, exact input/model/source/library hashes.
Passing this scan is NOT instantaneous-force/history/gravity/global accuracy
or production performance; it decides the next required full-body check.
Per-process60CPU/90wall seconds,1GiB and2CPU affinity; read-onlyAWS before/after,
owned handles and survivor census. No build, broad regression or G1 source edit.
Source-only frozen review before execution per skill. Budget exhaustion is
retained failure evidence, never an excuse to loosen physics.

Frozen73b9775079 source review found one LOCALIZED diagnostic failure-capture
gap, no architecture findings. The initial draft retained only ordinary-stage
scratch; a release/cold mismatch lacked its exact phase predecessor and failed
stage. One correction batch records original phase state/hash, complete command
and supply, ordinary/cold/comparison stage, available complete result evidence,
and appropriate unpublished raw scratch; numerical time uses repr so NaN cannot
erase the original exception. All three execution stages share this catch.
Successful physics, immutable predecessor, work debit, rates and limits remain
unchanged. This is proof evidence only, not runtime error recovery or retry.

### FB-01aj longer motion failure retained; single-step diagnosis

Frozen77aa565730 source review passed. Session25223/PID2168 exited0 (diagnostic
completed, NOT physical qualification). All three rates failed the first load
interval at native times100us:.0016s,50us:.00165s,25us:.001625s, with
"midpointStep: coupled body midpoint residual did not converge; no successor".
Release and cold repetition were never reached. Aggregate1.039852CPU,
1.048926wall seconds; max144000KiB; no survivors. Evidence
FB-01aj-midpoint-full-interval.json includes complete unpublished scratch and
phase predecessor. No failed body was published. AWS23:44:22Z->23:44:26Z same
task1556/image/identity,counts1/1/0,ticks2496689->2496699; checkpoint/cleanup
null,durabilityfalse. Existing clock-stalled ALARM remains. No production write.

Continue SAME accuracy item. Do not rerun whole interval or short-impact proof,
raise iteration/tolerance limits, change material or build a candidate yet.
Bounded diagnosis in existing tools/guala_body_midpoint.py (--stalled-step)
authenticates one saved100us failed-step state, replays that single native step,
checks no successor, and independently reconstructs the native midpoint residual
using the SAME native position/velocity/actuation/smooth-force/constraint laws.
Require bit-exact residual reproduction before interpreting the observer.
Capture proposal/position call counts, terminal constraints and residual.
Two predeclared central-difference spacings (cuberoot(machine epsilon) times
coordinate scale, and half) measure the local residual Jacobian and eight binary
fractions of its Newton direction. These are offline sensitivity measurements,
NOT a new solver, material coefficient, relaxation or acceptance threshold.
Bound: one existing native step plus2+4*nv+16 residual evaluations;2CPU,1GiB,
60CPU/90wall seconds; frozen source review then one run with AWS envelope.
No field/cognition/world/production source change or geometry simplification.

Frozenfd228d6e source review found one LOCALIZED evidence issue: singular or
nonfinite sensitivity could make JSON encoding discard the earlier native
rollback/residual measurement. One correction batch streams that baseline
first, captures sensitivity stage/coordinate/alpha on error, checks finite
Jacobian/direction/trial norms, and represents infinite conditioning explicitly
as null plus status. No physics or loop bound changed. A prior ledger append
missed its exact context line and made no write; corrected against actual line.

### FB-01aj saved-step cause localized — 2026-09-27 00:00Z

Frozened296a304171297d2db6fbf14add081b150c73aab61fd0fe0af7a7d57afcfa3a
passed final source review. Session62023/PID11428 completed exit0,0.572184wall,
0.566817aggregateCPU seconds,143644KiB peak; no survivors. Evidence
FB-01aj-midpoint-single-stall.json. One failed100us step only, NOT a trajectory
rerun or build. Native inputSHA073eda5a5809a9d58d1bebdfdbb9eb369eac72aba201409b71c46d7579a7b5fb
restored exactly; refusal left complete integration state unchanged.
Public native stage functions reproduced the terminal residual BIT-EXACTLY.

Measured:70DOF,29 frozen-stage proposals,703 position evaluations, final inner
Newton1iteration. Normalized residual decreases .0168902476744 to
.00173488174605, then cannot reach original1e-10 threshold. Terminal joint-limit
row37 is at signed gap-1.3552527156068805e-20rad with reference acceleration
5055.46675015504rad/s2 and positive reaction .06781645935731388Nm.
Other rows28/39/42/46 remain recorded. This is NOT a mere near-tolerance
roundoff stall or proof that more iterations would solve it.

Source cause boundary: engine_core_constraint.c:728 instantiates a hinge row
only at gap<=margin; :2224 gives a_ref=-B*v-K*I*(gap-margin). At zero gap with
incoming velocity, this damping reference is finite. The row disappears just
outside the limit. Thus the midpoint algebra encounters a discontinuous force
activation, not only the smooth bearing/contact equation used by the earlier
scalar control. Binary backtracking of a frozen-stage proposal cannot guarantee
a root or descent across that boundary. Prior short-impact proof remains valid
for its measured state, NOT this different boundary.

Independent offline central-difference Jacobians at two declared resolutions
have condition~3.3692e8 and nearly identical trial residuals. A1/16 Newton
fraction reduces residual to7.78868e-6; full direction increases it to.00710157.
This demonstrates a better local direction exists, but does NOT establish a
converged root, continuous solution, certified error or a runtime solver fix.
Do not promote that diagnostic Jacobian, relax tolerance, add damping, or
declare convergence from reduction alone.

AWS23:58:14Z->23:58:17Z unchanged sole task1556/image/identity,counts1/1/0,
ticks2499402->2499411; errorsnull,durabilityfalse. CPU51.131064%,RAM2.661133%.
Clock-stalled ALARM persists. No live writes. Publication/Slack restrictions
remain unchanged and were not retried.

Single next numerical solution item: resolve the first actual joint-limit onset
in time, using the existing signed joint-gap geometry and SAME constitutive law,
before asking one midpoint equation to span both inactive and active regimes.
First qualify this on the SAME saved failed100us interval only; preserve exact
total elapsed time, all generalized forces, signed work, positive work, bearing
loss, motor braking, contact sensory return and original tolerances. Numerical
event trials are disposable scratch, never lived actions or heat. Require a
bounded crossing bracket and one-sided force evidence under the ratified1us
event contract; no universal collision-policy claim. The previous two-contact
event witness is reference machinery, not permission to run a broad replay.
Complete this source-derived event contract before any new solver edit/build.
General250ms/load/release/gravity/body mounting/production remain OPEN.

### FB-01aj joint-limit onset contract — 2026-09-27 00:10Z

Previous body goal turn PROGRESS: committed696fa5c50 with one saved-step cause;
user-requested2af57ce60 audit completed separately in shared ledger00:06Z.
Body tree is clean on a1/guala-functional-body; no body process survives.
ContinueFB-01aj, not reopening local impact, exact work custody or cognition.
Requested: bounded articulated motion with truthful sensation. Current reality:
one100us full-load step refuses at a joint-limit activation discontinuity.
Conflict:YES with full-body qualification. Exclusions: all physical coefficients,
anatomy, cognitive/kernel laws, tolerances, actor/world sources and production.
Reduced numerical mechanical trial only; no microscopic biology/fullDSF claim.

Single next artifact extends existing tools/guala_body_midpoint.py with
--limit-event. No native rebuild, solver replacement or production timestep
policy. Extract its existing authenticated failed-input reader once and reuse
it; closed stalled-step behavior/evidence is not rerun.

Use the same recorded100us input, original command/supply and unchanged native
midpoint/ABI2 law. Target joint37 comes from the retained failure, not a runtime
behavior/selection table. Derive its signed lower/upper gap and gap velocity
from native jnt_range, margin, qpos and qvel. Require an initially positive,
closing gap. Every trial restores identical complete integration state and
uses the existing compiled one-step interval function and original safety/work
checks. Trials may change numerical h only; rejected trials consume no lived
time, work or heat. Only the known residual-convergence refusal may bound the
numerical search, and rollback must remain byte-exact; other failures stop.

First find a SUCCESSFUL crossing-side endpoint by bisection between the initial
time and the known failed end (max53 trials). A failed trial is an unresolved
numerical upper time bound, NEVER evidence of a negative gap. Positive-gap
successful trials raise the lower time; only a measured nonpositive gap
establishes a crossing bracket. Then bisect successful one-step trial endpoints
until the bracket is<=1us,.5us,.25us in three independent predeclared cases.
At most53 further trial calls per case; preserve exact low/high signs/times.
This brackets the numerical trial-flow onset, not a continuous exact impact.
Reject unexpected additional new joint rows for this single-onset witness.

Accept the crossing-side state/work ONCE and execute the remaining original
100us duration from it under the SAME native law. Original end time must be
exactly reached; no coordinate clamping, time warp or synthetic force. Capture
both bracket-side instantaneous native constraint/sensor evidence, all separate
positive/signed/braking/bearing work, remaining supply, full endpoint observation
and integration bytes. No intermediate state is published to body/world custody.
Fresh native model/data repeats each successful case exactly; failure retains
stage, last attempted dt, bracket, primary scratch and original input reference.
Max6*(53+53+1)=642 native steps, twoCPU,1GiB,60CPU/90wall seconds; no whole-body
history/replay. Stream each case before the next so failure cannot erase evidence.
Read-only AWS before/after plus owned-process cleanup. Frozen source-only review
before execution. This is local onset feasibility/cold/work evidence; it cannot
close whole250ms/gravity/sensory accuracy, real-time cost or production acceptance.

Source preflight correction before implementation: the saved failure contains
the complete mechanical state at1.6ms but its available_work_j is the whole
uncompleted250ms call's input, not the remaining allowance at that inner step.
Recover that missing budget ONCE via the already-successful16*100us prefix
from the archived phase predecessor and original command. Require byte-exact
integration payload equality with the saved failure before using the resulting
positive-work debit; otherwise stop. Reuse that authenticated same-law prefix
successor in every onset/cold case. Additional bound16 native steps (total658),
not a full interval rerun. No energy refill or inferred heat. Fresh repeats use
the resulting current-law body header, not an old-law identity transplant.

### FB-01aj onset diagnostic review correction — 2026-09-27

Previous goal work is PROGRESS: bounded diagnostic source and saved failure
are present; intervening user audit completed without organism execution.
Revalidated tree/HEAD696fa5c50 and frozen de01c2a0 before source review.
Reviewer body_force_review found two LOCALIZED evidence defects, not a new
settlement law: signed-zero differences escaped array equality; remainder
failure omitted completed bracket state/work and lacked an explicit native
rollback record outside the search branch. Execution remained withheld.

One correction batch: compare canonical little-endian float64 bytes for the
saved input, prefix reproduction, trial restore, snapshots and native refusal;
retain current completed lower/upper trial states with work, one-sided observed
forces/sensors when available, remaining supply, completed remainder and combined
work on any later failure, all explicitly UNPUBLISHED. Native FatalError at any
trial stage records exact primary rollback before propagation. Known refusal
still cannot count as a measured negative gap. No new physical coefficient,
model, tolerance, native solver, control, or extra numerical step is introduced.
Bound remains658 native calls. Failed attempts remain scratch, not lived work.

Instruction preflight record: attempted an incorrect bundled reference name
embodiment-law.md; actual SKILL names embodiment-ui-law.md. Read the latter and
world-environment-catalog.md completely; do not retry the nonexistent path.
Authority-root helper's historical required documents remain absent in this
branch as previously recorded; explicit git root/branch/HEAD and this ratified
sprint remain the active-body source identity. G1's independent witness changes
are confined to main guala-live and do not enter this body candidate.

### FB-01aj onset diagnostic execution — 2026-09-27 00:26Z

Final source-only review PASS, fingerprint1b462365de8d0367b84741e463635cf852e4a6b1fee0a20c0e4b0b3363229aa7.
Executed ONCE in session49343, owned child28465; exit0 means diagnostic
completed, NOT mechanics passed. Child0.737566s wall/0.725154s aggregateCPU,
143516KiB maxRSS, no timeout, no surviving process. TwoCPU/1GiB bounds held.
Evidence docs/evidence/FB-01aj-midpoint-limit-event.json SHA
f97ffdfb1d130387703beb3e92b701c8bd8de7f097bf8557751336f328332923.

The16-step successful prefix reproduces the saved primary integration BYTES
exactly. Measured debit0.06292443959864111J, remaining supply4674.886075560401J,
successor SHAe8c6b7455e832fe49bff52f162249e10911142759320b445c8ca4a8a3d72bd97.
No energy refill. Three declared widths1/.5/.25us each refuse at their fourth
trial, BEFORE the requested bracket width, so no remainder/cold-repeat claim.
Total native calls28 (16+3*4), below658 ceiling. All repeated widths retained
same first failure; do NOT repeat or tune the widths.

Joint37 starts at gap2.5252056417024415e-5rad, closing-.655329610371183rad/s.
Successful lower endpoint1.637500ms has gap4.3447160902912826e-8rad;
upper1.650000ms has gap-8.54360627997905e-6rad. Bracket12.5us is too wide.
Intermediate43.75us trial to1.643750ms refuses same native residual law.
Primary rollback byte-exact=True. Lower/upper integration bytes, positive/signed/
braking/bearing work, original allowance and failed-trial predecessor persist
as unpublished evidence. No boundary force/sensor, completed100us successor,
accuracy or production qualification is inferred.

### FB-01aj earlier-refusal observation contract — 2026-09-27

Continue the same unresolved joint-limit numerical seam from local commit
014ff0e32. Add only an authenticated reader of the saved43.75us refusal and a
CLI selector invoking the existing, verified native residual/sensitivity
observer. Reuse saved_motion_refusal solely to authenticate identical full
integration bytes and model, not to advance or repeat the16-step prefix.
Require receipt SHA, decompressed payload SHA/size, failed stage/width,
recorded exact rollback, identical original precursor, and captured start/dt/end.
Restore the same state and numerical dt before the SINGLE native failed step.
Return the original observer's constraints/aref/force/position, normalized
residual, exact observer reproduction, bounded diagnostic sensitivity and
streamed baseline. All physics and convergence tolerances remain unchanged.
Neither an observed row nor sensitivity direction is promoted to runtime.

Only tools/guala_body_midpoint.py changes. New --event-stall branch selects the
new archive reader; default --stalled-step remains the existing input path.
Strengthen its primary rollback comparison to canonical bytes for both modes.
One native step plus existing2+4*nv+16 residual-evaluation ceiling, same
twoCPU/1GiB/60CPU/90wall wrapper and read-only AWS envelope. Existing failures
and accepted first-event trial evidence are never overwritten or rerun.
This diagnostic answers only the actual earlier refusal row/cause and cannot
claim numerical integration accuracy, full interval, body deployment or cognition.


AWS00:26:40.804943Z->00:26:43.972832Z: sole task1556
5cb1fece1cac4f32b6d2f9b53b61b9ab,image dc9ba00725d886110346c59ccdb36d1856d9cb316ea4f074a5bc88d9c9c794f7,
identity1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1,counts1/1/0,
ticks2504875->2504885,persisted2504857; errorsnull,durabilityfalse.
CPU51.236988->51.145842%,RAM2.661133%. Existing clock-stalled ALARM persists;
other4alarmsOK. No production writes. Pre-census saw unrelated git processes
and this read-only census, no competing body run; unrelated processes untouched.

A receipt-inspection shell heredoc mistakenly used a mismatched closing marker,
so Python parsed shell text and refused with SyntaxError before execution.
Corrected the marker and decoded the existing receipt read-only; no harness
was rerun. Retain this tooling failure, not a physical failure.

Single next causal question: which native constraint row prevents the earlier
43.75us trial from converging? The original100us diagnosis identified joint37;
that does NOT prove joint37 is the first event or the row at this new failure.
Inspect/replay ONLY the newly saved failed step with the already verified
native-residual observer, using its captured exact predecessor and dt.
No full prefix/history repetition, broader trajectory or speculative limit-law
change. Preserve existing law/tolerance and authenticate all input evidence.
Only then derive the complete event ordering or solver correction from the
observed cause. General250ms/gravity/body mounting/restart/production remain OPEN.

### FB-01aj next observer approved; external health gate refused launch — 2026-09-27 00:32Z

Source reviewer PASS fingerprint5070871582fb3ea937024a1d894376462f26fe07e4eeb320fbf4fce00ca72ad2.
Attempt session32827 stopped before OWNED_CHILD/native execution: required
production preflight00:32:14.099350Z reported ECSdesired/running/pending0/0/0,
no tasks, observerHTTP503. No event-stall evidence artifact was created; do not
claim this diagnostic ran or failed physically. Previous local28-call onset
measurement remains intact and is not reopened.

Read-only follow-up: ECS stopped sole1556task5cb1fece1cac4f32b6d2f9b53b61b9ab
at00:30:43.559Z and drained at00:30:52.869Z. CloudTrailUpdateService at00:30:38Z
requested desiredCount0 with no task-definition change, no error, Boto3client.
Purpose/initiator unknown. No G1 stop/cutover notice existed in the latestledger.
A1 recorded coordination notice in main collaborative_todo.md and asked Joe
nonblockingly; no restart, update-service, deploy, marker or live-state write.
Keep goalactive; this is first external prerequisite interruption, not a
three-turn impasse. No goalcompletion/pause/block declaration.

Resume only after rechecking actual external state and coordination; never
restart a diagnostic that lacks a handle merely because observation timed out.
Here wrapperauthoritativelyexited1 before spawning any child. Prepared frozen
source may be reused; do not redo its implementation, prior impact proof,
prefix work, or completed onset trial. Preserve pending event-stall observer
and verify unchanged source/fingerprint before its first actual run.

### FB-01aj resumed earlier-refusal result and domain-partition contract — 2026-09-27 00:38Z

Previous goal turn PROGRESS: source/evidence committed335e86bc2; external
scale-down was rechecked, not treated as a lost test handle. ECS now has sole
healthy1557 taskb35c96647179444cabf98b6441c30fed, image
b5925e5fcaab71bac3fefcbaada587f85f62bad6b0a3153c1b7f74b04e655fa7.
Reviewer custody check confirmed identical sourceSHA
e17ae73851dc955d8f81f53bbd3b621996d684cda4d2b1991268f7f5f789d78f and carried
existing approval to fingerprinta00cda166ac93b491a65b679e088feea93a9b8c57d927c3263bc807b7f5d325a.
No repeat review of mechanical law. First actual --event-stall execution
session95077/child39284:0.672914s wall,0.666193s aggregateCPU,143144KiB,
exit0/no survivors. One native failed step and298 bounded residual evaluations;
NO prefix or trajectory replay. Evidence FB-01aj-midpoint-event-stall.json SHA
7c1b7416ae8655322208c6308faa85be3b3e08f84a6ff329ce32115942450920.

Native residual independently reproduced BIT-EXACT. At43.75us it stalls at
.002030096482185229 normalized residual vs1e-10 tolerance, 29 proposal calls.
Active joint rows28/39/42/46. Row39 has position-0.0, reference
5839.405583553522rad/s2 and force.07933450240889728Nm. Joint37 is NOT an
active row here. Two finite-difference resolutions give similar condition
3.72196e8 and full direction residual3.96024e-6; NOT convergence or a law fix.
Archive-only arithmetic using native getState field order and declared one-free/
all-hinge anatomy confirms q39=1.2760926014309293e-5rad initially, while at the
previous successful37.5us endpoint q39=-1.2556587571327249e-5rad and joint37
still+4.3447160902912826e-8rad. First targeting37 missed an earlier boundary.
No numerical/native execution was needed for this retained-state arithmetic.

AWS00:37:58.659549Z->00:38:01.690132Z counts1/1/0,same original organismidentity,
ticks2506315->2506325,persisted2506309,errorsnull,durabilityfalse,
CPU51.207692%,RAM2.492269%; existingclock-stalledALARM unchanged,other4OK.
No live write. The external health interruption is cleared for this local work.

Single next contract: replace the OBSERVER-SELECTED joint37 diagnostic with a
bounded joint-domain partition of this SAME100us interval, using identical
native force, material, anatomy and residual law. No runtime solver change.
Retire --limit-event and its target-specific function; archived evidence stays.

Construct signed lower/upper gaps directly from all declared limited hinge
coordinates, native ranges and margins. Boolean gap<=0 denotes mechanical
constraint-domain membership, never semantic cognition or a selection score.
Native advancement is still the sole mechanical settlement; observers identify
only numerical domain changes. Attempt remaining time; unchanged endpoint
domain may settle, changed domain is bracketed by SAME-prefix native trials.
A known convergence refusal supplies an unresolved numerical upper bound ONLY
when no actual crossing-side observation exists. Any refusal inside an already
measured bracket stops with retained evidence. No failed step counts as a
negative-gap or force observation. Abort if non-joint constraints enter this
bounded witness. Do not claim endpoints prove absence of hidden in/out events
or guarantee the first continuum crossing.

Bracket unchanged/changed domain to1/.5/.25us in three independent declared
cases. Once bracketed, accept its crossing-side native state/work ONCE and
continue the unspent original duration from that new full state, allowing
subsequent joint boundaries to be measured in causal order. Preserve original
end time exactly, positive/signed/braking/bearing work separately, all rejected
trial isolation and remaining actual energy. No clamping, force blending,
tolerance change, prescribed joint list, extra motor authority or synthetic heat.
Existing107-native-call per-case diagnostic ceiling bounds the entire loop,
not each event; every accepted segment advances representable physical time.
Each success has fresh native-instance exact repeat; at most642 native calls
over6 cases, original twoCPU/1GiB/60CPU/90wall. Failure retains complete current/
bracket/accepted-candidate states, work, budget and rollback, all unpublished.

Reuse the prior16-step prefix state/work WITHOUT recomputing it: authenticate
the existing onset receipt and original failed raw state, capture it under the
SAME current-law model and require exact prefix-successor SHA and bytes.
Supply must equal recorded original minus prior actual positive work. No new
energy or header substitution. Same single tools/guala_body_midpoint.py file;
review frozen source before one local run. Local domain-partition feasibility
and numerical mesh evidence are NOT full250ms/gravity/body/cognition/production
qualification. Those original goal requirements remain open.

### FB-01aj joint-domain resolution measured — 2026-09-27

Prior goal work PROGRESS: the reviewed joint-domain partition completed the
formerly refused100us interval. Frozen fingerprint
10ee370dd545c3b5fb8b5365b3e014b6f930803fb491354ad02672be3abc2cc8,
session6585/child44588, exit0,1.648094s wall/1.643382s aggregateCPU,
147444KiB maxRSS, no timeout or survivors. Evidence
docs/evidence/FB-01aj-midpoint-joint-events.json SHA
af2dda02925dd22e16717625326ead2fbd7cae5ce267dfb5c789de8ec415d71d.
Native calls31/35/39, each fresh-instance repeat byte-exact:210 total, below642.
Same native library de96a1766223905d26b1df0e68ce7bc97608cf2c6238acef8dcf8b344a3fd48f
and interval ABI2 a137418386a8288ac9e99324f0f7176674d14c0eb4b66d47ddc4104e589f2caf.

All three1/.5/.25us brackets observe joint lower limits39,37,35,33 in that
order; each completes at original end .0017000000000000006s. Failed numerical
trials roll back primary bytes exactly and debit no physical work. No prefix
replay, joint clamping, coefficient/tolerance/force-law changes or heat fiction.
At finest resolution positive/signed work .00806805227405821J, braking0,
bearing/self-bearing .00023748516116534816J; supply4674.878007508127J.

Archive-only arithmetic after authentication, no native run: .5->.25us
endpoint maximum joint-rate error .0017447807778086522rad/s vs
.010436573529184272 limit; specific-force worst normalized error
8.887050044953099e-6m/s2 vs .03112942979598029; gyro8.783323168727612e-6rad/s
vs .012912278174505746. Joint-angle maximum9.633827226216449e-8rad vs
.00017453292519943296. Maximum world-frame rotation disagreement
1.1920928955078133e-7rad; translation6.097298959159481e-10m. This frame-centre
measurement is NOT full primitive surface error or all link linear rates.
Positive-work disagreement4.8286114689988224e-12J vs9.06805227405821e-6J;
bearing disagreement4.2179187958102035e-11J vs1.237485161165348e-6J.
The1->.5us pair also meets those measured endpoint limits. These are mesh
disagreements, NOT a continuum enclosure or full-history sensory qualification.
One-sided limit loads are retained at their actual distinct bracket times;
zero-before/positive-after is not averaged/time-warped into pointwise equality.
No surface contacts occur in this interval. Full250ms, gravity, contact history,
whole-body lifecycle/cost and mounting remain OPEN.

AWS pre/post00:47:06.707394Z->00:47:10.962492Z: sole1557 task
b35c96647179444cabf98b6441c30fed, imageb5925e5fcaab71bac3fefcbaada587f85f62bad6b0a3153c1b7f74b04e655fa7,
counts1/1/0, identity1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1,
ticks2508043->2508056,persisted2508037, checkpoint/cleanupnull,durabilityfalse.
CPUaverage51.209771%,maximum51.712979%,RAM2.514648%; clock-stalled ALARM
persists, other4OK. G1 subsequently confirmed its intentional1557 cutover in
the shared ledger; no unresolved production-stop question remains.

Read-only comparison lookup included a nonexistent substrate/functional_body.py;
the actual observation authority is functional_body_native.py, already read.
No file or process was changed by that failed lookup. Do not repeat that path.

Next exact item: extend mechanical load/release feasibility from the saved
successful1.7ms successor to the original250ms load endpoint and250ms release,
with original remaining supply, sole native settlement and explicit bounded
failure evidence. Reuse the completed prefix; do not rerun prior diagnostics.
This continuation remains offline until full accuracy, restart, integration
and safety gates pass. The functional-body goal remains ACTIVE/incomplete.

### FB-01aj continued load/release contract — 2026-09-27

From locald6ef3ba67, continue ONLY the still-open full mechanical interval.
Reuse authenticated1us-bracket successor at1.7ms and its measured remaining
supply from af2dda02925dd22e16717625326ead2fbd7cae5ce267dfb5c789de8ec415d71d.
Never replay the accepted0-1.7ms prefix or reset energy. Validate saved full
integration bytes and final observation under its original last substep.
Retain current model/library/ABI/source identity, effort and thermal work law.

Single tools/guala_body_midpoint.py extension: continue same torso load to
absolute .25s then release exactly that actuator to zero through .5s. Fixed
nominal step100us, shortening only the final step to meet the phase endpoint.
Use the sole native interval settlement. A successful ordinary step remains
unchanged. On the already-characterized midpoint-convergence refusal, require
byte-exact primary rollback and invoke the existing joint-domain partition
on exactly that refused step with its real remaining allowance. Supply the
recorded initial refusal so it is NOT executed twice. No physical/safety
refusal is retried; any surface-contact constraint in the joint-only partition
remains a disclosed unsupported boundary and ends this candidate measurement.
No force/coefficient/tolerance change and no generic contact-law claim.

Sum only accepted positive/signed/braking/bearing work, travel is a maximum;
remaining supply subtracts actual accepted positive work. No rejected-trial
work or scratch becomes a published body. Every accepted segment strictly
advances represented time; each phase ends at its original exact endpoint.
Bound each ordinary case by5000 nominal calls plus existing642 diagnostic
calls (5642 total), including refused calls. A successful case gets one exact
fresh-instance replay from SAME saved1.7ms predecessor;11284 total-call ceiling.
Original2CPU/1GiB/60CPU/90wall wrapper remains. Failure records current complete
integration state, last attempt, partition evidence, work and supply for the
next causal diagnosis; no full-history/earlier-prefix rerun is needed.

Retain only phase endpoints, compact event brackets, an ordered accepted-step
digest and the exact last failure; do not serialize full body/sensors for every
successful100us step. Fresh replay must match all deterministic output including
the accepted-step digest, work and sensory endpoint. Warm start, time, controls
and all integration fields remain included. This is offline feasibility/cost
and fresh numerical continuation, not mounted world cold restart, full250ms
accuracy, gravity, receptor-history qualification or production delivery.
Review the frozen sole-file implementation before its one bounded execution.

### FB-01aj continued interval measured — 2026-09-27 01:03Z

Source-only review PASS, fingerprintc997d1c25431b396b9084a382c0807d0a5a2eec3672bdb0a5995a68f38df9c2b.
One execution session3955/child51696,0.851113s wall/.848480s aggregateCPU,
147104KiB maxRSS, exit0/no survivors. Exit0 is diagnostic completion, NOT a
full-interval pass. Artifact FB-01aj-midpoint-continued-motion.json SHA
8d0ea545e1d1bd00a5698c7546f4f786c9fa9c27be42f79ecce3e53429a8b8f5.

198 successful100us steps carry the saved1.7ms successor to21.5ms. The199th
native call,21.5->21.6ms, refuses midpoint convergence with BYTE-EXACT primary
rollback. Joint-domain helper correctly refuses the already-present surface
contact at zero additional native calls. No phase reaches250ms, no release or
cold repeat is claimed. Accepted continuation positive/signed work
9.947940203258739J, braking0, bearing/self-bearing1.9544323273666238J;
remaining supply4664.930067304892J. Full last predecessor and attempted dt,
complete integration scratch, partial work and refusal cause are preserved.
Do not replay the198 accepted steps or earlier1.7ms prefix.

This isolates the next numerical boundary to SURFACE-CONTACT convergence, not
joint-only onset or resource exhaustion. The prior joint resolution remains
closed locally. Earlier local-refinement source used the PREDECESSOR integrator
and stopped rather than subdividing a native convergence refusal; it cannot
be reused as evidence about this midpoint solve. Earlier current-law2ms impact
measurement demonstrates finer midpoint steps at surface contact, but used a
different authenticated predecessor. It is not proof for this new21.5ms state.

AWS01:02:49.885221Z->01:02:53.092931Z: same1557task/image/organismidentity,
counts1/1/0,ticks2511022->2511031,persisted2511013, errorsnull,durabilityfalse.
CPUaverage51.140824%,maximum51.612756%,RAMaverage2.518717%,maximum2.520752%.
Existing clock-stalled ALARM remains,other4OK. No production write or competing
body process; shared host IDE/TFE processes preserved. The first sandbox-only
census observed only its own namespace; used a read-only host census instead.

Tooling-only failed proposal construction: JavaScript rejected Python-style
triple quotes before any source write. Corrected to JavaScript template strings,
then applied the full source file once; no mechanical execution was duplicated.

### FB-01aj contact-capable numerical subdivision contract — 2026-09-27

Single next correction is numerical convergence at saved21.5ms, not a new
contact constitutive law. Replace the full-interval witness's joint-only
recovery restriction with chronological time subdivision of ONLY the named
midpoint-nonconvergence refusal. The same native solver still computes every
force and accepted successor; geometry/contact/supply/safety refusals end the
run. This is body-only deterministic numerical approximation, not cognition.

Authenticate the retained continued-motion receipt
8d0ea545e1d1bd00a5698c7546f4f786c9fa9c27be42f79ecce3e53429a8b8f5,
its source predecessor, complete failed-step bytes, actual dt, primary rollback
and remaining supply. Start exactly at21.5ms; reuse its known failed100us
attempt without executing it again. Old1.7ms prefix and198 good steps are not
rerun. Original load endpoint .25s and release endpoint .5s remain fixed.

On a numerical refusal, retain the SAME full integration predecessor and
split only its attempted duration at the represented midpoint. Execute the
left subinterval, then the right from its genuine accepted successor. A failed
right branch must not replay the accepted left. Debit only successful
subinterval work once. No temporal extrapolation, omitted contact, pose clamp,
force smoothing, altered residual tolerance or invented heat. Strictly ordered
representable times plus existing5642 total native-call budget bound all
subdivision, successful and refused. Pending time stack capped by53 binary
time refinements; unrepresentable split or exhausted resource bounds refuses.

No failed native trial is treated as measured contact/event evidence. This
algorithm establishes convergence-feasibility only: it does NOT certify event
brackets, detect hidden in/out contact, or replace the separately ratified
whole-history accuracy comparison. Native equation convergence is necessary
but insufficient for physical integration accuracy. Retain that limitation
in every receipt. General contact-history/error verification remains required
before runtime mounting. Remove now-unused joint-only helper options added for
the previous continuation; preserve its original historical diagnostic mode.

Bounded evidence: accepted endpoint and work, compact subdivision timing/counts,
ordered trace digest, exact first failing numerical predecessor/scratch and
partial accepted-only work. One successful full run gets one fresh exact
continuation under the identical schedule/law; no repeat on failure. Same
2CPU/1GiB/60CPU/90wall and read-only AWS envelope, no build/native source change.
One source-only frozen review precedes the single execution.

Frozen67a7427a88bda723cd68ae88aa2bb8da4efaa18cd5078c23f9140a27549b9504
review found one LOCALIZED caller defect before execution: native refusal
restores primary integration bytes but leaves midpoint derived geom_xpos/xmat.
The interval travel sampler would copy those stale derived arrays. Corrected
in one batch: set trial dt, restore the actual predecessor through the existing
native restore/forward helper, assert exact primary bytes, THEN charge/execute
the next subdivision trial. Retain latest refused derived geometry separately
as bounded unpublished diagnostic evidence before rebuilding it. No geometry
override, force-law change or rejected work debit. No harness ran on67a7427a.

### FB-01aj full endpoint continuation PASSED — 2026-09-27 01:13Z

Final source-only review PASS5073decead9ae86849c7144d534b38ad83c852eae9507f1045b512e5573ea798.
Executed once, session8364/child57236. 14.801630s wall/14.797957s aggregateCPU,
143532KiB maxRSS, exit0/no timeout/no survivors. Artifact
docs/evidence/FB-01aj-midpoint-subdivided-motion.json SHA
aa640b34086a7ca5b9c6ce5a35130a6fc6a83aae34cd64653fafaeb2a4591bf4.
Source and native library/ABI fingerprints held before/after. No production
source, state, actuator, caregiver or service mutation.

The saved21.5ms predecessor (bodySHA
7cff1d656c7a4155627cfd595689b9b7f791be3daac79abef53fc7bbb47f2427)
reaches original250ms load and500ms release endpoints. Fresh-instance replay
of the SAME continuation matches complete deterministic result, full state,
sensors, work, event/refusal counts and trace DIGEST EXACTLY. Each case5180
native calls, two cases10360 below11284. Ordinary accepted steps4635;
152 nominal steps subdivided,349 accepted smaller steps,394 added native
trials.197 recorded numerical refusals include the already-archived initial
refusal; that first failed call was NOT repeated. Finest accepted subdivision
1.5624999999963585us. No failed-trial work was debited.

Remaining supply4664.930067304892->4660.354104427842J. Continued load work:
positive4.575962877050519J, signed4.294950819749095J,
braking.2810120573014244J,bearing/self-bearing1.872831499218862J.
Release work: positive/signed/braking EXACTLY0; bearing/self-bearing
.18671530388407198J. Total continuation positive4.575962877050519J,
signed4.294950819749095J,braking.2810120573014244J,bearing2.0595468031029336J.
Maximum substep surface travel .0006661204419389405m. Endpoint bodySHA:
250ms2d831f6bed11034534b201f77212ecfdd54bcc0f37dfa1f0574ff9e7d9f72c46;
500msc4a63075332ce0a798303f5872f0a7fa5f8bf2eda6073a77e8348b00e992f435.
Kinetic energy .40165810979482475J at250ms, .006827685139227984J at500ms;
zero-gravity potential0. Endpoint contact counts0 do NOT mean no earlier
contacts. Unassigned constraint/numerical energy remains unassigned; kinetic
loss beyond measured bearing/braking is NOT relabelled heat.

Acceptance meaning is strictly bounded: successful load/release continuation
and same-numerical-law fresh-instance reproduction, from its authenticated
prefix. NOT a from-genesis single-policy proof, continuum enclosure, complete
contact-event/sensory-history accuracy, real-gravity proof, body/world paired
cold restore, whole-organism mounting, real-time performance or live delivery.
The14.8s contains both instrumented continuations; no pure native solver timing
or production latency is inferred. Original objective remains ACTIVE/open.

AWS01:12:48.711851Z->01:13:05.932976Z: same sole1557task/image/identity,
counts1/1/0,ticks2512899->2512952,persisted2512869->2512933;
checkpoint/cleanupnull,durabilityfalse. CPUaverage51.220748%,maximum51.730308%,
RAMaverage2.530924%,maximum2.532959%. Existing clock-stalled ALARM persists,
other4OK. No required approval is outstanding for the next bounded body work.

Single next acceptance item: qualify the complete load/release numerical path
from one authenticated initial body under the SAME general integration rule,
against the RATIFIED physical accuracy contract. Preserve all required surface,
rate, inertial, contact/event and separate work evidence during that measurement
so a later missing-observation audit does not force a repeated full run. Reuse
existing exact analytical controls and archived onset evidence without reruns;
neither convergence nor endpoint agreement alone replaces history accuracy.
Include solver-vs-observation cost attribution in that same measurement.
Only then mount a qualified minimal native time-integration implementation;
do not promote the offline Python diagnostic, its history digests, or its
test-only resource caps into cognitive/body authority. Gravity/world mounting
and live delivery remain original required gates, not waived deliverables.

### FB-01aj common-genesis trajectory accuracy contract — 2026-09-27

Previous turn PROGRESS:32ecdb831 contains measured endpoint continuation and
exact fresh repeat. No worker is pending. This advances the SAME unresolved
accuracy item; it does not reopen analytical equation, impulse or prefix proofs.
Scope: one offline pair of complete0->250ms load->500ms release trajectories,
same authenticated genesis anatomy and initial supply, same native midpoint law
and generic numerical-refusal subdivision. Only nominal integration resolution
differs100us/50us. Keep native100us model/limits/material identity while varying
diagnostic dt, as in existing mesh comparisons. No serialized model-header
transplant, runtime law, coefficient, tolerance, neural or production change.

One new tools/guala_body_trajectory_accuracy.py uses existing engine_at,
archived_controls and subdivide_refused_step; no duplicated mechanical solver.
Every actual native call is counted/timed. Nominal calls5000/10000 plus existing
642 extra-call ceiling per case bound16284 total. Preserve twoCPU/1GiB/60CPU/
90wall child limits. Stop on physical/safety/resource refusal; subdivide only
the named midpoint nonconvergence with exact predecessor/derived-geometry
restoration and actual accepted-only work. No heavy regression suite rerun.

Observe BOTH trajectories at common100us physical times, derived from integer
microsecond indices. Compare primitive surface displacement including rotation,
geodesic orientations, geometry linear/angular velocities, joint rates,
proprioceptive angles, inertial specific force/gyro, local contact force/couple
with unique position-bounded correspondence, and separate positive/signed/
braking/bearing work under the already RATIFIED error ceilings. Use explicit
per-channel numerical errors, not a cognitive score. Unmatched/ambiguous touch
points remain unresolved, never paired by ordinal or nearest-neighbour guess.

Read each converged native midpoint contact before interval post-kinematics
overwrites its geometry. Accumulate accepted-only world-frame impulses and
force-magnitude path integrals by actual geometry pair, retaining local touch
separately. After each successful substep, restore only DERIVED endpoint fields
with mj_forward, assert primary integration bytes unchanged, and observe contact
support. Retain changed endpoint-support brackets and exact predecessor bytes
for later native-flow localization. A bracket wider than1us is explicitly
UNQUALIFIED; endpoints do not establish absence of hidden in/out events.
Neither mesh agreement nor numerical convergence is a continuum enclosure.

Memory/evidence: bounded per-channel worst errors and their physical times,
first/worst failure samples, observed contact-event inputs and two phase
endpoints, not full repeated sensory/world histories. Emit recoverable progress
states every10ms of diagnostic physical time (observer only) so interruption
does not force replay of completed prefixes. Keep accepted impulse and separate
work, primary states, remaining supply and native-call counts in those records.
Measure native-step, interval-wrapper and observation durations separately;
observer overhead is not production latency. Whole history is sampled, not
silently certified between observations. A failed accuracy assertion does not
end the measurement early; a physical/numerical/resource refusal does.

No production mount is authorized by this diagnostic. Its decisive output is
the explicit accuracy PASS/FAIL/UNRESOLVED map and any retained causal failure,
not a green invocation. Review one frozen source candidate before execution.

### FB-01aj trajectory source review batch — 2026-09-27

Frozen94fe2e60e993af3845cb10b69d0aa29409644c3376a0700e9f8674acc5ebe0c5
reviewed source-only by body_force_review. Three LOCALIZED findings, no
architectural rejection: stage impulse/endpoint receipts together, preserve
nonfinite failure bytes and reject nonfinite derived sums/ratios, and retain
accumulated metric summaries plus event deltas in10ms progress frames. All three
corrected in one source batch before any native execution. No force, anatomy,
tolerance, custody, production or cognitive source changes. All native reads
assert unchanged complete integration bytes. Existing material/impulse/local
correspondence and bounded chronological subdivision laws reused unchanged.
The edit orchestration first had a JavaScript quoting syntax error before any
shell execution; corrected transport quoting, no file/test/native side effect.
Missing historical causal-parsimony markdown in this older worktree is recorded
as skill/document drift; use the current bundled ratified instruction, do not
invent that file or rerun its missing-file path. Read-only main ledger still
shows1557 cutover and prior A1 body receipt; no conflicting source handoff.

### FB-01aj complete sampled trajectory comparison FAILED accuracy — 2026-09-27 01:42Z

Source-only final review PASS1aec5ae73fc1488e18a1b1b0a86199e645dbf9a3b793f0f6f58315aac95936c2.
One bounded execution, session43709/child71317, terminal exit0, no timeout or
survivors.29.109949s wall/29.096555s aggregateCPU; peak148480KiB. Exact loaded
native/ABI fingerprints unchanged. Diagnostic source SHA
a25a9c4782657fa85670bb75ca2d0a82cddb6bc1c1b5d687f60f20825278bb55.
Artifact docs/evidence/FB-01aj-midpoint-trajectory-accuracy.json SHA
c6ac46c2d01131f294f184847a3d9caa7a68d8eaa327af4c5dca6d91245cc01e,
439583bytes. Packed measurement SHA
15c2d45a4acc2b068f7b0b1200318651a2febcc41e5161ab9b0ea286394ca72d.
A later read-only receipt-inspection command had a mismatched here-document
terminator; Python parsed no code and executed no native/state operation.
Corrected only that read command; the mechanical experiment was NOT rerun.

Both common-genesis cases finish0->250ms load->500ms release. Total15664native
calls<16284:100us5410(5205accepted/205refused),50us10254(10127accepted/127refused).
All quantities remain finite, support empty at endpoints, same physical law.
This DOES NOT pass accuracy. First sampled failure1800us:
guala/right/digit-0/distal/flexion/rate. Both trajectories have zero accumulated
surface impulse/support at this point. Original1.6->1.7ms joint-limit evidence
remains intact; first disagreement precedes any sampled surface contact.
Saved BOTH1800us full primary states/supplies/work, not just a failure string.

Across5000 matched100us observations, worst surface displacement6.481560mm
versus0.1mm limit; orientation.09087157rad versus.000174533rad; angular-rate
34.061958rad/s versus.01589153rad/s; specific-force disagreement12276.128536m/s2
at367900us versus.01670301m/s2. Force, impulse, positive/braking/bearing and
signed-work histories fail their ratified limits.62tactile samples have
unresolved correspondence;39matched points;4921both-empty samples. Matched
intrinsic couples are zero but do NOT qualify missing/unmatched contact.
40/44 endpoint-support brackets retained with exact raw predecessors; widths
6.25–100us and25–50us respectively, all above1us. No hidden-event or continuum
enclosure claimed. These are mesh disagreements, not a proof that the50us
trajectory is the exact solution.

Final positive work14.594895573304J vs14.571917204946J;
braking.281012058447J vs.258033690059J;
bearing4.015424616595J vs4.006762823292J.
Final signed work nearly matches14.31388351486J yet its earlier history fails;
endpoint agreement is not sufficient. No unexplained work is renamed heat.
Native-step time7.228320s/5.607823s; interval overhead.733363s/1.175621s;
observer4.726930s/5.733878s. This instrumented offline bench is not real-time
production evidence; observer and solver costs are reported separately.

AWS01:39:22.417068Z->01:39:53.914276Z same sole1557task
b35c96647179444cabf98b6441c30fed, imageb5925e5f...655fa7,
identity1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1,counts1/1/0;
ticks2517901->2517999,persisted2517893->2517989;checkpoint/cleanupnull,
durabilityfalse. CPUmean51.201517->51.147431%,RAM2.551270%.
Existing clock-stalled ALARM persists; remaining4alarmsOK. No live writes.

Disposition: retain this as a truthful FAILED qualification, not a rejected
force law or successful accuracy certificate. Convergence-only subdivision does
not control time-discretization error. No deployment/mount, tolerance relaxation,
force averaging or cognitive workaround. The next bounded item is to isolate
the first1800us disagreement using the ALREADY AUTHENTICATED0.25us joint-event
endpoint at1700us (joint-events artifactaf2dda02925dd22e16717625326ead2fbd7cae5ce267dfb5c789de8ec415d71d)
as a common predecessor. Compare one100us advance with two50us advances, actual
sensor/work consequences and boundary changes, before designing minimal
accuracy/event-aware native advancement. Do not rerun the0->500ms proof or
already closed joint-event construction to obtain this input. Contact-event
qualification, gravity, whole-world mount, paired restart, performance and live
delivery remain required. Goal ACTIVE, no user decision outstanding.

### FB-01aj first-discrepancy isolation contract — 2026-09-27

Previous goal turn PROGRESS:2f72a9103 records completed but accuracy-failing
500ms trajectories, exact retained states and the unchanged live health envelope.
Advance the same accuracy item; do not reopen or regenerate the accepted
joint-event witness. Single diagnostic tools/guala_body_first_divergence.py
reads authenticated joint-events and trajectory-accuracy artifacts. Reobserve
their two original1800us states without advancing, then restore the SAME finest
(.25us event bracket)1700us native endpoint into two existing100us-body engines.
One100us versus two50us advances, same actual effort/supply/time, at most3native
calls, no subdivision/retry on failure. Reuse the reviewed Trajectory observer,
Errors channels and native interval; no new integrator or force law.

Record actual original first-error magnitudes, complete limited-joint gaps,
rates, active constraint types/IDs/forces, same-start/step endpoints, separate
work/supply, primary bytes and comparison limits. This distinguishes accumulated
predecessor differences from error generated inside the next100us window;
it does not alone prove which earlier event generated the inherited difference.
A local pass is not a full-trajectory pass. No tolerance, safety, material,
cognitive or world-mount change.2CPU/1GiB/60CPU/90wall outer ceilings preserved
but only3physical steps allowed. Read-only AWS before/after and child census
required. Freeze/source review before this first execution.

Source-only review9afec526dfb28723dbd53c50cd99f7a73bc10ac5e1c3d629e1d67abae541c588
found one LOCALIZED custody omission: explicitly restore each archived
observation's native_dt_s and reset both common-predecessor engines to the shared
100us timestep before derived-state reconstruction. Corrected before any run;
finite/positive checks retained. Read archived controls once instead of twice.
No force/trajectory/persistence identity change. No architectural redesign.

### FB-01aj same-predecessor isolation — 2026-09-27 01:51Z

Final frozen source review PASSdb2eb52c344ab0d139bd324804105d191df10fbf19bf30d5fd83963ac3b1cb26.
Executed exactly3native steps, session56150/child79662,0.722265s wall,
.718365s aggregateCPU,153724KiB peakRSS,exit0,no survivors.
Artifact docs/evidence/FB-01aj-midpoint-first-divergence.json SHA
df2887df851390b2d6a8db95d2d66411495bb2495546ef9f9ff95ebf7162c8d4;
source SHAe188d8c8ac06fa2c9da2c34ce10065d220aa22d931b8a72c692d56bc90134bec.
Input raw integration SHA0e5dd67cb3ba20fd0f00aafb3edf186223207210d66646904f429683077c4b46.
All original/archive fingerprints, actual timesteps and primary state checks hold.

Local window1700.0000000000006us->1800.0000000000006us completes without
numerical refusal. Native observed joint-constraint IDs remain
[28,33,35,37,39,42,46] before/after all3steps; no surface contact/impulse.
Yet one100us versus two50us steps produces proprioceptive-rate disagreement
.01061525773131966rad/s versus.01013601529895023allowed,ratio1.047281.
Original differing-history states reproduced the same first failure category:
.010351732655144968vs.010137464931870342,ratio1.021136.
Thus inherited state difference or event-location error ALONE does not explain
the first failure: local time-discretization disagreement exists even with an
identical predecessor and unchanged observed endpoint constraint roster.
This does not prove absence of hidden intra-step changes or the exact continuum
solution. Other measured channels pass this local window, not the fullmotion.

Local positive work.008549183206751458J/.008549238096674888J;
bearing.0002661312869229646J/.0002661913415761766J; braking0.
Native step time~.00450s total. Neither prefix nor fulltrajectory was replayed.
AWS01:50:43.637120Z->01:50:46.669606Z same1557task/image/identity,counts1/1/0,
ticks2519608->2519612,persisted2519589,errorsnull,durabilityfalse;
CPUmean51.058302%,RAM2.681478%;pre-existing clock-stalled ALARM remains.

Next bounded item: one predeclared local resolution map25/12.5/6.25/3.125us
(4+8+16+32=60calls), reusing the saved50us result rather than replaying it.
Same authenticated1700us input, efforts, supply and native law. Compare all
approved sensory/mechanical/work channels and actual constraint-domain evidence.
A local convergence map guides minimal numerical-error-controlled advancement;
it cannot certify full500msaccuracy, contacts, gravity or production.

Local resolution-map implementation contract: extend ONLY the existing offline
first-divergence tool with --refinement. Authenticate the saved3callreceipt,
reuse its50us endpoint with its exact recorded timestep/work, and integrate
the same saved1700us predecessor at25/12.5/6.25/3.125us(60newcalls total).
Compare adjacent meshes in ALL existing physical/sensory/work metrics. Record
joint gaps/constraint roster/support before and after every substep; preserve
any changed boundary and exact endpoint/partial failure state. Emit each
completed case independently, retain nonfinite/failure-safe records through the
reviewed observer. No adaptive threshold, fitted coefficient, new law or runtime
mount in this measurement. A missing contact channel is not a claimed contact
qualification. Same bounded network-denied child and read-only AWS envelope.

Source-only review69a90b98cca4562d366f2317ee19c2ea47322db1e27ad9bcb420ee550e87cb16
identified two LOCALIZED omissions before execution: refinement entry must check
actual loaded-native version as main() already does; interrupted cases must
retain accumulated joint-boundary changes, last observed boundary and attempted
substep, not only primary state. Batched both corrections once. No mechanics,
coefficient, tolerance, candidate matrix or runtime change. Re-freeze and final
source-only review required before the fixed60call measurement. The intervening
user feeding-witness audit remained read-only and did not reopen body work.
First ledger append had an incomplete context line; apply_patch refused without
modification. Corrected from the actual tail; no diagnostic was executed.

### FB-01aj local resolution map completed — 2026-09-27 02:05Z

Final source-only review PASSb51d58ea4f59ffaa5019f284e6c6ec033621ff36ed3c815707efdba5932bc2c0.
Same1700us archived predecessor, saved50us result reused without replay.
All60new native calls complete:4/8/16/32 at25/12.5/6.25/3.125us. No refusal,
no observed joint/support boundary changes, no surface contact. Adjacent mesh
proprioceptive-rate differences(rad/s):.0025281271089792057,
.0006246044451357347,.00015569525154893182,.00003889394614314812.
Ratios to unchanged ratified limits:.249358,.061603,.015356,.003836.
All measured local sensory/mechanical/work comparisons pass; approximately4x
error reduction on halving steps supports second-order discretization here.
This is NOT a continuum enclosure, contact qualification or fullmotion pass.
Intrinsic-couple impulse retains UNQUALIFIED status; absent contact is not proof.

Artifact docs/evidence/FB-01aj-midpoint-first-divergence-refinement.json
SHAad25ecfae7475907043f2f192f5769fc3dda75b5c6533e5f3b01e999bf808eb3.
Source SHA7afa81ac22fb1c184cb6bbeaffaf5e9cc7bd32f111bcc3ef00d058c6c9ad77c5.
Session86006,child89690,exit0,no survivors;wall.992747s,aggregateCPU.990175s,
childCPU.907950s,peakRSS152680KiB. Unchanged native library and interval hashes.
No fulltrajectory replay, native compilation, force/material change or livewrite.

AWS02:04:46.252737Z->02:04:49.839772Z:same sole1557task
b35c96647179444cabf98b6441c30fed,imageb5925e5f...655fa7,
identity1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1,counts1/1/0,
ticks2521261->2521265,persisted2521253,errorsnull,durabilityfalse;
CPUmean51.369301%,RAM2.734375%;existing clock-stalled ALARM persists,4othersOK.

Next correction is numerical-error-controlled advancement of the SAME force
law, not another force fit, tolerance relaxation or uniform tiny-step policy.
Use shared-predecessor coarse/fine steps as a local discrepancy estimator,
retain only accepted fine physical state/work and restore all rejected trial
state. Native residual convergence alone cannot admit a physical interval.
Boundary changes and full-motion qualification remain separate required gates;
local mesh agreement is not an exact global-error bound. Define complete
transaction/call-budget/rollback contract before editing the advancement path.

### FB-01aj accuracy-controlled interval implementation contract — 2026-09-27

Previous goal turn PROGRESS209397c87:60calls establish local second-order
discrepancy convergence; no fullmotion/contact/gravity pass. Keep same objective.
Candidate scope: native/functional_body/interval.pyx and the adapter's ABI/header
binding in substrate/functional_body_native.py, plus one focused offline proof.
No force/native solver patch, anatomy, coefficient, safety-tolerance, cognition,
world schema, thermal law or production change. Physical primitive remains the
same native midpoint step; only numerical interval admission changes.

Exact caller map: EmbodimentWorldAuthority._native_transition -> NativeBody.advance
-> compiled advance_interval -> existing native midpoint force settlement ->
MechanicalSuccessor -> native integration bytes/world projection -> existing
prepared world/thermal publication. Observe/restore consume the same integration
bytes. World/material time and chemical/thermal debit occur only AFTER successful
interval return. No candidate step may publish to that authority early.

One model/data scratch only. Save mjSTATE_INTEGRATION at the requested interval
and current trial predecessor; restore through mj_setState plus mj_forward.
No model/anatomy duplicate, checkpoint database, runtime history or callback.
For each declared nominal step: one coarse step, restore predecessor, two half
steps. Compare all modeled geometry position/orientation, geometry velocity,
instrumented proprioceptive/inertial channels, endpoint physical contacts and
actual midpoint contact impulses, plus separate signed/positive/braking/bearing
work. Use unchanged ratified dimensional accuracy limits. Contacts require
unambiguous corresponding native geometry pair and spatial point, not semantic
identity. Observe limit/contact-domain changes; changed brackets wider than1us
must refine. Domain samples do not certify hidden interior roots.

On excessive discrepancy, unresolved contact correspondence, or named native
midpoint-convergence refusal, restore trial predecessor and bisect chronological
time. On any physical safety/supply refusal, nonfinite value, unrepresentable
time, or exhausted call bound: restore whole interval predecessor and original
model timestep, then raise. Never reduce effort, inject energy, average contact
forces, fit parameters, weaken thresholds or rename residual work as heat.
Only fine accepted motion/work is committed to the interval accumulation.
All coarse, refused and accepted native calls count toward3*max_substeps: three
native evaluations per caller-declared numerical work unit, not a timing loop.
Refinement consumes this same finite allowance; it cannot allocate more work.
Caller may later declare a measured larger budget, never a hidden retry budget.
Pending binary partitions are bounded by representable binary64 subdivision.

ABI advances to3 and header binds the new interval law. Old unmounted numerical
state headers must fail closed; no implicit header rewrite or old-law fallback.
Existing world mount schema remains unchanged. Cold proof uses new-law state;
archived input is admitted only as explicitly authenticated diagnostic raw state,
not a persistence migration. Final timestep is restored to declared nominal h.

Local coarse/fine difference is an error indicator, NOT a global continuum
enclosure. The full-motion comparison and contact-event gates remain mandatory
before mounting. Proof first uses the already-authenticated1700us case: finer
motion accepted without energy double debit, exact repeat/new-instance restore,
and insufficient-budget refusal leaving predecessor bytes/time/effort unchanged.
Frozen source-only review before compile; one bounded proof with AWS envelope
and terminal child census. No broad regression or repeated fulltrajectory yet.

### FB-01aj frozen source review correction — 2026-09-27 02:29Z

Source-only review fde016c3e63012659cfba961cd10b9090ccde65de5c11e9a9701cb6901ca8709
completed with one LOCALIZED finding and no architectural finding. Pair impulse
relative allowance incorrectly summed individual point-force magnitudes. Restored
the ratified resultant convention: sum oriented world force/couple vectors per
native geometry pair first, then integrate each resultant magnitude. Signed
impulses remain unchanged. The same reduction is exercised by a minimal partial-
and complete-cancellation arithmetic falsifier; it is not a simulated contact or
claim of full contact qualification. No threshold relaxation or force-law change.
The intrinsic-couple impulse allowance integrates the ratified instantaneous
1e-5 Nm tolerance over actual dt plus .001 times resultant couple-path integral;
this is a local dimensional criterion, not closure of absent-contact evidence.

Correction batch complete; re-freeze and final source review before compilation.
No candidate execution has occurred. Read-only build preflight initially found
no Cython in default Python; the already-recorded scoped dependency directory
/tmp/guala-body-interval.Hdyavt/build-deps is present and reports Cython3.1.2,
setuptools79.0.1 and numpy2.4.6. Build wrapper binds that directory explicitly;
no package install or native force-library rebuild. The prior successful local
resolution map and all physics limits remain closed/unchanged.

### FB-01aj accuracy-controlled local interval PASSED — 2026-09-27 02:35Z

Final source review PASSb3c7c1d088b244540dc91d109577b0ffd8f2fabb1c442b868369014895db98df.
No architectural findings. Compiled only the interval extension into
/tmp/guala-body-accuracy.f0fjtehc/python; ABI3 SHA
7a30227654117e48308d6d443f8a4e79d5b18600af0a8149a3f2a94c8dd07638.
Native force library remains de96a176...3fd48f; predecessor ABI2 remains
a1374183...9f2caf, unchanged. No package install, live mutation or force rebuild.

Session73710: build child7474 exited0,8.660638s wall,8.650990s aggregateCPU,
318348KiB peakRSS. Proof child7522 exited0,.938620s wall,.934013s aggregateCPU,
152636KiB peakRSS. Both terminal censuses have zero survivors. Proof used27
native calls under480 ceiling, no broad suite or fulltrajectory replay.

Authenticated1700us predecessor now advances100us with8 native evaluations,
refining the previously failing coarse step. Independent archived25us reference
agrees to qmax8.67e-19 and vmax8.88e-16. Positive/signed work
.008549251809799178J,braking0,bearing.00026620631694027937J; rejected coarse
work is not debited. Exact repeat returns identical MechanicalSuccessor.
Next100us interval is identical between existing and freshly restored engines.
Three refusal branches pass: smaller compute allowance after3calls; zero supply
after1call; changed applied effort with zero supply after1call. All restore
original predecessor bytes, effort and nominal timestep. Pair resultant
partial/complete cancellation arithmetic checks pass.

Artifact docs/evidence/FB-01aj-midpoint-accuracy-control-proof.json SHA
bb7ae1f244540448208dd0ff4dd638651c47deb4d8e1f22ea915773014db2d63.
Proof source22e393321e3ebbe18fdce48826c3f4151775d2d05f358205c57244df03d92137.
This is COMPILED/LOCALLY EXERCISED, not fullmotion/contact/gravity/world mounting
or continuum-error qualification. No learned behavior or production claim.

AWS preflight initially refused without compiling:02:31:29Z task1559 counts0/0/0
and HTTP503 during G1's active deployment;02:33:26Z counts1/1/0 but healthUNKNOWN,
observation already available. No process/service interference; read-only recheck
cleared at02:34:43Z. Actual proof envelope02:34:43.302675Z->02:34:55.570386Z:
sole healthy1559task5b56802a81ba4978a36aafb995e829a3,
image3c9fce0ce0eaed2196b883a061b424d27c7f1d1709f433039394fba51d2e4b5d,
sameidentity1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1,counts1/1/0,
ticks2522706->2522737,persisted2522700->2522732,errorsnull,durabilityfalse.
CPUmean50.983928%,RAM2.294922%;pre-existingclock-stalledALARM,other4OK.

Next one item: qualify this numerical interval over the existing complete
load/release motion and contact-event evidence. The old fixed-step diagnostic
observes every native trial; it must NOT accumulate rejected adaptive trials as
physical impulses/work. Use only accepted fine trajectories in any observer,
with no change to the force law or ratified tolerance. Complete that bounded
observer contract before editing or executing. Mount/gravity/live gates remain.

### FB-01aj accepted-trajectory qualification contract — 2026-09-27

Previous goal turn PROGRESS99c81bc56. Requested architecture: unchanged bounded
body mechanics, now requiring honest whole-motion accuracy evidence. Current
reality: new ABI3 local accuracy/repeat/cold/refusal proof passes, but full motion
is unqualified. Conflict: no new architecture conflict; evidence remains
incomplete. Do not extend old fixed-step refusal subdivision or count its
rejected attempts as physical impulse. Exact next item: replace only the
offline trajectory diagnostic and emit one bounded common-genesis comparison.
This is reduced rigid-body/soft-contact numerical verification, not seven-field
DSF, learned locomotion, real gravity or production qualification.

Scope is tools/guala_body_trajectory_accuracy.py plus this ledger/evidence.
Runtime source, interval ABI3 binary, native force library, material, anatomy,
limits, cognitive source, persistence/world schemas and live deployment frozen.
Same authenticated zero-gravity torso load250ms then release250ms; numerical
nominal steps100us/50us with the SAME physical model and loads. Each uses
NativeBody.advance on100us comparison intervals, not old raw-step subdivision.
Their new-law headers differ only for declared numerical limits; physical
genesis payloads must agree and authenticate against archived model/controls.
Actual binary64 clocks are reported; never rewrite time to nominal grid labels.

Offline observer wraps module _one_step and _close without changing their return
values. Generated C confirms dynamic module lookup at both call sites. Retain
only the last two fine trial records. _close is called only AFTER the runtime
domain-width condition passes; when it returns True, stage its exact fine
impulses/work and both contiguous fine intervals. Commit observer state only
AFTER NativeBody.advance returns successfully. Any refusal discards that
interval's staged observation. Both fine predecessor/successor bytes, domain and
contact-support change brackets are retained for observed events; rejected
trial forces/work never enter accumulated physical totals. All numerical calls
still count for resources. State checks prove observation leaves primary bytes
unchanged; finally restores all observer bindings.

First falsifier: run this observer on the authenticated1700us input and match
its full successor/work to the archived99c81bc56 unobserved proof (8evaluations,
4acceptedfinepieces). This proves selection excludes rejected/coarse trials.
Then run at most one full comparison, stopping immediately on first channel
failure, unresolved tactile correspondence, wide observed event bracket or
physical/numerical refusal. Preserve both paths' last-successful states,
predecessors, accepted work/impulses, original failure and native call/timing
counts. Continue to500ms ONLY while all sampled gates hold; no expensive
post-failure replay. Existing per-channel thresholds unchanged; unresolved
intrinsic-couple impulse or hidden crossing claims remain explicitly unqualified.

Use prior whole-motion native-call envelope16284 scaled by the three numerical
evaluations per coarse/fine attempt:48852overall ceiling, plus8control calls.
This is a diagnostic work ceiling, not physical admission or a promised bound
on effort needed to complete motion.2CPUs/1GiB/60CPU/90wall outside limits,
progress every10ms plus final first-failure record. Source freeze/review required
before first execution; no native rebuild. Read-only AWS before/after and exact
child census. Record failures without weakening criteria or altering supply.

Source-only review4eff95dd7f4d1e1d60221364d82b88e415e8e3c25a1acef77eaee951a7ab396b:
one LOCALIZED evidence omission, no architectural findings. Added bounded
8-frame traceback to interval and top-level exception receipts so an empty
AssertionError cannot erase the failed-invariant location. No mechanics,
observer selection, physical thresholds or budgets changed. Re-freeze/final
source review before any diagnostic run. Unused Path/zlib imports were already
removed in pre-freeze lean pass. Prior local source/runtime proof stays closed.

Read-only shell hygiene: a grouped lookup used main-tree cwd for a body-only
sprint path (absent), and later read the stale body-tree collaborative ledger.
Neither was used as current serving evidence. Coordination reads/appends bind
/workspaces/Tao_Financial_Engine/collaborative_todo.md explicitly; body sprint
reads bind this worktree. No mutation or diagnostic followed either assumption.

### FB-01aj accepted-trajectory measurement — 2026-09-27 02:50Z

Final frozen source review PASS9e32cd935a7dd4e0cab0e2edfc58be76256faa024ad26eff3463b789bbf98717.
No runtime or binary rebuild. Observer control exactly matches the prior
unobserved1700us successor/work:8nativecalls,4acceptedfinepieces. Thus coarse/
rejected trials are excluded and the observer preserves that physical result.

One comparison ran to21,900us then stopped at first qualification failure:
no sampled motion, proprioception, inertial, contact force/couple, contact
impulse or work-channel failure; tactile correspondence matches10points with
zero unresolved samples. Surface worst error ratio.0002425573; joint-rate.1209533;
specific-force.1588922; contactforce.06159767; contactimpulse.2631811;
positivework.00894391; bearingwork.0873203. These are prefix-only results, not
full500msqualification. Intrinsic-couple impulse remains UNQUALIFIED.

First blocker: one loaded/unloaded contact-support transition per mesh at
21,843.75us->21,846.875us, width3.125us>1us. Geometry pair[6,22] remains in the
collision roster while its force becomes zero. Before/after joint/constraint/
geometric domain tuples are identical. Runtime _snapshot currently includes
geometric contact pairs but omits loaded-pair presence, so its boundary_change
condition cannot see this force-support event. This is a precise omission of
existing measured contact evidence, not a new force/material-law problem.
Both meshes retain exact predecessor/successor integration bytes, supply,
accepted work and domains. Raw event predecessor SHA:
100us c665c27b8e18711530ee831dfdf35af8423ef56f73c9567bd299656c40369bf6;
50us d3e944325d76fd2a2cb37dc1afeaf6cccca95dfb2e5cbf66a0f311fb52dc3f55.
All earlier observed event brackets satisfy1us. No prefix replay is needed to
reproduce this next boundary. No hidden-event or continuum claim follows.

Artifact docs/evidence/FB-01aj-midpoint-accepted-trajectory.json SHA
07e1bb88682a25cc8e04d81a7301d156d606e012e31ef4f83b5325d7184206e2.
Source eda3496c79299bffb822d8c7f05cf31617bc68fb421ff25801be66b984bc12bb.
Session5224,child17495,exit0,no survivors;8.5655s wall,8.556829s aggregateCPU,
157712KiB processpeakRSS.3726nativecalls incl8control,under48860ceiling.
100uspath1586calls/816acceptedpieces/20numericalrefusals;
50uspath2132calls/1208pieces/15refusals. All refused attempts remain unpublished.
The process exit0 means diagnostic evidence completed, NOT qualification PASS.

Read-only AWS02:48:45.112268Z->02:48:56.462495Z:samehealthy1559task
5b56802a81ba4978a36aafb995e829a3,image3c9fce0c...d2e4b5d,
sameorganismidentity,counts1/1/0,ticks2524532->2524557,persisted2524524,
checkpoint/cleanupnull,durabilityfalse;CPUmean51.545477%,RAM3.029378%.
Existing clock-stalledALARM persists;other4OK. Caretaker7712 remains G1-owned.
No livewrites,pushorSlack.

Next bounded correction: carry the existing nonzero native contact-wrench
pair roster into _snapshot's numerical boundary signature, preserving
multiplicity and the same zero/nonzero definition already used by tactile
feedback. Reuse the wrench already read by that loop; no added force solve,
threshold, sensory channel, material law or cognitive state. Advance numerical
law identity so old unmounted headers cannot silently continue under new
admission. Update only directly affected diagnostic law/version checks.
First proof starts from the saved event input, not genesis, and verifies
loaded-support brackets<=1us plus unchanged rollback/custody. Only then
continue full-motion accuracy. Complete this narrow contract before source edit.

### FB-01aj loaded-contact signature correction contract — 2026-09-27

Previous turn PROGRESSc36bed036. Requested architecture: preserve physical
loaded/unloaded contact transitions within the existing1us numerical boundary
criterion. Current reality: _snapshot reads each nonzero wrench for feedback
but omits its pair from domain; saved3.125us event proves the omission. Conflict:
YES with that numerical-evidence criterion, not the force/material law.
Do not extend geometry-only contact classification. Exact next item: append
the loaded native pair roster (including multiplicity) to the existing
transient domain tuple, reusing each already-read wrench. This reduced
rigid-body/contact model does not evaluate DSF or microscopic tissue deformation.

Caller/transaction/rollback remain exactly the99c81bc56 contract:
NativeBody.advance -> advance_interval -> _snapshot.domain -> boundary_change
-> accepted fine state/work -> MechanicalSuccessor -> existing world custody.
No new physical solver, sensory channel, persistent memory, force threshold,
contact label, cognitive authority or allocation scaling. Loaded means the
same np.any(wrench) already used by tactile feedback; zero is not relabeled.
Existing1us criterion and finite call bounds unchanged. Domain tuple is scratch
only; numerical law identifier advances v1->v2 to reject old unmounted headers.
No header fallback/migration in NativeBody or world authority.

Authorized edits: native/functional_body/interval.pyx; directly affected law
checks in tools/guala_body_accuracy_control_proof.py and observer/domain checks
in tools/guala_body_trajectory_accuracy.py; one short saved-event proof tool.
Offline archive comparisons may reconstruct the v1 digest prefix solely to
compare the same raw physical payload against its authenticated old receipt;
that prefix must never be restored as accepted current state. Explicit saved
raw diagnostic input remains separate from cold persistence, which uses v2 only.

First proof authenticates artifact07e1bb...4206e2 and each stored first-wide
event. No prefix replay. For both100/50us cases restore the saved pre-event
raw coordinates explicitly, advance100us, require actual loaded->unloaded
contact support change and all observed brackets<=1us. Verify deterministic
repeat and new-instance cold continuation, old-header refusal and zero-energy
refusal with exact predecessor restoration. Carry exact native calls under480
for this local proof;2CPU/1GiB/60CPU/90wall outer bounds. Record measured force/
work/accepted state without claiming global continuum or fullmotion accuracy.
Unchanged contact-free observer control must still match its archived physical
payload/work even though current law header differs. One frozen source review
before interval-only compile and this proof; no force-library build.

Source-only reviewc3c28331db5d5c8c262614720a0022cc6fded6443c33afa85a83cab758b82f55
found one LOCALIZED evidence omission: completed event and comparison operands
could be lost if a later branch failed. Batched correction records each case
incrementally and retains both complete MechanicalSuccessor operands only on
actual repeat/cold mismatch. The first event receipt survives later failures;
zero-energy refusal preserves expected input and active-case state. No runtime
or physical assertion changed. No architectural finding. Final freeze/review
before any execution.

Operational continuity: prior-turn in-memory runner strings were unavailable
after a container/session restart; no candidate process had launched. Recreated
the same bounded read-only-health build/proof wrapper at the explicit temporary
path /tmp/a1-loaded-contact-run-20260927.py using apply_patch, so its identity
survives the next context loss. This is offline orchestration, not runtime or
cognitive state. Current process census shows the restarted development
container and no heavy Python/build job; do not assume old caretaker PIDs still
exist. Revalidate exact library/dependency paths/hashes and live health in the
launch command; no automatic process restart or service modification.

### FB-01aj loaded-contact boundary verified locally — 2026-09-27 03:15Z

CONTINUES FB-01aj. The geometry-present/force-unloaded omission is locally
closed; whole-motion qualification remains the next item, not a new cognitive
scope. The runtime reuses existing nonzero wrench evidence in its transient
boundary signature and advances the numerical law to v2. No force law, material,
anatomy, tolerance, cognitive state or production path changed.

Independent source review identified only localized proof-evidence retention
omissions. First-event and mismatch evidence were retained; final review found
the warm result also needed recording before the cold call. Applied precisely
that proof-only line and checked the delta directly, without another review
cycle. Executed frozen fingerprint
d324fe2a1e435016ee4d6515f889ce1db5e020b751006d5d9cd6f28dacecf7ff.
One interval-only build, 8.021s wall, 7.791s aggregate CPU, 318976KiB peak RSS.
Force library unchanged. New ABI library:
c76880a83e18f6299026666f63bdd184da685b796fc97e9325ba721d02de3b65
at /tmp/guala-body-loaded.s13rgk1v/python.

Both authenticated saved unloading events pass: bracket 0.7812500000016487us
versus the unchanged 1us limit, formerly 3.125us. Pair [6,22] genuinely unloads.
Both repeat exactly; old-law state headers refuse without mutation. The
contact-free observer control retains exactly the archived raw successor/work.

Proof harness defect disclosed: the 480-call allowance exhausted during the
second mesh's cold continuation. The first mesh completed all branches; second
mesh completed the event, repeat and warm continuation. Receipt retains
completed=False and the exact failure. No whole proof or prefix was rerun.
A fresh isolated process restored only the retained second-mesh predecessor,
compared its complete successor with the saved warm result, then checked zero-
energy refusal. Both pass: 36 + 4 = 40 calls, 0.757s wall, 0.755s aggregate CPU,
145668KiB peak RSS. First proof: 480 calls, 2.076s wall, 1.979s aggregate CPU,
155364KiB peak RSS. Actual total 520 calls includes 15 discarded budget-limited
attempt calls. Future diagnostic ceiling corrected from the measured complete
branch cost: 8 control + 251 first mesh + 246 second mesh = 505 calls.
This changes only the diagnostic allowance, not runtime limits or tolerances;
the combined 505-call command was not rerun. Linked receipts prove the branches.

First immutable receipt:
docs/evidence/FB-01aj-midpoint-loaded-contact-proof.json
SHA 74b07efaf411a6d6886415b1b053f9b3feac05d0841454f213af810f0bf63562.
Completion receipt, including exact offline continuation source:
docs/evidence/FB-01aj-midpoint-loaded-contact-completion.json
SHA 4f634e3548a589596ceda0a1791d42095343f38ef03bbb1f9a8b8cb509928f88.
Sessions79611/44405; build7321, proof7360, completion8191 all terminal; exact
post-run PID/process-group census finds no survivors. No broad tests.

Read-only AWS envelopes03:11:05Z->03:11:17Z and03:13:46Z->03:13:49Z:
same sole1559task5b56802a81ba4978a36aafb995e829a3 and immutable image
3c9fce0ce0eaed2196b883a061b424d27c7f1d1709f433039394fba51d2e4b5d;
counts1/1/0,RUNNING/HEALTHY,sameidentity,ticks2527462->2527492 and
2527813->2527820,checkpoint/cleanupnull,durabilityfalse. CPUmean51.10%;
RAM3.07-3.09%. Existing clock-stalledALARM remains; other4OK. This is not
a blanket organism-health claim. No live writes, process interference, push
or Slack. Current container census does not establish prior caretaker7712
continuity after the development-container restart.

Next: resume the single whole-motion accuracy qualification with loaded-contact
boundary evidence included. Full500ms, gravity, intrinsic-couple impulse,
continuum enclosure, mounting and production qualification remain OPEN.
Do not reopen the closed saved-event correction or rerun completed proof
branches. Preserve approved numerical approximations and frozen cognition.

### FB-01aj v2 trajectory and exact-coincidence contract — 2026-09-27 03:25Z

Previous goal turn PROGRESS4193b5dc7; this continues whole-motion accuracy.
One unchanged v2 witness reached22,200us with all sampled channels PASS and
all observed event brackets<=1us, then refused22,200->22,300us because no
representable subdivision remained. Primary predecessor rollback is exact.
4372nativecalls,9.021s wall,9.011s aggregateCPU,150344KiBpeakRSS;child10545,
session31338terminal,no survivors. No rebuild or broad suite.
Artifact FB-01aj-midpoint-accepted-trajectory-v2.json SHA
988fd726ae61716c5beebefa2347fd2035484683da1f8ed0dd773da35aaba224.

One observer-only replay of that saved100us interval (not genesis) established
the exact predicate:39 contact-correspondence refusals,1 upstream accuracy
refusal,222nativecalls,1.079s wall,1.073sCPU;child11928/session92059terminal.
At the last comparison, one constraint contribution versus two EXACTLY
coincident contributions at pair34/10, both sides. Coarse magnitude13.013449N;
fine contributions6.508800N each. Identical per-side local positions. Summed
force difference.004151661N < unchanged allowance.023017601N. Raw1:2 record
cardinality causes _contacts_close to return False down to dt6.94e-18s.
Artifact FB-01aj-midpoint-contact-comparison-diagnostic.json SHA
bbd0e5ee803b7e24bd33d9ac4d9698478d290f243b281bfd70e3f9fd81f35e7c.
Both receipts retain exact states, observer source and read-only AWS envelopes.

This is NEW evidence at22.278ms under the midpoint law; it does not reopen the
September26 older-window finding that ruled out capsule/box manifold switching
there. No shape, friction, stiffness, solver, impulse law or anatomy change.

Requested architecture: numerical comparison independent of how native solver
partitions a force into exact-coincident contributions. Current reality:
_contacts_close and diagnostic tactile_limits require raw1:1 point records.
Conflict:YES with that representation-independent mechanical comparison.
Do not extend row-cardinality identity or add proximity clustering. Exact next
change: one shared numerical _contact_resultants primitive groups ONLY equal
physical key and exactly equal local position; sums vector force and intrinsic
couple. Separate points and keys remain separate. No averaging, rounding,
nearest-point matching, new thresholds, force replacement or time adjustment.

Conservation: for common point r, sum(r cross F_i + tau_i) equals
r cross sum(F_i) + sum(tau_i); power at common local rigid velocity similarly
adds. This is exact mechanical load representation, not a DSF reduction.
The approved rigid-body model does not represent microscopic tissue stress;
all raw tactile contributions remain in actual BodyFeedback and world codec.

Bounded source map: NativeBody.advance -> advance_interval -> _snapshot ->
_close -> _contacts_close -> new scratch resultants -> existing unique
position-bounded comparison -> accepted fine state/work -> MechanicalSuccessor
-> NativeBody._observation -> NativeWorldObservation.as_record/from_record.
Only numerical comparison changes. _snapshot and actual contacts/BodyFeedback,
native force solver, impulse accumulation, world codec and cognition unchanged.
Diagnostic tactile_limits uses the SAME primitive, not a second arithmetic law.
Runtime scratch O(current contact rows), no persistent/cross-beat state.
Numerical law v2->v3 rejects old unmounted headers; diagnostic raw states stay
explicit, authenticated input. No implicit restore migration.

Authorized files: native/functional_body/interval.pyx; diagnostic contact
comparison in tools/guala_body_event_resolution.py; current law assertions in
accuracy_control_proof, trajectory_accuracy and loaded_contact_proof tools;
one bounded saved-predecessor proof. Preserve all prior receipts.
Acceptance: exact coincident sum invariants; distinct points/keys and excessive
force still refuse; saved22.2ms predecessor advances through former refusal;
exact repeat/cold continuation and energy rollback; raw tactile rows unchanged.
No full trajectory rerun before this narrow acceptance. Source-only frozen
review before compile, interval-only build, resource and read-only AWS envelope.

Read-only03:18:47Z->03:18:58Z and03:21:41Z->03:21:44Z retain sole1559task/image,
sameidentity,counts1/1/0,ticks2528482->2528509 and2528857->2528864,
errorsnull,durabilityfalse. CPU~51%,RAM~3.1%;existingclockALARM,other4OK.
No livewrites,pushorSlack. Operational read mistakes retained: broad /tmp glob
hit an unrelated permission-denied socket directory; no launch followed.
functional_body.py does not exist; actual projection is functional_body_native.py
and embodiment_world.py. Subsequent reads used resolved source matches only.

Frozen source review4cd94896...dda77631 identified one LOCALIZED lean issue:
the new helper repeated three input finiteness scans already performed by the
physical producer. Removed only those scans, retained array conversion and
both summed-vector overflow checks; documented the validated-input precondition.
Physical equivalence, distinct-point/key separation, rollback, identity and
proof evidence otherwise passed source review. Final freeze/review follows;
no candidate compilation or execution yet.

### FB-01aj exact-coincident comparison verified — 2026-09-27 03:34Z

Final frozen source review PASS
0a17ae91cf810809f9c6b169378667862bfe5fc9305c158d3c198656055fc181.
One interval-only build:8.404s wall,8.388s aggregateCPU,330424KiBpeakRSS.
One saved-state proof:333nativecalls under10105ceiling,1.324s wall,
1.307s aggregateCPU,144644KiBpeakRSS. completed=True. No broad regression
or repeated full trajectory; the exact22.2ms predecessor was the input.

The former contact-cardinality failure now advances100us through the event.
Coincident load algebra preserves force, moment and power; distinct keys and
even one-ULP-separated points remain separate. Saved coarse/fine load error
.004151661N is within the unchanged.023017601N allowance. Excessive force and
displaced contact points refuse. Actual feedback rows and world codecs remain
unchanged. Full MechanicalSuccessor repeats exactly and cold continuation agrees
exactly; energy refusal leaves predecessor unchanged. Oldv2 header refuses.
No implicit header migration, averaged force, softened constraint or new field.

Proof artifact docs/evidence/FB-01aj-midpoint-coincident-contact-proof.json SHA
a35cf28f453b603d507f1a6439f46013117ca0b70df1aead94b37a0d905ffe02.
Proof sourceaca90644bcf5b787545ab1785f8115253aa4c0eb6bf895adcf44e70d1ad5f3d8.
Compiled interval
/tmp/guala-body-coincident.f_yh3n0n/python/guala_body_interval.cpython-311-x86_64-linux-gnu.so
SHA13a29c323d79bf9a617209f9db9605dbc985d61fb4273ead87a9539df53e996b.
Same force libraryde96a176...a3fd48f, version3.3.7+guala.midpoint-step.1.
ABI3, lawmidpoint-dyadic-accuracy-v3. Session95894,build16936/proof16980
terminal; exact process-group census confirms no survivors.

Read-only AWS03:33:20Z->03:33:32Z retains sole1559task/image/identity,
counts1/1/0,RUNNING/HEALTHY,ticks2530379->2530407,persisted2530348->2530380,
checkpoint/cleanupnull,durabilityfalse. CPUmean51.34%,RAM3.10%;existing
clock-stalledALARM remains,other4OK. No livewrites,pushorSlack.

This closes ONLY exact-coincident numerical correspondence. Next use the
existing accepted-trajectory tool with the v3 compiled library for the single
whole-motion qualification. Do not reopen the saved comparison, add proximity
merging, or alter the force law. Full500ms,gravity,intrinsic-couple-impulse,
continuum-enclosure,world integration/restart/performance/live remain OPEN.

### FB-01aj v3 whole-motion check: contact-onset disagreement — 2026-09-27 03:44Z

One unchanged-source accepted-trajectory witness reused the compiled v3 ABI;
no build and no broad regression. Frozen tree
4135db62d83a08bac34f8027bb1616768c0fec03006a0090c5685d349d496ee1.
Source and ABI hashes match the preceding reviewed proof. The test passed the
former22.278ms refusal and sampled qualification through47.9ms, then stopped
at48.0ms with all_completed=False. Runtime accepted both states; this is an
accuracy failure, not a successful qualification or another contact-count refusal.

9984 native calls,19.212s child wall,19.198s aggregateCPU,152512KiBpeakRSS.
The unchanged48860-call ceiling extrapolated from prior9.021s/4372calls to
100.82s; operational limits were120CPU/180wall seconds,2CPU,1GiB. No physics or
tolerance changed. Session30548/child20570 exited; exact group census and final
host census prove no proof/build survivor. AWS reads only, no production writes.

Failure is concentrated at right palm/digit-4 distal contact pair(23,33).
The100us nominal mesh brackets its loaded onset at47.964453125–47.964843750ms;
the50us mesh brackets it at47.981640625–47.982031250ms. Each bracket is only
0.390625us wide, but their onset times differ17.1875us. Therefore narrow LOCAL
event brackets do not establish agreement of independently evolved trajectories.
This is an observed distinction, not yet a proven cause of the accumulated error.

At48ms: distal linear-rate error0.009209414m/s exceeds0.002688715 allowance;
proximal angular-rate error0.290831959rad/s exceeds0.019807508;
distal joint-rate error0.252252937rad/s exceeds0.010792406;
local contact force error0.110152921N exceeds0.010743032;
pair impulse error1.16814368e-5Ns exceeds1.89603625e-6;
palm specific-force error0.261746091m/s2 exceeds0.026270996.
Position,orientation,joint angles,gyro and work comparisons remained within
their limits. Full500ms/load-release,gravity and production qualification remain
OPEN. Intrinsic-couple impulse and continuum enclosure remain unqualified.

Exact states/events retained once in
docs/evidence/FB-01aj-midpoint-accepted-trajectory-v3.json
SHA25ca41a761e715243770425b6c7e383f93838b1750ef059ca28348dc04788c5e.
Next single diagnostic: branch both nominal meshes from the SAME authenticated
saved pre-onset state, measure the short contact interval, and distinguish local
integration error from error accumulated before contact. Use saved bytes, not
genesis replay. Do not loosen thresholds or change the force law without that
causal result. No new body/cognitive mechanism is authorized by this failure.

Read-only AWS03:42:03Z->03:42:25Z: sole1559task/image/identity unchanged,
counts1/1/0,RUNNING/HEALTHY,ticks2531623->2531675,persisted2531596->2531660,
checkpoint/cleanupnull,durabilityfalse. CPU51.16%,RAM3.064%;existing
clock-stalledALARM persists,other4OK. This is not a claim that all live organism
health gates pass. No push or Slack. G1 ownership remains unchanged.

Read-only inspection correction: first_failure_states is a LIST, not a mapping;
one summary command raised AttributeError without altering evidence or running
physics. Subsequent inspection checked the type before accessing its contents.

### FB-01aj contact discrepancy follows incoming state — 2026-09-27 03:58Z

Previous turn PROGRESS292e08c7d. Same accuracy defect; no runtime, solver,
material, anatomy, tolerance or production change. Two bounded saved-state
diagnostics reuse the reviewed v3 library; neither replays genesis.

Common-predecessor test: each of the two recorded pre-onset states near48ms
was branched at nominal100us and50us and advanced100us. All four intervals
completed. Within each pair, full raw successors are BYTE-IDENTICAL and every
ratified measure passes; contact onset brackets agree. This isolates the
original mismatch to the different incoming states, not these short contact
settlements. It does not prove that either incoming state is continuum-exact.
128nativecalls,0.990s childwall,0.987s aggregateCPU,159852KiBpeakRSS.
Session34022/child23101 terminal,no survivors. Frozen tree de6cdaabc...657f9b8.
Artifact FB-01aj-midpoint-common-predecessor-onset.json SHA
41fc5be1c8c335b5da2dd78a27c6b6546bee9d486b21b5d93b0aafa0243b8390.

Resolution map: restore the SAME authenticated contact-release state at
31.467968750ms and run the following16.7ms at100,50,25us nominal resolutions.
All167 matched samples complete; both adjacent-resolution comparisons pass
every ratified metric. All three find the next onset in the SAME
47.964062500–47.964843750ms bracket. Position differences remain approximately
1e-8m; no blanket free-flight resolution reduction is justified by this map.
This confines the original incoming difference to the retained state at/before
31.467968750ms. It does not establish which earlier settlement created it.
4286calls under5433ceiling,8.027s childwall,8.011s aggregateCPU,
162224KiBpeakRSS. Session90610/child24909 terminal,no survivors.
Frozen tree343f26e8...0c4b8b46. Artifact
FB-01aj-midpoint-freeflight-resolution-map.json SHA
1d7a816badb907cfeecf36d0b9112e61356607bd0a86b33a9552b148966f15dc.

Existing-data comparison (no physical execution): the original87-event sequences
have identical support changes. The earlier right-palm/digit-4 onset ends at
30.704296875ms vs30.703906250ms (0.390625us difference); subsequent release
brackets agree. Their later48ms onset differs17.1875us. Thus passing LOCAL
state/wrench checks and sub1us event brackets does not establish retained
trajectory accuracy. A new special-case contact matcher or unmeasured global
timestep cut would not address that demonstrated distinction.

Next single item: use the retained pre-contact/event states around30.704–31.468ms
to measure the incoming/outgoing state, impulse and work discrepancy and its
response to the SAME physical law at100/50/25us. Include the observed retained
predecessors, not only a convenient new common state. This is a bounded
numerical error-allocation investigation, not permission to change forces,
weaken acceptance, force mesh equality or rerun full500ms before its cause is
resolved. No production candidate selected from a passing sample alone.

AWS read-only03:48:08Z->03:48:12Z and03:52:50Z->03:53:01Z: same sole1559task,
image and organism identity;counts1/1/0; ticks2532495->2532502 and
2533168->2533194; errorsnull,durabilityfalse. CPU51.38/51.28%,RAM3.064%.
Existingclock-stalledALARM remains;other4OK. Final actual-host census contains
no proof/build/caretaker worker. No live mutation,pushorSlack. Full-body
accuracy/gravity/integration/restart/performance/deployment remain incomplete.
Rigorous continuum enclosure is not claimed; the ratified contract accepts
explicitly labelled numerical estimates, not a claim of every future trajectory.

### FB-01aj retained-error and computational feasibility map — 2026-09-27 04:28Z

The previous conversational status turn was NO PROGRESS. This block continues
the same whole-motion numerical-accuracy defect; it does not reopen the exact-
coincident contact comparator. Runtime source remains at 3e08b0c4b. No force,
material, anatomy, acceptance limit, cognition or production change was made.
Reduced rigid-body/soft-contact numerical verification only; no DSF evaluation.

Three authenticated local receipts now make the next choice quantitative:

1. `FB-01aj-midpoint-prior-contact-map.json`, SHA-256
   `15e21854d94f947311a3c48b320251ca44893f4911725da09a9c6c62af35aa56`.
   Actual archived stage replay reproduces predecessor/successor/work exactly.
   Both original incoming states through the preceding contact were crossed
   with 100/50/25 us meshes. All local comparisons pass; retained differences
   remain. 1422 calls, 3.416 s wall, 170932 KiB peak RSS. This does NOT identify
   a new force or contact-matching defect. Small locally admitted errors can
   survive into a later contact; local acceptance does not prove whole-motion
   accuracy. Session 63393 / child 29093 terminal, no group survivors.

2. `FB-01aj-midpoint-error-allocation-feasibility.json`, SHA-256
   `f4626dc41923a86c0316a619f058cf0f35338b5e453cc83662b6651eb45ffe0b`.
   Offline allocation multiplies retained-state absolute/relative allowances
   by dt/H, with H=0.25 s; additive work/impulse absolute allowances scale once.
   Instantaneous wrench/acceleration limits stay unchanged. A stable atan2
   relative-rotation calculation avoids the near-zero acos cancellation floor.
   Both nominal meshes finish 100 us with identical successors, but each uses
   256 accepted fine pieces and 638/636 native calls. Identical adaptive paths
   are NOT independent convergence evidence. Native work alone costs about
   0.22 s per 100 us simulated; interval overhead costs another 0.48 s. This
   is not a viable real-time correction. No runtime candidate or schema change
   is selected from this pass. Total 1274 calls, 2.548 s wall, 159620 KiB RSS.
   Session 70336 / child 30842 terminal, no group survivors.

3. `FB-01aj-midpoint-truncation-regime.json`, SHA-256
   `1b0a9fefbaec3dd58fcc32a082de267e0b93ba68b4b3e418e67c333446a54c2f`.
   Frozen input tree 0f7114e7c60d17dad8f003c2c5e3f58a406e6cc4d6d1998e3d903f39b1adff4e.
   One exact archived native-stage control, then three saved predecessors
   (events 78, 80, 84) at twelve dyadic durations, 100 to 0.048828125 us.
   Every branch restores the same complete predecessor; no cumulative replay.
   All 36 cases execute, 109 calls under 145, 0.872 s child wall,
   0.855 s aggregate CPU, 156308 KiB peak RSS. Native step time is 0.029705 s.
   On unchanged sampled domains, dominant rate discrepancies approach h^3,
   and dt/H-normalized discrepancies approach h^2. Near event 80, allocated
   retained-error ratios are 10.714 / 2.709 / 0.681 / 0.171 at 3.125 / 1.5625 /
   0.78125 / 0.390625 us. This is genuine truncation-error reduction, not a
   floating-point floor or evidence supporting another contact special case.
   Session 59522 / child 36240 terminal, no group survivors.

The source-only reviewer proposes a transient dyadic next-trial hint from the
accepted discrepancy: h_next = h/sqrt(rho) for this observed local order and
dt/H allocation. It would only propose trials; every existing finite, supply,
collision, discrepancy and event check still applies. It is not a whole-motion
bound and cannot eliminate required fine-motion cost. Therefore it is NOT
being presented as the practical solution or promoted to runtime by itself.
If a future allocation law uses H, H must be independent of CPU/call allowance;
increasing a resource ceiling must never silently change physical accuracy.

Higher-order numerical integration is now a bounded feasibility question, not
an accepted architecture. In particular, blindly extrapolating midpoint states
is unsafe for stiff decay: with z=h*lambda, R(z)=(1+z/2)/(1-z/2), and
E(z)=4*R(z/2)^2/3-R(z)/3 tends to 5/3 as z tends to negative infinity. Such a
method can amplify a decaying mode. It also needs truthful stage work/impulse
accounting and cannot reuse midpoint-only receipts. Do not implement an XML-only
RK4 switch (already rejected at 17:19Z), negative-work clipping, a larger native
call budget, a relaxed tolerance, or a contact-specific matcher as a workaround.
The single next item is a source-level choice of a bounded, stiff-stable
numerical correction preserving the existing force law and complete custody;
then map its smallest saved-state falsifier before implementation. No new
behavioral, neural, curriculum or anatomical mechanism is in scope.

Operational envelopes were read-only; all three children denied network.
Latest 04:23:32Z -> 04:23:35Z retains task 1559, sole task
5b56802a81ba4978a36aafb995e829a3, image 3c9fce0c...2e4b5d,
identity 1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1, counts 1/1/0,
ticks 2537602 -> 2537610, null checkpoint/cleanup errors and no durability
block. CPU 51.36%, RAM 3.064%. Existing clock-stalled ALARM remains; other
four alarms OK. This is not a complete live-health clearance. Final host
census has no proof/build/caretaker survivor. No push, Slack or live write.
All functional-body accuracy/gravity/integration/restart/performance/deployment
gates remain explicitly incomplete.

### FB-01aj next numerical mechanism selected for bounded qualification — 2026-09-27 04:33Z

The independent source-only reviewer rejects unrestricted midpoint Richardson
extrapolation. Its initial Gauss-Legendre recommendation was compared explicitly
with two-stage Radau IIA and revised to Radau: the same two stage count and
positive work weights, but L-stability and an endpoint equal to the final stage.
This is a PROPOSAL for the already-authorized body-only numerical domain, not
a new material law, runtime candidate, measured speedup or passed accuracy gate.

Use the fixed tableau A=((5/12,-1/12),(3/4,1/4)), b=(3/4,1/4), c=(1/3,1).
For scalar decay y'=lambda*y its amplification is
R(z)=(1+z/3)/(1-2*z/3+z*z/6), z=h*lambda, tending to zero for stiff decay.
Its third order sacrifices one smooth-regime order against two-stage Gauss,
whose stiff amplification tends to one. This choice must still be falsified
on the retained nonlinear contact states; scalar stability is not body proof.

The bounded physical/numerical contract to implement in an OFFLINE stage probe:

- Inputs: the authenticated complete saved body predecessor, constant admitted
  efforts, remaining chemical work supply and positive trial duration. Use the
  same model, constraints, damping, limits and instantaneous force evaluator.
  No full-history replay, production import, coefficients retuned to h or new
  motor decisions. Start from the existing saved-state regime/control receipts.
- Solve both coupled stage equations simultaneously. For ordinary translational
  and hinge coordinates, q_i=q_0+h*sum_j(A_ij*v_j) and
  v_i=v_0+h*sum_j(A_ij*a_j). Each a_j comes from the unchanged instantaneous
  physical dynamics at its own q_j,v_j,t_0+c_j*h. Two independently converged
  midpoint solves are NOT the Radau equations.
- A free-root rotation uses one local SO(3) chart R_i=R_0*exp(hat(sigma_i)).
  Its equation is sigma_i=h*sum_j(A_ij*J_r(sigma_j)^(-1)*omega_j), not an
  average of quaternion coefficients or angular vectors. Confirm the native
  free-joint angular-velocity convention before coding this map. For body-
  frame angular velocity the inverse right Jacobian is
  I+hat(sigma)/2+[(1-(theta/2)*cot(theta/2))/theta^2]*hat(sigma)^2.
  Use its analytic zero limit, not a physical deadband; reject chart/finite
  failures rather than clamping pose. Native tangent utilities alone do not
  establish higher-order rotation accuracy.
- Numerical acceptance requires the complete, dimensionally normalized stage
  residual. Iterations, stage/force evaluations and line search must be finite
  and counted. The offline probe may use bounded dense numerical Jacobians
  for qualification, but that cost is diagnostic and is NOT a production
  performance claim or permission to ship a dense recurring controller.
- State-dependent work is integrated at the same stages with weights 3/4,1/4:
  signed motor work h*sum(b_i*tau dot v_i), positive/braking work from positive/
  negative physical power, bearing loss h*sum(b_i*v_i^T*B*v_i), and contact
  impulse from each stage's actual oriented world-frame pair resultants.
  Separate self/world-bearing channels remain separate. Positive weights keep
  dissipative quadrature nonnegative; numerical energy discrepancy remains a
  discrepancy, never heat. Do not reuse midpoint-only work/impulse receipts.
- Only after convergence and all physical/supply checks, the final stage is
  the endpoint. Recompute its actual feedback. Do not extrapolate contact
  records, persistent bytes, warm starts, controls or elapsed time. Failed
  probes restore the full predecessor. Any later runtime law must retain the
  ordinary whole-interval rollback, explicit header identity, cold continuation,
  bounded contact subdivision and current world publication boundary.

Exact next executable item: one offline Radau stage primitive and small
common-predecessor dyadic map with separately measured residual, work, contact,
state error and CPU/calls. First reproduce the accepted instantaneous physical
law at the saved predecessor. Then compare same-state meshes; no production
source edit/build or broad whole-motion run until this primitive is justified.
The earlier dt/H implementation/schema proposal is NOT being extended merely
because it was tested. Its impractical required fine-step cost remains recorded.

Reference roles: MuJoCo 3.3.7 computation documents distinguish instantaneous
forward dynamics from numerical integration; the frozen local source remains
authoritative: https://mujoco.readthedocs.io/en/3.3.7/computation/index.html .
Hairer/Wanner's stiff-integrator materials describe the Radau family, not this
body's qualification: https://www.unige.ch/~hairer/preprints/coimbra.pdf .
No framework upgrade, new cognitive state, force softening, tolerance relaxation
or authorization request is needed for this bounded numerical investigation.

### FB-01aj Radau saved-state primitive measured — 2026-09-27 04:58Z

PROGRESS: the reviewed offline two-stage Radau primitive now has executable
evidence. This continues the existing body-only numerical accuracy/cost defect;
it is NOT runtime integration, a complete body, or production qualification.
Frozen source tree was 4d18163d1ea7bfd1d33c2ef8766561baff4bbdeb3d462fbfd147af9e014c4ed2.
No physical force, anatomy, material, cognition or acceptance tolerance changed.

One source-only review found localized diagnostic-evidence gaps. A single batch
added finite aggregate work/travel checks, retained partial-case state and failed
nonlinear operands, complete sensory/impulse repeat comparison, and separate
counts for stage forwards, setup/restore forwards and the archived native step.
Final frozen source-only review passed before execution. Exact sources are
retained inside the receipt (including the stage module), not organism memory:

- /tmp/a1-body-radau-stage-20260927.py:
  462edb5d8fbaabb7b61ac6fd7c571a4ec7775595240d731d61882b69414811d4.
- /tmp/a1-body-radau-regime-20260927.py:
  2714aaba48aaf9ba0b2497d4bf3b1f7336628874f3eb03fd90a796eebe1c8e21.
- docs/evidence/FB-01aj-radau-stage-regime.json:
  15ed890c9604b7ac5a45372b722d1655c835503cc8e9c2c01e3ed59007e6ad4f.

The saved event-80 predecessor is at 31.016406249999864 ms. Three fresh copies
advance the same 25 us with 1, 2 and 4 pieces. All complete; sampled constraint
domains agree. This is only sampled-domain evidence, not continuous absence of
an unobserved event. Controls reproduce the archived native stage exactly and
the current instantaneous acceleration/sensory law exactly. The rotation-chart
inverse satisfies its algebraic control. A fresh repeat is exact in full retained
state, work, impulse and complete endpoint sensory/contact observation. Positive
work with zero supply refuses and restores the complete predecessor exactly.

All ratified local comparison channels pass; intrinsic couple impulse remains
UNQUALIFIED because no separate ceiling was ratified. The principal joint-rate
discrepancy falls from 2.2107801019188855e-5 to 2.82007443330734e-6 rad/s on
refinement, about 7.84-fold. Contact impulse discrepancy falls from
1.3558961653503096e-9 to 1.7285579758269116e-10 Ns. These are numerical estimates,
not an exact continuum enclosure or the required whole-motion result. Existing
near-zero acos orientation observations are not evidence of exactly zero
rotation error. No accumulated-error allocation or long-interval pass is claimed.

Cost is explicitly unacceptable as a production implementation: 12351 stage
forwards (under 33310), 21 setup/restore forwards (under 21), one archived native
step. The single 25 us trajectory requires 1763 forwards and three Newton
updates; finer steps each require 1177 forwards and two updates. A 146-variable
central-difference Jacobian takes 584 stage forwards per Newton update. This
dense diagnostic differentiation dominates the work; a higher call ceiling or
repeated broad trajectory is not the next correction. Internal native constraint
iterations are not mislabeled as separately counted calls. Stage forward wall
time is 0.905945 s; complete child wall 2.603997 s, aggregate child CPU 2.599964 s,
peak RSS 166880 KiB. Session 96625 / exact child 48419 exited 0, no timeout,
no group survivors and no exact-command survivor in final host census.

Next single item: source-map the smallest efficient way to solve these SAME
coupled residuals, retaining the existing actual residual/finite/work/rollback
checks. Compare any available native instantaneous derivative with bounded
matrix-free numerical solving; do not substitute derivatives of a different
integrator, a softened force, stale physical feedback, a guessed contact law,
or a production dense solver. The primitive stays offline until its work and
whole-motion error are qualified. No further user authorization is needed for
this already-approved body-only numerical question.

Read-only AWS 04:56:22Z -> 04:56:27Z: sole task 1559 / task
5b56802a81ba4978a36aafb995e829a3, image 3c9fce0c...2e4b5d, same organism identity,
counts 1/1/0 and RUNNING/HEALTHY. Ticks 2542346 -> 2542357; checkpoint/cleanup
errors null; durability false. CPU average 50.9391%, RAM 3.0660%. Existing
clock-stalled ALARM remains; other four alarms OK. This is not full health
clearance. No live mutation, push or Slack. G1 ownership is unchanged.

Operational mistakes retained rather than hidden: an initial Delete+Add patch
for the same scratch path was rejected without mutation, then replaced through
separate apply_patch calls; source lookup guessed two nonexistent paths before
using rg --files; the already-known legacy root-validator failure was repeated
read-only and must NOT be repeated again (preflight its historical handoff first;
otherwise use the exact git root/branch/HEAD and this sprint authority). An initial
process census and metric print were too broad; subsequent census selected only
the owned group/command and result extraction emits channel maxima only. None
of these errors launched a second physical test or changed production state.

05:00Z source-grounded next mechanism: independent review recommends bounded
matrix-free Newton-GMRES on the SAME coupled Radau residual. Pinned MuJoCo
engine_derivative_fd.c:538 differentiates mj_step, so mjd_transitionFD is the
wrong target. engine_derivative.c:1485 mjd_smooth_vel covers only smooth-force
velocity derivatives, not complete constrained acceleration/position dependence.
engine_derivative_fd.c:601 mjd_inverseFD is instantaneous but still coordinate-
wise finite differencing and needs an inverse-to-forward derivative solve plus
the rotation-chart chain rule; it is not a verified drop-in shortcut. Owner
read these exact source boundaries; no production derivative substitution made.

The narrow candidate for OFFLINE qualification is a centered directional
product Jp = [R(x+epsilon*p)-R(x-epsilon*p)]/(2*epsilon), in dimensionless scaled
coordinates, with roundoff-derived perturbation and bounded Krylov dimension.
Each product needs four stage forwards instead of four times all 146 unknowns
for a complete Jacobian. Retain the actual nonlinear residual, line search,
Newton/call ceilings, identical stage work/impulse integration and full rollback.
Predicted Krylov improvement can never admit a successor. Compare against the
retained dense-Radau result, complete sensory/contact output and work before
any longer run. Reduced cost is plausible, not measured or accepted. No new
numerical contract, implementation, source review or run is claimed yet.

### FB-01aj matrix-free offline correction contract — 2026-09-27 05:06Z

Previous turn was PROGRESS (local commit ed237ce5a, short Radau receipt). This
continues numerical accuracy/cost, not new body functions or a production law.
Requested: same stage equations/physical successor within ratified numerical
limits at less compute cost. Current: dense differentiation passes the short
saved-state comparison but costs 1763 stage forwards per 25 us. Conflict: YES
with required production performance; no force/geometry defect is inferred.
Not extended: dense production Jacobian, predecessor-integrator derivatives,
relaxed tolerances, cognition or live mutation. Single next item: offline
matrix-free correction against the already-retained dense Radau evidence.
Reduced numerical body mechanics only; DSF joint fields are not evaluated.

Exact solver substitution: let S be the existing diagonal variable scale and
F(z)=R(x+Sz), where R is the unchanged dimensionless coupled stage residual at
the current Newton iterate x. Solve J_z delta_z=-R(x) by finite, non-restarted
GMRES; return physical delta_x=S delta_z to the unchanged line search. For
each unit Krylov direction p, centered difference uses
epsilon=machine_epsilon^(1/3)*max(1,norm(x/S))/norm(p). This is a numerical
roundoff/truncation balance for differentiation, not a physical coefficient.
Every plus/minus evaluation restores the identical full predecessor before
evaluating each physical stage. No retained cross-step derivative or controller.

Use two-pass modified Gram-Schmidt and a bounded projected least-squares solve.
The diagnostic ceiling is 32 Krylov directions, six existing Newton iterations
and sixteen existing line-search divisions. These are execution/refusal bounds,
not physical accuracy limits. Linear prediction may stop at the larger of the
existing nonlinear tolerance and sqrt(machine_epsilon)*initial residual norm;
it can only propose a correction. The actual nonlinear residual and physical
checks alone govern success. Nonfinite operands, unrepresentable perturbations,
Krylov breakdown without convergence, resource exhaustion or failed decrease
refuse and preserve the complete predecessor. Partial linear and nonlinear
failure evidence must be retained in the external receipt.

Authority/mutation/rollback/work quadrature/endpoint/cold header remain exactly
the offline stage contract above. Nothing is mounted or serialized as a runtime
law. Storage is O(n*32+32^2) transient solver data; calls at most
9*(5+6*(4*32+2*16))+1 = 8686 stage forwards for the same nine-step diagnostic
including its instantaneous-force control. Existing setup/restore/native-step
entry counts remain separate. No timing estimate qualifies deployment.

Acceptance: reproduce the same archived native stage and instantaneous force,
then compare 1/2/4-piece successors with the retained dense-Radau states/work/
impulses/full endpoint observations from receipt 15ed890c...6ad4f. Retain ordinary
refinement comparisons, exact fresh repeat and zero-supply rollback; report
costs and first failure. Reference restoration must reproduce its saved
observation before using it as evidence. A small algebraic linear-solver control
is supporting numerical evidence only. No broad trajectory, native build,
production source edit or force-law change is authorized by a local pass.

### FB-01aj matrix-free saved-state result and next regime — 2026-09-27 05:16Z

OFFLINE PASS on the named short comparison. Receipt
docs/evidence/FB-01aj-radau-krylov-regime.json SHA256
0cd0811396d725582ab8ea6361eb62ac8d9a4bbd5a93c76bdf5084e0e18c7009.
Frozen source review required one localized reporting correction: unresolved
tactile correspondence must not become an aggregate pass just because
first_failure is null. Final review passed after requiring every qualified
metric group's status PASS; only intrinsic couple impulse remains explicitly
UNQUALIFIED. All three dense references restore their complete endpoint
observations exactly before comparison. All qualified dense-reference and
1/2/4 refinement comparisons pass. Fresh repeat and zero-supply rollback are
exact. Same saved force law/rotation/algebra controls pass; no tolerance changed.

Stage forwards fell 12351 -> 361 across the same nine-step protocol, about
34.2x fewer, NOT a 34x end-to-end or production speedup. Outside-stage forwards
are separately 30 (including nine new reference-restore calls), plus one
archived native step. Single 25 us motion uses 49 forwards instead of 1763;
its stage wall time is 0.009632 s and native time 0.003712 s. This is still not
real-time performance. Finer 2/4-piece copies use 82/132 forwards. Two Newton
updates converge per step with 6+4, 5+3, or 4+2 Krylov directions, rather than
146-coordinate Jacobians. Residuals remain below the unchanged 1e-10 limit.
All-stage native wall time 0.030102 s; complete child wall 1.002666 s, aggregate
CPU 0.994137 s, peak RSS 163264 KiB. Full-body qualification remains false.

Session84927/child54970 terminal, exact group/command census no survivors.
Read-only AWS05:13:26Z->05:13:29Z retains sole1559task/image/identity,counts1/1/0,
ticks2544809->2544816, errorsnull,durabilityfalse. CPU50.9524%,RAM3.0762%.
Existingclock-stalledALARM remains;other4OK. No push,Slack or live mutation.

Single next diagnostic, SAME primitive unchanged: map local accuracy, sampled
contact-domain changes, actual residual and solver work across authenticated
saved successors of events78/80/84/86 (30.590625,31.01640625,31.46796875,
47.96484375 ms). At each, independently compare one full step and two half
steps at100/50/25/12.5/6.25/3.125/1.5625/0.78125 us. Each branch restores the
same complete source with its actual remaining work supply. No full-history
replay or parameter/force/tolerance tuning. At most96 steps plus one actual
archived native control; stage ceiling96*965=92640, separate setup/restore
allowance accounts two reusable copies, one control instance,64 branch restores,
one control restore/post-forward and at most64 failed-branch rollback forwards.
Whole child remains2CPU/1GiB/60CPU-seconds/90wall-seconds, network denied.
Failures are retained per independent regime point, including the first failed
step/rollback, not retried or treated as successful physical progression.
Record complete accepted raw states/work/impulses, and per-channel-group worst
error with label/status; do not print or duplicate every channel into chat.
Retain per-stage nonlinear evidence and instantaneous sensor values in the
receipt as already supplied by the primitive. A local regime pass is not an
interval controller or production law; whole-motion comparison remains required.

### FB-01aj contact-regime map and exact endpoint refusal — 2026-09-27 05:23Z

Receipt docs/evidence/FB-01aj-radau-contact-map.json SHA256
1d69fb485b2dce7979fd7856c552020b3a1d035197dbb34c3e47084e31159f1c.
Source-only frozen review passed. Of32 independent points,30 completed their
full/half comparison and all30 passed every ratified channel (couple impulse
still explicitly unqualified). Event80 at100us crosses sampled domains and
has a joint-rate ratio0.8547 and contact-impulse ratio0.8072: it is close to
local allowance, not evidence for whole-motion acceptance. Source-model forces
and all solver limits remain unchanged. Primitive calls3416, extra forwards72,
native stage wall0.265421s; child2.221862swall/2.215293saggregateCPU/170216KiBRSS.
Session63693/child57621 terminal with no exact command/group survivor.

Two points were NOT physically evaluated at full100us (events84 and86). The
driver forms stop=begin+requested_duration and passes stop-begin; binary clock
rounding makes this difference slightly larger than the strict100us maximum.
The primitive refuses before its first stage forward. These are diagnostic
endpoint-construction errors, not nonlinear/contact instability or evidence
that the two points passed. Their independent half-step branches did execute;
the full raw inputs and refusals are retained. Empty sampled-stage sets must
not be interpreted as proven unchanged domains.

Bounded correction: construct a common representable endpoint for each pair.
If round-to-nearest(begin+h)-begin exceeds h, select the immediately preceding
representable endpoint toward begin. Require positive advance and actual span
<=h without epsilon slack, then split that SAME endpoint for the half path.
This directed rounding does not relax step, force, energy, geometry or error
ceilings. Record nominal and actual spans. Recheck ONLY events84/86 at100us;
the30 passing points will not be replayed. Stage/linear primitives remain
byte-identical. No production-source correction or new numerical law is implied.

Read-only AWS05:20:16Z->05:20:21Z retains sole1559task/image/identity,counts1/1/0,
ticks2545768->2545778,errorsnull,durabilityfalse. CPU51.3392%,RAM3.0762%.
Existingclock-stalledALARM remains;other4OK. No push,Slack or live mutation.

### FB-01aj contact regime complete; accumulated-motion accuracy next — 2026-09-27 05:33Z

Previous turn was PROGRESS: the exact running session17299 was polled to
completion, not restarted. Receipt FB-01aj-radau-endpoint-check.json SHA256
2808e9a277304fae786e9734f13f78e092c7a86009e2e597f0a03049df0c5721
corrects only the two unevaluated common endpoints. Both actual spans are
9.999999999999593e-05 seconds, strictly within100us. Event84 passes. Event86
fails proprioceptive right digit4 distal rate: error0.011651297214733791rad/s
versus allowance0.011516276492226715, ratio1.011724338383002. This physical
comparison failure is retained, not rounded away. Other ratified groups pass.
Event86 at50us already passed in the prior map (worst rate ratio0.109630);
no passing point was rerun. Combined map:31/32 sampled points pass, not a
global or continuum accuracy certificate. Intrinsic couple impulse remains
explicitly unqualified. No changed force, anatomy, or acceptance tolerance.

Endpoint check:358stageforwards,12outsideforwards,1archivednativecontrol;
stage native time0.022097s. Complete child0.897782swall,0.891591saggregateCPU,
169396KiBpeakRSS. Child59800 terminal with no exact-command/group survivor.
AWS05:26:11Z->05:26:14Z retains sole1559task/image/identity,counts1/1/0,
ticks2546623->2546630,errorsnull,durabilityfalse. CPU51.1830%,RAM3.0762%.
Existingclock-stalledALARM remains;other4OK. This is not full health clearance.

Requested architecture: accurate, bounded-cost whole body motion and sensory
return. Current code reality: offline Radau primitive/local regime map only;
no candidate runtime law has replaced the midpoint source. Conflict:YES with
completed delivery/real-time claims; no new cognition or force-law conflict.
Not extended:dense production differentiation, per-step full error allowances
misrepresented as global bounds, relaxed tolerances, sensory/cognitive shims.
Single next item: define and exercise accumulated-motion numerical control,
retaining this local regime and the authenticated prior trajectory; do not
reopen settled contact correspondence or replay the32-point matrix. Reduced
body numerical approximation; joint DSF dynamics are not evaluated or changed.
Predecessor local matrix-free equivalence/repeat/rollback stays closed by
receipt0cd08113...7009. Full motion, gravity, mounted integration, restart and
production performance remain OPEN. No push,Slack,productionwrite.

Read-only path preflight found no tools/guala_body_interval.py or historical
September05 parsimony-law document in this tree; interval source is
native/functional_body/interval.pyx (located with rg). Skill historical-route
drift does not authorize invented files or a second architecture. Body root,
branch,HEAD and this sprint continue as the explicit continuity authority.

### FB-01aj compiled Radau stage contract — 2026-09-27 05:37Z

Independent design review recommends common-genesis paired whole motion:
250ms load+250ms release at100/50us nominal ceilings, no cross-copy resets,
accumulated work/impulse and all sensory/pose comparisons at common100us
times; chronological observed event brackets<=1us. Stop at first failed or
unresolved qualified comparison or resource limit. This proves mesh agreement,
not a continuum enclosure or absence of unsampled hidden crossings.

The15,000 unrefined Radau steps extrapolate to144s at the measured25us Python
cost, before event refinement. Do NOT launch that over the60CPU/90wall budget
or increase the budget. The next single implementation is compiled execution
of the SAME coupled Radau residual and bounded Newton/Krylov algebra. This is
needed to reach the accumulated-motion proof, not a new physical controller.

Authorized source: native/functional_body/radau.pyx (new compiled candidate
only) and native/functional_body/build.py (single builder, explicit module
selection; interval remains the existing default). Owner:A1. No import from
organism/NativeBody, no startup/schema/package change or live use yet. Existing
midpoint runtime source remains unchanged pending full numerical qualification.
Temporary reference/driver stays offline and authenticated by recorded SHA.

Translation boundary: same NativeBody model/data and integration predecessor
-> restored instantaneous native mj_forward law -> typed stage residual loops
and roundoff-derived centered Jv -> two-pass GMRES/projected least squares ->
actual nonlinear residual/backtracking -> exact same stage capture, positive
Radau work/impulse quadrature, finite/geometry/travel/supply checks -> endpoint.
Use the Python MuJoCo entry for mj_forward/mj_setState/quaternion integration
to preserve its native fatal-error translation; typed Cython removes array
construction and scalar/vector Python algebra, not physical force evaluations.
Keep projected NumPy least-squares initially to avoid a new linear algebra law.
Only observed measured cost decides whether this is enough; no native-speed
claim follows merely from compilation.

No new coefficients, convergence thresholds, relaxation, retained derivatives,
force caches, controller, body state or cognition. Same6Newton/16backtrack/
32Krylov execution caps; finite work count handed in by caller. Same1e-10
native nonlinear tolerance. Transient storageO(n*32+32^2), fixed per-step
diagnostic trace; no state retained in organism. Full integration predecessor
and model timestep restored on every failure, including supply/call refusal.
Successful endpoint retains original controls, force state and warm start as
before. Test-only evidence never uses the old custody header as a new law ID.

Freeze all source, review source-only, batch localized findings once, then
compile in isolated output using pinnedCython3.1.2,no-fast-math,fp-contractoff.
First proof compares unchanged saved Radau states/work/contact impulses/full
observations, actual residual, exact same-engine repetition and cold source
restore, zero-supply/call failure rollback. It must reproduce the archived
force control before new comparisons. No broad test until this passes. Raw
reference outcomes including event86 failure cannot be silently discarded.
Resource envelope2CPU/1GiB/60CPU/90wall, read-only AWS before/after and exact
process census remain mandatory. Any failure remains evidence, not admission.

05:50Z compiled candidate/source review: one localized diagnostic correction
was made before build (never report uninitialized/stale Krylov residuals).
Test-only proof retains actual and expected operands before a cold-reference
mismatch assertion. Runner success now requires actual completed proof and
all ratified reference comparisons, not just child exit0. Resource wording
corrected:60CPU-seconds/1GiBaddress-space limits are PER PROCESS;90wall-seconds
applies to the group. AggregateCPU is measured and must be<=60 for acceptance;
aggregate memory is NOT enforced/measured by maximum single-process RSS.
Do not repeat a stronger memory-cap claim. Two-core affinity remains inherited.

First compile failed before physical execution: Cython3.1.2 interprets
typed-double ** fractional exponent as potentially complex, refusing ordered
comparison at radau.pyx:127. Source-only review missed this compile boundary.
Receipt FB-01aj-radau-compiled-proof.json SHA995298e2ce16ef47312721be82c9fa7f7b911d8f7af52f3e5676b30280940a9d
preserves exact source/compiler failure, no body motion result. Build0.857swall,
0.847saggregateCPU,161432KiBsingle-processpeak. Child68218 and session92706
terminal; exact host group/command census no survivors. No broad tests ran.
Narrow compile correction: use libc real pow for positive MACHINE_EPS^(1/6)
and MACHINE_EPS^(1/3). Same operands/exponents/physical laws/limits; no complex
domain is needed or permitted here. Fresh frozen review before rebuilding.

AWS05:48:20Z->05:48:23Z keeps sole1559task/image/identity,counts1/1/0,
ticks2549801->2549808,errorsnull,durabilityfalse,CPU51.1383%,RAM3.0762%.
Existingclock-stalledALARM remains;other4OK. No push,Slack or live mutation.

### FB-01aj compiled algebra qualified locally — 2026-09-27 05:55Z

Compiled-source proof PASS, receipt FB-01aj-radau-compiled-proof-v2.json
SHA18307f40e5fdd9022c6e7688e0d9f799562b2c1e637d9a55bbfabd3140f415a8.
All7 retained reference observations restore exactly; candidate successors pass
all ratified reference comparisons. Fresh same-implementation repetition and
zero-supply/call-ceiling rollback are exact. Cross-implementation outputs are
numerically equivalent, not claimed byte-identical. The known100us event86
rate failure remains visible. No physical tolerance or law has changed.

Build10.710swall/10.697saggregateCPU/348412KiBmax-single-processRSS;
proof1.298swall/1.290saggregateCPU/168032KiBRSS.716stageforwards plus43outside
and1archivedstep; native-forward time0.060199s. Cost improvement is mixed:
event80 1/2/4piece stage wall0.013900/0.011041/0.024707s versus prior
0.009632/0.018512/0.029171s; first-call overhead is not separated. Event84
100us costs0.005719s and event86 costs0.009449s. No real-time claim.
Compiled unmounted artifact:/tmp/guala-body-radau.vnxyh_1c/python/
guala_body_radau.cpython-311-x86_64-linux-gnu.so,
SHA7dcfd6b997aa6311537cfa9ec830782a8c07f0d7494306e0a3c054545236c6d2.
Source SHAe8aab7e679773049067f501f8a707fdf2639651a2f84121d78c82d27b953534b.
Children69495/69536 terminal; exact host census no survivors.

Read-onlyAWS05:50:57Z->05:51:11Z keeps sole1559task/image/identity,counts1/1/0,
ticks2550174->2550209,errorsnull,durabilityfalse,CPU51.4055%,RAM3.0762%.
Existingclock-stalledALARM remains;other4OK. No push,Slack or live mutation.

Next single proof (independently reviewed design): paired common-genesis
250ms load+250ms release, with100us coarse and two half-step fine proposals.
No cross-copy reset, no reset of work/impulses at release, no local full-error
allowance misrepresented as global accuracy. Compare actual complete histories
at common endpoints<=100us apart, including48ms inside the SAME run. Refine
observed internal/contact/joint-domain changes to accepted endpoint brackets
<=1us; collocation stages are never called accepted physical trajectory states.
Corresponding physical contact/joint brackets compared across histories; no
claim of hidden-event exclusion or continuum enclosure. Stop at first failed
ratified group, unresolved correspondence, physical refusal or resource limit.
Keep accepted prefixes, full current/attempted states, accumulated work/impulses
and event evidence. No separate48ms trial or replay of passed prefixes.

Diagnostic execution budget is30,000 stage attempts (twice the15,000 nominal
whole histories), not a biological/accuracy coefficient. Stop at50CPU-seconds
inside the single proof process, leaving10seconds under its inherited60second
hard limit for failure serialization. Same90wall ceiling/2core affinity/1GiB
per-process address-space. Whole completion is NOT presumed within this budget;
budget failure is incomplete qualification, never a pass or hidden split run.
Native source will NOT be rebuilt for this observer. All numeric/safety limits
and frozen canonical cognition stay unchanged.

### FB-01aj whole-motion diagnostic evidence transport refusal — 2026-09-27 06:10Z

Reviewed driver ran once under freeze2cf1d736...f4b4ddb; child75882 exited1
in6.299s wall/6.296s CPU, no surviving PID/group. Its final evidence encoding
rejected numpy.bool_ in captured constraint-domain flags. The actual physical
stop reason and full trajectory were not serialized and are UNAVAILABLE, not
claimed passing. Native source/artifact remained unchanged. Failure retained in
FB-01aj-radau-whole-motion.json SHA08baee59845a046665a1046f42c9f88c1468cca7221fcf07489e1d12c60ce4ba.
This reporting bug survived source review; no numerical conclusion follows.

Bounded correction is evidence-only: existing plain_domain canonicalizes the
three captured domain tuples from native bool/int to Python bool/int without
changing comparison, force, state, trajectory, or acceptance. One same-budget
rerun is needed because the first child did not retain recoverable physics
output. No compiled rebuild, broad suite, new law, or hidden repeated success.
The earlier05:55Z section was moved to its chronological position; its content
and all prior evidence are preserved.

Read-onlyAWS06:09:18Z->06:09:27Z retains sole1559task/image/identity,counts1/1/0,
ticks2552842->2552861, checkpoint/cleanupnull,durabilityfalse. Existing
clock-stalledALARM remains;other4OK. No push,Slack or live mutation.

### FB-01aj paired whole-motion first physical accuracy failure — 2026-09-27 06:14Z

Reporting-only correction was independently source-reviewed, frozen and run once.
Receipt FB-01aj-radau-whole-motion-v2.json SHA256
0c6ce5ebb1b450e8d5a37ddd7cccdeac54ad134a11e596bb8a6b0a1b8afbe077.
The saved compiled-reference state/work/observation reproduces exactly. Two
fresh common-genesis histories advance without resets to19.2ms, then stop at
first ratified failure: right-foot specific force error0.14816675301907373m/s2
versus allowance0.061846197831344034m/s2, ratio2.3957293773034807.
Every other measured ratified group passes through that sample. Surface
position worst ratio0.000154931; joint rate0.115529; cumulative positive work
0.000020571; local tactile correspondence PASS (no physical contact pairs yet).
Intrinsic couple impulse remains UNQUALIFIED, not certified by empty contacts.
Both histories have17 observed domain changes and event correspondence PASS.
The last at19.02890625ms activates lower joint-limit index56 / native joint57;
no external or self-contact patch is present. Its exact causal contribution is
not yet established. No48ms,250msrelease or500ms completion claim is made.

Coarse accepted287pieces with95refinements; half-path470pieces/86refinements.
All757 accepted endpoints, predecessor hashes, raw successors, per-piece work,
actual remaining supply, complete event brackets, last solver operands and
both current full observations are retained. No failed-prefix reset or
archived midpoint state was substituted for either history.
939stage attempts;43307 probe force forwards (constructor/restore calls are
outside this count),3.021067s native-forward time. Wholechild6.735409swall,
6.707927saggregateCPU;167720KiBRSS. Diagnosticbody19.2ms is NOT real-time.
Child77339/session81393 completed with no survivor in final host group census.

Local correction command preflight also caught an off-by-one source-line index
before writing the rerun helper; zero file mutation occurred. Verified line
positions were then used in one whole-file replacement. No test was launched
by the failed edit guard. Reporting failures and this guard remain disclosed.

Read-onlyAWS06:12:34Z->06:12:43Z retains sole1559task/image/identity,counts1/1/0,
ticks2553288->2553309,checkpoint/cleanupnull,durabilityfalse. CPU51.0731percent,
RAM3.0762percent. Existingclock-stalledALARM persists;other4OK. No push,Slack,
production write, cognition/food/caretaker change, or numerical-tolerance change.

Single next item: explain this right-foot inertial discrepancy using retained
19.1ms predecessors and exact force law, distinguishing incoming-history error,
last-step truncation and force/warmstart dependence. No full-history replay,
material retuning, new semantic mechanism or broader suite. The numerical
candidate stays compiled-unmounted; fullbody goal remains ACTIVE/incomplete.

06:16Z source/receipt attribution review (no new physical execution): next
single map is2x2 over the final100us using each retained19.1ms predecessor,
its complete actual state and remaining supply. One100us versus two50us
steps to the SAME saved19.2ms endpoint,6totalRadau steps. Archived coarse
and half successors must reproduce before interpreting the two new cross
combinations. No common-state reset of earlier histories or full replay.
Record vector decomposition, not sum of norms:
A(C,100)-A(F,50)=[A(C,100)-A(C,50)]+[A(C,50)-A(F,50)], and its opposite.
This separates final-step mesh and inherited-state sensitivity; neither
constitutes a continuum error bound.
At each archived endpoint perform three scratch zero-time force evaluations
with retained, zero and other-lane warmstart. Physical pose/velocity/control/
time fixed; no work debit or lived-state mutation. Retained warmstart must
reproduce archived feedback first. Preserve specific-force and qacc vectors,
constraint state/force, solver iterations and M*a-qfrc_smooth-qfrc_constraint;
restore exact input bytes afterward. This tests native force-solve sensitivity
not excluded by the small outer Radau residual. No new solver, physical law,
tolerance, material coefficient or production exposure. Use existing same
resource/health envelope with no native rebuild,6Radau steps+6scratchforces,
explicit setup/restore accounting, and exact first-failure operands.

### FB-01aj right-foot inertial error causally localized — 2026-09-27 06:25Z

Previous goal turn was PROGRESS5fd4152cb; this turn continues the same body-only
numerical seam. Source/ABI/receipt hashes and clean body branch were rechecked.
Requested: preserve ratified mechanical and sensory accuracy without changing
forces. Reality: Radau remains compiled-unmounted, full-motion check fails.
Conflict: YES with claiming complete accuracy; no authority to weaken limits.
No extension to cognition, food/caretaker logic, material parameters or live
runtime. Reduction: numerical articulated mechanics only; this probe does not
evaluate DSF joint fields or cognition. Next is generic error-controlled mesh
selection using existing channel limits, not a semantic rule or force change.

One reviewed6-step/6zero-time-force attribution map completed; receipt
FB-01aj-radau-force-attribution.json SHA256
336d81a0d4a081e24e0dbbba2fb2b75658bdafedc5991407c5898ebb3d4e81e6.
Both original whole-motion successors reproduce exact state/work/supply/feedback.
From each retained19.1ms input, compare100us versus2x50us to the same saved
19.2ms output time. Vector decomposition closes exactly, without adding norms:
observed discrepancy norm0.14816675301907373m/s2;
coarse-input mesh term0.14817316432342098m/s2;
inherited-state term under same half-step mesh0.000006411939213480448m/s2.
Opposite decomposition agrees (mesh0.14817302101122737, inherited0.000006268640625927764).
Thus the final100us mesh dominates this measured discrepancy. This is numerical
attribution, not a bound against the exact continuum or a whole-motion pass.

At the two archived endpoints, retained/zero/crossed warmstart force evaluations
keep physical time/state/control unchanged and restore original integration
bytes exactly. Retained feedback reproduces exactly. Largest changed warmstart
specific-force difference8.674316223802008e-13m/s2; largest native dynamic
residual |M*a-qfrc_smooth-qfrc_constraint|7.167599846980011e-13. These operands
exclude meaningful force-solve/warmstart sensitivity for this discrepancy.
Native joint57 is guala/right/shin/knee, unchanged solref[.0002,1]. No physical
contact pair is present; sampled limit-event brackets already matched.

326Radau forward calls plus24setup/restore/scratch forwards =350total.
0.020287snative-forward time; child0.863051swall/0.855817saggregateCPU,
165848KiBRSS. Session67933/child82191 terminal; exact host census PID82705
confirms zero survivors. One initial read guessed absent installed .pyi/test
paths; no file changed or model ran. File discovery resolved authoritative
introspect/functions.py and source/include/mujoco/mjdata.h. Do not repeat those
absent-path reads. A sandbox ps view is NOT host process evidence; explicit
escalated read-only host census is required (now performed and recorded).

Read-onlyAWS06:24:53Z->06:24:56Z retains sole1559task/image/identity,counts1/1/0,
ticks2555000->2555008,checkpoint/cleanupnull,durabilityfalse,CPU51.3282percent,
RAM3.0762percent. Existingclock-stalledALARM remains;other4OK. No push,Slack,
production mutation, native rebuild, material/tolerance change or whole replay.

Corrective direction: reuse existing interval._close physical channel/work/
impulse criteria and dyadic full-versus-two-half selection for Radau, committing
only accepted fine motion and debiting only that motion. Same complete-state
rollback and left-coarse-result reuse; numerical convergence and sampled event
boundaries remain checked. This closes the measured absent mesh-admission seam;
local acceptance alone will NOT be advertised as accumulated-history accuracy.
Whole common-genesis qualification, gravity/integration/restart/performance and
production delivery all remain open. No broad test or scene-specific tuning.

06:29Z source-only correction contract confirmed by independent body reviewer:
Radau trials may use the existing generic dyadic admission transaction and
unchanged interval._close physical criteria. This is numerical approximation
already authorized for body mechanics, not a new physical force or cognition.
Preserve stage-based<=1us observed-domain brackets, exact full-state/supply/
timestep-keyed left-trial reuse, recomputed right branches after a changed
accepted left state, all-native-forward/trial limits, complete interval rollback,
and commit only fine-state work/impulses once. A rejected coarse/fine proposal
must not debit chemical reserve or heat or enter persisted body custody.

Next executable implementation is one unmounted numerical admission method,
then the saved19.1->19.2ms proof on both authenticated inputs at nominal100
and50us. Existing raw one/two-step receipt supplies the falsifying control:
unchanged _close must reject its100us error. Record actual accepted grids and
all rejections; no assumed sufficient step size. Exact repetition and raw-state
continuation can support this local proof, but they are NOT production cold
restart or permission to wrap new-law states in predecessor custody headers.
Energy and call-budget refusals must restore the complete interval predecessor.
If schedules collapse to identical grids, label agreement determinism evidence,
not independent continuum convergence. Full common-genesis histories are still
required afterward and cannot be reset at this saved boundary for that claim.


### FB-01aj local Radau admission implemented; focused proof contract — 2026-09-27

The single numerical correction is now implemented, still unmounted, in
RadauProbe.admit. Existing stage equations, physical force law, solref, channel
accuracy limits and interval._close are unchanged. One step is compared with
two halves; only accepted fine state/work/impulses are retained. Captured
stage/endpoint domain changes require <=1us fine pieces. Rejected numerical
trials restore their predecessor; whole-interval refusal restores the exact
initial integration state and model timestep. Left coarse-result reuse checks
exact predecessor/time bounds/supply. The right branch is recomputed after
accepted left changes. Native-force and proposal limits refuse, never invent
motion. Diagnostic state is bounded by the caller proposal budget and is not
organism memory, persistence custody or motor decision authority.

Frozen source SHA71949bc22e571e282cc757ad6c7ef356f715709b5f6ed0270f471cfb8ee3e4b4.
Focused proof /tmp/a1-body-radau-admission-proof-20260927.py SHA
 a1551c9128396a9ba5a2e578064d07d20114236c5b859120833b4c282c532894:
- Authenticate retained attribution evidence; unchanged _close must reject
  both archived100us step errors. No predecessor fabrication or earlier replay.
- Both authenticated19.1ms inputs, nominal100/50us; report actual accepted
  grids and every rejection. Compare all existing physical channel groups.
- Exact repeat; uninterrupted versus raw restored next interval. This is raw
  scratch continuation, explicitly NOT runtime cold restart or new-law custody.
- Zero work supply, proposal budget1 and force budget1 must refuse with exact
  whole-state/timestep rollback. Include all setup/restore forwards in counts.
Proposal allowance162 derives from3 trials per binary representability level;
it is an offline diagnostic bound, not a physiological coefficient. Maximum
refinement depth53; unrepresentable subdivision refuses. The unchanged outer
operational envelope caps each process60sCPU/1GiBAS, whole group90swall,2cores;
aggregateCPU is checked postrun and aggregate memory is NOT claimed enforced.
One build and this proof only, with read-only AWS pre/post and exact child
process cleanup; no broad suites, production changes, push or Slack.

A source replacement preflight rejected an expected hash that included one
extra trailing newline removed by apply_patch. No wrong source was changed.
The guard now authenticates actual on-disk bytes. An unmatched lowercase
sprint glob returned an absent-pattern error during a read; the exact known
sprint path is now used. Neither failed read/guard executed a physical model.

Exit is local numerical admission evidence only. Identical accepted grids are
determinism, not independent continuum convergence. Whole common-genesis
motion, gravity/world mounting, runtime restart, performance and live delivery
remain open. Rejected trials do not consume chemical reserves or heat, and no
cognitive/body custody law is modified by this scratch numerical transaction.


Source-only independent review found two LOCALIZED issues, no architecture
finding. One correction batch: exact canonical<f8 bytes replace numeric array
equality in new admission predecessor/rollback guards (signed zero matters);
raw-continuation results are recorded incrementally before each attempt so a
later failure cannot erase completed evidence. No equations or scope changed.
Final source SHA6e2857bf7fd1fdeeff3ab3e2289f1f98b6ee8873dea75b535cabb2ad9cd131d8;
proof SHAec8ee86ec12f9560a4282a4af5139bdad9df2bb5d8b16e44c95a861a7901362b.
No compile/model execution has occurred during source review or this batch.


### FB-01aj local Radau admission proof passes — 2026-09-27 06:48Z

PROGRESS: reviewed generic local-admission correction implemented and compiled;
no runtime mounting, changed force law, relaxed tolerance or cognitive change.
Final frozen candidate09bc36832824167c44a5f2026a50e1b2de585bd3fb735d3d97b168895e808449
passed independent confirmation of the two localized source/evidence fixes.
One build and one focused execution, not a broad regression replay.

Receipt docs/evidence/FB-01aj-radau-admission-proof.json SHA256
0868ef58ef81aa32a5b1728f25ec73e0a8f423006d9572ef065c42070dd3b4ce
retains exact source, runner, compiled artifact identity and complete raw proof.
Artifact /tmp/guala-body-radau-admission.as3w3bwe/python/guala_body_radau.cpython-311-x86_64-linux-gnu.so
SHAd5bfcb453693668e9a9829ab1f4d98c579cb034cc3ea237df4476f1031f205cf.

Both archived unadmitted100us successors fail unchanged _close as required.
For each retained19.1ms predecessor, nominal100us rejects once, uses8trials
with1exact left reuse, and accepts4pieces of25us. Nominal50us uses6trials,
no rejection, and accepts the identical4piece grid. Same-history successors,
feedback and work are exactly identical. This is deterministic local admission,
NOT independent continuum convergence. Cross-history right-foot discrepancy is
6.431040216404763e-6m/s2 against0.061863406302141315m/s2 allowance (largest
ratio0.00010395548). All ratified measured groups pass; intrinsic couple impulse
remains explicitly UNQUALIFIED. No global accuracy claim.

Fresh repeated admission is exact. A genuinely uninterrupted accepted engine
and separate raw-state-restored engine produce identical next100us successors;
both use8trials/4accepted pieces/1rejection. This proves raw scratch continuity,
NOT production cold restart or permission to reuse predecessor custody headers.
Zero work supply, proposal budget1 and force budget1 each refuse and restore
whole integration-state bytes and model timestep exactly. Rejected trial work
is excluded; no chemical reserve or heat debit occurs in this offline probe.

2541probe forwards+52setup/restore/etc=2593total. Native-forward0.163277s;
physical proof0.404503swall/0.407960sCPU. Whole child1.097423swall,
1.093962saggregateCPU,154192KiB peakRSS. Build13.453681swall/13.430899s
aggregateCPU,357976KiB maximum single-processRSS. No aggregate-memory claim.
Session94851/build90637/proof90691 terminal; exact host census91007 confirms
no children/orphans remain. A result-display command printed all per-channel
metrics and was output-truncated; compact field selection corrected that read.
No model was rerun and the complete authenticated receipt was unaffected.

Read-only AWS06:47:35->06:47:52Z: same sole1559task/image/organismidentity,
counts1/1/0,ticks2558277->2558318,checkpoint/cleanupnull,durabilityfalse.
CPU51.3604percent,RAM3.0762percent; existingclock-stalledALARM persists,
other4OK. No production writes, push, Slack or G1-source changes.

Close only the measured absent local numerical-admission seam. Single next
item: exercise this same compiled admission across the original uninterrupted
common-genesis loaded/released trajectory and compare accumulated physical
outputs/cost, without resetting earlier history at19.1ms. Preserve exact first
failure and accepted prefixes. No rebuild unless a new source defect demands
it; no reopening the completed saved-state proof. Full-body gravity/world
integration/runtime restart/resource qualification and production stay open.


### FB-01aj uninterrupted admitted-motion contract — 2026-09-27

Previous turn was PROGRESS (local commit c5df9ec70, passing bounded admission
receipt0868ef58...b4ce). Continue FB-01aj; do not reopen that saved-state seam.
Requested: unchanged-force whole-motion accuracy and measured cost. Reality:
compiled-unmounted local admission only. Conflict: YES with full-motion claims.
No cognition, DSF, care, food, optics, anatomy, force/tolerance changes or live
mounting. Reduced numerical body mechanics only; full joint DSF fields and
cognition are not evaluated, not altered. Single next action: one bounded
uninterrupted paired loaded/released trajectory using the compiled admission.

Use the original authenticated zero-gravity mechanical bench, common genesis,
same control and supply. Nominal100us and50us lanes independently advance using
RadauProbe.admit; compare existing physical/sensory/work/contact limits every
common100us endpoint. Retain complete accepted prefixes and separate observed
event brackets, not only final agreement. No reset at19.1ms or after any other
boundary. Targets remain48ms,250ms loaded, then250ms unloaded, not smaller
replacement success criteria. Subsample agreement is not continuum enclosure.

Offline observer wraps the actual primitive step only to retain before/two
stage/after domains and associate accepted fine pieces by exact predecessor,
endpoint and supply. It does not select/refine steps or change physical state.
Only successful admission contributes work and impulse; failed admission keeps
last accepted interval state and exact failure operands. Existing stage-only
unresolved events remain a qualification failure. Capture all native-forward
calls, observer overhead, trial counts, CPU/RSS and accepted grids. Clear trial
traces between common intervals; retain only necessary accepted history and
last failure, bounded by diagnostic duration/trial/CPU limits. No production
custody decoder is applied to new-law states.

The prior cost already warns that real-time operation is NOT established.
One diagnostic is limited to50sCPU (60shard),1GiBAS,2cores,90swall and30000
primitive proposals. A budget stop is explicitly incomplete, never a full
500ms pass. Retain completed history so no identical run is restarted to hide
failure or extend limits. No rebuild; source/module hashes are checked before
and after. Read-only AWS pre/post and exact process cleanup are mandatory.

Source-only reviewer confirmed one LOCALIZED proof-accounting-order finding:
a successful native admission must publish returned work/impulse/supply into
the offline record before any fallible event reconstruction. Corrected once;
interval outputs retained immediately and cumulative fields assigned together.
No native/force/admission source changed. Reviewer reported event keying,
canonical domains and independent-history flow consistent; review was stopped
after that bounded finding to avoid prolonging inspection. Root reverified
unchanged original fingerprint before edits; final delta confirmation follows.


### FB-01aj uninterrupted motion exposes event-resolution and cost limits — 2026-09-27 07:07Z

PROGRESS: one bounded continuous-history diagnostic completed with a physical
qualification failure, preserved intact. No native source change or rebuild.
Independent source review identified the one local accounting-order issue;
after that correction the primary agent performed final source/hash/AST-order
confirmation, with fingerprint52b851f28aa457dadd61706bc423facbf97e4ed7148a8c72d58ba78c859d86b3
verified before/after. The reviewer was stopped rather than allowing the narrow
confirmation to prolong the turn. Do not claim independent final approval.

Receipt docs/evidence/FB-01aj-radau-admitted-motion.json SHA256
5dbde1bf559b6218487a42113265e216d9c4629de7837632baa20c61f651c73b
retains exact proof/runner, both original-genesis histories, all1786accepted
pieces, first failure operands, stage-domain evidence and resource envelope.
The histories passed the previous19.2ms acceleration failure with local
admission. At20.4ms all ratified sensory, pose, motion, work and tactile groups
still pass. Largest ratio0.53513935 is right-foot acceleration:
error0.02280292821m/s2, allowance0.04261119716m/s2. Intrinsic couple impulse
remains UNQUALIFIED; no new authority is inferred from other passing fields.

Stop is observed-event correspondence at lower-limit index56/native joint57
(guala/right/shin/knee), reactivation after release at~20.082ms. Coarse event
bracket[20.3750000000,20.3753906250]ms; half bracket[20.3742187500,20.3750000000]ms.
Each is narrower than1us, but their union spans1.171875us, exceeding the required
worst-case1us bound. This proves INSUFFICIENT event-time evidence; it does NOT
prove actual crossings differ by1.171875us. No physical contacts are present
there.26observed event rows per lane. Coarse634pieces/113refinements/1168trials;
half1152pieces/94refinements/1915trials. Neither48ms nor250/500ms was completed.

3083primitive trials;120353probe forwards+1114outside=121467total. Native force
7.940227s; observed primitive13.547791s; observer metadata0.817019s; diagnostic
15.620962swall/15.618119sCPU. Whole child16.392051swall/16.376923aggregateCPU,
204840KiBRSS. Thus CPU cost is itself unqualified: even native forces alone cost
~194.6wall seconds per accumulated simulated second across these two histories.
This is a local benchmark ratio, NOT live-production timing or a general
constant extrapolation. Removing observer output alone cannot fix that cost.
Do not restart the500ms test unchanged or merely raise its diagnostic budgets.

Session37183/child97439 terminal; exact host census97768 confirms no survivor.
Read-only AWS07:05:54->07:06:13Z retains sole1559task/image/identity,counts1/1/0,
ticks2560984->2561031,checkpoint/cleanupnull,durabilityfalse,CPU51.1308percent,
RAM3.0762percent. Existingclock-stalledALARM persists;other4OK. No production,
cognition, food/care, force-law, threshold, push or Slack changes.

Single next bounded analysis: use the two retained event segments to distinguish
wide sampling brackets from genuine timing separation without replaying either
history. Native _Stages.evaluate already provides the actual hinge qpos/qvel
at Radau nodes1/3and1. Its hinge path is the integrated collocation polynomial
q(theta)=q0+h*((3theta/2-3theta^2/4)*v1+(3theta^2/4-theta/2)*v2).
This reproduces A rows(5/12,-1/12)and(3/4,1/4); joint-limit boundary remains
exactly range_lower+margin. A two-segment diagnostic can first reproduce each
saved accepted successor exactly, then inspect that numerical path's crossing,
including arithmetic uncertainty. Do NOT replace uncertainty with midpoint
estimates, relax1us, reset histories, or call the polynomial an enclosure of
the exact continuum. If event evidence can be tightened faithfully, keep it
separate from the remaining accumulated-state and serious force-call-cost
qualification. The next source correction must follow those operands, not a
new scene-specific tuning or cosmetic throughput claim.

Full goal remains ACTIVE/incomplete: body/world mounting, gravity, runtime
custody/restart, performance and live production are still not qualified.


### FB-01aj saved-segment event localization contract — 2026-09-27

Continue same numerical seam from local commit171425b66; previous turn was
PROGRESS (complete failing histories and measured force-call cost). No source
solver, acceptance threshold, physical coefficient or production edit. Requested:
resolve whether the1.171875us bracket union is coarse observation or actual
numerical-path separation. Reality: both narrow brackets pass locally but their
combined bound fails. Conflict: YES with a whole-motion pass. Do not extend
cognition, DSF, care, food, or new-law custody. This is reduced numerical-body
trajectory analysis; no joint DSF field or cognition is evaluated or altered.

One offline diagnostic replays exactly the two already accepted crossing
segments from authenticated raw predecessor bytes and exact supplied work in
the final admission receipt. No whole-history replay or new body header.
Require exact original successor, work, stage domains and endpoint clock before
using actual captured qpos/qvel at collocation nodes. Mapping limited-index56
to native joint/qpos/dof addresses comes from that loaded body's anatomy, not
hardcoded offsets. Range_lower+margin remains the actual transition boundary.

For each hinge path Q(theta)=q0+h*((3theta/2-3theta^2/4)*v1+
(3theta^2/4-theta/2)*v2), use exact rational arithmetic over the recorded finite
binary64 operands in this OFFLINE observer only. It does not replace body
numerics or re-enter organism state. Reconstruct the unique quadratic through
actual q0,q(1/3),q(1) too. If node construction discrepancies are delta1,delta2,
the two numerical polynomials differ by at most(9/8)|delta1|+|delta2| on[0,1],
from their Lagrange bases. Report that bound and both constructions; it is
construction-rounding sensitivity, NOT an ODE truncation-error enclosure.

Require a strictly decreasing crossing, outward endpoint signs even under that
rounding envelope, and bounded bisection (at most binary64 mantissa bits) using
exact comparisons. Return rational and outward-rounded physical time bounds;
compare their union with the unchanged1us limit. No guessed midpoint times.
If signs/uniqueness/bounds cannot be established, report inconclusive/failure.
Success establishes timing only for these numerical segments; it cannot turn
all earlier whole-motion, continuum, gravity, runtime restart or cost gates green.

Two Radau primitive calls only, existing binary, explicit total-forward bound,
ordinary bounded child resources/read-only AWS pre/post, exact child cleanup.
Save failed operands and restore input state even on failure. No build, broad
suite, push, Slack or live action. Computational-parsimony work remains separate:
localization may avoid unnecessary force reruns, but it does not erase measured
native-force cost or permit observer removal to be called a real-time solution.


### FB-01aj numerical crossing localized without a history rerun — 2026-09-27 07:29Z

PROGRESS: the specific 20.4 ms event-timing uncertainty is resolved for the two
retained numerical paths. This is NOT whole-motion or continuum qualification.
One independent frozen source-only review passed for proof SHA256
3bde699005222bab323f0d8fa3899af8b2bdcee38b204e7101f97da076d1e429
and runner SHA256
d587610b9b523085a60a3fd8ff59c57efe6dc44705777eabab08d4c5cbd9519d.
Tree fingerprint ab3134b3a38175a43c77bad95031b4a07777438b6971e11beccfc951612dde33
matched before and after execution. Native solver and all physical coefficients,
accuracy tolerances, authority boundaries and runtime source remain unchanged.

Receipt docs/evidence/FB-01aj-radau-event-localization.json SHA256
c8c14d5b35c54c9a09ebc1ca6bb1a4cd71a8c3a7eba72c0480f494d5794f7a9a
preserves exact proof/runner, rational brackets, actual replayed stage operands,
raw predecessors/successors, hashes and operational envelope. Each of the two
saved accepted segments reproduced original successor bytes, work, stage and
endpoint domains and clock exactly; each input/timestep was restored exactly.

The right knee lower-limit numerical activation occurs within these outward
time brackets in seconds:
- Coarse history: [0.020375313118024580, 0.020375313118024582].
- Half-step history: [0.020374518290786726, 0.020374518290786730].
Their exact-rational combined width is approximately 0.7948272378543825 us,
below the unchanged 1 us bound. The prior 1.171875 us sampled bracket union was
insufficient observation, not proof of excessive actual numerical separation.
Uniform differences between velocity-integrated and rounded-position numerical
polynomials are bounded by 4.244289898377132e-25 rad and
3.915746978957111e-25 rad respectively. These bounds are NOT continuum solution
error or a bound on arbitrary floating-point dense-path evaluation.

Exactly two primitive replays: 38 stage force calls plus 8 setup/restore calls.
The numerical diagnostic used 0.126151 s wall / 0.127993 s CPU; complete child
used 0.782770 s wall / 0.779289 s aggregate CPU, 190360 KiB maximum RSS.
Session 19400 and owned child/group 5568 are terminal; separate exact host census
confirms no survivor. No build, broad test suite or full trajectory rerun.
Read-only AWS 07:26:20 -> 07:26:23Z retains sole task1559, same task/image/identity,
ticks2563983 -> 2563991, checkpoint/cleanup null, durability false. Existing
clock-stalled ALARM persists while these samples advance; other four alarms OK.
CPU51.3965 percent average / RAM3.0762 percent. No live change or health repair.

Cheap reanalysis of the existing admitted-motion receipt, with NO simulation,
locates a material compute cost: the last 29 recorded primitive proposals used
903 force calls; 161 centered finite-difference Krylov directions account for
644 of them (two perturbations, two stages each). No line-search halvings occurred
in that retained batch. The accepted prefixes alone consumed 24198 calls across
634 coarse pieces and 39688 calls across 1152 half pieces. Median accepted piece
widths were 50 us and 25 us. These retained observations do not establish a
universal cost law or predict a speedup from any unimplemented change.

Single next item: source-map a bounded numerical correction to repeated force
evaluation, using this measured cost rather than rerunning unchanged histories.
Any correction must solve the same physical equations with the same residual,
observable and event limits; do not soften joints, remove sensors, bypass force
checks, invent success, or redesign cognition. Numerical event localization is
verified here for two hinge segments only; generic use and later accumulated
motion remain unqualified. Gravity, intrinsic couple impulse, runtime custody/
restart, world mounting and real-time cost remain open. No push, Slack, production,
food, caretaker, DSF or cognition change. Full body objective remains ACTIVE.


### FB-01aj bounded inverse-secant numerical correction contract — 2026-09-27

Previous goal turn PROGRESS: commit622d55154 resolves the two retained numerical
knee-crossing times without changing physics. This item addresses the separately
measured force-call cost, not cognition, food, new anatomy or production. Requested:
solve the same coupled body equations within the same accuracy limits at lower
cost. Reality: 644 of 903 force calls in the retained last proposal batch estimate
directional derivatives. Conflict: YES with claiming affordable body operation.
No extension of physical softness, thresholds, controllers or production custody.
This is authorized body-only numerical approximation; no DSF field is evaluated,
flattened or replaced by the numerical residual norm.

The isolated radau.pyx candidate retains the exact evaluate() stage-force and
SO(3) residual implementation, stage work/impulse quadrature, ordinary local
admission checks, physical refusals and endpoint feedback. Only its nonlinear
correction algorithm changes. In scaled variables z=x/S, initialize H_0=I (the
zero-duration residual Jacobian limit), propose delta_z=-H_k R_k, and retain the
existing sixteen-division line search requiring measured true-residual decrease.
For actual accepted differences s=delta_z and y=delta_R, use Broyden's second
inverse update H_next=H+(s-H*y)*y^T/(y^T*y). Implementation normalizes y by its norm
to avoid squaring a small denominator and stores rank-one vectors. An approximate
inverse proposes a trial only; the unchanged full force residual must converge
to the existing model tolerance, and all physical checks remain authoritative.

Storage is bounded by two 32-by-n arrays (n=146 here), plus existing stage state.
Thirty-two secant iterations and sixteen line divisions are diagnostic refusal
ceilings, not physical parameters or convergence guarantees. No restart, rank
truncation, across-step derivative cache, heuristic damping, residual acceptance
relaxation or alternate-solver fallback. Nonfinite/zero-update degeneracy and
failed decrease refuse; ordinary numerical admission may subdivide as before.
The inverse is discarded at every primitive step and never enters body memory.
Raw rollback verification now compares canonical bytes, including signed zero.

The primary numerical reference is the inverse-update identity documented at
https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.broyden2.html .
Kelley's treatment explicitly warns that secant directions need not be descent
directions: https://epubs.siam.org/doi/10.1137/1.9780898718898.ch4 . Neither source
guarantees this body will converge or run faster. No new library dependency is
introduced; code implements the displayed bounded update and measured refusal.

Single focused proof: four authenticated retained predecessor states, never a
whole history. Three are the published event80/84/86 contact-regime states; one
is the admitted-motion predecessor at20.3ms. Run the unchanged compiled Krylov
control first and require its three archived successors/work/observations exact.
Then run the new compiled candidate on identical inputs and physical intervals;
compare all ratified pose, rate, sensory, work and contact channels, preserving
the explicit intrinsic-couple-impulse qualification gap. Actual stage domains
must agree. Require fresh raw-input repeat and exact zero-energy/force-budget
rollback. Report paired call counts and timing separately; lower calls is not
real-time or accumulated-motion qualification.

At most six candidate primitive proposals plus one one-call refusal. Each main
primitive has maximum 5+32*2*16=1029 stage forwards; outside setup/restore has its
own seventy-call cap. Existing2core/60CPU/1GiBAS/90wall child limits, offline socket
denial, read-only AWS pre/post, exact child census, source freeze and independent
source-only review remain. One build and one control/candidate comparison only.
No broad regression rerun, numerical threshold change, push, Slack or live writes.
If it fails convergence or does not reduce measured work, preserve the result
and do not promote it as the performance solution. Full body goal remains open.


### FB-01aj fourth-control classification correction — 2026-09-27 07:50Z

The single build succeeded in12.72s; no rebuild is needed. The unchanged Krylov
control reproduced all three archived contact/release successors exactly, then
correctly refused the100us proposal from20.3ms. The harness incorrectly assumed
this was an accepted primitive. The earlier admitted-motion receipt already
records that exact coarse refusal followed by37 adaptive proposals and16 accepted
fine pieces. This is a harness reference-selection mistake, not a production
incident or proof that the new solver failed: the candidate has NOT yet run.
The negative control and exact rollback are retained in
FB-01aj-radau-secant-proof.json SHA256
aafdd48393eb2b66d6162bd16973f7935c940d404d18f8d0396b0c65cbed5411.

Corrected bounded continuation reuses the three completed positive control
records and the already-authenticated fourth ADMITTED endpoint/work/observation.
No old successful control is replayed, no failed receipt rewritten. The candidate
will run three matched primitives and the fourth100us interval through ordinary
admit(), using the pre-existing162-trial representability cap. The overall6174
stage-forward budget and70 outside-forward cap remain unchanged; resource limits
are not raised. Failure still preserves raw state/work before sensor collection.
Positive energy and one-call refusal controls use the first known-successful
primitive, not the known-refused coarse proposal. The original coarse failure
remains explicitly disclosed.

Compare physical endpoint channels for all four states. Exact stage-domain
comparison applies to the three common primitive paths only; the fourth can use
its own adaptive mesh and its cross-history event timing remains UNQUALIFIED.
Force-call speed comparison covers only the three positive matched primitives;
there is no new claim of fourth-case timing improvement or whole-motion speed.
A complete failure or higher cost remains a recorded rejection, never a pass.
Same compiled candidate module cbe9c22083b77731b65c3222e51789c28edb97ceac4cff4edf09be1bee2d02cc;
no force, tolerance, algorithm, body source or production changes in this correction.

### FB-01aj saved-state secant comparison passes; full-motion cost still open — 2026-09-27 07:58Z

PROGRESS, continuing FB-01aj. Requested architecture: the same bounded body
mechanics at lower numerical cost. Current code reality: compiled-unmounted
inverse-secant correction now passes four retained-state physical comparisons.
Conflict: YES with any claim that the complete body is qualified or real-time;
those gates remain open. Do not extend cognition, food, caretaker, physical
softness, accuracy limits or production custody. Single next item: bound the
new solver's accumulated-motion accuracy and cost using retained evidence,
without replaying the unchanged old controls or raising their budgets.
This is body-only numerical approximation, not DSF evaluation; no DSF field
is flattened or replaced. Gravity, full motion, intrinsic couple impulse,
world mounting, runtime restart and production remain unqualified.

Frozen independent source review passed before this continuation. Fingerprint
c3cb4b7a608bc7940461b4d9a9a35b84bf7df9fae464f04692f2d08727316bb3
matched before and after execution. Proof SHA256
273dee52ff18afa6993c09b83846d334a61f1fa5f9e83ac5122417c875fa0140;
runner da97276c87e8161f2f132614be204f4cb3258edefbb71cbf8ff2ef6a3fbf0989.
Receipt docs/evidence/FB-01aj-radau-secant-proof-v2.json SHA256
436deba429bb4f40588f721870b8ea3aa436a5f4b16212c2b09eaac2fc3e6a2f
retains the loaded source, all measurements and operational envelope.

On the three common successful primitive steps, native force calls fall from
49/61/81 to 23/25/31: 191 to 79 total, a 58.64 percent reduction in these cases.
All ratified endpoint channels pass unchanged limits; actual stage domains
match. This is NOT a 58.64 percent whole-body wall-time speedup. The fourth
100us interval uses ordinary adaptive admission and passes against the earlier
authenticated admitted endpoint/work/sensory reference, using 583 force calls.
Its cross-history event timing and speed comparison remain unqualified.

Fresh replay is exact. Zero-energy and one-forward-budget refusals restore
raw input bytes and timestep exactly. Total proof: 708 solver calls including
the one-call limited refusal, plus 40 outside calls: 748 calls altogether.
Numerical proof wall0.251834s / CPU0.251925s; entire child wall1.035133s /
aggregate CPU1.028843s, maximum single-process RSS174952KiB. Resource ceilings
unchanged; 1GiB address-space enforcement is per process, not aggregate RAM.
Session25986 and child/group15867 are terminal. Exact host census finds neither
the PID nor a group survivor. No rebuild, old-control replay or broad suite.

The first harness reference-selection failure remains preserved in the prior
receipt. Never claim the fourth coarse old primitive succeeded. An inspection
command also initially treated the compressed measurement envelope as a direct
JSON object; decode and verify its raw length/SHA before extracting bounded
summaries. Do not print complete channel maps or encoded states during review.

Read-only AWS07:53:27->07:53:30Z retains sole task1559, same task/image/identity,
ticks2567892->2567900, checkpoint/cleanup null, durability false. Existing
clock-stalled ALARM remains despite advancing samples; other four alarms OK.
CPU51.2825 percent average, RAM3.0640 percent. No live health repair claimed.
No push, Slack, production or G1-owned cognition/food/caretaker changes.
The complete functional-body goal remains ACTIVE and incomplete.

### FB-01aj changed-solver sustained-motion qualification contract — 2026-09-27

Previous turn PROGRESS: local commit8f3f47fb2 reduced force calls on three matched
steps while preserving physical limits and exact refusal rollback. Continue
FB-01aj, not a reopened cognition or body-authority design. The compiled solver
now needs accumulated-motion evidence; saved single steps cannot supply it.

One no-build offline proof will reuse the earlier paired common-genesis motion
contract: nominal100/50us histories, unchanged benchmark force/anatomy/supply,
pose/rate/sensor/work/tactile limits, intended48/250/500ms checkpoints, and real
effort removal at250ms if reached. Stop on the first actual accuracy, event,
numerical or resource failure. Keep30000 primitive/162 local-trial allowances,
50CPU-second internal deadline,60CPU/1GiBAS-per-process/90wall group limits,
two-core affinity, offline socket denial and read-only AWS pre/post snapshots.
No old solver/control rerun, build, tolerance increase or changed physical law.

The observer carries actual start and Radau stage hinge position/velocity
operands on changed hinge segments only. It uses the already-proven integrated
quadratic and rounded-node polynomial envelope to localize monotone lower/upper
activation/release times with exact rational diagnostic arithmetic. Validate
the helper first against both authenticated prior segment enclosures and
sign-reflected polynomial cases, without replaying mechanics. Unsupported
nonmonotone or nonbracketed segments explicitly refuse; no guessed crossing.
Non-hinge contact events retain conservative sampled intervals. Compare exact
time-enclosure unions to the existing1us bound; this does NOT enclose continuum
truncation error or certify contact behavior between all sampled nodes.

The observer never changes admission, effort, integration mesh or body state.
Raw accepted successors/work are recorded before subsequent evidence checks;
all prefixes and first failure remain in one receipt. Source and compiled
identities must match before/after. Same numerical source and ABI as8f3f47fb2.
Independent source-only review precedes this single bounded execution.
No production/cognition/care change, push or Slack. Full body goal stays open.

### FB-01aj observer startup-boundary correction — 2026-09-27 08:08Z

The first changed-solver sustained probe stopped after0.1ms in the coarse lane,
before any paired sample: the observer tried to localize EVERY hinge crossing.
Several joints start exactly on their limits; the first released hinge's dense
quadratic is not monotone on the entire accepted segment. The localizer refused
honestly. No motion-channel failure was measured. Native admission had already
accepted that100us interval; this is not a solver failure or whole-motion pass.
Receipt FB-01aj-radau-secant-motion.json SHA256
682a525726c8d6446a23eaf1b051073f89fc0f48d44a854635398ecef93db5d9
preserves raw successor, work, actual stage operands and refusal. Child21254
finished in0.816s; exact host census confirms no survivor. No heavy history ran.

Localized observer correction: retain the original conservative sampled event
interval when the paired union ALREADY satisfies1us. Only when that union is
wider must the validated monotone hinge construction establish a tighter bound;
failure then remains failure. This preserves prior acceptance, does not guess a
nonmonotone root, and avoids extending to a new polynomial root solver. Persist
the event-correspondence records and any exact tighter bounds in the receipt.
All physical source, limits, budgets and compiled binaries are unchanged.
One final frozen source review, then one corrected bounded probe. The earlier
failure stays intact. No production or cognitive modification is authorized.

### FB-01aj sustained motion reaches first real contact-impulse failure — 2026-09-27 08:12Z

PROGRESS, not qualification. Final frozen source-only review passed for
fingerprint b0c2a111d059c135f7b1bfb240ef3d5871790f3576d50aa127b29fb8b7e788cb,
proof5c8a5d9e12fde670cd228ceb87a09edffac6e31d3d79af834626fa62dfe4f3bc,
runnerd253bb2e608f69e0332d67c8494d6d394a2e98aa7f2a0d12cd32281edc9acdf2.
One corrected run completed normally and stopped at the FIRST physical failure,
26ms in both histories; no48/250/500ms checkpoint or release phase was reached.
The two prior exact event operands and four sign-symmetry checks passed. The
earlier20.4ms knee timing boundary passed without changing its1us limit.

First failure is accumulated force impulse for native pair(10,20), left palm
and left digit4 distal surface. Disagreement2.9074546504203697e-5 N*s exceeds
allowed2.0336853058625396e-6 N*s (14.29648 times the limit), with reference
integrated force magnitude0.0010336853058625396 N*s. This is not a negligible
roundoff discrepancy and is NOT accepted. Motion/rate/proprioception/inertial,
work and instantaneous tactile comparisons still pass; event correspondence
reports PASS. Intrinsic couple impulse remains explicitly UNQUALIFIED.

Saved evidence isolates the failing contact to the last100us interval. Pair
contact begins inside[25.9470703125,25.9472656250]ms in both histories, far within
the unchanged timing bound. After25.95ms the coarse history accepts two25us
pieces; the half history uses four6.25us pieces followed by two12.5us pieces.
Both ordinary local checks passed, yet their cumulative impulses disagree.
This alone does not establish whether the cause is time-integration error,
inherited physical-state sensitivity, or contact-feature changes. Do not guess
or relax impulse accuracy. All authentic saved predecessors remain available.

Receipt docs/evidence/FB-01aj-radau-secant-motion-v2.json SHA256
6fb55748bbb472b84c5a5b89f77295611edd72c3cf96214e6a0dbf9c3278aebc
retains complete accepted prefixes, event operands/enclosures, work, impulses,
first failure, source/ABI hashes and resource/health evidence. Candidate source
and force laws remain unchanged from8f3f47fb2. No rebuild or old-control replay.
5610 primitive proposals,104516 solver forwards plus2084 outside forwards.
Native force time7.42755s; numerical proof19.25498s wall/19.24398s CPU; complete
child20.18261s wall/20.15179s aggregate CPU,241388KiB peak single-process RSS.
The candidate is still not real-time-qualified. Diagnostic process limits held.
Session42775/child22452 are terminal; separate exact host census has no survivor.

Read-only AWS08:09:32->08:09:55Z retains sole task1559/same image/identity,
ticks2570212->2570265, no checkpoint/cleanup error or durability block. Existing
clock-stalled ALARM persists; other4OK. CPU51.15->51.07percent average,
RAM3.07617percent. No production health repair or new live body capability.

Single next item: saved-contact attribution only. From each authenticated
25.95ms predecessor, compare identical remaining50us physical intervals with
1/2/4/8/16 fixed numerical pieces, unchanged force/work/feedback laws, and exact
coarse accepted two-piece replay as the control. This separates discretization
from inherited-state effects without restarting26ms histories. Treat fixed-grid
trials as diagnostic, not admitted body successors. If needed, inspect actual
contact normals/features on those same stages rather than inventing smoothing.
No change to physics or acceptance until this exact cause is established.
No push,Slack,production,cognition,food or caretaker changes. Goal ACTIVE.

### FB-01aj saved-contact attribution contract — 2026-09-27

Continue the single impulse-accuracy failure preserved in f556e8773. Requested:
bounded mechanics with truthful contact impulse and feedback. Current reality:
26ms paired histories disagree14.29648 times the existing impulse allowance.
Conflict: YES with claiming mechanically qualified delivery. No extension of
physical softness, selection/cognition, acceptance tolerances or production.
Single next item: identify whether the saved contact discrepancy comes from
numerical subdivision or inherited-state sensitivity. Body-only numerical
diagnosis; no DSF projection or full-field cognitive claim.

From the two authenticated25.95ms predecessors, replay both original accepted
tails (coarse two25us pieces; half four6.25us and two12.5us pieces) with their
recorded budgets. Require each raw successor, work receipt and final observation
to reproduce exactly before interpreting a numerical comparison. This uses
actual physical input, not invented contact state. For each same predecessor,
also use1/2/4/8/16 dyadic pieces over the same remaining50us; reuse the coarse
two-piece control as that grid result. At most68 primitive proposals. These
fixed grids are diagnostic and are NOT ordinary admitted physical successors.

Keep actual Radau contact-stage impulses, world contact positions, normals,
local wrenches, dimensions and constraint addresses. Observation reads existing
stage data and adds no force evaluation or body mutation. Retain raw state/work
before optional sensory inspection. Any failed grid/refusal remains in evidence;
never replace it with a fallback. Restore each copied predecessor exactly after
each schedule. No state reaches production or the organism's memory.

Compare same-history grid errors and cross-history16-piece results. Decompose
the original impulse difference into retained prior-impulse difference, each
history's tail discretization effect, and remaining inherited-state difference
at the common fine grid. Report arithmetic closure without treating a numerical
decomposition as a physical explanation beyond what those comparisons prove.

Use the same compiled solver/library,68*(5+32*2*16) forward ceiling plus60 outside
calls, and existing2core/60CPU/1GiBAS-per-process/90wall limits. Read-only AWS
pre/post and exact child cleanup required. Independent frozen source-only review
before this one no-build run. No26ms replay, full suite, push or Slack.

Independent source review found one evidence-only gap: contact position/frame/
distance and derived impulse comparisons were not explicitly checked finite
before recording. Correct those fields, impulse paths, differences, norms,
allowances and ratios before execution. Negative impulse paths and nonpositive
allowances refuse. No solver, motion, tolerance or run-budget change. Freeze and
obtain final source confirmation on this one localized correction batch.

### FB-01aj saved-contact attribution result — 2026-09-27 08:28Z

Final independent source review PASS after the single evidence-finiteness
correction. Candidate freeze c71ce5be069bddb6d9508df01a400af76d787c7fa547ce4c0ce88af8b126a2c1.
Proof SHA256 f72605b7765f6ecdce7451a0844e7d85308e2630262d5bf18a7652df3728af4b;
runner e150406906f94f7f56efbf1c2ea95e84d6fbd3f117c9af615756bdd3417d4bd2.
One run only, no build. Both original schedules reproduced each saved raw state,
work receipt and final observation exactly. All11 schedules returned; all copied
predecessors/timesteps restored exactly. Fixed grids remain diagnostic only.

The dominant discrepancy is numerical subdivision, not inherited state. On the
same coarse predecessor the original two25us pieces differ from16 pieces by
2.8956277877775987e-5 N*s. On both predecessors,1/2-piece results fail the existing
impulse allowance by14.6-14.8 times;4-piece results pass at ratios0.12744/0.14448;
8-piece results differ from16 by1.7056e-9 N*s (ratio0.000862). Fine-grid inherited
state difference is8.122629416848512e-8 N*s, versus the original2.9074546504203697e-5.
Prior impulse difference3.8881974799456703e-8 and half-tail grid effect4.676826828993062e-9
complete the vector decomposition with zero recorded arithmetic residual.
These are measured numerical comparisons, NOT a continuum error certificate.

Source inspection shows admission already compares all sampled stage domains.
Every schedule has one unchanged sampled domain, while early contact wrench
variation is resolved differently on finer grids. Thus merely extending a
contact-domain label or loosening its timing gate is not the correction. The
one-versus-two local integration check can agree spuriously on this transient.
No contact smoothing, physical retuning or blanket fixed-timestep reduction.

Single next item: correct this numerical admission blind spot using the actual
contact impulse trajectory and existing accuracy units; first demonstrate that
the changed check rejects this authenticated false-convergence case, and accepts
its resolved counterpart. Reuse the saved50us predecessors, not the26ms history.
Any proposed additional residual/quadrature check must be derived and independently
reviewed before code execution; no claim that an arbitrary extra sample proves
accuracy everywhere. Only after focused verification resume sustained motion.

Receipt docs/evidence/FB-01aj-contact-impulse-attribution.json SHA256
658a31bd14ba9d2fc44ae328463bd8563c6bb680f6183d1914574d1f23593e4b.
68 primitives,1302 solver forwards plus28 outside calls. Numerical matrix0.3819s
wall/0.3796s CPU; complete child1.1204s wall/1.1166s aggregate CPU,216048KiB peak
single-process RSS. Session71186/owned child-group29028 terminal; separate host
census confirms no survivor. No long-history restart or background remainder.

Read-only AWS08:26:03->08:26:07Z retains sole task1559/same image/identity,
ticks2572531->2572540, no checkpoint/cleanup error or durability block. Existing
clock-stalled ALARM persists; other4OK. Last CPU51.4146percent average,
RAM3.07617percent. No production health correction is claimed.
Body remains compiled-unmounted, not real-time or fully qualified. Gravity,
world integration, restart and remaining safety/performance gates remain open.
No push, Slack, production, cognition, food or caretaker changes. Goal ACTIVE.

### FB-01aj matched contact-tail refinement contract — 2026-09-27

The intervening user exchange was status only (NO PROGRESS), not a live wait.
Revalidated clean body HEAD d2b14d4304b731f4bcb1350411f7f533481b8f02 and
the authenticated crossed-history and original fine-tail receipts. Continue
FB-01aj; the closed local estimator and crossed-history attribution stay closed.
Only two missing final50us cells execute: coarse-start/half-step tail and
half-start/coarse-step tail from their exact47.9ms saved states/remaining energy.
Replay their existing14/12 accepted pieces as exact controls; run128/256-piece
dyadic tails using the unchanged compiled law. Reuse original coarse/half256
outcomes without reintegration. Maximum794 primitive attempts,8s internal CPU;
2cores/60CPU/1GiB address-space/90wall external envelope. No build.

Impact path: authenticated saved body -> RadauProbe.step -> numerical body
successor/work/contact impulses -> native observations and geometric gap ->
offline comparison -> immutable evidence. No runtime/schema/codec/mount edits.
Existing diagnostic helpers are authenticated before reuse. Failed step operands,
rollback, partial progress, expected/actual control observations, exact references,
timing bounds and cost survive failure. Fixed-grid results are altered numerical
successors, not exact enclosures of prior accepted trajectories or continuum truth.
Both128/256 same-tail comparisons must pass existing full physical/sensory limits.
Original256 vs crossed256 comparisons share the same26ms initial state/energy;
their final50us incremental impulse/work origin is explicitly identical in time.
Record initial47.9ms states separately: they remain history-dependent.

Event separation for corresponding pair(23,33) onset brackets[a,b],[c,d] is
[max(0,a-d,c-b), max(b-c,d-a)]. Upper<=1us passes, lower>1us fails,
otherwise unresolved. Missing, duplicate or unmatched events cannot pass.
No tolerance relaxation or physical-law change. Intrinsic couple impulse and
whole-history accuracy remain separately unqualified. Restored references must
match raw/time/full observation before being compared; do not trust a receipt
label alone. Test-only limits never enter the body law or cognition.

One frozen independent source review precedes one offline run, with read-only AWS
pre/post and owned-group census. No push, Slack, production or G1-owned edits.
Success closes only the same-initial-state final-contact ambiguity; remaining
new-law history, cost, gravity, mounting and restart gates are not waived.

### FB-01aj matched contact-tail ambiguity resolved — 2026-09-27 09:34Z

PROGRESS: one independent source review, one localized failure-evidence ordering
batch, final PASS, then one no-build diagnostic. Source physics is unchanged.
The review prevented loss of raw/accounting operands when an observation raises;
raw/time/work/supply now precede fallible observation and reference checks are
attached before restore. This is an observer correction, not a body-law change.
Freeze3b094873ab7498a464755f0fa5a49dce516240f5519e9fd55969344c2feda88b;
proof580ffdee6948a74136d1d318bed49b05d553e8f167859e3da949ef0307ac9abc;
runner6632c28dbb826012686940dcc4a7ae5e4396568235cf8746fb0b71a12b03d1f2.
Receipt docs/evidence/FB-01aj-matched-contact-tail.json SHA256
f6d17a2a7adf6f43ed13f8c6128654e1d84fcba79762ba2421bd908bc4c0a4d1.

Both14/12-piece controls reproduce every raw successor/work and final native
observation exactly. Original coarse/half256-piece references restore raw/time/
observation exactly without reintegration. Both crossed128/256 refinements pass
all measured endpoint/work/impulse/sensory limits and have event separation upper
bounds0.390625us. Matching26ms initial states across old/new fine-tail references
gives geometric event separation0.390625..0.781250us for BOTH comparisons, below
the unchanged1us ceiling. Joint-rate worst ratios0.733974/0.703918; all measured
physical groups pass. The previously ambiguous same-start final event is closed.

These are altered final50us numerical successors. They do NOT retroactively
certify the old accepted trajectories, the continuous physical solution, the
inherited pre26ms history, or full-body readiness. Intrinsic couple impulse still
has no separately ratified qualification ceiling. Earlier failed evidence stays
unchanged. No force law, anatomy, timestep tolerance, or cognition was tuned.

794 primitives,8148 solver/8172 total forward calls;2.200s numerical wall/CPU,
0.591s native forward. Full child3.155s wall/3.149s aggregate CPU,246984KiB peak
single-process RSS. Session23135/group54504 terminal; separate host census empty.
Read-only AWS09:31:40->09:31:46Z retained sole1559/same digest/identity,
ticks2582187->2582200; checkpoint/cleanup null,durability false. CPU51.2509percent,
RAM3.07617percent. Existing clock-stalled ALARM persists; other4OK. No live health
correction claimed. No build, push, Slack, production, G1-source or kernel edit.

Next accuracy path must begin with one byte-identical initial body and remaining
energy under the current contact estimator, not splice histories from the old
law at26ms and mislabel them identical. Reuse archived accepted controls as
evidence, but do not rerun this now-closed final-tail comparison. The full goal
remains ACTIVE: sustained accuracy/cost, gravity, ordinary body/world mount,
restart integration and eventual production safety remain unproved.

### FB-01aj contact quadrature correction contract — 2026-09-27

Continue32a4b0053's authenticated false-convergence case. Requested architecture:
force/energy-limited body motion with truthful tactile impulse. Current compiled
unmounted Radau candidate can miss an early contact transient in both coarse and
half-step quadratures. Conflict:YES with qualified mechanics. Do not extend
force smoothing, softened anatomy, cognitive controls, relaxed tolerances or
production. Single next change: add a start-inclusive embedded contact-impulse
comparison to the existing bounded numerical primitive and its normal refinement.
This is authorized body-only numerical approximation, not evaluation or reduction
of the seven-field DSF; no cognitive field is being substituted.

Derivation, separately for each world-frame contact pair and force/couple:
Radau's Q_R=h*(3*F_1/4+F_2/4), at abscissae1/3 and1, remains the physical
quadrature. Endpoint trapezoid Q_T=h*(F_0+F_2)/2 is exact for affine force in time.
Q_T-Q_R=h*(F_0/2-3*F_1/4+F_2/4), an independent O(h^3) smooth-trajectory indicator.
Read F_0 from already settled predecessor contact data, without an extra forward
solve. Reuse the actual converged final Radau stage for F_2. Apply the SAME
force/couple impulse allowances already in interval._close, with Q_R's existing
integrated resultant magnitude as relative reference. No new coefficient or
numerical tolerance. A finite local indicator cannot certify arbitrary hidden
transients or global error; sustained-motion and event qualification remain
mandatory. It can reject the demonstrated one/two-grid false agreement.

This is a passive contact-integral estimator on the Radau trajectory, NOT a new
trapezoidal dynamics solver or a replacement for work/energy accounting. Standard
Radau error-estimation precedent is documented at
https://drake.mit.edu/doxygen_cxx/classdrake_1_1systems_1_1_radau_integrator.html
(Drake solves an implicit trapezoid for full-state estimation; this narrower
passive-integral calculation does not claim to reproduce that implementation).

Bounded impact: native/functional_body/interval.pyx extracts its unchanged
impulse comparison into _impulses_close; _close delegates to that same authority.
native/functional_body/radau.pyx reads starting contact resultant, compares the
embedded integral, and raises a named numerical refusal on mismatch. Existing
admit recognizes that refusal and subdivides; existing state/timestep rollback
and accepted-only work debit remain authoritative. No new persistent state,
codec, anatomy, observer authority, API, world caller or production mount.
Existing Radau evaluation/stage solve must remain byte-identical. Extra work is
two sparse contact-pair reductions/comparisons per attempted primitive, no extra
force evaluations. Shared helper prevents a second tolerance implementation.

Focused acceptance from existing saved evidence: both false-converged50us
primitives must refuse with exact raw/timestep rollback; resolved final fine
primitives must reproduce archived successors/work exactly; ordinary admission
from each original predecessor must meet the unchanged complete endpoint/work/
contact comparison against its authenticated16-piece reference. Fresh repeat
must be exact. Zero supply and force-budget exhaustion must roll back. Bound
trials by the prior3*(float-mantissa-bits+2) allowance, one two-module build and
one proof,2cores/60CPU-per-process/1GiBAS-per-process/90wall each exact child group,
read-only AWS before/after and survivor census. No long-history run in this gate.
No runtime or production delivery claim, push, Slack, cognition or G1 edits.

Implementation source preflight: complete _Stages solver/evaluation class is
byte-identical to32a4b0053. Only contact integral comparison and its named
refinement refusal are added. Interval comparator is extracted without changing
its arithmetic. One edit-script line guard stopped before touching radau.pyx;
re-read the actual numbered line and applied that file once, preserving the
completed interval/doc edits. No compile or physics execution occurred there.

Frozen proof paths:/tmp/a1-body-contact-estimator-proof-20260927.py and
/tmp/a1-body-contact-estimator-run-20260927.py. Proof reuses authenticated controls
from658a31bd14ba9d2fc44ae328463bd8563c6bb680f6183d1914574d1f23593e4b,
not a re-execution of the old matrix. At most3*MAX_TRIALS+6 primitives, with
MAX_TRIALS=3*(float64 mantissa bits+2)=162. Force bound is that count times the
existing(5+32*2*16) per-primitive solver bound, plus the one-call refusal and
2*MAX_ATTEMPTS+24 outside forwards. CPU/wall limits remain independent hard
limits. Two serial isolated native builds, one bounded proof, no background run.

Independent source-only review found no estimator/physics/rollback architecture
defect. One localized proof correction attaches actual admission report and raw
successor/work/impulses before fallible observation or comparisons; resolved
primitive, repeat and refusal operands are likewise retained before assertions.
Source solver/helper and all numerical limits remain unchanged. Re-freeze and
final source confirmation are required before the first build/proof.

### FB-01aj contact quadrature correction verified locally — 2026-09-27 08:42Z

PROGRESS: final source review passed. Frozen candidate
cda09ec9d2bff702091a853d00aa47b6d1806e2117ac5110f00b9b8b10835b15 built once;
one focused proof completed. Both saved inaccurate50us primitives now refuse
with exact raw-state/timestep rollback. Each already-resolved final fine step
reproduces its archived successor and work exactly. Ordinary admission from
each authenticated25.95ms predecessor resolves the remaining50us in15 trials,
8 accepted pieces,3 numerical rejections. Complete endpoint/sensory/contact/work
comparison against each authenticated16-piece reference passes, unchanged limits.
Force impulse errors4.94619e-9/4.94609e-9N*s have ratios0.002499 of their existing
allowances, versus the predecessor coarse result's14.6286/14.6631. Fresh full
admission repeat and its accepted path are exact. Zero energy and one-call
force-budget refusals restore exactly. No synthetic impulse or work is published.

This closes the demonstrated saved-contact quadrature defect only. It does not
prove global-error control, sustained motion, intrinsic couple impulse, gravity,
world mounting, restart integration or production performance. The stage solver,
physical contact laws, anatomy, force limits and acceptance allowances did not
change. Existing midpoint law still uses the same extracted comparison.

Source hashes:
interval.pyx8391d81b1147e1973e1b147fc63c456176b46bc39137e8afa8f6fa2f118b7119;
radau.pyx605d88391082809cdebdfc6a9b2ed888103114d59d5e08ebdc5cbed16adfd92b.
Compiled modules in/tmp/guala-body-contact-estimator.qmush2pu/python:
interval102b1db8cdf60bb2808117bb685eb907c9a449c2c1ea9d1bb9a826799a80580d;
radau3f2525fa5e9a7b4bebf1ead9a88fe3efabf06bf652fb73eae56061f9d0f50d61.
Law is radau-iia2-secant-contact-estimator-v1. Source/proof/runner, native ABI,
resource and read-only health evidence are embedded in
 docs/evidence/FB-01aj-contact-estimator-proof.json, SHA256
42d4f6c3567871f56dd91db89e2ab22fdf1f7ec2607c59beb3bb3f90cf260fb3.

51 primitive attempts,1065 solver forwards plus55 outside. Numerical proof
0.3606s wall/0.3600s CPU; full child1.0200s wall/1.0134s aggregate CPU,
154588KiB peak single-process RSS. Two serial builds took8.4025/13.0045s wall,
8.3816/12.9798s aggregate CPU,340588/361340KiB peak single-process RSS.
Session91245 and exact owned groups35194/35232/35286 are terminal, with separate
host census confirming no survivors. No build repeat or old history replay.

Read-only AWS08:41:30->08:41:54Z retains sole task1559/same image/identity,
ticks2574807->2574869, checkpoint/cleanup null, durability false. Existing
clock-stalled ALARM remains; other4OK. CPU51.1355->51.3242percent averages,
RAM3.0782->3.0762percent. No production remediation claimed.

Single next item: sustained-motion accuracy/cost qualification with these
compiled modules, preserving this focused success and its predecessors. Use
saved authenticated checkpoints where appropriate; explicitly distinguish a
continued copied trajectory from a fresh new-law genesis history. Do not claim
an unchanged prior prefix was checked by this new estimator merely because it
passed the old law. Keep existing event/localization limits and cost ceilings.
No new build is required. No push, Slack, production, cognition or G1 changes.
The full body goal remains ACTIVE and incomplete.

### FB-01aj contact-corrected sustained continuation contract — 2026-09-27

Previous turn PROGRESS:1bb861e5a fixes the saved contact integration defect.
Continue the same body accuracy/cost item, not its closed focused proof. Requested:
bounded articulated motion with truthful feedback. Current reality: two verified
contact-corrected successors at~26ms, not sustained-motion-qualified. Conflict:YES
with claiming complete body delivery. No extension of force softening, cognitive
controls, relaxed accuracy, production or native source in this turn. Single next
item: one bounded sustained continuation from those authenticated successors.
Body-only numerical qualification; no DSF field is evaluated or replaced.

Restore each raw successor and exact remaining physical energy from
FB-01aj-contact-estimator-proof.json SHA256
42d4f6c3567871f56dd91db89e2ab22fdf1f7ec2607c59beb3bb3f90cf260fb3.
Require exact raw state, clock, observation, initial constraint-domain match and
complete initial paired physical comparison before any advance. The predecessors
are genuinely different numerical histories; do not pretend they are identical.
Existing tests proved each local successor. They do NOT prove their pre26ms
history was executed under this new estimator, and this run makes no such claim.
Work/impulse accumulators measure increments AFTER the authenticated restart
boundary; remaining energy carries forward exactly, with no replenishment.

Reuse unchanged body anatomy, benchmark effort and supply,100/50us nominal
admission, complete local/sensory/impulse comparisons, event evidence and exact
hinge localizer from the reviewed motion-v2 proof. Check48/250/500ms absolute
body times, releasing effort at250ms if reached. Stop on first discrepancy,
unresolved correspondence or existing50CPU/30000primitive diagnostic ceiling.
These are observation checkpoints, not a rewritten body clock or success waiver.
Compiled interval/radau modules from qmush2pu remain byte-authenticated; no build.
One offline child,2cores/60CPU/1GiBAS-per-process/90wall hard envelope; read-only
AWS before/after and exact process-group survivor census. Preserve all partial
results if the budget or physical checks stop progression. Record current raw
states, accepted prefixes, work/supply, constraints and native/observer cost.
No test loosening, repeated focused proof, whole-history replay, push or Slack.
The skill-required independent frozen source review precedes this one run.

### FB-01aj continued motion boundary measured — 2026-09-27 08:56Z

One approved no-build continuation completed its measurement and stopped on
physical discrepancy at47.95ms, from the authenticated26ms restart boundary.
Receipt docs/evidence/FB-01aj-contact-estimator-motion.json SHA256
2b1c53fdc2ab498ac4658e9d94d50402482a8c6d306eb237f5f11c610a108caa.
This is a FAILED sustained qualification, not a crash or qualified half-second.
Saved raw predecessors/successors, accepted paths, energy, impulses and complete
sensory outputs are retained. Earlier contact correction remains locally proved.

Right palm/digit4 distal contact onset differs across numerical histories:
coarse bracket47.93671875..47.9375ms versus half47.93359375..47.934375ms;
union3.90625us exceeds1us allowance. At47.95ms proximal angular-rate disagreement
0.04870086rad/s exceeds0.01984837; distal joint-rate ratio4.15115; local contact
force ratio1.65746; specific-force ratio1.61227; impulse ratio1.01494.
Surface positions, orientations, work and gyroscopes remain within limits.
These results do not alone distinguish inherited trajectory error from the last
50us integration error. No force law, tolerance or event check has been relaxed.

4079 primitives,76199 solver forwards,77735 total audited forwards. Numerical
13.7815s wall/13.7742s CPU for21.95ms additional simulated motion; native forward
time5.2339s. This instrumented result is NOT real-time performance. Full child
14.6188s wall/14.5977s aggregate CPU,223748KiB peak single-process RSS.
Session60788/group38800 terminated; independent exact host census has no
survivors. Read-only AWS08:50:31->08:50:48Z retains task1559/image/identity,
ticks2576141->2576182, checkpoint/cleanup null, durability false. Existing
clock-stalled ALARM remains; other4OK. No production repair claimed.

Single next item: attribute this exact final50us from each saved47.9ms predecessor.
Replay only the recorded accepted tail to verify state/work; independently refine
each predecessor on two fixed grids with maximum spacing EVENT_S/2 and EVENT_S/4.
The powers-of-two counts derive from interval length and the existing event bound
(128/256 pieces), not a new acceptance threshold. Compare same-predecessor grid
refinement separately from different-history fine-grid discrepancy. Query signed
native capsule/box separation and retain actual onset brackets, endpoint state,
work, impulses and full sensory comparisons. This diagnostic observes the same
physical laws, not a new motor controller or global-error certificate. At most1024
primitives/8CPU seconds internally; existing hard child resource envelope remains.
One no-build offline child; read-only AWS envelope; frozen source review required.
Proof:/tmp/a1-body-contact-time-attribution-20260927.py. No production, cognition,
force, admission or tolerance changes. No whole-prefix replay, push or Slack.

### FB-01aj inherited contact-timing discrepancy isolated — 2026-09-27 09:04Z

PROGRESS: one frozen source review, one localized evidence correction (retain and
compare archived/actual final sensory observations), and final PASS preceded one
no-build diagnostic. Reviewer withdrew a proposed domain-serialization correction:
current_domain already returns plain_domain; no redundant conversion was added.
Freeze33a72d77e723adc815cdf2c9332b26bf0957ae5590dfb2db26b7333cbc5f81fd.
Proof43eaf9ab10df129666d9eb2089d7e4505f18c8ef41e651f8653f3e2e7947da5d;
runner3d6272e636e00dd6bc29851c9f8cc70734724a1e2fd2d27a42dec9a6b8573300.
Receipt docs/evidence/FB-01aj-contact-time-attribution.json SHA256
230a64146221e91a8e4ae748267d9a2f35c50c47c734b688af91b1454de39a72.

Both saved final50us control paths reproduced every raw successor/work value and
final full sensory observation exactly. Fixed128/256-piece comparisons from EACH
same predecessor pass the complete existing physical tolerances. However, the
two DIFFERENT predecessors retain the discrepancy under the256-piece grid:
onset separation is bracketed2.9296875..3.3203125us, still greater than1us.
At47.9ms the native signed gaps already differ:0.747879842um versus0.688163836um
(59.716006nm). Different-history fine-grid joint-rate ratio4.85912, angular-rate
ratio2.87359, force ratio1.96351 and specific-force ratio1.90960 remain failures.
The fine-grid impulse comparison here is incremental over final50us, NOT the
longer continuation's cumulative impulse metric; its ratio2.25352 is not a direct
comparison with the earlier1.01494 accumulated ratio.

Thus refining only the last contact or changing contact forces is not supported.
The mismatch is inherited BEFORE47.9ms. This result does not yet isolate whether
it originates in the pre26ms histories, their restart-state difference, or their
subsequent independently admitted motion. Initial within-tolerance states are
not identical states, and nonlinear contact can amplify their differences.
Do not label that remaining distinction a new solver-law defect without evidence.

792 primitive steps,8126 solver forwards/8144 total;2.0261s numerical wall,
2.0278s CPU,0.5716s native forward. Complete child2.7759s wall/2.7730s aggregate
CPU,203656KiB peak single-process RSS. Session48606/group43290 terminal, separate
host census empty. No rebuild, full-history replay or physical-source change.
Read-only AWS09:02:38->09:02:43Z retained sole1559/same image/identity,
ticks2577930->2577944; checkpoint/cleanup null, durability false. Existing
clock-stalled ALARM remains, other4OK. CPU51.3526->51.3503percent averages,
RAM3.0782->3.0762percent. No live remediation claimed.

Single next item: distinguish inherited restart-state error from new-law global
trajectory error using the already saved common boundaries before proposing a
propagated-error admission correction. A same-start comparison must use EXACTLY
the same authenticated state and remaining energy; merely passing an initial
endpoint tolerance does not establish that equivalence. Do not rerun the closed
final-window proof. Preserve all failed and passed evidence; no tolerance change,
force smoothing, new controller, cognition, production, push or Slack. Full body
integration, gravity, sustained accuracy, performance and restart remain open.

### FB-01aj crossed-history attribution contract — 2026-09-27 09:12Z

Previous turn PROGRESS:cf8051a2e isolates inherited pre47.9ms contact discrepancy.
Continue FB-01aj sustained mechanical accuracy/cost, not closed local contact proof.
Requested architecture: bounded articulated mechanics with truthful feedback.
Current code: compiled-unmounted numerical body; global accuracy/cost unqualified.
Conflict:YES with claiming delivered mechanics. Do not extend forces, anatomy,
tolerances, cognitive rules, production custody or world mounting in this step.
Single next item: isolate initial-state versus discretization contributions.
This is body-only numerical evidence; no seven-field DSF evaluation or reduction.

Use the existing2x2 experiment. Original receipt2b1c53fdc2ab498ac4658e9d94d50402482a8c6d306eb237f5f11c610a108caa
already supplies coarse-start/coarse-step and half-start/half-step outcomes from
26ms to47.95ms. DO NOT rerun those cells. Run only coarse-start/half-step and
half-start/coarse-step from the byte-exact saved26ms bodies and their respective
remaining energy. Native/source hashes and existing observed Radau admission
remain unchanged. Reuse the exact220 archived common endpoints; no genesis replay.

Compare same-initial-state/different-step results separately from same-step/
different-initial-state results, with existing full endpoint/work/impulse/sensory
limits and event-correspondence law. Restoring the original diagonal endpoints
must reproduce their archived full observations exactly. Retain both new paths,
initial/final state and observations, work/supply, event brackets, refinements,
failure and cost evidence. Terminal comparisons are causal attribution, NOT an
all-time or continuum accuracy certificate. If matched initial states disagree,
the post-restart numerical paths contribute error; if only different initial
states disagree, earlier inherited history is implicated. Report mixed outcomes
literally rather than forcing either hypothesis.

At most30000 primitives/162 per admission/50CPU seconds internally, existing
2core/60CPU/1GiB-AS/90wall child limits, no network from child, read-only AWS
before/after and exact process-group census. One no-build run after independent
frozen source review. No physics source edits, push, Slack, or live mutation.
Proof:/tmp/a1-body-contact-crossed-history-20260927.py. Helper source is reused
only after exact hash authentication; no rejected mechanism is reintroduced.

Authority recovery: body root/branch/HEAD verified directly; archived August
handoff/authority/parsimony documents remain absent as previously recorded.
An abbreviated embodiment-curriculum.md reference was attempted once and is
absent; canonical-routes inspection resolves the real skill reference as
embodiment-curriculum-ui.md, read completely. No command from that failed read
executed, and no missing authority contents were invented.

### FB-01aj crossed-history attribution measured — 2026-09-27 09:18Z

PROGRESS: one source review and one localized reference-evidence correction,
then final PASS, preceded one no-build two-cell diagnostic. Expected and actual
reference raw/time/observation operands now survive failed comparisons. Freeze
73a3e267add2bd37024ee864db81378012b0e7ddf6b88087824b114b158cbc0d;
proof4c726da576d4c55d6c498260d6ad9ed6501879830a7b4198a407180c47d202a9;
runner794c53b09b15e9571cea8eafd0acc9cf6ac3f6e6999e8c8d4e6168f086706f35.
Receipt docs/evidence/FB-01aj-contact-crossed-history.json SHA256
e090f15727f976dbbf0929a6a7358afae2e9ea942ff3a3490f924db6d9c77453.

Both archived diagonal references restored exact raw states, clock, remaining
energy and full observations. Only the two missing crossed cells ran, through
the220 exact archived common endpoints. Both reach47.95ms with completed native
admission and retained full trajectories. At that terminal boundary, SAME initial
state/different step sizes pass all measured physical channels, including work,
impulse, tactile correspondence, angular motion, proprioception and inertial
return. Worst joint-rate ratios0.65124/0.31729 are below the unchanged allowance.
Intrinsic couple impulse remains separately UNQUALIFIED as before.

Different initial states at SAME step size still fail angular-rate, joint-rate,
local force and specific-force comparisons. Joint-rate ratios3.83507/3.50219;
geometric contact-onset separation is at least1.5625us/1.953125us, exceeding1us.
Thus pre26ms inherited differences materially drive the demonstrated discrepancy.
This contradicts blaming the post-restart force law alone. No physical-source
correction is justified by that attribution; nothing physical was edited.

Same-initial-state contact timing remains UNRESOLVED, not demonstrated compliant:
sampled bracket unions1.171875us/1.5625us exceed1us, but their minimum separation
is0. The existing observer labels the failed upper-bound gate FAIL; scientifically
these intervals do not prove that the actual numerical event difference exceeds
1us. For intervals[a,b] and[c,d], the separation range is
[max(0,a-d,c-b), max(b-c,d-a)]. Passing requires upper<=1us; proven excessive
separation requires lower>1us. Ambiguous brackets remain fail-closed. No threshold
or acceptance requirement has been weakened. Do not equate upper-bound failure
with a proved force-law defect or report all-time trajectory accuracy.

4077 primitives,76271 solver forwards/77816 total;14.0714s numerical wall,
14.0320s CPU,5.3036s native forward. Full child15.0306s wall/14.9688s aggregate
CPU,263980KiB peak single-process RSS. Session38849/group47909 terminal; independent
host census empty. No rebuild or replay of known diagonal controls/genesis.
Read-only AWS09:14:53->09:15:10Z retains sole1559/same image/identity,
ticks2579783->2579827; checkpoint/cleanup null, durability false. Existing
clock-stalled ALARM remains, other4OK. CPU51.2897percent average/RAM3.08024percent
latest samples. No production health repair claimed.

Single next item: resolve the ambiguous same-initial contact-time measurement
from its saved event predecessors. Preserve the admitted histories; do not rerun
the26..47.95ms crossed matrix or change mechanics merely to fit broad observer
brackets. Use tighter justified numerical event enclosures, or explicitly tighter
accepted event pieces with their altered successors disclosed. Existing final-
window and crossed-history receipts are reusable controls, not new experiments.
Future sustained qualification must use one exact initial state/energy per matched
comparison. The pre26ms history has NOT been requalified under the new estimator;
full new-law history, gravity, performance, world mounting and restart remain open.
No push, Slack, production, cognition, food or caretaker changes. Goal ACTIVE.

### FB-01aj current-law identical-genesis motion contract — 2026-09-27 09:39Z

Previous turn PROGRESS:605c3758c closed the matched-start final-contact ambiguity.
Its contract/result are at the earlier matched-contact-tail headings in this
ledger (10988/11026 at that commit); their position does not reopen the seam.
Requested architecture: sustained bounded articulated mechanics and truthful
feedback. Current reality: compiled-unmounted Radau numerical law; full history
and cost remain unqualified. Conflict:YES with calling the body delivered.
Do not extend physical forces, anatomy, cognition, kernel, tolerances, or live
mount/custody. Single next item: matched identical-genesis/current-law trajectory.
Reduced body mechanics only, not seven-field DSF cognition or microscopic anatomy.

Prior corrected26ms states inherit pre26ms trajectories from the old estimator;
none of those runs proves a fresh current-law history. Reuse authenticated
ObservedProbe/Lane/Errors/hinge-localizer source and already-qualified primitives.
Start both lanes at the SAME exact raw genesis, effort, energy, model and time.
One uses nominal100us, one50us. Ordinary Radau admission controls accepted pieces;
no scripted pose or controller changes. Check all existing physical/sensory/work/
impulse tolerances and event correspondence at common<=100us endpoints.
Target48ms,250ms powered,500ms after250ms effort release. Stop at first causal
failure or50CPU seconds/30000 primitive attempts; retain complete accepted prefix
and last attempt so a resource-limited prefix can continue without genesis replay.
Event upper-bound failures remain non-compliance, not proof of a force-law defect;
report lower/upper timing separation for a failed paired event when available.

The two initial raw states, energy, observations and domains are captured before
comparison. Same current law from genesis is the essential difference, not a
repeat of the old-history continuation or final-tail attribution. Budget exhaustion
is an incomplete measurement, never a mechanics pass. All primitive refusals must
retain exact rollback evidence. Intrinsic-couple impulse remains UNQUALIFIED.
Partial lane times may differ if the second lane refuses; do not label that pair
a completed common endpoint. Native/accounting/observer costs stay distinct.

One frozen source review and one no-build offline run under the existing2core/
60CPU/1GiB-AS/90wall envelope, read-only AWS pre/post and exact owned-group census.
No full history starts again unless the current-law path or initial conditions
change for a stated causal reason. No production, push, Slack or G1-source edits.

### FB-01aj current-law first failure and bounded attribution — 2026-09-27 09:44Z

The current-law identical-genesis run fails at32.4ms, not on a resource limit:
left-foot specific-force disagreement0.0503621031m/s2 exceeds0.0495029697m/s2
(ratio1.017355). All other measured groups and event correspondence pass. The
current local-admission law checks each substep, not accumulated trajectory error.
Do not infer the exact error origin or relax the limit from this alone.
Receipt f2a5cbd29eaed4ab8a9974f8bddac8ff4a52aaa63ed85f8440a156ef6cb10ca0
contains the entire accepted prefix and both final100us predecessors.

Next exact measurement: replay only each recorded final100us mesh (4/6 pieces)
to reproduce its final raw/work/observation; execute the two missing cross-mesh
tails from those SAME predecessors.20 primitives total,8CPU seconds internally,
existing external resource and read-only AWS envelope. Observe both saved initial
states before advancing, preserving full sensory vectors and unchanged comparisons.
Compare same-initial/different-mesh and different-initial/same-mesh separately.
These are fixed-piece numerical attribution paths, not new admitted production
successors or a global-error certificate. No force, feedback, tolerance, contact,
or cognitive source change. One frozen independent review, one no-build run.
This answers whether the failed final sample needs a local transition repair or
accumulated-error control; no complete trajectory or genesis rerun is authorized.

### FB-01aj accumulated trajectory-error boundary measured — 2026-09-27 09:51Z

PROGRESS: the first fresh identical-genesis/current-estimator pair completes324
common100us samples before a real specific-force failure at32.4ms. Event timing,
position/orientation, rates, work, contact impulse and tactile channels all pass.
Foot vectors are (17.0189714,-1.3088121,-35.6738139) versus
(17.0207052,-1.3142042,-35.6237713)m/s2. Norm difference0.0503621m/s2 exceeds
0.0495030m/s2; ratio1.017355. This is not the prior inherited-old-law contact
ambiguity. No whole-motion, gravity, real-time or production readiness is claimed.

Genesis receipt docs/evidence/FB-01aj-current-law-genesis.json SHA256
f2a5cbd29eaed4ab8a9974f8bddac8ff4a52aaa63ed85f8440a156ef6cb10ca0.
Freeze2e14cc2460f958778205e3d5a8bdd2ed309ae12460b770dc1ba4817fd6e41359;
proof3095e501738dcdb7e14270f2e13b4a38e405b1be78c92c9f5d3d482272284596;
runnerf91c3c936a875b47a14205750d6dcef486b225991a1525105ce768e120eb6273.
Independent source review PASS without corrections.8074primitives,148344solver/
151763total forwards;27.6835s numerical wall,10.4338s native,2.2043s observer;
full child28.7802s wall/28.7433s aggregate CPU,262648KiB peak RSS. This remains
far from demonstrated real-time cost even after excluding observer work.
Session85251/group57349 terminal; separate host census empty. Read-only AWS
09:38:54->09:39:25Z retained sole1559/same digest/identity,ticks2583216->2583291,
no checkpoint/cleanup/durability error. Existing clock-stalled ALARM persists.

One20-primitive saved-final100us attribution, not a new whole-history run,
reproduces both original4/6-piece meshes raw/work/observation exactly. Both
SAME-initial/different-mesh comparisons pass; foot acceleration errors only
0.0048425/0.0048444m/s2 (ratios0.09773/0.09786). DIFFERENT-initial/SAME-mesh
comparisons still fail at0.0552061/0.0552043m/s2 (ratios1.11530/1.11517).
At32.3ms the incoming acceleration discrepancy was0.0133300m/s2 against an
allowance0.2387529m/s2. It amplifies while the reference acceleration falls;
the allowed relative component therefore also contracts. The final local
transition is not the dominant cause. Tighter final pieces alone cannot remove
the accumulated state discrepancy. Do not change the foot sensor or forces.

Attribution receipt docs/evidence/FB-01aj-acceleration-attribution.json SHA256
46b8e8d60544b4d7fd85648687efba935de7400c673c675c27360f3f8988731a.
Freeze216be540bdf9b0b37d66e730c5926ef39f2e149c34526634ee72cd6abefeb4f5;
proofc517a840b15d8f63efa332ffcdf13b62bbc3adfa02ac0a28a0bcfe387a9177c9;
runnereb12d8b21e17179414f05bbe0d1382fdf55d6426f4f10051cd2a7b71fac2c016.
Independent review PASS.20primitives,404solver/422total forwards;0.243s numerical
wall,0.0271s native; full child1.3217s wall/1.3157s aggregate CPU,279752KiB RSS.
Session6140/group60689 terminal; host census empty. Read-only AWS09:47:39->43Z
retained sole1559/same digest/identity,ticks2584502->2584511; no custody errors;
same existing alarm, other4OK. No rebuild or physical/cognitive source change.

Corrective boundary: RadauProbe.admit/_close verifies fresh local comparisons
but does not carry a trajectory-wide accuracy guarantee. The next numerical
contract must address accumulated error over the physical publication interval,
preserving channelwise state/force/work limits, bounded cost and exact rollback.
Do not hide drift by resetting comparison histories, artificially synchronizing
body states, loosening limits, changing forces, or adding a sensor override.
Use the saved path to derive the smallest justified accumulated-error control
or more efficient convergent solver; do not repeat these closed attributions.
Any further full-origin run requires a causally different reviewed numerical
candidate, not another execution of this unchanged failing law. Full objective
ACTIVE/incomplete. No push, Slack, production, kernel or G1-owned source edits.

### FB-01aj higher-order numerical candidate contract — 2026-09-27

Continues accumulated-error correction, not a new anatomy/cognition project.
Predecessor56910e85f isolates accumulated trajectory error: the same-initial
final100us mesh pairs pass, but inherited-state pairs fail. No force or foot
sensor correction is justified. Existing sustained qualification remains open.

One bounded numerical replacement: three-stage fifth-order right-Radau IIA
collocation in native/functional_body/radau.pyx. Inputs remain raw mechanical
state, admitted efforts, physical duration and available mechanical work. Outputs
remain numerical successor, independently measured physical work, passive contact
impulses, stage observations and exact refusal rollback. Same native force law,
joint/skin geometry, SO(3) right-inverse chart, residual tolerance, bounded inverse
secant iteration and dyadic local admission. No DSF/kernel/cognition/world mount,
stored-state schema or physical coefficient changes.

Derive nodes c=((4-sqrt(6))/10,(4+sqrt(6))/10,1) from
10*c^3-18*c^2+9*c-1=0. For Lagrange basis l_j at these nodes,
A_ij=integral_0^c_i l_j(s)ds and b_j=integral_0^1 l_j(s)ds=A_3j.
Positive b=((16-sqrt(6))/36,(16+sqrt(6))/36,1/9) integrate through degree4.
The scalar linear stability function is
(1+2z/5+z^2/20)/(1-3z/5+3z^2/20-z^3/60), decaying to0 for stiff negative z.
This is not the rejected explicit RK4 or midpoint Richardson extrapolation
(which amplifies stiff decay to5/3). It is not the rejected dt/H allocation
(which required256 pieces per100us), a duplicate runtime trajectory, or a new
acceptance threshold. General reference for this method:
https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.Radau.html
That reference is not evidence of Guala accuracy.

All three coupled stages evaluate the actual native forces. Terminal stage owns
the endpoint and warmstart. Work and impulse weights use all three positive b.
The separate start-inclusive passive trapezoid comparison remains:
Q_R=h*sum(b_i F_i), Q_T=h*(F_0+F_end)/2. Endpoint trapezoid is sampled directly
at the final collocation stage, not by reusing the old two-stage weight.
No energy residual is converted to heat and no negative work is clipped.
Every numerical refusal restores exact predecessor and original timestep;
admission retains its current atomic rollback. Stage arrays are per-primitive,
O(3*nv) with secant rank bounded by32. No new persistent state or solver history.

Evidence ladder: source-only frozen review, then one offline bounded build and
a small saved-state panel before another whole-origin trajectory. Panel covers
genesis/free motion, saved loaded contact, saved lower-joint-limit state,
same-input deterministic replay, depleted energy refusal, and primitive/admission
rollback. Compare100/50/25us nominal admission of the same saved physical input
with the existing full channelwise comparator; retain refusals and cost. Fixed
saved prefixes are numerical diagnostics, not new learned experience or proof
of accumulated accuracy. Validate tableau identities and positive quadrature
before interpreting native results. Stop on first causal failure.

Higher order alone does not prove any global error bound. The named exit
remains SAME-genesis/current-law sustained trajectory and physical sensory/event
accuracy under the existing limits, followed by affordable compute. Do not reset
histories or relax tolerances to get that result. The two-stage quadratic hinge
event observer is inapplicable to three stages: it must not be reused unchanged.
Use truthful accepted-piece event brackets for the initial panel; if a later
sustained comparison needs tighter localization, derive cubic collocation
enclosures from the three-stage operands before claiming timing compliance.

Current translation boundary: this Radau module is compiled-unmounted. The
ordinary engine still invokes the accepted interval module. No production caller,
persistence decoder, interface or motor authority is changed in this candidate.
Runtime mounting, gravity, restart integration, intrinsic-couple impulse and full
cost remain open. A successful panel only permits the next sustained proof.

Operational envelope remains offline2-core/60CPU/1GiB-per-process-AS/90s-wall,
read-only AWS pre/post and exact child-group census. No push, Slack or live writes.
One implementation owner; one frozen source review and one localized correction
batch at most. Body branch source only. Record all outcomes in this same ledger.

Preflight correction: a read glob tools/guala_body_radau* and the subsequently
guessed native/functional_body/build_radau.py did not exist. Both reads failed
without mutation or execution. The actual verified builder is build.py with
--module radau. Future build preflight checks that exact file and dependencies.

### FB-01aj Radau3 saved-state panel passed — 2026-09-27 10:11Z

PROGRESS, not body completion. Frozen candidate
aa1694d3c9cf68a4bcdb32796c2bb1aeaa0c96d0efd50f0c3dec8b27ff4ad386
passed independent source review. The solver required no review correction.
The two proof corrections retained failed admission and full impulse operands/
exact replay comparison. The separately supplied runner required final measured
CPU/attempt checks and a post-run binary hash check; both were confirmed before
any build. These were evidence-only corrections, not numerical retuning.

One build, no prior trajectory rerun. Source radau.pyx SHA256
78000f1994293cd4eab63eed4438d02bb7f5bfc2c103bddb5e25dcecbd3d7a5e.
Compiled candidate at /tmp/guala-body-radau3.mys5pg2b/python/
guala_body_radau.cpython-311-x86_64-linux-gnu.so SHA256
963c8047874be40142b3629a909d29c392244d926b12c7cf63196527587e76fa.
Existing interval ABI3, engine, optics and physical model unchanged.
Proof /tmp/a1-body-radau3-panel-20260927.py SHA256
8e6ca55ea98b49c8dc25ca4581b80cd0ad8b1b2ab7880c4b740ab280197e498f;
runner /tmp/a1-body-radau3-panel-run-20260927.py SHA256
db3d71c536c4594d8da129e7ebbb03fa93aac36bde1c79ba1e8416744dab079f.
Receipt docs/evidence/FB-01aj-radau3-saved-regimes.json,838203bytes,SHA256
7f62ca5c19929b7948d2f36f40866921304aafaf2958d9fa45c916dff203d10d.

Exact Q(sqrt6) derivation confirms collocation integrals and quadrature degrees0..4.
All six100/50/25us same-initial comparisons pass existing state/sensory/work/
impulse/tactile limits. Inputs are saved genesis,25.949999999999862ms contact
state and31.9999999999998ms lower-limit predecessor; each interval is100us.
Worst reported channel ratios are below0.000401; orientation comparison near
floating-point floor dominates. This is not a sustained-history result.
Exact repeated input reproduces state, work, supply, impulses and observation.
Zero-energy and exhausted-admission-budget refusal both restore exact raw state
and timestep. Changed sampled domains have accepted pieces<=1us. Inter-lane
event timing, hidden crossings and intrinsic-couple impulse remain unqualified.

331 primitives,8020 solver forwards;1.96943s panel wall/1.96595s CPU,
0.55127s native force evaluation,1.20395s primitive transition work. Individual
100us physical intervals cost0.111..0.183s in this diagnostic; therefore this
does NOT establish real-time feasibility or a speed improvement. Full proof
child2.60487s wall/2.59335s aggregate CPU,259108KiB peak RSS. Build13.55287s
wall/13.52948s aggregate CPU,360024KiB peak RSS. Session73456 terminal; exact
owned groups68793/68853 terminal, separate host census confirms no survivors.

Read-only AWS10:09:50->10:10:08Z: sole1559/same image/identity,
ticks2587778->2587823, no checkpoint/cleanup/durability errors. Existing
clock-stalled ALARM persists; other4OK. CPU50.9323percent average,RAM3.07617percent.
No production state, caretaker, food, cognition, kernel, push or Slack change.

Single next item: sustained SAME-genesis/current-three-stage-law comparison
with stage-correct event observation and explicit cost reporting. Do not reuse
the two-stage quadratic hinge localizer. A cubic collocation numerical enclosure
or truthful accepted-piece timing bracket must be used, with unresolved timing
left unresolved. No second local-panel run, no body-force/threshold change, no
claimed all-future trajectory bound. Reuse the new binary; no rebuild without a
causal source change. Full objective remains ACTIVE/incomplete.

### FB-01aj Radau3 same-genesis sustained contract — 2026-09-27 10:17Z

Continues FB-01aj; previous turn PROGRESS in ca7d8497b. Saved-state panel receipt
7f62ca5c19929b7948d2f36f40866921304aafaf2958d9fa45c916dff203d10d
keeps the new three-stage primitive, algebra and local rollback prerequisite
closed. Current law is compiled-unmounted; full body delivery remains in conflict
with claiming completion. No force, anatomy, cognitive/kernel, tolerance, motor
interface or production extension. Reduced numerical body mechanics only; this
proof neither evaluates seven-field cognition nor microscopic biological anatomy.

One new SAME-genesis comparison uses the current Radau3 law on both paths,
nominal100us/50us, unchanged100us-or-less common samples and .048/.25/.5s
checkpoints, with effort released at .25s. No inherited two-stage prefix, no
state synchronization/reset, no new load or retuned coefficient. All existing
state, sensory, work, force, impulse and event tolerances remain. Stop on first
causal failure or50CPU seconds/30000primitive attempts; save full accepted
prefix and last attempt to continue a resource-limited trajectory without
restarting. No repeat build or local regime panel. Intrinsic-couple impulse and
hidden continuum crossings remain expressly unqualified.

Observer correction only: joint-limit times must use actual THREE stage q/v,
not the predecessor's quadratic polynomial. With binary Radau nodes c_j,
form q_v(theta)=q0+h*sum(v_j*integral_0^theta L_j(s)ds), a cubic. Independently
form the cubic q_p through measured (0,q0),(c1,q1),(c2,q2),(1,q3). Their exact
rational difference E(theta) has degree3. Its Bernstein coefficients beta_k
give |E(theta)|<=max|beta_k| on[0,1] by the convex-hull property. For monotone
decreasing event coordinates, enclose the roots using q_v minus/plus that
bound, clipped only to the already observed numerical event interval. Certify
monotonicity from the derivative's Bernstein coefficients, and verify exact
rational sign brackets for both q_v and q_p. Never call this a continuum
trajectory enclosure or alter native state to improve the bracket. Ambiguous/
uncertified events remain a qualification failure, not a guessed event time.

Cheap linear/cubic algebra and sign-reflection checks precede native history.
Event narrowing occurs only when accepted-piece brackets are insufficient;
geometric contacts retain truthful accepted-piece brackets. Exact two-stage
observer evidence remains historical evidence, not a three-stage validator.
Current saved limits proof supplies the known relevant physical regime.

Reuse only the reviewed observer/Lane/evidence shape from the prior source;
all stage-specific law assertions, force-call budgets and event mathematics
are updated. Raw states, per-stage event operands, partial-lane times, physical
work/impulse and failed rollback evidence must survive refusals. A resource cap
is an incomplete measurement; no whole-motion PASS or real-time claim follows.
No source repair is implied if the next failure is only insufficient evidence.

One frozen source-only review of proof/runner, no new native compile; same
offline2core/60CPU-per-process/1GiB-AS/90wall envelope and read-only AWS pre/post.
No push, Slack, live writes, or G1 edits. Independent terminal process census
required. One bounded exact next action: execute this sustained numerical
qualification, then follow only its first causal result.

### FB-01aj Radau3 sustained prefix and resource boundary — 2026-09-27 10:21Z

PROGRESS: one same-genesis/current-Radau3 run reached218 common100us samples,
21.8ms, with every completed state/sensory/work/impulse/tactile comparison and
event correspondence PASS. The stage-correct cubic observer passed its exact
linear/cubic/sign-reflection checks. This is not a whole-motion pass: the next
coarse interval21.8..21.9ms exhausted162 primitive admission trials and rolled
back byte-exactly to21.8ms. The half lane also remains21.8ms; its last completed
interval was21.7..21.8ms. No mismatch of those statuses is hidden.

Receipt docs/evidence/FB-01aj-radau3-genesis.json,6446423bytes,SHA256
5a2827aa1c371e346c5e1612cb76accee8576fed7f0232b9e006497a8dc849fb.
Frozen source-only review PASS with no corrections:
c06086300a79f9c41f9684ee7b5c75ef948571adc74351b79e9e9a4f8169e951.
Proof /tmp/a1-body-radau3-genesis-20260927.py SHA256
da1e98d439548807658d4e4fa5d36e500f725272e3bf3fee8f92040e7e2bc193;
runner /tmp/a1-body-radau3-genesis-run-20260927.py SHA256
08eb5a269a7fcfc466bed044b2301371687861598e1818c5baa242f8a50a0a5b.
No build or physical/numerical source change this run.

3937primitive attempts,99062solver/100671total forwards.17.2344s numerical wall,
17.2173s CPU,6.7734s native forces,14.6046s primitive transitions,1.1013s observer.
Full child18.0707s wall/18.0307s aggregate CPU,214828KiB peak RSS. Session64293
terminal; exact owned group72517 terminal and separate host census empty.
Read-only AWS10:18:59->10:19:19Z retains sole1559/same image/identity,
ticks2589080->2589131,no checkpoint/cleanup/durability errors. Existing clock
ALARM remains,other4OK; CPU51.4203percent average,RAM3.07617percent. No live write.

The saved failed interval contains76 provisionally accepted pieces ending at
21.8875ms, not a published successor.162trials,38refinements,10reused left trials.
27 refinements were caused by the passive start-inclusive trapezoid/Radau impulse
comparison,10 by local accuracy or domain change,1 by coupled residual descent.
All134 successful primitive trials and28 primitive refusals remain inspectable;
the entire100us admission rolled back. Do not simply raise the trial allowance
or retry the identical full-origin trajectory. No demonstrated force/sensor
defect follows from this resource refusal.

Single next item: quantify the contact-impulse estimator's contribution using
only the saved failed interval. Compare the actual Radau impulse against an
independently refined same-predecessor trajectory and the passive estimator;
retain refused-trial endpoint/stage evidence without changing the return verdict.
Use already recorded provisional prefixes as authenticated numerical controls,
not as newly published state. The measurement must distinguish real impulse
error from a lower-order estimator demanding unnecessary subdivision.

One possible numerical replacement, NOT approved by this evidence alone:
a positive three-point start-inclusive embedded quadrature through0,c2,1,
where c2=(4+sqrt6)/10 is the only existing interior Radau node in[1/3,2/3].
For a node a in that interval, exact integration of the quadratic Lagrange basis
gives weights (3a-1)/(6a),1/(6a(1-a)),(2-3a)/(6(1-a)).
These are nonnegative, integrate degrees0..2, use existing force evaluations,
and retain both start and end evidence. This differs from the order2 trapezoid
and requires no new dynamics, negative work, force calls, thresholds or state.
Do not replace the estimator unless the saved-state regime evidence shows it
retains genuine impulse-error refusal, including the prior loaded-contact
counterexample. It is a diagnostic candidate, not an assumed remedy.

No complete-history replay is authorized until a causally justified numerical
change is reviewed. Exact native forces, physical tolerances and rollback remain
closed. Full sustained accuracy, speed, gravity, mounting and restart remain
open. Goal ACTIVE; no push, Slack, cognition, food or caretaker edits.

### FB-01aj passive impulse-estimator attribution contract — 2026-09-27 10:29Z

Continues db245dc8f's measured resource refusal, not a new physical law. Body
delivery remains incomplete; reduced body mechanics only, no DSF/cognitive
evaluation. The numerical source/binary, forces, anatomy, physical tolerances
and caller return verdicts are frozen. Next exact item is one saved-state
diagnostic, with no full-history replay, build, admission-budget increase,
production mutation, push, Slack, or G1-owned edits.

Inputs: Radau3 failed coarse interval predecessor at21.8ms; both exact
25.95ms loaded-contact counterexample predecessors from authenticated
FB-01aj-contact-estimator-proof; and identical genesis as a control. Check raw
state sizes and artifact digests before execution. Query50/25/12.5us proposals
for the three loaded cases,50us for genesis. The current solver still refuses
its original errors. A read-only wrapper records its actual five weighted
impulse observations and raw stage wrenches, and forwards every original
return value/exception unchanged. Capture unpublished endpoint/work/observation
before exact rollback; inspecting that proposal is NOT admitting its successor.

For each proposal, independently integrate the same physical predecessor on
two fixed dyadic grids, first with pieces<=0.5us and then half that spacing.
Both grids must use ordinary unchanged primitive verdicts. Verify their
channelwise state/feedback/work and force/couple impulse agreement before
interpreting the proposal error. Retain every reference step's work, impulse
and successor plus failed-step rollback. These fine trajectories are numerical
references, not proof of continuum exactness or new published/lived experience.
If either reference refuses or the pair disagrees, stop with an unresolved
measurement. Never suppress that refusal or overwrite the reference.

Separately evaluate the previously derived positive0,c2,1 quadrature from
recorded forces only, using exact rational moment identities for binary c2.
No extra force solve or alternate verdict is applied to the body. Compare
actual trapezoid estimate, alternative estimate, and proposal-vs-refined physical
impulse; expose force and intrinsic-couple operands/limits independently.
Specifically detect any alternative-estimator acceptance when the refined
impulse comparison fails. A favorable point alone cannot authorize a change.

At most2500primitive attempts/20CPU seconds internally, with the existing
2core/60CPU-per-process/1GiB-AS/90wall offline envelope and read-only AWS pre/post.
The proposed matrix needs at most2410primitives including all refinements;
the call budget is fixed, not raised after failure. Raw force sampling is
passive diagnostic I/O, not new runtime cost or learning. No new compiled
artifact. One frozen source-only proof/runner review before execution; preserve
all outcomes and an independent terminal child-group census in this ledger.

### FB-01aj passive attribution: reference contact boundary — 2026-09-27 10:38Z

One bounded diagnostic executed; measurement recorded, attribution INCOMPLETE.
No numerical/physical solver edit or build. Original proposal verdicts remained
active. Source-only review closed one localized reporting defect before the run:
capture available stage/endpoint evidence in finally, and retain restored
observation before comparison. Final review PASS with unchanged worktree
fingerprint8e33c23fb322eee296e8d948e525ab003fd26e8b030d0fe704e3488fa29a1c3e.
Proof SHA2565c158afeb773f33d82188a6382160db99e8dae4544b263d4fa2eb57325c4d3d8;
runner SHA256bdb3caecbf1f963fa9a30bfb9e1ac9a0900c5fa8f5bb63812ec70af86a719558.

The50us proposal from21.8ms was refused by the existing trapezoid/Radau gate;
the alternate0,c2,1 estimate also fails. Maximum impulse-error/allowance ratios
were985.676 and434.088 respectively. These are estimator disagreements, NOT
measured errors against an independent trajectory. No alternative acceptance
or source replacement is justified by them.

The first128-piece reference reached21.806640625ms after17 accepted primitives.
Its18th primitive,0.390625us, converged its nonlinear residual to2.40817e-12
but failed the unchanged contact-impulse gate and rolled back byte-exactly.
Thus no pair of independently refined references completed, no proposal-error
comparison was possible, and the older counterexamples/genesis matrix was NOT
reached. This is an unresolved reference-contact transition, not a successful
estimator attribution or proof of wasted computation. Partial stages, raw
proposal endpoint, return/rollback state, reference steps, work and impulses
are retained. No accepted production or lived state was manufactured.

Receipt docs/evidence/FB-01aj-radau3-impulse-attribution.json,131444bytes,SHA256
3b1f624bd4f8b97346c23870516a345919c777d6840fbb7a6a59d0327c0e826b.
19primitive attempts,391native forwards,0.34783s numerical wall/0.34651s CPU.
Full child0.97411s wall/0.96955s aggregate CPU,193024KiB peak RSS. Session56188
terminal; group79493 terminal with separate host census empty. Read-only AWS
10:37:31->10:37:34Z retained sole1559/same image/identity,ticks2591812->2591821,
no checkpoint/cleanup/durability errors. Existing clock-stalled ALARM remains,
other4OK; CPU51.294percent average,RAM3.11483percent. No live mutation.

Next exact item: resolve this saved reference transition by bounded dyadic
subdivision with the original refusal/rollback law, then establish agreement
of two independently refined trajectories before interpreting either estimator.
Do not rerun the unchanged full-origin trajectory, increase work budgets, weaken
tolerances, suppress a contact, or replace the estimator on this evidence.
Previously accepted reference prefixes may be reused only with authenticated
raw state/work/impulse continuity; a refused step remains unpublished. Native
force laws and cognitive scope stay closed. Sustained numerical accuracy and
performance, gravity, body/world mounting and restart integration remain OPEN.
Goal ACTIVE; no push, Slack, G1-owned edits or production changes.

### FB-01aj refined reference contract — 2026-09-27 10:43Z

Continues60c1e5245's exact reference-step refusal. No physical law, numerical
solver, anatomy, tolerance, production or cognitive change. The first128-piece
reference cannot cross the contact boundary on a fixed grid even though its
nonlinear solve converged. A comparison cannot establish estimator quality
without a converged reference; the former diagnostic correctly stopped.

One offline proof correction: subdivide a reference step only after the exact
known contact-impulse estimator refusal, requiring byte-exact rollback before
halving. Other refusals and work exhaustion remain terminal. Both independent
reference grids retain their original maximum spacing,0.5us/0.25us, and can only
refine. Terminate if the midpoint is unrepresentable or existing2500primitive/
20CPU limits are exhausted. No fallback state or changed caller verdict.
Maintain the original saved-state/proposal matrix and complete channelwise
reference agreement requirement. Neither reference is a continuum certificate.

Avoid repeated work: authenticate prior receipt3b1f624bd4f8b97346c23870516a345919c777d6840fbb7a6a59d0327c0e826b,
its first proposal, and seventeen accepted reference pieces. Verify exact raw
predecessor/successor chain, grid timestamps, work, supply and impulse totals
before reusing that prefix. Resume from the accepted state, never the refused
endpoint. The old50us coarse proposal may be observed from its authenticated
unpublished endpoint; this does not turn a refused proposal into body experience.
No repeat proposal or reference-prefix integration. Other paths begin from their
original authenticated physical predecessor and remain independently integrated.

Capture each new refused step and rollback, accepted successor and work/impulse,
any incomplete reference, and comparisons before the first terminal error. Keep
the same offline2core/60CPU-process/1GiB-AS/90wall and read-only AWS envelope.
One frozen source-only review before this one run; no rebuild or whole-history
trajectory. Source and binary hashes unchanged. Intrinsic-couple comparison is
the existing local gate, not a newly ratified global impulse tolerance. Body
mounting, gravity, restart and sustained cost remain open.

### FB-01aj refined-reference result and exact rejection frontier — 2026-09-27 10:50Z

Refined references completed all nine loaded-state comparisons, agreeing on
state/sensory/work/contact and local force/couple impulse. Seven proposed coarse
motions genuinely fail; both older12.5us proposals pass reference accuracy but
are refused by BOTH estimators. Their original/alternative maximum ratios are
21.6576/1.5912 and21.6711/1.6055; actual impulse-error ratios0.6602/0.6464.
The three current21.8ms proposals50/25/12.5us genuinely fail, with actual impulse
ratios135.846/124.953/347.199. Replacing the gate is not yet justified: the alternate
accepted none of these loaded proposals. No false acceptance occurred in them.

The exact force discontinuity is resolvable with the existing law. Reference
subdivision reached0.000381469727us locally; coarse/fine reference agreement
does not certify the continuum. The original prefix/proposal restored exactly,
including sensory observations. Source-only review PASS after one localized
evidence-order correction. No native edit or build.

The run stopped at2500primitives during the finalgenesis control's fine grid,
after250/256 pieces. That control is incomplete; no full-matrix PASS. Do not
increase the allowance or replay completed cases to obtain a green label.
45706forwards,11.284s numerical wall/11.283s CPU. Full child12.286s wall,
12.266s aggregate CPU,291028KiB peak RSS. Session43156 terminal; owned83418
gone with separate host census empty. Read-only AWS10:46:22->10:46:36Z retains
sole1559/same image/identity,ticks2593146->2593182,no custody errors; existing
clock ALARM persists,other4OK. Receipt7398228bytes,SHA256
c7ea6decfea2ba92c95b3d1b7928f5e4b89223c4b5ad862443347d4e7fb6948e,
docs/evidence/FB-01aj-radau3-refined-impulse-attribution.json.
Freeze e7e453ef90ffa38846acf241130bab089b40ad95fd7b4ab5518ba28d577ddc60;
proof8de7591399dbe7b9e5c11326ff4df7921d95ed4837ae64226d982cc4b7e0ff7d,
runner56f89224180d417b285b301a629c9d77b3bdcc971641aa7f818535bd965d5e25.

Source-data analysis now identifies the exact small-step rejection frontier
that produced the162-trial limit:27 saved impulse refusals, all with raw exact
rollback state and supply matching a provisionally accepted prefix. Those
states remain diagnostic proposals, not published/lived successors. Seventeen
refusals localize the sharp onset; the later ten sample smooth loaded contact.
The tested50/25/12.5us initial proposals alone do not resolve that latter cost.

Single next bounded measurement: passively replay the remaining24 actual saved
refusals (indices7..143 as listed in the authenticated solver record; the first
three already have negative reference evidence), plus6.25us at each of the two
older loaded predecessors. Reuse the completed nine negative/reference results,
do not redo them or finish the irrelevant quiet-control matrix. For each exact
saved proposal, retain original caller refusal and evaluate0,c2,1 off-path. Only
if the alternate passes, establish its true motion/impulse error against TWO
independently refined references using the unchanged solver and previous
subdivision law. Stop on any false acceptance, unresolved reference or ordinary
solver error. At most2500primitives/20CPU seconds; no budget increase, native
change or rebuild. This maps the actual rejection frontier before deciding
whether an estimator change is justified. Authenticate source supply by exact
predecessor hash, not a guessed energy amount. Same frozen-review/offline/AWS
envelope, no production/push/Slack/cognitive/food/caretaker changes.

Frozen frontier review found one localized provenance distinction: saved solver
index1 has dt4.999999999999796e-05, whereas the prior50us comparison used
5.000000000000143e-05. Those endpoints are one binary ULP apart; comparative
negative evidence is not byte-exact coverage. Include index1 in this run, skip
only the exactly matching indices2/3. The final matrix is25 actual refusals
plus2 older6.25us proposals, not24+2. Same2500primitive/20CPU budget, no physics
change, one final source review before execution. No other finding reported.

### FB-01aj exact refusal frontier PASS — 2026-09-27 10:56Z

All27 proposals completed within the unchanged budget:25 actual saved refusals
plus two older6.25us controls. All25 reproduced the original refusal exactly.
The alternative0,c2,1 estimate accepted nine of those25; EVERY newly supported
proposal passed full state/sensory/work/contact and local force/couple impulse
comparison against two independently refined same-predecessor references.
The other16 remain refused. Both older6.25us controls pass both estimators and
the same full comparison. Combined with the retained nine earlier comparisons,
no tested alternative acceptance concealed a real physical error. This is a
bounded numerical regime map, not a global-error or whole-body certificate.

Newly supported original solver indices34,38,66,70,83,110,120,121,143 include
both sharp-onset and smooth-loaded regimes. This supports a derived higher-order
start-inclusive estimator instead of the low-order trapezoid; not a tolerance
relaxation or larger admission allowance. Contact force evaluations, actual
Radau state/work/impulse, original signs, anatomy and physical laws remain exact
relative to the same numerical candidate. No source change was made by this
diagnostic and no real-time/body deployment claim follows.

Receipt docs/evidence/FB-01aj-radau3-refusal-frontier.json,4666019bytes,SHA256
273771de2bb0a2be2470022d299292bd583af69569a8c704f16df3f80a7aa20b.
Frozen review PASS fd418f72c6db55c1e3a6b43682c606f01dfea605f012882cfa7dcf27b6fd274b.
Proofdc30409c4e160fed67e69f6d066f3c017ccd544ad3332ac7fa4592b49f01a0b9;
runner217004dcaff8b2aa79e21146ae5ebda5e17ee393a9dde809e32b7d6e9e7c4583.
1169primitive attempts,22289forwards,6.695s numerical wall/6.687s CPU;
full child7.619s wall/7.599s aggregate CPU,301652KiB peak RSS. Session94943
terminal; group86457 gone, separate host census empty. Read-only AWS retains
sole1559/same image/identity,ticks2594380->2594406,no custody errors; existing
clock ALARM persists,other4OK. No production/push/Slack/G1-owned source change.

Next single numerical correction may replace only the passive trapezoid impulse
estimate with the positive quadratic0,c2,1 rule already derived and measured.
Reuse existing stage impulses/forces; add no native force evaluation, body state,
controller, cache, physical tolerance, semantic action or custody mechanism.
Before any whole-history replay, require exact saved-proposal successor/work/
impulse equivalence, known-error refusal, unchanged exact rollback and the
original failed100us admission under the SAME162-trial allowance. Follow only
that result. Gravity, sustained motion accuracy/cost, world mount, body sensory
integration, cold restart and production remain open. Goal ACTIVE.

### FB-01aj positive embedded estimator implementation contract — 2026-09-27 11:02Z

Entry evidence is bf867fb7b's complete saved-refusal frontier. Nine of25 exact
old refusals are accurate under two independent references and the derived
positive quadratic estimator. The original trapezoid unnecessarily refines
those states. This is a numerical-estimator defect only, not a force/sensory
law defect. The prospective primitive trajectory and all actual Radau work/
impulse remain identical; only the passive error indicator changes.

Authorized source: native/functional_body/radau.pyx, constant coefficients and
RadauProbe.step's embedded contact impulse only. For a=C[1], use weights
w0=(3a-1)/(6a),wa=1/(6a(1-a)),w1=(2-3a)/(6(1-a)); exact integration of the
quadratic Lagrange basis through0,a,1. All are positive and sum to1. c1 is not
eligible because its start/end rule has a negative weight. Form initial/end
impulses using existing calls with dt*w0 and dt*w1, and obtain the middle term
by positive rescaling wa/B[1] of the EXISTING weighted stage impulse. No extra
native force evaluation or persistent state. Four existing pair components
(force, intrinsic couple, force path, couple path) all retain the same weight.
Keep E read-only alongside A/B/C. Update the diagnostic numerical-law identity.
Floating weighting is within the already authorized body-only approximation;
the independent proof derives exact rational moments at the binary node.

Causal path: RadauProbe.step -> existing _Stages.solve/evaluate -> actual native
forces/three-stage state/work -> passive embedded impulse comparison -> existing
same error/rollback on refusal -> unchanged RadauProbe.admit local whole-channel
comparison and sampled-event gate. No biology/neuron/kernel/cognition/runtime
mount, schema or body custody extension. Repository caller census confirms
guala_body_radau is not imported by serving code; build.py only selects an
isolated diagnostic extension. Production and main G1 files are out of scope.
No new locks/owners/labels/controllers/decision tables or lifetime history.

Mutations and rollback remain exactly as before: all stage trials unpublished,
raw integration state and timestep restored on any failure, same energy/travel/
residual limits, same162 admission trials. No artificial dissipation or state
synchronization. O(reached contacts) transient reweighting only; no new contacts,
stage solves, native force calls or retained body bytes. No stale v1 fallback.

Acceptance before any full-history rerun: compile once after frozen source-only
review; replay authenticated saved proposals and require the mapped verdicts,
bit-exact raw prospective state, observations, actual Radau impulses, energetic
work and stage-force-call count. Known inaccurate proposals stay refused with
exact rollback. Prove coefficient moments independently. Then settle the exact
previous21.8..21.9ms failed interval under the original162-trial allowance and
compare it with two independently refined same-predecessor references. Include
same-input replay plus zero-energy and exhausted-budget rollback. Preserve the
first failure rather than tuning or raising limits. Internal2048primitive/20CPU
measurement cap, existing offline2core/60CPU-process/1GiB-AS/90wall envelope and
read-only AWS pre/post. No push, Slack, live writes, or broader source changes.
Neither success nor compilation establishes sustained/global accuracy, real-time
speed, mounted body/world mechanics or cold production continuation.

### FB-01aj positive estimator result and local-refusal attribution — 2026-09-27 11:18Z

The reviewed positive estimator preserves all37 saved prospective raw states,
observations, actual Radau impulses, energetic work, iterations and force calls
exactly. Known errors remain refused. The original100us admission nevertheless
exhausts the SAME162 trials:72 fine pieces reach21.8875ms, then the whole interval
rolls back exactly to21.8ms. New36 refinements are18 impulse,17 local/domain,
one residual; old38 were27 impulse,10 local/domain,one residual. Fewer passive
impulse refusals did not establish bounded interval completion. No reference,
same-input admission replay, zero-energy or one-trial rollback subtest after
that failure was reached. No sustained/global/performance claim follows.

Receipt FB-01aj-radau3-positive-embedded-proof.json SHA256
8bda9317bc0d3171c330d4420e4af4ead1e250c1e93efc4035d129b984531715;
source cbc084a1dc775d2f555af7e07b7caf18bbf66b947ea67c7eef1ca4104e5616d3;
binary1d25cfed911742bfef99d53a770754bc673f2fdffe6f3abc80b8992adc773937.
Frozen source review0ddbd4e49cc303741afd027f84f7c700ac6d5bb88d83398b7109ae4a307d78bd PASS.
Build14.092s,362360KiB RSS; numerical2.485s,199primitives4836forwards;
full proof3.192s,282280KiB RSS. Owned groups91234/91339 terminal, independent
censuses empty. AWS sole1559/same image/identity,ticks2596131->2596180,no
custody errors; existing clock ALARM unchanged,other4OK. No production writes.

Next is passive attribution of precisely17 saved local/domain refusals, not a
new numerical law or full-history replay. Each predecessor comes from the
authenticated accepted-prefix raw state, crosschecked against the next piece's
predecessor SHA and recorded available work. Re-evaluate its exact coarse/left/
right primitive once (51 total), separately report the unchanged sampled-domain
event gate and every existing motion/sensor/work/impulse/contact comparison.
Return no overridden gate result; leave solver, tolerances, anatomy,162-trial
allowance and production untouched. Output is diagnostic, not accepted motion.
Use existing binaries, no build;10CPU-second internal/51primitive limit and the
existing offline2core/60CPU-process/1GiB-AS/90wall envelope with read-only AWS.
No complete-history or previously proved37-case repeat. Independent source-only
review precedes execution. The packed raw-state schema was checked before
freeze; an apply_patch attempt to delete/add one path in a single patch refused
without mutation. Full replacement must use separate patch operations. No
numeric run was made with the draft unpacker. Goal ACTIVE; body remains unmounted.

### FB-01aj local-refusal attribution outcome — 2026-09-27 11:33Z

All17 saved local/domain refusals reproduced exactly. All17 pass the unchanged
coarse/fine motion, sensory, energetic work, contact force and impulse checks;
all17 fail only the existing sampled-domain timing gate. The largest non-impulse
normalized error is0.0028507954573975397 of its existing allowance. These are
not17 demonstrated inaccurate trajectories. They remain REFUSED because event
timing is a separate required invariant, not because a successful endpoint
comparison authorizes discarding a physical transition.

Three cases include release of lower joint boundary57 and corresponding
constraint-row removal. Thirteen cases contain constraint-state changes only;
one case removes loaded pair(6,22), retaining(10,34). Geometry pairs otherwise
remain unchanged. The broad any-domain-change test forces both half-intervals
below1us even when state/work comparisons are comfortably within tolerance.
Do not infer that all these events are artificial, delete their timing gate,
increase the162 allowance, or relax the physical thresholds. Next single item:
map chronological same-trajectory sampled event brackets against the already
ratified1us uncertainty. Any event-local correction must retain all changed
domain evidence, refuse unresolved brackets and preserve exact rollback. Reuse
these saved observations before considering further numerical execution; do
not rebuild or replay the complete history merely to inspect event timing.

Receipt docs/evidence/FB-01aj-radau3-local-rejection.json,919830bytes,SHA256
cbe9974c9988aad01dd2f0e41cf33c1b46048738247ee868e9087c262239c8e6.
Proof ca4768043387b4eaab04b2a20b9b015ecbb0ee0b88f8db9d762d9d17a6922441;
runner a59a42eee3b9cfe53c519b18d00f61ac837a62e2967f01492ba0f23358436ff9.
Frozen tree ab06607d2e71048a533528f38765dfbab3a4d6f14e7313829b18434390e7c19e.
Independent review found two localized diagnostic issues (retain branch evidence
and restore case state on failure; reject nonfinite derived ratios). Both were
corrected in one batch and final review PASS preceded the only execution.
51primitives/1374forwards;0.735s numerical CPU,1.428s child wall/1.421s aggregate
CPU,162104KiB peak RSS. Exact group99597 terminal, runner and independent host
censuses empty. Sandbox /proc is namespace-local; host census uses the approved
host context. An unrelated short G1 publish_channel_books.py process had ended
before the guarded execution. No process was signaled.

Read-only AWS11:30:28->11:30:32Z retained sole1559,identical image/identity,
ticks2599678->2599687,CPU51.3768%,RAM3.125%,no custody errors. Existing clock
ALARM remains,other4OK. No build, mounted change, push, Slack or production
mutation. Positive estimator source remains compiled-unmounted; interval cost,
sustained/global accuracy, gravity, world/sensory mount and restart are OPEN.
Goal ACTIVE. This evidence closes attribution, not body qualification.

### FB-01aj chronological event-admission contract — 2026-09-27 11:48Z

Continue d8f357879, PROGRESS. Seventeen authenticated rejected intervals pass
all physical comparisons. Static reading of their saved domains and actual
Radau time formula finds narrow fine-path event brackets in cases2,5,6,7,12,16;
all coarse-path brackets remain wider than1us. Coarse/fine domain sequences
match in fifteen cases; cases8 and16 differ and must remain unresolved. Thus
five measured cases support more precise event admission, not a blanket removal
of event checking. This metadata calculation performs no native motion replay.

Independent source analysis agrees: coarse proposals are unpublished error
estimates, not the committed body path; their bracket WIDTH need not dictate
the committed fine path's temporal resolution. But coarse-only or mismatched
sequences cannot be discarded because endpoint _close passes. Current Radau3
genesis observer also assumes whole-piece widths and drops stage-only event
correspondence; it must consume the same chronological evidence before any
sustained-motion claim. The existing global independent-history correspondence
gate remains mandatory and is not redefined by local admission.

Single correction authorized in native/functional_body/radau.pyx: derive
ordered observed-domain transitions from each path's start, actual stage times
and endpoint. Preserve all seven domain components (joint boundary flags,
constraint types/ids/states, geometric and loaded pairs). Require monotone
finite sample times, no contradictory domains at one time, identical reduced
coarse/fine DOMAIN SEQUENCES (only adjacent duplicates removed), overlapping
corresponding coarse/fine brackets, and every committed fine bracket <=1us.
The domain sequence is numerical mechanical evidence, not a DSF reduction or
cognitive representation. Do not intersect brackets to invent a tighter time,
infer hidden crossings, interpolate force, or accept endpoint agreement alone.
Coarse/fine motion, sensory, contact, impulse and work comparisons stay exact
to their current tolerance. Stage-only excursions retain both transitions.

Expose the one numerical event comparison helper to the offline proof, and
reuse it in admit(). Accepted-piece diagnostic receipts carry only sample
indices and measured start/end times for their brackets; their domains come
from the original captured snapshots, not a second body store. No body schema,
runtime mount, controller, physical law or production caller changes. Existing
caller census keeps Radau compiled-unmounted. Temporary work scales with the
same fixed stage count and reached constraint/contact domain; no new force
evaluation or retained body state. Left-trial reuse, debit/commit order and
full input/timestep rollback remain unchanged. Update numerical-law identity.

Verification after one frozen independent review and one compile: classify the
same17 saved cases without replaying their motion; preserve wide brackets,
coarse-only/mismatched sequences and contradictory same-time observations as
negative controls, retain stage-only excursions. Then retry ONLY the original
21.8->21.9ms interval under the same162-trial allowance. Capture accepted work/
state immediately and actual chronological brackets. If complete, compare
against two independent references at <=0.5/0.25us, including physical fields,
work, impulse, observed event sequence/timing, exact repeat and energy/budget
rollback. Original2048-primitive/20CPU proof limits stay; no failed proof is
restarted with larger bounds. No37-case repetition, full-history replay, changed
force constants, tolerance relaxation, push, Slack or production mutation.
Read-only AWS and exact host process census wrap the bounded offline proof.

One source-construction preflight initially assumed the old gate block was
eight lines; the explicit boundary assertion refused BEFORE any file mutation.
Use exact structural start/end markers to delimit the complete replacement;
do not retry the guessed offset. No compiled or numerical run occurred.
Full body qualification, integration/restart and performance remain OPEN.

### FB-01aj chronological event admission verified — 2026-09-27 11:59Z

PROGRESS, continuing the same numerical accuracy/cost item. Frozen candidate
3d7a2afe6d75e9a35e08494394f187180f56bd4fdc3afa8b2d94cfe7fe72eb6b.
Independent source review found no event-gate architecture defect and two
LOCALIZED proof faults: raw NumPy domain scalars were not JSON-safe, and late
path assignment could lose partial stage evidence after failure. One batch
canonicalized only observer types and attached partial admission/reference
paths before assertions, retaining execution and observer errors separately.
Final independent review PASS; no source edits after review. Proof SHA256
9e00295b506ec6b32393e2f54cf7402cbf7e2f048d1e3658a711cf2188578ba2;
runner ad3bb31d09a8600b06de6f7495f9f02bb34665db78783a440a4a4dbd39d6a54a.

ONE native rebuild and ONE offline bounded proof completed. All17 saved cases
were classified from authenticated saved observations without replaying their
motion: cases2,5,6,7,12 pass the new timing gate; other12 remain refused.
Observer controls retain stage-only excursions and reject wide fine brackets,
coarse-only changes, disjoint brackets, same-time contradictions, decreasing or
nonfinite times. No force, energy, anatomy, physical tolerance or budget changed.

The original21.8->21.9ms interval now COMPLETES in139 of162allowed trials:
64accepted fine pieces,31refinements,12exact-input reuses. Prior v2 failed at162
and rolled back. Two independent references (nominal256/512 pieces, actual
264/519 after their own estimator refinement) pass motion/sensory/contact/work
and impulse comparisons; candidate versus finest reference also passes.
Material event sequences agree; maximum candidate/reference bracket union is
0.7654655446200087us, below unchanged1us. All seven mechanical-domain components
remain captured; global material correspondence retains its prior physical
keys. This is observed numerical-path evidence, NOT continuum event enclosure.
Same-input replay is exact. Zero-energy and one-trial refusals preserve exact
raw body state and original timestep. Full-history/global qualification is NOT
inferred from this100us witness. Existing global intrinsic-couple qualification
remains open; local impulse gate has not been promoted into that claim.

Receipt docs/evidence/FB-01aj-radau3-stage-events-proof.json:4868510bytes,
SHA25623f8610650dd716e8241307d412d4af48bf18793206584426a1d0fda9c36974e.
Source SHA714391817f603f0bc7c0a46f5af7391181cc1a11b13cba14fca447ec3256fe29,
law radau-iia3-secant-stage-events-v3; compiled ABI in
/tmp/guala-body-stage-events.2omn8l5l/python/ has SHA256
b6aa6ee30e22f18d78359b0dbad002f8ddd9c149dd70279917dd3b6e0a005d10.
1078primitive attempts,21696force calls,5.505numerical CPU seconds under the
original2048/20sec proof bounds. Build14.866s/363268KiB; proof child6.418s,
282348KiB peak single-process RSS. Two-core affinity,1GiB address-space and
90s child-group wall limits; no aggregate-memory guarantee claimed.

Host preflight found no concurrent Python/compiler work. Build group10167 and
proof group10244 ended with zero survivors. Independent post-census initially
matched its own parent shell because of substring searching, NOT a surviving
proof. Corrected the read-only census to exact argv entries plus exact groups;
result empty. Permanent recurrence guard: never infer orphan status from a
script name embedded in the inspection command itself; match actual argv.
No process was signaled and no numerical proof was repeated.

Read-only AWS11:57:04->11:57:28Z retains sole1559/same image and identity,
ticks2603522->2603580,no custody errors,CPU50.9516%/RAM3.1494% (latest metric
11:55Z). Pre-existing clock-stalled ALARM persists;other4OK. No production
mutation, push or Slack. G1 cognition/caretaker/deployment files untouched.
Body remains compiled-unmounted. Next: carry these accepted chronological
brackets into the existing sustained same-genesis qualification observer;
preserve full physical, event, work, restart and cost gates. Do not repeat the
closed37-case estimator panel or this completed local proof. Goal ACTIVE.

### FB-01aj v3 sustained observer contract — 2026-09-27 12:03Z

Continue b1dba6cf3 (previous turn PROGRESS). Requested architecture remains the
complete bounded functional body; current reality is compiled-unmounted body
mechanics with the100us event/cost seam now proven. Conflict with claiming full
delivery: YES, sustained accuracy/cost, gravity, integration and restart remain
open. No extension of cognitive/kernel code, force constants, anatomy, admission
limits, tolerances or production. This is reduced numerical rigid-body mechanics,
not full DSF or microscopic biology; no new omitted field claim is introduced.

Single next item: carry the v3 chronological stage events into the existing
same-genesis sustained proof. Existing 100us/50us paths, <=100us common samples,
.048/.25/.5s checkpoints and effort release at.25s remain. Original30000primitive,
50CPU-second limits and162trials per admission remain. Stop on first failure,
preserving both accepted histories and exact failed transaction. No rebuild:
use the authenticated b1dba6cf3 binary. A fresh history is necessary because the
positive estimator and chronological gate change which fine paths are accepted;
the old v1 prefix cannot be mislabeled a history generated by v3. Do not rerun
the closed37case or100us local panels.

Observer-only changes: record actual start/stage/end times and all seven
mechanical domains with canonical JSON scalar types. Verify native accepted
event brackets against adjacent captured samples, retain stage-only excursions
in order, and build the unchanged material-event correspondence from EACH
adjacent domain change, not only the whole piece's endpoints. Preserve original
whole-piece q/v operands for the already qualified exact cubic hinge localizer;
its normalized time is tied to the full piece, not the narrower sample bracket.
Any derived numerical enclosure must overlap the actual observed bracket; do
not intersect intervals or invent a midpoint to force timing agreement. Keep
unresolved/nonmonotone cases unresolved. Non-material constraint transitions
remain fully recorded and checked locally; global material keys remain unchanged.

Primitive mechanics and world state are not edited. Observer state cannot steer
motion, resample it or become retained organism data. Append original row/prefix
evidence before fallible timing assertions so a failure remains attributable.
Existing exact cubic algebra/sign tests are retained, alongside a small stage-
only chronological observer falsifier; neither is organism-learning evidence.
One frozen source-only independent review, no native build, one offline run with
the same2core/1GiB-AS/60CPU-per-process/90wall envelope, read-only AWS pre/post and
exact argv/process-group census. No push, Slack or production mutation.

### FB-01aj v3 first sustained failure / final-interval attribution — 2026-09-27 12:09Z

One independent source review PASS (no corrections), no rebuild, one sustained
run. V3 passes the .048s checkpoint and581 completed common100us comparisons,
then FAILS at58.2ms. Both lanes actually reached58.2ms, not a trial-limit rollback.
First metric failure: left-palm angular-rate error0.0342483661rad/s against
0.0161171336rad/s allowance (ratio2.1249663). Other left-hand channels also fail.
The lower-joint11 event differs by at least3.185009745042236us; exact cubic
numerical enclosure confirms this exceeds1us, not merely an uncertain wide
bracket. Material event and motion discrepancies are retained, not suppressed.

Receipt docs/evidence/FB-01aj-radau3-stage-genesis.json:15528753bytes,SHA256
49a444a5aa038e6368546cc70949d9b7291ae5fa9178216f3d12f8293f997c1d.
9942primitives,258404force calls,44.8273numerical CPU seconds; child46.2041s,
316216KiB peak RSS.1940/3852accepted fine pieces. This is NOT whole-motion or
real-time qualification. Native v3 remains unchanged and compiled-unmounted.
Owned group13869 terminal; independent exact argv/group census empty. AWS
12:06:15->12:07:04Z retains sole1559/same image/identity,ticks2604858->2604976,
no custody error. Existing clock alarm persists,other4OK. No production change.

Bounded next action follows this first causal failure only: use the recorded
58.1ms predecessors and16/18-piece final meshes. Reproduce both actual native
successors exactly, then execute the two crossed initial-state/mesh tails.
68primitive attempts maximum,8CPU seconds, no refinement or new motion rule.
Measure incoming states and same-initial/different-mesh versus different-initial/
same-mesh outputs separately, keeping actual q/v and chronological hinge-event
operands. This determines whether the new failure comes from that local crossing
or accumulated incoming state; it does not repeat the closed two-stage32.4ms
attribution or infer this new cause by analogy. All calls use the v3binary, no
force/tolerance/gravity changes, no whole-history rerun. Preserve original
execution errors and partial physical evidence before observer assertions.
One frozen source-only review and one bounded offline probe with AWS envelope.
If this is again accumulated drift, increasing method order or repeatedly
shrinking only the final step is not accepted as the general correction.

Attribution execution12:12Z stopped after the first16-step control on an
OBSERVER bookkeeping assertion, not a body mismatch. Every raw successor,
primitive work operand, supply and final observation matched exactly. The
observer left-folded work per primitive; native admit() first folds each accepted
left/right pair, then folds that pair into interval work. Floating addition
order yields last-bit differences (signed work1.0442552560452855e-10 versus
1.0442552560452854e-10J). Do not loosen the exact-control assertion or alter
physical quadrature. Correct the observer's reduction order to match the native
transaction. Retain the failure receipt61e98c5ae4ccb89adc2b1f330f869b87142459289aefc6e57b5ff625e79c4647
(125365bytes) and reuse the16 authenticated control steps, not replay them.
Only52remaining primitive calls are authorized under the original8CPU bound.
The reused control's work is reconstructed from the actual recorded per-step
operands with native pair grouping, then checked exactly against the original
interval. No sampled force, body state, source, tolerance or budget is changed.
Original incoming hinge angles already differ by4.2884910043e-6rad at58.1ms;
this is observed incoming drift, not yet the completed crossed-tail attribution.
Child group16341 terminal/census empty;1.043s/281648KiB; AWSsame1559,samealarm,
ticks2605817->2605826,no custodyerrors. One localized proof correction/final
review before the remaining calls. Never rerun the46second history for this.

### FB-01aj completed crossed-tail attribution — 2026-09-27 12:18Z

Requested architecture remains bounded, numerically qualified body mechanics
with truthful physical/sensory return. Current reality: local chronological
event admission passes, but sustained motion fails at58.2ms. Conflict with
integration readiness: YES. No cognitive/kernel extension, changed force law,
weakened tolerance, increased trial allowance, or production mutation. This is
reduced rigid-body numerical mechanics, not a full DSF evaluation. Next item is
trajectory-error control at the existing boundary, not more anatomy or behavior.

The corrected observer reuses the16 authenticated coarse-control steps and
executes only52 remaining primitives. Native pairwise work/supply arithmetic
is reproduced exactly; both original control endpoints/observations match.
One localized correction/final source review PASS, no rebuild or full replay.
Diagnostic completed, but all four physical cross-comparisons FAIL. Completion
of attribution must not be reported as physical qualification.

Same initial state, different final-interval mesh: palm angular-rate agreement
passes (ratios0.15444/0.22051), but palm specific-force disagreement fails
(0.0509568/0.0308392 and0.0738107/0.0303890m/s^2; ratios1.65234/2.42886).
Different inherited initial states, same mesh: palm angular-rate disagreement
fails (0.0378024/0.0161201 and0.0367327/0.0161171rad/s; ratios2.34504/2.27911),
as do ten other surface angular-rate channels. Palm specific-force ratios are
18.5343/17.7448. The incoming58.1ms observations pass the physical comparison,
yet their4.2884910043e-6rad joint-angle difference is amplified at the limit.
Thus inherited drift is causal to the angular-rate failure, and a separate
local mesh-dependent sensory error also remains. Do not claim the failure is
solely inherited drift or that local error control already suffices.

Receipt docs/evidence/FB-01aj-radau3-stage-tail-remaining.json:336167bytes,
SHA25682279b50c431ddb9261146360320c436bd1a6601145b58cc2410af60b79c34b2.
Frozen candidate82bf97195836d7dbc4eb89d0ae2275fcbeafa12c0023bc1fe8260da0bc13371b;
proofc8e1a1f605dc82ce09951ca0cb2f55a376c3c2cf0855c41fe176bb54f49a952d;
runnercaa668da8f5ae7df784631f41cc1d6926de3e5233e2f548e8898716a3e5f9856.
52primitives/1012forward calls/0.615956numerical CPU seconds. Child1.20185s,
281744KiB peak RSS. Owned group18762 exited with no survivors; independent
host census shows no Python/compiler workers. AWS12:18:44->48Z retains sole
1559/same image/identity,ticks2606663->2606671,no custody errors. Existing
clock-stalled ALARM persists;other4OK. No production mutation, push or Slack.

Bounded next direction: inspect saved local defects and incoming uncertainty
against the joint-limit event sensitivity before changing the integrator.
Accuracy of each isolated step does not establish trajectory-wide accuracy;
fixed current-state tolerances permit a smaller pose error that still changes
future event timing. Preserve both inherited and local failure evidence. Do not
reset either trajectory, synchronize states, hide the acceleration return,
shrink only this final tail, raise method order by trial-and-error, or rerun the
unchanged whole history. No next numerical law is claimed proven by this
diagnostic. Body stays compiled-unmounted; sustained accuracy/cost, gravity,
integration and restart remain OPEN.

### FB-01aj all-force increment attribution contract — 2026-09-27 12:36Z

Continues the same sustained-accuracy defect. Predecessor82e4b2aa5 preserved
the failed history and crossed-tail diagnosis; the local chronological-event
seam remains closed. No native/physical/cognitive change in this item.

Authenticated saved-state analysis (no physics replay) validates the complete
integration payload layout against both initial and final observed q/v. At
24.1ms the largest generalized-rate discrepancy is1.02031e-5; at24.2ms it grows
to0.00505852rad/s at DOF28. The later failing joint11 initially differs by only
9.26437e-12rad at24.1ms, then accumulates4.28849e-6rad by58.1ms. Maximum normalized
nonlinear residual across accepted pieces stays below1e-10. This does not
prove nonlinear-solver error is zero, but it does not justify loosening or
retuning that residual. No full-state/sensory evidence is projected into DSF.

Source-only independent analysis identifies a precise missing estimator:
step() checks start-inclusive CONTACT impulse quadrature, while joint-stop
generalized forces enter qacc but never that independent comparison. Existing
_close already covers endpoint acceleration/rate sensors; those are not missing.
The hypothesis is unproved: stage accelerations and stop reactions were not
retained by the previous tail observer. An all-force check cannot be described
as a cure for inherited drift before its actual effect is measured.

Single next item: observer-only map of actual start/three-stage acceleration
and joint-limit reactions on68 archived accepted pieces:8 first-interval free
pieces (duplicate half-lane omitted),12/14pieces at24.1->24.2ms,16/18 at58.1->58.2ms.
All original predecessors, available work and successors are authenticated.
Reconstruct available work by the original common-interval/pair subtraction
order; never invert rounded remaining supply. Restore each actual predecessor
independently and require byte-exact successor and work. This is not another
continuous trajectory trial, a new admission decision or a fabricated history.

Measure dv_R=h*sum(B_i*a_i), dv_E=h*(E_0*a_start+E_1*a_middle+E_2*a_end), using
the existing positive embedded weights. Units are m/s for root translation and
rad/s for generalized rotation. Report diagnostic componentwise rate allowances
already used by the coupled solver; do not claim these replace the complete
physical/sensory comparison. Capture start/actual-stage q/v/qacc, joint-limit
multipliers and J^T*f_limit through native mj_mulJacTVec, plus total generalized
constraint force. Native force/state values are never overwritten. Keep only
four scratch force samples during nonlinear solves and authenticate the final
three against the stage values actually returned; no extra force solve or new
integrator is introduced. If the estimate does not detect the actual discrepancy,
record that failure rather than lower thresholds. Inherited error remains open.

Proof /tmp/a1-body-radau3-all-force-observer-20260927.py and paired runner;
one frozen source-only review before one offline run, original8CPU diagnostic
ceiling,2core/1GiB-AS/60CPU-per-process/90wall outer envelope. AWS read-only
before/after and exact host census. No build, changed limits, push or Slack.
The retained receipt is offline evidence only; no runtime schema or sensory
consumer changes. One numerical approximation, not full DSF or biology.

Operational recurrence noted: the generic skill root-check was mistakenly
invoked again despite the known absent July HANDOFF. It exited65; no state
changed. Do not invoke that path without first checking its required authority
file exists. Current git root/branch, complete AGENTS, ratified user approvals,
skill authority and this sprint ledger remain the existing verified worktree
authority; do not fabricate historical documents. Earlier diagnostic console
dumps also exceeded the intended output size; subsequent readers must select
named scalar metrics/counts, never print whole domain/state/comparison objects.

One source-only review found two localized observer defects: failed cases must
retain actual state/time and four force samples, and retained operands require
finite checks. Corrected together before execution; no intermediate nonlinear
trial receives a new physical refusal. Nonfinite failure operands remain
lossless packed binary rather than becoming invalid JSON or disappearing.
Same batch corrects the initially unverified12:44 timestamp to clock-verified
12:36Z. Final review is limited to this batch. No source physics changed.

### FB-01aj all-force hypothesis rejected — 2026-09-27 12:47Z

Continues the sustained body-accuracy item; no closed prerequisite reopened.
Requested architecture: bounded numerical body mechanics with truthful motion,
contact and sensory return. Current reality: compiled-unmounted v3, sustained
accuracy and cost unqualified. Conflict with claiming integration readiness: YES.
No extension of cognition, L0-L4, anatomy, force constants, accuracy thresholds,
trial ceilings or production. Reduced rigid-body numerical mechanics, not full
DSF or microscopic biology. Single next item: resolve propagation of retained
numerical error through joint-limit transitions, using saved evidence first.

The 68-piece observer completed and reproduced every original raw successor and
work result exactly. The proposed independent all-force increment estimator
would reject ZERO pieces. Its maximum diagnostic normalized discrepancy is
0.000038691967 in the free interval, 0.3687924945 at the first rate-growth window
(24.1->24.2ms), and 0.2622868209 at the final failed window (58.1->58.2ms).
Therefore it is NOT a sufficient correction for the demonstrated sustained
failure. Do not implement this guard as the solution, lower its thresholds to
fit the failure, or repeat the same 68-piece panel. The additional force samples
are diagnostic evidence only; none enter organism state or runtime admission.

Receipt docs/evidence/FB-01aj-radau3-all-force-observer.json:1177291bytes,
SHA256 ad0d1893f86f4acb677a3f6e4eba48d04b39d4efeb0dad31a0efc3349f8b6026.
Proof SHA256 d00d8a1f8bbcf1dc756afa30155b8cca35645a319cc8bf0450e9302c58eed97c;
runner SHA256 b00066823fbba367ebcd43f67a82ca210602da85ede73c660f00c86b7b767107.
68 primitives,1523 native forward calls,0.765304 numerical CPU seconds;
child1.614203wall/1.592323aggregate CPU seconds,281108KiB peak RSS.
Jacobian-transpose instrumentation count1591 is an upper bound, not an exact
failure-path count. Final localized review passed after correcting this label.
Owned session38725/group27304 terminal; independent host census empty.
Read-only AWS12:40:33->37Z: sole1559/same image/identity,ticks2609910->2609920,
no checkpoint/cleanup/durability errors. Existing clock-stalled ALARM remains;
other4OK. Task CPU51.3753%, memory3.161621%. No production mutation, push or Slack.

The saved sustained history also separates numerical cost from observer cost:
258404 force calls consume17.75899s; primitive execution37.49072s; observer3.22212s;
total numerical CPU44.82729s for58.2ms of motion. Removing observer overhead alone
cannot establish real-time performance. This must not become another blind
higher-order or smaller-step replay. No executable trajectory-error correction
is yet qualified. Force sensitivities and their cost must be established before
selecting one. Native radau/interval remain byte-identical at714391817f60... and
8391d81b1147... respectively. Sustained accuracy/cost, gravity, integration and
restart remain OPEN; goal ACTIVE.

### FB-01aj solved-constraint state handoff contract — 2026-09-27 12:56Z

Previous goal turn PROGRESS:161119812 rejects the ineffective all-force check.
New saved-state evidence, not a physics replay: at24.175ms maximum lane rate
disagreement is6.19077e-6; at24.2ms it becomes0.005058517rad/s. During this last
25us coarse piece, joint23 reaction falls0.00940817->0Nm while the recorded
constraint state remains SATISFIED throughout. The prior joint57 onset has
already occurred, so another onset-only numerical correction is not the next
causal repair. One-sided event quadrature remains an unimplemented analytical
possibility, not a chosen solution or explanation for this first error growth.

Exact producer defect: patched MuJoCo3.3.7 engine_solver.c:945 writes final island
states to iefc_state; engine_forward.c:748-785 gathers back qacc/qfrc/efc_force,
but not efc_state. The latter is left from warmstart. engine_island.c:558-562
defines map_efc2iefc. interval._snapshot and trajectory.current_domain read the
stale array, so admission misses actual solved active-set transitions. Existing
same-state force/trajectory receipts remain valid as motion evidence; their
constraint-state/event-completeness claims are not corrected-law evidence.

Single correction: after a completed physical mj_forward, read final constraint
states in native row order from iefc_state[map_efc2iefc] when the EXACT native
islands-supported predicate is true; otherwise efc_state. No constraint rows or
forces are edited and no force solve is repeated. Zero rows return empty. One
helper in native/functional_body/interval.pyx serves both its _snapshot and
tools/guala_body_trajectory_accuracy.py current_domain. All these callsites
follow completed mj_forward; do not apply it to midpointResidual scratch.
radau.pyx numerical law identity and interval law identity advance because mesh
admission changes. ABI/layout and physical integration payload do not change;
NativeBody's existing law-bound header prevents silently restoring an old law.
No cognition/L0-L4/body/world schema/production changes. Reduced body mechanics,
not DSF evaluation. Physics, timing/accuracy thresholds and bounds unchanged.

Proof: eleven archived primitives (eight free controls and three first-error
pieces) preserve exact raw successor/work/native calls but expose the missed
transition. Validate island and ordinary solver-state branches without modifying
live state; assert the getter changes no raw state/force/sensor bytes. Then two
admissions from the SAME saved24.1ms predecessor with100/50us proposals, plus
64/128-piece independent references over just100us. Retain all physical/sensory/
work/impulse comparisons, chronological event brackets, exact replay/rollback
and law-bound cold-state rejection. No whole-history replay. Bound proof to
527 primitive attempts (11+2*162+64+128),8numerical CPU seconds; any additional
replay/rollback primitives require reducing reference/control allocation rather
than exceeding this bound. One frozen independent source review, two selected
extension builds, one offline proof;2cores/1GiB-AS/60CPU-process/90wall group.
Read-only AWS pre/post and exact host census. No push/Slack/production writes.
The helper adds only O(nefc) native-row mapping during existing snapshots, no
persistent state or duplicate physics. Full-body sustained accuracy/cost remains
open until separately qualified; this repair cannot be declared a global cure.

Command hygiene: a guessed setup.py path failed before any action, and a broad
/tmp name search hit an unrelated unreadable daemon directory. Actual builder is
native/functional_body/build.py. Future discovery uses that explicit directory
and known proof paths, not a broad /tmp search or guessed build filenames.

Frozen source review872ec77d09dd... found no architectural defect. Two localized
proof corrections batched before compilation: canonicalize native scalar types
in event sequences, and pre-attach control/custody records so failed assertions
retain actual state, forces, path and cold comparison operands. Native source is
unchanged by this batch. Exact full-file proof replacement and one final review;
no test, numerical run or build has occurred yet.

### FB-01aj solved-state handoff locally verified — 2026-09-27 13:15Z

Requested architecture remains bounded body mechanics and truthful sensory
return; cognition and L0-L4 stay unchanged. Current reality: v4 observer repair
is compiled and locally verified, not mounted. Conflict with claiming complete
body qualification: YES. No extension of force laws, tolerances, resource caps,
cognitive policy or production. Reduced numerical rigid-body model, not full
DSF/biology. Single next item: sustained same-genesis qualification under v4,
using the existing witness and fresh corrected-law histories, not relabeling v3.

Final source-only review passed after fixing the already-identified cold-proof
recording order: raw restored bytes are recorded before observation; observation
errors cannot replace a primary restore failure. Proof SHA256
b7919ead40281bc51ab91d79e26ca8cd86520ff15ab956d9bba555867c8fbbb8;
runner3ceaab9fec9a43e104f1f4b598d122b221570328888e117b0a445cea384a8dc6;
frozen body candidatead91e7b78351aa1d02f565f364eb4c50f4ebd4f2e8152ff88ff705527392603f.

One build of each affected extension and one offline proof completed. All11
archived controls preserve exact raw successor, work and native call count.
All6 native solver branches report their final states without mutating physical
state, force or sensory arrays. The saved coarse24.175->24.2ms piece now detects
one real solved-state change: [1,1,1] becomes[0,1,1], whereas stale warmstart
reported[0,1,1] throughout. This is measured evidence of the missing handoff.

From the SAME saved24.1ms predecessor,100us/50us proposal admissions complete
in48/44primitive attempts. Both agree with independent64/128piece references
on motion, orientation, proprioception, inertia, contact, work and impulses
under unchanged tolerances. Exact replay, fresh-engine body bytes/observation,
old-law restore rejection, zero-energy refusal and trial-ceiling whole-interval
rollback all pass. This does NOT establish global trajectory accuracy or speed.

Receipt docs/evidence/FB-01aj-solved-domain-proof.json:1252255bytes,
SHA256 d1e5de4d9372b944c89253c5a3f567c4c042afc7ff07ddb36df7d4ed48a9abc0.
345primitives/8015native calls/2.143183numerical CPU seconds;
child2.993772wall/2.977366aggregate CPU seconds,280984KiB peak RSS.
Builds8.763253/14.640401wall seconds; peak process RSS343132/364000KiB.
Owned build groups40365/40454 and proof40549 terminal with no survivors;
independent exact host census empty. Offline extensions retained only in
/tmp/guala-body-solved-domain.wxenj18y/python; no runtime mount or installation.
Interval binaryc537507b0da41416c554965863325abaee2f3e01002f6d46ee44e2d27cd2c788;
Radau binaryafdbb787d93fd83b16fd03108821cb32be260c8a6e7c503cbcd5adf7ba5cfd80.

Read-only AWS13:14:05->34Z: sole1559/same image/identity,
ticks2614948->2615018,no checkpoint/cleanup/durability errors. Existing
clock-stalled ALARM persists,other4OK. No G1 source changes, push, Slack or
production writes. Goal ACTIVE. Sustained accuracy/cost, gravity, body/world
integration and restart remain OPEN. A later receipt inspection accidentally
printed the admission lists instead of their lengths; it changed no state and
did not trigger a rerun. Future evidence readers must inspect field types and
print counts, not nested admission histories.

### FB-01aj v4 sustained qualification contract — 2026-09-27 13:20Z

Continues FB-01aj; prior turn PROGRESS at0b1f55c7c. Receipt
d1e5de4d9372b944c89253c5a3f567c4c042afc7ff07ddb36df7d4ed48a9abc0
keeps the solved-domain translation and local restart/rollback seam closed.
Requested architecture: bounded articulated body with truthful sensory return.
Current reality: v4 compiled-unmounted, local proof passed, sustained accuracy
and cost remain open. Conflict with claiming delivery: YES. No extension of
cognition/kernel, anatomy, force equations, tolerances, world mount or production.
Reduced numerical rigid-body mechanics; not full DSF or microscopic biology.
Single next item: one current-law same-genesis sustained qualification.

Reuse the complete reviewed v3 witness from authenticated receipt49a444a5...
with only v4/schema/binary identity updates and compact console output. Both
lanes start from the identical original raw body/energy, not any v3 accepted
prefix. The changed observer affects numerical admission, making fresh histories
necessary. Preserve100us/50us proposals, <=100us common sampling, checkpoints
.048/.25/.5s, effort release at.25s, all physical/sensory/work/impulse metrics,
chronological event records and unchanged material-event correspondence. Solver
state transitions remain captured and checked locally; no new global event
claim. Exact cubic hinge localizer and observer algebra checks are unchanged.
No standalone local proof/panel repeat and no native build.

Same30000primitive/50CPU-second measurement limits and162trials per admission.
Stop on first causal failure, ambiguous event, or resource limit. Retain exact
accepted prefixes, raw states, supplied energy, work, impulses and last failed
transaction. Resource exhaustion is INCOMPLETE, not PASS or permission to weaken
limits. Reuse a retained current-law prefix if continuation is later justified;
never restart a completed prefix solely because an observation window ended.
Cost is measured separately from observer work; no real-time claim from passage
of an accuracy gate. Intrinsic-couple impulse and unsampled continuum crossings
remain unqualified as in the existing contract.

Proof /tmp/a1-body-radau3-solved-genesis-20260927.py SHA256
6f6999a513f752fb5c23946cde660ddadac5de2e86bd39302255fd4110f13636;
runner /tmp/a1-body-radau3-solved-genesis-run-20260927.py SHA256
5a8b33b7756737f3cd1bbf65878517b09c0fa4a5a85a172ce53f88603c9e5de9.
Use the two already measured wxenj18y binaries with exact source/binary hashes.
One frozen source-only review, one offline run:2cores/1GiB AS per process,
60CPU seconds per process/90wall per group. Read-only AWS pre/post and exact
terminal process census. No push, Slack, production or G1 changes.

Skill routes refreshed; four named historical authority/parsimony documents
remain absent in this worktree. Do not invoke the known-failing generic root
script or fabricate them. Current AGENTS, ratified body-only numerical approvals,
verified branch/root and this existing sprint contract govern the bounded work.

### FB-01aj v4 retained sustained prefix and cost boundary — 2026-09-27 13:28Z

Independent frozen source review PASS; no localized corrections or native build.
One bounded execution stopped at its declared50CPU-second budget, not at an
accuracy failure. Both v4 paths agree through68.4ms (685completed common-sample
comparisons; initial equality checked separately), pass the48ms checkpoint and
material-event correspondence. The
old v3 failure at58.2ms does not recur on this measured v4 prefix. This is not
qualification of the full500ms protocol, global continuum accuracy or speed.

At stop, coarse has advanced to68.5ms, half remains at68.4ms with exact failed-
interval rollback. Retain both separately: never move the half state to the
coarse state, discard the extra coarse interval or restart either history.
Any future continuation must finish the existing half interval, compare both
at68.5ms, and preserve prior work/impulses/events before further advancement.
The original native source/binaries and all numerical/physical limits unchanged.

Receipt docs/evidence/FB-01aj-radau3-solved-genesis.json:17115346bytes,
SHA256 c243a427cb3344d7ff1ebde75f1aaef353e4fad4d50ad2d1e791c3a1e974e85d.
10890primitive attempts,283648probe force calls,287696total observed forwards;
50.006021numerical CPU seconds. Child51.391103wall/51.336622aggregate CPU seconds,
354212KiB peak RSS, no timeout. The .006021s cap overshoot is one bounded
primitive/check interval, NOT a silently increased allowance. Failure and
partial history retained; requested_motion_accuracy_passed=False.

Cost attribution: primitive execution41.702058s, of which force evaluations
19.402748s; observer3.578210s. The other primitive time is NOT all proven waste:
it includes the nonlinear solve, physical/sensory checks and representation.
Removing observer work alone cannot qualify live cost. Coarse2130accepted
pieces/3870completed trials/296reuses, half4322pieces/7018completed trials/239reuses.
Mean accepted piece lengths32.159624us/15.826006us; minimum0.000762939us.
Coarse refusal counts:272event,23other local accuracy,8nonlinear decrease,
76embedded contact-impulse. Half:217event,22other accuracy,57embedded impulse.
Typical accepted coarse pieces require28forwards, half22; this is a source of
real repeated numerical work, not a UI, logging or process-stall defect.

Source-only cost preflight preserves prior rejected methods: full implicit and
implicitfast histories remain rejected for measured accuracy, dense finite-
difference stage Jacobians remain rejected for cost, and blind uniform step
shrinking/order increases remain rejected. A larger nominal step is not an
innocent performance setting here: engine_core_constraint.c:1244-1257 clamps
positive solref to>=2*dt, and the current fixed response is200us with REFSAFE
enabled. Exceeding100us would change instantaneous force coefficients. Do not
do it or weaken the event/accuracy gate to reduce work.

Single next item remains sustained accuracy/cost: attribute the remaining
numerical/representation work on a bounded selection of these saved current-law
states before choosing a correction. Use exact raw/work controls, no genesis
replay, no force changes or speculative speed claim. The solved-state handoff
and its local lifecycle proof remain closed; the full objective remains ACTIVE.
One source search guessed a nonexistent native-body path and returned exit2;
the existing probe import resolves the actual module as
dsf_ai_service/substrate/functional_body_native.py. Use that inspected path.

Owned session87360/group44229 terminal, no survivors; exact host census empty.
Read-only AWS13:22:47->13:23:40Z: sole1559/same image/identity,
ticks2616211->2616343,no checkpoint/cleanup/durability errors. Existing clock
ALARM remains,other4OK; CPU50.930792%/memory3.198242% at13:21Z. No production,
G1 source, push or Slack changes. Gravity, integration and restart remain open.

### FB-01aj saved-v4 cost attribution contract — 2026-09-27 13:36Z

Previous turn PROGRESS:ec5e374bd preserves the new68.4ms matched prefix and
measured computation boundary. This continues sustained accuracy/cost; it does
not reopen the solved-state handoff or change the body law. Requested complete
body remains unmounted and unqualified. Conflict with claiming delivery: YES.
No cognition, kernel, forces, tolerances, timestep ceiling or production changes.
Reduced numerical rigid-body mechanics, not full biological or DSF evaluation.
Single next item: attribute numerical/representation cost using ten saved steps.

Deterministic selection per recorded v4 lane: first and last accepted piece,
maximum force-call count, shortest piece, and first observed hinge, solved-state,
geometric and loaded-contact changes. Deduplication yields five per lane, ten
total; this selects diagnostics, never organism actions. Initial pieces already
contain limit transitions and are not mislabeled contact-free. Original input
energy is reconstructed with the proved native subtraction/reduction order.
Coarse's one extra completed68.5ms interval is retained explicitly; half ends at
68.4ms. No history is replayed, synchronized or fabricated.

Passively time the existing snapshot, physical checks, contact impulse/estimator,
geometry-velocity/contact-force getters and native forward calls. cProfile
records function-call cost. Timings are instrumented and inclusive (nested
getters overlap their parent snapshot/impulse), not an uninstrumented benchmark
or additive partition. Exact saved raw successor, work and native call count
must all match; check expected wrapper coverage and restore every method/module
function before leaving a case, including failures. Raw failure state and cost
operands are retained. No timing value influences motion or admission.

One frozen independent source review, no native build, one offline10primitive/
4CPU-second proof. Same2core/1GiB-AS/60CPU-process/90wall process envelope,
read-only AWS pre/post and exact terminal process census. No production write,
Slack, push or G1 change. No attribution result is a solver-performance repair.
Use measured dominant work to select the next bounded correction; do not hide
force cost behind observation removal or reintroduce rejected implicit methods.

Probe /tmp/a1-body-radau3-cost-profile-20260927.py SHA256
849c42b587ee81ad50ac49fd8d5ddd9599bdc7c324780446e3905187321119ae;
runner /tmp/a1-body-radau3-cost-profile-run-20260927.py SHA256
d3e858b52142b4aaf57b8a20d0a53caff286fd566384c168be0ba2646cd44e1d.
Production remains independently checked by the runner; prior known baseline
sole1559/sameidentity, existing clock alarm, no custody errors. Body binaries
remain the source-matched v4 wxenj18y pair. No new coefficient or force law.

### FB-01aj saved-v4 cost result — 2026-09-27 13:45Z

PROGRESS, same sustained accuracy/cost item. The reviewed ten-control diagnostic
passed every saved raw-successor, work and native-forward-count comparison;
all measurement wrappers restored. No native source or physical law changed.
Receipt docs/evidence/FB-01aj-radau3-cost-profile.json:74556bytes, SHA256
ad02b9997b47d7c2531e3b3a73f134e9a772bf50cc14916c1786943213c963b3.
Packed measurement verified independently:277713bytes, SHA256
0a577525047eaa4db78e689e23c8ea0720d086d11a7c7775f56f2febeea3bf0b.
Ten primitives,223 forwards,0.590598451numerical CPU seconds. Child1.255993wall,
1.234865aggregate CPU seconds,296744KiB peak RSS. No timeout or error.

Measured waste boundary: interval._snapshot asks mj_objectVelocity separately
for each of50geometries, repeated five times per primitive. All2500getter calls
across ten controls carry real evidence, but2500Python/FFI dispatches are not
distinct physical settlements. One typed array traversal can preserve every
row without a Python call or NumPy row-view allocation per geometry. Do not
remove geometry rows, stages, finite checks or contact/sensory measurements.
The exact upstream map is engine_core_util.c:730-782 (world-frame geom branch)
and engine_util_spatial.c:477-505 (motion transform, no rotation): static welded
bodies return six zeros; otherwise angular velocity is cvel[:3], and linear
velocity is cvel[3:] minus (geom_xpos-subtree_com[root]) cross cvel[:3]. Preserve
the upstream subtraction/product order and signed-zero behavior. This is an
observation-only call-boundary correction, not a force or integration change.

Cost disclosure: ten instrumented primitives total0.055271wall seconds.
Native forwards0.018977s, snapshots0.018030s, nested velocity getters0.005012s,
impulses0.006032s, checks0.002050s. These inclusive timings overlap and include
instrumentation overhead. cProfile reports0.019543s in measurement wrappers
themselves,0.018551s native forwards and0.002909s native velocity getters.
Do not present wrapper time as production waste, subtract it to manufacture
a speed claim, or claim a getter replacement solves the substantial force cost.
Measure uninstrumented paired cost only after exact evidence equivalence.

Single next correction: native typed world-geometry velocity traversal inside
interval.pyx, preserving the existing snapshot schema, force call count, raw
state, work and every geometry velocity bit. Prove native-reference agreement
and snapshot equality on these saved controls, then entire primitive agreement
including replay/rollback; no sustained-history rerun until the bounded local
correction is verified. No new dependencies, ABI, stored cache, state law or
production mount. Frozen source review precedes any build or numerical proof.
This correction can remove repeated dispatch, not qualify full delivery alone.

Receipt inspection initially treated profiler_functions (an integer count) as
a list; that read-only formatting command raised TypeError. Corrected reader
checks types and traverses profiler (the actual row list). No numerical rerun.
Owned session38776/group50267 exited; independent host process census empty.
AWS13:38:37->41Z:sole1559/same identity and image,ticks2618515->2618525,
no checkpoint/cleanup/durability errors. Existing clock ALARM,other4OK;
CPU51.350934%average/51.780653%max,memory3.173828% at13:36Z. No production,
G1 source, push or Slack changes. Goal ACTIVE; body compiled-unmounted.

### FB-01aj native velocity boundary contract — 2026-09-27 13:52Z

Previous turn PROGRESS:ea1f80911 retained exact saved controls and measured
dispatch cost. Continuing the same accuracy/cost item, not reopening the
solved-domain handoff. Requested bounded functional-body delivery is not yet
qualified: current body is compiled-unmounted; conflict with delivery YES.
No cognition, kernel, force law, tolerances, anatomy, runtime mount or G1 edits.
Reduced numerical rigid-body mechanics only; no full biological/DSF claim.
Single exact next item: verify equivalent native geometry-velocity traversal.

Changed executable source: native/functional_body/interval.pyx only, full-file
replacement. _snapshot -> _geometry_velocities borrows geom_bodyid, body_weldid,
body_rootid, geom_xpos, subtree_com and cvel once, allocates the same ngeom*6
float64 output, executes the unchanged native world-motion transform in typed
loops. No per-geometry Python calls or NumPy row views. Read-only memoryviews
retain no state after return. Static-body six positive zeros, angular component
copies and linear subtraction/cross-product evaluation preserve native order.
Default checked memoryviews retain shape/type/index failure behavior rather
than introducing unchecked raw-pointer arithmetic. Existing _finite remains.

Causal impact: midpoint _one_step/advance_interval and Radau stage/endpoint
capture consume the same snapshot. _close, sampled-event comparison and the
trajectory observer receive unchanged velocity, state, pose, contacts, solved
constraint domain and sensory arrays. No force re-evaluation is deleted.
Unchanged NativeBody capture/restore header and interval/Radau law strings:
ABI3/v4, no state/schema migration. The correction cannot affect body state;
any failure produces no output, and the existing caller owns transaction
rollback. Ordinary cold state and the next step must match the saved control.
No package/production integration is added; this remains an unmounted proof.
No diagnostic data, recurrence cache or second physical authority is created.

One reviewed build of interval only; reuse the unchanged authenticated Radau
and MuJoCo binaries. Proof: ten original saved controls, fifty full snapshots
compared byte-exactly to the accepted scalar snapshot from pinned ea1f80911;
all geometry velocity rows, raw successors, work and force calls must match.
The candidate path raises if it calls the old per-geometry getter. Disposable
arithmetic scratch independently checks signed-zero and finite motion cases,
explicitly not a physical organism trajectory. Two timed repetitions compare
both implementations from identical saved inputs, reversing execution order;
no profiling/measurement wrappers in timed steps. Timing never admits motion.
One fresh cold restore/next step, one zero-energy and one force-budget refusal
must preserve exact state.53primitive attempts/5CPU seconds maximum; do not
repeat the sustained prefix. Small test count is scoped evidence, not full
500ms accuracy or real-time qualification. No improvement claim before data.

Same two-core,1GiB-AS/process,60CPU-s/process,90wall-s/group operational envelope;
network denied in build/proof, read-only AWS pre/post, fingerprint/source hashes
checked before and after, explicit handles and independent terminal census.
No push/Slack/production mutation. No rollback fallback or tolerance changes.
Source-only independent review required before any compilation or proof.

Source SHA256 5d978491164774fc14b803232f00cdc0f9f98f94c7eeb8b9c9b5accf036f03e6.
Probe /tmp/a1-body-velocity-boundary-proof-20260927.py SHA256
2165a05ad37fb92c794df586ffe4e8ace34cc2e93731d3a814dd3fe523b12b83.
Runner /tmp/a1-body-velocity-boundary-run-20260927.py SHA256
aa885c44f60abe03aa71cbfcca45d873ba2a8ff41592dc26f4eb8990bd5d09e5.
Pre-freeze source check corrected the draft proof's nonexistent max_calls
attribute to the actual RadauProbe.ceiling before execution; no failed run.
An upstream-header search for mju_cross returned no match in engine_util_blas.h;
bounded source lookup located engine_util_spatial.c:357 instead. Native source
was inspected, not inferred from the helper name. No new physical coefficient.

Frozen review150520ad51dcf74499d66276aa514b043429797ccc2d65a0c64ac727545ee966:
no architectural defect; native arithmetic/lifetimes pass. Two localized proof
gaps corrected in one batch before any build: failed comparisons now retain
actual/reference operands and active trial/custody state before assertions;
the newly built interval binary joins the post-proof hash check. Failure
packing includes byte states and signed float bits. Successful trial inputs
remain referenced by authenticated hashes instead of repeated raw history.
Compact console output omits raw custody payloads; receipt retains them.
Native source unchanged by review. Final source-only review required once.
Final probe SHA256
4d667832f45a256f62e9a03b7ffdaacb317b741e93d5c42b332bb31059ea614b;
final runner SHA256
90bf798c4969f075a631556eb680667f4f0d4390797fc396f4bf372d9235426f.

### FB-01aj native velocity boundary verified — 2026-09-27 14:00Z

PROGRESS: final frozen source review395bac15f24cba515abad172bd43e2ddaca7264fa31c7792cd4d25109270c3b7
PASS; both localized evidence gaps closed, no architectural finding. One
interval build and one focused proof ran; no repeated sustained history.
All53primitive attempts/1207forwards completed within0.339958numerical CPU
seconds. All50full snapshots/2500geometry rows match the previous native getter
bit-for-bit. Ten saved-state controls and40paired timing steps preserve raw
successor, work, impulse, stages and exact force-call counts. Candidate snapshot
cannot call the old per-geometry getter. Signed-zero/static and finite-motion
arithmetic checks pass. Fresh cold restore/next step, zero-energy refusal and
force-allowance refusal pass with exact state preservation. Source, binaries
and frozen tree hashes rechecked after execution.

Receipt docs/evidence/FB-01aj-velocity-boundary.json:42383bytes, SHA256
dd0d5e5b2f2543cb282657980da3fb5a288271523555ee165c7b2acb01818606.
Packed raw measurement:114521bytes, SHA256
3e0c5462dbb42cb414600ac4f827beaf86bc159a3fed4609910a3ad0141fc246.
New interval binary /tmp/guala-body-velocity.uw41fxqs/python/
guala_body_interval.cpython-311-x86_64-linux-gnu.so SHA256
04c168a94573c7b3282b9f1ea00e5821a00b8126357b8e6eb7f0d38b4b67a4f9.
Same Radau wxenj18y binary, MuJoCo midpoint library, law/ABI3/v4 and state header.
Build11.899wall/11.878aggregate CPU seconds,342428KiB peak RSS.
Proof1.315wall/0.906aggregate CPU seconds,145992KiB peak RSS; no timeout.

Unprofiled short paired timing (20same-state steps each): scalar reference
70.195ms wall/84.004ms process CPU; candidate66.896ms wall/64.120ms process CPU.
Reversing order also reduced wall time in each repetition (35.544->33.379ms;
34.650->33.517ms). This is a small local measurement, not a sustained benchmark
or real-time guarantee; clock/scheduling effects limit extrapolation. The
removed250getter dispatches per primitive are proved absent, not merely hidden.
All physics work and evidence rows remain. Native force-solver cost is still
substantial and open; no claim this modest correction solves the total budget.

Session59890 and child groups58341/58402 terminal, independent host census empty.
Preflight briefly saw unowned PID58232 (python tools/publish_channel_books.py,
PPID/PGID351); it had exited before follow-up inspection. No signal was sent;
do not claim the shared host was idle throughout. It was not a body proof child.
AWS13:59:15->30Z:sole1559/same identity/image,ticks2621541->2621578,
persisted2621516->2621548,no checkpoint/cleanup/durability errors. Existing
clock ALARM,other4OK. CPU51.340716%average/51.814559%max,memory3.175863%
at13:57Z. No G1 source, push, Slack or production change.

Close this exact observation-dispatch seam; do not re-review or retest its
settled arithmetic. Next: resume the preserved sustained v4 histories, first
complete half68.4->68.5ms against the already-completed coarse interval, then
advance without replay, synchronization, tolerance changes or duplicated
prefix evidence. Same bounded execution envelope; preserve partials on budget
exit. Body remains compiled-unmounted. Full500ms accuracy, sustained cost,
gravity, integration and restart remain OPEN; objective ACTIVE.

### FB-01aj saved-history continuation contract — 2026-09-27 14:10Z

Previous turn PROGRESS:f55ae5926 closes the exact velocity-dispatch correction.
Requested architecture remains the full bounded functional-body precursor.
Current reality compiled-unmounted; conflict with production-ready delivery YES.
This continues sustained accuracy/cost, does not reopen the getter arithmetic.
No native source, physical force, anatomy, tolerance, time-step ceiling, kernel,
cognition, G1 or production changes. Reduced numerical body mechanics, not
full biological anatomy or DSF evaluation. Single next item: continue saved
coarse/half v4 histories without replaying or synchronizing their predecessors.

Authoritative input: docs/evidence/FB-01aj-radau3-solved-genesis.json SHA256
c243a427cb3344d7ff1ebde75f1aaef353e4fad4d50ad2d1e791c3a1e974e85d.
Coarse at0.06849999999999876s, half at0.06839999999999877s, last common sample
0.06839999999999877s (685comparisons). Their separate5120byte physical states,
remaining work supplies, cumulative motor/bearing work and contact impulses
are authoritative. Restore each independently under the same header/law;
prove raw state, time and whole body observation equal the saved values before
any new numerical interval. Never reconstruct supply by a different subtraction
order, copy a lane's state into the other or discard the extra coarse interval.
Complete half to the saved coarse endpoint first, then compare before proceeding.

Reuse authenticated v4 observer/admission source prefix unchanged. No new motion,
event, error or force operator. Coarse100us/half50us proposals, same<=100us
common observations,48/250/500ms checkpoints and one torque release at250ms.
Continue cumulative channel maxima and unresolved-status evidence so an earlier
failure cannot disappear across chunks. Material event correspondence remains
cumulative; raw accepted/refused paths and contact-stage history in the new
receipt contain only newly executed intervals. Parent history is retained once
by content-addressed reference, not replayed or copied wholesale. Compact
previous-attempt metadata remains available if a lane has not yet advanced.
Same initial control/anatomy must regenerate the saved genesis identity; no
genesis trajectory is executed. Old law/state mismatch and non-budget failure
are not resumable. A mismatch retains exact restored operands or the failed
comparison states; ordinary admission retains failed interval rollback evidence.

One reviewed offline continuation, no build. Max30000primitive attempts,
50CPU seconds,162trials/admission; unchanged two-core/1GiB-AS per process,
60CPU-s/process and90wall-s/group. Read-only AWS pre/post, frozen/source/binary
hash checks and exact terminal census. A budget exit preserves independently
advanced lanes and last proved common time, reports incomplete, and permits
continuation only when no accuracy/event/refusal-integrity failure occurred.
Do not reinterpret chunk budgets as a real-time performance pass. No push,
Slack, production mutation or G1 edit. Full objective remains ACTIVE.

Compiled interval remains uw41fxqs SHA256
04c168a94573c7b3282b9f1ea00e5821a00b8126357b8e6eb7f0d38b4b67a4f9;
Radau wxenj18y and midpoint native library unchanged. Interval directory comes
first on import path so the old interval co-located with Radau cannot shadow it.
Probe /tmp/a1-body-radau3-continuation-20260927.py SHA256
e562695dd44281f122125b3b2009bd795aa4d794f1e3027d73171948c83ab711;
runner /tmp/a1-body-radau3-continuation-run-20260927.py SHA256
148095b2747517c2f3c13b5992d95f858ca2a25f865496c32748cb35fad3f3df.
Source-only independent review before execution. One receipt inspection
mistakenly printed complete metric channel dictionaries, producing truncated
console output; no numerical work was repeated. Later readers must select
status/counts/maxima explicitly, not emit whole channel maps.

### FB-01aj continuation result — 2026-09-27 14:27Z

Frozen source review PASS. One continuation executed from the two independent
saved states; no build, source change, synchronization or predecessor replay.
The last passing common observation advanced from68.4ms to173.4ms. The next
observation at173.5ms FAILS the existing left-palm specific-force bound:
error0.04354165409228073m/s^2, allowed0.042863499434688285m/s^2,
reference32.86349943468828m/s^2, ratio1.0158212620653095. Do not relax this
bound or label the failed prefix resumable. Other measured channel groups and
material-event correspondence PASS there; intrinsic-couple impulse remains
explicitly UNQUALIFIED. The full500ms protocol and sustained runtime cost remain
open. This is a measured accuracy rejection, not a resource-limit exit.

Receipt docs/evidence/FB-01aj-radau3-continuation-1.json:
16553316bytes, SHA256
0dde7d4af486bf88ff89de9c91b84a7c0161fda16c8ec0329c3367b89ab645af.
Authenticated raw payload48551131bytes, SHA256
5fd13e890db5c29e8f854a811c8c4be197981102bcba99d88e96739e8bffd97d.
Both exact failed states and their separate173.4ms predecessors are retained.
No saved accepted prefix is to be discarded or promoted to a new law.

New execution:10081primitives/255840probe forwards/259255total forwards;
42.43608992numerical CPU seconds,43.739676child wall seconds,
43.601184child self CPU,320500KiB peak RSS. The two lanes accepted2244/4312
new pieces and13new event pieces each; old history remains content-addressed.
Primitive wall33.761086s includes16.572814s native forces; observer2.749185s.
These are offline qualification costs, not a claim of viable production speed.

First causal boundary to investigate, without replay: lower joint-limit index9
activates near173.4954ms, immediately before the acceleration disagreement.
The retained coarse event bracket is
[0.17349543846658372,0.17349550781248718]s; half bracket is
[0.17349531249998718,0.173495433633601]s. Their union fits the unchanged1us
event allowance, while the pointwise acceleration allowance fails. This is
an observed association, not yet proof of which numerical operation causes
the discrepancy. Next isolate this one100us interval from both independent
173.4ms predecessors, distinguishing inherited state error from local event
integration error. No global step/tolerance/force changes and no heavy restart.

Owned group65607 exited normally, no survivors; independent host census empty.
Read-only AWS14:19:47->14:20:34 retains sole1559/same image/identity;
ticks2624476->2624586, persisted2624460->2624556, no custody errors.
Existing clock-stalled alarm persists; other4alarms OK. No production/G1 writes,
push or Slack. Objective ACTIVE; compiled-unmounted body remains unqualified.

Inspection hygiene: one compactness mistake emitted saved base64 states and
another emitted whole event-domain arrays; a scalar common-sample value was
also treated as a mapping by a read-only inspection and raised TypeError.
These did not execute mechanics or change evidence. Subsequent inspection
selected scalar bounds, changed indices and digests only. Do not repeat them.

### FB-01aj palm-boundary attribution contract — 2026-09-27 14:28Z

Previous turn PROGRESS:81b176325 retained the173.5ms acceleration rejection and
changed the next action from continuation to local causal diagnosis. Body tree
is clean at that commit. Numerical source still f55ae5926, compiled-unmounted.
The prior result heading14:27Z was entered before that clock time; authoritative
execution timestamps are the receipt's14:19:47--14:20:34Z. This heading corrects
that documentation time error, not the measured execution or evidence hashes.

Requested architecture: unchanged bounded functional-body precursor. Current
reality: sustained acceleration accuracy and cost unqualified. Conflict with
production-ready claim YES. No native body/cognition/kernel/G1/production source
or force/tolerance changes. Reduced articulated rigid mechanics, not full
biological anatomy or full DSF evaluation. Next one item: attribute the saved
173.4--173.5ms interval's left-palm specific-force error.

Input authority: continuation-1 receipt SHA256
0dde7d4af486bf88ff89de9c91b84a7c0161fda16c8ec0329c3367b89ab645af,
unchanged v4 law/probe and velocity ABI. First independently restore both failed
endpoints and require bit-exact body state and complete observation. Then replay
only the last100us from each lane's own last_attempt predecessor/supply, with
nominal proposals H/{1,2,4,8} for H=100us. Keep the existing<=100us force-law
response boundary. Require original coarse H and half H/2 rows to reproduce
their saved raw successor, whole observation, interval work and supply exactly.

This8row matrix distinguishes local discretization sensitivity from inherited
state separation. Compare coarse-vs-half inputs at each equal resolution and
neighboring resolutions within each input using the unchanged Errors observer.
Reproduce the original cross-resolution palm failure exactly. Store complete
row endpoints, observations, interval work, accepted/refused admission receipts
and event evidence; summarize only scalar metrics on console. Historical work
and impulse totals are not reverse-subtracted or fabricated: diagnostic totals
are explicitly new-interval-only and have no production authority.

Scope/input->native->evidence: authenticated retained predecessor -> existing
interval._restore -> accepted v4 Lane.advance/Radau admission -> native forward
and physical feedback -> unchanged Errors comparison -> one diagnostic receipt.
No schema migration, mount, new body law, historical replay, selected winner,
or continuation from the previously rejected trajectory. Either restore or
reproduction mismatch rejects diagnostic interpretation and retains operands.
Exceptions retain current row state/last_attempt and report failure. Existing
fail-closed admission rollback remains authoritative.

Single script /tmp/a1-body-palm-boundary-20260927.py SHA256
85e3b019478cbff81ddc0f0681edc97c6d32ef5199d8c25d83ba27dfb00e8219.
No build. At most3000primitive attempts and10numerical CPU seconds under the
existing2core/1GiB-AS/60CPU-s-per-process/90wall-s-group envelope; network-denied
child, immutable binary/source hashes and read-only AWS pre/post. Source review
under one frozen fingerprint before execution, exact terminal host census after.
No push/Slack/live changes. Full objective ACTIVE, no readiness claim.

Source-only review found one LOCALIZED diagnostic evidence-ordering gap: an
exception during restore or observation could precede attachment of its row.
One batch corrected both endpoint/predecessor branches to pre-attach expected
operands, retain actual raw state/time in finally, and record observation errors
separately. No numerical path change. Replacement script SHA256
ec5b903bf34d138a61e5ffa5329e703fec48324488e47fc00c2da8d120e94e9a.
Final source review before the single bounded run. No execution yet.

### FB-01aj palm-boundary attribution result — 2026-09-27 14:37Z

Final source review PASS; one offline diagnostic completed. Frozen fingerprint
1e37f395c8602937e3d9144908cfcf2069159eef9afc1ab4a54bbc247f0fc5a5
verified pre/post; native source and binaries unchanged. Both saved endpoint
states and entire observations reproduce exactly. Original coarse H and half
H/2 replays reproduce raw endpoints, work, supply and observations exactly;
the original failing palm metric is identical. All8matrix rows completed.

Receipt docs/evidence/FB-01aj-palm-boundary-diagnostic.json:
733344bytes, SHA256
8172e90ee1324166e2c7220b6c88b81924dd8e61b1f09197eee250ea6757122b.
Authenticated payload2453583bytes, SHA256
1fae995978ba33f614334eae501e7c039ec80bc21d42e88a4937c0c7dbd8a67e.
310primitives/6060probe forwards;1.667858numerical CPU seconds,
2.311966child wall,2.211065child self CPU,305588KiB peak RSS.
Owned group71246 exited normally; independent host census empty.

Decisive result: refining only the last100us from100us to12.5us nominal
changes the left-palm output by approximately1e-10m/s^2 within either input.
The cross-input disagreement remains0.04354165409m/s^2 (ratio1.015821262),
regardless of the local resolution. Therefore the failed measurement is not
an observation/restoration error, nor removable by repeatedly refining this
last interval. The incoming trajectories already differ. This closes local
attribution, NOT whole-motion accuracy or body delivery.

The activated joint is guala/left/forearm/elbow. At173.5ms, coarse/half elbow
angles are -4.5589758550415885e-7/-4.7105974037155846e-7rad, and rates are
-0.0991821734689424/-0.09900608824679329rad/s. A read-only traversal of4010
common retained endpoints (no mechanics execution) verifies the qpos layout
against the saved complete observation, qpos index16/qvel index15/nq71.
Largest elbow rate-error jump occurs across the elbow-limit event at
173.4953125--173.49609375ms:1.8327405407e-4rad/s. Before it, the largest
recorded rate-error jump is9.0765693646e-6rad/s at59.6875--59.690625ms,
coincident with lower-limit index11 activation. Another earlier jump is
1.4993707111e-6rad/s at26.7--26.8ms. These are trace locations, not yet proof
that changing a particular event algorithm repairs the full history.

Relevant causal source is native/functional_body/radau.pyx:admit: each
interval._close comparison starts both trials from one identical predecessor.
It bounds local disagreement, not amplification of already different incoming
states at a later unilateral constraint. A local pass is consequently not a
global sensory-error guarantee. Next bounded item: use the retained earlier
event boundaries to derive/test event-accurate trajectory control, preserving
the actual force law and all sensory limits. Do not synchronize histories,
loosen limits, replay the full history before a local correction is proved,
or keep halving the final100us that this matrix has already cleared.

Read-only AWS14:33:47->14:33:52Z retains sole1559/same image/identity,
ticks2626508->2626520,persisted2626476->2626508; no custody errors.
Existing clock alarm persists; other4alarms OK. No G1/production source,
push or Slack. Goal ACTIVE. Sustained accuracy/cost, gravity, integration,
cold lifecycle and final production delivery remain open.

### FB-01aj resumed earlier-event attribution contract — 2026-09-27 17:05Z

Joe resumed the functional-body goal after the COG-OSC-02 plan handoff to G1.
Continue the same accuracy/cost boundary from f195d058c; do not reopen the
closed velocity getter or final100us palm diagnostic. Candidate remains
compiled-unmounted. Cognition, DSF, force laws, sensory tolerances and G1's
production source remain unchanged. Reduced articulated mechanics, not full
biological anatomy. Current production-qualified body claim conflicts: YES.

The final173.4--173.5ms interval is already cleared as the source of local
discretization error. The incoming paths differ. Next bounded input: retained
common intervals26.7--26.8ms and59.6--59.7ms, identified in the prior raw-history
analysis, with each lane restored from its own authenticated predecessor.
The latter includes the lower-limit11 crossing. Compare H/{1,2,4,8} within
each input and matched resolutions across inputs. No full-history numerical
replay, state synchronization, accepted winner, or production successor.

Historical supply must not be reconstructed by reversing subtraction. This
diagnostic replays only recorded forward work arithmetic: paired accepted
fine pieces -> original common-observation transaction sum -> remaining
supply. Verify every predecessor hash and piece supply; require final state,
total work and remaining supply match the complete authenticated parent
exactly before using any selected intermediate predecessor. This accounting
read executes no body motion. Original H/coarse and H/2/half intervals must
reproduce raw endpoints, work and supply exactly before refined comparisons
are interpreted. Record actual input/output observations and accelerations;
exceptions retain attached row operands and ordinary admission rollback.

Input receipt FB-01aj-radau3-solved-genesis.json SHA256
c243a427cb3344d7ff1ebde75f1aaef353e4fad4d50ad2d1e791c3a1e974e85d.
Proof /tmp/a1-body-earlier-events-20260927.py reuses the fingerprinted v4
local mechanics/observer and reviewed bounded runner. Two intervals,16rows,
<=3000primitive attempts,10numerical CPU seconds; existing two-core,1GiB-AS,
60CPU-s/process,90wall-s/group envelope. Immutable source/binaries,
network-denied child, read-only AWS pre/post, owned-process census. No build.

Frozen independent source review precedes execution. Exit evidence identifies
whether earlier local event discretization or inherited state separation
dominates; it does not certify the complete trajectory or a new event law.
Only after that distinction may the event-accuracy implementation contract
change. Full motion accuracy/cost, gravity, body/world mount, restart and live
delivery remain open. Functional-body goal ACTIVE; no new user decision needed.

### FB-01aj earlier-event diagnostic result — 2026-09-27 17:15Z

Independent frozen source review PASS from body_force_review; no source edits
or numerical work in review. Frozen tree
5beb24f5498034ea72a066e8dc4c2f46f4e0a07704efe3aa24d10e088ad49ff5,
script d53a0223834b9389e0ae5b5aebd4c90c0eea7d416651f2f7c9e70fee7470ed57.
Receipt docs/evidence/FB-01aj-earlier-event-attribution.json SHA256
7c08f70a523cd47a2f30d88643fdface5321aab825ac8657d045ca7cea2571fc.

16/16 saved-state rows completed; all original-resolution controls reproduced
exact state, work and supply. Forward-only work accounting reproduced both
complete parent histories before selecting intermediate predecessors. No
whole-history dynamics replay. 304 primitives,7934 probe-forward calls,
2.644488 numerical CPU seconds,2.650845 numerical wall seconds; child process
CPU3.780497s and wall3.797110s, exit0, no survivors. Existing force law,
source/binaries, timestep ceiling and all acceptance tolerances unchanged.

At26.7--26.8ms, same-input H versus H/2 changed palm specific force by
0.0021855174m/s2; H/2 versus H/4 by0.0000349012; H/4 versus H/8 by0.0000016388.
Matching resolution across inherited inputs differed by only3.898e-6m/s2.
This interval introduces measurable local discretization difference, within
the existing local tolerance (about6.5419m/s2 at this large acceleration).
At59.6--59.7ms, matching-resolution cross-input difference remained
0.00790675698m/s2 at every refinement. Same-input refinement changed it by
at most1.74e-10m/s2. Thus refinement of this later crossing does not erase
the inherited difference. Neither result certifies the entire trajectory or
proves that this single earlier interval explains every later difference.

The prior173.5ms whole-trajectory palm failure remains OPEN. Next mechanics
work must account for propagation of earlier local defects through later
constraint transitions; do not repeat the cleared final-interval matrix or
synchronize the two independent histories. No tolerance relaxation, artificial
damping, force alteration, whole-body qualification or production mount.

Read-only pre/post production envelope at17:08:44--51UTC remained task1560,
same image45b4591c43a6067eb7367bda2be2e08fd26429e2f43c46055c1b99d249da39ed,
same organism identity, ticks2653920->2653942, paired durability unblocked,
errors null, service1/1/0. Existing clock-stalled alarm remained ALARM while
ticks advanced; the other four listed alarms were OK. Do not describe this as
an all-alarm-green production audit. No live writes were made.

Joe added a P0 cognitive-contract review request during the running diagnostic.
That review is separate documentation-only work in the main Guala checkout;
body ownership and ACTIVE goal are unchanged. No additional body test running
after this completed bounded diagnostic; exact-child exit and host census
confirmed. Evidence is retained for the next numerical correction.

### FB-01aj independent-history admission candidate — 2026-09-27 17:24Z

Previous goal turn: PROGRESS (saved earlier-event attribution and P0 review
handoff). Current physical candidate still unmounted/unqualified. Continue
body-only numerical work; no cognition, kernel, physical force, material,
coefficient, sensory tolerance, or G1 source change.

Source cause: local admission compares Phi_h(x) with Phi_h/2(Phi_h/2(x))
from the SAME current x, then discards the coarse history. That indicator
cannot constrain later Phi_h(x_coarse)-Phi_h/2^2(x_fine) when x_coarse and
x_fine have diverged. The saved26.7ms and59.6ms controls now demonstrate this
distinction. A small local discrepancy is not a sustained accuracy proof.

Bounded correction in native/functional_body/radau.pyx: keep existing local
v4 stage/residual/force law intact and add admit_trajectory with separate
radau-iia3-independent-history-v1 admission identity. Two numerical paths
start from the identical last committed body predecessor, retain their own
states through the entire UNPUBLISHED requested interval, and compare on the
fixed common observation grid. Compare existing pose/velocity/sensory/contact
tolerances, accumulated actual work and impulse, full sampled event-domain
sequence, and corresponding event bracket union<=1us. Local accepted pieces
now expose their already-computed event sequence; no additional force solve.

On disagreement, halve both meshes and retry from the original open-interval
predecessor only. Never synchronize the paths mid-history or replace an
already committed life. Independent fine work alone may be returned/debited
after success. Failed trials do not advance live time or spend real reserves.
Bound both total primitive trials and refinement rounds; any unresolved or
unrepresentable interval, physical failure or exhausted allowance restores
the exact original integration state/timestep. One anatomy/engine is reused
serially, with two transient numerical state buffers, not two body owners.
This is numerical error control, not an organism heuristic or motor decision.

This strengthens admission at actual sample points. It is not a continuum
error enclosure, intrinsic-couple qualification, real-time cost pass, gravity
proof, body/world integration or production authorization. Those gates remain
open. Persistent serialization/mount authority is unchanged because this new
candidate method is not connected to NativeBody.advance or production.

Native candidate SHA256
4273a731a7177dfbf297ab766f34e98c2bad9883fb7caac2835aa07d80b65756.
Next source-only frozen review precedes build. The first bounded proof will
use archived local predecessors and exact accepted controls, plus retained
173.5ms disagreement to exercise the comparator without replaying history.
Prove real bounded local trajectory, unchanged original-step results, exact
rollback on work/compute refusal, and finer-only accounting before any longer
changed-mesh trajectory. No unchanged full-motion rerun.

### FB-01aj independent-history admission proof — 2026-09-27 17:52Z

Previous turn: PROGRESS (reviewed native correction and bounded G1 P0 document
handoff). This turn: PROGRESS. The same FB-01aj numerical-accuracy item
continues; no closed optical, force, kernel, cognitive or material law reopened.

Native source-only review found localized reporting defects: preserve actual
event/impulse disagreement operands and failing lane context; prepare the final
snapshot before declaring success. Corrected together, including plain-Python
event-domain encoding. Final reviewer PASS; source SHA256
2353d94561e2c2249d4a04fe89f95f7f384fccc60f3b34b50ae48cd3e4e3fe83.
Frozen worktree823b4bb7733b4fb3bab139b0b59d5fd32d5aa0d6d12527b6cda6a90a0498aa2e.
No force/residual law, coefficient, tolerance, release time or production mount
was changed. Local and outer snapshot-before-success ordering are now truthful.

Proof source /tmp/a1-body-history-admission-20260927.py SHA256
df92e4e82dd9727ebf9bacd43f3234c602ff01c3d0603d3409ee2162b8e554ec,
retained in the receipt. Its separate source review strengthened failure-safe
operands, full observation/impulse controls, per-lane entry/exit custody, and
post-proof binary hashing. One reviewer scope concern was disproved by the
existing global declaration and withdrawn; no change was made for it.
Final source-review PASS preceded all execution.

One Radau-only isolated build succeeded:26.8748 aggregate child CPU seconds,
26.9002 wall seconds. Artifact:
/tmp/guala-body-history.wufobn6a/python/guala_body_radau.cpython-311-x86_64-linux-gnu.so
SHA25637a8624240d9e81f7911f9cf780e34beedcddffb9b2f45a9b8f5021476071dba.
The prior interval binary and physical native library were reused unchanged.

Receipt docs/evidence/FB-01aj-independent-history-admission.json SHA256
b82306f7848e436ef972b842e527ce7cb870c0f31802a08bcfc8ae4ad16d0418.
All five cases PASSED:
-26.7--26.8ms saved control: exact fine state, complete observation, impulse,
 work and supply match; fine work returned/debited once (12 primitives).
-26.7--26.9ms: two distinct independent histories each resume their own prior
 successor through two observations; no synchronization (114 primitives).
-One-trial allowance refusal: exact whole-interval state/timestep rollback,
 false completion/acceptance and correct failed-lane evidence (1 primitive).
-Zero available work: actual energetic refusal and exact rollback, no fake
 accepted motion or duplicate debit (1 primitive).
-Retained173.4--173.5ms inputs: exact prior endpoint/observation/impulse controls
 reproduce; actual event sequences and brackets agree, but the new history
 comparator correctly rejects state/sensory accuracy (74 primitives).

Total202 primitives,5324 probe forward calls,1.7977801 numerical CPU seconds,
1.8182225 numerical wall seconds. Full proof child2.644743 aggregate CPU seconds,
2.670627 wall seconds; reported peak single-process RSS165372KiB. No whole
trajectory replay. Refinement-loop recovery after an actual whole-history
disagreement was not exercised by these positive cases; do not claim it was.
The old sustained173.5ms failure is DETECTED, not erased or globally solved.

Process preflight found G1 cargo45663/rustc45999; both exited before this build.
Exact owned build49391/proof49546 exited0 with no process-group survivors;
post-run host census confirmed both absent and no body compiler/test remaining.
Bounds:2 cores,1GiB address space/process,60 CPU seconds/process,90 wall seconds
per owned group; numerical10 CPU seconds/3000 primitive allowance. Aggregate
allocator peak is not enforced or claimed. Build artifacts remain scoped under
the recorded unique temporary directory for continuation, not installed.

Read-only production envelope17:50:54--17:51:26UTC: same task1560, task
502e361c4b484240b65b4be38023dca4, same45b4591c... image and organism identity,
ticks2662374->2662482, persisted2662348->2662476, service1/1/0 HEALTHY,
checkpoint/cleanup null and durability unblocked. CPU51.26%,RAM2.99% from
the matching latest available CloudWatch sample. Existing clock-stalled ALARM
remained while ticks advanced; other four listed alarms OK. No live writes.

Next: test accumulated accuracy with ONE genuinely finer independent history
against the authenticated retained50us reference, reusing the existing reference
states/work/events rather than replaying its dynamics. Start from the same
genesis; never splice the failed173.5ms states into a shared predecessor.
Freeze/review that bounded continuation proof before execution. Preserve full
500ms/release, gravity, tactile-couple, cost, integration and restart gates as
OPEN. Neither these five cases nor compilation authorizes production delivery.
