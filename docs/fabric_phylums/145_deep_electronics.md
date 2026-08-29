# 145 DEEP ELECTRONICS — circuits that do things
File 85 handled push, flow and the loop. This is the floor above it:
what changes once a wire stops merely delivering energy and starts
carrying a meaning — a shape in time that must survive noise, get
switched, counted, amplified, and turned back into the world.

ESSENCE: two completely different jobs travel down wires that look
  identical. A power circuit only has to deliver energy, and nobody
  cares what shape it arrives in. A signal circuit has to deliver a
  shape, and the energy is only the vehicle carrying it. Almost every
  design rule flips between the two.
ROOT: premise — a wire carries a quantity over time, and everything
  about the design depends on whether the quantity is the product or
  the pattern is.
CANNOT: no judging a signal wire by whether the power arrived — it can
  be perfectly adequate in energy and worthless in shape. And no
  ignoring the power side when designing a signal: the meaning rides
  on top of a supply, so a supply that wobbles rewrites the message.
THREAD: language (a shout that arrives loud and unintelligible),
  plumbing (a pipe delivering water against a pipe delivering a
  pressure signal), music (loudness against tune).
ASKED-AS: power cable signal wire difference audio hum mains carries meaning energy shape matters

ESSENCE: a signal is nothing but a voltage that changes as time
  passes. Sound, temperature, a heartbeat, a picture, a spoken word —
  all of them enter a circuit as one wiggling voltage, and once inside
  the circuit has no idea what any of it meant.
ROOT: measurement / a quantity in the world can be stood in for by a
  quantity in a machine, and the standing-in is the whole trick.
CANNOT: no circuit that knows what its signal represents — it only
  knows the numbers, so the meaning must live in the design and the
  reading. And no signal without a time axis: a single instant of
  voltage carries nothing, because a shape needs duration to exist.
THREAD: writing (marks standing in for sounds), maps, music (a groove
  in a record is one wiggle carrying an orchestra), the body (a nerve
  carrying pain and light down chemically identical lines).
ASKED-AS: signal voltage over time microphone sensor wiggle waveform represents sound picture reading

ESSENCE: every wire carries a little random hash that nobody put
  there — the jostling of warm atoms, the graininess of charge, and
  stray pickup from every machine in the building. Noise is not a
  fault to be found. It is a floor that exists in a perfect circuit.
ROOT: physics / matter comes in discrete jiggling pieces, so any real
  conductor is a small crowd in permanent random motion.
CANNOT: no circuit with zero noise at any price — the floor can be
  lowered by cooling, narrowing, and care, and never removed. And no
  signal smaller than the floor being recovered by better equipment:
  once it is under, it is not there to find.
THREAD: photography (grain in a dark picture), astronomy (a faint star
  under the sky's own glow), the mind (hearing a name in static),
  chance (a small true effect buried under variation).
ASKED-AS: noise hiss static electrical interference floor random why always there faint signal

ESSENCE: the number that matters is never how big a signal is — it is
  how big it is compared with the noise beside it. A tiny signal in a
  quiet place beats a big one in a noisy place, and a circuit's real
  quality is how little it adds to that ratio as the signal passes.
ROOT: this file / noise is a floor, so a signal only exists as far as
  it stands above one.
CANNOT: no recovering information from a signal buried under the
  noise, however much it is magnified. And no stage that improves the
  ratio by amplifying: everything after the first stage sees the noise
  already mixed in, so the first stage sets the ceiling for all of it.
THREAD: photography (a bright lens beats a high sensitivity setting),
  medicine (a test's answer against its scatter), teaching (a clear
  voice in a quiet room), evidence (an effect against its own noise).
ASKED-AS: signal to noise ratio quiet recording amplify hiss louder first stage clean

ESSENCE: turning the volume up magnifies the noise exactly as much as
  the signal, so it never rescues anything. What helps is collecting
  more signal at the start, keeping the noise out on the way in, or
  refusing to listen to the parts of the range where the signal is not.
ROOT: this file / signal-to-noise is a ratio, and multiplying both
  halves of a ratio by the same number changes nothing.
CANNOT: no gain improving what has already been lost. And no fixing a
  bad first stage anywhere later in the chain — the damage is done in
  the first centimetres, which is why the delicate amplifier is put at
  the sensor and not at the far end of the cable.
THREAD: photography (cropping does not add detail), the mind (asking
  someone to repeat rather than shout), cooking (no seasoning rescues
  a poor ingredient), keeping knowledge (a bad copy copied bigger).
ASKED-AS: turn up gain louder still noisy amplify preamp near sensor long cable weak

ESSENCE: analogue and digital are not two technologies. They are one
  decision about noise. Analogue keeps the whole shape and accepts
  that every copy is slightly worse. Digital throws the shape away,
  keeps only high-or-low, and can therefore be copied forever.
ROOT: this file / noise adds at every stage — so the choice is whether
  to carry a value that noise can shift, or a verdict that noise must
  overturn entirely to change.
CANNOT: no analogue chain that does not degrade with length and
  copying. And no digital signal that is immune rather than tolerant:
  it survives because the noise is smaller than the gap between high
  and low, and when noise exceeds that gap it fails suddenly and
  completely rather than gracefully.
THREAD: keeping knowledge (a photocopy of a photocopy against a
  retyped text), music (tape hiss against a file), language (a spoken
  number against a written one), voting (a count against a shove).
ASKED-AS: analogue digital difference why better copy tape record noise threshold high low bits

ESSENCE: a digital circuit does not read a voltage, it takes a view.
  Anything above one line is called high, anything below another is
  called low, and the gap between the lines is the entire defence
  against noise. Widen the gap and the circuit is tougher and slower.
ROOT: this file / digital is a verdict rather than a value, and a
  verdict needs a threshold to be a verdict at all.
CANNOT: no noise immunity without wasting voltage on that gap — the
  margin is bought from the supply. And no signal sitting in the gap
  being safe: a voltage between the two lines is read differently by
  different chips on the same board, which is how one lazy edge makes
  a fault that moves around.
THREAD: law (a legal threshold turning a continuum into two states),
  exams (a pass mark), medicine (a cut-off deciding a diagnosis),
  sport (in or out with nothing in between).
ASKED-AS: logic level high low threshold volts between undefined noise margin marginal flaky board

ESSENCE: there is no such thing as a single ground. Ground is a piece
  of metal with resistance, carrying every return current in the
  circuit, so two points both called ground sit at slightly different
  voltages — and a signal measured against the wrong one has that
  difference added straight into it.
ROOT: electricity / a voltage is only ever a difference between two
  points, and any real conductor develops a difference along it when
  current flows.
CANNOT: no two grounds being the same point unless nothing flows
  between them. And no clean measurement of a small signal referenced
  to a ground that also carries a motor's current: the motor's own
  return appears in the reading, indistinguishable from the signal.
THREAD: measurement (a datum agreed once so everyone's numbers meet),
  building (a level line surveyed from two different benchmarks),
  money (two ledgers both claiming to be the record).
ASKED-AS: ground noise hum buzz two grounds different voltage return current reference point measurement

ESSENCE: grounding is the commonest fault in electronics because it is
  the part that looks like nothing. A ground connection is drawn as a
  little symbol with no properties, so it gets no thought — while in
  the real board it is a shared road every current drives down.
ROOT: the mind / attention follows what is drawn, and the schematic
  draws grounds as identical symbols rather than as one shared piece
  of metal.
CANNOT: no finding a grounding fault by studying the schematic — the
  schematic is precisely where the information was thrown away, so it
  is found with a meter, a scope, and a walk of the physical board.
  And no rule of thumb that survives: it depends on the layout.
THREAD: engineering practice (the interface nobody owned), building
  (the drain everyone assumed somebody else had run), plumbing,
  software (the shared variable nobody thought of as shared).
ASKED-AS: grounding problem hum buzz mystery fault schematic looks fine layout board earth

ESSENCE: a loop of ground wire is an aerial. When two boxes are joined
  by a signal cable and both are also earthed at the wall, the pair
  makes a closed ring, and any magnetic field passing through that
  ring drives a current round it — which appears in the signal as hum.
ROOT: electricity / a changing magnetic grip on a loop drives a
  current in it, and nothing about the loop being made of ground wire
  exempts it.
CANNOT: no ground loop without a loop — the cures all break the ring
  (one earth point, an isolating transformer, an optical link), and
  none of them work by adding more earthing. And no ground loop in a
  battery-powered box, which is why the fault vanishes on the bench.
THREAD: engineering practice (a fault that disappears in test), the
  home (a buzz that starts when the aerial is plugged in), music
  (studios wired to a single star point), electricity (induction).
ASKED-AS: ground loop hum buzz two devices plugged in aerial isolator earth lift studio

ESSENCE: every current that goes out must come back, and it comes back
  by the easiest path it can find — which at high speed is the metal
  directly underneath the outgoing wire. So the return path is part of
  the signal, and interrupting it moves the current somewhere unplanned.
ROOT: electricity / charge does not pile up, so a complete loop exists
  for every current whether the designer drew one or not.
CANNOT: no signal without its return, so no such thing as a one-wire
  connection. And no slot, gap or split in a ground plane being
  harmless: the return has to detour round it, making a large loop
  that radiates and picks up, from a change that looks cosmetic.
THREAD: plumbing (no flow without a way back), traffic (a closed road
  sending everything down a lane), motion and force (force flowing
  through a solid and crowding at a gap).
ASKED-AS: return path ground plane slot cut under trace loop radiates emissions high speed

ESSENCE: every source has a stiffness and every load has an appetite,
  and the two argue over the voltage. A stiff source barely sags when
  a hungry load pulls; a weak one collapses. This one relationship
  decides whether connecting two working things gives a third.
ROOT: electricity / every real path charges a toll, including the
  paths inside a source, so a load's draw is always partly spent
  before it leaves the source.
CANNOT: no source holding its open-circuit voltage into a load. And no
  connecting two circuits without changing both: the load alters what
  the source does, and the source alters what the load receives, which
  is why two blocks that each worked alone can fail as a pair.
THREAD: engineering practice (parts each right and the whole wrong),
  people (two good speakers in a bad conversation), plumbing (a tap
  that dies when another is opened), money (a price where two meet).
ASKED-AS: impedance source load sags connecting two circuits voltage drops stiff weak drive

ESSENCE: matching means two opposite things. For power, you match the
  load to the source to get the most across. For signals, you match
  the cable to both ends so nothing bounces back — and a mismatch at
  speed sends an echo down the wire that arrives late and lies.
ROOT: physics / waves reflect wherever the medium changes, and a cable
  carrying a fast edge is a medium, not a piece of string.
CANNOT: no maximum power transfer without wasting half of it in the
  source — the matched condition is the efficient one for signals and
  the wasteful one for energy, so the two goals cannot both be served.
  And no ignoring reflections once the edge is faster than the trip
  down the wire and back.
THREAD: sound (a loudspeaker and a room), waves (an echo from a change
  of medium), plumbing (water hammer at a sudden closure), light
  (reflection at every boundary between materials).
ASKED-AS: impedance matching ohms cable terminator reflection ringing antenna speaker echo fast

ESSENCE: two resistors in a line make a voltage smaller by a chosen
  fraction — and that is the seed of nearly everything. Set a
  threshold, read a sensor, bias a transistor, sense a current: they
  are all this one arrangement, dividing a push in a ratio you own.
ROOT: electricity / in a series path everything shares one current and
  splits the push, so the split follows the ratio of the tolls.
CANNOT: no divider that holds its ratio into a load — the load is a
  third resistor and it joins the sum, so a divider feeding something
  hungry does not deliver what the arithmetic said. And no dividing a
  voltage up: this arrangement can only ever go down.
THREAD: money (a share split by agreed proportions), motion and force
  (a lever's ratio), cooking (dilution), making (a gear ratio).
ASKED-AS: voltage divider two resistors half sensor reading ratio loading changes wrong bias

ESSENCE: an instrument put onto a circuit becomes part of that
  circuit. A meter draws a little current, a scope probe hangs a small
  capacitance on the node, and delicate circuits change their
  behaviour the moment they are watched — sometimes into working.
ROOT: evidence / every measurement is a measurement of the instrument
  and the subject together, and nothing separates them for free.
CANNOT: no observation without loading — the only choice is how
  little. And no trusting a fast measurement made with a slow probe:
  the probe's own capacitance rounds off the edge it was brought in to
  look at, so the picture on the screen is the probe's opinion.
THREAD: engineering practice (a rig that changes what it holds),
  measurement (a thermometer that must take heat to learn), the mind
  (a question that changes the answer), medicine (white-coat readings).
ASKED-AS: probe loading scope meter changes circuit works when measuring capacitance ground lead

ESSENCE: put a resistor in front of a capacitor and you have built a
  clock. Charge trickles in through the toll and fills the bucket at a
  rate that slows as it fills, so the voltage always climbs the same
  curve — most of the way in one time constant, effectively there in five.
ROOT: electricity / a capacitor's voltage is set by how much charge is
  in it, and a resistor decides how fast charge can arrive.
CANNOT: no capacitor jumping to its final voltage, however sudden the
  switch — the climb is unavoidable, which is why every real edge has
  a slope. And no separating the two parts: only the product of
  resistance and capacitance matters, so many different pairs give an
  identical delay.
THREAD: cooking (a pan approaching oven temperature), the body (a drug
  reaching a steady level), money (compound interest run backwards),
  chance (a decay that always keeps the same fraction).
ASKED-AS: rc time constant delay charging capacitor curve five times slow edge timer

ESSENCE: because a capacitor takes time to charge, it lets quick
  wiggles through and blocks slow ones — and a coil does the reverse.
  Put either in a signal's path and you have built a sorter that keeps
  one speed of change and discards another. That is all a filter is.
ROOT: this file / a capacitor's climb takes time, so a change faster
  than that time passes across it while a slow one is followed and
  cancelled.
CANNOT: no filter that separates two things at the same speed — it
  sorts by rate of change alone, so noise inside the signal's own band
  is untouchable by any filter ever built. And no sorting without
  losing: everything kept is also delayed.
THREAD: music (tone controls and crossovers), the ear (separating
  pitches), farming (a sieve sorting by size and nothing else), the
  mind (attention keeping one rhythm of events).
ASKED-AS: filter high pass low pass capacitor cuts noise bass treble crossover rumble sorting

ESSENCE: a filter cannot be both sharp and quick. Making the boundary
  between kept and discarded steeper means the filter must watch the
  signal for longer before it commits — so every gain in sharpness is
  paid for in delay and in a wobble at the edges.
ROOT: physics / waves add, and telling two nearby rhythms apart
  requires observing enough cycles for their difference to show.
CANNOT: no filter with a vertical edge and no delay. And no removing
  a noise close in frequency to the signal without damaging the signal
  — sharpening the cut only moves the damage into ringing and phase,
  which is a different disfigurement, not an absence of one.
THREAD: measurement (a fast reading against a precise one), the mind
  (a snap judgement against a considered one), photography (shutter
  speed against noise), law (a quick verdict against a careful one).
ASKED-AS: filter sharp steep delay ringing cutoff slope tradeoff response fast precise wobble

ESSENCE: a power rail is not a rail. Every time a chip switches, it
  grabs a gulp of current, and the wire back to the supply is too slow
  and too long to deliver it — so a small capacitor is placed beside
  each chip as a private local reservoir, refilled between gulps.
ROOT: this file / a coil-like wire fights sudden changes of current,
  so a distant supply cannot answer a demand that arrives in a
  billionth of a second.
CANNOT: no fast digital circuit working without local reserves — the
  rail sags on every edge, and a sagging rail is read as a logic error
  somewhere else on the board. And no reservoir working if it is far
  away: the value on the schematic matters less than the distance.
THREAD: the home (a header tank near the shower), farming (a water
  butt beside the greenhouse), logistics (stock held at the shop and
  not the depot), the body (glycogen stored in the muscle that uses it).
ASKED-AS: decoupling capacitor bypass close to chip supply sag glitch rail noise reservoir switching

ESSENCE: a coil stores energy in the field around it and insists on
  keeping its current going. That insistence is a nuisance when you
  open a switch and a gift when you build a converter: chop the supply
  on and off and the coil smooths the chopping into a steady flow.
ROOT: electricity / a changing current fights itself through its own
  field, so a coil resists any attempt to stop or start it suddenly.
CANNOT: no opening a loaded coil quietly — the current's insistence
  appears as a spark or a voltage spike large enough to destroy the
  switch, which is why every relay and motor gets a path for it. And
  no coil storing much in a small space: energy in a field is bulky.
THREAD: motion and force (a flywheel's refusal to stop), plumbing
  (water hammer when a valve slams), the home (a boost converter in
  every torch), cars (an ignition coil making thousands of volts).
ASKED-AS: inductor coil spike relay clicking flyback diode switching converter smoothing spark energy

ESSENCE: a diode is a one-way door for current, and it charges a fixed
  toll to open — a little under a volt, no matter how much is passing.
  That fixed toll is why a diode is both the simplest protection in
  electronics and a persistent small waste in every power path.
ROOT: electricity / a junction between two differently doped
  semiconductors passes charge easily one way and almost not at all
  the other.
CANNOT: no diode with zero forward drop, so no lossless one-way valve
  — at high current the toll becomes real heat. And no diode blocking
  in reverse forever: past its rated backward push it breaks down and
  conducts, which is a failure in one part and the whole purpose of
  another.
THREAD: plumbing (a non-return valve), the body (heart valves and vein
  valves), law (a one-way permission), making (a ratchet).
ASKED-AS: diode one way current backwards protection voltage drop point seven volts reverse blocking

ESSENCE: rectification is making a back-and-forth flow into a one-way
  one by simply refusing half of it, or by flipping the wrong half
  over. What comes out is not steady — it is a series of humps — so
  every mains-powered thing contains a rectifier and then a smoother.
ROOT: this file / a diode passes one direction only, so an alternating
  push driving diodes produces a lumpy but one-directional flow.
CANNOT: no chemistry, chip, or battery running on the alternating form
  — the conversion is compulsory, not a convenience. And no rectifier
  producing a smooth output on its own: the humps are inherent, and
  removing them is a second, separate job.
THREAD: the home (every charger brick), the body (nerves as strictly
  one-way pulses), farming (a mill wheel taking only one direction),
  water (a tidal barrage working on both flows or one).
ASKED-AS: rectifier bridge diodes mains dc converts humps ripple charger adapter alternating smoothing

ESSENCE: regulation is a circuit whose whole job is to hold a voltage
  still while the world tries to move it — the mains sagging, the load
  suddenly doubling, the temperature rising. It does this by measuring
  its own output and continuously correcting, thousands of times a second.
ROOT: this file / negative feedback holds a quantity against
  disturbance by turning the difference into a correction.
CANNOT: no regulator holding an output it cannot measure — anything
  after the sensing point, including the wire to the load, drops
  voltage the regulator never sees. And no regulator faster than its
  own loop: a sudden load step always causes a dip before the
  correction arrives.
THREAD: the body (temperature and blood sugar held by correction), the
  home (a thermostat), money (a central bank holding a rate), control
  (the loop as the general shape).
ASKED-AS: voltage regulator steady output load changes dips sense wire droop correction stable supply

ESSENCE: a linear regulator holds its output steady by burning the
  surplus as heat. Feed it twelve volts to make five, and every amp
  the load takes throws seven watts into the air. It is quiet, cheap
  and simple, and it is a heater with a useful side effect.
ROOT: electricity / power is push times flow, so a voltage dropped
  while current passes is power turned into heat, with nowhere else
  for it to go.
CANNOT: no linear regulator being efficient across a large drop — the
  waste is fixed by arithmetic, not by design quality. And no ignoring
  it at low current and keeping the answer at high current: the same
  circuit that runs cool at a trickle needs a heatsink at an amp.
THREAD: motion and force (braking as work turned into heat), money (a
  fee taken as a fixed slice), the home (a dimmer that got warm), cars
  (an engine idling to hold a speed downhill).
ASKED-AS: linear regulator hot heatsink wasted heat drop voltage efficiency burns difference amps warm

ESSENCE: a switching supply refuses to burn the surplus. It chops the
  input into pulses, stores each pulse briefly in a coil, and lets the
  average out — so it can be nine parts in ten efficient, and can even
  raise a voltage. The price is that it is now a small radio transmitter.
ROOT: this file / a coil smooths chopping into a steady flow, and a
  switch that is either fully on or fully off wastes almost nothing in
  either state.
CANNOT: no switching supply that is quiet — the sharp edges that make
  it efficient are exactly what radiates, so efficiency and
  cleanliness pull against each other. And no efficiency from a switch
  that lingers half-open: all the loss is in the moment of transition.
THREAD: engineering practice (a trade recorded or lost quietly), the
  home (every phone charger and its buzz on a radio), cooking (an oven
  cycling on and off rather than holding a middle setting).
ASKED-AS: switching supply efficient smps buzz radio interference noise chopping coil boost step

ESSENCE: a transistor is a valve where a small push at one terminal
  decides how much flows between the other two. That is the entire
  device, and the entire modern world: a signal too weak to do
  anything is given command of a supply that can.
ROOT: electricity / in some materials the conduction can be switched,
  so electricity is allowed to control electricity.
CANNOT: no amplification without a supply to be governed — the
  transistor contributes no energy at all, it only decides how much of
  somebody else's is released. And no control without some cost: the
  controlling terminal always takes a little current or charge, and
  that little sets how fast the valve can be worked.
THREAD: making (a tap governing a mains pressure), the body (a hormone
  in trace amounts commanding an organ), people and power (a small
  authority releasing a large budget), farming (a sluice gate).
ASKED-AS: transistor base gate small signal controls current switch amplify valve tap supply

ESSENCE: an amplifier does not make a signal bigger. It makes a bigger
  copy, drawn from the power supply, in the shape the small one
  dictates — which is why a failing amplifier reproduces the supply's
  own faults, and why an amplifier can never be louder than its supply
  allows.
ROOT: this file / a transistor governs a supply, so the output is the
  supply seen through the input's shape.
CANNOT: no output swinging beyond the supply rails, so no amplifier
  exceeding what it is fed. And no amplifier that is honest about
  shape at every size: past a certain output the copy stops matching,
  and what comes out is a squared-off version of what went in.
THREAD: music (a small amplifier distorting where a big one is clean),
  people (an assistant with a boss's authority), photography (pushing
  a dark picture and revealing the sensor's own faults).
ASKED-AS: amplifier gain copy louder distortion clipping supply rails headroom power amp shape

ESSENCE: gain and speed are one budget. A given amplifier can give a
  large magnification over a small range of speeds, or a small one
  over a wide range, and the product of the two is roughly fixed by
  the device. Asking for both is asking to be given the budget twice.
ROOT: physics / the charge that controls the valve takes time to move
  in and out, and that time sets how fast the valve can be worked.
CANNOT: no high gain at high speed from one stage — the way round is
  several modest stages in a row, which multiplies gain while each
  stays inside its own budget. And no cheating with feedback: feedback
  trades away gain to buy the speed, it does not create either.
THREAD: engineering practice (conflicting requirements settling
  somewhere), motion and force (gears trading turns for twist),
  photography (aperture against depth), the mind (breadth against depth).
ASKED-AS: gain bandwidth product amplifier fast slow stages cascade tradeoff high frequency rolls

ESSENCE: drive a transistor hard enough and it stops being a valve. It
  is either fully open, dropping almost nothing, or fully shut,
  passing almost nothing — and both states waste very little. Digital
  electronics is the deliberate refusal to use the useful middle.
ROOT: this file / a valve's loss is push multiplied by flow, and in
  either extreme one of the two factors is nearly zero.
CANNOT: no low-power digital circuit that lingers between the states
  — the heat is made in the crossing, so a slow edge costs more than a
  fast one, and a signal stuck halfway cooks the chip. And no analogue
  precision from a device driven into its ends.
THREAD: making (a switch against a dimmer), people (a decision taken
  against one held open), the mind (committing against dithering),
  law (a binary verdict from a continuum of facts).
ASKED-AS: saturation cutoff transistor switch fully on off digital heat slow edge middle

ESSENCE: a logic gate is a small arrangement of switches wired so that
  the output answers a question about the inputs — both, either,
  neither. Everything a computer does is built out of these, and
  nothing else is needed: the arithmetic, the memory, the decisions.
ROOT: mathematics / any statement about true and false can be built
  from a handful of basic combinations, and a switch is exactly a
  true-or-false device.
CANNOT: no logic without a switch that one signal can operate — a
  material that cannot gate its own signal cannot decide anything. And
  no gate that answers instantly or for free: each one costs a delay,
  a little power, and space, and a real machine is billions of them.
THREAD: mathematics (and, or, not as a complete kit), plumbing (valves
  arranged to answer a question about two taps), people (a committee
  rule requiring both signatures), the mind (a rule that combines cues).
ASKED-AS: logic gate and or not switches transistors computer decides truth table built from

ESSENCE: a digital signal is a polite fiction. Underneath, every edge
  is a real voltage climbing a real slope, ringing as it lands,
  reflecting off the far end of the track and coming back. The
  fiction holds only while the underlying analogue behaves.
ROOT: this file / digital is a verdict laid over a value, and the
  value never stopped being one.
CANNOT: no digital design escaping analogue at speed — the faster the
  edges, the more the wires behave like the components they are. And
  no debugging a fast digital fault with digital thinking: what looks
  like a wrong bit is usually a good bit arriving on a bad edge.
THREAD: language (a clean word made of a messy sound), money (a round
  figure hiding pennies), computing (a clean abstraction leaking),
  law (a bright-line rule and the mess it was drawn across).
ASKED-AS: digital really analogue edges ringing overshoot fast signals square wave reflections underneath

ESSENCE: a threshold with no memory chatters. If a slowly rising noisy
  signal crosses a single line, it crosses it many times on the way
  through, and the output flickers. The cure is two lines — one to go
  up, a lower one to come back — so the circuit must commit before it
  can change its mind.
ROOT: this file / noise sits on every signal, so any single boundary
  is crossed repeatedly by a signal that is only just at it.
CANNOT: no clean switching from a single threshold in the presence of
  noise, ever. And no free hysteresis: the gap that stops the chatter
  is also a deadband, so the circuit now responds late in both
  directions, which is the price of the stability.
THREAD: the home (a thermostat that would cycle every few seconds
  without a gap), the mind (an opinion that resists small evidence),
  law (a threshold with a separate, harder test to reverse it),
  control (deadband in every practical loop).
ASKED-AS: schmitt trigger hysteresis chatter flickering threshold noisy signal two levels deadband switching

ESSENCE: nothing in a circuit happens at the instant its cause does.
  Every gate takes a small time to change, every wire takes time to
  carry, and those delays add along a path. The longest such path
  through the machine is what actually sets its top speed.
ROOT: physics / a push travels at a finite speed, and a switch takes
  time to move charge in and out of itself.
CANNOT: no instantaneous logic, so no clocking a machine faster than
  its slowest path can settle. And no fixing this with a better clock:
  the limit is in the path, so the answer is a shorter path, a faster
  device, or splitting the work into more, smaller steps.
THREAD: engineering practice (the critical path setting a finish
  date), traffic (the slowest junction), cooking (the longest dish),
  computing (the pipeline that splits a long step into several).
ASKED-AS: propagation delay gate speed nanoseconds longest path clock rate limit settle slow

ESSENCE: a clock is not a source of speed. It is an agreement about
  when everyone looks — a shared drumbeat saying the wires have had
  long enough to settle, so whatever they hold now may be believed.
  Without it, every part of the machine would be reading mid-change.
ROOT: this file / signals take time to settle, so a system of many
  parts needs a common moment at which values are declared valid.
CANNOT: no synchronous machine running faster than its worst path,
  because one clock serves the whole. And no clockless design escaping
  the problem: it must instead carry handshakes saying "I am ready",
  which costs wires and complexity in place of the drumbeat.
THREAD: music (an orchestra's beat), people (a meeting time everyone
  keeps), farming (a market day), computing (turn-taking protocols).
ASKED-AS: clock speed megahertz why needed timing edge everyone reads same moment synchronous

ESSENCE: the two rules that decide whether a machine works are that
  data must be steady for a little while before the clock edge, and
  for a little while after it. Miss the first and it has not arrived;
  miss the second and it has already moved on. Everything else is
  arranging for those two.
ROOT: this file / a storage element samples a value at an instant, and
  a real sampler needs the value held still around that instant to
  capture it.
CANNOT: no reliable capture of a signal still moving at the edge. And
  no fixing a hold violation by slowing the clock: setup gets easier
  when the clock slows, hold does not change at all, so a hold fault
  is a wiring fault that no speed setting will cure.
THREAD: photography (a subject that must hold still for the shutter),
  cooking (adding an ingredient at exactly the right second), people
  (a vote counted at a stated moment), sport (crossing a line as the
  whistle blows).
ASKED-AS: setup hold time violation clock edge data stable timing fails slower clock wiring

ESSENCE: one clock has to reach millions of places, and it does not
  arrive everywhere at once. The difference in arrival time between
  two parts of a chip eats directly into the time available for work,
  so a large part of designing a fast machine is distributing its beat
  fairly.
ROOT: physics / a push travels at a finite speed, so a signal
  distributed over distance arrives later at the far end.
CANNOT: no zero skew across a large machine. And no ignoring it in one
  direction: skew that helps one path hurts the path going back, so it
  cannot simply be tuned away, only balanced.
THREAD: music (musicians spread across a large hall), engineering
  practice (a fleet drifting out of configuration), astronomy
  (signals from distant places arriving in the wrong order).
ASKED-AS: clock skew distribution tree arrives late different parts chip timing budget balanced beat

ESSENCE: when a storage element is asked to decide about a signal that
  changed at exactly the wrong instant, it can hang halfway — neither
  high nor low — for an unbounded time. It always resolves, but there
  is no guarantee when, and anything watching it may see nonsense.
ROOT: physics / a device with two stable states also has a balance
  point between them, and a nudge that lands exactly there takes an
  unpredictable time to fall off.
CANNOT: no circuit that can never go metastable when two independent
  clocks meet — the probability can be made tiny and never zero. And
  no cure by inspection: the failure is rare, random, and looks like
  every other intermittent fault, which is why the discipline is to
  synchronise at every crossing whether or not a fault has been seen.
THREAD: chance (a rare event that is certain given enough trials),
  balance (a coin landing on its edge), engineering practice (an
  anomaly nobody could reproduce), computing (a race between threads).
ASKED-AS: metastability flip flop undecided two clocks crossing domains rare glitch synchroniser random

ESSENCE: a memory cell is a bit made physical, and there are two
  families. One is a pair of gates each holding the other up, fast and
  greedy for space and power. The other is a tiny bucket of charge,
  dense and cheap, that leaks — so it must be read and rewritten
  thousands of times a second merely to keep saying the same thing.
ROOT: electricity / a capacitor holds charge and every real insulator
  leaks a little, while a cross-coupled pair of switches has two
  states each of which sustains itself.
CANNOT: no fast, dense, cheap and persistent memory in one cell — the
  families exist because the properties refuse to combine. And no
  charge-based cell surviving without power: forgetting is what a
  leaking bucket does, so persistence needs a different physics again.
THREAD: the mind (a rehearsed thought against a written note), keeping
  knowledge (a fire that must be fed against a carving), the home
  (holding a thought in your head while fetching a pen).
ASKED-AS: memory cell ram refresh leaks flip flop holds bit static dynamic forgets power

ESSENCE: converting a real signal into numbers is two separate acts.
  You choose the moments to look — that is sampling — and you choose
  the marks on the ruler — that is quantising. Each throws away a
  different thing, and each has its own irreversible cost.
ROOT: measurement / a continuous quantity can only enter a counting
  machine by being cut in two directions, time and size.
CANNOT: no conversion without discarding — the original was infinite
  in both directions and the record is finite in both. And no undoing
  either loss afterwards, however clever the processing: what was
  between the samples and between the marks was never recorded.
THREAD: photography (frames and pixels), maps (scale and grid),
  writing (spelling a continuous sound with discrete letters),
  measurement (every instrument's resolution and its interval).
ASKED-AS: analogue to digital converter sampling bits ruler moments lost detail recording resolution

ESSENCE: to record a wiggle you must look at least twice per wiggle.
  Look often enough and the numbers hold everything the original had,
  up to that speed. Look less often and you do not get a rough version
  — you get a confident wrong one.
ROOT: mathematics / two points per cycle are the fewest that can
  distinguish a rhythm from a slower one, and fewer leaves the two
  indistinguishable.
CANNOT: no capturing anything faster than half the looking rate, at
  any bit depth or any expense. And no gentle degradation at the
  boundary: just under it the record is faithful, just over it the
  record is a different signal entirely.
THREAD: photography (frame rate and a spinning wheel), astronomy
  (observations too far apart to see a period), medicine (readings too
  infrequent to catch a rhythm), the mind (checking too rarely).
ASKED-AS: sampling rate twice highest frequency audio khz enough capture wiggle cycles fast

ESSENCE: aliasing is what a too-slow look produces: a fast thing
  reported as a slow one, with total confidence and no sign of error.
  A wheel that turns backwards in a film, a hum that appears in a
  recording that had none — the invented signal sits inside the real
  band and can never be told apart afterwards.
ROOT: this file / fewer than two looks per cycle cannot distinguish a
  fast rhythm from a slow one, so the machine reports the slow one.
CANNOT: no removing an alias after sampling — it is now
  indistinguishable from a genuine signal at that speed, which is why
  the filter must sit before the converter, in the analogue world. And
  no detecting it from the data alone.
THREAD: photography (helicopter blades standing still), music
  (unwanted tones in a cheap recorder), evidence (a survey taken at
  intervals that match the thing being surveyed), farming (sampling a
  field in rows that match the planting).
ASKED-AS: aliasing wagon wheel backwards film false frequency low tone appears filter before sampling

ESSENCE: the ruler has smallest marks, so every reading is rounded,
  and the rounding is an error added to the signal. It sounds like a
  small hiss and behaves like noise — except that when the signal is
  very quiet it stops being random and becomes a distortion that
  follows the signal, which the ear notices far more.
ROOT: this file / quantising assigns a continuum to a finite set of
  values, so the difference between the true value and the assigned
  one is a leftover that must go somewhere.
CANNOT: no conversion without this error — more bits shrink it and
  never abolish it. And no hiding it at low levels by adding bits
  alone: deliberately adding a little noise before conversion trades a
  slightly higher hiss for the removal of the correlated distortion,
  which is a real and counter-intuitive bargain.
THREAD: money (rounding to the penny, and where the pennies go),
  measurement (an instrument's last digit), maps (a grid's cell size),
  photography (banding in a smooth sky).
ASKED-AS: quantisation error bits rounding hiss distortion quiet passages resolution steps dither noise

ESSENCE: a converter's bits are a statement about how finely it
  divides, not about whether the divisions are in the right places.
  A sixteen-bit reading from a drifting reference and a warm circuit
  may be accurate to eight — the extra digits are honestly computed
  and mean nothing.
ROOT: evidence / precision is the size of the smallest step reported
  and accuracy is closeness to the truth, and neither implies the other.
CANNOT: no accuracy from resolution — the digits arrive regardless.
  And no better accuracy than the reference the whole thing is
  measured against: every reading is a comparison, so a reference that
  moves by one part in a thousand caps the answer there.
THREAD: measurement (a scale reading to a milligram and out by a
  gram), money (a valuation quoted to the penny), the mind (confidence
  from detail), medicine (a number given to two decimal places).
ASKED-AS: bits resolution accuracy sixteen bit really eight reference drift precision digits meaningless

ESSENCE: negative feedback is the trade at the heart of good
  electronics. Take a device with enormous, unreliable, temperature-
  dependent gain, feed a slice of its output back to oppose its input,
  and you get a modest gain set by two resistors — stable, linear,
  predictable, and almost independent of the messy device inside.
ROOT: this file / an amplifier magnifies the difference at its input,
  so returning some output as opposition drives that difference toward
  zero and the ratio toward what the return path sets.
CANNOT: no getting this for nothing — the whole benefit is bought with
  gain that is deliberately thrown away, so the more stability you
  want the less magnification you keep. And no feedback fixing what
  happens outside the loop: distortion after the sensing point is
  invisible to the correction.
THREAD: control (a loop comparing wanted to actual), the body
  (regulation of temperature and sugar), money (a policy that leans
  against a trend), people (criticism as correction).
ASKED-AS: negative feedback amplifier stable gain resistors set linear distortion reduced tradeoff loop

ESSENCE: the operational amplifier is the practical result: a part
  with gain so large it is treated as infinite, sold with the
  understanding that it will never be used bare. What it does is
  decided entirely by the components wrapped around it, so one part
  becomes an adder, a filter, a comparator, or a follower.
ROOT: this file / with enough gain, feedback makes the behaviour a
  property of the feedback network rather than of the device.
CANNOT: no using it without feedback for anything but comparison —
  bare, its output slams to one rail or the other on the smallest
  input. And no infinite gain in fact: at high speed the real gain
  falls, so every ideal-seeming circuit stops behaving somewhere.
THREAD: making (a general-purpose tool defined by its jig), language
  (a word whose meaning is set by its sentence), computing (a generic
  routine specialised by what is passed in).
ASKED-AS: op amp inverting follower feedback resistors circuit does what infinite gain rails

ESSENCE: turn the feedback the other way and the system stops
  correcting and starts running away. Any small disturbance is fed
  back to make itself bigger, so the circuit charges to one extreme
  and stays — which is exactly how a memory latch and a fast decision
  are made.
ROOT: this file / feedback returns some output to the input, and the
  sign decides whether the return opposes the change or joins it.
CANNOT: no stable middle in a positively fed-back circuit — the
  balance point exists and nothing rests there. And no positive
  feedback without a limit somewhere: the run-away always ends at a
  rail, a saturation, or a fire, so the limit is part of the design
  and never an accident.
THREAD: money (a bank run), people (a rumour amplifying itself), the
  living world (a population without a predator), sound (a microphone
  in front of its own speaker).
ASKED-AS: positive feedback runaway latch snap decision squeal microphone speaker howl unstable extreme

ESSENCE: an oscillator is a loop that cannot settle. Arrange for a
  signal to come back to its own input in step and slightly stronger,
  and the circuit starts from its own noise and builds until something
  limits it — so a circuit given no input produces a rhythm out of
  nothing.
ROOT: this file / a loop with gain above one and a return in step will
  grow any disturbance, and there is always a disturbance because
  there is always noise.
CANNOT: no oscillator that starts from perfect silence — it needs the
  noise floor as a seed, which is the one time noise is the point. And
  no oscillator with clean amplitude and perfect purity: the limiting
  that stops the growth is a distortion, so the two are traded.
THREAD: music (a bow or a reed feeding a resonance), the body (a
  pacemaker cell that fires on its own), weather (a self-sustaining
  circulation), the mind (a thought that keeps re-triggering itself).
ASKED-AS: oscillator makes signal from nothing loop gain feedback starts noise builds limits tone

ESSENCE: the good timekeeper in electronics is not electronic. A
  quartz crystal is a tiny mechanical tuning fork, cut to ring at one
  sharp frequency, that speaks electricity because squeezing it makes
  a voltage. Circuits are unstable; a lump of shaped rock is not.
ROOT: motion and force / every object answers strongly to a short list
  of rhythms, and a well-cut crystal has one very sharp one and
  extremely little damping.
CANNOT: no comparable steadiness from resistors and capacitors — their
  values move with temperature and age, so an electrical timing loop
  drifts by percent while the crystal drifts by parts per million. And
  no crystal that is exact: it still moves with temperature, which is
  why precise clocks heat theirs to a constant temperature.
THREAD: time (a pendulum's isochronism), music (a tuning fork),
  astronomy (a rotation used as a standard), making (a hard reference
  surface everything is measured from).
ASKED-AS: crystal oscillator quartz watch accurate mhz tuning fork frequency stable temperature drift

ESSENCE: a phase-locked loop is a follower. It runs its own oscillator,
  constantly compares its rhythm to an incoming one, and nudges itself
  until the two march together — so a clean local beat can be locked
  to a weak, noisy, distant one, and multiplied up to any speed.
ROOT: this file / negative feedback drives a difference toward zero,
  applied to the difference in timing between two rhythms rather than
  between two voltages.
CANNOT: no lock without the loop being able to reach the incoming
  rhythm — outside its capture range it simply never finds it. And no
  instant lock: the loop takes time to pull in, and a loop made fast
  enough to lock quickly is also fast enough to follow the incoming
  jitter it was supposed to filter out.
THREAD: music (a musician locking to a beat), the body (a body clock
  pulled by daylight), people (a crowd's clapping falling into step),
  control (tracking a moving target).
ASKED-AS: phase locked loop pll lock onto signal clock recovery multiply frequency jitter tracking

ESSENCE: getting rid of heat is a chain of obstacles, and the chain
  matters more than any link. From the silicon to its case, from the
  case to the heatsink, from the heatsink to the air — each step has
  its own resistance, and the hottest point is inside where nobody can
  put a thermometer.
ROOT: heat and electricity / heat is made throughout a body and leaves
  only through its surface, so a small hot source needs a path to a
  large cool one.
CANNOT: no cooling by a big heatsink if the joint to it is poor — the
  worst step sets the total, and a smear of paste is routinely that
  step. And no measuring the temperature that actually matters: the
  junction inside is inferred from the case and the known chain,
  never read.
THREAD: making (errors accumulating along a chain), building (a wall's
  insulation defeated by one bridge), the body (blood carrying heat to
  the skin), plumbing (the narrowest pipe setting the flow).
ASKED-AS: heatsink chip hot thermal paste junction temperature case air chain cooling fan

ESSENCE: every current that changes throws out a field, and every wire
  it reaches picks some of that field up. Nothing is isolated: a motor
  starting, a switching supply chopping, a radio transmitting, and a
  lightning strike ten kilometres away all arrive in a circuit that
  nobody connected them to.
ROOT: electricity / a changing current wraps a changing field around
  itself, and a changing field drives a current in any loop it crosses.
CANNOT: no circuit that neither emits nor receives — the same physics
  does both, so a design quiet in one direction tends to be robust in
  the other. And no fixing it at the end of a project: it is decided
  by layout, loop area and cable routing, which are settled long
  before anybody switches on.
THREAD: electricity (induction), the home (a radio buzzing when the
  fridge starts), engineering practice (an interface nobody owned),
  people (a conversation overheard through a wall).
ASKED-AS: interference emc emi noise motor starting radio buzz picks up emissions fields

ESSENCE: any conductor is an aerial, in both directions, and how well
  it works depends on its length compared with the wave. That is why
  the trouble is nearly always in the cables rather than the board:
  the board's tracks are centimetres and the cables are metres.
ROOT: physics / a wiggled charge sheds waves, and a conductor radiates
  and receives best when its length is a simple fraction of the
  wavelength.
CANNOT: no shielded box being quiet with an unfiltered cable leaving
  it — the cable carries the noise out past the shield, and the box
  becomes decoration. And no ignoring what a wire is attached to: the
  cable and the box together make the aerial, not the cable alone.
THREAD: astronomy (a dish sized to what it listens for), music (a
  string's length setting its note), the home (an aerial cut for a
  band), waves (bending depending on stride against size).
ASKED-AS: cable antenna length wavelength radiates picks up ferrite filter shielded box leaks

ESSENCE: a shield is a conductor that intercepts a field and gives its
  currents somewhere to go. It works well against electric fields at
  almost any thickness, poorly against slow magnetic fields unless it
  is made of the right metal — and not at all if it is not connected,
  or if it has a gap the wave can fit through.
ROOT: electricity / free charge in a conductor moves until the field
  inside is cancelled, which handles electric fields; magnetic fields
  are not cancelled that way and must be diverted or damped instead.
CANNOT: no shielding a magnetic field with aluminium foil, however
  neatly. And no shield working while it floats: an unconnected shield
  is a piece of metal that has been added to the aerial rather than
  taken away from it.
THREAD: electricity (a metal shell with no field inside), the home (a
  microwave door mesh), medicine (a scanner room lined with copper),
  building (a lead apron stopping one thing and not another).
ASKED-AS: shielding foil braid cable screen connected one end magnetic field mu metal gap

ESSENCE: send a signal down two wires as a difference rather than
  against ground, and any interference that hits both wires equally is
  subtracted away at the far end. The noise arrives; it simply
  arrives on both, so the difference never notices it.
ROOT: this file / a signal is a difference between two points, so
  choosing which two points defines what counts as noise.
CANNOT: no rejection of interference that lands unequally on the two
  wires — which is why the pair must be twisted, so both see the same
  field along the whole run. And no infinite rejection: the two paths
  are never perfectly matched, and the mismatch is the leak.
THREAD: measurement (comparing two samples treated alike so the shared
  conditions cancel), medicine (a control group), music (balanced
  cables on long runs), evidence (a difference measured rather than a
  level).
ASKED-AS: balanced differential pair twisted cancels noise common mode microphone long cable hum

ESSENCE: sometimes the answer is to have no metal path at all. Send
  the signal across as light, or as a magnetic handshake, and the two
  sides no longer need to agree about ground — which stops loops,
  survives a large difference between the two ends, and keeps a fault
  on one side from reaching a person on the other.
ROOT: this file / a shared ground is what makes two circuits one, so
  removing the shared conductor genuinely separates them.
CANNOT: no isolation across a wire, so the barrier costs a component
  and some speed. And no isolation surviving a capacitor across the
  barrier: any path at all, including stray capacitance, partly undoes
  it, which is why isolation is rated in volts rather than assumed.
THREAD: medicine (equipment touching a patient kept apart from the
  mains), engineering practice (a deliberate break in a chain),
  computing (an air gap between networks), the home (a shaver socket).
ASKED-AS: isolation optocoupler transformer barrier separate grounds safety medical floating breaks loop

ESSENCE: a spark from a finger carries thousands of volts and can
  punch a hole through the insulation inside a chip. The cruel part is
  that it often does not kill it — it wounds it, and the part works
  for months and then fails in service with nothing to see.
ROOT: electricity / rubbing relocates charge and an insulator strands
  it, so an ordinary person accumulates a push far beyond what a thin
  internal layer can survive.
CANNOT: no chip surviving a discharge it has no protection for. And no
  telling a wounded part from a healthy one by testing: it passes, and
  the damage shows only as a shortened life, which is why the handling
  discipline exists rather than a screening test.
THREAD: engineering practice (a latent fault found only by a demand),
  medicine (an injury that shows up years later), making (a rope
  shock-loaded once and still used), the home (a winter doorknob).
ASKED-AS: static electricity chip damage wrist strap esd handling latent failure months later spark

ESSENCE: a battery's rating is a promise made under gentle conditions.
  Pull hard and you get less out of it, not merely faster — the same
  cell that gives its full amount over ten hours gives noticeably less
  over one. The stated capacity is a measurement, not a container size.
ROOT: chemistry / the reaction happens at surfaces and the ingredients
  must travel to reach them, so a heavy demand outruns the transport
  and part of the cell never takes part.
CANNOT: no getting the rated capacity at a high rate. And no comparing
  two batteries by their headline figure alone: the number is only
  meaningful with the rate, the temperature and the cut-off voltage it
  was measured at, all three of which the label often omits.
THREAD: farming (a well that yields less when pumped hard), the body
  (a sprint against a walk drawing on different supplies), money (a
  fund's value under a forced sale), water (a slow spring).
ASKED-AS: battery capacity mah high current less runtime rate discharge rating measured slow drain

ESSENCE: you cannot read how much is left in a battery. There is no
  wire that carries the answer — only a voltage that sags under load,
  droops with cold, and sits nearly flat across most of the discharge
  of the very chemistries we use most. Every fuel gauge is a guess
  from indirect signs.
ROOT: evidence / a quantity that is not directly observable can only
  be inferred through a model, and the model carries every assumption
  it was built with.
CANNOT: no true state-of-charge reading — a battery meter is
  counting what went in and out, and errors accumulate until something
  resets them. And no gauge that stays right as the cell ages: it was
  calibrated against a battery that no longer exists.
THREAD: control (estimating a state from noisy measurements), money (a
  balance inferred from flows), the body (thirst as a poor gauge),
  farming (soil moisture judged from the surface).
ASKED-AS: battery percentage wrong jumps fuel gauge state charge estimate flat voltage ageing

ESSENCE: the schematic says what is connected; the board decides
  whether it works. Track length, loop area, which side of the chip
  the reserve capacitor sits, where the return current is allowed to
  run — none of it appears in the drawing, and all of it is circuitry.
ROOT: this file / a wire carries resistance, capacitance and coupling,
  none of which the schematic's clean lines represent.
CANNOT: no predicting the behaviour of a fast or sensitive circuit
  from its schematic. And no two boards from the same schematic
  behaving alike: they are different circuits that happen to share a
  diagram, which is why a working design is a layout and not a drawing.
THREAD: engineering practice (drawings say the intention, the building
  says what happened), cooking (a recipe against a kitchen), building
  (a plan against a site), maps (the map and the ground).
ASKED-AS: schematic works board doesnt layout matters tracks length placement redesign same circuit

ESSENCE: a great many bugs blamed on software are electrical. A supply
  that dips on a heavy edge, a reset that arrives before the voltage
  is up, a noisy input read as a keypress — the program is innocent
  and behaving correctly on a lie it was told by the hardware.
ROOT: this file / digital is a verdict laid over an analogue value, so
  a bad value produces a wrong verdict that is then obeyed perfectly.
CANNOT: no finding this class of fault by reading code — it is not in
  the code, and the search there can continue indefinitely. And no
  reproducing it reliably: it depends on temperature, on what else is
  switching, and on the length of a cable, so it presents as the
  intermittent bug nobody can catch.
THREAD: engineering practice (an anomaly closed without being
  understood), medicine (a psychiatric label on a physical illness),
  computing (a memory fault reported as a logic error).
ASKED-AS: intermittent bug blamed software really hardware supply dip reset noise glitch random crash
