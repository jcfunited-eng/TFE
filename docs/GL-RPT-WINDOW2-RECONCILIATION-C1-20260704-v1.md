# GL-RPT-WINDOW2-RECONCILIATION-C1-20260704-v1

doc_id: GL-RPT-WINDOW2-RECONCILIATION-C1-20260704-v1
From: c1a | To: Eve, Joe, c1b
Responds to: Joe's direct order ("the branch reconciliation is
yours... merge them, fold in the remember()-growth backgrounding fix
c1b diagnosed... push the reconciled SHA") and
`GL-RPT-WINDOW2-FINDINGS-C1B-20260704-v1.md`.
Vehicle: her live-path source, git reconciliation + one correctness
finding. Zero deploy action — c1b holds the trigger.

**Merge done, pushed (`9bdc042`). c1b's `remember()` backgrounding is
in and verified. Their `recall()` memoization fix direction is NOT
implemented — I tested the core premise directly and it's false, not
just risky. Reporting that correction now, before it goes anywhere
near a deploy, rather than after.**

---

## Failures first

**1. c1b's proposed `encode_state()` memoization would have silently
returned wrong recall/recognition results — a correctness bug, not
a performance one.** Their fix direction (sound reasoning, precisely
scoped, explicitly not rushed by them) rested on one claim:
`Neuron.encode_state()`'s output depends only on the query signal and
the neuron's fixed parameters, not on accumulated bindings — citing
`brain.py`'s own docstring ("identical back-to-back queries with zero
teaching between them return the same deltas," GL-CMD-SENSE-REPAIR).
That docstring is true as far as it goes. It does NOT say
`encode_state()` is independent of teaching that happens BETWEEN
queries — and that's the case that matters, since `read_word` calls
`remember()` for every single word.

Tested directly, three ways, isolating exactly what changes:
- Raw `encode_state()` calls, no snapshot/restore: differ even
  back-to-back (expected — this bypasses `Brain.recall()`'s own
  restore mechanism, not a fair test on its own).
- `Embryo.recall()` (the real, snapshot/restore-wrapped path),
  back-to-back with zero teaching: **identical** — confirms the
  documented invariant holds correctly.
- **The actual question**: instrumented one specific neuron to
  capture its `encode_state()` output through two real
  `Embryo.recall()` calls for the identical query ("peter"), with
  exactly one real `remember()` call (a different word) in between.
  Result: `[0, 0, 40, 41, 44, 41]` → `[0, 0, 27, 45, 38, 104]` —
  **completely different**, not a rounding difference.

Mechanism, once measured: the `event_count` observable's krimelack is
no-reset by design — its accumulated phase/winding state advances
with every real teaching event and is never cleared between queries
(only recall's OWN incidental mutation is restored, per GL-CMD-SENSE-
REPAIR). `_unwrapped_deltas`'s delta computation depends on where in
that ever-advancing trajectory a query happens to land, not just on
the query signal. A cache keyed on `(neuron, word)` — as scoped —
would return whatever the FIRST query happened to compute, forever
after, regardless of how much she's since learned. That's a stale,
silently wrong answer, presented with the same confidence as a fresh
one. Worse than the current slow-but-correct behavior, not better.

**2. This does not mean c1b's diagnosis of the underlying problem was
wrong — it was precise and is still exactly right.** `organism.recall()`
really is O(population), really has no ceiling, really is confirmed
wired into every word via seam 2, and her real conversations really
were measured at 82-120+ seconds/turn. Only the specific proposed
fix (memoization) is disqualified. The cost problem itself remains
open and unsolved as of this report.

**3. No replacement fix is offered here either, and I'm not inventing
one under this same time pressure.** Rushing a second unverified
optimization immediately after disproving the first would repeat the
exact mistake this report just corrected. The `recall()` cost
question needs real, separate investigation — bounded eviction,
sampling, accepting the cost, or something else — each of which
needs its own measurement before being trusted, the same way this
one just got measured and rejected.

---

## What's actually reconciled and pushed

`guala-live` @ `9bdc042`:
- P1+P3 (organism/tapestry live, brain-driven emission) — already
  deployed (task:462/463).
- All 6 P2 seams (recall, recognition, association, habituation-for-
  READING; attention/affect declined with reasons) — **not yet
  deployed**, ratification still open.
- Tapestry-expose backgrounding — already deployed (task:464),
  confirmed functionally identical to what's on this branch (diffed
  before merging; no independent content to reconcile).
- **`organism.remember()` backgrounding** (c1b's
  `guala-organism-perf-fix-20260704`, `1b67a7d`) — merged in this
  session, clean merge, no conflicts. Re-verified after merge: smoke
  test (`converse`, `_do_emit`, `_do_emit_phased`, `compose_autonomous`,
  `_daydream_tick`) all pass; both background workers (organism,
  tapestry) confirmed alive; `read_word` end-to-end now ~49.8ms/word
  in this sandbox (down from ~85-100ms/word before this merge,
  further down from the original ~272-457ms/word before any
  backgrounding existed).

## What's still open, honestly

- `organism.recall()`'s O(population) cost, uncapped against her own
  growth — the single largest remaining known cost, confirmed
  responsible for the 82-120+ second live turn times c1b measured.
  No safe fix identified yet (Failure 3).
- Whether the P2 cognitive seams themselves are ratified for deploy —
  unchanged by this reconciliation, still Eve/Joe's call, restated in
  every seam report.
- The duplicate-frame-binding shelf item (c1b's finding #1) —
  untouched, not this report's scope.

### Changelog
- v1 (2026-07-04, c1a): merged `guala-organism-perf-fix-20260704`
  into `guala-live` (`9bdc042`), re-verified. Tested and disproved
  c1b's `encode_state()` memoization fix direction before
  implementing it — a real correctness risk caught before it reached
  code, not after. `organism.recall()`'s cost remains open.
