# ELECTRONICS — THE COLOR
Built 2026-08-30 to the ratified model (fabric/MODEL.md). Seed authored
by Claude from docs/fabric_phylums/145_deep_electronics.md and
docs/fabric_phylums/85_deep_heat_light_electricity.md; growth from here
must trace to what is written. Mirror: docs/phylums/electronics/white.md
— same parts, opposite sign.

## THINGS
The units this subject is about. Each sits in many phylums at once; its
other homes are named so a cascade can branch.

- CHARGE — the moved stuff; never created, only relocated; where an
  insulator strands it, it piles up until it jumps; also: physics,
  chemistry (ions), weather (the storm's stacks), body (nerves).
- VOLTAGE — the push; only ever a DIFFERENCE between two points, never
  a property of one; also: physics, measurement (every datum needs a
  second point).
- CURRENT — the flow; whatever goes out must come back, and the loop
  exists whether the designer drew it or not. The wire is already full
  of loose charge: the push travels near light speed while the charges
  crawl slower than an ant — a full pipe, pressed at one end; also:
  physics, computing, medicine (shock is dosed in it).
- RESISTANCE — the toll every real path charges; turns passage into
  heat, grows in metals as they warm; also: physics, engineering,
  economy (every channel takes its cut).
- THE SIGNAL — a voltage that changes as time passes; sound, heat, a
  heartbeat, a picture all enter as one wiggling voltage, and the
  circuit has no idea what any of it meant; also: language (marks
  standing in for sounds), music, mind, measurement.
- NOISE — the random hash on every wire that nobody put there: warm
  atoms jostling, charge in lumps, stray pickup from every machine in
  the building. Not a fault — a floor that exists in a perfect
  circuit; also: physics, astronomy, mind.
- GROUND — the point everyone agreed to call zero, usually the earth
  itself; really a piece of metal with resistance carrying every
  return current; also: earth (literally), measurement, law (an agreed
  datum so numbers can meet).
- THE TWO SPRINGS — the capacitor, a bucket for charge, springs
  against changing VOLTAGE (passes fast wiggles, blocks steady flow);
  the inductor, a flywheel for current, springs against changing FLOW
  (passes the steady, fights the sudden); also: physics, computing
  (memory as tiny buckets), transport (momentum's twin).
- THE DIODE — a one-way door charging a fixed toll to open, a little
  under a volt regardless of traffic; also: body (heart and vein
  valves), craft (the ratchet).
- THE TRANSISTOR — a valve where a small push at one terminal decides
  how much flows between the other two: electricity controlling
  electricity, the modern world in one device; also: computing
  (billions per chip), body (a trace hormone commanding an organ),
  farming (the sluice gate).
- THE SWITCH — the atom of computing: true-or-false made physical;
  also: mathematics (logic's kit), computing, governance.
- THE BATTERY — a chemical pump for charge: push fixed by the reaction
  inside, spent partly against its own internal friction; its rating
  is a promise made under gentle draw — pulled hard, the same cell
  gives less, because the reaction lives at surfaces the ingredients
  must travel to reach; also: chemistry, transport, economy.

## CLAIMS
What holds, written to be tested by a crossing query.

- Fix any two of push, flow, and toll and the third is decided — you
  never get to choose all three (the law is in SCIENCE).
- Two different jobs travel down identical wires: a power circuit
  delivers energy, and nobody cares what shape it arrives in; a signal
  circuit delivers a SHAPE, the energy only the vehicle. Nearly every
  design rule flips between the two.
- A signal exists only as far as it stands above the noise beside it;
  a circuit's real quality is how little it adds to that ratio.
  Turning up the gain magnifies both alike and rescues nothing —
  collect more at the start, keep noise out on the way in.
- Analogue and digital are one decision about noise. Analogue keeps
  the whole shape and every copy is slightly worse. Digital keeps a
  verdict — high or low — which noise must overturn entirely, so
  copies are perfect forever. The price: the shape is thrown away.
- A digital signal is a polite fiction: every edge is a real voltage
  climbing a real slope, ringing, reflecting off the far end of the
  track. The fiction holds while the underlying analogue behaves.
- An amplifier does not make a signal bigger: it makes a bigger copy,
  drawn from the power supply, in the shape the small one dictates —
  so it reproduces the supply's faults and can never swing past what
  the supply provides (clipping is that ceiling).
- Feedback's sign is destiny: returned output OPPOSING the input
  steadies and holds; returned output JOINING it runs away to an
  extreme and stays — a fault in an amplifier, the working principle
  of a latch, a snap decision, and an oscillator.
- Whatever is induced opposes the change that induced it: draw current
  from a generator and its shaft grows heavy. If the induced effect
  helped its cause, the loop would feed itself for free — the mirror
  holds the graveyard of machines built on that hope. Read either way
  round, every motor is a generator and every generator a motor.
- An instrument put onto a circuit becomes part of it: a meter draws
  current, a probe hangs capacitance, and delicate circuits change the
  moment they are watched — sometimes into working.
- The schematic says what is connected; the board decides whether it
  works. And many bugs blamed on software are electrical: a supply
  dipping on a heavy edge, a reset arriving early, a noisy input read
  as a keypress — the program obeys a lie the hardware told.
- Resistance is not fixed: a cold filament or stopped motor lets a
  surge through in the first instant — why bulbs blow at switch-on and
  motors are sized for several times their running current.
- Every insulator has a strain past which it conducts — dry air gives
  way near 3,000 volts per millimetre, then everything crosses at
  once; the doorknob snap and the lightning bolt are the identical
  event at two sizes.
- Charge on a conductor sits entirely on its outside and crowds onto
  the sharpest points; the enclosed space holds no field at all — why
  a metal box protects its contents and a sharp rod bleeds a
  building's charge away quietly.

## SCIENCE
The math, physics, and chemistry of circuits, held — not mentioned.
Each piece is a LAW a query can compute with, a RULE it can follow,
and where it earns it, a WORKED case proving the rule runs.

### PHYSICS — the loop's law

LAW: push = flow × toll. V = I × R, volts, amps, ohms.
RULE: fix any two, solve for the third; a circuit never grants all
  three wishes.
WORKED: a 9-volt battery across 450 ohms: I = 9 ÷ 450 = 0.02 A.
  Check backwards: 450 × 0.02 = 9. ✓

LAW: in series, one current and the push splits by the ratio of tolls;
  in parallel, one push and the currents add, each branch independent
  (house wiring is parallel; the fuse sits in series with all of it).
RULE: two resistors in a line make a chosen fraction of a voltage —
  the seed of nearly everything: a threshold set, a sensor read, a
  transistor biased.
WORKED: 9 V across 10,000 + 20,000 ohms: I = 9 ÷ 30,000 = 0.0003 A.
  Across the 20,000: 0.0003 × 20,000 = 6 V; across the 10,000: 3 V.
  Sum 6 + 3 = 9. ✓ The junction reads 6 volts.

LAW: a source spends a load's draw partly inside itself: terminal push
  = open push − current × internal toll.
WORKED: a 12-V car battery, 0.02 ohms inside, cranking at 200 A: lost
  inside = 200 × 0.02 = 4 V; the terminals show 12 − 4 = 8 V — the
  dimmed headlights, and why a source is two numbers, never one.

### PHYSICS — power and heat (why wires warm)

LAW: power = push × flow. P = V × I — what you buy, what a wire must
  survive, what becomes work or heat.
WORKED: a kettle at 230 V drawing 10 A: 230 × 10 = 2,300 W. The same
  power could arrive as 23 V at 100 A or 2,300 V at 1 A.

LAW: in a resistance the whole toll becomes heat, growing with the
  SQUARE of the current: P = I² × R.
RULE: to cool a wire, halve the amps: fatter copper, shorter runs,
  higher voltage for anything travelling far.
WORKED: a 0.5-ohm extension cord at 10 A: 10² × 0.5 = 50 W — a lamp's
  heat lying in the coil of cord. At 20 A: 20² × 0.5 = 200 W — four
  times the heat for twice the draw. Ratings are law, not advice.
WORKED (the grid, the same square at planet size): deliver 10,000 W
  through a 1-ohm line. At 100 V it carries 100 A and wastes 100² × 1
  = 10,000 W — the wire eats as much as arrives. At 10,000 V it
  carries 1 A and wastes 1² × 1 = 1 W. A hundredfold push cut the
  waste ten-thousand-fold — why the grid runs high and thin, stepped
  down only at the last street.

LAW: a valve's loss is drop × flow, so a switch at either extreme
  wastes almost nothing — one factor is nearly zero.
WORKED: a transistor fully ON, dropping 0.05 V at 2 A: 0.1 W. Held
  HALF-open, dropping 6 V at 2 A: 12 W — a hundred and twenty times
  the heat. Digital electronics is the deliberate refusal to use the
  useful middle; this arithmetic is the reason.
WORKED (regulation, both roads): make 5 V at 1 A from 12 V. Linear
  burns the surplus: (12 − 5) × 1 = 7 W of heat for 5 W of work — 5 ÷
  12 ≈ 42%, a heater with a useful side effect. Switching chops the
  input into pulses a coil smooths: nine parts in ten, drawing only
  5 ÷ 0.9 ≈ 5.6 W — at the price of being a small radio transmitter.

### PHYSICS — the two springs at work

LAW: a capacitor's stored energy = ½ × C × V², joules.
WORKED: a camera-flash bucket, 0.001 farads at 300 V: ½ × 0.001 ×
  90,000 = 45 J; dumped in a thousandth of a second, 45 ÷ 0.001 =
  45,000 W for that instant — filled slowly, thrown all at once.

LAW: a resistor before a capacitor is a clock: τ = R × C seconds; the
  voltage climbs ~63% in one τ, ~99% in five.
WORKED: 10,000 ohms × 0.0001 farads = 1 second: two-thirds full at one
  second, done for practical purposes at five. Every delay and timer
  is this curve — charge through a toll, slowing as the bucket fills.

LAW: an inductor fights back with L × (change of current ÷ time).
RULE: never open a switch on a coil without an exit for the current (a
  diode across it) — faster opening means a fiercer spike, not less.
WORKED: 0.1 henry at 0.5 A interrupted in a millionth of a second:
  0.5 ÷ 0.000001 = 500,000 amps per second; 0.1 × 500,000 = 50,000 V —
  from a 12-volt circuit. Hired instead of feared, the same insistence
  is the switching supply and the ignition coil.

LAW: the capacitor's slow climb lets fast wiggles pass and follows
  slow ones; the coil does the reverse. Either in a signal's path
  sorts by speed of change — that is all a filter is (tone controls,
  crossovers, rumble cuts). Sharpness costs watching time; the mirror
  holds that certified trade.
RULE (the reservoir): a rail is not a rail — a chip gulps current
  faster than the distant supply can answer, so a small capacitor
  BESIDE each chip is its private reservoir, refilled between gulps.
  Placement is the function.

### PHYSICS — fields, induction, radio's arithmetic

LAW: two coils on one iron core trade push for flow in the ratio of
  their turns, power conserved — and only a CHANGING current induces,
  which is why the grid is alternating.
WORKED: 240 V into a 20-to-1 transformer: 240 ÷ 20 = 12 V out; a 0.5-A
  draw in supports 0.5 × 20 = 10 A out. Check: 240 × 0.5 = 120 W in,
  12 × 10 = 120 W out. ✓ The lever's bargain in charge's currency.

LAW: a conductor radiates and receives best when its length is a
  simple fraction of the wave; wavelength in metres ≈ 300 ÷ frequency
  in MHz.
WORKED: at 100 MHz, 300 ÷ 100 = 3 m; a quarter is 75 cm — the metre of
  cable out of a box is a fine aerial while the board's centimetre
  tracks are deaf; interference trouble is nearly always the cables.

LAW: a loop is an aerial too — a changing magnetic field through a
  closed ring drives a current round it. Two boxes joined by a signal
  cable, both earthed at the wall, make such a ring; the driven
  current appears in the signal as hum (the ground loop).

### MATHEMATICS — the counting machine (the switch made arithmetic)

LAW: any statement about true and false builds from a handful of
  combinations — both, either, neither — and a switch is exactly a
  true-or-false device. Gates wired from switches suffice for ALL of
  it: the arithmetic, the memory, the decisions. And n switches hold
  2ⁿ states.
WORKED: 10 switches: 2¹⁰ = 1,024 states; 16: 2¹⁶ = 65,536 — every
  count, letter, and picture an address in such a space.

LAW: a digital circuit takes a view, not a reading: below one line is
  low, above another high; the gap between is the defence.
WORKED: a classic family calls under 0.8 V low, over 2.0 V high; the
  1.2-V forbidden gap is the noise margin — hash smaller than the gap
  changes nothing. Digital's trick, bought by refusing the middle.

LAW: to record a wiggle in numbers, look at least twice per wiggle;
  often enough and the numbers hold everything up to that speed, less
  often gives not a rough version but a confident wrong one (the
  mirror holds that cannot).
WORKED: hearing tops near 20,000 wiggles per second; discs sample
  44,100 times per second — past twice — and all the ear could take is
  in the numbers.

LAW: the ruler has smallest marks: n bits divide the range into 2ⁿ
  steps and every reading rounds to a step.
WORKED: 16 bits across 1 volt: 1 ÷ 65,536 ≈ 0.0000153 V — steps of
  fifteen millionths of a volt. The rounding behaves as a small hiss —
  except on the quietest signals, where it becomes a distortion that
  follows the signal; deliberate noise (dither) trades it back.

### THE AMPLIFIER'S ARITHMETIC (feedback, the founding trade)

LAW: an amplifier magnifies the difference at its input; return a
  fraction β of the output to OPPOSE the input and the working gain is
  A ÷ (1 + A × β) — for large A, almost exactly 1 ÷ β: set by two
  resistors, nearly independent of the messy device inside.
WORKED: device gain 100,000, return one part in a hundred: 100,000 ÷
  (1 + 1,000) = 100,000 ÷ 1,001 ≈ 99.9. Let the device drift to
  200,000: 200,000 ÷ 2,001 ≈ 99.95. The device changed 100%; the
  amplifier changed 0.05%. This is why the op amp is sold with gain
  treated as infinite and never used bare: the network around it
  decides everything — one part becomes an adder, a filter, a
  follower, a comparator.

LAW: gain and speed are one budget, their product roughly fixed by the
  device; asking for both is asking for the budget twice.
WORKED: a 1,000,000-per-second budget: gain 1,000 leaves 1,000,000 ÷
  1,000 = 1,000 wiggles per second — telephone-slow; gain 10 leaves
  100,000 — hi-fi-fast. The road to both is stages in a line, each
  paying its own noise toll on the way in.

LAW: feedback turned to JOIN the input drives any disturbance to an
  extreme (a latch, a snap decision); arranged to return in step and
  slightly stronger round a loop, it builds a rhythm from its own
  noise and holds it — an oscillator, a signal from nothing, because
  there is always noise to start from. A quartz crystal in the loop
  lends its one sharp mechanical rhythm and the wobbly circuit
  inherits a rock's stability — every watch, every computer beat. A
  follower loop locks a clean local beat to a weak noisy distant one —
  clock recovery.

### TIME AND SPEED (what sets a machine's pace)

LAW: nothing happens at the instant of its cause: every gate takes
  time to change, every track time to carry, and delays ADD along a
  path. The longest path sets the machine's top speed. A push crosses
  a board at roughly 15 cm per billionth of a second.
WORKED: a machine beating 2,000,000,000 times a second has half a
  billionth per beat; the push covers 15 × 0.5 = 7.5 cm in that time —
  track LENGTH is a real fraction of a beat, and delivering one clock
  fairly across a chip eats into the work time. The clock is not a
  source of speed; it is an agreement about when everyone looks — a
  drumbeat saying the wires have settled and may be believed.
RULE (the two commandments): data steady a little BEFORE the clock
  edge and a little AFTER — miss the first and it has not arrived,
  miss the second and it has already moved on. Where a signal crosses
  between stranger clocks, the sampler can be caught mid-change and
  hang undecided — the mirror holds that certified cannot.

### CHEMISTRY AND MATTER — pushed charge; why materials conduct

LAW: a battery's push is set by its reaction — fixed steps per cell:
  ~1.5 V dry cell, ~2 V lead-acid, ~3.7 V lithium; stacking adds.
WORKED: the 12-V car battery is six lead cells: 6 × 2 = 12 V. ✓

LAW (settled): electrons in matter live in permitted arrangements. In
  a metal the next arrangement up is free at any nudge — loose charge
  everywhere, hence conduction, and hence the toll: charge trips over
  jiggling atoms; more jiggle, more toll. In an insulator the gap to
  the conducting arrangement is too wide for any ordinary push. In a
  semiconductor the gap is SMALL — bridgeable by warmth, light, or a
  neighbouring push — and seeded impurities (doping) place charge just
  below it to order. A junction of two differently seeded regions
  passes charge one way (the diode); a third terminal bending the gap
  makes conduction switchable (the transistor); the same junction run
  backwards turns light's packets into pushed charge (the solar cell).

LAW (settled fact, mechanism split across the sheets): below its own
  critical cold a superconductor's toll is exactly zero — ring
  currents persist for years without decay. The cold kind is
  understood: electrons pair, and the pairs glide without tripping.
  The cost is the condition: today's useful ones bathe in liquid
  helium (every hospital magnet). The warm ceramics' mechanism and the
  room-temperature want live in the mirror, with the gap stated
  exactly.

LAW (the heat chain): heat leaving a chip crosses added resistances —
  silicon to case to sink to air, each in degrees per watt; the
  hottest point is inside, computed, never read.
WORKED: 3 + 0.5 + 4 = 7.5 °C/W; at 10 W: 10 × 7.5 = 75 degrees above
  a 20° room = 95 °C at the silicon while the case is merely warm.

## METHODS
How things are done here — each with what governs it and what breaks
it. The prepositioned how-to-build.

- AMPLIFY AT THE SOURCE: the first stage sets the noise for life —
  beside the sensor, never at the cable's far end; everything after
  amplifies signal and noise alike.
- FILTER BEFORE YOU SAMPLE: refuse, in analogue, every speed above
  half the looking rate BEFORE the converter — after it, an invented
  slow signal is indistinguishable forever.
- RECTIFY THEN SMOOTH: diodes flip or refuse the wrong half of an
  alternating push (humps, not steadiness); the charge spring fills
  between humps. Every charger brick is this sentence.
- REGULATE BY MEASURING YOURSELF: compare output to wanted, correct
  continuously — negative feedback as a supply. Linear: quiet, simple,
  burns the surplus (the 42% arithmetic). Switching: nine parts in
  ten, but a small radio station.
- SWITCH HARD OR NOT AT ALL: the extremes are nearly free (0.1 W vs
  12 W above); pass through the middle quickly — the middle is where
  the heat lives. And give every coil an exit (the flyback diode), or
  the 50,000-V arithmetic answers the switch.
- DECIDE WITH TWO THRESHOLDS: one line to go up, a LOWER one to come
  back, so the circuit commits before it can change its mind — every
  thermostat and clean button; the single line's chatter is in the
  mirror.
- CLOCK IT: storage looks only on the shared drumbeat, margins proven
  along the LONGEST path; between stranger beats, a chain of samplers
  spends beats to buy near-certainty against the undecided hang.
- ONE REFERENCE, RETURNS PLANNED: ground carries real current — give
  every fast signal its return directly underneath, join references at
  one star point, never cut a slot under a track. Breaks silently: the
  drawing looks identical either way.
- SUBTRACT WHAT YOU DID NOT SEND: carry the signal as the DIFFERENCE
  between two twisted wires; interference lands on both equally and
  the difference never notices.
- SHIELD, MIND THE GAPS: a grounded skin intercepts electric fields at
  almost any thickness; slow magnetic fields need diverting metal; a
  gap the wave fits through is an open door. And when grounds cannot
  agree, remove the metal: cross as light or a magnetic handshake —
  loops broken, faults kept from people (medicine's bedside rule).
- HANDLE AS IF WOUNDED: a winter finger carries thousands of volts
  into layers that survive tens; the injury is often latent — works
  for months, fails in service. Strap, mat, chassis-first.
- DEBUG DOWNHILL FROM THE SUPPLY: when behaviour is impossible, check
  the rail under load, the reset's timing, and ground's actual voltage
  before blaming the logic — and budget the probe as a component, or
  chase the ghost of a circuit that changes when watched.

## MEANS
What the methods run on, with the numbers that matter.

- THE RESISTOR — the deliberate toll: sets currents, splits pushes,
  turns current into readable voltage; its heat rating is the limit.
- THE TWO SPRINGS — timers, filters, reservoirs, converters; from
  chip-side specks to the flash bucket.
- THE DIODE — one-way passage at fixed toll (~0.7 V silicon, ~0.3 V
  Schottky): protection, rectification, the coil's exit.
- THE TRANSISTOR AND THE OP AMP — the valve, and gain bought in bulk
  to be shaped by its surrounding network.
- THE CRYSTAL — one sharp rhythm, parts-per-million steady; the beat
  everything counts by.
- THE TWO MEMORY FAMILIES — a pair of gates holding each other up
  (fast, greedy) and a leaking bucket of charge reread thousands of
  times a second merely to keep saying the same thing (dense, cheap).
- THE HONEST INSTRUMENTS — meter (slow truth), scope (fast truth at
  the price of intruding); each a component of what it touches. The
  bench supply: current-limited so mistakes cost smoke, not boards.
- WIRE AND CABLE — twisted pair (difference-carried), coax (shield
  around signal); the plain wire is, at radio speeds, an aerial both
  ways.
- THE HEATSINK, FAN, AND PASTE — the chain's cheap links; air gaps are
  insulation. The strap and mat: charge given a quiet path so it never
  speaks through a chip.
- SOLDER AND THE IRON — the joint is an electrical part: a cold grey
  joint is a resistor; an intermittent one, a mystery filed for years.

## PURPOSE
The wants this subject answers — the doors a query enters by.

- DELIVER ENERGY IN THE LOAD'S SHAPE: stepped, steadied, rectified,
  regulated — from falling water to a chip's whisper.
- CARRY MEANING: stand a quantity of the world in for a quantity in a
  machine and move it — the signal job, shape as cargo.
- MAKE THE WEAK COMMANDING: amplification — a sensor's millionths of a
  volt given command of motors and speakers.
- DECIDE: the switch made arithmetic — gates answering
  both-either-neither at speed; all computation is this.
- REMEMBER AND KEEP TIME: a state held by feedback (the latch) or
  charge (the bucket); the crystal's beat under everything that
  counts.
- SENSE AND ACT BACK: the world into numbers (sample, quantize) and
  back out into light, sound, and motion.
- PROTECT PEOPLE: fuse in series, earth's third prong, breaker,
  isolation at the bedside — a fault finds a trip, not a person.

## HISTORY
How the knowledge arose, in what order, at what cost — the order
carries why.

- Charge known first as trick and terror: rubbed amber, stored jars,
  lightning — one thing, seen only when the jar's spark and the sky's
  were shown to be the same event at two sizes.
- The telegraph made wires carry meaning before power: continents
  wired for clicks before anyone wired them for light. The signal job
  is the older profession.
- The grid war was decided by a component: alternating current won
  because only a changing current steps up and down, and the I²R
  square made high voltage the only way to ship power far. The beaten
  direct current stayed — in every battery, every chip, back under the
  oceans — a surpassed method still best for some queries, exactly as
  the model says.
- The vacuum tube gave the first valve — amplification and radio born
  together; fragile, hot, hungry, it ran the first computers by the
  roomful.
- Feedback was invented to cross a continent: telephone repeaters
  drifted daily, and the trade — spend enormous gain to buy modest
  stability — was found there, then proved to be the shape of
  regulation everywhere: circuits, bodies, markets.
- The transistor replaced the tube — the same valve in a crumb of
  seeded crystal — and the integrated circuit put first dozens, now
  billions, on one crumb, doubling on a drumbeat for fifty years. The
  switch got so cheap that spending thousands on one decision became
  normal engineering.
- Quartz replaced the pendulum: a rock's rhythm, electrically spoken,
  put laboratory timekeeping on every wrist.
- The digital turn was the noise decision made once and for all:
  copies had always decayed; carrying verdicts instead of values made
  the ten-thousandth copy identical to the first — and sound,
  pictures, letters, and money moved into numbers for it.

## RELATIONS
First-class connections — the cascade's paths outward. Each names what
runs along it.

- PHYSICS: the loop's law, the square of current, fields and
  induction, aerial arithmetic, light's packets in every solar cell
  and LED. Electronics is physics given terminals.
- CHEMISTRY: every battery a reaction with wires attached — cell
  voltages, the surface-transport limit under heavy draw, doping as
  seeded impurities, corrosion as slow unsoldering.
- MATHEMATICS: true-and-false made physical, 2ⁿ states on n switches,
  twice-per-wiggle sampling, ratios in dividers and feedback, the RC
  curve's exponential.
- COMPUTING: this phylum's child — gates, memory, clocks, and the
  analogue truth under every digital fiction; hardware's lies become
  software's ghosts along this path.
- ENGINEERING: the board as built artifact, thermal chains, ratings
  and margins, the discipline that the drawing is not the thing.
- MEASUREMENT: every instrument is a circuit and every measured
  circuit is disturbed; precision-versus-accuracy runs both ways.
- MUSIC: amplifiers, microphones, balanced cables, crossovers — quiet
  floors and honest reproduction drove audio electronics into being.
- BODY: nerves as one-way pulses down loaded lines, the heart as
  oscillator (defibrillation as forced reset), senses as converters;
  the body solved signal-over-noise chemically first.
- MEDICINE: bedside isolation, the scanner's superconducting magnet in
  its helium cold, pacemakers — electronics trusted with lives.
- ECONOMY: power billed as push × flow × time; the transistor's
  collapsing cost rewrote what is worth automating; the grid a market
  for a good that cannot yet be stored (the mirror holds the want).
- EARTH AND WEATHER: the literal ground under every reference; storms
  stacking charge to breakdown; humidity deciding whether a winter
  walk arms a finger; the sky's noise on radio.
- ASTRONOMY: the sky heard in radio; receivers chilled toward the cold
  floor to hear faint stars under the amplifier's own hiss.
- CRAFT: soldering, layout, enclosure — the hand skills this phylum
  runs on; a joint is a made thing before it is a circuit element.
