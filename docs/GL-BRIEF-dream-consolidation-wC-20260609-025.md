# GL-BRIEF-dream-consolidation-wC-20260609-025

**Title:** Dream Consolidation — Grounding Brief and Implementation Spec
**Author:** wC
**Date:** 2026-06-09
**Charter:** GL-CHARTER-motivation-v3-wC-20260609-024
**Status:** Design ready. c1 command ready to send after Vision Stage 1 lands and is observed.
**Priority:** Highest leverage of remaining motivation work. One change, multiple wins.

## What This Fixes

Bug #3 from GL-RPT-autonomy-investigation-20260609: dream phase samples atlas read-only. The implementation comment said "consolidation" but the code only reads — it never reinforces.

Code path: `_atick_dreaming` in `gualaloom_v5_engine.py` lines 1519–1551. Every 200 ticks during dream phase, the code samples 3 random chi keys from atlas, looks up mode words + sight motifs at those addresses, logs a `dream_artifact` event. Atlas state is not modified.

Real sleep biology says replay strengthens. Without that, atlas entries hover at low strength forever (which is exactly what we observed: 20 entries clustered at 0.0-0.1 band post-fix). The decay-fix prevented mass collapse. Reinforcement-during-dream completes the cycle.

## Biological Grounding

**Sleep-dependent memory consolidation.** The most-replicated finding in modern memory neuroscience: memories formed during waking are labile and become durable through sleep replay. Slow-wave sleep (SWS) replays hippocampal sequences in compressed form, strengthening cortical traces that encode the same patterns. REM sleep consolidates emotional and procedural memories. Without sleep, daytime learning fades. With sleep, traces become persistent.

The mechanism is LTP-on-replay: when a memory trace fires during sleep, the same synaptic strengthening that LTP produces during waking happens again, with the consolidation-favoring conditions of sleep (high acetylcholine, reduced sensory interference, specific brain rhythms). Spike-timing-dependent plasticity during replay sequences is what makes the trace durable.

**Spike replay in hippocampus.** Wilson and McNaughton (1994), Pfeiffer and Foster (2013), and many others: during SWS, hippocampal place cells fire in the same sequences they fired during awake exploration, but compressed 5-20x in time. These replays drive cortical strengthening. Sequences that were experienced are the ones that get replayed and strengthened.

**The two-stage model (McClelland, McNaughton, O'Reilly 1995).** Hippocampus acquires episodes rapidly during waking. Neocortex consolidates them slowly via sleep replay. The brain doesn't try to learn everything immediately — it delays cortical learning to a phase (sleep) where interference is low and replay is selective.

**The substrate-relevant insight:** dream-replay isn't passive observation. It's the mechanism by which experiences become memories. Our atlas is the substrate's equivalent of cortical memory. Dream should be where atlas entries get strengthened.

## The Simplest Sufficient Approximation

During dream phase, when chi-address sampling finds atlas entries, those entries get reinforcement (+strength). Same reinforcement increment that atlas re-encounter uses during waking. Apply to every atlas entry sampled during dream.

That's the core fix. Three sub-questions to address in design:

1. **Selective reinforcement?** Real biology is selective — emotionally salient or task-relevant memories get more replay weight. For initial fix: uniform reinforcement on sampled entries. Selectivity can be added later when self-section exists (self-tagged entries could get extra weight).

2. **More replays per dream?** Current dream samples 3 chi keys every 200 ticks. Over a 2500-tick dream phase: ~12 sampling events × 3 keys = 36 entry-touches per dream. That's small relative to atlas size (currently 20 entries; would grow). May want more replay density. Initial fix: keep current cadence, observe whether 36 reinforcements per dream is enough. If atlas still under-reinforced, increase density.

3. **Sequence replay vs random sampling?** Real biology replays sequences, not random points. Our current implementation samples random chi addresses. Sequence replay is more biological but more complex to implement. Initial fix: keep random sampling. Sequence-aware replay is a future enhancement.

## Substrate-Coherent Design

### What Stays the Same

- Dream initiation: needs-driven sleep selection or manual sleep
- Sleep phase first 2500 ticks (existing decay + needs recovery)
- Dream phase second 2500 ticks (existing chi sampling + dream_artifact logging)
- Sampling cadence (every 200 ticks, 3 chi keys per sample)
- Random chi-address sampling (sequence-aware replay is future work)
- Dream artifact logging unchanged

### What Changes

In `_atick_dreaming` at the chi-sampling step: when an atlas entry is returned from the lookup, call `atlas.reinforce(chi_address)` — same reinforcement path as waking re-encounter (+0.1 strength, capped at 1.0 or whatever the ceiling is).

If both mode_bank lookup and sight motif lookup return entries: both get reinforced.

Log the reinforcement as part of the dream_artifact event: add fields `reinforced_chi_addresses: [list]` and `reinforcement_count: N` so we can observe the consolidation activity.

### What This Doesn't Change

- Mode_bank: dream still doesn't modify mode_bank vectors or salience — the substrate-honest interpretation is that mode_bank carries the substrate's vocabulary of patterns, and dream consolidates the *bindings* (atlas) not the *vocabulary* (modes)
- Sight motifs: dream doesn't create new visual motifs or modify motif chi_profiles — only the atlas-level bindings get reinforced
- Needs: dream continues to recover stability and novelty as before
- Krimelack: dream doesn't fire krimelack — sensory processing is for waking

This preserves all existing behavior. Adds reinforcement only at the atlas layer.

## Hypothesis This Tests

The atlas-strength-clustered-at-low-band observation (all 20 entries at 0.0-0.1 band, mean 0.07) has two competing explanations:

- **Tuning hypothesis:** reinforcement rate (+0.1 per re-encounter) is too small relative to decay
- **Reinforcement-frequency hypothesis:** entries don't get re-encountered enough during waking activity, so they decay without being touched

Dream consolidation tests both. If dream-replay reinforces 36 entries per dream cycle (and dreams happen periodically when stability deficit triggers sleep), atlas entries get reinforced even if waking re-encounters are sparse. After this fix:

- If atlas strength distribution shifts upward (entries appear in 0.3+ bands) → reinforcement-frequency hypothesis confirmed, fix works
- If atlas strength stays clustered low even with dream consolidation → tuning hypothesis still applies, increase reinforcement magnitude
- If atlas strength shifts upward but then over-saturates (entries all at 1.0) → reinforcement is too generous, tune down

This is a clean experiment. One change, observable outcome, multiple possible learnings.

## Coexistence With Existing Autonomy

This is a minimal substrate change inside the dream phase. Nothing about activity selection, attention, emission, suffering, or any other autonomy mechanism is affected. The change is at the lowest level — what dream's existing chi-sampling does when it finds an entry.

## Instrumentation

The dream_artifact event already logs sampled chi-addresses and recalled content. Add to the event:
- `reinforced_atlas_addresses: [list of chi addresses reinforced]`
- `reinforcement_count: integer`
- `pre_strength_sum: float` (atlas total strength before this dream cycle's reinforcements)
- `post_strength_sum: float` (after)

This lets us observe per-dream atlas reinforcement directly.

## Acceptance for This Piece

After deploy and at least one dream cycle:

- `dream_artifact` events show `reinforcement_count > 0`
- Atlas strength distribution measurably shifts upward over multiple dream cycles
- No regression in other behavior — activity selection still works, emission still fires when conditions met, suffering recovery unchanged, sight motifs continue forming

If atlas strength distribution doesn't shift after several dream cycles, that's data — go back to tuning. If it shifts too aggressively (saturates at 1.0), that's also data — reduce reinforcement magnitude. Either way we learn something the current substrate isn't teaching us.

## c1 Command

```
DREAM CONSOLIDATION — under GL-CHARTER-motivation-v3-wC-20260609-024
and per GL-BRIEF-dream-consolidation-wC-20260609-025.

DO NOT START until Vision Stage 1 has landed and been observed by
wC. The vision fix is independent but we are sequencing landings
so each can be observed alone before the next.

GOAL: Fix bug #3 from the autonomy investigation report. Dream
phase currently samples atlas read-only. After this change, dream
sampling also reinforces the sampled entries (LTP-on-replay biology).
This may resolve the atlas-strength-clustered-at-low-band issue
in one stroke.

STEP 1 — Audit existing dream code.

Read _atick_dreaming in gualaloom_v5_engine.py lines 1519-1551.
Report the exact sampling mechanism (how chi keys are picked, how
lookup happens, how dream_artifact is constructed).

STEP 2 — Add reinforcement at sample time.

When _atick_dreaming samples a chi address and the lookup returns
an atlas entry (mode_bank OR sight motif), call the same
reinforcement path that waking re-encounters use. Increment
strength by the same amount (+0.1 or whatever the current
re-encounter increment is), capped at the existing ceiling.

If both mode_bank and sight motif lookups find entries at the
same chi address: reinforce both.

STEP 3 — Augment dream_artifact event logging.

For each dream_artifact event, also log:
  - reinforced_atlas_addresses: list of chi addresses that were
    reinforced this sampling cycle
  - reinforcement_count: integer count of entries reinforced
  - pre_strength_sum: atlas total strength at start of this dream
    cycle
  - post_strength_sum: atlas total strength at end of this dream
    cycle

This lets wC observe per-dream atlas reinforcement directly from
the event log.

STEP 4 — Deploy to production.

This is a small, low-risk change at a clear hook point. Deploy
to Guala (cdef9bcf) — this is enhancement of existing autonomy,
not new substrate primitive. Per the charter, this counts as
integration-readiness because:
  - It's a single bug fix at a specific line range
  - Behavior is reversible by reverting one commit
  - Failure mode is at most: atlas strength changes don't behave
    as expected, which is observable and bounded
  - It doesn't introduce new state, only modifies existing
    operation

STEP 5 — Observe and report.

After deploy, watch for at least 30 minutes of substrate time
(allow at least one full sleep cycle to occur — sleep is
needs-driven so wait until stability deficit triggers it, OR
trigger manual_sleep from UI for faster observation).

Report:
  - Commit SHA
  - dream_artifact events from the observation window with full
    new fields
  - Atlas health snapshot (strength distribution by band) before
    deploy and after at least one dream cycle
  - Whether atlas strength distribution shifted upward
  - Any regression in other autonomy events (activity_started/ended
    rate, emission events, suffering_recovery rate)
  - Honest narrative of what surprised you, what diverged from
    spec

WHAT NOT TO DO:
  - Do not start before Vision Stage 1 is observed by wC
  - Do not change anything else about dream — no new chi sampling
    sequences, no changes to needs recovery, no changes to dream
    cadence
  - Do not modify mode_bank or sight motif data during dream
    (only atlas reinforcement)
  - Do not modify the atlas reinforcement function itself (use
    the existing waking-reinforcement path)
  - Do not skip the observation step

This is a substrate enhancement, not a new primitive. The bar is:
existing dream behavior preserved, atlas reinforcement added,
observable outcome.
```
