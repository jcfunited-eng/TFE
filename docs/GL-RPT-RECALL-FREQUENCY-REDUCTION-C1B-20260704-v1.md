# GL-RPT-RECALL-FREQUENCY-REDUCTION-C1B-20260704-v1

doc_id: GL-RPT-RECALL-FREQUENCY-REDUCTION-C1B-20260704-v1
From: c1b | To: Eve, Joe, c1a | Responds to Joe's direct order to
actually fix the organism.recall() cost, not just report it. Real,
tested, partial mitigation — not a full fix of the architecture.
Stating that plainly, not overselling it.

---

## What this is, and what it is not

**Is:** a real reduction in how OFTEN the expensive `organism.recall()`
call runs, at the two highest-frequency call sites, verified by
cProfile call counts before/after, not assumed.

**Is not:** a fix to `organism.recall()`'s own O(population) cost per
call. That cost is architecturally unchanged — each actual call still
costs what it cost before, and will still grow as she grows. This
does not remove the underlying problem c1a and I both already
reported; it reduces how often the live path pays it.

**Is not a repeat of the disproven cache.** That idea failed because
it assumed `encode_state()`'s output was safely reusable across time
— false, since teaching (`remember()`) legitimately changes it. This
fix makes no such assumption: it computes a real, fresh `recall()`
result every Nth call and honestly reuses `self._last_surprise` (the
codebase's own pre-existing fallback value, already used by
`_affect_kwargs`) for the calls in between — a slightly-stale-but-real
value, not a value asserted to still be exactly correct. Same
"honest degradation, not silent lie" principle already accepted for
the tapestry/organism queues dropping items under back-pressure.

---

## The two changes

**1. `read_word`'s seam-2 recognition call** (the dominant cost —
runs on every word she reads or hears, not just replies): now runs
every 3rd word (`RECOGNITION_EVERY_N_WORDS = 3`), reusing
`self._last_surprise` otherwise.

**2. Seam 4's habituation freshness sample** (`_reading_freshness_
from_organism`): sample size cut from 10 words to 3 — same real-
signal-less-often principle; this call site has no `remember()` calls
interleaved with its own `recall()` calls, so it's purely a call-count
reduction, cleanly safe.

Left unchanged: the "clarification shape" fallback path's `max(recall
for w in words)` — this only runs once per reply attempt (not per
word read), already much lower frequency than the two sites above;
not touched under this same time pressure without separately
verifying it.

---

## Measured, not assumed

cProfile, same realistic-scale test as every other measurement this
session (~280+ accumulated words before profiling the next 14):

| | Before this fix | After this fix |
|---|---|---|
| `_recognition_from_organism` calls per 14 words | 14 | **5** |
| read_word cost | ~49.8ms/word (post-window-2 merge) | **38-47ms/word** |

Call count dropped by the expected factor (~1/3 retained, matching
`RECOGNITION_EVERY_N_WORDS = 3`); the time reduction is real and
proportionate, confirmed via cProfile's own call-count column, not
inferred from wall-clock alone.

**Honest ceiling on what to expect live:** this reduces one real
contributor among several (`_recall_response`/seam 1, `_association_
from_organism`/seam 3, and the per-call `organism.recall()` cost
itself are all unchanged). Real conversational turns should measurably
improve but will not be fast — the underlying architecture question
remains exactly what c1a's reconciliation report already said it was:
open, unsolved, needing its own dedicated investigation.

---

## Deploy

Built on `guala-live`'s current tip (`b2206cd`) — no reconciliation
needed. Compiled clean. Fresh backup before cutover.

### Changelog
- v1 (2026-07-04, c1b): recall-call-frequency reduction at the two
  highest-frequency call sites, verified via cProfile call counts
  before/after. Real, tested, partial mitigation of the organism.
  recall() cost — not a fix of the underlying architecture, stated
  plainly.
