# 104 DEEP WRITING SOFTWARE — the working knowledge of building programs

ESSENCE: a name is a claim about what a thing IS, planted where
  every future reader will trip over it. Readers believe the name
  over the code, so a wrong name teaches the wrong idea to
  everyone who comes after, forever.
ROOT: language / a word carries its concept into every head that
  reads it.
CANNOT: no clear thought about a badly named thing — nobody
  re-derives the truth from the lines when a confident name sits
  right there. And no good name for a thing holding two ideas;
  the struggle to name it IS the design confessing.
THREAD: biology (a misfiled species hides from its own kin), law
  (a term defined loosely is argued over for a century), kitchens
  (the jar labelled sugar holding salt).
ASKED-AS: naming names called label what to call it bad confusing rename word variable

ESSENCE: the name is the test. Say aloud what a piece does; if
  the sentence needs the word "and", or trails into "and also",
  you are holding two things in one coat and the coat is the only
  thing joining them.
ROOT: this file / a name is a claim about what a thing is.
CANNOT: no honest short name for a piece with two jobs — the name
  either lies by leaving one out, or grows into a description. No
  reuse of such a piece either; whoever wants half of it must
  take both halves.
THREAD: tools (a thing sold as a knife-and-spoon is neither),
  teaching (a lesson with two aims teaches neither), writing (the
  sentence that will not shorten holds two sentences).
ASKED-AS: function job does two things and split it up name describe what it does

ESSENCE: state is memory kept inside the program, and it is where
  most difficulty lives. With state, the same call with the same
  inputs gives different answers, because something that happened
  earlier and elsewhere decided which way it goes.
ROOT: causation / the next moment is written from this one, and
  the past is not printed on the page.
CANNOT: no understanding a stateful part by reading it — the page
  shows the rules, never the history that chose the branch. No
  two runs alike without the same history, whether or not anyone
  wrote that history down.
THREAD: medicine (a symptom that depends on last month), law (a
  penalty that depends on prior convictions), games (the same
  move is brilliant or fatal depending on the position).
ASKED-AS: state remembers different answer same input depends on earlier history changes over time

ESSENCE: a value that can never change cannot be changed behind
  your back. Hand it to ten workers, hold it across an hour, put
  it in a list — none of them can spoil it for the others. Whole
  families of fault simply have nowhere to happen.
ROOT: this file / state is where difficulty lives; remove change
  and the difficulty leaves with it.
CANNOT: no stale copy, no half-updated thing, and no surprise
  from a distance in something that cannot be written to. But no
  free lunch either: to change an unchangeable thing you must
  build a new one, and building costs.
THREAD: law (a signed original versus a page anyone may amend),
  money (a receipt that cannot be edited afterwards), writing
  (ink for contracts, pencil for drafts).
ASKED-AS: cannot change frozen fixed value copy never changes safe share read only constant

ESSENCE: a piece that only computes tells you everything in its
  name and its answer. One that also writes a file, sends a
  message, or alters a shared value is doing work the caller
  cannot see and did not agree to.
ROOT: this file / the name is a claim about the whole of what a
  thing does.
CANNOT: no local reasoning where effects are hidden — to know
  what one line does you must open every piece it calls, and
  every piece they call. No repeating a call safely when the
  first call already changed the world.
THREAD: medicine (a drug with undeclared second actions),
  contracts (a clause that also signs you up elsewhere), cooking
  (a recipe that quietly uses tomorrow's ingredients).
ASKED-AS: side effects writes files sends changes something else hidden surprise does more than returns

ESSENCE: cohesion is how much a part's insides belong together;
  coupling is how much it leans on other parts. Change travels
  along couplings — so put what changes together in one place,
  and keep the paths between places few and thin.
ROOT: craft / things that are used together are stored together.
CANNOT: no changing one end of a tight coupling alone; the other
  end comes with it. And no zero coupling in a system that does
  anything — parts must touch, so the craft is choosing where and
  how narrowly.
THREAD: the body (organs joined by few clean vessels), cities (a
  grid you can redevelop block by block, versus a knot), machines
  (bolted apart beats welded solid).
ASKED-AS: tangled connected depends touching everything belongs together apart tight loose change spreads parts

ESSENCE: what a part promises is what others may lean on; all the
  rest is its private business, free to be thrown away tomorrow.
  The promise is a debt you take on. The secret is the only
  freedom you keep.
ROOT: law / what is published and relied upon binds; craft / a
  tool is used by its handle.
CANNOT: no changing what you exposed — once someone leans on a
  detail it is a promise, whether you meant it as one or not. No
  freedom left in a part that kept no secrets.
THREAD: shops (the price list is public, the supplier deal is
  not), medicine (the label states the dose, not the factory),
  craft (a guarantee covers what it says and no more).
ASKED-AS: interface promise inside hidden private public what others use secret details change freely

ESSENCE: every simplification holds in the middle and fails at
  the edges. Push on speed, size, timing, or failure and the
  machinery underneath shows through. The map was never wrong —
  it was only thinner than the ground.
ROOT: this file / a promise covers what it states; everything
  outside the promise is still real.
CANNOT: no abstraction that never leaks — the only layer that has
  never leaked is one nobody has pushed hard yet. No repairing
  from above a leak whose cause is below; you can only work
  around it, knowingly.
THREAD: maps (the road that turns out to be a track), driving
  (the pedal's promise breaks on ice), translation (it holds
  until the poem).
ASKED-AS: leak shows through breaks down edge cases pretend simple underneath pushes hard fails

ESSENCE: layering is a rule about who may call whom — each level
  speaks only to the one beneath it. That rule buys one thing,
  and it is the whole point: any level can be torn out and
  replaced, because nothing reached past it.
ROOT: building / the floor carries the wall, never the reverse.
CANNOT: no swapping a level that others reached around. No level
  that calls upward — a floor leaning on its own ceiling is not a
  floor, and the two are one thing pretending to be two.
THREAD: post (letter, van, road — none knows the others' work),
  armies (orders down a chain, not shouted across it), the body
  (skin, muscle, bone, each in its order).
ASKED-AS: layers levels floors stack above below swap replace only talks to next one

ESSENCE: dependencies point somewhere, and the direction decides
  what can be reused and what must die together. Point the
  changeable and specific at the stable and general — never the
  reverse, and never in a circle.
ROOT: building / what is underneath carries what is above, so it
  must not need it.
CANNOT: no separate life for two parts that depend on each other
  — a circle is one part with a seam drawn on it. No stable core
  that knows its own callers; the moment it does, it moves
  whenever they do.
THREAD: farming (the crop depends on the soil, never the soil on
  the crop), law (by-laws point at constitutions), teaching
  (arithmetic does not depend on the word problem).
ASKED-AS: depends on arrow points which way circle loop reuse stable core changes often

ESSENCE: instead of a part reaching out to fetch what it needs,
  it is handed what it needs and simply uses it. The caller
  chooses. Now the same part works with the real thing, a
  stand-in, or next year's replacement, untouched.
ROOT: this file / dependency direction — being handed a thing
  removes the arrow that pointed outward.
CANNOT: no testing a part that fetches its own world; you cannot
  give it a different world to be tested in. No swapping what a
  part hard-wired for itself without cutting the part open.
THREAD: cooking (a chef given ingredients versus one who must go
  shopping), theatre (props come from the stagehand), tools (a
  drill takes any bit because it holds none).
ASKED-AS: handed given passed in instead of fetching swap fake test plug in pieces

ESSENCE: a value that anything may read and anything may write
  makes every part a neighbour of every other. The variable costs
  nothing. The cost is that no piece of the program can ever
  again be understood, tested, or moved on its own.
ROOT: this file / coupling is the path change travels; a global
  is a path from everywhere to everywhere.
CANNOT: no answering "what is it now" for a global — the true
  answer is "whatever ran last", and everything ran. No unit
  small enough to test alone once a global runs through it.
THREAD: kitchens (one salt cellar everyone reseasons from),
  money (a joint account with no memo line), roads (one shared
  lane in both directions).
ASKED-AS: global shared variable everywhere anything can change it hard to test whatever ran last

ESSENCE: what happens when things go wrong is half the design,
  not a coat of paint at the end. Every call that can fail is a
  fork in the story, and somebody has to have written the failing
  branch before it is walked.
ROOT: this file / a promise must state what happens when it
  cannot be kept.
CANNOT: no bolting recovery onto a shape that assumed success —
  recovery needs facts the happy path never bothered to keep. No
  system more reliable than its worst-handled failure, however
  good the rest is.
THREAD: flight (the checklist is mostly what to do when something
  breaks), sailing (reefing is rehearsed in calm), hospitals
  (triage is designed before the crash, not during).
ASKED-AS: what if it fails errors handling design plan for failure not afterwards catch

ESSENCE: a fault caught at its birth names its own cause. The
  same fault swallowed and carried onward surfaces far away as
  nonsense, with the guilty line long out of sight. Loud and near
  beats quiet and later, every time.
ROOT: evidence / a signal is traceable only while it is still
  near its source.
CANNOT: no tracing a swallowed error back home — you arrive at
  the symptom and the trail is cold. No safety in continuing on a
  value you already know is wrong; every step after builds on it.
THREAD: medicine (pain that stops you saves the joint), factories
  (the line halts at the bad part, not at the loading bay), money
  (a wrong entry caught at the till, not at the audit).
ASKED-AS: crash loudly early stop right there hide swallow error surfaces later somewhere else

ESSENCE: check what comes in at the door, once, where the outside
  meets the inside. Past that line everything is known good, and
  no inner part has to ask again. Trust is a place with a wall,
  not a habit everyone tries to keep.
ROOT: this file / fail early; and law / evidence is admitted at
  the door, not weighed afterwards.
CANNOT: no trusted interior without a guarded door. No checking
  in the middle — by then you cannot tell what came from outside
  and what the program built itself, so you must suspect
  everything or nothing.
THREAD: the body (skin and gut wall do the filtering), buildings
  (one ticket gate, not a guard at every seat), farming
  (quarantine at the gate, not in the herd).
ASKED-AS: check input at the door edge outside data trust inside clean once bad

ESSENCE: an act is idempotent when doing it twice equals doing it
  once. Messages get lost, so senders try again, so receivers see
  doubles. Only acts that survive repetition survive a world that
  repeats things out of anxiety.
ROOT: this file / a network answer that never came is
  indistinguishable from work that never happened.
CANNOT: no safe retry of an act that stacks — "add ten pounds"
  twice is theft, "set it to fifty" twice is nothing. No delivery
  that is exactly once; you get at least once, and you make the
  extra times harmless.
THREAD: light switches (flip up twice, still up), medicine (a
  dose repeats badly, a splint does not), post (the same letter
  arriving twice should not double the order).
ASKED-AS: doing it twice same as once repeat retry again double charge safe harmless

ESSENCE: two workers touch one value with no agreed order, and
  the answer depends on who won by a hair. The program is right
  nearly always and wrong sometimes. The text looks correct
  because the fault lives in the timing, not the lines.
ROOT: causation / two causes on one effect need an ordering, and
  nothing supplies one by itself.
CANNOT: no seeing a race by reading the code — the fault is an
  ordering nobody wrote down. No test that proves it gone;
  passing is exactly what a race does most of the time.
THREAD: sport (two runners and one baton), traffic (an unmarked
  crossroads works until it does not), speech (two people
  starting the same sentence at once).
ASKED-AS: works most times fails randomly timing two at once who gets there first intermittent

ESSENCE: each holds what the other needs, and each waits politely
  forever. Nothing crashed, nothing reported an error, and every
  worker is behaving correctly. The system is simply stopped, and
  it will stay stopped.
ROOT: this file / shared things need turns, and a turn taken is a
  turn somebody else is waiting on.
CANNOT: no escape from the inside — none may release before
  finishing, and none may finish before the other releases. No
  deadlock at all where everyone takes what they need in one
  agreed order; that single rule kills it dead.
THREAD: doorways (two people each stepping aside forever), money
  (two firms each waiting for the other to pay first), law (two
  courts each awaiting the other's ruling).
ASKED-AS: stuck frozen waiting forever nothing moves each holds what the other needs hung

ESSENCE: one worker has one story. Two have every interleaving of
  two stories, and the count explodes with each hand added. The
  machine gets faster; the head that must hold all those stories
  does not get bigger.
ROOT: mathematics / combinations grow faster than the things
  combined.
CANNOT: no proving a concurrent design by running it — the run
  you did not get is the one that fails. No cheap concurrency:
  the speed is bought with reasoning, and the bill arrives at
  every future change.
THREAD: kitchens (two cooks, one stove, endless orders of
  operations), music (an orchestra needs a conductor because ears
  cannot), traffic (junction rules exist because heads cannot).
ASKED-AS: at once hard to think about orderings combinations too much to hold workers head

ESSENCE: a cache is a fast liar you invite in on purpose. It
  answers instantly with what was true, and nothing tells it when
  the world moved on. Its two hard problems: knowing when to
  throw the old answer out, and deciding when two questions count
  as the same question.
ROOT: computer science / a kept answer trades space for time;
  this file / naming is the hardest act, and a cache key is a
  name.
CANNOT: no cache without a story for going stale — "it refreshes
  eventually" is a story with a hole in it. No correct key that
  leaves out anything the answer depended on; leave one thing out
  and two different questions get one answer.
THREAD: news (yesterday's paper read as today), the mind (a first
  impression outliving the person), kitchens (a sauce prepped for
  a menu that has since changed).
ASKED-AS: old answer stale out of date wrong key same question refresh clear cached copy

ESSENCE: nearly all of a program's time hides in a tiny part of
  it, and nobody guesses which part correctly. Speeding up the
  rest buys nothing but complication — so watch where the time
  actually goes, and let the measurement pick the target.
ROOT: evidence / a guess and a measurement are not the same kind
  of thing, however confident the guesser.
CANNOT: no knowing where time goes without watching it go;
  intuition here is reliably, famously wrong. No honest claim of
  a speed-up without a before and an after measured the same way.
THREAD: medicine (test before treating), plumbing (the narrowest
  pipe sets the flow, and it is rarely the one you would replace),
  farming (fix the one poor field, not the whole farm).
ASKED-AS: slow where is the time going measure guess optimise faster before changing hotspot

ESSENCE: there are two levers on speed: the shape of the work as
  the job grows, and the size of each step. The first is worth
  thousands, the second a few percent — and yet at small sizes
  the plain method beats the clever one, and most work is small.
ROOT: computer science / cost grows with size in different
  shapes.
CANNOT: no buying your way out of a bad shape with fast hardware
  or tight code. No assuming the clever method wins either: below
  some size its setting-up costs more than its cleverness saves.
THREAD: travel (a better route beats a faster car, but not for
  crossing the road), farming (rotation beats a sharper hoe),
  books (the index beats reading faster, once the book is thick).
ASKED-AS: faster machine better method scale grows huge small lists clever plain choice speed

ESSENCE: every piece of memory has a beginning, an owner, and an
  end. Someone must give it back, exactly once, after everyone
  who was using it has finished. Most memory faults are arguments
  about that "after".
ROOT: craft / a borrowed thing has a lender and a return.
CANNOT: no memory without an owner — "everyone owns it" and
  "nobody owns it" both end in the same corpse. No use of a thing
  past its end; the address stays valid-looking long after the
  meaning there has gone.
THREAD: libraries (a borrowed book has a due date), tenancy (keys
  handed back when the lease ends), tools (the ladder returned to
  the shed, or lost to the world).
ASKED-AS: memory who owns it free release give back when finished still using gone

ESSENCE: a leak is memory taken and never returned. Nothing
  breaks today. The program serves an hour, a day, a week,
  swelling quietly, and then dies of something that looks nothing
  like the cause.
ROOT: this file / every allocation has an end, and a leak is an
  end that never comes.
CANNOT: no finding a leak in a short run — a leak is not an
  event, it is a slope, and a slope needs time to be visible. No
  leak at all in a program that ends soon; long life is what
  invents the fault.
THREAD: the body (slow swelling, not a wound), houses (clutter
  kept from every year), money (a small subscription nobody ever
  cancelled).
ASKED-AS: leak memory grows slowly restart every day eats ram runs out after hours

ESSENCE: a bug is a wrong line inside a right shape; a design
  fault is a right line inside a wrong shape. The first is fixed
  where you found it. The second keeps growing new bugs wherever
  you patch it, and each patch is correct.
ROOT: software development / a bug is the gap between intent and
  instruction — but a shape can be intended wrongly too.
CANNOT: no fixing a design fault at the site of a symptom; press
  it down here and it rises there. No meaningful count of
  remaining bugs while the shape is wrong, because the supply is
  being manufactured.
THREAD: medicine (a symptom versus a disease), building (a
  cracked tile versus a settling foundation), law (a typo in a
  statute versus a statute that should not exist).
ASKED-AS: keeps coming back patch again same problem elsewhere deeper wrong shape not typo

ESSENCE: a fault you cannot summon on purpose is a fault you
  cannot prove you fixed. Reproducing turns a story into an
  experiment: now one thing can be changed and the answer watched
  for a change.
ROOT: evidence / a claim becomes testable only when it can be
  made to happen again on demand.
CANNOT: no verified fix without a reliable reproduction — the
  best you can honestly say is "it has not happened lately". No
  reproduction without the same inputs and the same history,
  including the parts nobody thought to write down.
THREAD: mechanics (the noise the car will not make at the
  garage), medicine (a rash you can bring on is a rash you can
  treat), science (a result nobody can repeat is not yet a
  result).
ASKED-AS: make it happen again reproduce steps every time cannot repeat prove fixed test

ESSENCE: strip away everything that still leaves the fault
  standing. What remains is the fault and nothing else. Most bugs
  confess while you are stripping — the cause shows itself at the
  cut that finally makes it stop.
ROOT: this file / reproduction makes it an experiment; software
  development / halve the suspect ground and ask which half.
CANNOT: no understanding a fault buried in a thousand
  irrelevant lines; the noise is doing the hiding. No minimal
  case without a check at every cut that still says "failed" —
  otherwise you are not shrinking it, you are losing it.
THREAD: cooking (drop ingredients until the taste goes),
  medicine (an elimination diet), electricity (unplug everything,
  then add back one at a time).
ASKED-AS: smallest example cut away strip down until only the fault remains simple version

ESSENCE: every fault fixed should leave behind the test that
  would have caught it. That test is a scar — the system's memory
  of a pain it has already suffered, standing guard so the same
  wound cannot be opened twice.
ROOT: writing / memory outside the head survives the head, and
  survives the person leaving.
CANNOT: no lasting memory of past pain in people's heads alone —
  people leave, and the same mistake is fresh to whoever arrives.
  No confident change of old code without the scars in place;
  without them, courage is just luck.
THREAD: the body (immunity remembers the infection), sailing
  (charts marked where ships were lost), law (rules written the
  morning after each disaster).
ASKED-AS: same bug came back again test guard old fixes stays fixed check suite

ESSENCE: refactoring is changing the shape without changing what
  it does — the outside identical, the inside made workable
  again. It is the only way a program that is still being used
  stays a program anyone can still work in.
ROOT: this file / a promise is the outside; the shape inside is
  the secret, and secrets may be rebuilt.
CANNOT: no refactoring without a way to prove behaviour
  unchanged; without that it is rewriting and hoping. No doing it
  in the same breath as adding a feature — then a difference in
  behaviour cannot say which act caused it.
THREAD: houses (moving interior walls, same address), writing (a
  redraft that says the same thing better), music (rearranged,
  same tune).
ASKED-AS: tidy up rewrite inside same behaviour clean rearrange without breaking shape change safe

ESSENCE: a shortcut taken today is time borrowed from tomorrow,
  and the loan charges interest: every future change costs a
  little more because of it. Small debts, taken knowingly, are
  ordinary and useful. Unnamed debt compounds until all the
  effort goes on servicing it.
ROOT: money / interest compounds, and compounding is quiet at
  first.
CANNOT: no debt-free system built at speed — the choice is only
  which debt, taken knowingly, repaid when. No repaying a debt
  nobody wrote down; an unrecorded shortcut is never found again,
  it is only suffered.
THREAD: money (the loan itself), houses (the roof repair deferred
  another year, then another), the body (sleep borrowed back with
  interest).
ASKED-AS: shortcut quick fix later cleanup mess piles up harder every time borrowed cost

ESSENCE: complexity bought for speed is paid at once and forever,
  while the speed itself is only a guess about which part will
  matter. Make it work, make it right, and then make fast the one
  place the measurement condemned.
ROOT: this file / almost all the time hides in a tiny part, and
  nobody guesses which part.
CANNOT: no undoing complexity once other things lean on it — the
  clever version becomes load-bearing long before it is proved
  necessary. No speed worth having in code that is not yet
  correct; fast and wrong is only wrong sooner.
THREAD: building (fitting a house to a road that was never laid),
  farming (irrigating a field before knowing the crop), packing
  (gear carried for a trip that went another way).
ASKED-AS: make it fast first correct later worth optimising early complexity speed guess unnecessary

ESSENCE: writing code takes less of you than working out why it
  misbehaves. Write at the very edge of your cleverness and you
  have, by your own arithmetic, nothing left over for the day it
  goes wrong.
ROOT: the mind / untangling costs more than tangling.
CANNOT: no debugging a piece harder than the head that wrote it —
  the author is the strongest reader it will ever have, and the
  author is already spent. No long life for what one person
  understood on one good day.
THREAD: climbing (never go up what you cannot come down), knots
  (the one nobody can untie is not a good knot), writing (a
  sentence too dense to edit).
ASKED-AS: too clever tricky code hard to follow smart one liner debug later headroom

ESSENCE: the code already says what it does. A comment earns its
  keep by saying why — the reason, the option rejected, the
  strange outside rule that forced this shape. Anything else is a
  second copy that quietly rots out of step.
ROOT: this file / duplicated knowledge drifts apart, and nothing
  warns you.
CANNOT: no comment restating the code that stays true — the code
  moves, the sentence does not, and the reader believes the
  sentence. No recovering a reason that was never written; it
  lived in one head, and heads leave.
THREAD: maps (a note that the ford floods in spring), medicine
  (notes recording why this treatment, not that one), law (the
  record behind the words).
ASKED-AS: comments explain why not what obvious outdated notes helpful useless restate the line

ESSENCE: two things that look alike today may be alike by
  accident. Join them early and every later difference must be
  forced through one shape with flags and exceptions. Two honest
  copies cost less than one dishonest sharing.
ROOT: this file / cohesion is about what truly belongs together,
  which is not the same as what currently resembles.
CANNOT: no cheap un-joining of a bad shared piece — by then both
  callers depend on its compromises. No knowing whether two
  things are one thing until both have changed a few times.
THREAD: tailoring (one pattern forced onto two bodies), law (one
  statute stretched over unlike cases), cooking (one sauce base
  that keeps needing exceptions).
ASKED-AS: copy paste twice share common code too early forced together similar not same

ESSENCE: the dangerous duplication is not repeated text but
  repeated knowledge — one rule, one number, one meaning living
  in two places. They get changed one at a time, and then the
  system believes two things at once.
ROOT: this file / a fact with two homes has no home; law / one
  register of record.
CANNOT: no keeping two copies of a rule in step by good intention
  alone. No finding the second copy when it matters; nothing
  points from one to the other, which is exactly why it was
  missed the first time.
THREAD: records (one address book, not five), building (one
  measurement everyone works from), music (parts copied from one
  score, never edited apart).
ASKED-AS: same rule written twice two places update both forgot one fact lives where

ESSENCE: building for a future you imagine costs today's time,
  today's complexity, and tomorrow's wrong guess. The general
  version built before the second real case arrives is almost
  always general in the wrong direction.
ROOT: software development / every added piece must pay rent, and
  an unused piece pays none.
CANNOT: no knowing the shape of a second case before it exists —
  one example cannot define a family. No free option either: the
  flexibility is carried, tested and explained forever, used or
  not.
THREAD: building (rooms for children never had), packing (the
  just-in-case kit that becomes the heaviest bag), farming (a
  barn sized for a herd that never came).
ASKED-AS: might need it later future proof flexible extra options never used guess wrong

ESSENCE: code nobody runs is still read, still searched, still
  believed, and still edited by mistake. It costs everything live
  code costs and returns nothing. Delete it — the history keeps
  it if it is ever wanted again.
ROOT: software development / every change is kept with its
  history, so deleting loses nothing.
CANNOT: no harmless unused code in a system people must read; a
  reader cannot tell it is dead without doing the work of proving
  it. No trusting kept-just-in-case code when the day comes — it
  has not been run or tested in years.
THREAD: gardens (dead wood cut out so the tree can be read),
  maps (a road drawn that no longer exists), houses (the box kept
  unopened for a decade).
ASKED-AS: unused old code delete remove commented out just in case never called clutter

ESSENCE: one ordinary style used everywhere is read faster than a
  collection of individually better styles. Surprise spends
  attention, and attention is the scarce thing in the room. Do
  the boring thing the house already does.
ROOT: teaching / a familiar form frees the mind to take in the
  content.
CANNOT: no fluent reading of a place with a new convention in
  every corner. No local improvement worth the break in pattern
  unless it is carried everywhere; half-applied, it is simply one
  more dialect.
THREAD: roads (a sign means the same in every town), music
  (notation is not reinvented per piece), kitchens (every branch
  keeps the knives in the same drawer).
ASKED-AS: style same way everywhere different habits mixed conventions surprising odd corner house rules

ESSENCE: the strongest check is a shape that cannot say the wrong
  thing. If two things must never both be filled in, make them
  one thing with two forms — then no check is needed, none can be
  forgotten, and no future writer can drift from it.
ROOT: this file / validation at the boundary, carried further:
  build the door so the bad thing does not fit through it.
CANNOT: no forgetting a rule the shape itself enforces. No safety
  in relying on every writer, present and future, to remember a
  rule the shape still lets them break.
THREAD: engineering (a plug that fits only one way), machines (an
  interlock that will not let the guard open while the blade
  turns), law (a form that cannot be signed incomplete).
ASKED-AS: impossible by shape cannot even say it wrong combination prevented not checked design

ESSENCE: "there is nothing here" is a real answer that needs a
  shape of its own. The classic wound is a program that assumed
  something would always be there, met nothing, and fell over
  somewhere far from the assumption.
ROOT: logic / absence is a case in the world, not a malfunction
  in it.
CANNOT: no answer about a thing that is not there. No silent
  stand-in for missing, either — a zero or a blank put where
  "unknown" belongs turns an open question into a confident wrong
  fact.
THREAD: records (a blank field means unasked, not zero), medicine
  (no result is not a normal result), shops (out of stock is an
  answer, not a price of nothing).
ASKED-AS: nothing there missing blank none not found no value crashes on absent unset

ESSENCE: everything opened must be closed — files, connections,
  locks, handles — and the closing has to happen on the path
  where something went wrong, which is precisely the path nobody
  rehearses.
ROOT: this file / every resource has an owner and an end; and
  every failure is a fork in the story that someone must write.
CANNOT: no release that runs only when all goes well; failure is
  when release matters most. No long life for a program with a
  slow drip of unclosed things — the limit is simply further away
  than the fault.
THREAD: sailing (gear secured before the weather, not after),
  kitchens (the gas turned off even when the dish is ruined),
  libraries (the book returned even unread).
ASKED-AS: opened file must close release handle connection left hanging even when something fails

ESSENCE: anything that can grow without a limit eventually
  reaches one — a list, a queue, a retry, a log file, a
  recursion. The fuse is long and burns quietly under a program
  that looks perfectly well.
ROOT: physics / no store is infinite, so unbounded growth always
  meets a wall it did not plan for.
CANNOT: no unbounded thing that is safe — only ones that have not
  filled yet. No graceful behaviour at a limit nobody named; an
  unplanned limit arrives as a crash, never as a polite refusal.
THREAD: farming (a herd never culled outgrows the land), houses
  (a loft that never had a clear-out), roads (a car park with no
  count, full at the worst hour).
ASKED-AS: no limit grows forever list queue retries fills up eventually eats everything cap

ESSENCE: the clock, the random source, the network and the
  machine's own settings are inputs even when nobody names them.
  Reach out for them from inside and the piece answers
  differently on every run, and no test can pin it down.
ROOT: this file / what is handed in can be chosen; what a part
  fetches for itself cannot.
CANNOT: no repeatable run with an unnamed input. No testing what
  happens at midnight on the last day of February inside code
  that asks the world what time it is.
THREAD: science (an experiment must state every condition),
  cooking (a recipe that depends on the weather has to say so),
  sport (a fair race measures the wind).
ASKED-AS: works differently each run random clock time zone depends on today hard test

ESSENCE: faults gather at the edges — zero, one, empty, full,
  first, last, and the moment a count rolls over. The middle of a
  range is where the code is right, because the middle is what
  the author pictured. The ends are where the thinking ran out.
ROOT: mathematics / a rule stated for the general case says least
  about its own extremes.
CANNOT: no confidence from testing the middle alone. No fence
  built right without counting posts and gaps separately; they
  are never the same number, and that gap is a whole family of
  faults.
THREAD: building (corners and joints fail, not walls), sewing
  (hems and seams give first), medicine (the very young and the
  very old break the dosing rule).
ASKED-AS: off by one first last empty zero edge case boundary counting fence posts

ESSENCE: a loop is a promise that holds at every turn plus
  something that moves toward an end. A recursion is the same
  bargain: a smaller problem each time, and a case small enough
  to answer outright. Break either half and it never stops.
ROOT: mathematics / induction — a truth kept at each step, and a
  ground floor to stand on.
CANNOT: no loop that ends without something changing toward its
  ending. No recursion without a case answered outright; with no
  floor it falls until the machine stops it.
THREAD: stairs (each step alike, and a landing), directions (walk
  until the church, or walk forever), stories (a tale within a
  tale needs an innermost one).
ASKED-AS: loop repeats forever recursion base case stops something true every time round infinite

ESSENCE: choose how the facts are arranged and most of the code
  writes itself; choose badly and every piece spends its life
  translating. Show someone the data and they can very nearly
  guess the program.
ROOT: computer science / how facts are arranged decides how they
  are found.
CANNOT: no clean code over a bad arrangement — the mess has to
  live somewhere, and it lives in every reader. No fixing that by
  effort in the code; the repair is upstream, in the shape.
THREAD: kitchens (the layout decides the movements), libraries
  (shelving decides the searching), building (the plan decides
  the plumbing).
ASKED-AS: how data is laid out decides the code shape structure first awkward fits

ESSENCE: debugging is not staring, it is asking. Say plainly what
  you believe is happening, find the cheapest thing that would be
  false if you were wrong, and check that one thing. Believe,
  test, cut, repeat.
ROOT: evidence / a belief that forbids nothing cannot be checked.
CANNOT: no learning from changing five things at once — when it
  works, you know nothing about why. No hypothesis worth the time
  if every possible outcome would confirm it.
THREAD: medicine (diagnosis by ruling out), mechanics (swap one
  part, not five), science (the experiment that could have gone
  the other way).
ASKED-AS: guess and check hypothesis one change at a time staring at code experiment

ESSENCE: if it worked before, something changed between then and
  now, and the fault has a birthday. The history is a list of
  suspects in order — and halving that list finds the guilty
  change far faster than reading the code ever will.
ROOT: software development / every change kept with its history;
  halving finds anything, given a test that says which half.
CANNOT: no birthday found without a reliable way to say "broken
  or not" at each point you try. No such search through work kept
  as one enormous change; big steps hide their own culprits.
THREAD: medicine (what changed in the diet), farming (which
  season the field turned), households (the bill that started
  climbing in March).
ASKED-AS: it worked before what changed which version broke it history search last good

ESSENCE: an error message is read by a stranger at their worst
  moment. It should say what was expected, what was found
  instead, and where — those three sentences are the whole
  difference between a minute and a day.
ROOT: this file / failure is part of the design, and the message
  is the part a person actually meets.
CANNOT: no diagnosis from a message that only says something went
  wrong. No use in one that names the failing line but not the
  value that broke it — the code was already visible; the data
  was not.
THREAD: medicine (a useful referral names the findings), law (a
  refusal must state its grounds), teaching (a mark with reasons
  teaches; a score alone does not).
ASKED-AS: unhelpful message expected got where line number confusing error text says nothing

ESSENCE: when a piece is hard to test, the difficulty is almost
  never in the testing. It is the shape saying it needs too much
  world, does too many things, or hides its inputs. The test is
  the first customer, complaining early and cheaply.
ROOT: this file / a part that is handed its world can be given
  any world, including a small one.
CANNOT: no easy test for a piece tangled into everything — the
  test must rebuild the tangle first. No ignoring that signal
  cheaply: whatever makes a thing hard to test makes it hard to
  change.
THREAD: engineering (a part that cannot be bench-tested cannot be
  serviced), craft (a joint you cannot inspect is a joint you
  cannot trust), medicine (a symptom that resists measurement
  resists treatment).
ASKED-AS: hard to test awkward setup mocks everywhere shape problem design smell untestable
