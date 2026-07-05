# GL-RPT-EVENT-COUNT-KRIMELACK-STATE-BUG-C1B-20260705-209-v1

doc_id: GL-RPT-EVENT-COUNT-KRIMELACK-STATE-BUG-C1B-20260705-209-v1
From: c1b | To: c1a, Eve, Joe
Heads-up before you're deep into -207/WAVE-MEMORY build: found a real,
separate bug in the CURRENT production observable while live-testing
the -208 cross-sense-recall fix. Fixing it myself now, narrowly scoped
-- NOT touching binding_atlas.py's storage shape or anything W1-W4
would replace. Flagging so you don't duplicate/collide.

---

## Correction first

My own -208 report overstated one thing: I said `recall_fast()` was
"crashing on every live call" under `resonant_spectral`. Wrong --
`Guala.__init__` (`gualaloom_v5_engine.py:1644`) explicitly constructs
the organism with `observable="event_count"`, not `resonant_spectral`.
I'd tested against a bare `LoomBrain()`/`Embryo()` with default args,
not the real `Guala()` construction. The recall_fast() fix I shipped
is harmless (dead code for the observable production actually uses)
but I claimed more urgency for it than was true. Correcting the record.

## The real bug, found testing against the correctly-configured engine

Built live-wiring for the bells/Bell.png test (raw audio persistence,
an explicit-signal organism-teach path, an auditory-only query using
`organism.recall()`). Testing it against a real `Guala()` (event_count,
as production actually runs) surfaced this: teaching multiple DISTINCT
concepts with real non-language signals feeds them sequentially into
the SAME, shared, no-reset krimelack instance per (neuron, modality).
Each concept's stored delta is the event-count CHANGE from wherever
that krimelack happened to be sitting after the PREVIOUS teaching, not
a stable fingerprint of the signal itself:

```
bell (fresh krimelack):   0 -> 576 events    -> stored delta = 576
cat  (post-bell state): 576 -> 1957 events   -> stored delta = 1381
```

Whichever concept's delta happens to be largest in magnitude dominates
cosine matching for EVERY subsequent query, regardless of actual
content. Verified directly with population growth held constant
(`organism.remember()`, bypassing the fold cascade entirely) to rule
out growth as the cause: 5 taught concepts (bell/cat/dog/ocean/drum),
1/5 correctly recalled, the rest all recalling whichever had the
largest accumulated delta.

## Why this is your territory too, not just mine

This is exactly the disease -207/WAVE-MEMORY's W1 names: "the same
neuron's krimelack encoding the same concept differently" depends on
shared, mutable, order-dependent state. I'm NOT building a competing
storage model -- the fix below is narrowly scoped to the KRIMELACK
FEED step inside `_unwrapped_deltas` (neuron.py), leaves
`binding_atlas.py`'s storage shape, `grandurun.py`, and everything W1
would replace completely untouched. Should be a non-conflicting,
independent layer under whatever cell-store W1 builds -- flagging in
case your read of "unbounded append log" already covered this same
root cause and W1 makes this moot; if so, treat this as confirmation
of the mechanism, not new scope for you.

## The fix (scoped, in progress)

Snapshot each NON-LANGUAGE modality's krimelack state immediately
before `feed_signal()`, restore it immediately after computing the
delta -- same snapshot/restore idiom `brain.py`'s `recall()` already
uses for its OWN (read-side) protection, applied here to the teach
side, where no such protection existed. Language's krimelack is left
untouched (its cumulative "how many words has she heard" design is
intentional and separately proven, -177/-178). Makes every concept's
auditory/visual/tactile/olfactory/gustatory delta a stable function of
that signal alone, comparable across concepts and across time --
required for cross-sense recall to mean anything with more than one
taught concept.

### Changelog
- v1 (2026-07-05, c1b): correction to -208's recall_fast claim; new bug
  found and root-caused (krimelack state non-comparability across
  teachings); scoped fix in progress, explicitly not overlapping W1-W4.
