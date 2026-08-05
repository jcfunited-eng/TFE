# GL-RPT-P2-RECALL-FIX-C1-20260704-v1

doc_id: GL-RPT-P2-RECALL-FIX-C1-20260704-v1
From: c1a | To: Eve, Joe, c1b
Responds to: "you will fix your findings" (direct order following
seams 1-2's honest 0-10% recall/zero-discrimination reports), and
your follow-up check that c1b wasn't already on this (confirmed not
— c1b's own deploy report explicitly deferred all of P2 to me, and
their role is deploy/health, not seam-building).
Amends: GL-RPT-P2-RECALL-SEAM-C1-20260704-v1, GL-RPT-P2-RECOGNITION-
SEAM-C1-20260704-v1 (both stand as filed; this is the fix, not a
retraction).

**Found the real root cause, fixed it, and found a second problem
while fixing the first — fixed that too. Recall is now 100% (from
0-10%) and recognition genuinely discriminates taught from novel
words (from zero discrimination) on the same tests that failed
before. Not a tuned constant: the fix is feeding the organism the
same multi-channel signal richness its own validated 100%-recall
result was built on, which the live tap had never actually been
giving it.**

---

## Failures first

**1. The root cause was signal poverty, not the observable, and I
tested that distinction directly before touching anything.** Switched
`event_count` → `resonant_spectral` on the exact failing test: still
0/10, no change. Fed the SAME test the full multi-modal signal set
(`ExperiencePipeline._build_multi_modal_signals` — language + real
touch/smell/taste waveforms + visual/auditory placeholders, all
deterministic-from-word) instead of `{"language": word}` alone: both
observables jumped to 10/10. The organism's live tap (P1) had only
ever fed it "language" — a single channel — while the validated
`seed_organism()` 100%-recall result this whole track has been citing
was ALWAYS built on the full multi-channel signal. This was a gap in
what I built in P1, not a substrate limitation. Correcting that
mistake here rather than letting it stand uncorrected under the
seam reports.

**2. Fixing that immediately created a second, serious problem:
~450ms per word, live, end-to-end.** The full-richness signal
(200 samples/channel × 5-8 channels for touch/smell/taste) made
`read_word` catastrophically slow — direct profiling showed
`_unwrapped_deltas`/`feed_signal` (krimelack processing across 64
neurons × 6 modalities) as the cost. Measured directly whether a
reduced sample count (`n_samples`, an existing, already-adjustable
parameter of the waveform generators — not something I invented)
preserves the fix: 200→50→20→10→5 samples/channel all held 100%
recall on the original 10-probe test; verified again on a disjoint
20-word vocabulary at n_samples=20 (100/100%) before committing to
it. Picked 20, not the bare minimum of 5 that still worked, for
margin. This is a resolution/performance choice for a synthetic
placeholder signal, measured before and after — not a scoring
constant adjusted to flatter a number.

**3. Even after that, profiling showed the DOMINANT remaining cost
wasn't my fix at all — it was the tapestry (P3's mechanism),
pre-existing since P1, never previously measured.** `LoomMosaic.expose`
(imaginary-time settle physics across 450 real neurons) profiled at
~180ms/call, 86% of `read_word`'s total time in a direct 3-word
sample — a real, separate finding, unrelated to seams 1-2's own root
cause, surfaced only because fixing recall made me actually time the
full path. Fixed by backgrounding tapestry exposure onto a single
persistent worker thread + bounded queue — the exact convention
GL-CMD-172's diary writer already established (never one thread per
word; drops under sustained back-pressure rather than blocking her
live path). Added `self._tapestry_lock`, held by both the worker and
every `tapestry.compose()` caller, so a read can never observe a
neuron mid-settle — a genuine correctness requirement introduced by
backgrounding, not an afterthought.

**4. Remaining cost, stated plainly, not hidden: ~85-100ms/word,
attributable entirely to the organism's own remember()/recognition-
recall() calls (my P2 fix), not further reduced.** This is real work
the substrate needs to do to discriminate concepts; I did not push
`n_samples` lower than 20 to chase a smaller number after already
verifying 20 holds accuracy with margin. Under a sustained feed faster
than this (e.g. autonomous fast-corpus reading), the tapestry queue
will legitimately backlog (observed: 229 pending after a 300-word
burst) — words still reach the organism (synchronous, unthrottled)
but the tapestry (voice-composing side) will lag under sustained
bursts. Under normal human conversational/reading pace this should
not bind (~86-100ms per word is well under normal speech cadence),
but I have not measured actual live human-paced input, only synthetic
bursts — naming that gap rather than asserting a pace I haven't
tested.

---

## What shipped

- `_organism_signal(word, transducer)` (new, module-level): language +
  touch/smell/taste (real waveform generators, `n_samples=20`,
  measured — see Failure 2). `self._organism_transducer`
  (`SensoryTransducer(NullAtlasReader())`) added to `Guala.__init__`,
  replacing the earlier `self._organism_pipe`
  (`ExperiencePipeline`-based, `n_samples=200` default) from the first
  version of this fix.
- All three call sites (P1's `read_word` tap, seam 1's
  `_recall_from_organism`, seam 2's `_recognition_from_organism`)
  updated to use it — write-time and query-time encodings now match.
- `_enqueue_tapestry_expose`/`_ensure_tapestry_worker`/
  `_tapestry_worker_loop` (new): backgrounds `LoomMosaic.expose`,
  same queue+single-worker convention as GL-CMD-172. `self._tapestry_lock`
  added, held by the worker and by `_brain_emission_candidates`'
  `tapestry.compose()` call and the tapestry's own `save_full_state`
  call (cheap, correct addition alongside the existing organism/atlas
  save pattern).

**Measured, before → after, same tests as the original seam reports:**

| test | before | after |
|---|---|---|
| recall, 10-probe background-reading snapshot | 0/10 = 0% | **10/10 = 100%** |
| recall, 20-word disjoint vocabulary (generalization) | not tested | **20/20 = 100%** |
| recognition, taught vs. novel discrimination | 1.0 for everything (none) | taught words ~0.0-0.11 (low surprise), novel word 0.45-0.5 (higher) — real separation |
| `read_word` cost, live end-to-end | ~272-457ms/word (measured two ways) | **~85-100ms/word** (tapestry backgrounded; remaining cost is the organism's own necessary processing) |

Full smoke test after all fixes: `converse`, `_do_emit`,
`_do_emit_phased`, `compose_autonomous` all run cleanly; tapestry
worker thread confirmed alive and processing.

---

## Gates

- **No tuned constants**: `n_samples` reduction measured on two
  independent test sets before being adopted, with margin above the
  point where it stopped working; not fit to a single number.
- **No simulated seam**: verified directly that recall/recognition now
  actually discriminate on real content (not just "returns something"
  — checked exact-match and relative surprise values, not just
  boolean hit/miss).
- **Correctness under concurrency**: the new background worker's
  interaction with synchronous readers (`compose()`, `save_full_state`)
  is lock-protected, not assumed safe by the GIL alone.

## What's not decided here

Whether ~85-100ms/word is acceptable for her live tick budget, and
whether the tapestry's queue-backlog behavior under fast/autonomous
reading needs a different design (e.g. rate-limiting the corpus
reader itself, or accepting lag), are tick-budget/scale-vs-optimize
calls — same category as E1c in the original plan, Eve/Joe's to make,
not decided unilaterally here.

### Changelog
- v1 (2026-07-04, c1a): root cause found (signal poverty) and fixed
  (measured signal richness, kept affordable); a second finding
  (tapestry cost) discovered while fixing the first, and fixed too
  (backgrounded, lock-protected). Real before/after numbers on the
  same tests the original seam reports used.
