# HANDOFF — read this, then DIRECTION.md, then FIRST_RIBBON.md

## Where it stands
5,368 pieces of knowledge in docs/fabric_phylums/, 5.0 MB of
plain text across 164 files, 160 subjects, 12,866 words, 4,682
laws parsed out of the entries' own CANNOT lines.

Three claims in the previous version of this file were re-run and
did not hold. They are corrected here rather than deleted, because
a wrong number that gets quietly removed gets believed again next
time.

- "loads in a second" — it is 8.8 seconds, warm. Measured
  repeatedly, not once.
- "49,519 links between themselves" — the code builds no
  entry-to-entry links at all. It builds 52,022 entry-to-SUBJECT
  links, and every one of those fans out to every entry in that
  subject: 1.7 million effective hops.
- "a figurative question answered correctly" — "why do people say
  time flies" lands in flight and lift. It does not hold.

WORKS (re-run this session, not taken on trust):
- core.py loads the whole corpus indexed and bitwise.
- os_fabric.py routes bread, whip and sky correctly.
  BUT: a question reaches 1,279–2,271 of the 5,368 entries. That
  is 24–42% of the fabric. It is a broadcast, not routing, and the
  ranking afterwards is doing the work. This is the same fault as
  the onions/mourning-rites miss — not a separate bug.
- follower.py + interpreter.py run written procedures. Verified:
  347+288=635, 1204-377=827, and binary 1100+111=10011 and
  101+11=1000, all followed from written rules. Asked to
  multiply, it refuses and names the act it lacks. (The binary
  claim only holds for binary input; feeding it decimal returns a
  wrong number without complaint. Worth a wall.)
- maker.py eliminates by law and reports both what stands and
  what closed.
- first_ribbon.py now parses, by elimination. See below.
- fabric_persist.py runs unattended. It had been DEAD since beat
  68670, killed by a rename failure. Fixed and restarted.

DOES NOT WORK:
- Routing is a broadcast (above). Ambiguous words still land
  wrong (onions/cry -> mourning rites).
- Grouping is thin on sentences whose word pairs are rare in the
  corpus, so long questions over-stage and hundreds of readings
  survive.
- No conversation. No world building.

## The rules that were broken repeatedly — do not break them
1. Knowledge is the processor. CORRECTED by Joe, 2026-08-29: the
   test is not that no domain word may appear in code. That test
   is wrong and it produces contorted code. The test is
   PERMISSION — if the knowledge permits a move, the move is
   allowable in code. The defect is deciding something the
   knowledge has not sanctioned, or overriding what it says.
1a. What a ribbon is, in Joe's words, because the previous build
   had one role out of five: a ribbon is a PROGRAM, a QUERY, a
   CARRIER OF DATA, and an EXCHANGER OF POSSIBLE AND IMPOSSIBLE
   — all at once. Ribbons come from outside (a person) and from
   inside (the fabric's own musings), and the internal ones are
   supposed to be persistently running to discover new knowledge.
1b. The point of the whole thing: when this operating-system
   ribbon is done it should be able to CREATE ANYTHING — the way
   a large model does, at a tiny fraction of the energy. Parsing
   is a means to that, never the goal.
2. Plain speech to Joe. No invented vocabulary, no metaphor, no
   fenced theatre. He has corrected this more than ten times.
3. Never report a passing test as a working system. Ask: does it
   run when I am not typing?
4. Read the fabric's own walls before designing anything. They
   rule out routes and save nights.

## The first ribbon — built 2026-08-29, and how to check it
It parses by elimination, on the same engine as everything else.
eliminate.py is that engine, extracted so there is one: stage,
grip, kill, survive. The walls live in
docs/fabric_phylums/174_how_a_sentence_is_built.md.

  python fabric/first_ribbon.py "the dog bit the man"
    groups: the dog | bit the man
    18 staged, 16 closed, 2 stood, doing 'bit', 'the dog' under it

Two proofs were run, both reproducible:
- Change "three sightings" to "twelve" in 174 and the grouping
  changes with NOTHING in the code touched. The settings are read
  out of the entries at run time.
- Remove 174 and the ability dies naming all four things it
  lacks, instead of defaulting. Put it back and it returns.

Still open on it: sentences whose word pairs are rare in the
corpus group badly and leave dozens of readings standing. The fix
is more walls in 174, not more code — that is the whole point of
where it was put.

Two things learned the hard way, both recorded in 174 so they are
not re-tried:

- A wall must be written BARE. An explanation inside a wall puts
  the wall's own subject in front of it and it then grips on
  itself. One wall silently never fired for this reason.
- "No group hanging under one the writing never sets beside it"
  looks right, is measurable, and killed every reading of every
  sentence over two groups. It contradicts a wall that outranks
  it: composition is compulsory, so a reading must be able to join
  words the corpus never put in one line. Company decides a group;
  it may not decide a join.

And one about the life, not the language: reading its own question
was unbounded work inside a beat that has to be bounded. It wedged
the whole life — CPU burning, no beats, deaf to the stop signal,
because STOP is only checked between beats. How much may be staged
at once is now read from 174 as knowledge (four groups), and what
could not be staged is named. Anything added to a beat must be
bounded before it goes in.

## Next build
The ribbon has to MAKE, not only read. Reading a sentence is the
means; the goal in Joe's words is that anything can be made on
this, cheaply. The sense-from-company and ready-made-chunk walls
in 174 are written and not yet used by anything.

Data never enters the knowledge. It rides in on the ribbon —
including anything fetched from the internet — is used or added
to, and leaves. That is why the fabric stays small.
