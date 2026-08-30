# HANDOFF — read this, then DIRECTION.md, then FIRST_RIBBON.md

Written 2026-08-29, later than the version it replaces. Every number
below was re-run in the session that wrote it. The version before
this one carried numbers that were wrong — corpus size, corpus bytes,
two of the three vector counts, and one claim about what the parser
does. Those are corrected here, and the same warning applies to this
file: re-run it.

## Numbers, re-run

- 5,427 entries in docs/fabric_phylums/, 166 files, 3.7 MB of plain
  text, 19,472 distinct words. (Was written as 5,382 / 160 / 5.0 MB /
  12,866. All four were wrong.)
- core.py loads and indexes it in 8.0s.
- vectors: 2,050 down, 2,247 across, 1,558 floors, built in 10.4s.
  (Was written as 1,989 / 2,808 / 1,552. "Across" was out by 561.)
- core.laws parses **0** laws. All 5,427 denial lines were removed on
  purpose and nothing has been written to replace that parse path, so
  core.judge() cannot fire. Anything relying on it is inert.

## What was done this session — the reading

The job is communication: cognition and syntax before any assembly.
Nothing can be told what to build until it can say what it was told.

**A bench now exists: `fabric/reading_test.py`.** Thirty sentences,
each with what it must turn on and what it must be about, written
down before the change that was graded against them. Fifteen were
written after the rule was settled and were never looked at while
settling it. Run it before and after anything on the language side.
This is the thing whose absence let a grouping change silently break
"the dog bit the man".

**Baseline when the session opened: 5 of 15.** "how do I sharpen a
knife" turned on "I". "the dog bit the man" turned on "man". "salt
melts ice" turned on "salt".

**Now: 15/15 on the settled set, 13/15 held out.**

The cause was in the knowledge, not the code. 174 said the doing is
"the group whose words most often sit straight after the frame's
pointers", and the code was faithfully running it. That is the
contrast upside down: a pointer arrives FOR a content word, so
counting what sits after a pointer ranks the THINGS first and the
doing last. Turned round it is not a count at all:

  a group is a run of frame words carrying one content word, so a
  group of one word arrived alone, and **the doing is the group that
  arrived alone**.

Split by which half decided, because they are not the same strength:

  settled by contrast (a group arrived alone)   20 of 20 correct
  settled by the fallback rate                   9 of 10 correct

The reading now says which of the two settled it, and says when the
deciding rate rests on too few sightings to be a habit. A reading
that hides that is claiming the stronger of the two.

Also corrected: what a sentence is ABOUT is now each group's head,
not every word outside the frame. The old rule lost any subject
common enough to have entered the frame — in a fabric written about
physics and cooking, "the fire heated the water" came back as not
being about water.

The pointers are counted, never listed: a frame word is a pointer
when what follows it comes from outside the frame more than three
quarters of the time. That derivation puts an, a, the, every, its,
same, no, two at the top and nothing was hand-picked. Measured
sensitivity: any cut from 0.70 to 0.80 gives the same score, so it is
a plateau and not a fitted edge.

## Corrections to what the last handoff said

- "first_ribbon.py parses by elimination against 174" — half true and
  the half that failed is the important one. The NESTING is genuinely
  eliminated: "the dog bit the man" stages 192 readings and 144 are
  closed by 174's HOLDS lines (self-hanging, loops). The DOING was
  never eliminated at all — it was picked by a ranking, and the
  ranking was the falsified rule. Elimination decided the shape and a
  false count decided the subject.
- "wanting.py is the only thing whose output is not in the corpus" —
  still true, and it is the right shape, but two of its four sample
  sentences read wrong when the session opened. Being the right shape
  and being correct are different claims.

## The rules — do not break them

1. Knowledge is the processor. The test is PERMISSION: if the
   knowledge permits a move, the move is allowable. The defect is
   deciding something the knowledge has not sanctioned, or overriding
   it. Corollary learned this session: when the reading is wrong,
   look in the knowledge first. The doing rule was wrong in 174 and
   the code was innocent.
2. A ribbon is a PROGRAM, a QUERY, a CARRIER OF DATA, and an
   EXCHANGER OF POSSIBLE AND IMPOSSIBLE, all at once.
3. The point: it should be able to CREATE ANYTHING at a tiny fraction
   of the energy. A build that answers instead of makes is off the
   heading.
4. Knowledge is a coordinate and a vector. The links are the vector.
5. THE FINGER. A thing is a finger, and one, and skin, and a way to
   point, all at once, until something says not that.
6. Plain speech to Joe. No invented vocabulary, no metaphor.
7. Never report a passing test as a working system.
8. Run reading_test.py before and after any language change. A bench
   that is not run is not a bench.

## A RULE I WROTE AND HAD TO RETRACT — read this one

I reasoned my way to a rule for telling how two things sit together —
one bears the other when its share of the shared company runs more
than twice the other way — wrote it into 174 as an unmarked HOLDS
line, and shipped it. It lasted one commit. Falsified: animal/dog
scores 0.57 against 0.07 and music/salt scores 0.57 against 0.23, a
true kind-relation and an unrelated pair with the same number. It was
reading which of the two words is commoner.

Writing my own constructs into the knowledge is PERMITTED — the
standing word is "if they work for you, have at it". Permission is not
ratification. The failure was not the writing, it was the missing
name: unmarked in 174 it reads as the fabric's rule instead of mine.
Mark them, and try to break them the same day.

## RANKING IS THE TELL

If the work is improving which entry comes back, it is retrieval.
Measured: five of five answers the old answering path gave were
already written in the corpus before the question was asked. Cutting
a stored set can only return a member of it — arithmetic, not a
quality problem.

The page now leads with what it HEARD, and the old answering path is
below a line that says what it is. It was not deleted, because
deleting it hides the finding instead of recording it.

## THE WORD IS ASSEMBLER, NOT COMPUTE (Joe)

An assembler takes parts and a specification and puts the parts
TOGETHER. An arrangement is never a member of the parts list. That is
the property every failed build lacked. Candidates are not things to
be found — they are ARRANGEMENTS, generated by combination, never
stored, always larger than the parts.

The reading is the specification an assembler would take. It is now
correct on ordinary sentences, and it returns no entry.

## THE RIBBON IS BUILT — all six pieces

FIRST_RIBBON.md named the shape: group the sentence, build a nesting,
take word behaviour from distribution, produce the sense from the
company at hand, carry chunks, keep the contrast. All six run.

- GROUPING works. A group is frame words carrying one content word.
- NESTING carries ROLES now — the group before the doing is the doer,
  the one after is the done-to. Written in 174 as knowledge about
  THIS language, not as a fact about language. Without it "the dog
  bit the man" and "the man bit the dog" were the same reading.
- CONTRAST finds the doing: the group that arrived alone. 20 of 20
  where a contrast exists.
- SENSE is produced from company, never fetched. light with star and
  sky gives stars, cloud, gas, gravity, black; with weight and heavy
  it gives energy, rock, wheels, steel.
- CHUNKS are carried whole: public health, martial arts, blood sugar.
- CONTENT is assembled. Where two of the sentence's own words meet,
  computed against the pair in hand. Across eight pairs the best
  single entry in the corpus held at most 4 of the 6 words produced,
  usually 3 — it is not a member of the parts list. Asked twice it
  goes a step out: what stands with the ground but with neither of
  the pair.

## THE NUMBERS, AND WHICH ONE TO QUOTE

  being told what to do   29/30   (14/15 of it held out)
  the doing               63/70   (40 of them reshaped by rule)
  is-or-acting            43/60   (hand-labelled; always-ACT scores 36)

QUOTE THE FIRST ONE. Being told what to do is what the ribbon is for —
everything else reads sentences ABOUT things. It was 3 of 15 when that
bench was first built and the fabric could not read an instruction at
all: every rule in 174 looked for the doing anywhere but first,
because a statement puts its doer there.

An ORDER names no doer — the one being told is the one who will — so
its doing is the first thing said. It is told from a statement by four
marks, any one of which is enough: a pointer opening a later group, a
constraint hung off it, an asking word that is not first, or any later
group opened by a frame word at all.

THREE BENCHES, and each has caught what the others could not:
  fabric/telling_test.py  30 instructions, half written after the
                          rules were settled and never looked at
  fabric/reading_test.py  70 doing cases, 40 reshaped BY RULE
                          rather than chosen, plus 7 role cases
  fabric/kind_test.py     60 sentences drawn by seed from the
                          fabric's own writing, labelled by hand

RUN ALL THREE BEFORE AND AFTER ANY LANGUAGE CHANGE. Between them they
caught: a chunk rule that took roles 7 to 4, a retraction that took
the reading to 0/70, a merge that read well on statements and took the
reading to 29/70 on questions, and a word-class that gained one case
while costing 37.

## TWO THINGS ABOUT THE FABRIC READING ITSELF

The processor is the knowledge, so writing knowledge changes the
reading. Two separate effects, both measured:

1. DRIFT. Adding one entry to 174 — twelve lines — moved the kind
   bench by three of sixty with the code identical. Benches are not
   comparable across a knowledge edit. Measure both arms against the
   same corpus.
2. EXAMPLES BECOME EVIDENCE, and this one is worse. An illustration
   written into 174 is a sighting like any other. Writing "keep food
   cold" there twice took that pair to the chunk habit floor, the
   grouping carried the whole order as one part, and the very
   sentence used to explain how an order is read stopped being
   readable. WRITE THE RULE, NEVER THE SENTENCE IT APPLIES TO.

## THE FRAME NEEDS SPREAD, NOT JUST FREQUENCY

A word is common for one of two reasons: it is structural, or this
fabric happens to be about it. Frequency cannot tell them apart — both
are frequent — and that is why counting failed for a day. Spread can,
and spread is not a kind of frequency. Across 162 subjects the, a, is,
of and and reach 1.00 of them; water reaches 0.49, air 0.43, mind
0.44, words 0.41.

The frame is now the commonest hundred words that reach more than
three fifths of the subjects. This mattered because a frame word never
closes a group, so the better the corpus covered a subject the less
readable that subject became. All three benches rose at once.

## THE MEASURING INSTRUMENT WAS THE PROBLEM FOR HALF A DAY

Every number on the is-or-acting split was taken against a proxy —
does the sentence contain is/are/was/were anywhere — which calls
"while a thing IS changing state its temperature stops moving" a
sentence about what something is. Two rules were nearly shipped on
that proxy's word and one was nearly rejected on it. Sixty
hand-labelled sentences settled all of it in one run.

Build the instrument before optimising against it. A number from a
proxy you know is wrong is not a measurement.

## Next

1. **The no-contrast doing.** When every group arrives the same way
   the rate decides and reads 9 of 10. THREE routes are now closed
   and filed: doing-endings, the rate over the whole frame, and the
   written form's own inflection (which reads 9 of 10 too, and not
   the same 9).
2. **Kind-relations.** "Is a dog an animal" cannot be answered and
   three routes are closed. The likeliest reading, filed as reasoning
   and not as finding, is that this fabric holds none — it is written
   as essences about how things work, not as a taxonomy.
3. **The turn's words are still mine.** Every sentence saying.py says
   was hand-written by me. The parts are the fabric's and the English
   is not, and that is the honest boundary of what is built.

## The state of the corpus

All 5,427 denial lines were removed on purpose. They were a
hand-written second copy of what each claim already says, and every
failure came from computing on the copy. What a thing holds is
written as a claim (HOLDS lines) and the negative is read off it. Do
not put them back. Note that the nesting elimination runs off HOLDS
lines and works; core.laws is the dead path.

## THE CORRECTION THAT MATTERS MOST (Joe)

"You know knowledge but do you know how to use knowledge."

He typed "hello" into the page. The fabric found its entry on
greetings — which says a greeting carries no subject — and PRINTED
THAT SENTENCE AT HIM. It had the knowledge of how to greet him and
used it as an answer about greeting. That is what a retrieval tool
does.

His own words for why it matters: he collected ten degrees and
watched people who knew less do better, and the epiphany was that it
does not matter what you know, only what you do with it. Knowledge
sitting in a brain is worthless. That is the acceptance test.

## FAILURES ARE THE PRODUCT

Every measured failure goes to the white (99) with what would drain
it. When the possible side is generated rather than stored, the
accumulated closures are the only thing that shapes an answer.

Filed this session: the doing entry DRAINED, with how; a rate taken
over too few sightings; a subject common enough to enter the frame;
the rate taken over the whole frame instead of the pointers. The last
one reads three of fifteen — worse than the error it replaced, which
is exactly the kind of thing that gets rebuilt if it is not written
down.

Watch for a method that half-works because a known signal was
smuggled into it.
