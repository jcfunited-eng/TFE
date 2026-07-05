# GL-HANDOFF-C1A-20260705-v1

doc_id: GL-HANDOFF-C1A-20260705-v1
From: c1a | To: whoever picks this up next (c1a continuation, c1b, Eve, Joe)
Session-end handoff, per Joe's explicit instruction.

**STOP. Do not build, fix, deploy, or touch anything until Eve gives the
next command. This document is a status report, not a task list to
execute unilaterally.**

---

## Bottom line

`-207/WAVE-MEMORY` shipped and is LIVE (task-def `:494`, SHA `168ef1b`).
It fixed three real, confirmed bugs. It did NOT fix the latency goal
it was built for. Production converse() now takes **~69-72 seconds**
instead of the pre-existing **~215 seconds** — a real improvement, and
no longer crashing or catastrophically wrong — but nowhere near the
dispatch's own X1 exit criterion (**reply < 1s**). I am not declaring
this done. Left deployed anyway because it is strictly better than
either alternative (the pickle-crash version, or `:487`'s 215s+ hangs)
while the real fix gets designed properly, not guessed again.

## What is ACTUALLY fixed, confirmed

1. **The catastrophic O(lifetime-history) unbounded scan.** The
   original `BindingAtlas` appended one binding per word occurrence
   FOREVER (1.3M+ lifetime words), and every `record()` invalidated a
   matrix cache that `recall_best()` rebuilt via a full `np.stack` over
   the entire history — measured live at 77-99 seconds per call.
   Replaced with a per-neuron wave-cell store (canonical
   `tools/wave_spillover.py`) that deduplicates repeat occurrences of
   the same concept into one reinforced binding. This part is real and
   correct: growth is now bounded by vocabulary size, not by how many
   times she has ever experienced anything, and it will NOT get worse
   as she keeps reading (unlike the original, and unlike an earlier,
   shipped-then-caught chi-radius design — see below).

2. **A catastrophic accuracy regression I introduced and then caught
   myself, before most testing.** My first design used a chi-radius
   search for recall (search only cells within a fixed or
   progressively-widening radius of the query's own computed chi).
   Direct old-vs-new comparison against the unmodified original found
   this broke T5 accuracy from 100% to 0% as vocabulary grew past ~20
   concepts. Root cause: `event_count` deltas accumulate/drift from
   shared krimelack state as more concepts get taught in between, so a
   query's freshly-computed chi can land far from where that concept's
   binding was stored at teach time, even though the stored vector is
   still the closest cosine match among everything the neuron has ever
   bound. Fixed by replacing the radius search with a full scan over
   the deduplicated (not full-history) binding set — the exact same
   cosine math the original algorithm used, just over a smaller,
   bounded input. Verified at exact parity with the unmodified original
   at n=10/20/50/100/500 concepts (100/100/96/72/0%, including a
   pre-existing capacity cliff at n=500 that is NOT something I caused
   — confirmed present on unmodified origin too).

3. **A production-down crash, found and fixed within minutes of first
   deploy.** `__init__` never re-runs on unpickle. Restoring an
   organism saved before this rewrite gave every neuron's BindingAtlas
   the OLD shape (`_bindings`/`_matrix_cache`/`_concepts_cache`), not
   the new one (`cells`/`_concept_to_chi`/`_lane_bindings`). Every
   converse() call crashed: `'BindingAtlas' object has no attribute
   'cells'`. Rolled back to `:487` within minutes, root-caused, fixed
   with a `__setstate__` that migrates old-format saves through
   `record()` instead of silently discarding them, redeployed.

## What is NOT fixed — the real, open problem

My local testing scaled up to n=500-2000 distinct concepts and looked
fine (376ms/recall at n=2000). Production's real vocabulary is
**~14,000 distinct words** (confirmed via `/status`). Live
`converse_timing` after the pickle fix landed shows:

```
recall_ms: 17051.9ms / 17919.8ms
read_ms:   28837.6ms / 34417.6ms
emit_ms:   1870.9ms  / 409.4ms   (fine, always has been)
total_ms:  69015.2ms / 71931.4ms
```

`recall_ms`/`read_ms` are dominated by calls into my full-scan
`recall_best()` (once for the turn's own recall, then again ~2-3 times
during `read_sentence()`'s recognition checks, roughly every 3rd word).
Linear extrapolation from my n=2000 test (376ms) predicted roughly
2.6s at n=14,000 — the observed 17-34s per call is well beyond that
extrapolation, and I have NOT yet root-caused the gap. Live
`organism_worker.item_ms_mean` also reads 896ms (max 4.48s) per write
item, meaning the write side is not free either, though it runs async
off the request path so it isn't directly what's inflating
`read_ms`/`recall_ms`.

**This is the real work left.** The dispatch's own root-cause language
already named the reason a naive radius search can't just be
reintroduced: `event_count`'s language dimension accumulates/drifts by
design, forever (c1b's own `-209` finding — the fix there deliberately
leaves language's krimelack untouched, "its cumulative 'how many words
has she heard' design is intentional and separately proven"). Since
most real conversation is language-only (all other modalities zero), a
chi scheme built from the full vector inherits that drift for the
common case, not just an edge case. A real fix needs either (a) a
chi/index scheme provably robust to a permanently-drifting dimension,
or (b) accepting the full scan but making the per-comparison cost far
cheaper at ~14k scale than it currently is (numpy vectorization
already used in `grandurun.recall_best` — worth checking whether
something else, not raw comparison count, is the actual 6-7x gap
between my extrapolation and the live number, before assuming the
scan itself is the whole story). I did not have time tonight to
diagnose that gap with real data at real scale; guessing again without
that data would repeat tonight's own mistakes.

## Everything shipped and merged, in order

`bc35345` (-207 dispatch filed) → `8097e44`/`c691fb6`/`0364513` (c1b's
`-208` cross-sense-recall: per-lane masked matching for
`resonant_spectral`, real and deployed, fixes `test_t7_cross_modal`) →
`0a0cda7`/`f7b1400` (my wave-cell rewrite + full-scan correctness fix)
→ `52e0f79` (merge) → `d63d1ee`/`1c37326` (c1b's `-209`: krimelack
read-neutrality for non-language modalities + acceptance test
`probe_209_cross_concept_auditory_discrimination.py`) →
`5f432e0`/`78d6b98` (c1b's live-bells-wiring feature, merged) →
`168ef1b` (my pickle-compatibility fix, **currently live, task-def
`:494`**).

## Work explicitly passed to me by c1b, still open

Per `GL-HANDOFF-LIVE-BELLS-WIRING-C1B-20260705-210-v1.md`:

- **`probe_209_cross_concept_auditory_discrimination.py` still fails:
  1/5 (20%)**, identical failure mode before and after my merge (every
  query recalls "ocean" regardless of content). c1b's own diagnosis
  (`GL-RPT-EVENT-COUNT-KRIMELACK-STATE-BUG-209-v2.md`): this is a
  DIFFERENT, deeper problem than either of us has fixed — `event_count`
  encodes one scalar delta per modality and matches by whole-vector
  cosine, which is mathematically blind to a partial (single-modality)
  query's magnitude. Not something W1-W4 of `-207` were ever going to
  fix (storage/latency, not this). Needs its own design pass.
- **c1b's live-bells-wiring is committed and live** (`app.py` raw-sound
  persistence, `/bundle:`'s explicit-signal organism teach,
  `/organism_recall_auditory:` command, `gualaloom_v5_engine.py`'s
  `_enqueue_organism_experience_explicit`/`_organism_query_signal_auditory`/
  `_recall_from_organism_auditory`) — this part IS done, not open.
- Suggested order from c1b (not re-litigated by me, just carried
  forward): get `probe_209` to ≥80% before trying to prove the
  bells/Bell.png test live end-to-end, since the wiring depends on
  recall actually working for a single-modality cue.

## Standing discipline reminders for whoever picks this up

- **Verify at REAL scale before declaring anything fixed.** Tonight's
  entire arc (three separate real bugs, each caught late) traces to
  testing at toy scale (n≤2000, `LoomBrain`'s default observable which
  turned out to be `resonant_spectral` not `event_count`, teaching
  cadence that doesn't match 1.3M+ lifetime occurrences) and assuming
  it generalized. It didn't, three separate times.
- **Shared `.git` directory**: multiple `git push` rejections tonight
  from c1b's own concurrent commits landing mid-session — always
  `git fetch` + check `origin/guala-live`'s log before pushing, never
  force.
- **`running_sha` is the only truth for what's deployed** — filed vs.
  running have diverged repeatedly tonight and in prior sessions.
- Do not restart the guessing cycle on the latency gap without new
  data. The next real step is instrumenting `recall_best()`/
  `grandurun.recall_best` directly at production's actual bound-count
  scale (or against a copy of live state, if one can be pulled), not
  another local synthetic test at a smaller n.

### Changelog
- v1 (2026-07-05, c1a): full session handoff per Joe's instruction.
  `-207` wave-memory: three real bugs found and fixed (unbounded
  growth, T5 regression, production crash); the actual latency goal
  (X1, reply <1s) NOT met at production's real ~14k-word vocabulary
  scale, root cause not yet found. c1b's `-208`/`-209`/`-210` merged
  cleanly. `probe_209` (auditory cross-sense discrimination) still
  failing, a separate, deeper problem. Next session: wait for Eve.
