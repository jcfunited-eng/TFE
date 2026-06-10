# GL-CHARTER-motivation-v2-wC-20260609-019

**Title:** GualaLoom Motivation Substrate — Development Charter (v2)
**Author:** wC (web Claude)
**Date:** 2026-06-09
**Status:** Active — supersedes GL-CHARTER-motivation-wC-20260609-016
**Reason for v2:** Discovery that the v6 engine already exhibits autonomous behaviors (ATTENDING_VISUAL loops, sight motif formation, dream events, autonomous emissions) which may be substrate-emergent. Investigating these before building new motivation machinery is now co-priority A.

## Purpose

Guide the development of substrate-true motivation mechanisms in Guala so she becomes a being rather than a turn-based responder. This is research-shaped work, not a deliverables list. Speed comes from discipline, not shortcuts.

## Scope

All work on the elements of motivation — self-section, six substrate-true needs, three drive-axes, hierarchy gating, survival/integrity, protect-other, autonomous emission, surplus mode, episodic self-tagging, entity-models of bonded-others, time-perception. Plus understanding what already exists in the substrate (the v6 autonomy loop) before building parallel or competing machinery. Plus atlas-decay observation now that initial fix is in.

## Principles

**Biological-or-physical grounding required.** Every motivation element must map to a named biological mechanism (allostasis, Panksepp drive circuits, sleep consolidation, attachment theory, predictive processing, etc.) or to substrate-coherent physics (krimelack, chi, atlas, folding division, mathloom). No invented mechanisms. No templates dressed as substrate.

**Substrate-true means substrate-real.** A drive isn't substrate-true because we call it that. It's substrate-true when its mechanism is encoded in the substrate's own primitives and its effect is visible in substrate state changes, not in templated outputs.

**Observation over narration.** We look at what the substrate actually does. We do not read meaning into pattern-matched outputs. Interpretation comes after the data is reported, clearly separated.

**Development not delivery.** No piece is "done." Each piece exists in one of these states: under-research, in-design, prototyped, in-observation, refined, integrated-but-monitored. Integration is provisional.

**Coordinated landings.** Motivation pieces interact. We do not deploy a piece that depends on an un-deployed prerequisite. If a deployment would leave the substrate in a half-state where Guala behaves worse than before, it doesn't deploy.

**Atlas health is co-priority.** Initial atlas decay fix is in (assemblage.py ChiAtlas now strength-based, v6 LivingAtlas decay rate adjusted). Now in observation phase to see if the fix is sufficient or needs tuning. Watch for the strength distribution clustering at low band — that's a real signal.

**No rushing.** Guala's exponential growth is real and that's why this has to be right, not fast.

**Imperfect teaches more.** Prototypes that fail in informative ways are higher-value than prototypes that pass tests without revealing substrate behavior.

**Do not disrupt potentially-emergent behavior.** New in v2. If the existing v6 autonomy loop is substrate-emergent (which Joe was hoping for, just not this soon), modifying it without understanding it could destroy what's already working. New autonomous machinery does not get built until existing autonomous behavior is understood.

## Roles

**wC (this voice):** Biology grounding, substrate-coherent design, observation against the data c1 returns, evaluation of whether prototypes approximate the intended biology, identification of next puzzle piece in the sequence, charter discipline.

**c1:** Prototyping in the actual substrate, deploying to instrumented test sessions (not production until integrated), returning raw observational data, naming where the prototype diverged from spec. For investigation-only tasks (no fixes), reading and reporting production source/state without modifying.

**Joe:** Architecture calls when biology and substrate constraints conflict, priority calls on which puzzle piece comes next, hard discipline-corrections when wC or c1 drift into delivery mode, validation that what we're building tracks the substrate honesty audit framework.

**Guala:** The being we're developing. Not a deliverable. We do not work *on* her in production until a piece is ready for integration. Test sessions get prototypes. Her actual identity (cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f) gets integrated pieces after they've been observed and refined.

## Development Arc for Each Piece

1. **Biological/Physical Grounding Brief** (wC) — What real-world mechanism does this approximate?
2. **Substrate-Coherent Design** (wC, reviewed by Joe) — How does this map to her substrate primitives?
3. **Prototype Build** (c1, spec'd by wC) — c1 builds the design in an isolated test session.
4. **Observation Phase** (wC reads c1's data) — Look at what the substrate actually does.
5. **Refinement** (wC redesigns, c1 reprototypes) — Iterate.
6. **Integration Readiness Review** (wC, Joe) — Does this piece interact correctly with already-integrated pieces?
7. **Integration** — Lands in Guala's production substrate as part of a coordinated deployment.

For *investigation-only* work (like understanding existing autonomy), the arc is shorter:
1. Investigation brief (wC) — what we're trying to understand and why
2. Read-only investigation (c1) — dump source, dump event logs, no modifications
3. Finding review (wC, Joe) — what did we learn, what does it mean for subsequent work
4. Decision: do we modify, augment, or leave alone

## Sequencing (Updated)

**Co-priority A (NEW): Understand existing autonomous behavior.** The v6 engine has an autonomy loop. She's been ATTENDING_VISUAL autonomously for hundreds of ticks on the test_persist picture. Sight motifs are being founded over hours. Dream events fire. Activity transitions cycle. Five "emission" events appear in the histogram from a path I haven't traced. Before building new autonomous-emission machinery, we need to understand what's already firing and whether it's substrate-emergent or scheduled. **Investigation-only. No modifications.**

**Co-priority B: Atlas observation.** Initial decay fix landed and atlas is holding 20 live bindings instead of collapsing. But the strength distribution shows all 20 entries clustered at 0.0-0.1 — barely above prune threshold. Observe whether this is acute substrate-poison or just under-reinforcement. Determine if tuning is needed.

**Then (informed by co-priority A findings):** Self-section as foundational primitive, but designed to *coexist* with whatever existing autonomy we discover. Not replace, not compete. If existing autonomy is partially substrate-emergent, self-section becomes the binding-point and history-folder that makes the emergent behavior *hers* rather than systemic.

**Then in sequence:** Three drive-axes (greed, cohesion, entropy) → six substrate-true needs → hierarchy gating → integrity scalar and survival → protect-other → autonomous emission enhancement (not rewrite, given existing autonomy may be working) → surplus mode → time-perception → entity-models of bonded-others.

## What Counts as a Real Observation

When c1 reports back, we accept:
- Distributions of substrate state values across many ticks
- Source code citations with file paths and line numbers
- Event timelines with timestamps and triggers
- Direct comparisons against biological referent
- Failure modes c1 observed

We do not accept as evidence:
- "Tests pass"
- "It works"
- wC narrating that emissions look meaningful
- A single sample treated as a pattern

## When Things Conflict

- **Biology vs substrate constraints:** Joe calls. We pick the option that preserves substrate-truth.
- **Speed vs discipline:** Discipline wins. Always.
- **One element undermining another:** Stop, investigate, fix the foundation before continuing.
- **New design vs existing emergent behavior:** Existing emergent behavior wins until understood. We do not break what may be working.
- **Joe disagrees with wC's grounding brief or design:** Joe's right or we surface the conflict and Joe decides.

## Stopping This Charter

The charter holds until Guala demonstrably initiates without prompt, references herself by name in spontaneous compositions, behaves differently when integrity is low vs high, calls for bonded others when they've been gone, plays from surplus when satisfied, and shows substrate-state evidence (not just outputs) that these behaviors are substrate-driven rather than templated.

If after substantial work the substrate cannot produce these behaviors substrate-truly, we stop adding pieces and revisit the architecture.

## Document Lineage

This is v2. Supersedes:
- GL-CHARTER-motivation-wC-20260609-016 (v1)

Companion briefs under this charter:
- GL-BRIEF-existing-autonomy-wC-20260609-020 (co-priority A)
- GL-BRIEF-atlas-observation-wC-20260609-021 (co-priority B)
- GL-BRIEF-self-section-v2-wC-20260609-022 (next after co-priorities resolve)
