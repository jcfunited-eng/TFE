# 125 DEEP ENGINEERING PRACTICE — how large things are actually built
Nothing here is about materials or sums. This is the other half of
engineering: agreeing what is wanted, proving it was achieved, running
it for thirty years, and finding out why it broke. Large projects fail
here far more often than they fail at the physics.

ESSENCE: a requirement says what the thing must do and a specification
  says how it shall be built — and confusing the two is how a project
  gets locked into one answer before anybody has understood the
  question. "Must survive a two-metre drop" leaves the field open.
  "Must have a rubber bumper" has already chosen.
ROOT: language / a description of a need and a description of a
  solution look identical on paper and do completely different work.
CANNOT: no good design from requirements that are secretly solutions —
  the alternatives were deleted before anybody compared them. And no
  requirement that is untestable being a requirement at all: if there
  is no measurement that could show it was missed, it is a wish with a
  number on it.
THREAD: law (a rule stating an outcome against one stating a method),
  teaching (a question that contains its own answer), cooking (a recipe
  against a description of the dish).
ASKED-AS: requirements specification what versus how customer asked design brief testable wish

ESSENCE: the requirements that cause the trouble are the ones nobody
  wrote down because everybody assumed them — that it can be lifted by
  two people, that it fits through a door, that it works in the rain,
  that somebody can reach the filter. These are discovered on site,
  after they cost the most.
ROOT: language / words are lossy vessels, and the parts of an
  expectation that seem too obvious to state are exactly the parts that
  never get stated.
CANNOT: no complete requirement list — the unwritten ones are invisible
  by definition, so the only defence is walking through the whole life
  of the thing with people who will use it. And no fixing this by
  writing more: obviousness is what hides them, and more paper does not
  make the obvious visible.
THREAD: making (an agreement that runs on its terms plus a larger
  unwritten expectation), software (the users' assumptions), building
  (the plan that ignores how people move).
ASKED-AS: forgot requirement obvious nobody said doesnt fit through door assumed missing implicit

ESSENCE: the requirements always conflict — lighter and stronger,
  cheaper and faster, safer and simpler. What actually happens is not
  that somebody resolves them, but that one quietly loses without a
  decision ever being recorded, and nobody can say afterwards who
  traded it away or for what.
ROOT: premise — the demands genuinely conflict, so there is a
  negotiated point and no maximum, and every negotiation has a loser.
CANNOT: no design meeting every requirement fully. And no honest
  project without the trades written down: an unrecorded trade cannot
  be revisited when the situation changes, so it hardens into a fact
  that nobody remembers choosing.
THREAD: making (a design as a settlement between parties who want
  different things), people and power (a rule kept and its reason
  lost), politics, budgets.
ASKED-AS: conflicting requirements tradeoff weight cost dropped quietly decision record why chosen

ESSENCE: every machine has a box of conditions it was designed for —
  a range of temperature, load, speed, voltage, users, weather. Inside
  the box its behaviour is known. Outside it, the design makes no
  promise at all, and most disasters happen a short distance outside a
  box nobody had drawn on paper.
ROOT: evidence / a design is validated over the conditions it was
  analysed and tested in, and says nothing whatever about the rest.
CANNOT: no design that is safe everywhere — the envelope has edges by
  construction. And no envelope that is real unless it is written and
  enforced: an unstated limit is one an operator will cross without
  ever knowing they left.
THREAD: aircraft flight envelopes, medicine (a drug tested on adults
  given to a child), a ladder's weight rating, sat-navs directing
  lorries down farm tracks.
ASKED-AS: operating limits envelope design conditions outside range temperature load rated exceeded

ESSENCE: what happens just outside the envelope is a design choice that
  is almost never made. A system can be built to slow down, complain,
  and hold — or to keep obeying right up to the moment it comes apart.
  The behaviour at the edge is where the safety actually lives.
ROOT: engineering / a system fails at its weakest point, so the
  designer gets to nominate not only where it fails but how it acts as
  it approaches.
CANNOT: no system without an edge, and no edge without behaviour there
  — the only question is whether that behaviour was designed or
  inherited by accident. And no discovering it in service safely: the
  edge case has to be tested deliberately or it is tested by an event.
THREAD: making (a part that bends, sags and warns against one that lets
  go whole), aircraft stall warnings, electrical fuses, a car that
  understeers gently rather than snapping.
ASKED-AS: overload behaviour limit exceeded warning gradual sudden failure edge case protection

ESSENCE: margin is eaten by many small decisions, each of them
  perfectly defensible. A little heavier here, a little hotter there,
  one more feature, a cheaper supplier — and no single step is wrong
  while the total quietly leaves nothing in hand. The last person to
  ask for something reasonable gets blamed.
ROOT: mathematics / independent small losses accumulate along a chain,
  and nobody owns the total unless somebody is made to.
CANNOT: no margin that survives an unowned budget — it has to be
  tracked and allocated like money, or it is spent by whoever asks
  first. And no knowing how much is left at the end without having
  counted at every step: margin is not visible in the finished thing.
THREAD: making (errors accumulating along a chain), weight in aircraft
  argued gram by gram, money (a contingency spent in the first quarter),
  packing a car boot.
ASKED-AS: margin eaten reserve gone weight budget contingency creep allowance nothing left

ESSENCE: a trade study looks like arithmetic and is mostly a judgement
  — because the weights chosen for cost, weight, risk and schedule
  decide the winner before a single number is entered. Change the
  weights by a little and a different option wins.
ROOT: evidence / a comparison across unlike things needs a rate of
  exchange between them, and that rate is an opinion nobody can measure.
CANNOT: no objective comparison of options that differ on several axes
  — the weighting is where the decision was actually taken. And no
  honest study that hides its weights: publishing them is what lets
  somebody argue with the decision instead of with the sum.
THREAD: money (a discount rate settling a hundred-year argument),
  hiring scorecards, sports rankings, any table where the columns get
  points.
ASKED-AS: trade study options scoring weights matrix decision comparison criteria chosen justify

ESSENCE: systems engineering exists for one reason: the parts can each
  be right and the whole still be wrong. Somebody has to own what
  happens between the boxes — the budgets for weight, power, heat and
  time, and every assumption one team made about another.
ROOT: people and power / specialisation raises output and destroys the
  overview, so the connections belong to nobody unless a job is created
  to hold them.
CANNOT: no large system correct by each team doing its own part well.
  And no ownership of the whole without authority over the parts: a
  systems role that can only advise ends up documenting a failure it
  predicted, which is the commonest shape this failure takes.
THREAD: orchestras and conductors, the body (organs that work and a
  person who does not), towns (buildings that are each fine on a street
  that is not), medicine (specialists and nobody treating the patient).
ASKED-AS: systems engineering whole integration parts each fine overall failed budgets ownership

ESSENCE: most requirements describe boxes and almost none describe the
  lines between them — yet the lines are where projects die. Two teams
  each build correctly to their own understanding of the boundary, and
  the two understandings differ by an assumption neither wrote down.
ROOT: making / an interface is where two independent chains of work are
  asked to agree, and each chain contains its own private reasoning.
CANNOT: no working interface without one owner and one written
  definition — shared ownership means nobody checks. And no interface
  that is only a drawing: it also carries timing, tolerance, power,
  heat, protocol, and who is responsible when it moves.
THREAD: making (two shops building halves that must meet), tunnels
  bored from both ends, language (a word two people use differently for
  a year), plumbing between two contractors.
ASKED-AS: interface between teams mismatch assumption boundary connector protocol both correct fit

ESSENCE: when two contracts meet, the gap between them belongs to
  nobody. Each side has priced its own scope and neither has priced the
  space in between — so the cable tray that crosses, the bracket that
  supports both, and the commissioning of the pair fall into a hole
  that is discovered on site.
ROOT: law / a contract binds what it names, and what it does not name
  is somebody else's problem by definition.
CANNOT: no gap-free split of a project into contracts. And no
  discovering these gaps by reading contracts side by side: they show
  up when somebody walks the interface asking who does the fixing, the
  testing, and the making good, which is work nobody is paid for.
THREAD: people and power (the free-rider problem in a hard hat),
  building (the steelwork and the glazing ordered from different
  drawings), medicine (handovers between wards).
ASKED-AS: scope gap contractors not my job between packages site clash responsibility contract missing

ESSENCE: everything on a project is fine until the parts are put
  together, and then all the schedule that was saved gets spent at
  once. Integration is where every optimistic assumption meets every
  other one, and it is the phase whose duration is always guessed and
  never known.
ROOT: mathematics / the number of pairs that must agree grows with the
  square of the number of parts, so the joining work grows much faster
  than the building work does.
CANNOT: no project finishing on time whose integration was estimated as
  a fixed percentage. And no shortening it by working harder in the
  parts: earlier partial integration is the only real cure, which costs
  schedule at the start to save it at the end.
THREAD: people (a meeting that works at six and dies at twenty),
  software (the merge nobody planned), building (the fit-out), an
  orchestra's first rehearsal together.
ASKED-AS: integration phase overran everything late assembly together first time schedule slipped

ESSENCE: verification asks whether the thing was built to the
  specification; validation asks whether the specification was the
  right one. A system can pass every test and still be useless, because
  the tests were written from the same misunderstanding as the design.
ROOT: evidence / a check made against a document can only find
  departures from that document, never faults inside it.
CANNOT: no validation from inside the project — it needs the user, the
  real environment, or somebody with no stake in the answer. And no
  substitute in more verification: testing harder against a wrong
  requirement produces a well-made wrong thing.
THREAD: teaching (a student who passes the exam and cannot do the job),
  software (built to spec and hated), law (a contract performed to the
  letter and useless), cooking to a recipe that was mistyped.
ASKED-AS: verification validation built right thing passed tests useless requirements wrong user

ESSENCE: a test that stops at the required load tells you the thing met
  the requirement and nothing about how much it had in hand. Testing to
  destruction is what tells you where the edge really is — and until
  something has been broken, the margin is a calculation rather than a
  fact.
ROOT: evidence / a limit is only known by finding it, and a test that
  never approaches the limit measures compliance rather than capability.
CANNOT: no knowing the real strength without breaking something. And no
  useful test that stops the moment it passes: the most valuable part
  of the run is what happens after the requirement is met, which is
  precisely the part that costs extra and gets deleted.
THREAD: making (samples broken to certify the rest), medicine (dose
  ranging to find the harm), bridges once loaded with soldiers, crash
  testing.
ASKED-AS: test to failure destructive break limit margin proof load passed requirement capability

ESSENCE: qualification testing proves the design and is done once,
  cruelly, on units that are then thrown away. Acceptance testing
  proves each individual unit and must never damage it. Mixing them up
  means either shipping a part that was hurt in test or approving a
  design on evidence that was too gentle to find anything.
ROOT: evidence / a claim about a design and a claim about one item are
  different claims and need different evidence.
CANNOT: no proving a design with tests mild enough to be run on
  deliverables. And no proving an individual unit with a test run on a
  different one — which is why every batch needs both, and why the
  cheapest thing to cut is the one that would have found the problem.
THREAD: making (a proof test spending some of a part's own life), exams
  against inspections, food safety (a recipe validated once and a batch
  checked every day).
ASKED-AS: qualification acceptance testing design unit each batch proof damaged sample delivered

ESSENCE: a test rig is itself a machine, with its own stiffness, its
  own resonances, and its own errors — so a surprising result is at
  least as likely to be the rig as the article. Half of testing is
  proving that the apparatus is not what you measured.
ROOT: evidence / every measurement is a measurement of the instrument
  and the subject together, and nothing separates them automatically.
CANNOT: no test result trusted before the rig has been checked against
  something known. And no rig that does not change the thing it holds:
  a fixture stiffer or softer than the real mounting gives an answer
  about a machine that will never exist.
THREAD: measurement (an instrument's own error), medicine (a trial
  measuring the trial's conditions), cooking (a recipe tuned to one
  oven), microphones changing the sound of a room.
ASKED-AS: test rig fixture results wrong apparatus calibration mounting stiffness artefact measurement

ESSENCE: a test only teaches you about the places you put sensors. If
  the failure happens somewhere unmeasured, you get an expensive event
  and no explanation — and the article is destroyed, so the run cannot
  be repeated with the instrument moved.
ROOT: evidence / data does not exist where it was not recorded, and no
  amount of later analysis can create a channel that was never wired.
CANNOT: no reconstructing an unmeasured failure from the wreckage
  alone. And no instrumenting everything: channels cost money, weight
  and time, so the sensor plan is a bet on where the surprise will be,
  made by the people least likely to guess the surprise.
THREAD: aircraft flight recorders, medicine (a monitor watching the
  wrong sign), photography (the shot you did not take), history (the
  records that happened to survive).
ASKED-AS: sensors instrumentation data missing channel failure unexplained test recorded measurements plan

ESSENCE: the most valuable thing that can happen in a test programme is
  something unexpected — and the strongest pressure in a test programme
  is to explain it away and carry on. A schedule turns an anomaly into
  a nuisance, and the nuisance turns up again later at full size.
ROOT: evidence / a surprise is information about a gap between the
  model and the world, and it is the only kind of information a test
  can produce that was not already known.
CANNOT: no learning from an anomaly that is closed without being
  understood — "could not reproduce" is not a resolution, it is a
  deferral. And no cheap time to investigate one: the moment it appears
  is always the moment there is least schedule to spend on it.
THREAD: medicine (the odd result in a trial), people and power (bad
  news thinning as it climbs), science (the anomaly that started a
  field), the intermittent fault nobody could catch.
ASKED-AS: anomaly test unexplained cleared could not reproduce ignored schedule pressure investigation

ESSENCE: an accelerated test squeezes years into weeks by turning
  something up — heat, load, cycles, humidity. It works only if the
  speeding up does not change how the thing fails. Push too hard and
  you have carefully measured a failure mode that would never have
  occurred.
ROOT: chemistry / rates rise with temperature in a knowable way, so
  time and temperature trade — but only while the same process is doing
  the damage.
CANNOT: no acceleration factor that is valid without knowing the
  failure mechanism. And no reading calendar life off an accelerated
  test alone: it ranks designs against each other reliably and predicts
  years unreliably, and it is nearly always quoted as though it did the
  second.
THREAD: cooking (a hot oven making a different loaf, not a faster one),
  medicine (an animal model), weathering tests under lamps, wine.
ASKED-AS: accelerated life testing years weeks temperature chamber factor prediction lifetime realistic

ESSENCE: a model is a guess with arithmetic attached until it has been
  measured against a real thing. Calibration is what turns it into a
  tool — and it must be calibrated against something it did not help to
  design, or it is only agreeing with itself.
ROOT: evidence / a plan cannot test itself, and a model is a plan
  written in numbers.
CANNOT: no confidence in an uncalibrated model however sophisticated —
  detail is not accuracy, and a finer mesh does not fix a wrong
  assumption. And no calibration that covers conditions never measured:
  a model tuned in one range is an extrapolation everywhere else.
THREAD: weather forecasting checked against what happened, medicine
  (a risk score validated on new patients), maps corrected by walking
  the ground, money (a valuation model fitted to its own history).
ASKED-AS: model simulation calibration validated against test measured reality accurate assumptions confidence

ESSENCE: a simulation answers the question it was set, under the
  assumptions it was given — steady load, perfect joints, uniform
  material, no corrosion, nothing rattling. Every one of those is a
  boundary on the answer, and the picture on the screen shows none of
  them.
ROOT: evidence / a computation contains only what was put into it, and
  what was left out leaves no trace in the result.
CANNOT: no simulation more reliable than its worst assumption — the
  colours look equally confident where the model is right and where it
  is nonsense. And no assumption list that is complete: the dangerous
  ones are the ones nobody knew they were making.
THREAD: making (a drawing that only checks the drawing), money (a
  forecast made of its own inputs), medicine (a prediction from healthy
  volunteers), maps that omit what they omit.
ASKED-AS: simulation assumptions boundary conditions results confident colours wrong analysis limits reality

ESSENCE: a model that was tuned until it matched the data will match
  that data — that is not evidence, it is arithmetic. The only real
  test is whether it predicts a measurement that was not available when
  the model was built.
ROOT: evidence / a claim fitted to observations cannot be checked
  against the same observations, because the fitting removed the
  disagreement by hand.
CANNOT: no validation from the data used for calibration. And no
  confidence from a good fit with many adjustable parameters: with
  enough knobs, any curve can be reproduced, and the fit says more
  about the knobs than about the world.
THREAD: money (a strategy tested on the history it was designed from),
  medicine (a score built and tested on one group), teaching to the
  test, forecasting after the event.
ASKED-AS: model fitted matched data prediction new test parameters tuned overfit validation independent

ESSENCE: a standard is the cheapest thing an engineer can buy —
  decades of other people's accidents compressed into a few clauses,
  paid for by somebody else. Working to one is not timidity; it is
  refusing to re-derive, alone and at your own risk, what a whole
  industry already learned expensively.
ROOT: keeping knowledge / a record outlives its maker, and a standard is
  a record of failures written as instructions.
CANNOT: no departing from a standard without taking on the burden of
  proving the alternative — the departure moves the responsibility onto
  you personally, entirely, which is the real reason they are followed.
  And no standard that explains itself: the clauses arrive without the
  bodies behind them, so they read as arbitrary until somebody digs.
THREAD: cooking (a technique that survived), medicine (protocols
  written out of deaths), law (precedent as compressed conflict),
  making (a tolerance published so strangers can hit it).
ASKED-AS: standards codes why clause follow deviation justify industry accumulated experience arbitrary

ESSENCE: a code is a floor, not a target. It describes the worst
  building or machine that may legally be produced — so "it meets code"
  answers a legal question and says nothing about whether the thing is
  any good, comfortable, durable, or sensible.
ROOT: law / a rule is written to be enforceable against the least
  careful party, so it is set where nobody can argue, which is low.
CANNOT: no quality guaranteed by compliance. And no code covering
  everything that matters: it covers what can be written, measured, and
  defended in a dispute, which leaves out most of what makes something
  good to live with or to operate.
THREAD: building (a code minimum insulation against a comfortable
  house), food hygiene rules against a good kitchen, exams as a
  minimum, speed limits.
ASKED-AS: meets code minimum standard legal compliance good enough quality building regulations exceeds

ESSENCE: you cannot inspect everything, so inspection is a sample, and
  a sample gives a probability rather than a certainty. Doubling the
  number checked does not double the confidence, and the number
  inspected has to be argued from what failure would cost, not from
  what feels thorough.
ROOT: chance / a conclusion about a batch from a handful of items is a
  statistical claim, whose strength is set by the size of the sample
  and the rate being looked for.
CANNOT: no quality inspected into a product at the end — inspection
  sorts, it does not improve, and it finds a rate that the process
  already fixed. And no sampling that finds a rare fault: catching a
  one-in-a-thousand defect reliably means checking thousands.
THREAD: making (yield setting the real price), medicine (screening and
  its false results), customs checks, farming (grading a harvest from a
  scoop).
ASKED-AS: inspection sampling batch checked percentage quality control rare defect confidence sorting

ESSENCE: every inspection method has a smallest thing it can see, and
  anything smaller is invisible to it. So "inspected and passed" never
  means there is no crack — it means there is no crack larger than the
  method could detect, which is a completely different sentence.
ROOT: evidence / an instrument has a detection limit, and a negative
  result is a statement about the instrument as much as about the part.
CANNOT: no inspection proving the absence of a flaw. And no inspection
  interval set without knowing that limit: the whole logic is that a
  crack too small to see must stay too small to matter until the next
  look, which requires knowing both the smallest visible size and how
  fast it grows.
THREAD: medicine (a scan that cannot see a small tumour), airport
  security, farming (pests below a threshold), astronomy (a survey
  reporting what it could see).
ASKED-AS: inspection passed crack undetected smallest size ultrasonic dye penetrant limit interval

ESSENCE: commissioning is the first time the whole thing is run as one
  system rather than as a collection of correctly installed parts — and
  it routinely finds problems that no amount of component testing could
  have found, because those problems only exist in the combination.
ROOT: making / an assembly has behaviour its parts do not, so the first
  full run is an experiment whatever the paperwork says.
CANNOT: no handing over an uncommissioned system honestly. And no
  compressing commissioning without moving its findings into service:
  the discoveries are made either by the commissioning team or by the
  operators, and the second is far more expensive and less forgiving.
THREAD: making (the first build as an instrument for producing
  surprises), an orchestra's first full rehearsal, a restaurant's soft
  opening, a hospital ward opened before its systems were run together.
ASKED-AS: commissioning first run whole system snags handover startup problems together tested

ESSENCE: the drawings say what was intended and the building says what
  happened. Somebody moved a duct around an unexpected beam, a valve
  went in the other way round, a wall shifted three hundred millimetres
  — and unless the record was corrected, the next person drills into
  something nobody drew.
ROOT: evidence / a record is only as true as its last update, and
  updating it happens after the work, when everybody has moved on.
CANNOT: no as-built record that is free without being paid for during
  construction — collected at the end, it is reconstructed from memory
  and it is wrong. And no safe alteration of an old system from design
  drawings alone: they describe an intention that was thirty years ago.
THREAD: maps that were never updated, medicine (notes that do not match
  the patient), keeping knowledge (a record outliving its maker), old
  wiring behind plaster.
ASKED-AS: as built drawings differ actual site changes record updated survey drilled unexpected

ESSENCE: over a system's life the paper version and the real version
  drift apart — a modification here, a temporary fix that stayed, a
  procedure everybody stopped using. The organisation then manages the
  paper one, which is the only one it can see, while the real one keeps
  running.
ROOT: people and power / bad news thins as it climbs, and a divergence
  from the documented state is a small piece of bad news at every step.
CANNOT: no plant that stays identical to its documentation without
  deliberate, funded effort. And no safety argument built on documents
  that were not checked against the plant: an analysis of a system that
  no longer exists is a comfort, not a defence.
THREAD: software (the diagram nobody updated), law (rules on the books
  and not on the street), accounting (two systems both claiming to be
  the record), the recipe versus what the cook actually does.
ASKED-AS: documentation outdated actual plant modifications temporary fix permanent drift paperwork reality

ESSENCE: a maintenance interval is a claim about how something fails,
  and most intervals were inherited rather than derived. Replacing a
  part every year makes sense if it wears out on a schedule — and no
  sense at all if it fails randomly, which most parts do.
ROOT: chance / a failure rate that does not rise with age gives no
  reason to replace anything early, since the new one is as likely to
  fail as the old.
CANNOT: no interval justified without knowing whether the failure rate
  rises with age. And no benefit from replacing a random-failure part
  early — it costs money, takes the machine out of service, and
  introduces a fresh chance of installation error for nothing.
THREAD: medicine (routine screening that helps and routine screening
  that harms), replacing tyres by depth against by date, filters,
  aircraft maintenance rebuilt around this discovery.
ASKED-AS: maintenance interval schedule replace hours annual why that number wear random failure

ESSENCE: the useful question is not when a part will fail but how long
  it gives you between the first detectable sign and the failure
  itself. That gap sets the inspection interval — you must look at
  least twice inside it — and where the gap is minutes, no inspection
  schedule can help at all.
ROOT: chance / a detectable warning is only useful if somebody looks
  during the window it is present, so the window and the looking rate
  are one design.
CANNOT: no inspection catching a failure whose warning is shorter than
  the interval. And no inspection strategy at all for a mode with no
  warning: those must be designed out, protected against, or accepted,
  because looking more often does not reach them.
THREAD: medicine (a screening interval set by how fast a disease
  progresses), tyre tread, bridge cables, the noise a bearing makes for
  a week before it seizes.
ASKED-AS: warning signs before failure inspection interval detect noise vibration window catch time

ESSENCE: watching a machine's condition — its vibration, its
  temperature, the metal in its oil — replaces a calendar with
  evidence, and lets a part be changed when it needs changing rather
  than when the diary says. It costs sensors, analysis, and somebody
  who reads the trend.
ROOT: evidence / a measurement of the actual state beats a prediction
  from age, provided the measurement really tracks the damage.
CANNOT: no condition monitoring without knowing which signal precedes
  the failure — measuring the wrong thing gives a comforting flat line.
  And no benefit from data nobody looks at: the failure mode of
  monitoring is not a broken sensor, it is an unread trend.
THREAD: medicine (blood tests against age-based rules), the body (pain
  as a monitor), farming (soil testing rather than a fixed fertiliser
  schedule), engine oil analysis.
ASKED-AS: condition monitoring vibration oil analysis trend predictive maintenance sensors data unread

ESSENCE: most things do not wear out. Their chance of failing is high
  when brand new — from installation errors, manufacturing faults and
  wrong parts — then settles to a low steady rate for a long time.
  Which means an overhaul often resets a machine to its most dangerous
  period.
ROOT: chance / early failures come from mistakes and defects rather
  than from age, so a fresh installation carries a fresh chance of
  every one of them.
CANNOT: no assuming that newer is safer. And no overhaul that is free
  of this risk: any intervention that opens a system reintroduces the
  infant-mortality period, which is why unnecessary maintenance
  measurably lowers reliability rather than raising it.
THREAD: medicine (surgery carrying its own risk), computing (a reboot
  that breaks a machine that had run for years), a car that develops a
  fault right after a service.
ASKED-AS: infant mortality bathtub curve new parts fail overhaul made worse reliability service

ESSENCE: a large share of failures happen shortly after somebody worked
  on the machine — a connector not reseated, a tool left inside, a
  filter fitted backwards, a valve left shut. Maintenance is not a
  neutral act; it is an intervention with its own failure rate.
ROOT: chance / across enough repetitions every possible error occurs at
  its own steady rate, and maintenance is a long series of manual
  operations under time pressure.
CANNOT: no maintenance without a risk of introducing a fault. And no
  reducing it by exhortation — the answers are fewer interventions,
  work that cannot be done wrongly, and a functional check afterwards
  that would reveal it.
THREAD: making (a part that can be fitted backwards will be), medicine
  (hospital-acquired infection), aviation checklists, surgical counts
  of instruments.
ASKED-AS: failed after service maintenance error reassembly left tool connector loose check afterwards

ESSENCE: a backup that is never exercised is not a backup, it is a
  belief. Standby pumps, emergency generators, alarms, relief valves
  and spare channels can all sit broken for years without anybody
  discovering it, because nothing about their failure shows.
ROOT: evidence / a fault in a device that is not being used produces no
  symptom, so it can only be found by deliberately going to look.
CANNOT: no protection from an untested standby — the failure and the
  demand arrive together, which is exactly the worst arrangement. And
  no measuring redundancy without a test regime: two channels with an
  unknown failure rate are not two channels, they are one and an
  assumption.
THREAD: smoke alarms with dead batteries, fire pumps started monthly on
  purpose, medicine (a screening programme finding what has no
  symptoms), insurance policies nobody ever read.
ASKED-AS: backup never tested standby generator failed when needed latent fault check regularly

ESSENCE: two of the same thing protect against one of them breaking by
  chance, and not at all against a fault in the design, the batch, the
  software, or the maintenance — because both have it. Real redundancy
  against a design error must be different in kind, and that costs far
  more than a second copy.
ROOT: chance / independence is what makes duplication work, and two
  identical items share every cause that is not random.
CANNOT: no protection from duplication against a common cause. And no
  cheap diversity: two genuinely different designs mean two development
  efforts, two sets of spares, two training regimes, and two chances of
  a mistake — which is why it is reserved for the few places it is
  worth it.
THREAD: money (everybody hedged with the same counterparty), farming (a
  field of identical plants), aircraft with hydraulics of different
  design, two engines fed from one tank.
ASKED-AS: redundancy two identical backup same fault diverse design duplicate protection common software

ESSENCE: the thing that defeats redundancy is a cause that reaches
  every copy at once — one flood, one power supply, one wrong batch,
  one instruction issued to all of them, one maintenance visit. The
  copies are only independent if nothing they share can fail.
ROOT: chance / a shared dependency turns several devices into one
  device with several bodies.
CANNOT: no independence between units sharing a supply, a room, a
  cable route, a technician, or a design. And no finding these by
  looking at the units: they are found by tracing what every copy
  depends on, which is a different and less popular exercise.
THREAD: money (systemic risk), the living world (a monoculture and one
  disease), data centres with both feeds in one trench, back-ups stored
  in the building they back up.
ASKED-AS: common cause both failed same room power supply batch flood shared dependency independent

ESSENCE: three channels voting two-to-one sounds unarguable, until you
  ask what compares them. The voter is a single thing that can fail,
  and a fault in it defeats all three — so the arrangement moves the
  problem rather than removing it, and the voter becomes the part that
  matters most.
ROOT: engineering / a system fails at its weakest point, and adding
  copies creates a new component whose job is to decide between them.
CANNOT: no voting scheme without a decider, and no decider that cannot
  fail. And no protection from a fault that makes two channels agree
  wrongly: a shared sensor error is unanimous, and unanimity is exactly
  what the voter is built to trust.
THREAD: people (an agreed way to change the rules), courts and their
  judges, computing (a coordinator that becomes the single point),
  three clocks that all drifted the same way.
ASKED-AS: voting three channels two out of redundancy decider single point agree wrongly

ESSENCE: a well-designed system does not go from working to dead. It
  sheds functions in an order somebody chose — losing the comforts,
  then the conveniences, then the non-essential, keeping the core
  running on the last supply. That order is a design decision and it
  is usually never made.
ROOT: engineering / a designer nominates the weakest point, and the
  same authority lets them nominate the sequence in which capability
  is given up.
CANNOT: no system that never loses anything. And no graceful
  degradation without deciding beforehand what is essential — under
  failure there is no time to work it out, so a system that has not
  chosen will shed whatever happens to go first.
THREAD: the body (blood withdrawn from the skin before the organs),
  aircraft dropping to standby instruments, power grids shedding load
  by district, a phone dimming its screen at low battery.
ASKED-AS: degraded mode partial failure limp home backup essential functions shed priority order

ESSENCE: after a failure the question is not who was careless but what
  the wreckage says. Metallurgy, fracture surfaces, recorded data and
  the sequence of events answer it — and the investigation has to
  resist the pressure to reach the answer everybody already expected on
  the first afternoon.
ROOT: evidence / a physical failure leaves marks that record how it
  happened, and those marks do not care what anybody's theory was.
CANNOT: no honest failure analysis under a deadline set by a lawsuit or
  a press cycle. And no reading the cause off the biggest broken piece:
  the part that failed first is often small, undramatic, and elsewhere,
  and everything else broke afterwards as a consequence.
THREAD: medicine (a post mortem), aviation accident investigation,
  detective work, the fuse that blew because something else was already
  wrong.
ASKED-AS: failure analysis broken part why investigation fracture surface evidence blamed first cause

ESSENCE: large accidents do not have a cause, they have a chain — a
  design weakness, a maintenance shortcut, an ambiguous procedure, a
  tired operator, and a bad day, all of which had to line up. Naming
  one of them "the root cause" is an administrative act, and it usually
  names the last human in the sequence.
ROOT: chance / a system with defences fails only when several
  independent things go wrong together, so a single-cause story is
  almost always incomplete.
CANNOT: no single root cause of a defended system's failure. And no
  safety improvement from a report that stops at the last person to
  touch it: fixing that one link leaves every other link exactly as it
  was, ready for the next combination.
THREAD: medicine (a patient death with six contributing factors), the
  Swiss cheese picture of layered defences, history (a war with one
  named trigger), family arguments.
ASKED-AS: root cause contributing factors chain accident blame single reason report investigation

ESSENCE: before the failure, listing every way each part could fail and
  what it would do is dull, slow, and the cheapest safety work there
  is. Done afterwards, the same list is called an investigation and it
  costs a hundred times more.
ROOT: evidence / a rule can only encode what has been imagined or seen,
  so imagining systematically is the only way to get ahead of the
  seeing.
CANNOT: no such list being complete — it finds the failures somebody
  could think of, which is why it never replaces testing or operating
  experience. And no value from one done as a formality: a table filled
  in to satisfy a reviewer finds nothing, and its existence is then
  used as evidence that the thinking was done.
THREAD: medicine (asking what else it could be), chess (looking at the
  opponent's replies), insurance underwriting, pre-mortems.
ASKED-AS: failure modes analysis fmea what if list beforehand checklist formality reviewer thinking

ESSENCE: the first time a rule is broken and nothing bad happens, the
  breach becomes evidence that the rule was too strict. Repeat this and
  the abnormal becomes the normal, in small defensible steps, until the
  organisation is operating far outside what it would ever have
  approved in one move.
ROOT: evidence / absence of harm is read as proof of safety, even
  though the defence that was removed is exactly the one that only
  matters on a rare day.
CANNOT: no organisation holding a standard it routinely exceeds without
  consequence — the standard follows the practice. And no self-
  correction from inside: everybody present remembers the last hundred
  times it was fine, and the newcomer who objects is told how things
  actually work.
THREAD: the space shuttle programme's o-rings, people and power (a rule
  kept and its reason lost), speeding, medicine (a shortcut that saves
  ten minutes every day for years).
ASKED-AS: normalisation deviance shortcut got away with it standard slipped accepted practice drift

ESSENCE: an operator is part of the machine, and the machine's design
  decides what they will do at three in the morning. Which way a lever
  moves, whether two switches look alike, whether the display shows
  what the system is actually doing — these settle the error rate far
  more than training does.
ROOT: the mind / attention is narrow and under stress it narrows
  further, so behaviour follows what the equipment makes easy.
CANNOT: no design that removes human error by instruction. And no
  operator reliably tracking a state the display does not show: mode
  confusion is a design fault wearing a person's name, and it recurs
  wherever a control means different things at different times.
THREAD: making (a part that can be fitted backwards will be), aircraft
  cockpits redesigned after identical-looking levers, hobs whose knobs
  do not map to their rings, medicine (look-alike drug packaging).
ASKED-AS: human error operator mistake controls display confusing switches design layout training

ESSENCE: an alarm that goes off often and means nothing is worse than
  no alarm, because it trains people to ignore it. In a real upset,
  hundreds arrive at once and the important one is somewhere in the
  list — and by then nobody is reading the list at all.
ROOT: the mind / attention is one beam and a signal that is usually
  false stops earning any of it.
CANNOT: no alarm system that works without ruthless pruning — every
  alarm must have an action, a priority, and a reason to exist, or it
  is noise with a legal justification. And no operator handling a flood
  of them: the number that can be dealt with per minute is small, fixed
  by people, and not negotiable.
THREAD: car warning lights taped over, medicine (monitor alarms and
  desensitised nurses), fire alarms in a building that has them weekly,
  crying wolf.
ASKED-AS: alarms too many nuisance ignored flood priority console operator overwhelmed alerts

ESSENCE: automating the routine work leaves the human with only the
  rare, difficult, sudden situations — the ones automation could not
  handle — while removing the daily practice that would have kept them
  sharp. So the operator is asked to be at their best precisely where
  they have had least experience.
ROOT: the mind / skill is maintained by use, and automation removes
  exactly the ordinary use through which the skill was kept alive.
CANNOT: no automation that leaves the operator's job unchanged — it
  changes it from doing to watching, and people are poor at watching.
  And no handover from machine to human that is instantaneous: the
  human needs to know what has been happening, and the moment of
  handover is when they know least.
THREAD: autopilots and manual flying practice, self-driving handovers,
  medicine (relying on a decision tool), calculators and arithmetic.
ASKED-AS: automation operator monitoring skills faded takes over emergency handover autopilot watching

ESSENCE: when a system is designed so that a mistake is easy and its
  consequence is severe, the person who makes it is not the cause — but
  they are the one standing there, they are the cheapest thing to
  correct, and the report writes itself. So the design fault survives,
  wearing somebody's name.
ROOT: people and power / attention goes to what is concrete and
  present, and a person is far more concrete than an arrangement.
CANNOT: no learning from an investigation that ends at the operator —
  the same trap is left set for the next one. And no honest reporting
  culture where the report ends in blame: the information stops
  arriving, which removes the only means of finding the traps.
THREAD: aviation's deliberately unpunishable incident reports, people
  and power (the whistleblower punished for a true report), medicine
  (blaming a nurse for a labelling system), rail signalling.
ASKED-AS: operator blamed human error design fault report punished culture reporting stopped trap

ESSENCE: procedures get written for the normal case by somebody who has
  time, and they are used in the abnormal case by somebody who does
  not. So the steps that matter most are the ones least likely to have
  been written, and the procedure often runs out precisely where the
  situation started to be difficult.
ROOT: language / an instruction is a compressed copy of an intention,
  and what the writer thought was routine got compressed hardest.
CANNOT: no procedure covering every case it will meet. And no operator
  who can follow one they have never rehearsed under pressure — reading
  is not doing, so an unpractised emergency procedure is a document
  rather than a capability.
THREAD: people and power (a written rule bought at the price of the odd
  case), fire drills, aviation checklists rehearsed until automatic,
  recipes that assume you know how it should look.
ASKED-AS: procedure emergency written normal case abnormal steps missing rehearsed drill pressure

ESSENCE: how a thing is bought decides much of how good it will be.
  Awarding to the lowest price without qualifying the bidders selects
  for whoever misunderstood the job — because the bidder who
  understood it priced the difficult parts and therefore lost.
ROOT: money / a price is where two valuations meet, and a bid that is
  too low is usually a misreading rather than an efficiency.
CANNOT: no quality bought by price alone. And no cheap escape once a
  wrong bidder is appointed: the shortfall comes back as claims,
  variations, delays and disputes, and the total exceeds every bid that
  was rejected.
THREAD: money (adverse selection — the eager seller knows why),
  hiring, medicine (the cheapest supplier of a critical item), building
  contracts settled in court years later.
ASKED-AS: lowest bid tender cheapest contractor underbid claims variations quality procurement selection

ESSENCE: a specification can name a product or describe a performance,
  and the choice decides who carries the risk. Name the part and you
  own whether it was the right part. Describe what it must achieve and
  the supplier owns it — but only if the description is measurable.
ROOT: law / a contract binds what it names, so what is specified is
  what has been taken responsibility for.
CANNOT: no shifting risk to a supplier with an unmeasurable
  performance clause — "suitable for purpose" without a test is an
  argument, not a requirement. And no innovation from a specification
  that names the part: it has already forbidden every other answer,
  including better ones.
THREAD: requirements against specifications, building (a design-and-
  build contract against a drawn one), law (a rule stating an outcome
  or a method), buying a service against buying a thing.
ASKED-AS: specification performance prescriptive named product supplier responsibility measurable clause risk

ESSENCE: the quality of a large project is made three or four levels
  down the supply chain, where nobody from the client has ever been.
  The main contractor manages contracts; the welding is done by a
  subcontractor's subcontractor, on a rate, on a Friday.
ROOT: people and power / delegation loses what cannot be said, and each
  further level loses it again, while the accountability stays at the
  top where it cannot see.
CANNOT: no quality assured by paperwork travelling up the chain — the
  certificates arrive whatever happened. And no visibility without
  going to look: the only reliable inspection is somebody's presence at
  the place the work is being done.
THREAD: making (the maker finds the truth first), food supply chains
  and their scandals, people and power (bad news thinning as it
  climbs), clothing factories.
ASKED-AS: subcontractor chain quality certificates paperwork site visit levels down who actually

ESSENCE: the items with the longest delivery time decide the shape of
  the whole plan, and they must be ordered before the design that
  depends on them is finished. So large projects commit to their
  biggest, least reversible purchases at the moment they know least.
ROOT: making / an assembly is a stack of one-way doors, and the door
  that takes eighteen months to open must be opened first.
CANNOT: no waiting for design maturity on a long-lead item without
  losing the schedule. And no cheap change once it is ordered — which
  is why the early decisions about transformers, turbines, bearings and
  pressure vessels are the ones that later look reckless and were
  merely early.
THREAD: farming (ordering seed before knowing the season), building
  (the lift ordered at the start), publishing print runs, weddings.
ASKED-AS: long lead items ordered early delivery time transformer turbine design incomplete commit

ESSENCE: in any plan some tasks have slack and some do not, and only
  the ones without it move the finish date. Speeding up anything else
  produces activity and no progress — and the moment a task with slack
  slips far enough, it silently becomes one of the ones that matter.
ROOT: mathematics / the finish is set by the longest chain of dependent
  tasks, and everything else is waiting for that chain.
CANNOT: no shortening a project by accelerating work that is not on the
  chain. And no fixed critical path: as delays accumulate the chain
  moves, so a plan that identified it once and never looked again is
  managing yesterday's project.
THREAD: traffic (a jam at one junction), cooking a large meal, the body
  (the slowest step in a reaction), the queue with one slow till.
ASKED-AS: critical path schedule delay float slack tasks finish date speed up chain

ESSENCE: schedule pressure is the commonest ingredient in serious
  accidents — not because anybody decides to be unsafe, but because it
  is the thing that turns every other weakness on. Tests get shortened,
  anomalies get closed, checks get skipped, tired people work another
  shift, and each of those is defensible on its own.
ROOT: premise — behaviour follows incentives, and a deadline is the
  loudest incentive in any organisation, felt daily by everyone.
CANNOT: no safety culture surviving a schedule that is known to be
  impossible — people will find the flex somewhere, and the flex is
  always in the checking. And no measuring this from inside: nobody
  logs "we hurried", so it appears in the record only as the things
  that were not done.
THREAD: aviation and rail disasters with a departure time behind them,
  medicine (a shift that ran long), construction, exams, launch windows.
ASKED-AS: deadline pressure rushed skipped checks accident schedule launch shift tired hurry

ESSENCE: work is ninety per cent done for most of its life. The final
  stretch holds all the integration, the awkward exceptions, the
  paperwork and the things that only appear when everything else is
  finished — and it is estimated by people looking at how much of the
  visible work is complete.
ROOT: evidence / progress is judged by what can be seen, and the
  remaining difficulty is by definition the part nobody has looked at
  yet.
CANNOT: no honest completion figure without counting what has been
  proved rather than what has been produced. And no schedule recovered
  in the last ten per cent: it contains the fewest opportunities to
  parallelise and the most dependencies, so it is where lateness gets
  realised rather than caused.
THREAD: writing (the draft against the finished piece), building
  snagging lists, software (the last bugs), moving house, the last mile
  of a journey.
ASKED-AS: ninety percent done last ten remaining takes longer estimate progress finishing snagging

ESSENCE: over a long life a fleet stops being one design. Every
  modification, repair, and substitution applied to some units and not
  others means the drawings describe an average machine that does not
  exist — and a spare part or a procedure correct for one is wrong for
  another.
ROOT: keeping knowledge / a record must be updated per item, and effort
  spent on records is the first thing dropped when the work is urgent.
CANNOT: no fleet staying identical without deliberate configuration
  control. And no safe generic instruction to a divergent fleet: the
  procedure that is right for most is the one that damages the odd
  unit, and nobody knows which unit that is until afterwards.
THREAD: software (versions in the field), medicine (a treatment
  protocol against an individual patient), cars with mid-year changes,
  buildings altered over decades.
ASKED-AS: configuration control versions fleet modifications which serial number spares drawings differ

ESSENCE: the first of anything costs more than anybody believes,
  because there is no learning curve yet, every estimate is an analogy
  from something different, and the problems are unknown rather than
  merely unquantified. The second is cheaper, and everybody remembers
  the second when planning the next first.
ROOT: evidence / an estimate is built from experience, and for a
  first-of-a-kind the relevant experience does not exist yet.
CANNOT: no accurate cost or schedule for a genuinely new large system.
  And no learning-curve savings on a project that only ever builds one:
  the whole benefit arrives in units that are never ordered, which is
  why first-of-a-kind economics ruin so many good ideas.
THREAD: making (the first unit carrying all the thinking), first
  nuclear plants of a design, tunnels, medicine (the first pill costing
  a billion), custom houses.
ASKED-AS: first of kind prototype cost overrun new design estimate learning curve second cheaper

ESSENCE: after every serious failure a report is written, and it is
  usually right. The difficulty is that reading it is nobody's job,
  the people who most need it are in a different company, and the
  lesson is only remembered by whoever was present. So the same
  accident recurs, in a new industry, a decade later.
ROOT: people together / an institution recruits new humans into old
  shapes, and the shapes travel far better than the reasons do.
CANNOT: no lesson learned by being written down. And no transmission
  without a mechanism — a standard changed, a design rule added, a
  training case taught — because a document with no owner is a
  document nobody reads.
THREAD: people and power (a rule kept and its reason lost), aviation
  turning findings into mandatory changes, medicine (near-miss
  registers), history repeating in a new sector.
ASKED-AS: lessons learned report filed nobody reads same accident again industry knowledge transfer

ESSENCE: for every accident there were many near misses that produced
  no damage and therefore no report. Those are the cheap data — the
  same trap, sprung without the cost — and they exist only in an
  organisation where reporting one is safe and welcome.
ROOT: chance / a rare bad outcome is preceded by many more encounters
  with its cause, so the causes are far easier to observe than the
  outcomes.
CANNOT: no near-miss data in a culture that punishes the reporter —
  the incidents continue and the reports stop, and management sees an
  improving record. And no waiting for accidents as a measurement:
  they are too rare to steer by, so a programme judged on accident
  counts is flying on a gauge that barely moves.
THREAD: aviation's protected reporting, people and power (the
  whistleblower punished for a true report), medicine, iceberg pictures
  with one accident above many incidents.
ASKED-AS: near miss reported no damage incident data culture punished statistics accidents rare

ESSENCE: every large project meets its real difficulty late — the thing
  that ends up defining it was not on the risk list at the start,
  because the early risks were the ones people could already imagine.
  The known difficulties get solved; the project is decided by the one
  nobody named.
ROOT: evidence / a plan can only anticipate a kind of trouble somebody
  has met, and a genuinely new undertaking contains kinds nobody has.
CANNOT: no complete risk register. And no protecting against an unnamed
  risk with a specific contingency: what covers it is general slack —
  time, money and margin held back — which is the first thing an
  efficient plan removes.
THREAD: making (a margin guarding against the size of a surprise and
  never its species), expeditions, medicine (the complication that was
  not on the consent form), war plans.
ASKED-AS: unknown risk late discovery register never expected difficulty biggest problem contingency slack

ESSENCE: a system designed to run for forty years is built from parts
  with five-year lives — chips, controllers, sensors, software,
  suppliers. Long before the structure is tired, its brain is
  unbuyable, and the replacement does not fit, physically or logically.
ROOT: making / a design is not real until every line can be bought, and
  what can be bought changes faster than what has been built.
CANNOT: no long-lived system without a plan for its short-lived parts —
  either spares bought at the start, or interfaces designed so a
  successor can be substituted. And no substituting a modern part
  quietly: the new one behaves differently, so it needs qualifying as
  though it were a new design.
THREAD: building (fast layers tied to slow ones), aircraft flying with
  parts nobody makes, medical equipment on an unsupported operating
  system, railway signalling.
ASKED-AS: obsolete parts discontinued spares forty year system chips software support replacement fit
