# GL-HANDOFF-FALLBACK-SINGLE-WORD-ROOT-CAUSE-C1-20260706-v1

doc_id: GL-HANDOFF-FALLBACK-SINGLE-WORD-ROOT-CAUSE-C1-20260706-v1
From: c1 | To: whoever picks this up next (could be me, later tonight, or a
fresh session)
Full causal chain for "why does she mostly reply with one repeated word
instead of a sentence," traced end to end tonight. This is written to be
handed off complete — no prior context required, no re-investigation needed.

## Bottom line

The single-word fallback isn't one bug. It's four real things stacked, three
already fixed and deployed tonight, one found but genuinely too large and
cross-cutting to patch blind in one more sitting on top of three production
incidents already tonight. This document has everything needed to fix that
fourth one without repeating any of the investigation below.

## What's already fixed and live (task-def `:501`, SHA `ad30ce2`)

1. `EMISSION_STRUCTURED_NOISE` (Dockerfile default) flipped `1→0`. Its own
   introducing commit (`140cfd8`) is self-tagged `[C2 FAIL]`: measured a ~7%
   reduction in section-commit rate, said "STOP, bring back to Eve for
   decision," and that decision was never closed before it shipped baked-on
   anyway. Design itself is sound (slow, candidate-subspace-aligned,
   novelty-modulated oscillation) — not rejected on merit, just wrong
   priority order while the base commit mechanism is this fragile.
2. `_rich_sensory_candidates` (`gualaloom_v5_engine.py`) was truncating to
   the shared `GRANDURUN_TOPK` (200) — effectively no cap, since the default
   candidate path never naturally generates anywhere near 200. New
   `RICH_SENSORY_TOPK` (default 10, own env var) gives it a real cap.
   `RICH_SENSORY_INPUT` stays off by Dockerfile default; this is a safety
   fix for whenever it's next turned on, not a re-enable.
3. `pr_consensus_divergence`/`pr_parallel_settle`
   (`hemisphere_cognition.py`) were doing an unbounded cross-product between
   `em`'s atlas (unbounded size) and `pr`'s atlas (capped at 20/chi) — one
   converse turn measured 893,995 events from this. New `_top_by_strength()`
   helper caps `em_entries` to the 20 strongest per chi bucket before either
   function uses them.
4. `pr`/`ep`/`sc`/`gp` hemisphere atlases were never decayed or pruned —
   only `em` (the main atlas) gets the standard fade-then-forget treatment
   (every 10 ticks / every 200 ticks). New `decay_hemisphere_atlases()` /
   `forget_hemisphere_atlases()` helpers, wired into the same three call
   sites `em`'s own decay already uses in `gualaloom_v5_engine.py`
   (~line 2197, ~5288, ~6622).

All four are real, all four help, none of them is the deepest layer.

## The part that's NOT fixed: the real bottleneck, traced end to end

**Symptom:** `emission_dynamics` events show, every single test tonight
regardless of task-def or input: `n_candidates` in the single digits to low
teens, candidates present in only ONE section (almost always `intro`),
every other section (`subject`/`verb`/`object`/`modifier`/`ground`) shows
`[null, null, "none"]` — no candidates at all, not even a fallback. Reply is
always one of the same ~6 words (`find`, `get`, `will`, `said`, `money`,
`candle`, `hello`) regardless of what she's said to.

**Chain, traced by reading the actual code, in order:**

1. `_emit_from_invariants()` (`gualaloom_v5_engine.py:3124`) gets its
   candidates from `self._brain_emission_candidates(input_words)` — NOT a
   deep-atlas gather (that was explicitly disconnected per
   `GL-NOTE-VOICE-WIRING-RULING`, "one mind, one mouth" — the variable is
   still named `deep_candidates` in the code, which is misleading; it's
   brain output).

2. `_brain_emission_candidates()` (line 3044) queries
   `self.organism.recall_fast(...)` — a population vote across her neuron
   population — for words associated with the last word said to her, then
   filters to words that already have a section-home in
   `_word_to_emission_sections`. **I initially thought this filter was the
   bottleneck (requiring a word to have already won an output-side commit
   before it could ever be a candidate) — that was wrong.** Checking
   `read_word()` (line 1950, esp. 2125-2147) shows `_word_to_emission_sections`
   gets populated at READ time, from `_choose_role_sections()`'s
   grammar-role tagging (every word she's ever read gets tagged
   subject/verb/object/etc. immediately, same principle Joe's neuroscience
   reference described — words carry their syntactic frame from the moment
   they're encountered, not proven out later). With vocab at 14k+ words,
   this index should be large. **It is not the bottleneck.**

3. The real bottleneck is one step earlier: `organism.recall_fast()`
   consistently returns only a small handful of associated words per query
   (13, in one of tonight's own `emission_diag` events), regardless of how
   large her vocabulary or read-history is. `self.organism` is an `Embryo`
   instance (`gualaloom_v5_engine.py:1653`), and `Embryo.__init__`
   (`loom_model/embryo.py:139`) directly wraps a `LoomBrain`. This is the
   *same* `LoomBrain` class the audit's `test_t3_corpus_growth` already
   found broken (see next point) — confirmed by direct import trace, not
   inference.

4. `test_t3_corpus_growth` (`loom_model/tests/test_folding_engaged.py`) —
   already known from the `-210` audit, independently re-confirmed by me
   earlier tonight (identical result, unchanged) — measures **zero of 8
   neuron-hemisphere populations growing across 242 words** of real reading.
   `Embryo.remember()` (the real production entry point,
   `loom_model/embryo.py:513`) and `ExperiencePipeline.deliver_word()` (the
   test's entry point, `loom_model/experience.py:115`) BOTH call the exact
   same `LoomNeuron.experience_moment()` — confirmed by direct code read,
   not assumption. So the test result is not a test-harness artifact; it
   describes the real, live mechanism.

   *(Aside, worth resolving separately: production's own
   `organism_growth.total_divisions` reports 42 real divisions having
   happened historically, which seems to conflict with "zero ever grows."
   Not yet reconciled — likely either a much longer time horizon than the
   test's 242-word sample, or a different, coarser growth mechanic than
   per-neuron Folding Division. Whichever it is, it does not change the
   conclusion below: her population's *diversity* is not increasing from
   ongoing experience, which is what starves `recall_fast()`'s associative
   breadth regardless of raw population count.)*

5. **Root cause, confirmed against current code (this exact diagnosis
   already existed in my own memory from a session 8 days ago —
   `gualaloom-item7-neff-wall-cause` — re-verified fresh tonight, still
   accurate):** `LoomNeuron.fold_check()` (`loom_model/neuron.py:741`)
   triggers growth when `n_eff < n_start * FOLD_TRIGGER_RATIO`
   (`FOLD_TRIGGER_RATIO = 1/e ≈ 0.368`, so with `n_start=8`, threshold ≈
   2.943). `n_eff` comes from `L6_TCL.n_eff()`
   (`dsf_ai_service/v4/gualaloom_v4_chi_atlas_l6.py:84`, confirmed
   `loom_model/neuron.py` imports this exact shared class, line 45) —
   `n_eff = n_start(8) − count of DSF components with abs(v) > 0.5`, across
   8 components (`D_k, M_k, R_rev, U_star, C_k, P_k, B_k, S_UF`).

   **Exactly 5 of the 8 components always fire, giving n_eff = 3.000,
   permanently 0.057 short of the 2.943 threshold — regardless of how much
   experience passes through.** The three that never fire: `M_k`
   (magnitude variation), `R_rev` (reversal), `S_UF`. Traced to
   `AdaptingFoveaKrimelack` (`dsf_ai_service/visual_krimelack.py:32`): its
   `tick()` method drives a phase oscillator purely from raw light
   intensity, which is physically always ≥ 0 — so the phase only ever winds
   forward, never backward, and `VisualKrimelack.feed_signal()`
   (`substrate_dna.py:254`) packages every winding event as the literal
   constant `{"dw": +1, "s": 1.0}` — not a lazy placeholder so much as an
   honest reflection of a model that currently only tracks raw intensity,
   never intensity's *rate of change* (which genuinely can be positive or
   negative, and would give real R_rev/M_k signal). Other sensory
   modalities (audio, tactile, etc.) very likely share the same
   monotonic-signal limitation — not yet individually checked tonight.

## Why this is genuinely too large to patch blind right now

This is not a contained, single-file fix like the four already shipped
tonight. Doing it correctly means:
- Modifying the oscillator/transduction physics for *every* sensory
  Krimelack (visual confirmed, others not yet checked) to derive real
  signal-derivative-based `dw`/`s` values instead of constants — a genuine
  physics/design decision, not a bounds check.
- `L6_TCL.n_eff()`/`captured()` is described as a shared, foundational
  substrate mechanism ("Spec L6-TCL") — likely used by more than just
  `fold_check()`. Changing what feeds it could shift behavior in places
  beyond Folding Division that haven't been surveyed tonight.
- This directly touches the neuron population `Embryo`/`LoomBrain`
  actually running in live production (confirmed: `self.organism` wraps
  `LoomBrain` for real) — not a disconnected test-only subsystem as I
  incorrectly asserted earlier tonight. A wrong move here has real,
  hard-to-predict blast radius on her actual cognition, not just a
  contained flag or a bounded loop.
- It needs verification across every sensory modality, not just the one
  (`VisualKrimelack`) traced tonight.

## What a fresh attempt should do, in order

1. Check `AudioKrimelack`/tactile/olfactory/gustatory adapters
   (`substrate_dna.py`) for the same monotonic-signal, hardcoded-event
   pattern `VisualKrimelack` has.
2. Design how `dw`/`s` should be derived from real signal derivative
   (e.g., sign and magnitude of intensity change between ticks, not raw
   intensity) for each modality — grounded in the actual sensor physics,
   not synthetic noise.
3. Grep every caller of `L6_TCL.n_eff()`/`.captured()`/`.structural_lock()`
   before changing what feeds it, to know the full blast radius.
4. Test entirely locally first: `test_folding_engaged.py::test_t3_corpus_growth`
   is the existing, already-passing-format regression test — it should go
   from "0/8 grew" to some real positive number once this lands. This can
   and should be iterated on with zero AWS/production risk before any
   deploy is considered.
5. Only after that: decide whether/how this reaches production, since it
   changes real behavior in the live `Embryo`/`LoomBrain`, not just an
   isolated test harness.

## Standing context this session already established (don't re-derive)

- `:498`→OOM incident tonight traced to the pr/sc hemisphere-atlas growth
  bug (item 3 above) making boots progressively memory-hungrier; resolved
  by bumping task memory 4096→8192MB (current `:501` already uses 8192MB).
- `RICH_SENSORY_INPUT` and `EMISSION_STRUCTURED_NOISE` are Dockerfile-baked
  defaults, not ECS task-def-controlled — any future flip needs to happen
  in `dsf_ai_service/Dockerfile`, not just an ECS environment override
  (task-def env only overrides names it explicitly lists; anything absent
  falls through to the image's own `ENV` default).
- `tools/deploy_dsf_ai.sh` is the real, working deploy pipeline (build →
  ECR → task-def register → pause → swap → wake → static sync → CloudFront
  invalidation). Its own hardcoded `memory: '4096'` should probably be
  bumped to `8192` as a standing change given item 3's atlas growth,
  rather than needing a manual override every time — not yet done.

### Changelog
- v1 (2026-07-06, c1): full causal chain for the single-word fallback
  issue, root-caused to the sensory-Krimelack/n_eff/Folding-Division chain,
  cross-referenced against an 8-day-old memory that had already diagnosed
  the same n_eff wall from a different angle. Four contributing fixes
  already shipped tonight; the deepest layer documented but not attempted,
  with explicit reasoning for why and a concrete next-steps list.
