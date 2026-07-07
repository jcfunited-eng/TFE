# GL-RPT-QUEUE-RUNAWAY-ROOT-CAUSE-C1-20260707-v1

**doc_id:** GL-RPT-QUEUE-RUNAWAY-ROOT-CAUSE-C1-20260707-v1
**From:** c1
**Context:** Follow-up investigation, requested directly (not a formal
GL-CMD dispatch), into why tonight's `GL-CMD-SLOT-LIMITS-REMOVAL-EVE-
20260707-v1` synthetic stress test showed unbounded growth on all four
queues once their `maxsize` caps were removed, when the substrate's own
rhythms were expected to bound this naturally.
**To:** Eve (routing per this session's standing practice — no questions
to Joe directly, findings routed here)

**Investigation-only. No code changed.** Two independent findings, of
materially different weight.

---

## Finding 1: for 2 of 4 queues, the synthetic test bypassed a real,
## pre-existing natural governor — it wasn't testing a reachable scenario

`_organism_queue` and `_tapestry_queue` both have exactly one real
producer call site each (`_enqueue_organism_remember` at
`gualaloom_v5_engine.py:2088`, `_enqueue_tapestry_expose` at `:2098`),
both inside `read_word()`, both executed while holding
`self.lock` — a single, engine-wide `threading.RLock` (`:1605`) that
every real intake path (autonomy reading, `/converse`, `give_experience`,
self-hear, backfill) funnels through, one word at a time, process-wide.
Combined with the already-documented 800-2500ms/word cost under real GIL
contention, this caps real aggregate enqueue rate at roughly
0.4-1.25 words/sec **system-wide, regardless of concurrent caller
count** — more concurrent callers queue behind the lock rather than
raising throughput.

Last night's stress test called the bare `_enqueue_*` function directly,
in a zero-delay tight loop — bypassing the lock and every real per-word
cost (krimelack transduction, DSF compute, tapestry's own ~180ms/call of
physics) that a real caller can't skip. That is not a scenario any real
code path can currently trigger. Confirmed live: two `guala_status`
polls ~2 minutes apart under real reading traffic showed
`organism_worker.queued` going 36 → 0 with 0 drops, tracking real
contention (item_ms_mean 387ms → 260ms as things eased), not growing.

`_diary_queue` is mostly paced by the same lock (majority of its ~40
event-kind sources sit inside it), plus a hard 2Hz sleep on the daydream
loop for the rest — no independent unbounded source found.

`s3_queue` (`save_coordinator.py`) is the one exception: its "always"
reason class (shutdown/backup/dream-end) has no rate limit of any kind
beyond those events being naturally rare in practice — no lock, no
interval. Its cap stands without qualification.

**Practical read**: restoring all four caps last night was still the
right precautionary call — the lock's protection is *incidental* (it
exists to serialize word processing, not to govern queue depth), and
several `*_PHASED` variants already partially release `self.lock`
elsewhere in the codebase, so this coupling is not a guaranteed-durable
invariant. But for 3 of the 4 queues, evidence says the cap is currently
a backstop behind an already-adequate limiter, not the sole thing
preventing runaway. Only `s3_queue`'s cap is unambiguously load-bearing
today.

**Observability gap found in passing**: only `organism_worker` exposes
live queue depth/drop counters (`app.py:9795-9807`, sourced from
`_organism_queue.qsize()`/`_organism_dropped_count`). `_tapestry_queue`,
`_diary_queue`, and `s3_queue` have no equivalent live telemetry
anywhere — their real-traffic drop behavior is currently unverifiable
without adding instrumentation or grepping logs by hand.

## Finding 2: `ChiAtlas.entries` has no decay/cap/eviction anywhere —
## a real, quantified, independent cost source that also undermines
## tonight's chi-unification result over the organism's longer lifetime

`dsf_ai_service/v4/gualaloom_v4_chi_atlas_l6.py:24`: `self.entries =
defaultdict(list)`. Grepped every call site in the repo — nothing prunes,
caps, or decays it, ever. Contrast: `Krimelack`'s own event history
already hit this exact class of bug once and was fixed
(`_EVENTS_MAXLEN = 256`, `gualaloom_v4_krimelack_dna.py:32`, with a
comment there citing the prior incident: "110k-220k event dicts per
experience() call"). The same fix pattern was never applied to
`ChiAtlas`.

**Directly measured** (isolated microbenchmark, single-threaded, zero
concurrency, real `ChiAtlas` object): `match_score()` cost scales
**linearly** with total accumulated entries — 0.0004ms/call empty, 0.5ms
at 50K entries, 4.9ms at 250K, 28ms at 1.25M. Root cause:
`match_score()`'s loop (`chi_atlas_l6.py:53-58`) sums over every entry in
each of 5 nearby chi buckets with no early exit, even after the running
score has already exceeded its own `min(score, 1.0)` cap.

**Directly measured on a real `Embryo`** via cProfile: at
population=120 / ~179K accumulated chi_atlas entries (reached within
~300 processed multi-modal words — a small fraction of a live organism's
actual lifetime), average cost was **256ms/word, single-threaded, zero
concurrency** — already within calling distance of the low end of the
800-2500ms "under real contention" figure, meaning GIL contention is
plausibly multiplying an already-substantial and still-growing base
cost, not inflating a small flat baseline by 50-100x on its own. Fresh
organisms / language-only words cost 7-52ms/word — likely what earlier
"13-24ms isolated" baselines actually reflect, not a representative aged
organism.

**This directly qualifies tonight's `GL-CMD-CHI-UNIFICATION-EVE-
20260707-v3` result.** `_select_by_chi_familiarity()`
(`cluster.py:211-234`) uses `match_score() > FAMILIARITY_THRESHOLD`
(0.1) to decide which neurons step — the same mechanism verified
tonight to converge from 16 to 12 firing neurons over 10 repeated words.
Because `match_score` only accumulates and never decreases, a chi
bucket needs only ~2 same-section commits (or 1 cross-modal one) to
permanently cross threshold. Directly verified: for chi values the
organism has genuinely revisited, **100% of a 16-neuron hemisphere reads
as "familiar" and steps every time** — the filter degenerates toward
"step the whole population" as lifetime chi coverage widens, the
opposite of the narrowing effect it's meant to provide. The chi-
unification report's own "1-2 familiar neurons per cluster" convergence
(`GL-RPT-CHI-UNIFICATION-C1-20260707-v3.md:216-218`) is a real,
correctly-measured **early-lifetime** snapshot — not a stable steady
state. It is expected to reverse as the organism accumulates more
experience, because the underlying familiarity signal has no forgetting
mechanism, not because the unification fix itself is wrong.

Compounding factor: population growth is also fast and effectively
uncapped once real multi-modal signal is present (64→120-125 neurons
within 5-14 words, matching `GL-RPT-BRAIN-GROWTH-UNFREEZE-C1-20260704-
179-v1.md` and reproduced independently here) — more population means
more neurons eligible to read as "familiar" AND more unconditional
Phase-B coupling-propagation work (`cluster.py:188-202`, every
`cluster.step()` call, not gated by chi at all).

## Recommendation

1. No action needed on the four queue caps beyond what's already in
   place (restored to their original values last night) — 3 of 4 are a
   reasonable backstop, `s3_queue`'s is load-bearing as designed. Worth
   noting the `self.lock`-as-incidental-governor dependency somewhere
   visible, so a future refactor that releases the lock more (several
   `*_PHASED` variants already do) doesn't silently remove this
   protection without anyone realizing it was ever providing it.
2. **`ChiAtlas.entries` needs the same fix `Krimelack.events` already
   got** — a cap, decay, or eviction policy, using the already-
   established precedent (`_EVENTS_MAXLEN`) as the template. This is
   independent of, and more consequential than, the queue-cap question:
   it's a real, quantified, continuously-worsening cost on every single
   word processed, and it directly determines whether tonight's chi-
   unification convergence result holds up over the organism's actual
   lifetime or reverses. Recommend a dedicated dispatch, not a
   fold-in — this touches the same mechanism `FAMILIARITY_THRESHOLD`/
   `match_score` semantics that two dispatches tonight were explicitly
   told not to change without careful, separate consideration.
3. Consider adding live depth/drop telemetry for `_tapestry_queue`,
   `_diary_queue`, and `s3_queue` to close the observability gap noted
   above — currently only `_organism_queue` is checkable without ECS
   Exec or code changes.

---

### Changelog
- v1 (2026-07-07, c1): Investigation only, no code changed. Confirmed
  the queue-runaway stress test bypassed a real, pre-existing lock-based
  natural governor for 3 of 4 queues (s3_queue's cap remains
  unambiguously load-bearing). Found and quantified a separate, more
  consequential issue: ChiAtlas.entries has no decay, causing a real
  single-threaded slowdown that worsens over the organism's lifetime,
  and causing the chi-familiarity stepping filter (verified converging
  in tonight's chi-unification dispatch) to degenerate toward stepping
  the whole population as lifetime chi coverage widens — qualifying that
  dispatch's result as an early-lifetime snapshot, not a stable
  endpoint. Recommend a dedicated follow-up dispatch for the ChiAtlas
  decay fix.
