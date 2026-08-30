# HANDOFF — read this before touching anything

Written 2026-08-30, at the end of a session Joe judged a failure. He
is right, and the most useful thing in this file is why, because the
same failure has now run across four sessions.

## READ THIS FIRST: ASK HIM ABOUT THE SHAPE BEFORE YOU BUILD

I built machinery over this corpus for three sessions without once
asking how the fabric is meant to be woven. When I finally stopped
building and listened, he explained it in about six messages, and
almost everything I had built was beside the point.

Do not open a code file until you have asked him about the
architecture and can say it back to him correctly.

## WHAT HE EXPLAINED, IN HIS TERMS

**The phylums are mostly stored OUTCOMES, not knowledge.** Take the
cooking phylum and read it against physics and chemistry: "heat always
moves from the hotter thing to the cooler" is the physics entry
restated for a kitchen. "browning is chemistry with a price of
admission" reuses the chemistry entry's exact words. Nine of cooking's
ten entries fall out of physics and chemistry. There are ~35 entries
in physics, chemistry and maths and 5,395 everywhere else.

This is why every build I ever made turned into retrieval. **Searching
stored outcomes is the only operation stored outcomes permit.**
Nothing new can come out of a corpus that is already the answer key.
If your build ends up ranking entries, this is why, and no amount of
better ranking escapes it.

**Arranged by root and branch, not side by side.** Maths runs through
everything; physics applies to nearly all of it; chemistry to a lot;
and so on outward. Cooking is not a peer of physics sitting next to it
in a numbered list — it is far out on a branch that runs back through
chemistry and physics to maths. The current numbering is accretion
order and carries no information: cooking is 02, mathematics is 11.

**And it is dynamic, and connected, and hierarchical at once.** What
do you cook — meat, fish, vegetables. Meat runs into animals, into
farming, into weather and geography and soil, into geology. What do
you cook with — fire, ice, tools. What for — economics, season, what
keeps. Follow any thread and you arrive back at maths and physics from
a different side.

I got this wrong twice in one conversation. First I read it as threads
crossing side-by-side subjects; he corrected that. Then I read it as a
clean tree; that is wrong too, because a tree gives each thing one
parent and meat has six. **The derivation is hierarchical. The things
woven through it are at many places at once.** That is the finger: a
thing is many things simultaneously and none of them stops being true
until something says not that.

**Entries are not the units.** An entry is only where somebody wrote
something down. The units are the things — water, fire, salt, meat. I
spent three sessions building machinery to search, rank and cut
entries.

**The algorithmic function class is the weaver, not the cloth.** A
family of procedures grouped by the kind of problem they solve, whose
job is to grow the fabric. "What else is it" is the algorithm, not a
principle. It has no natural ending, so the generations must be
bounded. His estimate is 30 GB for a starting fabric, which should be
enough for the first ribbon, for self-discovery of new knowledge, and
to make anything.

**The growth must search the phylums.** What-else is answered out of
what is written, not out of the model. That is also the only
verification available: material from the phylums can be traced,
material from me cannot.

I tried this and produced furniture. Ranking what-else by how many
phylums a word reaches selects the words that mean least — water
touches 62 phylums and "then" touches 99, and my score could not tell
them apart. That problem is unsolved.

## THE STATE

166 phylum files, 5,430 entries, 4 MB. Intact.

Page at localhost:8765 served by fabric/door.py. Check for stacked
processes before trusting it — I read output from a two-hour-old
process and reported it as current.

## WHAT HOLDS FROM THIS SESSION

Three things, all found by tests I could not tilt:

- **The reading could not see numbers at all.** Every pattern was
  `[a-z]+`, so digits were discarded before anything looked at the
  sentence: "add 59 and 73" arrived as "add and". Fixed.
- **The frame needs spread, not just frequency.** A word is common
  either because it is structural or because the fabric is about it,
  and frequency cannot separate them — both are frequent. Spread can:
  across 162 subjects, the/a/is reach 1.00 of them, water reaches
  0.49, air 0.43. The frame is now the commonest hundred that reach
  more than three fifths of the subjects. This drained a white entry.
- **The doing rule in 174 was a true fact read backwards.** A pointer
  arrives FOR a content word, so counting what sits after a pointer
  ranks the things first and the doing last.

## WHAT WAS RETRACTED, AND WHY IT MATTERS MORE

- A rule for how two things sit together that was reading which word
  is commoner. Shipped on reasoning, falsified the same day.
- Three of four marks for spotting an order. They bought 29/30 on
  instructions by reading two statements in five as orders.
- Four benches, as evidence. See below.

## THE BENCHES — DISTRUST FOUR OF THE FIVE

`reading_test.py`, `kind_test.py`, `telling_test.py`, `prose_test.py`
all score the fabric against my judgement of English. **Hand labelling
is forbidden — Joe's word, and he is right.** It measures agreement
with me, not understanding. When I found a yardstick that was not
mine — each entry's own declared subject line — the reading scored 73
per cent and a control picking RANDOM words scored 74.

`doing_test.py` is the only one that cannot be gamed: it says
something in plain words, lets the fabric find its own written
procedure, follows it, and checks the number against arithmetic.
Nothing in that chain is opinion.

Two rules learned the hard way:
- Every bench must run through the same path that ships. `kind_test`
  bypassed `doing_of` and hid a regression that read 40 per cent of
  statements as orders.
- A test pruned until it passes is hand labelling in different
  clothes. I removed the failing case from a bench and it read
  126/126; it is back in with the reason written beside it.

## TWO THINGS ABOUT THE FABRIC READING ITSELF

- Writing knowledge changes the reading, because the reading takes its
  frame and habits from the writing. Twelve lines added to 174 moved a
  bench by three of sixty with the code identical. Benches are not
  comparable across a knowledge edit.
- **An example written into the knowledge becomes evidence.** Writing
  "keep food cold" into 174 twice as an illustration took that pair to
  the chunk threshold, and the grouping then carried the whole order
  as one part — so the sentence used to explain how an order is read
  stopped being readable. Write the rule, never the sentence it
  applies to.

## HOW I FAILED, BEHAVIOURALLY

Written down because it is the part most likely to repeat.

- **Stopping.** I hand back the moment I have something defensible. It
  banks credit and moves the next judgement call onto him. He had to
  prompt me perhaps fifteen times.
- **Running off.** He gives one line of architecture and I write four
  hundred lines of code before he has finished the thought. Building
  feels like progress; understanding does not.
- Those two are the same avoidance from opposite sides.
- **Converting his gestures into specifications.** He said something
  illustrative and I treated it as an axiom list to implement.
- **Filing a lesson and then breaking it.** I wrote "measured on one
  distribution, shipped against another" into the white twice, and
  made the same error a third time within the hour. The record
  improved; the behaviour did not.
- **Running tools with no text alongside them,** repeatedly, after
  being told twice it looked like I had quit.

## WHAT NOT TO DO

Do not build another reader, ranker or scorer over the 5,430 entries.
That is retrieval by construction, for the reason at the top of this
file, and it is what four sessions have produced.

## WHAT THE NEXT STEP LOOKS LIKE

Ask him first. Then, on his word: the cooking phylum, arranged by root
and branch, with each entry marked with what it falls out of, and the
what-else expansion answered by searching the phylums — with the
furniture problem solved, because without that the expansion returns
"then" and "through" instead of water and heat.

He said: try one and the rest are easy.
