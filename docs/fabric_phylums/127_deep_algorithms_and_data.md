# 127 DEEP ALGORITHMS AND DATA — the shapes work takes
Every arrangement of facts is fast at some questions and hopeless at
others, and the choosing happens before a line is written. This file
is the catalogue of those shapes, the methods that walk them, and the
handful of facts — time, text, money — that ruin programs quietly.

ESSENCE: an array is a row of boxes side by side, so the ten
  thousandth is reached instantly and inserting in the middle means
  shifting everything after it. A linked list is the exact opposite:
  insert anywhere for nothing, and there is no way to the tenth but
  walking nine.
ROOT: computer science / arrangement is work stored in advance, and
  these two store opposite work.
THREAD: seating (a fixed row of numbered chairs against a queue people
  join anywhere), books (a bound volume against loose cards), trains
  (carriages coupled in order against a numbered platform).
ASKED-AS: array list which one insert middle slow index jump linked nodes shifting

ESSENCE: the row of boxes wins far more often than the arithmetic
  says, because the machine fetches whole neighbourhoods at a time.
  A chain of links scattered through memory pays a journey per step,
  and a hundred cheap steps lose to ten expensive ones.
ROOT: computing foundations / neighbours are free and strangers are
  expensive, so the layout can beat the method.
THREAD: shopping (one trip with a full basket), farming (walking the
  row rather than the field at random), libraries (a shelf against a
  slip that sends you to another floor each time).
ASKED-AS: array faster in practice pointer chasing scattered memory cache friendly layout wins

ESSENCE: a growable row solves the fixed-size problem by doubling:
  when it is full it takes a new home twice the size and moves
  everything. That copy sounds ruinous and is not — because it
  happens half as often each time it happens.
ROOT: mathematics / a cost that halves in frequency as it doubles in
  size adds up to a constant per item.
THREAD: houses (moving to a bigger one rather than adding a shelf
  every month), herds (a barn built for the next doubling), luggage
  (repacking once rather than restitching daily).
ASKED-AS: array grows resize doubling copy everything append cheap amortised capacity reserve

ESSENCE: a hash table gives up order entirely and buys near-instant
  finding with the proceeds. Turn the key into a number, go straight
  to that spot. No searching, no comparing, no walking — and no way
  ever to ask what comes next.
ROOT: mathematics / a fixed recipe can turn any key into a position,
  and a position is reached without looking.
THREAD: cloakrooms (a numbered ticket goes straight to the peg),
  post (a box number rather than a name to look up), warehouses (bins
  addressed by code, not arranged by kind).
ASKED-AS: hash map dictionary instant lookup by key unordered no sorting bucket table

ESSENCE: two keys can land in the same spot, and every hash table is
  really a plan for what to do then. That plan is fine while the
  table is roomy and honest — and it collapses if somebody is allowed
  to choose keys that all land together on purpose.
ROOT: mathematics / more possible keys than positions means
  collisions are certain, not unlucky.
THREAD: names (two families in one village sharing a surname), post
  (one box shared by a whole building), seating (double-booked seats
  and the usher's rule for sorting it out).
ASKED-AS: hash collision same bucket slow suddenly attacker chosen keys randomised seed load

ESSENCE: a search tree keeps order as it goes, so it can answer what
  a hash table cannot — the next key, everything between two dates,
  the smallest remaining. It pays for that with a walk down instead
  of a jump straight in.
ROOT: computer science / arrangement decides what can be found, and
  order is an arrangement with different powers.
THREAD: libraries (shelved by subject so the neighbours are relevant),
  dictionaries (open near the word, then walk), filing (folders in
  date order so a span can be pulled at once).
ASKED-AS: sorted tree range query between two values next key ordered walk down

ESSENCE: a tree's speed comes entirely from being short and bushy.
  Feed it already-sorted data and each item lands to the right of the
  last, so it grows into a single long chain — a list wearing a
  tree's name, and every lookup walks the lot.
ROOT: mathematics / halving reaches one from a million in twenty
  steps, but only if each step really halves.
THREAD: management (a chain of command one person wide), families (a
  line rather than a spread), roads (one long lane instead of a
  branching network).
ASKED-AS: tree unbalanced degenerates sorted input slow linear rebalance rotation self balancing

ESSENCE: a heap does not sort anything. It keeps one promise only —
  the smallest is on top — and that is all a queue by priority ever
  needs. Keeping that one promise is far cheaper than keeping the
  whole order, which is why it is used everywhere urgency matters.
ROOT: this file / buy only the arrangement your questions require, and
  order is more than most questions require.
THREAD: hospitals (triage names the next patient, not the full
  ranking), airports (the next flight to leave, not the day's
  running order), kitchens (the next ticket, not the evening sorted).
ASKED-AS: priority queue next most urgent heap top smallest not fully sorted scheduling

ESSENCE: a stack serves the newest first and a queue serves the
  oldest, and swapping one for the other silently converts a search
  that goes deep into one that goes wide. Same code, same graph,
  entirely different answer arriving in an entirely different order.
ROOT: causation / what is taken next decides what is discovered next,
  and discovery order is the shape of a search.
THREAD: exploring (following one corridor to its end against sweeping
  room by room), reading (chasing every footnote against finishing the
  chapter), queues (first come first served against last in first out).
ASKED-AS: stack queue depth first breadth first search order shortest explore frontier

ESSENCE: a graph is things and the connections between them, and
  almost every real body of facts turns out to be one — people and
  their contacts, roads and junctions, tasks and what they wait on,
  pages and their links. Trees and lists are graphs that were tidy.
ROOT: mathematics / a relation between pairs is the most general
  arrangement there is, so everything else is a special case of it.
THREAD: families (a tree until cousins marry), roads (a map is
  junctions and the roads between them), rumour (who told whom).
ASKED-AS: graph nodes edges network connections relationships between things follow links friends

ESSENCE: a traversal answers a small, exact set of questions: what
  can be reached from here, how many steps away, are there loops, and
  which parts are cut off from which. Nothing else. Everything harder
  is built out of repeating those.
ROOT: this file / a search discovers by following, so it can only
  report what following reveals.
THREAD: exploring (a cave surveyed by walking it), plumbing (tracing
  which taps a valve feeds), epidemics (contact tracing outward from
  one case).
ASKED-AS: reachable from here connected components how many steps cycle detect visit all

ESSENCE: once the connections carry weights — minutes, pounds, miles —
  step-counting stops working and you need a method that always
  extends the cheapest frontier so far. And a single negative weight
  breaks it, because a route can now improve after you thought it was
  settled.
ROOT: this file / greed is safe only where a step once taken is never
  regretted, and negative weights are exactly regret.
THREAD: travel (the fast road that is longer in miles), shipping
  (routes priced in fuel, not distance), money (a route with a rebate
  on it, taken round and round).
ASKED-AS: shortest path weights distance cheapest route negative edge dijkstra map directions

ESSENCE: some jobs must come before others, and a valid order exists
  only if nothing waits, however indirectly, on itself. When the
  method fails to produce an order it has proved something useful:
  there is a cycle, and it can name it.
ROOT: logic / a strict before-and-after cannot close into a ring
  without contradicting itself.
THREAD: building (foundations before walls), cooking (a sauce reduced
  before it is poured), study (the chapter that assumes the one that
  assumes it).
ASKED-AS: order of tasks dependencies circular cycle build order what comes first schedule

ESSENCE: there are two families. One compares items to each other,
  and no such method can beat a certain speed — that is proved, not
  merely unbeaten. The other looks inside the keys, digit by digit,
  and goes faster by assuming something about what keys are.
ROOT: mathematics / with only yes-or-no comparisons available, there
  is a floor on how few questions can distinguish every ordering.
THREAD: post (sorting by postcode digit against comparing addresses),
  cards (dealing into piles by suit against pairwise ordering),
  libraries (shelf marks against reading every spine).
ASKED-AS: sorting fastest comparison based radix bucket lower bound n log n

ESSENCE: no sort wins everywhere. The plain insertion method beats
  everything on tiny or nearly-ordered data; merging is steady, keeps
  equal items in place and works on data too big for memory; the
  quick method is fastest in practice and worst on the wrong input.
  Real libraries switch between them mid-run.
ROOT: this file / every arrangement is bought, and which purchase is
  worth it depends on the size and the starting state.
THREAD: cooking (a method per quantity — one steak, twenty, two
  hundred), transport (walk, bus, or freight, by distance), tools
  (a hand plane, a router, a mill).
ASKED-AS: quicksort mergesort insertion which sort small nearly sorted stable worst case

ESSENCE: a stable sort leaves items that compare equal in the order
  they were already in. It sounds like nothing until you sort by date
  and then by name, and expect each name's rows still in date order —
  which only happens if the second sort was stable.
ROOT: this file / sorting is a rearrangement, and what it does to
  ties is part of what it does.
THREAD: records (a filing system that preserves arrival order within
  a category), sport (tie-break rules stated in advance), queues
  (people served in the order they joined, within a priority).
ASKED-AS: stable sort ties equal items order preserved sort twice by two columns

ESSENCE: binary search halves the ground each guess and finds
  anything in a handful of steps — on one condition. The data must
  already be in order. Run it on unsorted data and it does not run
  slowly; it returns a confident wrong answer.
ROOT: mathematics / halving works because each comparison rules out a
  whole side, and it rules out nothing if the sides mean nothing.
THREAD: dictionaries (useless if the words were shuffled), guessing
  games (higher or lower needs a real ordering), medicine (a test
  whose reading assumes a condition nobody checked).
ASKED-AS: binary search must be sorted first wrong answer not found halving precondition

ESSENCE: sorting is rarely the goal and usually the enabler. Once
  data is in order, searching is halving, duplicates are neighbours,
  grouping is a single pass, and two ordered sets can be merged,
  compared or differenced by walking them side by side once.
ROOT: computer science / arrangement is work stored in advance, and
  order is the arrangement that most later questions want.
THREAD: stocktaking (count once in order rather than hunt per item),
  post (sorted sacks make delivery a walk), music (a catalogue in
  order makes gaps visible).
ASKED-AS: sort first then everything easier duplicates adjacent merge compare group scan

ESSENCE: split the problem into pieces, solve each the same way, and
  join the answers. Which of the three steps is heaviest decides
  everything — a cheap split and cheap join give a fast method, and an
  expensive join can eat the whole gain.
ROOT: mathematics / a problem defined in terms of smaller copies of
  itself has a cost defined the same way.
THREAD: building (a wall built in sections and joined), cooking (two
  pans and one plating), surveying (a region mapped in tiles that must
  then agree at the edges).
ASKED-AS: divide conquer split in half combine recursive break down merge results

ESSENCE: a greedy method takes the best-looking step available and
  never looks back. It is astonishingly effective and provably right
  only when the problem has a particular property: that a step which
  looks best now can never turn out to be the one you regret.
ROOT: mathematics / where local best and global best coincide by
  structure, no search is needed at all.
THREAD: travel (always taking the widest road), money (spending the
  largest note first), farming (planting the best field first and
  finding the machinery cannot reach the rest).
ASKED-AS: greedy best step now optimal proof works usually not always suboptimal

ESSENCE: the classic failure: making change from coins of one, three
  and four, greedily, for six. Take the four, then two ones — three
  coins, when two threes would have done. Nothing in the run reports
  anything wrong.
ROOT: this file / a greedy method is right by structure or not at all,
  and this structure fails.
THREAD: shopping (the biggest discount taken first losing the bundle
  deal), chess (the free pawn), hiring (filling the loudest vacancy
  first and leaving the team unbalanced).
ASKED-AS: coin change greedy fails wrong coins denominations counterexample suboptimal answer looks fine

ESSENCE: the same small problem gets solved again and again inside a
  big one — the naive way of counting rabbit pairs recomputes the
  same number millions of times. Write each answer down the first
  time and the whole thing collapses from impossible to a table.
ROOT: computer science / a kept answer trades space for time, aimed at
  a computation that repeats itself.
THREAD: accounting (a running total rather than re-adding the column),
  building (a cut list worked out once), navigation (distances between
  towns tabulated once and read forever).
ASKED-AS: dynamic programming memoise remember subproblems exponential to table repeated recompute overlapping

ESSENCE: the method only works if the best answer to the whole is
  built from best answers to the parts. Shortest routes have that
  property, so route-finding falls to it. Longest simple routes do
  not, and no amount of table-building will make them.
ROOT: logic / a claim about the whole may be assembled from claims
  about the parts only when nothing in the assembly can undo them.
THREAD: travel (the cheapest first leg is not always in the cheapest
  journey), building (the strongest single joint is not the strongest
  frame), diet (the best meal is not part of the best week).
ASKED-AS: optimal substructure why dp works longest path fails cannot combine best parts

ESSENCE: two ways to build the same table. Start at the top and
  remember answers as you fall into them, and only what is needed is
  computed. Start at the bottom and fill everything in order, and you
  gain speed, lose the recursion, and compute cells you never wanted.
ROOT: this file / a remembered answer can be filled on demand or in
  advance, and that is the same early-or-late choice as everywhere
  else.
THREAD: cooking (prepping everything against fetching as needed),
  study (reading the whole textbook against looking things up),
  stock (a full warehouse against ordering on demand).
ASKED-AS: top down bottom up memoisation table filling order recursion iterative dp

ESSENCE: try a choice, go on, and when it leads nowhere, undo it
  exactly and try the next. It is a full search that never holds the
  whole space in memory — only the current path and the choices still
  open along it.
ROOT: this file / a search must remember where it is, and a path is
  the smallest thing that says where it is.
THREAD: mazes (a hand on one wall and a retreat at each dead end),
  crosswords (a pencilled word rubbed out), locks (trying keys and
  putting each back).
ASKED-AS: backtracking try undo dead end all possibilities search recursion sudoku maze

ESSENCE: what makes a full search finish is not the trying, it is the
  abandoning. Prove a whole branch cannot contain an answer and you
  delete millions of futures with one test — which is why the cheap
  check that kills a branch early is worth more than any speed-up
  inside it.
ROOT: mathematics / a space that branches grows by multiplication, so
  a cut near the root removes a product, not a sum.
THREAD: hiring (a first filter that removes most applications),
  medicine (one test that rules out a whole family of disease),
  searching (calling off a wing of the building rather than sweeping
  faster).
ASKED-AS: pruning cut branch early impossible skip constraint propagation search space explosion

ESSENCE: recursion runs on a stack, and that stack is small — a few
  thousand frames, not a few million. A method that recurses once per
  item works beautifully on the test data and dies on a real file,
  far from the line that was actually wrong.
ROOT: computing foundations / a fixed store holds a fixed count, and
  the call stack is a very fixed store.
THREAD: ladders (a height limit set by the ladder, not the wall),
  paperwork (an appeal chain with a fixed number of levels), memory
  (a story within a story within a story, lost).
ASKED-AS: stack overflow deep recursion too many levels nested input crash depth limit

ESSENCE: the plain way to say what a method costs is to ask what
  happens when the data doubles. The same time. A little more. Twice.
  A bit over twice. Four times. Squared. Or the whole thing again for
  every extra item, which is the wall.
ROOT: mathematics / growth is a shape, and the shape is what survives
  as the numbers get large.
THREAD: farming (weeds double, rows only add), crowds (handshakes
  grow as pairs), post (one more town on a route against one more
  town connected to every other).
ASKED-AS: how slow when data doubles big o quadratic exponential linear growth scaling

ESSENCE: most methods have a common case and a rare terrible one.
  The quick sort's disaster, the hash table's pile-up: rare with
  ordinary data, and reachable on purpose. A system serving strangers
  is judged on its worst case, because a stranger will find it.
ROOT: chance / an average describes a population and says nothing
  about which member you are about to meet.
THREAD: bridges (rated for the heaviest lorry, not the average one),
  medicine (a treatment safe on average and fatal for one group),
  insurance (the rare claim is the whole business).
ASKED-AS: average case worst case usually fast sometimes terrible adversary chosen input attack

ESSENCE: some costs are rare and large but spread thin: a table that
  doubles occasionally, a list that compacts now and then. Averaged
  over all the operations the cost is small and honest — and any one
  unlucky operation still takes the whole hit, all at once.
ROOT: mathematics / a total divided over the acts that caused it is a
  fair account of throughput and a false account of any single act.
THREAD: money (an annual bill spread over months, still due in one
  lump), maintenance (a roof replaced once in thirty years), farming
  (a fallow year averaged into the yield).
ASKED-AS: amortised average over many operations occasional slow one spike latency throughput

ESSENCE: the shape hides a multiplier, and at real sizes the
  multiplier often decides. A method with a better shape and a heavy
  setup loses to a simple one until the data is large — which is why
  serious libraries use the clever method above a threshold and the
  plain one below it.
ROOT: mathematics / a comparison of growth rates is a claim about
  large numbers, and most real data is not large.
THREAD: transport (a plane beats a car, but not to the next village),
  cooking (a machine that must be cleaned beats a knife only past a
  quantity), tools (setting up a jig for two cuts).
ASKED-AS: constant factor hidden small inputs simple beats clever threshold switch over overhead

ESSENCE: an answer can be worked out each time it is asked, or worked
  out once and kept. The whole decision is a count: how many times
  will it be asked before the underlying facts change? Below that
  number the table is waste, and above it the recomputation is.
ROOT: computer science / a kept answer trades space for time — this
  is the arithmetic that decides which side to be on.
THREAD: cooking (a batch frozen against a dish made to order),
  reference (a printed table against working it out), tools (a jig
  built for a run of one).
ASKED-AS: precompute versus calculate each time worth caching how often asked table waste

ESSENCE: count the passes over the data, not the operations. A method
  that does twice the arithmetic in one sweep beats one that does half
  as much in three, because moving the data is the expensive part and
  arithmetic is nearly free.
ROOT: computing foundations / distance costs time and the processor
  spends much of its life waiting on memory.
THREAD: farming (one pass with a combine against three with separate
  machines), cleaning (one trip round the house with the whole
  basket), post (one round with all the letters).
ASKED-AS: one pass multiple passes over data memory bound arithmetic cheap sweeps fusion

ESSENCE: some methods rearrange the data where it lies and some need
  a second copy of everything. On a small list nobody notices. On
  something that fills most of the machine, needing a second copy is
  not slower — it is the difference between working and not.
ROOT: physics / a store is finite, so any method needing as much
  again has a size beyond which it simply cannot run.
THREAD: rooms (rearranging furniture against emptying into a second
  room), building (repairing a bridge in traffic against building a
  new one alongside), cooking (a bowl you must keep against tipping
  and rinsing).
ASKED-AS: in place extra memory copy of everything doubles ram sorting large file

ESSENCE: when the data will not fit, everything changes. One pass,
  bounded memory, no going back — and a whole family of methods
  becomes unavailable, because they all assumed they could look at
  something twice.
ROOT: physics / what does not fit cannot be held, so it must be
  consumed as it goes by.
THREAD: rivers (measured as they flow, never dammed), broadcasting
  (heard once), post (a sorting office that must clear each night).
ASKED-AS: too big for memory streaming one pass cannot fit process as it arrives

ESSENCE: a single pass with small memory can honestly give you a
  count, a total, a maximum, and anything built from those. It cannot
  give you a median, an exact count of distinct values, or any answer
  that needs to compare each item with all the others.
ROOT: this file / a method can report only what it kept, and one pass
  with small memory keeps very little.
THREAD: crowds (counting people at a gate against knowing the median
  age), weather (a running maximum is easy, a typical day is not),
  shops (takings are a total, the middle basket is not).
ASKED-AS: median from stream distinct count exact impossible running total max approximate

ESSENCE: a well-drawn sample of a thousand tells you almost as much
  about a million as about a billion. The honesty lives entirely in
  how it was drawn, not in how big it is — a huge sample drawn badly
  is a confident wrong answer.
ROOT: chance / a random draw carries the population's shape, and a
  chosen draw carries the chooser's.
THREAD: cooking (one spoonful from a stirred pot, none from an
  unstirred one), medicine (volunteers are not the population),
  farming (soil tested from a scatter of points, not from the gate).
ASKED-AS: sample subset representative random bias big enough estimate whole from part

ESSENCE: to keep a fair handful from a stream whose length nobody
  knows, keep the first ones, and let each later arrival replace one
  at random with a falling chance. At every moment what you hold is a
  fair sample of everything seen so far.
ROOT: chance / a probability that falls exactly as the population
  grows keeps every member equally likely, from first to last.
THREAD: raffles (a ticket whose odds hold however many enter later),
  logs (keeping a fair hundred lines from a flood), fishing (a catch
  that represents the day, not the first hour).
ASKED-AS: sample from stream unknown length fair reservoir replace random keep hundred

ESSENCE: for many questions an answer within one percent costs a
  thousandth of the exact one. That is not sloppiness — it is a
  purchase, and the discipline is stating what you bought: how wrong
  it can be, and how often.
ROOT: measurement / a number without a stated error is not a
  measurement, and an approximation without one is not an answer.
THREAD: surveying (a fix good to a metre, stated), engineering (a
  tolerance on every dimension), cooking (a pinch, where a pinch is
  known to be enough).
ASKED-AS: approximate good enough close estimate error bound how wrong tolerance exact expensive

ESSENCE: some structures are allowed to be wrong in one direction
  only. A membership filter says either "definitely not here" or
  "probably here" — never a false no. That one-sidedness is what makes
  it safe: you use the cheap answer to skip work, and check the rest.
ROOT: logic / an error that can only go one way can be corrected
  downstream, and an error that goes both ways cannot.
THREAD: medicine (a screening test that never misses and often alarms),
  security (a check that may stop the innocent but never passes the
  guilty), post (a sorting rule that may over-include a bag, never
  under-include).
ASKED-AS: bloom filter maybe present definitely not false positive never negative skip lookup

ESSENCE: making a choice at random removes the adversary's ability to
  choose your worst case. The bad input still exists; it just cannot
  be aimed at you, because you do not decide the same way twice.
ROOT: strategy / a predictable defence is a defence the opponent
  plans around, and unpredictability is the cheapest counter.
THREAD: sport (mixing your serve so it cannot be read), security (a
  patrol on no schedule), games (a bluff that only works if it is
  genuinely uncertain).
ASKED-AS: random pivot shuffle unpredictable avoid worst case attacker cannot aim seed

ESSENCE: one word covers three different jobs. Spreading keys across
  a table wants speed and evenness. Identifying content wants it to
  be impossible to forge a match. Both are called hashing, and using
  the fast one where the strong one belongs is a whole class of
  breach.
ROOT: mathematics / a many-to-few mapping can be easy, even, and
  forgeable, or slow, even, and infeasible to forge — not both.
THREAD: locks (a latch that keeps a door shut against one that
  resists a thief), seals (a wax blob against a tamper-evident band),
  signatures (an initial against a witnessed one).
ASKED-AS: hash function which one md5 fast versus secure fingerprint table spreading forge

ESSENCE: a password must never be stored, only a slow, salted
  fingerprint of it. Slow, so guessing billions costs real money.
  Salted, so cracking a million accounts is a million separate jobs
  rather than one lookup table used against all of them.
ROOT: this file / a fingerprint's strength must be matched to whether
  somebody is trying, and here somebody is always trying.
THREAD: locks (a safe rated in how many minutes it resists), money (a
  note whose forgery must cost more than its value), keys (every door
  keyed differently so one stolen key opens one door).
ASKED-AS: password stored hashed salt slow bcrypt leaked database rainbow table cracking

ESSENCE: the moment data leaves a program it must be written down in
  some agreed shape, and that shape is a promise to every future
  reader. A self-describing format costs bytes and survives; a
  positional one is compact and unreadable without a key that will
  be lost.
ROOT: computing foundations / two ends can only communicate under a
  shared format; the second end here is the future.
THREAD: archives (a box labelled inside and out), music (a score
  against a piano roll), archaeology (a script with no bilingual
  stone).
ASKED-AS: file format json binary compact self describing readable later parse saved data

ESSENCE: readers and writers of different ages will always be running
  at once, so a stored shape may only ever grow. Add fields, never
  reuse a name or a number, never change what an existing field
  means, and let old readers ignore what they do not recognise.
ROOT: shipping software / during any real deployment both the old and
  new code are running, and the data outlives both.
THREAD: law (statutes amended by addition, sections never renumbered),
  post (an address format that keeps accepting the old one), music
  (an instrument added to the score without rewriting the parts).
ASKED-AS: schema change add field remove breaking old readers version compatibility migrate format

ESSENCE: a schema is the contract between systems that will never
  meet and people who will never speak. It says what exists, what is
  required, and what each thing means — and it is the only place that
  knowledge is written down where a machine will enforce it.
ROOT: law / a rule kept by a registry beats a rule kept by mutual
  goodwill.
THREAD: forms (an official form is a schema with boxes), building (a
  drawing that every trade works from), music (a score that players
  who never met can perform together).
ASKED-AS: schema definition fields required types contract between systems meaning shared agreed

ESSENCE: two pieces of text that look identical on the screen may be
  entirely different bytes — an accented letter written as one
  character or as a letter plus a mark. So comparing text is not
  comparing bytes; it needs a rule that puts both into one form
  first.
ROOT: language / a written sign and its encoding are two different
  things, and one sign may have several encodings.
THREAD: names (Mac and Mc filed together or apart), spelling (colour
  and color as one word or two), post (an address matched despite
  punctuation).
ASKED-AS: same text different bytes accents unicode normalise compare duplicate names search

ESSENCE: alphabetical order is not a property of letters. It is a
  decision made by each language — where accented letters fall,
  whether a digraph is one letter, how case is treated — and no
  ordering is correct for all of them at once.
ROOT: language / writing is a convention, and the ordering of a
  convention's signs is part of the convention.
THREAD: directories (a phone book's rules stated in its front matter),
  libraries (filing rules that differ by country), dictionaries (where
  the letter with the ring goes).
ASKED-AS: sorting names alphabetical order accents wrong language collation locale uppercase first

ESSENCE: an instant in time and a reading on a wall clock are two
  different things. The instant is a point. The reading is that point
  plus a rule about where you stand, and the rules are changed by
  governments, sometimes with a few weeks' notice.
ROOT: measurement / a quantity and its expression in a unit are
  separate, and here the unit is decided politically.
THREAD: money (an amount and the currency it is quoted in), maps
  (a position and the datum it is measured from), law (a deadline
  stated in a jurisdiction).
ASKED-AS: time zone stored wrong utc offset future meeting daylight saving changed rule

ESSENCE: local time is not a continuous line. On one night an hour
  does not exist and on another it happens twice, so a timestamp can
  be ambiguous or impossible. Adding a month is not adding thirty
  days, and the thirty-first of the month may not exist.
ROOT: measurement / a calendar is a human rule fitted to an awkward
  sky, and human rules have seams.
THREAD: farming (a season, not a fixed number of days), law (a period
  of notice counted in working days), festivals (a date that moves by
  its own rule).
ASKED-AS: add one month end of month clock goes back hour twice missing date arithmetic

ESSENCE: floating point is a ruler whose marks get further apart as
  the numbers get bigger, so precision is relative, not absolute. Add
  a tiny number to a huge one and the tiny one vanishes entirely — and
  the same numbers summed in a different order give a different total.
ROOT: mathematics / a fixed number of significant digits spread over
  a vast range must space its representable values unevenly.
THREAD: measurement (a scale accurate to a gram and used to weigh a
  lorry), surveying (small angle errors compounding over distance),
  accounting (rounding applied in a different order).
ASKED-AS: floating point sum different order parallel results differ tiny value lost precision

ESSENCE: some quantities have to be exact: money, counts of things,
  legal measures. They are stored as whole numbers of the smallest
  unit, or in a type that works in decimal — and the rounding rule is
  part of the specification, written down, not left to whatever the
  language does.
ROOT: law / an amount owed is an exact fact, and an approximation of
  it is a different amount.
THREAD: money (a ledger that must balance to the penny), trade (a
  weight and measures rule with a stated rounding), pharmacy (a dose
  specified exactly, not nearly).
ASKED-AS: store money pennies integers decimal type rounding rule cents off by one

ESSENCE: any identifier made of real facts eventually changes —
  people change names, companies change registration, countries
  change codes, email addresses move. An identifier that means
  something is an identifier that will one day have to be edited, and
  editing an identifier breaks every reference to it.
ROOT: language / a name that describes is a name that becomes wrong
  when the thing changes; a name that only points does not.
THREAD: records (an NHS or social security number that says nothing),
  libraries (an accession number rather than a title), post (a
  property's unique reference against its house name).
ASKED-AS: primary key email as id changed name natural key surrogate meaningless identifier stable

ESSENCE: whether a thing has one of something or many, and whether
  that many is shared, decides the entire shape of the store and every
  query over it. Getting it wrong is not a coding mistake to be
  patched — it is discovered years later as a field holding a
  comma-separated list.
ROOT: logic / a relation is defined by how many of each side it
  admits, and everything built on it inherits that.
THREAD: forms (one box for a phone number), law (a title with one
  owner until it is inherited by three), families (a form with two
  parent fields).
ASKED-AS: one to many relationship second address comma separated list schema wrong assumed one

ESSENCE: a number with no unit attached is a rumour. Metres or feet,
  pence or pounds, seconds or milliseconds — the unit lives in
  somebody's head or in a column name, and the day two systems meet
  with different assumptions, a spacecraft is lost.
ROOT: measurement / a quantity is a number and a unit together, and
  half of that is not a quantity.
THREAD: medicine (a dose in milligrams or micrograms), building (a
  drawing with no scale stated), navigation (a depth in fathoms read
  as metres).
ASKED-AS: units missing seconds milliseconds metres feet mixed up conversion column name

ESSENCE: keeping only the current state throws away every question
  you have not yet thought to ask. Keeping what happened — each
  change, in order, as a fact that occurred — lets you rebuild any
  view later, including views nobody had imagined when the data was
  written.
ROOT: this file / a store answers only the questions its shape allows,
  and a record of events allows the most.
THREAD: accounting (a ledger of transactions, not a balance scribbled
  over), medicine (a chart that keeps every reading), law (an amended
  register that keeps the crossed-out text).
ASKED-AS: overwrote the old value history lost audit trail events append only rebuild

ESSENCE: programs are rewritten every few years; the data outlives
  all of them. Other systems read it, reports depend on it, exports
  are archived from it — so a mistake in the model is permanent in a
  way that a mistake in code never is.
ROOT: software development / a wrong early choice is ruinous once
  everything leans on it, and everything leans on the data.
THREAD: building (the street grid outliving every building on it), law
  (a register outlasting the office that made it), language (spelling
  fixed by a dictionary centuries ago).
ASKED-AS: database schema outlives code rewrite still same tables data model permanent legacy
