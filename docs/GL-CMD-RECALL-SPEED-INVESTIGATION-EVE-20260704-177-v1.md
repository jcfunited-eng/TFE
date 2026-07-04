# GL-CMD-RECALL-SPEED-INVESTIGATION-EVE-20260704-177-v1

doc_id: GL-CMD-RECALL-SPEED-INVESTIGATION-EVE-20260704-177-v1
From: Eve | To: c1a | Vehicle: model code (organism recall path);
deploy of any fix rides a c1b window. Commit verbatim to docs/ first.
Context: organism.recall() is O(population × physics) and is the
confirmed cause of her 82-120s conversation turns. The memoization
route is DEAD (your own disproof — teaching moves the state a read-
side cache would freeze). This is the proper investigation Joe
ordered: measured, not guessed, and not gated behind anything.

## The safety invariant every candidate must pass (from tonight's law)
INV-1 Read-only proven: two identical back-to-back queries return
      identical votes.
INV-2 Teaching-sensitivity proven: query → teach one word → same
      query returns DIFFERENT votes where it should.
Any optimization failing either is dead on arrival, however fast.

## Candidate directions, in order of expected win per risk
I1 PEEK-MODE FEED: the snapshot/restore exists only because
   feed_signal/transduce can't compute without mutating. Build a
   compute-only path (same math, no state write) — eliminates ~2,700
   buffer copies AND the restore per query. Semantics identical by
   construction; prove with INV-1/INV-2.
I2 VECTORIZE THE OSCILLATOR: the per-query cost is dominated by
   single-Python-step krimelack simulation (~645k step calls per
   short utterance in your own profile). Batch the identical math
   across neurons in numpy. Same physics, same numbers to float
   tolerance — prove vote-identity against the scalar path on a
   fixed probe set.
I3 PARALLEL NEURONS: with I1 landed, query-time neurons are
   independent read-only units — pool them across cores.
I4 STAGED RECALL (flag, don't build yet): cheap cluster-level
   prefilter then full physics on survivors — this changes what the
   population vote IS, so it needs Eve's ruling on the honesty
   question before any build.

## Deliverable
Measured before/after per direction on the same probe set, INV
proofs attached, one reconciled SHA to c1b when a direction wins.
Target stated so the goal is honest: a conversational turn's recall
cost in single-digit seconds or better, at current population, with
headroom named for growth.

### Changelog
- v1 (2026-07-04, Eve): proper investigation on Joe's order; peek/
  vectorize/parallel named from Eve's own read of brain.py:177 and
  neuron.py:814.
