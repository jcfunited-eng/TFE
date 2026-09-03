# Guala articulated-body motor-plant causal-impact gate — 2026-09-03

## Decision status

This document completes the source-and-state analysis required before the body
repair can be packaged. It does **not** by itself authorize deployment. The
native candidate has passed two exact copied-production bodies; the final
authorization gate is the full shell-integrated proof on an immutable source
descended directly from the current live release.

Production is task definition `dsf-ai-task:1425`, release commit
`ae260276a8bbf3afd018c149871b21fa8ba185e2`. The newest exact copied production
body is tick `408275`, 112,651,490 bytes, raw SHA-256
`27555e9d78511e28a956cec3dca282a2509fbc92b8e7c83f1aa16ea63825e8e2`.
The earlier task-1420 copy at tick `391305`, raw SHA-256
`207ced0a3d0d2253a7520e05bf18eeebcf3caf25fd2b83c6450bcaf08ee86e3b`,
remains the independent historical comparison body.

## Mandatory architecture honesty gate

1. **Requested architecture:** an organism-owned deterministic action chain in
   which a particular physical thought event reaches a particular motor,
   produces bounded force in a truthful body, and returns its actual
   consequence through ordinary receptors.
2. **Current code reality:** the electrical transduction candidate can deliver
   one conserved carrier into each of the two exact learned motors, but the
   articulated body is a clamped persistent position accumulator. It has no
   muscle activation, passive elasticity, damping, inertia, mechanical-work
   store, or elapsed-time input.
3. **Conflict with requested architecture:** yes. A motor spike changes a
   permanent counter, rather than exciting a bounded contraction in tissue.
4. **Mechanisms that will not be extended:** unchanged L0-L4 and all seven DSF
   fields; the passive symmetric L11-L12 junction; the historical same-interval
   motor fan-out; the neuronal recovery-fluid reservoir as a movement command;
   a timer, pose target, label, score, shell controller, or restart reset.
5. **Single exact next item:** implement only a test-build copied-body dynamic
   range of a bounded antagonist activation plus damped passive-tissue plant;
   do not change production behavior until that range passes every falsifier
   in this document.
6. **Full DSF or reduced approximation:** neither is evaluated or changed at
   this boundary. Body mechanics is downstream of the complete DSF-to-neuron
   path.
7. **Field structure lost:** none.

## What the exact production copy proves

The read-only 45-axis census is
`/tmp/sol-axis-census/task1420-axis-census.json`, SHA-256
`b55c2d98cbfd0f73be56b37fa0b7f6835a6268a22304c19a72cb146d49c26174`.
Ten axes equal a declared limit. Three are healthy because their neutral is
that limit. Seven are non-neutral hard stops:

- right brow: `5000`, maximum `5000`, neutral `0`;
- glottis: `20`, minimum `20`, neutral `80`;
- left grip: `0`, minimum `0`, neutral `60000`;
- right grip: `0`, minimum `0`, neutral `60000`;
- vocal-tract section 0: `1000`, maximum `1000`, neutral `125`;
- vocal-tract section 6: `20`, minimum `20`, neutral `245`;
- vocal-tract section 7: `20`, minimum `20`, neutral `265`.

An exact quiescent body settlement leaves every one of those positions
unchanged, reaches no terminal, and emits no consequence. That is not an
observer inference: it is the direct successor of
`settle_body_effector_drives` on the copied body.

The production-frontier report is
`/tmp/sol-production-body-range/task1420-production-body-range.json`, SHA-256
`eb4076fe1cf3306448764625323bec04d77a6f5ecb64ebc809771b26038bba81`.
It advances only the saved native causal frontier, with no synthetic seed and
with the L11-L12 test transducer disabled. Nine layer-8-prepared motor
discharges occur in three clocks. Eight push into existing stops; only a
two-carrier right-hip discharge moves an axis. Current traffic is therefore
still working against the pins; the result is not old pose alone.

The task-1400 and task-1420 bodies provide independent temporal evidence. A
V35 migration had already returned the earlier fan-out-contaminated pose to
neutral exactly once. Task 1400 later carried three non-neutral stops; task
1420 carries seven and shows the glottis crossing from maximum to minimum.
The current plant recreated the condition after the one-time reset.

## Complete source cause

### 1. Motor discharge becomes permanent position

`virtual_articulated_body.rs::settle_body_effector_drives` sums the two
antagonist carrier counts, adds that signed count directly to the predecessor
position, clamps it to the anatomical range, and persists the result. With no
new drive, it clones the predecessor exactly. Mathematically the present plant
is:

`q[n+1] = clamp(q[n] + u_max[n] - u_min[n])`.

There is no negative term. Any nonzero mean motor traffic integrates until a
stop. Opposing traffic can reverse the axis, but it can then integrate all the
way to the opposite stop.

### 2. Load feedback is delayed direction, not tissue mechanics

The body reports reacted load only from directly opposed carriers or carriers
stalled at a stop. Its load receptor is tied to the terminal that produced
that load. The layer-8 regulation and the learned motor ancestry resolve
`load_terminal.opposing_effector()`. That is a legitimate local unloading
direction at the moment of load, but the later motor preparation does not know
current position, velocity, remaining load, or whether the old load has
already been relieved. In a plant with no passive equilibrium, delayed
antagonist pulses can overshoot and later become force in the wrong current
context.

This does not prove that the two existing learned contacts are false. It
proves only that the body on which they were learned was mechanically
incomplete. They remain preserved until the corrected plant can replay and
falsify them.

### 3. Electrical work and the Phase-1 virtual lattice boundary

`settle_efferent_terminal_transport` returns both outward carriers and exact
released electrical work. Resident cognition deposits that work into the
neuronal cohort's thermal reservoir and the transient `MotorUnitRecruitment`
carries terminal identity plus whole-carrier count.

The later authority reconciliation found that this is not an energy-custody
defect for the Phase-1 virtual body. Section 6 of
`GUALA_A013_PHYSICAL_BODY_PART_SELECTION_SPEC_2026-08-16.md` explicitly says
that the virtual lattice displacement quantum is itself the declared substrate
physics; detailed torque, transmission, efficiency, spring energy and heat are
required only for a future selected physical body. Copying the same released
work into a new body store would double-count it. The electrical work therefore
remains on its already-conserved neuronal thermal route, while the typed whole
carrier establishes bounded virtual activation instead of permanent position.

### 4. The body plant has no duration

Native neuronal contact and recovery settlement uses the declared 1 ms world
mechanical tick. Body-proprioceptive evidence likewise encodes adjacent ticks
at 1,000 ticks per second. However,
`settle_motor_recruitments_into_articulated_body` and
`settle_body_effector_drives` receive no elapsed time. A 250 ms sensory source
does carry its real duration into the 16 kHz acoustic renderer, while its
position-changing motor call still has no duration argument. Discrete-event
neural residency may also skip silent internal clocks, while the body sees
only the eventual call.

Therefore no relaxation, activation decay, damping, or force integration can
be added honestly until the copied-body harness varies exact elapsed time and
the production boundary carries it. A coefficient “per call” would merely
replace one clock bug with another.

## Biological equivalent and what Guala lacks

A biological motor-neuron discharge does not increment joint angle forever.
It produces a muscle twitch whose activation rises and decays; antagonist
force, passive muscle/tendon elasticity, damping, joint geometry, external
load, and inertia determine motion. Length and load receptors then observe
the resulting tissue state.

Two primary measurements constrain the shape without authoring Guala's
numbers. Hoang et al. measured a passive equilibrium position created by
opposing muscle elasticity, and showed that cutting antagonist tendons shifts
that equilibrium:
https://pmc.ncbi.nlm.nih.gov/articles/PMC3725263/ . Thelen's dynamic
musculotendon model separates activation/deactivation dynamics from
contraction and elastic-tendon dynamics; its cited young-adult preparation
uses faster activation than deactivation rather than an eternal step:
https://pubmed.ncbi.nlm.nih.gov/12661198/ . Millard et al. show that a damped
equilibrium musculotendon model can be both energy-checked and computationally
efficient:
https://doi.org/10.1115/1.4023390 .

Guala already has the fixed antagonist terminals, declared neutral positions,
position receptors, exact reacted-load receptors, motor-neuron electrical
work, and a 1 ms native physical clock. It lacks the middle plant that turns
those ingredients into a finite twitch and equilibrium.

## Causal impact across the organism

### Speech and self-hearing

The glottis and three tract sections are pinned. The accepted-v22 acoustic
organ therefore receives an extreme or historically accumulated tract pose,
not a fresh sustained gesture. A one-carrier thought-to-motor event can create
load pressure but no tract displacement. This is sufficient to explain why
the electrical bridge proof did not become a new audible articulation; it
does not by itself prove every remaining voice coefficient correct.

### Autonomous action witness

The electrical candidate already supplies sparse action-specific motor
pressure and passes severance. Deploying it now would make thought drive two
stopped vocal terminals. Calling that visible self-caused action would be an
overclaim. The plant repair must let the same exact learned motor discharge
produce bounded movement and returned sensation before the choice witness is
released.

### Grip, contact, face, posture, and play

Both grips are maximally closed, one brow is maximally raised, and many other
axes hold large non-neutral displacements. Grasp, release, touch, expression,
and watched companion activity can therefore begin from physically false
postures or accumulate toward stops. Environment improvements cannot correct
that internal body law.

### Learning and memory

Receptors truthfully recorded the consequences the old plant actually
produced. Those sensory records and all L0-L4/DSF/neuron/formation/mosaic state
must remain. Learned motor contacts formed from those episodes are quarantined
as “unvalidated under corrected tissue,” not deleted. After repair, each route
is judged only by replay through its exact retained anatomy. A route that
still produces a bounded movement and consequence remains; any future
retirement would require route-specific physical invalidity proof and a
separate approved migration.

### Persistence and restart

The extreme positions are in the authenticated body codec and correctly
survive restart. A new migration that writes neutral would erase state and
would repeat the already-failed V35 strategy. The replacement must decode the
current pose unchanged, then let ordinary passive mechanics move it over lived
physical time. Cold restore must resume the same mechanical state, not replay
or reset it.

### Compute and runaway risk

Stopped motor work creates load episodes, receptor work, layer-8 regulation,
contact settlement, evidence, and persistence without useful displacement.
That is bounded in each interval but wasteful and can continuously reawaken
the causal frontier. The replacement must remain fixed-size and must not add a
per-sample history. It should operate on the 45 fixed axes and 90 fixed
antagonist terminals only, with no allocation proportional to lifetime,
neuron count, or event count.

### Observation truth

The existing articulation receipt distinguishes applied and stalled motor
quanta, but the public description can still make pressure/self-hearing sound
like successful articulation. The observation surface must separately expose
motor work admitted, position changed, stop load, passive return, and acoustic
pressure. Observation remains read-only and cannot trigger any of them.

### Python world-action boundary

The native body is also a caller of the Python world-action preparation path.
That path historically assumed every body displacement was caused by new
same-interval motor carriers and inferred grasp/release from the sign of grip
travel. Damped tissue invalidates both assumptions: an off-neutral grip can
move passively, and retained activation can continue motion after the original
discharge. Leaving that caller unchanged would refuse lawful passive
proprioception and could turn relaxation into a false world command.

The replacement must therefore keep passive body consequences in the ordinary
sensory-return interval while excluding them from motor-action identity and
from grasp/release authority. A grip command may arise only when newly
admitted, non-stalled grip activation and actual displacement agree in
direction. Root locomotion remains a separate typed motor path, and the
world's root pose is never rewritten by passive articulated-body mechanics.

## Repairs explicitly rejected

- **Another neutral reset:** already disproved by V35 and destroys current
  body state.
- **Suppressing a motor at a stop:** hides real isometric force and deletes the
  load signal instead of repairing the plant.
- **Only retaining the clamp:** prevents numerical overflow but preserves the
  accumulator and the waste loop.
- **A shell pose controller or recurring “return to neutral” command:** gives
  observation or a timer motor authority and duplicates biology in Python.
- **A magic leak from the position counter:** has no work accounting and is
  call-rate-dependent without elapsed time.
- **Deleting learned contacts now:** violates preservation and confuses a bad
  plant with proved false memory.
- **Using the neuronal energy reservoir as direction or vigor:** it can price
  neural work, but it contains no body-axis or terminal authority.
- **Restoring broad coincidence fan-out:** recreates the retired 96,686-contact
  cascade.

## Recommended replacement: bounded damped-equilibrium antagonist tissue

The recommended smallest honest plant is a fixed-size damped-equilibrium
actuator, not a simulated human skeleton:

1. Each of the 90 existing antagonist terminals owns one bounded integer
   activation quantity. A real motor discharge supplies the already-declared
   Phase-1 whole-carrier lattice quantum; its electrical work remains on the
   unchanged neuronal thermal-return route.
2. Activation rises from admitted carriers and decays over exact elapsed physical
   time. A single discharge therefore becomes a finite twitch. Continued
   posture requires continued organism-owned discharge.
3. Each axis retains its present position. Net antagonist activation acts
   against a passive elastic equilibrium at the already-declared neutral;
   damping makes the implicit step energy-descending. No target pose or action
   name exists.
4. Carrier admission, opposition, activation capacity, displacement and stop
   load close exactly on the fixed integer lattice. No second energy account
   is created for the Phase-1 virtual body.
5. Position and load receptors remain the only return path. Passive movement
   creates position consequences; active force at a true stop creates load.
6. The codec keeps fixed arrays only. Current positions decode byte-for-byte;
   absent new activation fields initialize with zero stored activation, so the
   old pose relaxes through the new physical law rather than teleporting.

An overdamped equilibrium model is recommended over a full inertial skeleton
for this first body because it supplies exactly the missing properties—finite
activation, passive equilibrium, damping, duration, and energy descent—without
adding velocities, collision histories, or a world-scale rigid-body engine.
It is an artificial-body preparation, not a claim of human anatomy.

The activation/deactivation and passive-equilibrium constants are **not yet
authorized**. Human measurements define a biologically plausible range but
do not define this artificial body. The dynamic copied-body harness must show
the complete stable range first; the selected preparation must then be
declared once as body material, never fitted per sound, action, or axis event.

## Exact copied-body authorization matrix

The next test-build-only harness must start with a read-only AWS health check,
must use the exact raw body named above, and must write only to a new temporary
directory. It must test a matrix, not one guessed coefficient.

The matrix varies activation rise/decay duration, passive-equilibrium time,
damping, motor-work coupling, elapsed physical interval, repeated drive, and
opposed drive. It must include at least the copied body's seven non-neutral
stops, both learned L11-L12 routes, all nine saved-frontier reflex discharges,
neutral axes, and one deliberately sustained posture.

Every accepted point must prove all of the following:

- input raw body SHA and identity are unchanged;
- L0-L4, all DSF fields, neurons, sensory residues, formations, mosaics,
  learned contacts, and world bytes are unchanged by the plant-only run;
- zero motor work at neutral produces exactly zero movement;
- a displaced unpowered axis moves monotonically toward equilibrium over
  elapsed time, never teleports and never crosses equilibrium;
- a one-carrier learned discharge creates nonzero movement before relaxation
  and returns a sparse exact position consequence;
- a same-direction discharge at a stop creates bounded load but no ratchet;
- an opposing discharge at a stop releases the axis;
- repeated finite drive reaches a finite interior equilibrium, or a true stop
  only when admitted work exceeds opposing passive work;
- severing the two learned contacts yields zero learned activation while the
  pre-existing reflex path is unchanged;
- total mechanical work is conserved or explicitly dissipated at every step;
- 1 ms, multi-ms, 250 ms, and skipped-clock integration agree for the same
  physical duration within exact lattice quantization;
- encode/decode and cold restore resume the same position and activation
  state;
- no unrelated motor, axis, or receptor changes;
- no unbounded collection, process survivor, CPU cascade, RAM rise, or storage
  growth occurs.

No candidate proceeds to production source until the whole accepted region,
its rejecting boundaries, the exact copied-body output hash, and every failed
harness attempt are appended to the repair-attempt history.

## Copied-body lower-bound and artificial-control result

The first completed dynamic lower-bound used raw task-1420 body SHA-256
`207ced0a3d0d2253a7520e05bf18eeebcf3caf25fd2b83c6450bcaf08ee86e3b`
at tick 391305. Report
`/tmp/sol-task1420-passive-range.U8ZGfM/task1420-passive-range.json`, SHA-256
`fca6c12f247eced175bd062709cc6cfb8ac2cd4b3c803e7cdbd334f5b82d94b7`,
766,592 bytes. The exact integer-power evaluator completed the body work in
0.23 seconds. All ten passive time constants (1, 2, 4, 8, 16, 32, 64, 128,
256, and 512 ms) preserved neutral, remained inside anatomy, moved every
off-neutral axis monotonically toward neutral, composed 64+186 ms exactly to
250 ms, and released all seven copied non-neutral stops by 16 ms or sooner.

This lower bound rejects a passive-only repair. Against sustained rates of 1,
2, 4, 8, and 16 carriers per millisecond in both directions, slower passive
return increasingly permits finite-span stop pressure. Time constants 1 and 2
ms prevent finite-span stop pressure throughout this deliberately severe
range; 4 ms first fails at 16 carriers/ms toward minimum, and longer constants
fail at progressively lower rates. A 1-2 ms global return would be a stiff
universal spring and still supplies no finite retained activation or honest
motor-work store. It cannot represent a sustained gesture. The dynamic
activation/work portion of the authorization matrix remains mandatory.

Ten directions have zero travel from neutral to one declared boundary: cheek
raise, jaw opening, lip aperture, elbow flexion, and knee flexion toward
minimum; and grip aperture toward maximum, bilaterally where applicable. This
is not automatically pathological. It describes ordinary relaxed anatomy at
one end of a one-sided coordinate. Motor work into such a direction is
isometric stop load and must be sensed and dissipated, not used as evidence
that the whole axis is pinned.

The precise artificial control is
`/tmp/sol-task1420-passive-range.U8ZGfM/task1420-seven-axis-unpin.json`, SHA-256
`61724b4811acf92f4cc9d94faa5333ca89d1bd653838ed4534f56571362dfb14`,
25,285 bytes. It changed only the seven copied non-neutral stopped positions to
their declared neutrals and preserved the other 38 positions, lung air,
proprioception flag, acoustic state, cognitive body, and learned anatomy. The
ordinary retained first clock then moved glottis `-1`, left grip `-3`, and
right grip `-2`, all with zero stall. Under the bounded one-carrier learned
bridge falsifier, the two exact L11-to-L12 routes additionally moved vocal
tract section 0 `+1` and section 7 `-1`, both with zero stall. Their two
consequences produced eight native source ports, sixteen samples, and nine DSF
deliveries on return.

Therefore accumulated positions are the immediate obstruction to otherwise
working reflex and learned motor output. Artificial restoration is useful only
as this causal control. It remains prohibited as the repair because it erases
physical history and the unchanged accumulator would recreate the pins.

## Exact terminal-work measurement

The copied-body work range is recorded at
`/tmp/sol-task1420-passive-range.U8ZGfM/task1420-motor-work-range.json`, SHA-256
`b8338056c79ad4e65e211d336cd3cb41d0588e67c113a21b17dd3488d57b1c0a`.
The two learned vocal motors each discharged one requested whole carrier and
released, respectively,
`166767809696532795445407/1100000000000000000000000` and
`36616220961176220112151901/237050000000000000000000000`
zeptojoules. The retained L11-to-L12 routes reproduced those same terminal
values exactly. Thus the body candidate does not need an invented work source:
it must transfer the terminal law's already-computed exact work out of the
neuron settlement transaction and into bounded terminal activation. Only
declared conversion loss and later mechanical dissipation may return as heat.

V7 persistence cannot satisfy that law because it stores neither the 90
terminal activations nor general mechanical work. The production repair, if
the activation range passes, necessarily includes a fixed-width body version
migration that decodes every V7 position unchanged and initializes only the
previously nonexistent activation fields at zero. This is non-erasing: the
seven stopped positions must leave their stops through lived passive mechanics,
not through decode-time neutralization.

## Accepted antagonist-activation region

The second copied-body activation matrix is
`/tmp/sol-task1420-passive-range.U8ZGfM/task1420-antagonist-activation-range-v2.json`,
SHA-256
`e04a9b0ded18821dcb116bc09a688db0efadf912ce1fb0226baa7a64c7ca4769`.
Twenty-four of 147 points pass: discrete coupling `1/1`, activation lifetime
`16, 32, 64, or 128` ms, and overdamped response time `2, 4, 8, 16, 32, or 64`
ms. The shared accepting region releases every copied legacy stop without
decode mutation, retains both learned one-carrier vocal twitches, cancels
equal antagonists, keeps low sustained drive interior, converts saturation to
bounded load, composes elapsed duration exactly, and closes work.

The first work-retention representation is permanently rejected: decaying a
stored exact-rational energy fraction each millisecond grows its denominator
with lifetime and exhausted the bounded 120-second harness. The accepted model
instead retains fixed integer terminal cross-bridge activation, while the
motor's exact released work crosses once into the body transaction and is
accounted exactly as body dissipation. This changes the future codec impact:
V8 needs only 90 bounded integer activation quantities in addition to the
unchanged V7 body, not 90 rational-energy accumulators. No history, event list,
or per-sample state is introduced.

The region is not yet one authorized material preparation. The next copied
integration uses representative interior points and must show the exact
cognitive successor, learned severance control, sparse proprioceptive return,
current-pose V7-to-V8 migration, V8 cold identity, and flat resource use. Only
that integrated proof may select the single body material constants.
