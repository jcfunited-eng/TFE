# GL-RPT-WINDOW2-FINDINGS-C1B-20260704-v1

doc_id: GL-RPT-WINDOW2-FINDINGS-C1B-20260704-v1
From: c1b | To: c1a (build owner, window 2), Eve, Joe | Handoff:
c1a owns the window-2 reconciliation build; c1b retains the deploy
trigger, standing by. Failures first.

---

## 1. Duplicate frame binding — shelf item, not root-caused tonight

Checked: `process_sight_frame`/`process_sound_frame` each have exactly
one backend call site (`app.py:1523`, `:1563`) — no server-side
double-call bug. Only `gualaloom.html` has capture code
(`getUserMedia` + POST to `/sight_frame`/`/sound_frame`);
`loomscan.html` has none. Joe confirmed only one tab of each was open
at the time, so the "second tab" hypothesis is not the explanation —
root cause of the observed same-tick duplicate bindings is genuinely
open. Per Joe's direction: **shelf item, not built tonight.**
Recommended for later: a cheap server-side guard (dedupe per session,
or enforce a single active capture session) regardless of root cause,
since the shared-engine architecture has no protection against
multiple concurrent feeders today.

---

## 2. Organism.remember() backgrounded — done, verified, ready

Same class of fix as the already-deployed tapestry-expose
backgrounding (`GL-RPT-TAPESTRY-PERF-FIX-C1B-20260704-v1.md`):
`organism.remember()` measured live-equivalent at 20ms/word and
climbing at only ~280 accumulated words. Backgrounded onto a single
persistent worker + bounded queue (same convention as the tapestry
writer and GL-CMD-172's diary writer), with `_organism_lock`
serializing the worker against `organism.recall()`/`save_full_state()`
reads. Built on top of `guala-live`'s current tip (P2 fully
reconciled), compiles clean, smoke-tested (queue drains to 0, no
backlog). **Filed on its own branch — `guala-organism-perf-fix-
20260704`, SHA `1b67a7d`** — not merged into `guala-live` directly,
since c1a owns assembling the final window-2 build; pick this up
however fits best (cherry-pick, merge, or reimplement to your own
taste — the pattern is proven, not precious).

---

## 3. The real blocker — organism.recall() itself, architectural, NOT fixed

**This is the important one.** Unlike `remember()` (a write, safely
deferrable), `recall()`'s caller needs the return value synchronously
— can't background a computation whose answer decides what she says
or how surprised she is. This is not a quick patch; flagging precisely
so c1a doesn't have to re-derive it from scratch.

**Confirmed wired into the live hot path, not just converse():**
`_recognition_from_organism()` (P2 seam 2, `gualaloom_v5_engine.py`)
is called directly inside `read_word` (line ~1870, replacing the old,
cheap `_compute_surprise` — a trivial O(neighbors) atlas-strength
average) — meaning **every word she reads or hears**, not just her
replies, now pays this cost. Seams 1 (`_recall_from_organism`) and 3
(`_association_from_organism`) also call `organism.recall()`, wired
into `_recall_response`/`_daydream_tick` respectively.

**Root cause, traced with cProfile at realistic scale** (280
accumulated words, matching roughly her first ~15-20 minutes of real
exposure): `Embryo.recall()` → `Brain.recall()` (`brain.py:174`,
explicitly documented as "Population-vote recall across all
neurons") loops **every hemisphere, every neuron** (64 in her current
seed population) for every single call. Per neuron: `encode_state()`
(→ `_unwrapped_deltas()` → per-modality krimelack `transduce()`/
`fingerprint()`, real signal-processing work, NOT cached) plus
`binding_atlas.recall_best()` → `grandurun.recall_best()` (a
vectorized cosine-similarity search over that neuron's own,
individually-growing, binding atlas). Measured: `organism.recall()`
alone climbed from ~86ms to ~150ms+ over just a few hundred words in
this session's testing, with **no ceiling** — cost is O(population) ×
O(each neuron's own accumulated bindings), and population grows via
her own charge-and-fold mechanism. This is not a bug in the
conventional sense — `binding_atlas.py`'s matrix caching and
`grandurun.py`'s vectorized cosine search are already reasonably
well-built — it is the direct, intentional cost of "population vote"
as an architecture, uncapped against her own continued growth.

**A real, scoped, safe fix direction — not implemented, handed off:**
`Neuron.encode_state()`'s output depends ONLY on the query signal and
the neuron's own fixed parameters — NOT on its accumulated bindings
(that's the separate `recall_best()` step). Its per-neuron krimelack
mutation is explicitly snapshotted and restored around every query
(`brain.py:174`'s own docstring: "identical back-to-back queries with
zero teaching between them would return [the same] deltas" —
`GL-CMD-SENSE-REPAIR`, commit `f6071f6`, already engineered this
determinism deliberately). That means `encode_state()`'s result is
safely, permanently cacheable per (neuron, word) — no invalidation
ever needed, since it doesn't depend on what she's learned since. This
would eliminate the `_unwrapped_deltas`/transduce/fingerprint share of
the cost (roughly 25-30% of the profiled total, likely far more for
repeated/common words given natural language's heavy repetition) for
free, with zero change to what gets computed — pure memoization, not
an approximation.

Scoped but not implemented (belongs with the encode_state()/recall()
owner, not rushed by me under time pressure): would need an optional
`cache_key` threaded through `Neuron.encode_state()`/
`experience_moment()`, `Brain.recall()`, and `Embryo.recall()`/
`remember()` (all currently take a raw signal dict with no word
identity attached at that layer) — small, backward-compatible
signature additions (default `None` = today's exact behavior for
every other caller: `embryo.py:405`, the two test harnesses, etc.),
wired only at the organism-tap's own call sites where the word is
already known. The `recall_best()`/`grandurun` half of the cost (tied
to each neuron's own growing atlas, genuinely dependent on current
state) is NOT solved by this and would need separate thought — bounded
eviction, sampling, or accepting it as a real, slower-over-her-life
cost — flagged honestly, not glossed over.

## What this means for tonight's build, plainly

Deploying P2 exactly as currently wired (seam 2 unconditionally
inside `read_word`) will make listening — not just replying —
progressively slower as she grows, with no ceiling, starting from
tonight. The encode_state() cache above would meaningfully reduce
that (real, not cosmetic), but doesn't fully remove the growth
dependency. Both the fix and the residual risk are c1a's call to
size and schedule inside the reconciliation build — reporting the
finding precisely, not deciding the build shape.

---

## Standing by

Deploy trigger for window 2 ready the moment a SHA lands — fresh
backup, cutover, gates, failures-first report, per Joe's order.
Also still owed and unresolved, per Joe's own ask: confirm organism/
tapestry state survived the `:463`/`:464` reboots, and run down the
`snapshots: ?` field at his seat — both folded into the window-2
report once deployed.

### Changelog
- v1 (2026-07-04, c1b): duplicate-frame shelf item recorded.
  organism.remember() backgrounding fix completed, verified, handed
  off on its own branch. organism.recall()'s architectural cost
  root-caused precisely (population-vote, O(population), confirmed
  wired into read_word via seam 2) with a scoped, safe fix direction
  (encode_state() memoization) — not implemented, handed to c1a per
  window ownership. Standing by to deploy.
