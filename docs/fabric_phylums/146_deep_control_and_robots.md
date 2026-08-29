# 146 DEEP CONTROL AND ROBOTS — machines that act
A machine that only moves is a mechanism. A machine that notices what
it did and adjusts is a different animal, and everything hard about
robots lives in that gap. These are the laws of loops, of limbs, and
of the fact that the world will not hold still to be worked on.

ESSENCE: a controller is one idea repeated forever — look at what you
  wanted, look at what you got, and act on the difference. Thermostats,
  autopilots, cruise control, a hand reaching for a cup and a factory
  arm are all this same three-step loop running at different speeds.
ROOT: premise — a difference between an intention and a state is
  itself a quantity, and any quantity can be made to drive an action.
THREAD: the body (temperature, balance, blood sugar), money (a policy
  leaning against a trend), teaching (marking work and adjusting),
  electronics (an amplifier tamed by returning some of its output).
ASKED-AS: control loop wanted actual difference thermostat cruise adjusts feedback corrects setpoint error

ESSENCE: open loop assumes and closed loop checks. A toaster runs for
  two minutes and hopes; an oven measures its own air and holds the
  number. Open loop is cheaper, faster, and perfectly adequate right
  up until anything is different from the day it was set up.
ROOT: evidence / a plan cannot verify itself, so a machine acting
  without measurement is trusting a prediction made in advance.
THREAD: farming (watering by calendar against by soil moisture),
  medicine (a fixed dose against one titrated to effect), cooking
  (a timer against a probe), navigation (dead reckoning against a fix).
ASKED-AS: open loop closed feedback toaster timer oven sensor checks assumes blind adjusts

ESSENCE: the sensor decides the whole design. A loop can only hold
  steady what it can measure, so the choice of measurement is the
  choice of what the machine will actually be good at — and everything
  unmeasured is free to drift as far as it likes.
ROOT: evidence / a correction is computed from a reading, so anything
  absent from the readings is absent from the correction.
THREAD: people and power (an organisation optimising what it counts),
  medicine (treating a number rather than a patient), teaching (a
  syllabus shaped by its exam), money (managing to the reported figure).
ASKED-AS: sensor choice measures what controls drifts unmeasured wrong thing steady reading decides

ESSENCE: the actuator sets the ceiling. A loop can ask for anything;
  the motor, valve or heater delivers only what it has. Once the
  demand exceeds what the muscle can give, the controller is shouting
  at a thing that is already doing its utmost.
ROOT: physics / a force, a flow, or a heat has a maximum set by the
  device producing it, and no arithmetic upstream changes that.
THREAD: the body (a muscle at full contraction), cars (flooring an
  accelerator on a hill), money (a bank at a rate floor), engineering
  practice (a system fails at its weakest point).
ASKED-AS: actuator limit motor maxed out demand exceeds power sluggish flat out ceiling

ESSENCE: the setpoint is what you asked for, the error is what you did
  not get, and the whole art is what to do with that one number. Every
  controller ever built is a different opinion about how much action a
  given error deserves.
ROOT: this file / a controller acts on a difference, so the difference
  is the only raw material and every design is a way of spending it.
THREAD: teaching (a mark as distance from an expectation), money (a
  target and a deviation), the mind (a goal and the felt gap), sport
  (aiming and correcting through a shot).
ASKED-AS: setpoint target error difference how much correction wobble around never exactly measured

ESSENCE: the simplest honest answer is to push in proportion — twice
  the error, twice the effort. It is stable, gentle and predictable,
  and it has one permanent flaw: it needs an error to produce any
  push at all, so it always settles slightly short of its target.
ROOT: this file / a proportional action is a multiplication of the
  error, and a multiplication of zero is zero.
THREAD: money (a tax that only bites once a threshold is passed), the
  body (a shiver that starts only once you are cold), the home (a
  thermostat that runs a degree under on a cold day), sport (aiming off).
ASKED-AS: proportional gain never reaches target offset droop steady error stronger push oscillates

ESSENCE: integral action is patience. It adds up the error over time,
  so even a tiny persistent gap accumulates into a push large enough
  to close it. That is how a loop finally lands exactly on its number
  — and it is also how a loop learns to be late.
ROOT: mathematics / a sum over time grows without limit while its
  ingredient is non-zero, so any lasting error eventually produces any
  size of response.
THREAD: money (interest compounding on a small shortfall), people (a
  grievance built from small repeated slights), farming (soil
  depletion from a small annual deficit), the body (fluid balance).
ASKED-AS: integral term removes offset reaches target slow lag overshoot accumulates sums patience late

ESSENCE: derivative action watches the rate of change and pushes back
  against fast movement — a brake that lets a loop be aggressive
  without slamming into its target. It is also the term that listens
  hardest to noise, because noise is nothing but fast change.
ROOT: this file / a loop's danger is arriving too fast, and the speed
  of approach is available before the arrival happens.
THREAD: driving (lifting off before the corner rather than at it),
  the body (an arm slowing before the glass), electronics (a filter
  that keeps only what is changing), the mind (reacting to a trend).
ASKED-AS: derivative damping rate change noise jitter kick spikes anticipates brakes approach twitchy

ESSENCE: tuning is not a search for the right numbers. It is a choice
  on a line running from sluggish to unstable, and every position on
  that line is a statement about what you fear more — being slow, or
  being wrong in an exciting way.
ROOT: premise — the demands genuinely conflict, so there is a
  negotiated point and no maximum.
THREAD: engineering practice (a trade study whose weights decide the
  winner), the mind (caution against decisiveness), medicine (a dose
  between ineffective and toxic), sport (control against power).
ASKED-AS: tuning pid gains sluggish unstable trial error tradeoff fast stable settings load

ESSENCE: overshoot is a loop arriving with momentum it cannot shed in
  time. Push hard enough to get there quickly and you get there
  already moving, so you go past, come back, go past less — and if the
  pushing is harder still, the coming back never gets smaller.
ROOT: motion and force / a mass in motion carries energy that must be
  removed before it stops, and removing it takes both force and time.
THREAD: motion and force (a spring and its damping), driving (braking
  late), money (a policy that turns a boom into a bust), the mind
  (over-correcting after a mistake).
ASKED-AS: overshoot oscillation hunting swinging back forth too much gain ringing settles resonance

ESSENCE: delay is the enemy of every loop that has ever been built.
  A controller acting on old information is correcting a situation
  that has already changed, so its push arrives at the wrong moment —
  and past a certain delay, the correction starts arriving in time to
  make things worse rather than better.
ROOT: this file / a loop responds to a difference measured earlier, so
  the older the measurement the less the response has to do with now.
THREAD: people (a shower whose water takes ten seconds to arrive),
  money (an economy responding to policy a year later), teaching
  (feedback given a term afterwards), traffic (concertina jams).
ASKED-AS: delay lag dead time shower tap unstable slow response old information overcorrect

ESSENCE: the loop must be quicker than the thing it is chasing. A
  controller sampling ten times in the time the system takes to move
  can steer it; one sampling once has already lost. The rule is not
  about the clock speed of the computer but about the pace of the world.
ROOT: measurement / a rhythm cannot be tracked by looking less often
  than it changes, so the looking rate must be set by the physics.
THREAD: electronics (looking at least twice per wiggle), photography
  (frame rate against motion), medicine (monitoring interval against
  how fast a patient deteriorates), farming (checking a crop weekly).
ASKED-AS: sampling rate fast enough loop speed hertz between samples misses dynamics slow

ESSENCE: when an output is already at its limit, the loop stops being
  a loop — but a term that accumulates does not know that, and keeps
  piling up demand that can never be delivered. When the situation
  finally frees up, the machine acts on a mountain of stored error and
  does something enormous.
ROOT: this file / integral action sums the error regardless, and
  saturation breaks the connection between demand and effect.
THREAD: money (a debt accruing while payment is impossible), people (a
  grievance stored during a period when nothing could be done), the
  home (an oven door left open while the thermostat winds up).
ASKED-AS: windup integral saturation limit output maxed huge swing startup reset stops accumulating

ESSENCE: feedback is always late because it waits for the mistake to
  happen. If you already know what is about to hit the system — the
  load being added, the door being opened, the demanded move — you can
  push for it in advance and let the loop handle only the leftovers.
ROOT: evidence / a known cause allows a prediction, and a prediction
  can act before the effect it anticipates arrives.
THREAD: cooking (turning the heat down before it catches), driving
  (easing off before a hill crest), the body (bracing before a lift),
  money (setting aside for a known bill).
ASKED-AS: feedforward anticipate known disturbance ahead of time load added compensate model prediction

ESSENCE: what you want to control is usually not what you can measure.
  Position is wanted and acceleration is sensed; temperature inside is
  wanted and the surface is sensed. An estimator is a small running
  model that combines what is measured with what is known about the
  machine to guess at the hidden state.
ROOT: evidence / an unobservable quantity can be inferred through a
  model, and the model supplies exactly what the sensor cannot.
THREAD: medicine (inferring an internal condition from external
  signs), navigation (a position from speed and heading), money (an
  economy's state from indicators), the mind (a theory of what someone
  is thinking).
ASKED-AS: state estimator observer hidden guess model sensors indirect infer position from acceleration

ESSENCE: a filter buys smoothness with time. Averaging a jumpy sensor
  gives a calm number that is also an old one, so every gram of noise
  removed is a fraction of a second of delay added — and delay is the
  thing loops cannot survive.
ROOT: this file / delay is the enemy of every loop, and every method
  of reducing noise works by considering more of the past.
THREAD: electronics (a sharp filter and its delay), money (a moving
  average that turns late), the mind (waiting for more evidence),
  medicine (repeating a test rather than acting on the first).
ASKED-AS: filter smoothing noisy sensor average lag delayed reading jumpy calm slower response

ESSENCE: sensor fusion is not averaging. Two sensors are usually good
  at opposite things — one steady but slow, one quick but drifting —
  so the trick is to believe each where it is strong and ignore it
  where it is weak, which needs a statement of how each one fails.
ROOT: chance / combining measurements reduces error only in proportion
  to how independent they are and how well their spreads are known.
THREAD: engineering practice (redundancy defeated by common cause),
  the body (balance from eyes, ears and joints, each trusted
  differently), evidence (combining studies of unequal quality).
ASKED-AS: sensor fusion combine gyro accelerometer drift steady weights trust each disagree noise

ESSENCE: when two sensors disagree, arithmetic cannot settle it. The
  average of a right answer and a wrong one is wrong, so a system with
  redundant sensors needs a rule for which to believe — and that rule
  is where the interesting failures live.
ROOT: engineering practice / a voting scheme needs a decider, and the
  decider is a single thing that can be fooled.
THREAD: engineering practice (three channels and their voter),
  medicine (two tests that conflict), law (two witnesses), navigation
  (an instrument disagreeing with the view out of the window).
ASKED-AS: sensors disagree which believe faulty average wrong third vote redundant reading conflict

ESSENCE: degrees of freedom is the count of independent ways a thing
  can move, and it is the first number to ask about any machine. Fewer
  than the task needs and some positions are simply unreachable; more
  than it needs and there are infinitely many ways to reach each one.
ROOT: mathematics / a position in space needs a fixed number of
  numbers to describe, and each independent joint supplies one.
THREAD: the body (a shoulder, elbow and wrist as a spare-jointed arm),
  mathematics (equations and unknowns), photography (a tripod head),
  making (a fixture that must locate exactly six ways).
ASKED-AS: degrees freedom joints axes arm six reach orientation extra redundant cannot position

ESSENCE: kinematics is the geometry of linkages — where the end goes
  when the joints move, and which joint angles would put the end
  somewhere wanted. Going forwards is arithmetic. Going backwards is
  the hard direction, and often has several answers or none.
ROOT: mathematics / a chain of rotations composes into one
  transformation, and inverting a composition of rotations is not
  generally a simple or single-valued operation.
THREAD: the body (many ways to touch your nose), making (a linkage
  drawn out to check its motion), maps (a route against a destination),
  mathematics (an equation with several roots).
ASKED-AS: kinematics forward inverse joint angles reach point elbow up down solutions geometry

ESSENCE: the workspace is the set of places the machine can actually
  get to, and it is never the shape people imagine. It has holes near
  the base, thin regions at full stretch, and orientations that are
  reachable at one point and impossible a centimetre away.
ROOT: this file / a linkage's reach is set by the geometry of its
  arms, and geometry produces awkward shapes rather than tidy boxes.
THREAD: making (a tool that fits but cannot be swung), building (a
  room a piano cannot be turned in), the body (scratching your own
  back), maps (accessible ground against a straight-line distance).
ASKED-AS: workspace reach envelope robot arm cannot get holes orientation stretch base awkward

ESSENCE: at certain postures an arm loses a direction. Two of its
  joints line up, so a motion that ought to be available now requires
  an infinite joint speed — and the machine, asked to move slowly
  through that pose, lashes out or refuses.
ROOT: mathematics / the relationship between joint speed and end speed
  collapses where the geometry degenerates, and the inverse of a
  collapsed relationship is unbounded.
THREAD: navigation (a compass at the magnetic pole), maps (a
  projection breaking down at the poles), the body (a joint at full
  extension losing leverage), mathematics (dividing by zero).
ASKED-AS: singularity robot arm wrist lines up jerks stops infinite speed pose avoid

ESSENCE: there are two ways to command a machine: tell it where to be,
  or tell it how hard to push. Position control is precise and blind —
  it will crush whatever is in the way to reach its number. Force
  control is gentle and vague, and cannot hold a place at all.
ROOT: motion and force / a contact has both a position and a force,
  and specifying one leaves the other to be decided by whatever is
  touched.
THREAD: the body (pushing a door against holding a glass), making (a
  clamp set by turns against one set by torque), people (a demand
  against a request), medicine (a dose by schedule against by effect).
ASKED-AS: position control force torque command push where crushes gentle contact stiff which

ESSENCE: a stiff robot is a dangerous one. If a limb refuses to yield,
  every small error in position becomes a large force, so it breaks
  the part, the tooling, or the person. Deliberate springiness — in
  the joint, the gripper, or the control — is what makes contact
  survivable.
ROOT: motion and force / a spring's force is its stiffness times how
  far it is bent, so a very stiff element turns a tiny displacement
  into an enormous load.
THREAD: making (a bolt tightened by feel against by gauge), the body
  (catching a ball with the hands moving back), building (a joint left
  free to move), motion and force (a spring against a rigid strut).
ASKED-AS: compliance stiff robot breaks part force springy gripper yields safe contact precision

ESSENCE: planning a path is not drawing a line. The route must avoid
  obstacles, stay inside the workspace, dodge singularities, respect
  joint limits, and be smooth enough that the motors can follow it —
  so most of the straight lines a person would draw are illegal.
ROOT: mathematics / a path is a curve through the space of all joint
  positions, and the obstacles carve that space into awkward
  disconnected regions.
THREAD: maps (a route through streets rather than as the crow flies),
  chess (a sequence that must be legal at every step), building (a
  route to bring a beam through a finished structure), the mind.
ASKED-AS: path planning route avoid obstacle collision smooth joint limits straight line illegal

ESSENCE: avoiding obstacles is a perception problem wearing a motion
  problem's coat. The planning is arithmetic; the difficulty is that
  the machine must know what is there, how far away, whether it is
  moving, and whether the thing it cannot see is empty space or a
  child standing still.
ROOT: evidence / an absence of detection is not a detection of
  absence, and every sensor has a limit below which nothing registers.
THREAD: driving (a blind spot), medicine (a scan that cannot see
  small things), the mind (attention missing the unexpected),
  evidence (inspection proving no flaw larger than the method sees).
ASKED-AS: obstacle avoidance sensor cannot see glass dark thin map moment passed clear

ESSENCE: localisation is a machine answering "where am I" without
  being told. Counting wheel turns works for a while and then drifts
  hopelessly; recognising a landmark corrects it instantly. Every
  navigating machine alternates between the two, forever.
ROOT: evidence / accumulated small errors grow without bound, and only
  an external reference resets them.
THREAD: navigation (dead reckoning corrected by a star sight), the
  body (walking a straight line blindfolded and curving), farming (a
  field paced out against surveyed), the mind (losing track of time).
ASKED-AS: localisation where am i drift wheels slip landmark correct map position lost

ESSENCE: mapping and localisation are the same problem twice. To build
  a map you must know where you were standing; to know where you are
  standing you need a map. The machine has to do both at once, from
  nothing, and every error in one poisons the other.
ROOT: mathematics / two unknowns each defined in terms of the other
  must be solved together, not one and then the other.
THREAD: history (a chronology built from documents that must be dated
  by the chronology), surveying (a traverse closed back onto its
  start), the mind (learning a building by walking it), astronomy.
ASKED-AS: mapping slam building map while moving drift loop closure revisit corridor meets error

ESSENCE: repeatability is returning to the same place every time.
  Accuracy is that place being the one you asked for. Robots are
  superb at the first and mediocre at the second, which is why they
  are taught by being driven to a point rather than told its numbers.
ROOT: measurement / a consistent instrument and a true instrument are
  different claims, and a machine can be excellent at one and poor at
  the other.
THREAD: measurement (a scale precise and out by a gram), sport (a
  tight grouping off the bullseye), evidence (precision against
  correctness), making (a jig that locates rather than a dimension).
ASKED-AS: repeatability accuracy robot same spot every time wrong place taught programmed coordinates

ESSENCE: calibration drifts. Temperature moves the machine's own
  dimensions, wear moves the gearing, a collision moves a mounting,
  and the numbers that were true at commissioning slowly become
  fiction — silently, because the machine keeps hitting its taught
  points beautifully.
ROOT: evidence / a record is only as true as its last update, and
  nothing about a machine's normal operation updates its calibration.
THREAD: engineering practice (a plant diverging from its
  documentation), medicine (an instrument reading consistently high),
  making (a worn gauge passing bad parts), time (a clock drifting).
ASKED-AS: calibration drift temperature wear collision offsets wrong parts scrap machine thinks fine

ESSENCE: safety cannot rest on the program being right. A protection
  that depends on the same computer that might be malfunctioning is
  not a protection — it is a hope. Real safety is a separate circuit,
  a fence, a limited torque, an interlock that removes power
  regardless of what any software believes.
ROOT: engineering practice / two identical things share every cause
  that is not random, so a check inside the suspect system is not
  independent of it.
THREAD: engineering practice (redundancy defeated by common cause),
  making (a mechanical stop rather than a limit in code), the home (a
  lift's mechanical brake), medicine (a physical dose limiter).
ASKED-AS: safety interlock emergency stop separate circuit software cannot guard fence torque limit

ESSENCE: the danger of a robot is not intelligence, it is momentum. A
  heavy arm at speed carries energy that must go somewhere on impact,
  and the whole modern approach to working beside machines is to
  reduce that energy — lighter limbs, lower speeds, rounded surfaces —
  rather than to make the machine cleverer about people.
ROOT: motion and force / kinetic energy grows with the square of
  speed, so halving the speed quarters the injury.
THREAD: transport (energy in a crash going with speed squared), sport
  (contact rules built around mass and speed), the home (a heavy door
  closer), making (a machine guard sized by what it must contain).
ASKED-AS: robot safety speed heavy arm momentum injury collaborative slow light rounded energy

ESSENCE: a robot at power-on does not know where it is. Its joints
  report positions relative to wherever they happened to be, so the
  first act of every machine's day is finding a physical reference —
  a switch, a mark, a stop — and agreeing that this is zero.
ROOT: measurement / a relative reading has no meaning until it is tied
  once to a known point.
THREAD: measurement (a datum agreed once), navigation (a fix before
  dead reckoning is worth anything), time (setting a clock), making
  (measuring everything from one reference face).
ASKED-AS: homing power on robot doesnt know where zero reference switch incremental absolute encoder

ESSENCE: the mechanism defeats the controller. Backlash lets a gear
  turn a fraction before the load moves, and stiction makes a joint
  refuse to start until the push exceeds a threshold and then lurch.
  Both are dead zones inside which the loop's commands do nothing at all.
ROOT: motion and force / friction has a stiff setting that must be
  broken before sliding starts, and a gear train has clearance between
  its teeth by necessity.
THREAD: making (a lead screw with take-up), driving (a clutch biting),
  the body (a stiff joint in the morning), the mind (a habit that
  resists starting and then runs away).
ASKED-AS: backlash slop stiction sticks lurch gears play dead zone hunting fine movement

ESSENCE: everything flexes, and a flexible structure has favourite
  rhythms. A controller pushed harder than the structure's own shake
  will find that rhythm and feed it, so a machine that is stiff enough
  mechanically is what allows a loop to be aggressive.
ROOT: motion and force / every object answers strongly to a short list
  of rhythms, and a feedback loop that pushes near one of them is a
  loop with extra gain at exactly the worst place.
THREAD: motion and force (resonance and damping), building (a floor
  that bounces), music (a body that rings at one note), engineering
  practice (an interface carrying more than a drawing shows).
ASKED-AS: resonance flex vibration gain limit floppy structure shakes bench mounting stiff loop

ESSENCE: the machine changes as it works. A gripper picking up a heavy
  part doubles the weight the arm is carrying; a tank empties; a joint
  warms up. A tuning that was right for one condition is now the
  wrong tuning, and nothing in the loop announced the change.
ROOT: this file / a tuning is chosen for one set of dynamics, and the
  dynamics belong to the machine plus whatever it is currently doing.
THREAD: driving (an empty van against a loaded one), the body (lifting
  with an unexpected weight), flight (an aircraft handling differently
  as fuel burns), cooking (a full pan against a nearly empty one).
ASKED-AS: load changes tuning wrong heavy part gripper gravity compensation empty full dynamics

ESSENCE: fast loops go inside slow ones. Command a joint's torque in a
  tight inner loop, its speed in a loop around that, and its position
  in a loop around that — so each layer sees a simple, well-behaved
  thing underneath instead of the messy machine.
ROOT: this file / a loop can only control what responds faster than it
  does, so a hierarchy works only if each level is quicker than the
  one above it.
THREAD: people and power (delegation with each level acting at its own
  pace), the body (reflexes below decisions), engineering practice
  (systems ownership across layers), computing (nested control).
ASKED-AS: cascade inner outer loop torque speed position faster nested tuning order oscillate

ESSENCE: an autonomous machine must decide what to do when it stops
  understanding. Freeze, stop gently, hold position, go limp, or
  return to a known safe place — each is right for a different
  machine, and a machine that has not chosen will do whatever its
  hardware happens to do when the commands stop arriving.
ROOT: engineering practice / a designer nominates how a system fails
  as well as where, and an unmade choice is made by the physics.
THREAD: engineering practice (graceful degradation), driving (a car
  losing power steering), medicine (an infusion pump on power
  failure), the home (a gate on a power cut).
ASKED-AS: what happens loss signal power fail safe stop hold limp default behaviour drone

ESSENCE: a watchdog is a machine's promise to notice its own silence.
  A separate timer must be patted regularly, and if the program stops
  doing so — crashed, stuck, waiting forever — the timer runs out and
  resets or shuts down the machine on its own authority.
ROOT: evidence / a fault in a system cannot be detected by that system
  while it is faulty, so the detector must live outside it.
THREAD: engineering practice (a standby that must be exercised), the
  body (breathing driven by an independent centre), people (an
  external auditor), computing (a heartbeat between machines).
ASKED-AS: watchdog timer reset crashed hung program outside independent proof alive heartbeat stuck

ESSENCE: what looks like a robot's intelligence is usually the
  environment being made simple for it. Parts arrive in trays at known
  angles, jigs hold work in one place, floors are flat and marked.
  The engineering effort went into removing variability, not into
  coping with it.
ROOT: chance / a task's difficulty is set by the spread of the cases
  it must handle, so narrowing the spread is a direct substitute for
  capability.
THREAD: teaching (a well-set exercise against an open problem),
  cooking (mise en place), making (a jig doing the thinking), farming
  (fields planted in rows a machine can follow).
ASKED-AS: structured environment jig fixture trays known position factory robot house messy fails

ESSENCE: grasping is the unsolved part. A limb can be positioned to a
  hair, and picking up an unfamiliar object of unknown weight,
  friction, and stiffness without crushing or dropping it remains
  something a small child does better than any machine.
ROOT: evidence / a grip must be chosen from properties that are not
  visible — mass, balance, surface, and how the thing deforms — and
  vision reports only shape and colour.
THREAD: the body (fingertips as the densest sensors we have), the mind
  (knowledge that cannot be put into words), making (a craftsman's
  feel for material), medicine (palpation).
ASKED-AS: gripper grasping pick up unknown object crush drop slip touch feel vision

ESSENCE: touch is rare on robots because it is hard, not because it is
  useless. A skin that reports pressure everywhere, survives impact,
  and does not drown its computer in data has been promised for
  decades — so most machines act on vision and position, blind at the
  only moment that matters.
ROOT: making / a sensor must survive the environment it senses, and a
  touch sensor is by definition the part being hit.
THREAD: the body (skin as a whole-surface sensor), medicine (a
  surgeon's feel through an instrument), making (a fit judged by
  hand), the mind (proprioception below awareness).
ASKED-AS: touch sensor force feedback skin pressure robot blind contact peg hole assembly

ESSENCE: driving a machine from a distance puts the delay inside the
  operator's own loop. Half a second between moving a hand and seeing
  the result turns a skilled person into a clumsy one, because they
  correct what they see, which has already been overtaken.
ROOT: this file / delay in a loop causes correction at the wrong
  moment, and a human operator is a loop.
THREAD: people (a bad phone line making conversation collide), space
  (a rover commanded in daily batches), music (playing together over a
  network), medicine (remote surgery's hard constraint).
ASKED-AS: teleoperation remote control delay lag overcorrect clumsy move wait look satellite

ESSENCE: a demonstration and a deployment are separated by a factor
  nobody budgets for. A machine that succeeds nineteen times in twenty
  is a marvel in a video and a disaster in a factory, because the
  twentieth case arrives every few minutes and somebody must be
  standing there for it.
ROOT: chance / a rare failure repeated often enough becomes a frequent
  event, so a rate that looks excellent per attempt is judged per hour.
THREAD: engineering practice (the last ten per cent of a project),
  medicine (a screening test's false alarms at scale), computing (a
  prototype against a service), farming (a harvester that jams).
ASKED-AS: demo works reliability ninety percent fails often factory scale operator intervene rate

ESSENCE: the hard part of robotics has never been the mechanism. Motors,
  gears and arms have been excellent for decades. What defeats them is
  that the world will not repeat itself — the light changed, the part
  is slightly bent, the box is wet, somebody moved the pallet.
ROOT: chance / real conditions have a distribution rather than a
  value, and the tail of that distribution has no end.
THREAD: engineering practice (the risk that was not on the register),
  medicine (the patient who does not read the textbook), teaching (the
  question nobody anticipated), the mind (coping with novelty).
ASKED-AS: robots hard world varies light changed bent wet moved cases endless mechanism fine

ESSENCE: a controller can only be as good as its picture of the
  machine, and every picture leaves things out — friction, flex, slop,
  heat, the cable dragging behind the arm. A loop tuned against the
  picture meets the leftovers on the first real run.
ROOT: evidence / a model contains only what was put into it, and what
  was omitted leaves no trace in the model's own results.
THREAD: engineering practice (a model calibrated against something it
  did not design), flight (simulators for procedures and aircraft for
  feel), medicine (a trial population against a clinic), cooking.
ASKED-AS: simulation real machine different friction flex cable tuned model gap first run

ESSENCE: two separate questions decide whether a machine can be
  controlled at all. Can the thing you care about be seen from the
  sensors you have? And can it be moved by the actuators you have? A
  no to either is fatal, and no amount of controller design fixes it.
ROOT: mathematics / a system's structure determines whether its
  internal states influence its outputs and whether its inputs
  influence its states, independently of any control law.
THREAD: people and power (an authority without the means to act),
  medicine (a condition with no available lever), money (a target no
  policy instrument reaches), engineering practice (requirements).
ASKED-AS: observable controllable sensor cannot see actuator reach state loop never works hardware

ESSENCE: holding still and moving smoothly are different jobs. A loop
  can be built to reject disturbances hard while tracking a changing
  target poorly, or the reverse — and a machine tuned for one is
  routinely blamed for failing at the other.
ROOT: this file / a loop's response to a change in target and to a
  push from outside travel through different parts of the loop, so
  they can be shaped separately.
THREAD: sport (a defender against an attacker), money (stability
  against growth), the body (standing still against walking),
  teaching (holding a class steady against moving it forward).
ASKED-AS: disturbance rejection tracking following target holds still shove different tuning both jobs

ESSENCE: a motion command must be smooth in more than position. A
  perfectly correct path with a sudden change of speed demands an
  infinite force, so real planners limit acceleration and even the
  rate of change of acceleration — which is why smooth machines look
  slower and are actually faster.
ROOT: motion and force / a change in motion is force multiplied by
  time, so a change demanded in no time demands a force without limit.
THREAD: transport (a train's ride quality set by rate of change),
  the body (a smooth lift against a jerk), music (phrasing against
  hitting notes), driving (a smooth driver being a quick one).
ASKED-AS: smooth motion jerk acceleration limit corners rounded shakes settling faster slower path

ESSENCE: balancing is not a posture, it is a continuous fall being
  continuously caught. A two-wheeled machine or a walking one is
  unstable on purpose, kept upright only by a loop running many times
  a second — so the moment the loop stops, it goes down.
ROOT: motion and force / a resting thing is stable if nudging it lifts
  its weight, and these machines are built the other way round, with
  their weight above their support.
THREAD: the body (standing still is a busy activity), cycling (a bike
  steered under its own fall), flight (deliberately unstable aircraft
  flown by computer), the mind (a habit held by constant small effort).
ASKED-AS: balance two wheels falling caught segway walking unstable loop fast stops falls

ESSENCE: legs buy roughness and cost everything else. A wheel is
  enormously more efficient on a prepared surface, and a leg can cross
  ground no wheel will touch — so the choice is not about elegance but
  about whether the world in question has been paved.
ROOT: motion and force / a rolling contact is standing still and
  wastes almost nothing, while a leg must lift and place a mass on
  every step.
THREAD: the living world (why animals have legs and rivers have none),
  transport (rail's efficiency bought with a prepared path), making
  (a specialised tool against a general one), farming.
ASKED-AS: legs wheels robot stairs rough ground efficient paved step height energy walking

ESSENCE: a mobile machine carries its own energy and its own
  computer, and both are weight. Every extra sensor, processor and
  motor costs battery, which costs mass, which costs motors — so
  autonomy is bought in watts, and a tethered robot is a completely
  different and much easier machine.
ROOT: energy / a vehicle carries its own supply, so every kilogram
  added must itself be carried for the whole journey.
THREAD: energy (a vehicle's fuel as a load), flight (payload against
  range), the body (a mammal's food budget), making (weight spirals).
ASKED-AS: battery power robot weight tether cable endurance watts sensors computer heavy autonomy

ESSENCE: motors are rated for how hard they can push and, separately,
  for how long. A joint holding a heavy arm still draws full current
  and produces no motion at all, so the most demanding thing many
  robots do is nothing — and they overheat doing it.
ROOT: heat and electricity / a wire's heating grows with the square of
  the current, and a stalled motor draws its largest current while
  doing no work at all.
THREAD: the body (an isometric hold being exhausting), making (a
  mechanical stop taking a load a motor should not), electronics
  (heat as the chain from the source to the air).
ASKED-AS: motor stall holding torque overheats duty cycle continuous peak brake gearbox current

ESSENCE: a machine can be programmed, or shown. Programming states
  coordinates and is exact, brittle and slow to change; showing drives
  the machine through the motion by hand and captures it, which is
  quick and inherits every wobble and every unstated assumption of
  the person doing the showing.
ROOT: language / an instruction is a compressed copy of an intention,
  and a demonstration is a different compression that keeps different
  parts.
THREAD: teaching (explaining a skill against showing it), cooking (a
  recipe against watching a cook), craft (apprenticeship), keeping
  knowledge (a written rule against a practice).
ASKED-AS: teach pendant demonstration programming coordinates by hand recorded wobble brittle moved part

ESSENCE: the human in a supervised machine is asked to be perfect at
  the one thing people are worst at: watching something that almost
  always works, and being ready to take over instantly at the moment
  it stops. The better the automation, the harder that job becomes.
ROOT: the mind / skill and vigilance are maintained by use, and a
  reliable machine removes exactly the practice that would maintain
  them.
THREAD: engineering practice (automation and the degraded operator),
  flight (autopilots and manual practice), driving (assisted driving
  handovers), medicine (a monitor watched all night).
ASKED-AS: supervising automation watching bored takes over emergency handover attention self driving ready
