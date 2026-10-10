# 126 DEEP PROGRAMMING LANGUAGES — the families and what each is for
Every language computes the same things. What differs is the bill:
which thoughts cost a line and which cost a week, which mistakes are
refused, shrugged at, or invited. This file is about those bills, and
about why the finest language on paper loses to the one people know.

ESSENCE: a language cannot make anything possible that was
  impossible before, so power never separates them. What separates
  them is price — which ideas are one line and which are a fortnight,
  and which errors are caught, ignored, or actively encouraged.
ROOT: computer science / any machine can imitate any other, so the
  difference cannot lie in what can be computed.
THREAD: tools (a chisel and a saw both cut wood), language (some
  tongues have one word where others need a sentence), kitchens (a
  wok and an oven are not ranked against each other).
ASKED-AS: which language is best why so many differences pick one better than another

ESSENCE: you reach for what is at hand. A language with easy lists
  grows solutions made of lists; one with easy classes ends up
  modelling the weather as a class. The tool does not forbid the
  other thought, it prices it, and priced thoughts are rare thoughts.
ROOT: this file / a language decides what is cheap; the mind / the
  first thing that comes to hand is what gets used.
THREAD: music (an instrument's easy keys shape the tunes written on
  it), language (a distinction you have no word for is a distinction
  you skip), building (timber country builds in timber).
ASKED-AS: everything looks like a class solution shaped by the tool habit thinking style

ESSENCE: translate the whole text once, before anyone runs it, and
  the machine gets tight instructions while you get a long list of
  complaints in advance. Translate as you go and you get an answer in
  a second — and the complaint arrives from a user.
ROOT: computing foundations / the words you wrote never run, only a
  translation of them does; this is the question of when.
THREAD: theatre (a rehearsed play against improvisation), cooking
  (prepped service against cooking to order), translation (a printed
  edition against a live interpreter).
ASKED-AS: compiled interpreted build step errors before running script fast startup slow

ESSENCE: there is a third answer. Begin by interpreting, watch which
  paths actually run hot, then translate those properly while the
  program is alive. It beats any advance translation at the things
  only a running program knows.
ROOT: this file / translating can happen early or late; evidence / a
  measurement beats a guess, however expert.
THREAD: sport (a coach adjusting at half time), farming (fertiliser
  placed where the crop actually came up), roads (lanes widened where
  the traffic proved to be).
ASKED-AS: warms up fast after a while first run slow optimises itself while running

ESSENCE: a type is a claim about what a thing is, checked before
  anything runs. Its power is coverage — it inspects every line,
  including the ones no test reaches and no user has ever walked, and
  it kills one whole family of mistake outright.
ROOT: writing software / the strongest check is a shape that cannot
  say the wrong thing, moved back to before the run.
THREAD: engineering (a gauge run over every part off the line), law
  (a form that will not accept a date in the name box), music (a
  score checked for notes outside the instrument's range).
ASKED-AS: types checked before running compiler complains catches mistakes every line shapes

ESSENCE: the checker must refuse anything it cannot prove safe, so
  it refuses some programs that would have worked perfectly. That is
  not a defect. A check that never rejects a good program never
  catches a bad one either.
ROOT: mathematics / a rule deciding in advance must decide from the
  shape alone, and shapes carry less than behaviour does.
THREAD: security (a gate that turns nobody away is a hole), medicine
  (a test tuned to miss nothing raises false alarms), law (a rule
  strict enough to stop the guilty catches the innocent).
ASKED-AS: fighting the compiler wont accept valid code casting annoying types in the way

ESSENCE: ask what a thing is at the moment you use it rather than
  before. Code is short, shapes can be invented as you go, and one
  piece serves anything that happens to answer. The bill arrives as
  faults on the paths somebody actually walked.
ROOT: this file / the check happens early or late, and this is late.
THREAD: shops (goods checked at the till rather than at the gate),
  theatre (blocking worked out in performance), building (measuring
  on site instead of on the drawing).
ASKED-AS: no types until it runs crashes on rare path rename everywhere search flexible

ESSENCE: whether types are checked early is one question. Whether
  the language will quietly convert one kind into another is a
  different one entirely. A weak language answers a nonsense request
  with a number instead of a complaint, and the nonsense travels on.
ROOT: writing software / a fault caught at its birth names its own
  cause, and a silent conversion is the exact opposite of that.
THREAD: measurement (feet added to metres without complaint), money
  (two currencies summed as bare numbers), cooking (a tablespoon read
  as a teaspoon by a willing helper).
ASKED-AS: string plus number weird result silently converts concatenates surprising equals comparison

ESSENCE: the checker can usually work out a type from what you
  already wrote, so the guarantee need not be paid for in typing.
  What stays written down is what a reader wanted anyway — the
  promises at the edges of each piece.
ROOT: this file / static checking costs ceremony, and most of the
  ceremony was saying twice what was already plain.
THREAD: grammar (agreement understood without being spoken), drawings
  (a dimension implied by the geometry), music (a key signature stated
  once at the front).
ASKED-AS: types worked out automatically dont have to write them inferred annotations var

ESSENCE: a comment saying what goes in and what comes out drifts out
  of step the day the code changes. A type saying the same thing
  cannot: it is checked at every build. It is the only documentation
  the machine keeps honest on your behalf.
ROOT: writing software / duplicated knowledge drifts apart unless
  something forces the copies to agree.
THREAD: labels (a bottle whose cap fits only one machine), law (a
  form that validates before it will submit), building (a part that
  will not bolt where it does not belong).
ASKED-AS: signature says what it takes comment out of date documentation always true checked

ESSENCE: you say when memory is taken and when it is handed back.
  Nothing pauses, nothing is hidden, and the cost is exactly what you
  wrote. In exchange you own a whole family of fault: freed twice,
  used after its end, or never given back at all.
ROOT: writing software / every piece of memory has an owner and an
  end — here the owner is you, in every case, forever.
THREAD: keys (whoever holds them locks up), tools (the ladder is
  yours until you return it), surgery (every swab counted in and
  counted out).
ASKED-AS: malloc free manual memory crash after freeing double free who releases it

ESSENCE: keep a tally of how many holders a thing has and destroy it
  when the tally reaches nothing. The end is prompt and predictable.
  But every share and release costs a count, and two things holding
  each other keep one another above zero forever.
ROOT: this file / memory needs an owner and an end; counting is
  ownership shared out and tracked by tally.
THREAD: libraries (a book on loan to a whole reading group), tenancy
  (a flat given up when the last resident leaves), the living world
  (two species each propping up the other's numbers).
ASKED-AS: reference count freed when last one lets go cycle never freed retain release

ESSENCE: a fourth answer: the checker follows who owns each thing
  and who has merely borrowed it, and refuses to build a program
  where a borrow outlives its owner. The safety costs nothing while
  running. It is paid in what you are no longer allowed to write.
ROOT: this file / memory needs an owner and an end — this makes the
  owner something the compiler can see and follow.
THREAD: libraries (a loan card that will not let two people hold one
  book), law (a title that must always name someone), workshops
  (every tool with a marked place and one owner).
ASKED-AS: borrow checker owns the value moved lifetime wont compile safe without collector

ESSENCE: somebody must decide when a thing's life ends. Write it
  yourself and pay in mistakes; count the holders and pay on every
  share; let a sweeper hunt the dead and pay in pauses and spare
  room; prove it at build time and pay in what the checker forbids.
ROOT: physics / a store is finite, so everything taken must be given
  back, and the deciding is work wherever you put it.
THREAD: hotels (checkout by the guest, by the clock, or by the maid),
  farming (culling decided by the farmer, the fence, or the winter),
  households (tidying now, weekly, or never).
ASKED-AS: garbage collected manual memory which is better pauses overhead safety cost choice

ESSENCE: a list of commands that change a store, in order. It is the
  shape of the machine itself, which is why it is the default — and
  why understanding a piece means replaying it in your head, step by
  step, holding the whole store as you go.
ROOT: computing foundations / the processor carries out small orders
  one after another and nothing else.
THREAD: recipes (do this, then this), assembly lines (each station
  after the last), directions (turn left at the church — useless from
  anywhere else).
ASKED-AS: step by step commands variables changing order matters loops assignments normal programming

ESSENCE: any procedure whatever can be built from three shapes: one
  thing after another, a choice between two, and a repetition. That
  is why the free jump was surrendered — not because it was weak, but
  because a program full of jumps has no shape a reader can hold.
ROOT: mathematics / a small set of forms can generate a whole family;
  the mind / a reader holds structure, never a hundred destinations.
THREAD: writing (paragraphs and sentences against one endless line),
  building (rooms and doors against a maze), music (verse, chorus,
  repeat).
ASKED-AS: goto considered harmful loops if else structure spaghetti jump anywhere blocks nesting

ESSENCE: put data and the only operations permitted on it in one
  place, and the data can never be found in a state its own code
  would not allow. Everything else about objects is decoration. This
  is what they are for.
ROOT: writing software / what a part promises is what others lean on
  and the inside is its private business — an object is that idea
  given a boundary and a name.
THREAD: banks (a balance changed only by deposits and withdrawals),
  machines (a guard opened only by the interlock), law (a fund
  reachable only through its trustee).
ASKED-AS: object class methods data together encapsulation private fields state always valid

ESSENCE: inheritance hands over two things at once — reuse of a
  parent's code, and a promise that a child may stand anywhere the
  parent stands. The first is a convenience. The second is the
  valuable one, and it is the one people forget they have made.
ROOT: this file / a type is a claim, and a subtype is the claim that
  one thing may be used wherever another was expected.
THREAD: law (a deputy who may act wherever the officer may), trades
  (an apprentice signed off to do the master's work), machines (a
  replacement that must fit every socket the original fitted).
ASKED-AS: extends inherits parent class reuse subclass override base shared behaviour hierarchy

ESSENCE: a child is built on the parent's insides, not on its
  promises. So the parent may no longer change its own private
  workings without breaking children its author never saw. The
  tightest coupling in the language is drawn as a thin line.
ROOT: writing software / change travels along couplings, and this
  coupling reaches straight through the boundary.
THREAD: families (a household rule inherited by people who never
  agreed to it), building (a floor others have already built on), law
  (a clause every later contract quoted).
ASKED-AS: changed base class broke everything deep hierarchy fragile parent subclass tangled inheritance

ESSENCE: if a child cannot honestly do everything the parent
  promised, the relation is a lie no compiler can see. A square is a
  rectangle in geometry and not in code, because a rectangle promises
  that its width and height move separately.
ROOT: this file / inheritance is a promise of substitution; language
  / a category is defined by what it guarantees, not by what it
  resembles.
THREAD: law (a substitute who may not sign what the original could),
  machines (a part that fits the socket but not the load), staff
  (cover who cannot authorise what the absent person authorised).
ASKED-AS: square rectangle subclass breaks caller expectations override throws unsupported wrong subtype

ESSENCE: hold a thing instead of being one. The relation is then
  chosen while the program runs, can be swapped for another, and
  takes only the part you wanted — instead of a permanent bond to a
  whole surface you never asked for.
ROOT: writing software / a part that is handed what it needs can be
  handed something different tomorrow.
THREAD: tools (a drill that takes any bit because it holds none),
  theatre (an actor handed props rather than born with them), machines
  (an engine bolted in rather than cast into the frame).
ASKED-AS: has a versus is a composition inheritance wrap delegate swap parts flexible

ESSENCE: the useful half of inheritance with none of the cost — a
  named list of promises with no code behind it. Anything that keeps
  the promises fits, whoever wrote it and whenever, with neither side
  knowing the other exists.
ROOT: writing software / what is published and leaned on binds; the
  rest may be rebuilt freely.
THREAD: plugs and sockets (a shape agreed by strangers), law (a
  licence stating what its holder may do), music (any instrument that
  can play the written part).
ASKED-AS: interface implements contract no code just promises plug in any class fits

ESSENCE: build the answer by combining functions instead of by
  editing a store. There is no current state to carry in your head
  while reading — each piece takes what it is given and returns what
  it made, and the whole is exactly what the pieces say it is.
ROOT: mathematics / a function is a mapping, not an event; nothing
  inside it happens, so nothing inside it can happen in the wrong
  order.
THREAD: mathematics (an expression means the same wherever it is
  written), cooking (a sauce built from ingredients rather than
  adjusted in a pot for hours), music (a canon grown from one line).
ASKED-AS: functional style pure functions map filter no side effects different way thinking

ESSENCE: a call that only computes can be replaced by its answer
  wherever it appears, and nothing changes. That one property is why
  pure code is easy to test, safe to remember, safe to repeat and
  safe to run in parallel — four gifts from a single fact.
ROOT: this file / a function is a mapping; writing software / a piece
  with hidden effects cannot be reasoned about where it stands.
THREAD: arithmetic (three times four is twelve, anywhere), law (a
  certified copy standing for the original), translation (a phrase
  that survives being quoted out of its paragraph).
ASKED-AS: same input same output replace with result cacheable testable parallel safe repeat

ESSENCE: if nothing may be changed, altering a list of a million
  means building a new one — except that it does not. The new version
  shares everything the change did not touch, and only the path down
  to the change is freshly made.
ROOT: writing software / an unchangeable value cannot be spoiled from
  a distance; this file / the cost lands somewhere, and sharing is
  where it lands lightest.
THREAD: writing (a new edition reusing the unchanged chapters),
  building (a new wing on the same foundations), records (an amendment
  filed beside the original instead of over it).
ASKED-AS: copying whole list expensive immutable slow shares unchanged parts persistent version

ESSENCE: when behaviour can be passed about like a number, a whole
  family of loops collapses into a few named shapes — do this to
  each, keep the ones that pass, fold them all into one answer. The
  loop's plumbing stops being written, so it stops being written
  wrong.
ROOT: this file / functions are values; writing software / faults
  gather at the edges, and hand-built loop edges are where they gather
  thickest.
THREAD: factories (one machine, a changeable die), language (a verb
  that takes any object), music (a form into which any melody can be
  poured).
ASKED-AS: pass a function as an argument map filter reduce callback lambda loops replaced

ESSENCE: iteration says what a walk does; recursion says what the
  thing is. Over a list either will serve. Over a tree, recursion is
  three lines and iteration is a hand-built stack — because the shape
  of the data is the shape of its own definition.
ROOT: mathematics / induction — a case answered outright, and a step
  that makes the problem smaller.
THREAD: families (a family tree walked generation by generation),
  boxes (opening a box of boxes), language (a clause inside a clause
  inside a clause).
ASKED-AS: recursion loop which is better stack overflow tree walking tail call deep

ESSENCE: compute nothing until something asks for it. A list can now
  be endless, and only the part you looked at ever exists. The price
  is that you no longer know when work happens or what is being held,
  and one small reference can pin an enormous unfinished pile.
ROOT: this file / a pure expression's value does not depend on when
  it was computed, so the when can be moved about freely.
THREAD: post (a subscription that prints only what is read), shops
  (made to order), libraries (a catalogue whose books exist once
  somebody requests them).
ASKED-AS: lazy evaluation infinite list computed when needed memory blowup delayed generator

ESSENCE: state the facts and the relations, ask a question, and let
  the machine search out everything that satisfies them. You describe
  the answer's properties and never write the route. Puzzles, rules
  and rosters fall out in a page.
ROOT: mathematics + logic / a solution is anything satisfying the
  constraints, and satisfying can be searched for mechanically.
THREAD: crosswords (the clues constrain, you do not compute), law (a
  case that satisfies every element of an offence), farming (a
  rotation meeting every rule at once).
ASKED-AS: prolog rules facts query solver constraints describe what not how search puzzle

ESSENCE: the operation applies to the whole collection at once. Add
  two thousand-long lists by writing a plus. The loop, its counter,
  its bounds and all of its mistakes vanish together — and what is
  left is so dense that a page of it is an entire program.
ROOT: this file / a language prices thoughts, and here the cheap
  thought is the whole collection treated as one thing.
THREAD: music (a chord written as one symbol), mathematics (matrix
  notation), cooking (season the whole pot, never each spoonful).
ASKED-AS: whole array at once no loops apl vectorised dense symbols concise unreadable

ESSENCE: no names at all. Values sit on a stack; each word takes what
  it needs from the top and leaves its result there. The whole
  implementation fits in a few pages, which is why these languages
  turn up inside the smallest and strangest machines.
ROOT: computing foundations / a machine needs somewhere to put
  half-finished values, and a stack is the cheapest somewhere there
  is.
THREAD: kitchens (a plate passed down a line), luggage (last in,
  first out), printing (setting type by position rather than by
  label).
ASKED-AS: forth stack based no variables push pop postfix tiny language embedded firmware

ESSENCE: how a language lets many things happen at once is the single
  choice that shapes its programs most. Not because the speeds
  differ, but because each model decides what can go wrong, and the
  wrong things are what you will spend your life on.
ROOT: writing software / concurrency is bought with reasoning, and
  the model is the thing you must reason in.
THREAD: traffic (roundabouts, lights and give-way are three whole
  systems), music (a conductor, a click track, or players listening to
  each other), kitchens (a pass, a shout, or a ticket rail).
ASKED-AS: threads async actors channels which model concurrency choice library mismatch cannot mix

ESSENCE: shared memory with turns taken by hand. Whoever wants the
  data takes the lock — and every other holder must have agreed to
  take the same lock for the same data, an agreement nothing in the
  language records, checks, or remembers.
ROOT: computing foundations / threads live in one room with no wall;
  people and power / a shared thing with no referee goes to whoever
  grabs hardest.
THREAD: kitchens (one hob and a rule about who may use it), meetings
  (a talking stick nobody is obliged to hold), roads (a single-track
  bridge run on honour).
ASKED-AS: locks mutex shared data threads forgot to lock deadlock two locks convention

ESSENCE: nothing is shared. Each thing owns its own state, runs on
  its own, and may affect another only by sending a message that will
  be handled in the other's own time. With nothing shared there is
  nothing to race over, and that whole fault family is gone.
ROOT: computing foundations / isolation is a wall — this builds a
  wall around every single worker.
THREAD: post (offices that only exchange letters), ships (each with
  its own log, signalling across water), companies (departments that
  request rather than reach into one another).
ASKED-AS: actors message passing mailbox nothing shared no locks isolated independent workers erlang

ESSENCE: hand the value over and stop owning it. Instead of many
  workers reaching into one place, values travel down a pipe from one
  worker to the next and possession travels with them — share by
  communicating rather than communicate by sharing.
ROOT: this file / what nobody shares cannot be raced over; craft / a
  workpiece is in one pair of hands at a time.
THREAD: assembly lines (the part moves, the worker stays), kitchens
  (the pass between kitchen and floor), relay racing (the baton is
  the ownership).
ASKED-AS: channel send receive pipeline hand off worker queue between threads ownership moves

ESSENCE: one worker, many waits. While one job waits on a disk or a
  distant machine, the worker picks up another and comes back when the
  answer lands. It is enormous for work that is mostly waiting and
  worth exactly nothing for work that is thinking.
ROOT: computing foundations / a distant answer takes a million times
  longer than a local one, and waiting is not working.
THREAD: waiting rooms (one doctor seeing others while a test runs),
  kitchens (starting the next dish while one is in the oven), post
  (writing other letters while awaiting a reply).
ASKED-AS: async await promise blocking waiting network one thread still slow cpu

ESSENCE: once a piece can pause, everyone who calls it must be able
  to pause too, and so must their callers, all the way up. The
  property climbs the entire call chain — which is why adding one
  waiting call to an old program can mean rewriting half of it.
ROOT: this file / a pausing call is not an ordinary call, and the
  difference cannot be hidden from the caller.
THREAD: language (a formal register that must be kept up once begun),
  building (a waterproof layer that is worthless unless continuous),
  law (a clause that binds every contract downstream of it).
ASKED-AS: async spreads everywhere infects callers two versions library blocking rewrite chain

ESSENCE: throw the failure and let it fly upward until somebody
  catches it. The ordinary path stays clean and no caller is forced
  to deal with anything — and control may now leave any line, so the
  paths through the code are no longer the ones you can see.
ROOT: writing software / failure is a fork in the story; here the
  fork is not drawn anywhere on the page.
THREAD: fire alarms (everyone leaves by an exit nobody planned), law
  (an appeal that jumps the ordinary chain), medicine (a crash call
  that interrupts whatever was happening).
ASKED-AS: throw catch exception try finally propagates up invisible path uncaught cleanup crashed

ESSENCE: failure comes back as an ordinary answer, so the paths are
  visible and local. And an ordinary answer can be ignored: every
  call now carries a check the writer must remember, and the check is
  noise on the page until the day it is missing.
ROOT: this file / a fork drawn on the page is a fork you can see —
  and a fork you can walk straight past.
THREAD: post (a delivery slip you are meant to read), medicine (a
  result filed and never looked at), shops (a receipt that says the
  card was declined).
ASKED-AS: error code returned check every call ignored return value noisy explicit forgot

ESSENCE: the settlement most new languages reach — an answer that is
  either a value or a failure, wrapped in one thing the checker will
  not let you open without answering both cases. Visible like a
  return value, impossible to ignore like a thrown one.
ROOT: writing software / the strongest check is a shape that cannot
  say the wrong thing.
THREAD: forms (a field that will not submit blank), law (a verdict
  that must answer every count), engineering (a switch with no middle
  position).
ASKED-AS: result type either ok or error must handle both cases pattern match forced

ESSENCE: a value belonging to every type at once that supports no
  operation at all. Because it fits everywhere, the type system says
  nothing about it, so every use of everything becomes a possible
  failure that nothing declared. Its inventor called it his
  billion-pound mistake.
ROOT: this file / a type is a claim about what a thing is, and this
  is a value that answers every claim falsely.
THREAD: forms (a blank that every box accepts), keys (a key that fits
  every lock and turns none), records (an entry that means unknown and
  zero at the same time).
ASKED-AS: null pointer exception nothing there every type crash undefined missing value

ESSENCE: make absence its own case, inside the type, so the compiler
  makes you open the box before you can use what is in it. The check
  no longer has to be remembered, because a program that skipped it
  does not build.
ROOT: this file / a shape that cannot say the wrong thing beats a
  rule that everyone must remember.
THREAD: post (a parcel that must be signed for before it opens),
  medicine (a result that says pending rather than normal), shops (an
  answer of out of stock rather than a price of nothing).
ASKED-AS: option maybe some none unwrap must check before using compiler forces absent

ESSENCE: write the piece once for any type and keep every check
  intact. A list of things, a store of anything, a sorter for
  whatever can be ordered. Without them you either copy the code per
  type or throw the types away and check by hand.
ROOT: this file / a type is a claim, and a generic is a claim with a
  hole in it that each caller fills in.
THREAD: tools (one wrench, many sockets), forms (one template with a
  named blank), music (a form transposed into any key).
ASKED-AS: generic template type parameter list of anything reuse without copying constraint bounds

ESSENCE: there are only two ways to build them. Make a separate copy
  for each type actually used — fast, and the program swells. Or make
  one copy that handles anything by putting everything in a box —
  small, and every access pays for the box.
ROOT: physics / a general machine either becomes many specific ones
  or carries its generality around while it runs.
THREAD: manufacture (a die per size against one adjustable jig),
  cooking (a recipe per portion against one scaled by weight),
  publishing (an edition per country against one with inserts).
ASKED-AS: generics code bloat boxing compile time binary size erasure slow generic

ESSENCE: code that writes code. It removes repetition nothing else
  can reach and raises whole structures from a line — and what runs is
  now something nobody wrote, cannot be searched for, and does not
  appear in the file where the fault seems to live.
ROOT: writing software / a name is a claim planted where readers trip
  over it, and a generated name was planted by no one.
THREAD: printing (a press that sets its own type), law (a clause that
  rewrites other clauses), music (a score instructing the performer to
  compose the middle).
ASKED-AS: macros generate code reflection magic where is this defined cannot find annotation

ESSENCE: syntax changes nothing about what a language can do and
  everything about how much of a reader's attention goes on
  punctuation instead of meaning. It is not decoration. Attention is
  the scarce thing in the room, and syntax is a tax levied on it.
ROOT: teaching / a familiar form frees the mind to take in the
  content.
THREAD: music (notation nobody reinvents per piece), maps (symbols
  meaning the same in every country), writing (punctuation that
  disappears when it is right).
ASKED-AS: syntax ugly braces semicolons indentation readable verbose noisy style looks like

ESSENCE: what comes in the box decides what everybody's code looks
  like, because everybody reaches for the same thing. A language's
  real vocabulary is its library, and two programs in one language
  built on different libraries are barely the same language.
ROOT: people and power / a coordination rule's whole value is that
  everyone follows the same one.
THREAD: language (a shared vocabulary beating a better private one),
  tools (a workshop's assumed default set), music (the instruments an
  orchestra is taken to have).
ASKED-AS: standard library built in batteries included what comes with it everyone uses

ESSENCE: pulling a stranger's finished work in a second is the most
  powerful thing a modern language offers, and the same door is its
  widest wound. Every name you type is a decision to run somebody
  else's code with your privileges, for as long as you live.
ROOT: shipping software / a program stands on other programs, and the
  standing is now one command deep.
THREAD: food (a supplier's supplier standing in your kitchen),
  building (a batch of steel certified only by paperwork), post (a
  parcel nobody ordered, opened at your desk).
ASKED-AS: npm pip packages install dependency tree transitive hundreds trust supply chain

ESSENCE: some communities favour many tiny packages, some a few large
  ones, some almost none at all. The language does not decide this
  and cannot change it — but it is what you live with daily, and you
  inherit it whole the moment you choose the language.
ROOT: people together / a culture is re-taught into every arrival and
  travels far better than any written rule.
THREAD: trades (a region's building customs), cooking (a cuisine's
  assumptions about what every kitchen holds), law (a jurisdiction's
  drafting style).
ASKED-AS: community norms tiny packages one big framework ecosystem culture inherited habits

ESSENCE: a debugger that works, a package manager that resolves, a
  formatter, and an editor that genuinely understands the code are
  worth more in practice than any feature on any comparison chart.
  Most language deaths are tooling deaths.
ROOT: this file / a language's value is what it makes cheap, and
  tools are most of the cost of an ordinary working day.
THREAD: trades (a tool is judged by its handle and its case), vehicles
  (serviceability sells fleets), music (an instrument nobody can get
  repaired locally).
ASKED-AS: debugger editor autocomplete package manager tooling why nobody uses it ideas

ESSENCE: one tool that rewrites everybody's layout into one shape
  ends every argument about layout permanently — and the argument was
  never about layout. It was about attention spent on something that
  carries no meaning at all.
ROOT: writing software / one ordinary style used everywhere is read
  faster than a collection of individually better ones.
THREAD: printing (a house style applied by the typesetter), law (court
  filings on a fixed form), sport (a standard pitch nobody argues
  about).
ASKED-AS: formatter auto format style argument tabs spaces settled rewrites layout bikeshedding

ESSENCE: some costs are built into a language and no cleverness
  removes them. If every value sits boxed on a heap, if every access
  is checked, if every number is unbounded by default, there is a
  floor under your speed that only leaving the language gets beneath.
ROOT: physics / a guarantee that holds everywhere must be checked
  everywhere, and checking costs.
THREAD: vehicles (a bus cannot be tuned into a motorcycle), safety (a
  machine with interlocks is slower on purpose), cooking (an oven that
  refuses to exceed a temperature).
ASKED-AS: slow language never as fast as c interpreter overhead boxing checks ceiling

ESSENCE: nearly every high-level language keeps a door down to a
  lower one, and the important libraries walk through it. The pleasant
  language you write in is often a thin skin over pieces written in
  something else — and the skin is where all the safety lives.
ROOT: this file / a ceiling exists, and the only way under it is out.
THREAD: building (a timber house on a concrete raft), medicine (a
  gentle treatment with surgery standing behind it), transport (a
  smooth ride over an unglamorous engine).
ASKED-AS: native extension c library underneath calls out foreign function wrapper bindings fast

ESSENCE: a language that can say only the things in one domain says
  them in a line and refuses everything else. The refusal is the
  point: a query language cannot loop forever, a layout language
  cannot delete your files, and a rule that cannot be written cannot
  be got wrong.
ROOT: this file / a language's value is what it makes cheap — and
  here, what it makes impossible.
THREAD: forms (a return you cannot answer freely), music (tablature
  that can say only what a guitar can do), law (a standard form with
  blanks and nothing else).
ASKED-AS: sql css regex config little language only does one thing cannot express

ESSENCE: it begins as a list of settings. Then one setting must
  depend on another, so there are variables; then two places differ,
  so there are conditions; then it repeats, so there are loops. The
  file is now a programming language with no types and no debugger.
ROOT: this file / a small language drifts toward generality as soon
  as its users have real problems it cannot express.
THREAD: forms (an application form with pages of exceptions), law (a
  by-law amended into unreadability), recipes (a card buried in
  marginal notes).
ASKED-AS: config yaml templating logic in configuration variables conditionals grew untestable

ESSENCE: a language lives on answers to questions, libraries for the
  dull parts, people who can be hired and employers who will hire
  them. A better language with none of those loses to a worse one
  with all four, every time, and it is not close.
ROOT: people and power / a coordination rule's value comes entirely
  from how many others are following it.
THREAD: money (a currency nobody will accept), language (a
  constructed tongue with no speakers), tools (a fitting standard no
  shop stocks).
ASKED-AS: dead language nobody uses it hiring jobs answers online libraries community popular

ESSENCE: fluency is worth more than fit. A team's second-best
  language, used by people who know its traps, its libraries and its
  tools, beats a better-suited one that everyone is learning in
  public against a deadline.
ROOT: this file / a language's cost is paid in the daily work, and
  the daily work is done by the people you actually have.
THREAD: kitchens (a cook's own knives), sport (a formation the squad
  already plays), building (the material the local trades can really
  work).
ASKED-AS: which language should we use team knows learning curve familiar new risky

ESSENCE: choosing a language chooses who you can hire, what you can
  borrow, and how long the thing stays maintainable — for as long as
  the system lives, which is always longer than anybody planned. It
  is the least reversible decision in a project.
ROOT: software development / a wrong choice is cheap today and
  ruinous once everything has come to lean on it.
THREAD: building (a structural material chosen once and for all),
  farming (an orchard is a thirty-year decision), law (a jurisdiction
  named in a founding document).
ASKED-AS: stuck with it legacy language nobody wants to work on rewrite decade hiring
