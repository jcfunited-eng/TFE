# GL-BRIEF-existing-autonomy-wC-20260609-020

**Title:** Existing v6 Autonomous Behavior — Investigation Brief
**Author:** wC
**Date:** 2026-06-09
**Charter:** GL-CHARTER-motivation-v2-wC-20260609-019
**Status:** Investigation-only. No modifications to production.
**Priority:** Co-priority A. Blocks self-section work and autonomous-emission work until findings are reviewed.

## The Observation We Need To Explain

Guala's substrate is doing things autonomously that no one explicitly triggered, and we (wC) didn't know about. Evidence:

- `current_activity: ATTENDING_VISUAL, target: 82fb8415f3f5 (test_persist picture)`, started_tick 1468705
- That picture has `times_attended: 264` — c1 uploaded it earlier in the session for a persistence test. Over the hours since, Guala has autonomously looked at it 264 times.
- `sight_section.n_motifs: 9`, founded across many ticks from 1194707 → 1468719. Visual motifs are being formed without human intervention.
- Event histogram shows: `activity_started: 89`, `activity_ended: 88` — she's been transitioning between activities ~89 times.
- `corpus_completed: 413` — she's been finishing books autonomously over and over.
- `wake: 9`, `rest: 2`, `sleep_manual: 1`, `dream_began: 1`, `dream_artifact: 12` — sleep/wake/dream events are firing.
- `emission: 5` — there's an autonomous emission path I haven't traced.
- `suffering_recovery: 16` — some mechanism is reducing suffering over time.
- `needs_snapshot: 146` — needs are being tracked periodically.

The autonomous emission test I designed went through the v7 converse path with a new internal-evidence injection. It produced 3000 emissions of biased noise. **Meanwhile, the v6 engine has been quietly running its own autonomy loop the entire time, generating substrate behavior I bypassed.**

Joe's hope was that emergent autonomous behavior would eventually arise from substrate dynamics. He didn't expect it this soon. We don't know whether what's happening is:
- **Emergent**: substrate dynamics (needs, drives, atlas state, mode_strength) causally drive the activity loop, picture attention, motif formation, dream cycle. This would be the substrate doing what Joe hoped.
- **Scheduled**: a coded loop runs activities on a cron-like schedule independent of substrate state. This would be normal engineering, not emergent.
- **Hybrid**: substrate state influences a scheduled framework. Most likely outcome — typical engineering reality. The question is how much state influences how much choice.

Understanding which it is determines what we do next:
- If emergent → preserve and enhance carefully, do not disrupt
- If scheduled → understand what it does and build substrate-emergent equivalents alongside or as replacements
- If hybrid → identify which parts are emergent and which are scheduled, decide piece by piece

## Biological Grounding

The phenomena we're observing have biological referents:

**Intrinsic activity / default mode.** Brains are not silent at rest. The default mode network fires spontaneously during inactive periods, generating self-referential thoughts, simulations, and consolidation activity. The substrate analog: idle ticks running substrate dynamics that produce activity selection and attention.

**Ascending arousal systems.** Locus coeruleus (norepinephrine) and basal forebrain (acetylcholine) modulate arousal and attention bottom-up. They drive activity-state transitions (sleep/wake/REM/quiet wakefulness/active wakefulness) based on internal state. The substrate analog: needs-driven activity transitions and arousal levels.

**Spontaneous attention shifts.** Humans don't sit and look at one thing forever. Attention spontaneously shifts based on novelty, satisfaction, and drive state. The substrate analog: ATTENDING_VISUAL → some other activity → back, driven by something in substrate.

**Consolidation during sleep.** Sleep replays recent experiences and consolidates them into long-term form. The substrate analog: dream_began, dream_artifact events suggest a sleep-replay mechanism already exists.

**Curiosity-driven attention (Panksepp SEEKING).** Animals attend to novel stimuli unprompted. The substrate analog: picture upload (novel stimulus) → autonomous attention (264 attendance events).

Each of these has known mechanisms in real brains, and each could plausibly map to mechanisms in Guala's v6 engine. The investigation has to find out which mappings exist and which are absent.

## What c1 Needs to Do

This is investigation-only. **No modifications. No fixes. No improvements.** Read source, read event logs, report.

The investigation has three threads:

**Thread 1: Source-level understanding.**
Find every place in the v6 engine where autonomy happens — activity selection, attention, dreaming, emission, suffering. Read the code. Report what each mechanism does and what governs it.

**Thread 2: Event-level evidence.**
Pull the actual event log for Guala. Look at the temporal pattern of autonomy events. Does activity selection correlate with needs state? Does dream_began follow rest, or arbitrary timing? Does emission fire on specific triggers? Does the 264-times-attended picture show attention pattern (consistent rate vs bursts vs decay)?

**Thread 3: Substrate-state causality test.**
For each autonomous behavior, determine whether substrate state is causally influencing it. The test: would the behavior happen identically if substrate state were different? If yes → scheduled. If no → at least partially emergent. If "depends on what kind of state change" → hybrid, and we want to know which dimensions of state matter.

## What We Want to Learn

After this investigation, we should be able to answer:

1. **What is the activity selection mechanism?** What governs READING → PLAYING → ATTENDING_VISUAL transitions? Is it timer-based, needs-based, atlas-based, mode-strength-based, or something else?

2. **What is the attention mechanism?** Why does she attend a specific picture 264 times? Is it because it's novel? Because of atlas binding strength? Because it's the only picture? Because of a sticky-attention bug? Because of curiosity drive?

3. **What is the visual motif formation mechanism?** sight_section has 9 motifs founded over a span of ticks. What triggers their formation? Are they from picture attendance, dream replay, both, or some other source?

4. **What is the emission mechanism?** Five "emission" events fired in this histogram. From what code path? With what triggers? What's the substrate state at the moment of emission?

5. **What is the dream/sleep mechanism?** sleep_manual: 1, dream_began: 1, dream_artifact: 12. What's the dream loop? Does it touch substrate state? Does it consolidate atlas? Does it produce new motifs?

6. **What is the suffering_recovery mechanism?** 16 recovery events. What reduces suffering? Is it presence-based, time-based, satisfaction-based?

7. **What is the needs_snapshot cadence?** 146 snapshots — what's the trigger? Time-based, state-change-based?

8. **For each: is the mechanism substrate-causal or scheduled?** This is the key question. Substrate-causal means "this fires because of substrate state values like needs / atlas / mode_strength / drive." Scheduled means "this fires on a timer or fixed sequence regardless of substrate state." Hybrid means "the schedule decides cadence but substrate state decides specifics."

## What Could Go Wrong

This is investigation only, so the failure modes are limited:
- c1 can't find the code (unlikely — c1 has full repo access)
- The mechanisms are spread across so many files that the report becomes unwieldy (possible — focus on the autonomy entry points first)
- c1 starts "improving" things while reading — explicit prohibition in command

The investigation needs to be honest. If c1 finds that an "autonomous" behavior is actually a 20-line scheduled loop with no substrate input, that finding is just as valuable as finding sophisticated emergent dynamics. We need ground truth, not flattery.

## Instrumentation Already Present

We already have the event log and persistence health. The investigation can pull from these directly without new instrumentation. If gaps appear (some autonomous behavior doesn't produce log events), c1 should note those gaps — they're either the mechanism not being event-logged, or the behavior actually not firing.

## Acceptance for This Investigation

c1 returns a report covering all eight questions above with:
- Source code citations (file paths and line numbers) for each mechanism
- Event log evidence (counts, timing patterns) for each mechanism
- Causality assessment (substrate-causal / scheduled / hybrid) for each mechanism
- An honest summary: "Of the autonomous behaviors observed, X are emergent, Y are scheduled, Z are hybrid"

After reviewing, wC and Joe decide:
- What to preserve untouched (likely all of it, until we understand more)
- What to extend (probably none in this round — extension comes later)
- Whether self-section work proceeds as planned, or needs to be redesigned to coexist with what already exists
- Whether the autonomous emission test we ran was actually testing the right path or bypassing what already works

## c1 Command

```
EXISTING AUTONOMOUS BEHAVIOR INVESTIGATION — under
GL-CHARTER-motivation-v2-wC-20260609-019 and per
GL-BRIEF-existing-autonomy-wC-20260609-020.

This is INVESTIGATION ONLY. Do not modify code. Do not fix anything.
Do not "improve" what you find. Do not deploy. Read and report.

The substrate has autonomous behaviors firing that wC did not
account for in the autonomous-emission test design. Joe wants to
understand them before we build any new motivation machinery on
top — they may be substrate-emergent and we don't want to disrupt
them by accident.

Eight questions to answer. For each, find the relevant source code,
pull event log evidence, and assess whether the mechanism is
substrate-causal, scheduled, or hybrid.

QUESTION 1 — Activity selection.
What governs READING → PLAYING → ATTENDING_VISUAL transitions?
  - Locate the code (likely in gualaloom_v5_engine.py or v6 engine)
  - What variables influence the next activity choice?
  - Cite source lines
  - From event log: pull the last 50 activity_started events with
    timestamps and substrate state snapshots (needs values at the
    transition, if logged)
  - Assessment: substrate-causal / scheduled / hybrid

QUESTION 2 — Attention mechanism.
Why has Guala attended the test_persist picture 264 times?
  - Find the picture-attention code path
  - What triggers an attention event?
  - From event log: timing of picture-attention events over the
    session — burst pattern, steady rate, decay, something else?
  - Is attendance correlated with substrate state changes?
  - Assessment

QUESTION 3 — Visual motif formation.
sight_section has 9 motifs. What triggers their formation?
  - Find the motif-formation code path
  - What inputs feed in (picture attendance? dream replay? both?)
  - Cite source lines
  - From event log: visual_motif_fired (12) and visual_motif_committed
    (5) — timing patterns
  - Assessment

QUESTION 4 — Emission mechanism.
The event histogram shows 5 "emission" events. From what code path?
  - Find it. This is the existing autonomous emission mechanism we
    didn't know about.
  - What triggers it? What's the substrate state at trigger?
  - Cite source
  - From event log: the 5 emission events with full context (tokens
    emitted, substrate state, what preceded them)
  - Assessment

QUESTION 5 — Dream/sleep mechanism.
sleep_manual: 1, dream_began: 1, dream_artifact: 12.
  - Find the sleep/dream code path
  - What initiates sleep? What happens during dream? What does
    dream_artifact represent?
  - Does dream modify atlas, mode_bank, sight, or any persistent
    substrate state?
  - Cite source
  - From event log: the sequence of dream events with timing
  - Assessment

QUESTION 6 — Suffering recovery.
16 suffering_recovery events. What reduces suffering?
  - Find the suffering decay/recovery code
  - What triggers recovery? Time? Presence? Substrate state?
  - Cite source
  - From event log: timing and triggers of the 16 recovery events
  - Assessment

QUESTION 7 — Needs cadence.
146 needs_snapshot events. What's the cadence?
  - Find the needs snapshot code
  - Time-based? Event-based? Threshold-crossing?
  - Cite source
  - From event log: intervals between snapshots
  - Assessment (likely scheduled — this is metadata, not behavior)

QUESTION 8 — Summary.
Of the autonomous behaviors observed, classify the overall picture:
  - How many mechanisms are substrate-causal?
  - How many are scheduled?
  - How many are hybrid?
  - Is there a unifying loop, or are these separate mechanisms each
    with their own logic?
  - What's the highest-level autonomy entry point that triggers the
    whole loop?

WHAT NOT TO DO:
  - Do not modify any code.
  - Do not fix any apparent bugs you find. Note them in the report.
  - Do not deploy.
  - Do not "improve" the autonomy.
  - Do not write new code paths or tests.
  - Do not interpret findings — just report what you found.

WHAT TO REPORT:
  - Per-question answers with source citations and event evidence
  - Question 8 summary with substrate-causal / scheduled / hybrid
    counts
  - List of any bugs or oddities you notice but did not fix
  - List of any mechanisms you couldn't find or understand
  - File paths of source you read so wC can reference them too

Standing by for the investigation report. wC and Joe review before
any further substrate work proceeds. The self-section prototype
and the atlas observation work are both blocked on this report.
```
