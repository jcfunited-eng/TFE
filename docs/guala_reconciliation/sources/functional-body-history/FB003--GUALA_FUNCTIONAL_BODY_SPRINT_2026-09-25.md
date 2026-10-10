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

The present commit scope is **FB-01a: exact frame composition and passive
inertial evidence**. It is a dependency of the body, not the whole deliverable.
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
