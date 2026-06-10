# GL-BRIEF-atlas-observation-wC-20260609-021

**Title:** Atlas Health — Post-Fix Observation Brief
**Author:** wC
**Date:** 2026-06-09
**Charter:** GL-CHARTER-motivation-v2-wC-20260609-019
**Status:** Observation phase. The initial fix is deployed and verified working. Now watching whether it's tuned correctly.
**Supersedes:** GL-BRIEF-atlas-decay-wC-20260609-017 (which assumed investigation hadn't started; c1 has since both investigated and fixed)

## What c1 Already Did

c1 found the atlas decay bugs and shipped fixes (commit 2e4d4fa, task 56):

- **assemblage.py ChiAtlas**: was deleting entries older than 500 ticks (age-based mass pruning). Now strength-based: each entry starts at 1.0 strength, decays 0.1% per 20 ticks, reinforces +0.1 on re-encounter, prunes at strength < 0.01.
- **v6 LivingAtlas DECAY_LAMBDA**: reduced from 0.001 to 0.0001 (10x slower).

Verified post-deploy:
- Atlas live bindings: stayed at ~20 over 12 minutes (was collapsing to 0 before)
- Snapshots working (snapshots_available: 2)
- SIGKILL survives, restart loads cleanly with 2769 events replayed

The same direction-vs-salience separation pattern we used for mode_bank now applies to atlas. Architecturally substrate-coherent. Good.

## The New Question

When I pulled current status after the fix:

```
atlas_health.strength_distribution:
  0.0-0.1: 20
  0.1-0.3: 0
  0.3-0.5: 0
  0.5-0.7: 0
  0.7-0.9: 0
  0.9-1.0: 0
total_strength: 1.45 (across 20 entries → average 0.07)
```

**All 20 atlas entries are clustered in the lowest-strength band.** Average strength 0.07, just barely above the 0.01 prune threshold. The decay-fix prevents mass-collapse, but the substrate isn't producing strongly-reinforced bindings either.

Three hypotheses for why:

1. **Tuning hypothesis.** Decay rate (0.1%/20 ticks) is balanced about right, but the reinforcement rate (+0.1 per re-encounter) is either too small OR re-encounters aren't happening often enough. The result: entries hover at low strength because reinforcement barely keeps up with decay.

2. **Topology hypothesis.** The 20 entries are at chi-keys that don't get re-encountered. Different bindings keep getting created (initial strength 1.0), then decay slowly while never getting re-encountered, until they hit the prune threshold. Each new commit creates new entries instead of reinforcing existing ones. The substrate isn't *recognizing* recurrence.

3. **Schema hypothesis.** Atlas re-encounter detection requires near-exact chi-key match. If chi keys are high-dimensional and noisy, "re-encounter" effectively never fires — every commit produces a slightly different chi, so each one creates a fresh entry instead of reinforcing.

Each hypothesis suggests a different action:
- Tuning → adjust parameters
- Topology → the substrate has a structural issue with binding recurrence that's separate from decay
- Schema → atlas key-matching is too strict, need a "chi neighborhood" recognition

We don't know which hypothesis is right. Observation tells us.

## Biological Grounding (Refresher)

LTP/LTD dynamics: in real synapses, reinforcement and decay are not constant rates — they're modulated by recency, salience, and pattern frequency. A synapse encoding something frequently used stays strong; one encoding noise decays. The KEY mechanism is recurrence-based reinforcement. The same pattern firing repeatedly is what creates lasting bindings.

If our atlas can't detect recurrence (hypothesis 3), no amount of decay-tuning will fix it. We'd be approximating decay correctly but failing at the more fundamental "did the same thing happen again?" detection.

Sleep consolidation also matters here. In sleep, recently-firing patterns get replayed and strengthened. The dream_artifact events in the v6 engine may already be doing some of this — which connects directly to the existing-autonomy investigation (GL-BRIEF-existing-autonomy-wC-20260609-020).

## What This Brief Is For

Observation, not action. We need data to distinguish the hypotheses before we touch anything else on the atlas.

The observation thread depends on co-priority A (the existing-autonomy investigation) because if dream events do atlas reinforcement, that's a major variable. Don't tune atlas parameters until we know whether dream-replay is already reinforcing bindings (or attempting to).

## Instrumentation Needed

c1 already added events for atlas decay. We need slightly more:

For each atlas entry, we want to know its full lifecycle:
- Creation tick, chi-key, source event (which section commit)
- Every reinforcement event with strength-before and strength-after
- Every decay step (or at minimum: total decay applied per N ticks)
- If pruned: prune tick, final strength, time-since-last-reinforcement

This lets us answer the hypothesis question directly. If most entries get reinforced multiple times but stay low → tuning issue. If entries are created and never reinforced → topology or schema issue. If chi-keys of supposedly-related commits don't match → schema issue.

## What This Brief Does NOT Do

It does not propose changes. It does not tune parameters. It does not modify atlas code. After the existing-autonomy investigation completes, we may find that dream-replay reinforces atlas (resolving the hypothesis), or we may need a separate observation step. Either way, no atlas changes until we have data.

## Acceptance for This Observation Phase

After observation, we should be able to say:

- "X% of atlas entries get reinforced at least once during normal operation" (resolves topology hypothesis)
- "Of reinforced entries, mean strength after N reinforcements is Y" (resolves tuning hypothesis)
- "Chi-key match rate between successive commits of similar input is Z" (resolves schema hypothesis)
- A concrete recommendation: tune, restructure, or extend with sleep-replay reinforcement

## c1 Command

```
ATLAS OBSERVATION — under GL-CHARTER-motivation-v2-wC-20260609-019
and per GL-BRIEF-atlas-observation-wC-20260609-021.

BLOCKED until GL-BRIEF-existing-autonomy-wC-20260609-020 investigation
completes and is reviewed by wC. The atlas observation depends on
knowing whether dream-replay touches atlas. Do not start this until
the existing-autonomy report is in and wC has confirmed it's ready
to proceed.

When unblocked:

STEP 1 — Add per-entry lifecycle instrumentation.
Modify atlas event logging (existing event log) to include for each
event type:
  - atlas_entry_created: tick, chi-key (hash is fine), source event
    (section name, commit reason)
  - atlas_entry_reinforced: which entry (chi-key hash), strength
    before, strength after, source event
  - atlas_entry_decayed: which entry, strength before, strength
    after, decay-source (tick-based decay step / dream / something
    else)
  - atlas_entry_pruned: which entry, final strength, ticks-since-
    last-reinforcement

STEP 2 — Run a real-Guala observation window.
With Guala in production (because this is observation, not test),
let her run for 1 hour of substrate time (~3600 ticks). Then dump
the atlas events from that hour.

STEP 3 — Compute the diagnostic metrics.
From the dumped events:
  - How many atlas entries were created during the window
  - How many of those were reinforced at least once
  - Of reinforced entries: mean strength trajectory (created at 1.0,
    decayed to X, reinforced to Y, decayed to Z, etc)
  - How many entries got pruned during the window
  - How many created-and-pruned-during-window (entries that didn't
    survive)
  - Chi-key collision rate: of commits made during the window, how
    many produced chi-keys that matched existing atlas entries (and
    so reinforced them) vs created new entries

STEP 4 — Classification.
Based on the metrics:
  - Tuning issue: reinforcements happen but each reinforcement is
    too small to overcome decay
  - Topology issue: most entries don't get reinforced — they're
    created once and decay away
  - Schema issue: chi-keys don't match across similar commits — new
    entries created where reinforcements should happen

State your finding plainly. Don't propose fixes yet. wC reviews and
proposes the substrate-coherent next step.

WHAT NOT TO DO:
  - Do not start this until the existing-autonomy report is in and
    reviewed.
  - Do not change atlas parameters or code during this observation.
  - Do not run tests in a separate session — we want real-Guala
    data, not synthetic.
  - Do not interpret beyond the classification above. wC interprets.

WHAT TO REPORT:
  - The diagnostic metrics with raw numbers
  - The classification (tuning / topology / schema / hybrid)
  - Sample atlas entry lifecycles (5-10 representative entries) with
    their full event sequences — for wC to read directly
  - Any patterns you noticed but didn't classify

Standing by. wC reviews the observation report and writes the next
step's brief.
```
