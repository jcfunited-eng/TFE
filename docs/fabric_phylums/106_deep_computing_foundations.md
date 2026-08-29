# 106 DEEP COMPUTING FOUNDATIONS — what the machine is doing underneath

ESSENCE: underneath every program, however clever, a processor
  does one kind of thing: it carries out very small orders, one
  after another. Move this number. Add these two. Compare them.
  Jump there. There is nothing else inside.
ROOT: computer science / a recipe is steps in order, and the
  machine is only a stage for steps.
CANNOT: no act a machine performs that is not built from these
  tiny orders. No understanding above that may contradict it —
  every picture, word and sound on a screen was assembled out of
  moves and adds.
THREAD: writing (every book is letters in order), building (a
  cathedral is placed stones), music (any piece is single notes
  in sequence).
ASKED-AS: instructions processor chip does simple steps move add compare jump nothing else inside

ESSENCE: the machine repeats one loop forever — fetch the next
  instruction from memory, work out what it means, do it, then
  move the marker on. That marker, "where am I", is the entire
  sense of place the machine has.
ROOT: this file / a processor only carries out small orders;
  computer science / a system is its state plus rules for moving.
CANNOT: no processor that knows what it is doing overall; it sees
  one instruction, never the program. No progress if the marker
  does not advance — the loop is not a feature, it is the machine
  being alive.
THREAD: reading (a finger moving along a line), assembly lines
  (one station, one action, then the next part), clerks (a stack
  of forms and a place-marker).
ASKED-AS: fetch decode execute loop next instruction where am i counter repeats forever

ESSENCE: inside the machine everything is numbers — a letter, a
  colour, a sound, an instruction. What a number means comes
  entirely from the agreement about how to read it. Change the
  agreement and the same bits are a photograph or gibberish.
ROOT: language / a symbol carries meaning only under a shared
  convention.
CANNOT: no meaning inside the data itself; a stored number does
  not know what it is. No reading a file without knowing its
  kind, which is why a wrong guess about format gives noise
  rather than an error.
THREAD: writing (marks mean nothing without the alphabet), money
  (a note is paper plus agreement), music (dots on lines, given a
  clef).
ASKED-AS: everything is numbers ones zeros bits meaning agreed same value picture sound text

ESSENCE: a number inside a machine has a fixed number of digits,
  so it has a largest value. Add one past it and it does not
  overflow into a bigger box — it wraps around, quietly, to a
  small or negative number, and everything after that is wrong.
ROOT: physics / a fixed store holds a fixed count of states.
CANNOT: no counting past the size of the box. No warning either,
  unless someone asked for one — the addition succeeds, and the
  wrongness travels downstream looking exactly like a normal
  value.
THREAD: odometers (rolling from all nines to zero), clocks (the
  hour after twelve is one), calendars (a two-digit year meeting
  the century).
ASKED-AS: number too big wraps around negative counter limit maximum value overflow rolls over

ESSENCE: fractions are stored in a scheme that cannot represent
  most decimals exactly, only very close. So a tenth plus two
  tenths is not quite three tenths, and errors from many small
  operations accumulate.
ROOT: mathematics / a finite store cannot hold an endless
  expansion, and most decimals are endless in the machine's base.
CANNOT: no exact equality test on these numbers; you compare
  within a tolerance or you get nonsense. No money held in them —
  count whole pennies, because a bank does not accept "close
  enough".
THREAD: measurement (a ruler has a smallest mark), cooking
  (repeated rounding of halves drifts), surveying (small angle
  errors compound over distance).
ASKED-AS: decimal not exact rounding money pennies wrong adds up point one arithmetic

ESSENCE: a byte is not a letter. Most alphabets need more than
  one byte per character, so counting, cutting and reversing text
  by bytes will split a letter in half and produce rubbish where
  a name used to be.
ROOT: this file / everything is numbers, and characters are
  numbers under an agreed scheme.
CANNOT: no reading text without knowing its encoding — the same
  bytes are two different words under two schemes. No safe
  cutting of text at an arbitrary byte; the cut must fall on a
  character boundary.
THREAD: language (a letter with an accent is still one letter),
  writing systems (some scripts join marks into one sign), post
  (a name misspelled by machinery that assumed an alphabet).
ASKED-AS: letters bytes accents emoji garbled question marks encoding length counting characters text

ESSENCE: people write in words; machines run small orders. Some
  systems translate the whole text once, in advance, and run the
  result; others translate line by line as they go. Either way
  the words you wrote never run — a translation of them does.
ROOT: this file / a processor only carries out small orders, so
  everything human must be turned into them.
CANNOT: no machine reading your source directly. No blaming only
  your text when behaviour is odd — the translator's choices, the
  version, and its settings are all part of what actually ran.
THREAD: translation (the audience hears the interpreter),
  cooking (a recipe read aloud versus prepped in advance), music
  (score to performance, always by someone).
ASKED-AS: source code translated machine instructions compiler runs directly build step language text

ESSENCE: memory comes in layers, each larger and slower than the
  last, and the machine spends much of its life waiting on the
  slow ones. Work that keeps touching things near what it just
  touched runs fast; work that jumps everywhere starves.
ROOT: physics / distance and size both cost time, and no material
  escapes both.
CANNOT: no memory that is both large and fast; the trade is
  physical, not a design failing. No speed from a good method
  that walks memory at random — the layout can beat the
  algorithm.
THREAD: kitchens (counter, cupboard, cellar, shop), workshops
  (the tools on the bench set the pace), libraries (the desk pile
  versus the stacks).
ASKED-AS: memory levels near far fast slow nearby data locality waiting cache layers speed

ESSENCE: the machine never fetches one number; it fetches a whole
  neighbourhood, because moving a block costs about the same as
  moving one item. Neighbours are therefore free and strangers
  expensive — how the data sits decides the speed.
ROOT: this file / distance costs; craft / one trip carries
  whatever one trip can carry.
CANNOT: no fetching a single value cheaply — you pay for the
  block whether you use the rest or not. No fast walk over data
  scattered one item per block; you are carrying buckets to take
  sips.
THREAD: shopping (one trip, a full basket), post (a parcel priced
  by the journey, not the gram), farming (walk the row, not the
  field at random).
ASKED-AS: grabs a whole chunk neighbours nearby free block line layout order in memory

ESSENCE: the gaps between where data can sit are not small. In
  the processor's own store it is in your hand; in main memory it
  is a walk down the corridor; on a disk it is a journey; across
  the world it is an expedition. Same word, wildly different
  price.
ROOT: this file / memory is layered, and each layer is
  further away than the last.
CANNOT: no treating storage as one thing — a design blind to
  which layer it touches will be a thousand times slower for no
  visible reason. No hiding a journey behind a tidy name; the
  waiting is real.
THREAD: distance (pocket, room, town, continent), libraries (in
  hand, on the shelf, in the warehouse, on loan), memory
  (recalled, looked up, written away for).
ASKED-AS: disk hard drive slower than memory thousands of times storage ram gap huge

ESSENCE: the machine can find memory that nothing can reach any
  more and take it back by itself. The price is that it must
  occasionally stop the program to do so — safety bought with
  pauses at moments you did not choose.
ROOT: software development / every allocation has an owner and an
  end; this is the machine owning the end.
CANNOT: no automatic collection without pauses or extra work;
  something must trace what is still reachable. No collector that
  saves you from holding on to things you no longer need — what
  is still referenced is still alive, wanted or not.
THREAD: cleaning (a nightly sweep that closes the shop), grazing
  (fields rested in rotation), libraries (a stock-take with the
  doors shut).
ASKED-AS: memory cleaned automatically freed collector pause stops briefly unreachable no longer referenced

ESSENCE: many programs want the same processor, memory, disk and
  network at once, and none of them can be trusted to share. The
  operating system stands between them: it hands out turns and
  space, and it alone may touch the hardware.
ROOT: people together / a shared resource with no referee is
  taken by whoever grabs hardest.
CANNOT: no fair sharing without a referee that outranks every
  player. No program reaching the hardware directly — it must
  ask, and the asking is exactly where safety lives.
THREAD: sport (the referee is on neither team), traffic (signals
  at a shared junction), courts (a dispute settled by someone
  above both parties).
ASKED-AS: operating system windows linux referee shares hardware turns between programs manages resources computer

ESSENCE: the machine runs in two modes: the privileged one, where
  anything may be touched, and the ordinary one, where programs
  live. A program asks for anything real — a file, a message, more
  memory — by knocking on a door and being carried across.
ROOT: this file / the operating system alone may touch the
  hardware, so there must be a door.
CANNOT: no touching the world from ordinary mode without
  crossing. No free crossing either: each one costs, which is why
  reading a file in one big piece beats reading it a byte at a
  time by a wide margin.
THREAD: banks (the counter between customer and vault), courts
  (an application, not a self-help remedy), buildings (a controlled
  door rather than an open wall).
ASKED-AS: asking the system to do it door between program and machine costly crossing

ESSENCE: the world does not wait its turn. A key press, an
  arriving packet, a finished disk read all interrupt the machine
  mid-loop: it saves its place, handles the event, and resumes as
  if nothing happened. That is how a machine that only marches
  forward can also react.
ROOT: this file / the processor's loop has a place-marker, and a
  saved marker can be returned to.
CANNOT: no noticing anything without either interruption or
  constant asking, and constant asking wastes the machine. No
  handling of an interruption that may take its time — everything
  else is stopped while it runs.
THREAD: shops (a bell at the counter), nursing (a call button
  mid-round), parenting (whatever you were doing, saved and
  resumed).
ASKED-AS: key pressed signal stops what it was doing handles then returns world interrupts

ESSENCE: each program runs inside its own walled room, with
  memory no other program can see or spoil. That wall is the
  reason one program crashing does not take the machine, and your
  bank page down with it.
ROOT: this file / the operating system is referee; law / property
  lines exist so neighbours need not trust each other.
CANNOT: no isolation without a wall, and no wall without a cost —
  talking across it means copying or asking permission. No
  containment at all where any part may write any other part's
  memory.
THREAD: ships (watertight compartments), buildings (fire doors),
  farming (fences so one sick animal is not the whole herd).
ASKED-AS: program crashed others fine separate own memory walls isolated processes task manager apps

ESSENCE: threads are workers inside one room. Sharing between
  them is instant because there is nothing in between — and for
  exactly that reason, one worker's mistake corrupts everyone's
  work, with no wall anywhere to catch it.
ROOT: this file / isolation is a wall, and a wall is what was
  removed here.
CANNOT: no cheap sharing and safe isolation at once; the wall
  removed for speed is the wall that was protecting you. No
  containing a fault inside one thread — the damage is the whole
  program's.
THREAD: kitchens (one bench, no partitions), ships (one hold, no
  bulkheads), offices (a shared desk where anyone may move
  anyone's papers).
ASKED-AS: threads share memory same program inside no walls one mistake ruins all workers

ESSENCE: there is one processor and many things wanting it, so
  the system hands out slices of time very fast, and each program
  believes it has been running all along. The smoothness is made
  entirely of turns.
ROOT: this file / the machine does one instruction at a time, so
  sharing must be sharing of time.
CANNOT: no running everything at once on one worker — the slices
  are real and the total is fixed. No promise about when your
  turn comes unless something specifically promises it; ordinary
  systems offer fairness, never punctuality.
THREAD: teaching (one teacher circulating among thirty), medicine
  (a waiting room with triage), kitchens (one oven, many dishes,
  timed turns).
ASKED-AS: many programs one processor turns slices seems at once scheduling waiting your turn

ESSENCE: every program is given its own clean map of memory,
  numbered from zero, and the machine quietly translates each
  address to wherever the real thing sits — or fetches it from
  disk if it is not in memory at all.
ROOT: this file / processes are walled rooms, and the wall is
  built out of this translation.
CANNOT: no two programs colliding in memory neither can name. No
  free translation, either: when real memory runs out the machine
  starts trading with the disk, and a fast program becomes a
  waiting one without changing a line.
THREAD: post (a box number that hides the real address), theatre
  (everyone believes they are centre stage), banking (your
  balance is not particular coins in a drawer).
ASKED-AS: each program own memory map addresses swap disk running out slow paging private

ESSENCE: the same trick played one level up: a whole machine, or
  a whole packaged world with its own files and libraries,
  running inside a real one. It lets a program carry its
  surroundings with it, so it meets the same world everywhere it
  runs.
ROOT: computer science / any machine can imitate any other; this
  file / the referee can hand out imaginary machines as easily as
  real turns.
CANNOT: no escaping the real machine underneath — its speed,
  memory and failures are still yours. No isolation as strong as
  a separate machine; a shared floor is still a shared floor.
THREAD: theatre (a stage set that travels with the company),
  shipping (a container that fits every lorry and ship), tents (a
  carried indoors).
ASKED-AS: one machine pretending many virtual container image same everywhere separate boxes inside computer

ESSENCE: a disk holds numbered blocks and nothing else. A file —
  a named thing, with a size, read from beginning to end — is an
  invention laid on top, held together by tables the system keeps
  about which blocks belong to whom.
ROOT: computer science / a layer keeps a promise and hides its
  workings.
CANNOT: no file without a record of its blocks; lose that record
  and the data is present but unreachable. No guarantee its
  blocks sit together, which is why reading "in order" can still
  mean the disk jumping about.
THREAD: libraries (a bound book, and a catalogue saying where),
  warehouses (an order assembled from scattered bins), music (an
  album is a name over separate tracks).
ASKED-AS: file blocks on disk saved name size pieces scattered where stored table lost

ESSENCE: names are arranged as a tree, so every thing has exactly
  one path from the root and no two things share it. The tree is
  not for the machine, which is content with numbers; it is so
  that people and programs can agree where anything is.
ROOT: computer science / arrangement is what makes finding
  possible; language / a name must be unambiguous to be useful.
CANNOT: no two files with the same full path — the path IS the
  name. No finding anything in a flat heap of a million names;
  hierarchy is what makes a name sayable, guessable and
  searchable.
THREAD: addresses (country, city, street, number), biology
  (kingdom down to species), families (a surname line, branching).
ASKED-AS: folders within each other path tree root directory where is it saved full name

ESSENCE: deleting usually removes the name, not the contents. The
  blocks are simply marked free, and until something else is
  written over them the data is still lying there, readable by
  anyone who looks past the index.
ROOT: this file / a file is a name plus a record of blocks, and
  removing the record is cheaper than scrubbing the blocks.
CANNOT: no erasure by deletion — that is why recovery tools work
  at all, and why a sold disk can betray you. No certainty of
  erasure without overwriting, and on some storage not even then.
THREAD: libraries (a card pulled from the catalogue, the book
  still on the shelf), paper (crossing out is not shredding),
  memory (forgetting a name is not losing the face).
ASKED-AS: deleted file still there recover undelete name removed blocks remain wiped shredded really

ESSENCE: "saved" usually means "handed to a buffer". The words
  are in memory, on their way, and the power going out now loses
  them. Truly on the disk means having asked for it and waited —
  which is slow, which is why almost nothing does it by default.
ROOT: this file / writing to a disk is a journey, and journeys
  are batched to be affordable.
CANNOT: no durability without the wait; speed here is bought with
  exactly the risk you are trying to avoid. No knowing from
  inside a program that a write reached the platter unless it
  asked and the answer came back.
THREAD: post (a letter in the pillar box is not delivered),
  banking (a payment shown as pending), promises (said is not
  done).
ASKED-AS: saved but lost power cut buffer not written yet flushed really on disk

ESSENCE: every act on a file is checked against who is asking:
  may this one read it, change it, run it? Security at rest is a
  small question asked at every single act, not a door locked
  once at the start.
ROOT: this file / the operating system referees; law / rights
  attach to particular persons and things.
CANNOT: no protection from a check made once and then trusted
  forever; the check belongs at each act. No help from any of it
  where everything runs as the owner of everything.
THREAD: banks (a signature checked at every withdrawal),
  buildings (keys per door, not per building), libraries
  (reference only, lending, restricted).
ASKED-AS: permission denied who can read write open locked owner access rights every time

ESSENCE: run any data through a fixed recipe and you get a short
  fingerprint. The same data always gives the same one; a
  one-letter change gives a completely different one; and going
  backwards from fingerprint to data is impractical.
ROOT: mathematics / a many-to-few mapping can be easy forwards
  and hopeless backwards.
CANNOT: no proving two files are identical without comparing
  them, but matching fingerprints make a difference vanishingly
  unlikely. No avoiding collisions in principle — there are more
  possible files than fingerprints, always.
THREAD: fingerprints (small, unique enough, useless for
  rebuilding the person), seals (a broken one shows tampering),
  weighing (a quick check that the sack was not opened).
ASKED-AS: fingerprint checksum same file changed one letter completely different cannot reverse quick check

ESSENCE: anything sent across a shared wire can be read and
  altered by whoever carries it. Privacy and identity are not
  properties of the wire — they are built on top, by scrambling
  the contents and by proving who the other end is.
ROOT: this file / a network is strangers passing messages, and
  strangers may read what they carry.
CANNOT: no secrecy on a public path without scrambling. No
  security from scrambling alone, either — an encrypted
  conversation with an impostor is perfectly private and
  completely lost; the identity check is the other half.
THREAD: post (a postcard versus a sealed letter), law (a signed
  and witnessed deed), speech (a whispered secret to the wrong
  person).
ASKED-AS: anyone can listen wire shared encrypted padlock who am i talking to certificate

ESSENCE: a network is not a wire between two programs. It is a
  chain of strangers carrying messages that may be dropped,
  delayed, duplicated or reordered. Reliability is something
  built on top; it is never a thing you are given.
ROOT: physics / a signal crossing distance through many hands has
  many chances to be lost.
CANNOT: no network call that cannot fail. No telling a lost
  request from a lost reply — the caller sees the same silence
  either way, and the work may or may not have been done.
THREAD: post (letters lost, delayed, doubled), rumour (a message
  across many mouths), sailing (a signal that may not be seen).
ASKED-AS: network message lost dropped delayed connection failed did it arrive unreliable internet unsure

ESSENCE: a message is chopped into small packets that travel
  independently, possibly by different routes. They arrive when
  they arrive. Putting them back in order and noticing what never
  came is work that somebody must do.
ROOT: this file / a network is unreliable message passing, and
  each piece is passed separately.
CANNOT: no assuming arrival order matches sending order. No
  reassembly without numbering — an unnumbered stream cannot be
  repaired, only taken as it comes.
THREAD: post (a set of parcels arriving over several days),
  building (materials delivered out of sequence), music (parts
  posted separately to be scored together).
ASKED-AS: packets pieces arrive out of order numbered reassemble different routes missing chopped up

ESSENCE: people use names; machines need addresses. Before any
  connection there is a lookup — a question to a directory that
  turns a name into a number. It is a step, it can be slow, it is
  cached, and it can be wrong.
ROOT: language / a name must be resolved to a thing before the
  thing can be reached.
CANNOT: no reaching a name directly; the translation is a real
  step with real failures. No instant change of a name's meaning
  either — old answers sit in caches everywhere, so the world
  moves over to the new address gradually.
THREAD: post (a name looked up in a directory to get an address),
  telephones (a phone book before a call), shops (a brand name
  resolved to an actual branch).
ASKED-AS: website address looked up phone book translation before connecting typed words into numbers

ESSENCE: two different things get called speed. Bandwidth is how
  much arrives each second; latency is how long the first bit
  takes to come. A wide pipe with a long wait is excellent for a
  film and terrible for a conversation.
ROOT: this file / carrying more and arriving sooner are different
  physical questions.
CANNOT: no fixing a wait by widening the pipe — width moves more,
  it does not move sooner. No help from bandwidth for a small
  message; there, the wait is the entire cost.
THREAD: post (a lorry of letters versus a phone call), water (a
  fat pipe still takes time to reach the tap), roads (more lanes
  do not shorten the drive).
ASKED-AS: fast internet slow ping lag download speed waiting first response wide pipe delay

ESSENCE: every question that must go and come back costs at least
  the time light needs for the journey, twice. Machines have got
  faster by enormous factors; that distance has not shrunk at
  all. So the cure is asking fewer times, never asking faster.
ROOT: physics / nothing outruns light, and the distance is
  geography.
CANNOT: no beating the round trip with better code or newer
  hardware. No chatty design across a distance — a hundred small
  questions is a hundred journeys, however small each one is.
THREAD: conversation (the pause on a call across an ocean), post
  (letters back and forth versus one full letter), shopping (one
  list beats twenty trips).
ASKED-AS: back and forth trip delay far away distance light speed too many requests

ESSENCE: two machines that have never met can work together only
  because both sides agreed beforehand on the shape of the
  messages and the order of the turns. The agreement is the whole
  connection; without it the wire carries nothing but noise.
ROOT: language / shared grammar is what makes sound into speech.
CANNOT: no communication without a shared format — an unagreed
  message is not misread, it is unreadable. No changing a
  protocol alone; both ends must move together, which is why old
  formats live so very long.
THREAD: language (grammar both speakers hold), music (an agreed
  tuning before anyone plays), law (contracts fixing form and
  sequence).
ASKED-AS: protocol agreed format both sides understand rules of talking message shape standard old

ESSENCE: a structure in memory is held together by addresses that
  mean nothing anywhere else. To travel, it must be flattened
  into a plain stream of bytes and rebuilt at the far end — and
  both ends must agree exactly how.
ROOT: this file / memory addresses are private to one program's
  map.
CANNOT: no sending a shape as it sits in memory; the links point
  at rooms the other machine does not have. No rebuilding what
  the sender did not include — anything implied by context is
  lost in the flattening.
THREAD: furniture (flat-packed to travel, rebuilt with
  instructions), music (a performance written down to be played
  elsewhere), recipes (a dish sent as words, not as dinner).
ASKED-AS: sending a structure across flatten into bytes rebuild other end pointer means nothing

ESSENCE: a call across a network is written to look like a call
  inside your program, and it is nothing like one. It can be slow
  by a factor of a million, it can half-happen, and it can fail
  in ways a local call never invents.
ROOT: this file / networks lose, delay, duplicate and reorder,
  while a local call simply runs.
CANNOT: no hiding a network behind a familiar shape — the
  differences leak out as timeouts, partial work and duplicates.
  No pretending it is fast: a loop that was free becomes a
  disaster when each turn crosses a wire.
THREAD: shops (asking the back room versus reaching the shelf),
  conversation (a letter is not a word in the same room), travel
  (a step versus a flight, both called "going there").
ASKED-AS: looks like calling a function but goes over the network slow fails differently

ESSENCE: client and server name who is asking and who is
  answering in one exchange — not what kind of box it is. The
  same program is a server to one and a client to another, minute
  by minute.
ROOT: this file / a protocol defines turns, and a role is a
  position in the turns.
CANNOT: no reading a system's shape from its hardware; roles
  belong to conversations. No server without an asker — nothing
  serves unprompted, which is why an unused server looks exactly
  like a broken one.
THREAD: shops (a shop is a customer of its suppliers), language
  (speaker and listener swap every turn), medicine (a doctor who
  is someone else's patient).
ASKED-AS: client server who asks who answers role not machine both at once request

ESSENCE: if a server remembers nothing between requests, any copy
  of it can answer any request. Add ten, remove three, lose one
  to a fire — nothing that mattered was inside them. Memory is
  what makes a machine irreplaceable.
ROOT: software development / state is where difficulty lives, and
  here it is also where inflexibility lives.
CANNOT: no free replacement of a machine holding something no
  other machine has. No abolishing state, either — it moves
  somewhere shared, and that somewhere becomes the limit and the
  weak point.
THREAD: shops (any till serves any customer), taxis (any driver,
  any fare), teaching (a supply teacher can take the class if the
  plan is on paper).
ASKED-AS: server remembers nothing each request alone add more copies any one answers scaling

ESSENCE: work does not arrive smoothly. A queue lets a fast,
  bursty sender hand off to a steady worker without either
  waiting on the other — turning a spike into a slightly longer
  wait instead of a collapse.
ROOT: this file / rates differ, and something must hold the
  difference.
CANNOT: no queue that rescues a worker who is slower than the
  sender on average — then the line grows forever and the queue
  has only delayed the failure. No unbounded queue that is safe;
  a line with no limit hides the overload until the memory is
  gone.
THREAD: shops (a checkout line absorbing the lunchtime rush),
  water (a tank between pump and tap), post (a sorting office
  holding the Christmas surge).
ASKED-AS: queue line waiting backlog buffer rush hour smooths bursts pile up grows forever

ESSENCE: since silence is indistinguishable from slowness, every
  remote wait needs a deadline chosen in advance. The deadline
  does not discover the truth — it decides how long you are
  willing to not know, and then lets you act.
ROOT: this file / a lost request and a lost reply look the same
  from where you stand.
CANNOT: no waiting without a limit unless you accept being stuck
  forever. No timeout that is right: too short abandons work that
  would have finished, too long ties up everything behind it. You
  are choosing which error to make.
THREAD: meeting someone (you leave after twenty minutes), post (a
  claim made after two weeks), medicine (a decision made before
  the results arrive).
ASKED-AS: waiting how long give up deadline hangs forever no answer decide unknown cut

ESSENCE: when something slows down, everyone retries — and the
  retries land on the thing that was already struggling. The
  cure becomes the disease: a system that would have recovered is
  finished off by its own clients trying to help.
ROOT: this file / retries are the answer to lost messages, and
  answers applied by everyone at once become a crowd.
CANNOT: no safe retrying without waiting longer each time and
  spreading the attempts out; identical rules make everyone knock
  in unison. No recovery for a service whose queue refills faster
  than it drains.
THREAD: crowds (everyone leaving by one exit at once), phones (a
  ticket line redialling in unison), traffic (a jam that reforms
  behind itself).
ASKED-AS: everyone retries at once makes it worse pile on recovering server falls again

ESSENCE: a database is not just storage. It is a promise-keeper:
  it enforces rules about the data that no single program can
  enforce, because it sits underneath all of them and sees every
  write, including the ones nobody remembered to check.
ROOT: law / a rule kept by a registry beats a rule kept by mutual
  goodwill.
CANNOT: no rule held by every program agreeing to hold it — one
  careless writer voids it for everyone, forever. No repairing
  broken data from outside once several programs have built on
  it.
THREAD: law (a land registry rather than neighbourly promises),
  weights (a certified scale above any shopkeeper), banking (the
  bank's ledger, not the customers').
ASKED-AS: database rules enforced storage keeps data correct many programs writing one guard under

ESSENCE: a transaction makes four promises: all of it or none of
  it; the rules still hold at the end; two at once behave as
  though one went first; and once confirmed, it survives the
  power going out. Those four together are what let money move by
  machine.
ROOT: this file / a database keeps what programs cannot;
  accounting / an entry has two sides and both must land.
CANNOT: no half a transfer surviving a crash — the missing half
  is the whole disaster. No confirmed-then-forgotten write; a
  promise that dies with the power was never a promise.
THREAD: accounting (double entry balances or is void), law (a
  deal signed by both or by neither), ceremony (it completes, or
  it did not happen).
ASKED-AS: all or nothing transfer money crash halfway saved confirmed survives power cut promise

ESSENCE: an index is a second arrangement of the same facts, kept
  so that questions can be answered without reading everything.
  It is paid for at every write, because every change must now be
  recorded twice.
ROOT: computer science / arrangement is work stored up in
  advance, and stored work must be maintained.
CANNOT: no free reading — every index makes writing slower and
  takes space. No help from an index for a question it was not
  built for; the wrong index costs everything and gives nothing.
THREAD: books (the index at the back, built by hand), libraries
  (a card catalogue maintained daily), shops (a stock list
  updated at every sale).
ASKED-AS: index faster lookup search slow query writing costs extra space back of book

ESSENCE: store each fact in exactly one place, so a correction
  happens once and no two copies can disagree. Then, when reading
  becomes too expensive, deliberately keep copies again —
  accepting the risk of disagreement in exchange for speed.
ROOT: this file / a fact with two homes drifts; and reading
  scattered facts costs journeys.
CANNOT: no two copies of a fact that stay equal by good
  intentions. No fast read of a fact scattered across many tables
  without either joining work or a kept copy — you are choosing
  which cost, not avoiding it.
THREAD: records (one address book, not five), cooking (a master
  recipe versus cards in every drawer), law (one register of
  title, amended once).
ASKED-AS: same fact stored twice copies disagree one place update everywhere duplicated speed reading

ESSENCE: when the data outgrows one machine, it is split by some
  key — customers A to M here, N to Z there. Each machine is now
  small again, and every question that crosses the split has
  become expensive or impossible.
ROOT: craft / division of labour, applied to facts rather than
  hands.
CANNOT: no splitting without choosing what to split by, and that
  choice decides which questions stay cheap forever. No easy
  counting, joining or transacting across the boundary — the
  split is real, not cosmetic.
THREAD: libraries (branches by subject, and the book you want is
  in the other one), post (sorting by district), schools (classes
  by year, and the pupil who needs both).
ASKED-AS: too big for one machine divided by customer letter range crossing the boundary

ESSENCE: keep copies on several machines and the death of one
  stops nothing. The same act creates the deeper problem: copies
  must be kept in step, and while a change is spreading, two
  honest machines hold two different truths.
ROOT: computer science / redundancy is what lets a message
  survive damage — at the cost of length, and here of agreement.
CANNOT: no survival of machine death without copies. No copies
  that are always identical — updating several things at a
  distance takes time, and during that time they differ.
THREAD: the body (two kidneys), law (deeds in triplicate,
  amended one at a time), families (the same story told slightly
  differently in two houses).
ASKED-AS: copies on several machines one dies another has it kept in step disagree

ESSENCE: when the link between two halves of a system breaks —
  and it will — you must choose: keep answering and risk the two
  sides giving different answers, or refuse to answer until they
  can talk again. There is no third door.
ROOT: logic / two parts that cannot hear each other cannot agree
  on anything new.
CANNOT: no system that is both consistent and available while
  split — not merely hard: impossible. No dodging the choice by
  not deciding; a system that never chose has chosen the worse
  one by accident.
THREAD: law (two courts cut off from each other), navigation (two
  ships out of contact holding one plan), families (two branches
  deciding in isolation).
ASKED-AS: connection cut between halves keep answering or wait different answers split choose tradeoff

ESSENCE: the usual settlement is to answer now and agree later:
  copies are allowed to differ for a moment and then converge.
  That moment is real, and everything above must be built knowing
  a reader may see yesterday's answer.
ROOT: this file / during a split, or during any spreading change,
  copies differ.
CANNOT: no "later" without a rule for settling disagreements —
  last-writer-wins, merge, or a human. No hiding the window from
  the user; a design that assumes reads are always current will
  be wrong in public.
THREAD: banking (a payment showing up tomorrow), post (a change
  of address in transit), rumour (the news reaching one village
  before the next).
ASKED-AS: catches up later agree eventually delay showed old value refreshed moment behind copies

ESSENCE: one machine is either up or down. Many machines are
  mostly up: this one slow, that one unreachable, a third
  answering with stale data. Partial failure is the normal
  weather, not the emergency.
ROOT: chance / with many parts, the chance that all are well at
  once falls away quickly.
CANNOT: no all-or-nothing failure in a system of many parts. No
  telling a dead machine from a slow one — you can only choose
  how long to wait, and be wrong sometimes in both directions.
THREAD: the body (an organ failing while you walk about), cities
  (a power cut on one street), teams (two members unreachable and
  nobody agreed they had left).
ASKED-AS: some parts down others fine partly broken slow unreachable half working many machines

ESSENCE: every machine has its own clock, and clocks drift, jump,
  and get corrected backwards. So "this happened before that"
  cannot be settled by comparing two machines' timestamps — the
  ordering has to be carried by the messages themselves.
ROOT: physics / there is no shared instant to appeal to, only
  signals that take time to arrive.
CANNOT: no shared "now" across separated machines. No ordering
  two events by their stamps when the clocks were never the same
  clock; a later stamp may belong to the earlier event.
THREAD: history (events dated from separate calendars), law (two
  witnesses and two wristwatches), navigation (longitude waited
  on a clock that could travel).
ASKED-AS: clock time wrong different machines timestamps which happened first drift order events unreliable
