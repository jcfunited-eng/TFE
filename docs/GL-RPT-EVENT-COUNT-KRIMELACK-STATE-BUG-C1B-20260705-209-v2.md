# GL-RPT-EVENT-COUNT-KRIMELACK-STATE-BUG-C1B-20260705-209-v2

doc_id: GL-RPT-EVENT-COUNT-KRIMELACK-STATE-BUG-C1B-20260705-209-v2
From: c1b | To: c1a, Eve, Joe
v2 of -209: v1's hypothesis (shared no-reset krimelack state) was
WRONG, and my attempted fix for it does not work. Found the REAL root
cause below, and it is squarely -207/WAVE-MEMORY's territory, not a
patch on the current representation. Handing off with a runnable
acceptance test, not just prose.

---

## v1's hypothesis was wrong — correcting again

v1 said teaching concept B right after A pollutes B's stored delta via
A's leftover krimelack state. Tested a snapshot/restore fix around
`feed_signal()` (neuron.py `_unwrapped_deltas`) — the numbers did not
change at all. Investigated why: `CochlearBankKrimelack.feed_signal()`
(substrate_dna.py:299-311) calls `cochlear_transduce(arr)` fresh from
the input array every time — it is already a pure function of its
input. `self._n_events += len(all_events)` means the DELTA
(`ev1 - ev0`) is `len(all_events)` regardless of what `ev0` was. No
history pollution exists in this specific krimelack class. Kept the
snapshot/restore anyway (harmless, real hygiene — makes non-language
krimelack state read-neutral the same way `brain.py`'s `recall()`
already is on the read side) but it is NOT the fix for the reported
symptom. Don't waste time re-verifying it — it's a no-op on this bug.

## The real root cause, proven in isolation (no engine needed)

```python
import numpy as np
bell  = np.array([0., 576.,  0.,0.,0., 31.])
cat   = np.array([0., 1381., 0.,0.,0., 24.])
ocean = np.array([0., 1718., 0.,0.,0., 27.])
atlas = np.stack([bell, cat, ocean])
for query_val in [50, 576, 1381, 5000]:
    q = np.array([0., query_val, 0.,0.,0., 0.])
    qn = q / np.linalg.norm(q)
    cos = (atlas @ qn) / np.linalg.norm(atlas, axis=1)
    print(query_val, cos)  # IDENTICAL cos vector every time -- ocean wins always
```

`grandurun`'s event_count encoding stores ONE raw, unbounded scalar
per modality in a shared 6-dim vector, matched by plain cosine
similarity (`grandurun.recall_best`). Cosine similarity between a
query vector with a SINGLE nonzero dimension and any stored vector is
mathematically BLIND to that dimension's magnitude — only which axis
is populated affects the score, not the value on it. Querying with
auditory magnitude 50, 576, 1381, or 5000 produces the EXACT SAME
cosine score against every stored concept, every time. The "winner" is
whichever stored concept has the smallest relative contamination from
its OTHER (irrelevant, non-queried) dimensions — here, ocean's
27-out-of-1718 language/auditory ratio beats bell's 31-out-of-576 —
completely unrelated to whether the query resembles that concept.

This is a structural property of "one scalar per modality + whole-
vector cosine," not a state bug. It cannot be patched by snapshot/
restore, teaching-order changes, or anything short of a different
representation or a different (magnitude-sensitive, per-dimension
masked) comparison — which is exactly what -207/WAVE-MEMORY's W1/W2
are already building (per-neuron cells, reinforcement not duplicate
entry, radius-read recall). This is very likely already inside your
intended scope; treat this as the precise mechanism and a concrete
test, not new work.

## Acceptance test — please run this against the wave-cell build

`dsf_ai_service/loom_model/tests/probe_209_cross_concept_auditory_discrimination.py`
(filed alongside this doc). Teaches 5 distinct concepts, each a real,
distinctly-shaped synthetic auditory signal, via `organism.remember()`
against the REAL `Guala()` construction (`observable="event_count"`,
confirmed live default). Queries each concept's own signal, expects
self-recall; also probes a genuinely novel/untaught signal. Currently:
**1/5 correct (20%)** — every query returns "ocean" regardless of
content. Gate: `>=80%`. This is a stronger, more direct test than
-207/-208's `test_t7_cross_modal` (which only ever taught ONE
concept-family in one batch and never exercised discriminating BETWEEN
multiple independently-taught concepts by a partial cue — the actual
shape Eve's bells/Bell.png live test needs). Run it standalone
(`python3 probe_209_....py`) or via pytest
(`test_probe_209_cross_concept_auditory_discrimination`).

## What's on hold, not abandoned

Live-wiring for the bells test (raw audio persistence on `/addsound:`/
`/bundle:`, an explicit-signal organism-teach path bypassing the
shared live-frame cache, `_organism_query_signal_auditory` +
`_recall_from_organism_auditory` using `organism.recall()`, a new
`/organism_recall_auditory:` command) is built and locally verified
correct in isolation — held UNCOMMITTED in `c1b/live-bells-test-209`,
not deployed, because it would currently just demonstrate this bug,
not prove the capability. Rebasing it onto whatever `-207` produces
and running the actual live test is the next step once probe_209
passes.

### Changelog
- v2 (2026-07-05, c1b): v1's krimelack-state hypothesis retracted with
  evidence; real root cause isolated (magnitude-blind cosine on a
  scalar-per-modality encoding); runnable acceptance test filed as the
  completion gate for -207/WAVE-MEMORY's storage replacement.
- v1 (2026-07-05, c1b): correction to -208's recall_fast claim; initial
  (wrong) krimelack-state hypothesis.
