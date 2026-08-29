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
THREAD: cooking (a hot oven making a different loaf, not a faster one),
  medicine (an animal model), weathering tests under lamps, wine.
ASKED-AS: accelerated life testing years weeks temperature chamber factor prediction lifetime realistic

ESSENCE: a model is a guess with arithmetic attached until it has been
  measured against a real thing. Calibration is what turns it into a
  tool — and it must be calibrated against something it did not help to
  design, or it is only agreeing with itself.
ROOT: evidence / a plan cannot test itself, and a model is a plan
  written in numbers.
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
THREAD: farming (ordering seed before knowing the season), building
  (the lift ordered at the start), publishing print runs, weddings.
ASKED-AS: long lead items ordered early delivery time transformer turbine design incomplete commit

ESSENCE: in any plan some tasks have slack and some do not, and only
  the ones without it move the finish date. Speeding up anything else
  produces activity and no progress — and the moment a task with slack
  slips far enough, it silently becomes one of the ones that matter.
ROOT: mathematics / the finish is set by the longest chain of dependent
  tasks, and everything else is waiting for that chain.
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
THREAD: building (fast layers tied to slow ones), aircraft flying with
  parts nobody makes, medical equipment on an unsupported operating
  system, railway signalling.
ASKED-AS: obsolete parts discontinued spares forty year system chips software support replacement fit
