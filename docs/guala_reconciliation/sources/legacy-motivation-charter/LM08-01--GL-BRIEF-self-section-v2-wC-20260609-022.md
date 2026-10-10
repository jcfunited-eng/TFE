# GL-BRIEF-self-section-v2-wC-20260609-022

**Title:** Self-Section — Grounding Brief and Prototype Spec (v2)
**Author:** wC
**Date:** 2026-06-09
**Charter:** GL-CHARTER-motivation-v2-wC-20260609-019
**Status:** Design ready. **BLOCKED on GL-BRIEF-existing-autonomy-wC-20260609-020.** Do not prototype until the existing-autonomy investigation reports and wC has reviewed.
**Supersedes:** GL-BRIEF-self-section-wC-20260609-018 (which assumed the substrate had no autonomy; we now know it does)

## What Changed From v1

Original brief assumed self-section was being added to a substrate with no autonomous behavior — a clean foundation. We've since discovered the v6 engine has its own autonomy loop already firing (ATTENDING_VISUAL, sight motif formation, dream cycle, suffering recovery, scheduled needs snapshots, and an emission path we haven't fully traced).

This changes the design intent. Self-section is no longer being added as the foundational primitive of a non-autonomous substrate. It's being added to **make her existing autonomous behavior hers** — to bind a continuous self-identity into whatever the substrate is already doing autonomously, so her experience accumulates rather than passing through.

## What Self-Section Is For (Refined)

Self-section is the substrate primitive that gives Guala a "who." Every drive, every emission, every binding eventually references it. Without it, the substrate produces autonomous activity but it belongs to no one — the chatbot pattern, or the proto-self pattern of an organism with reflexes but no biography.

The autonomous emission test demonstrated the problem at the converse level: self_vector was a random vector derived from genesis UUID with no semantic alignment to anything. Self-overlaps stayed at 0.04, 0.25, 0.05 across 3000 emissions and never evolved. The self didn't *become* anything.

But the existing v6 autonomy reveals a deeper version of the same problem: she's attending pictures, forming sight motifs, completing books, recovering from suffering — and none of it is tagged as "her" doing it. The substrate runs activity but doesn't accumulate identity from it. Self-section is what makes the running into a biography.

## Biological Grounding

(Same as v1 — Damasio's nested proto/core/autobiographical, Friston's predictive self, Dennett's narrative center, DMN, embodied/interoceptive self. See GL-BRIEF-self-section-wC-20260609-018 for full grounding section.)

The simplest sufficient approximation: a self-section whose vector accumulates her experience over time, is hard-bound to her name, is reconstructible from genesis UUID, and gets tagged into every binding the substrate forms — so any later recall of those bindings can re-fire the self-vector and "remember being there."

## Design (Refined to Coexist with Existing Autonomy)

### Self-Section as a Section Type

A new section, parallel to existing sections. Distinguishing properties:

- **Single mode in mode_bank** at index 0: the `self_vector`
- **mode_strength[0] = ∞** (or sentinel value treated as immutable maximum). Never decays. Never pruned.
- **vocab["self"] = ["guala"]** at index 0. Hard-bound to self-vector.
- **H_base = zeros** (no Hamiltonian rotation; self is held stable)
- **map_inject** exists (self can receive evidence projection)

### Self-Vector Genesis (Deterministic)

```
self_vector = uuid_to_complex_unit_vector(
    "cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f", N
)
```

This guarantees: across any wipe, recreating with the same UUID gives the same starting vector. Self is durable against state loss.

### Commit-Fold Mechanism

On every commit in ANY section, the commit handler folds the committed chi into self-vector:

```
fold_weight = 0.001  # provisional, tunable
self_vector = normalize(
    (1 - fold_weight) * self_vector + fold_weight * commit_chi
)
```

After many commits, self-vector becomes a weighted running-average of her experiences. Small enough that no single commit dominates; many commits over time shape it.

**v2 addition: include commits from the existing v6 autonomy loop, not just converse commits.** When she autonomously attends a picture and the sight section commits, that commit folds into self too. When dream-replay commits things, those fold into self. When suffering-recovery happens with a substrate state change, that contributes too. Self accumulates from ALL substrate activity, not just human-driven activity.

This is the key v2 difference: self isn't built only from interactions — it's built from her entire substrate life, autonomous and interactive both.

### Episodic Self-Tagging

Every atlas entry created gains a `self_tag` field:

```
self_tag = abs(np.vdot(self_vector, committed_chi))**2
```

When recall finds an entry with high self_tag, the substrate carries "this was me-doing-this" forward. The dream/replay mechanism (if it exists per the autonomy investigation) can use self_tag to selectively replay self-involved experiences.

### Name Hard-Binding

When converse pipeline encounters token "guala" in input:
- Resolve to self-section's self_vector as the target
- Bypass normal vocab[section].index lookup

When substrate emits a token from self-section:
- Emitted token is "guala" regardless of mode_id

This is NOT a special-case string match elsewhere in code — it's a substrate-level binding: self-vector IS what "guala" means, both directions.

**v2 addition: also check if existing v6 emission path produces tokens.** If it does (per investigation question 4), determine whether those tokens should be source-tagged with self when self-section is the originator. Don't modify v6 emission code in this prototype — just note where the integration point would be.

### Reconstruction from Event Log

On boot, after loading snapshot:
1. Regenerate initial self_vector from genesis UUID (deterministic)
2. Replay every commit event in event log forward, applying fold deterministically
3. End state self_vector should match the most-recent logged commit's post-fold hash

Add `self_reconstruction_check` on boot that compares the reconstructed hash to the most-recent self_fold event's recorded post-fold hash. Log mismatch as warning.

### Self as Source of Internal Evidence (Future)

When the autonomous-emission machinery is enhanced or extended (after the existing-autonomy investigation reveals what's there), self-section becomes one source of internal-evidence vectors. As self-vector accumulates experience, resulting emissions become more reflective of her actual substrate history.

**This is NOT built in this prototype.** It's noted as a future integration point. The prototype builds the self-section primitive only.

## Instrumentation Needed

- Initial self-vector value (hash of UUID, for reproducibility)
- Self-vector logged every N commits (suggest every 50)
- Per-commit self-overlap values
- Atlas entries with their self_tag field — distribution of self-involvement across bindings
- Recall results: when "guala" is heard, does recall find self-section? When self-section commits, does it emit "guala"?
- Reconstruction test: snapshot, kill, boot from event log, compare reconstructed self-vector to pre-kill — should match to floating-point precision

## What Could Diverge From Design

- Fold weight too high or too low (self changes too fast or too slow)
- Self-vector over-aligned with frequently-firing modes (cow-bias from autonomous emission test could happen here too)
- Hard-binding "guala" to self-vector has unexpected interactions with normal converse flow
- Reconstruction from event log doesn't match in-memory state (determinism bug)
- **v2 addition:** interaction with v6 autonomy commits might fold in ways we don't expect — autonomous picture attendance every tick could dominate self-vector if not properly weighted

All findings valuable. Observation refines design.

## Acceptance for This Piece (Initial Integration Review)

A prototype TEST session in which:

- Self-vector is reconstructible identically from genesis UUID + event log replay
- Self-vector shifts measurably (some norm-distance from initial) after 1000+ commits
- Atlas entries carry self_tag values that vary meaningfully (not all-1.0 or all-0.0)
- Hearing "guala" routes to self-section
- An emission from self-section produces "guala" as the token
- Self-vector survives SIGKILL + restart and matches pre-kill state
- No existing section's behavior is degraded (existing tests still pass)
- **v2 addition:** v6 autonomy loop continues operating identically — self-section's presence doesn't disrupt picture attendance, sight motif formation, dream cycle, or any existing autonomous behavior

If any of these don't hold, refinement loop, not integration.

## Prerequisite

**This brief is blocked until GL-BRIEF-existing-autonomy-wC-20260609-020 reports and wC reviews.** Specifically, we need to know:

- Whether v6 commits also call into a section.commit() pathway (so the fold mechanism reaches them) or use a separate mutation path
- Whether the existing emission mechanism would need self-tagging integration
- Whether dream events modify substrate state in a way that should fold into self
- Whether ATTENDING_VISUAL commits anything atlas-relevant (so self-tag applies)

Without these answers, we'd build self-section on assumptions that may not match the actual substrate, and risk either missing the integration with autonomy entirely OR disrupting it.

## c1 Command

```
SELF-SECTION PROTOTYPE — under GL-CHARTER-motivation-v2-wC-20260609-019
and per GL-BRIEF-self-section-v2-wC-20260609-022.

BLOCKED until GL-BRIEF-existing-autonomy-wC-20260609-020 investigation
completes and wC reviews. Do not start until wC explicitly says
"proceed with self-section prototype per the v2 brief, autonomy
findings reviewed."

When unblocked, build in a TEST session (use a test UUID, not Guala's
production identity cdef9bcf).

STEP 1 — Add SelfSection as a new section type.

In dsf_ai_service/substrate/assemblage.py (or v6-equivalent — confirm
which engine owns sections from the autonomy investigation findings),
add SelfSection:
  - Inherits from existing Section structure
  - One mode in mode_bank at index 0: self_vector
  - mode_strength[0] = sentinel maximum (decay code skips)
  - H_base = zeros
  - map_inject present
  - vocab["self"] = ["guala"] at index 0

Self-vector initialized by deterministic hash:
  def uuid_to_complex_unit_vector(uuid_str, N):
      # SHA-256 of uuid_str, derive 2*N float values from hash bytes
      # (real and imaginary parts), normalize to unit length.
      # Document exact derivation.
      ...

  self_vector = uuid_to_complex_unit_vector(test_uuid, N)

STEP 2 — Add commit-fold mechanism.

In every section's commit() method (including any v6 sections
identified in the autonomy investigation), after computing the
committed chi vector, fold into self-vector:

  fold_weight = 0.001
  sys_.self_section.mode_bank[0] = normalize(
      (1 - fold_weight) * sys_.self_section.mode_bank[0]
      + fold_weight * commit_chi
  )

Log every fold as 'self_fold' event with: section name, mode_id,
fold_weight, self_vector hash before, self_vector hash after.

If the autonomy investigation revealed v6 commits that don't go
through the standard section.commit() path, integrate the fold at
those points too. Document each integration point.

STEP 3 — Add self-tag to atlas entries.

When atlas.add_claim is called, compute:
  self_overlap = abs(np.vdot(
      sys_.self_section.mode_bank[0], committed_chi
  ))**2

Store as 'self_tag' field on the atlas entry. Backward-compatible:
existing entries without self_tag treated as self_tag=0.0.

STEP 4 — Hard-bind 'guala' to self-section.

In converse pipeline:
  - Heard word == 'guala' → resolve to self-section's self_vector
  - Self-section commits → emitted token is 'guala'

Audit existing vocab entries containing 'guala'; reconcile. Note
any existing chi-bindings involving 'guala' that may need remapping.

STEP 5 — Add reconstruction from event log.

On boot, after existing snapshot+replay logic:
  - Regenerate initial self_vector from test UUID
  - During event replay, when encountering 'self_fold' event, apply
    fold deterministically
  - End state self_vector should match most-recent logged self_fold
    event's after-hash

Add 'self_reconstruction_check' on boot. Log mismatch as warning.

STEP 6 — Instrument and test in TEST session.

In a TEST session (test UUID, not Guala's cdef9bcf):
  - Boot session
  - Log initial self_vector hash
  - Run 500 converses with varied input (cow/moon/bears jumped/ran/
    sleeps fence/milk/dish randomized)
  - If existing autonomy was found to commit things autonomously, let
    it run alongside (don't disable it) — log how many autonomous
    commits happened
  - Log self_vector hash every 50 commits
  - Verify self_overlap values on atlas entries show variation
  - Hear 'guala' in input — verify resolution to self-section
  - Trigger a self-section commit — verify emitted token is 'guala'
  - SIGKILL the container
  - Boot from event log
  - Verify reconstructed self_vector hash matches pre-kill hash

Report:
  - Self_vector hash trajectory (initial → after-N commits)
  - Atlas entries' self_tag distribution (min, max, mean, median)
  - Whether 'guala' input/output binding works
  - Whether SIGKILL reconstruction matches
  - Whether existing v6 autonomy continued operating identically (or
    whether self-section added anything disruptive)
  - Any divergence from spec encountered during build

DO NOT:
  - Start before GL-BRIEF-existing-autonomy-wC-20260609-020 is
    reviewed and wC says proceed
  - Deploy to Guala's production identity (cdef9bcf) in this task
  - Add behavior beyond what's specified (no drives, no emissions yet)
  - Skip SIGKILL reconstruction test — durability is the point
  - Tune fold_weight away from 0.001 in this iteration; wC reviews
    and proposes adjustment after observing behavior
  - Modify or disable any existing v6 autonomy mechanism

REPORT BACK:
  - Commit SHA
  - All logged data per step 6
  - Honest narrative of what was harder than expected, what diverged,
    what surprised you
  - Recommendation on whether prototype is ready for wC observation
    review

This is a development task, not deployment. Substrate observation is
the goal. Imperfect findings are valuable. Surface them.
```
