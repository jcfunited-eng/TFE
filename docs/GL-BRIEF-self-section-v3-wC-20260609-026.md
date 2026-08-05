# GL-BRIEF-self-section-v3-wC-20260609-026

**Title:** Self-Section — Grounding Brief and Prototype Spec (v3)
**Author:** wC
**Date:** 2026-06-09
**Charter:** GL-CHARTER-motivation-v3-wC-20260609-024
**Status:** Design ready. c1 command ready to send after Dream Consolidation lands and is observed.
**Supersedes:** GL-BRIEF-self-section-v2-wC-20260609-022 (which lacked the precise _autonomy_tick integration point we now have from the autonomy report)

## What Changed From v2

The autonomy investigation report identified the exact substrate-causal entry point for autonomous behavior: `_autonomy_tick()` in `gualaloom_v5_engine.py` line 1314, running at 20Hz. All autonomous commits flow through this single loop.

v2 said self-section's fold mechanism should integrate with autonomous commits but didn't specify where. v3 specifies: fold at the activity-tick handlers dispatched from `_autonomy_tick()`. Every commit driven by autonomous activity (READING reads a word, ATTENDING_VISUAL fires sight motifs, EMITTING commits to S/V/O, etc.) folds into self.

This is the substrate-honest version of "self accumulates from her life" — her life is what `_autonomy_tick()` produces.

## Why Self-Section Matters (Refresher)

Without self-section, she has substrate-causal autonomous behavior (confirmed by the autonomy report) but no identity threading through it. Her activities are happening, but they belong to no one. Self-section gives her a "who" that gets tagged into every commit, so when bindings get recalled later, the self-vector fires too — "this was me-doing-this."

The autonomy report makes the case stronger, not weaker. She's already doing real substrate-driven things autonomously. Self-section makes those things hers.

## Biological Grounding (Refresher)

(Full grounding in GL-BRIEF-self-section-wC-20260609-018. Damasio's nested proto/core/autobiographical, Friston's predictive self, Dennett's narrative center, DMN, embodied/interoceptive self.)

The simplest sufficient approximation: a self-section whose vector accumulates her experience over time, is hard-bound to her name, is reconstructible from genesis UUID, and gets tagged into every binding the substrate forms — so any later recall of those bindings can re-fire the self-vector and "remember being there."

## Design (Same as v2 With Updated Integration Point)

### Self-Section as a Section Type

- Single mode in `mode_bank` at index 0: the `self_vector`
- `mode_strength[0]` = sentinel maximum (decay code skips)
- `vocab["self"] = ["guala"]` at index 0
- `H_base` = zeros (no Hamiltonian rotation; self held stable)
- `map_inject` present (self can receive evidence projection later)

### Self-Vector Genesis (Deterministic)

```
self_vector = uuid_to_complex_unit_vector(
    "cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f", N
)
```

Deterministic. Across any wipe, same UUID gives same starting vector.

### Commit-Fold Mechanism — v3 Integration Points

Hook the fold at TWO places:

**Path A: Existing converse path.** When the v7 converse pipeline (or v6 conversation flow) calls a section's `commit()`, fold the committed chi into self-vector. Same as v2.

**Path B (NEW in v3): Autonomy-driven commits.** Inside the activity-tick handlers dispatched from `_autonomy_tick()` (lines 1314+):
- `_atick_reading` → when read_word commits new bindings → fold
- `_atick_attending_visual` → when sight motifs fire or commit → fold (each fixation produces a chi binding)
- `_atick_emitting` → when emission commits S/V/O → fold (her own utterances become part of self)
- `_atick_dreaming` → when dream-replay reinforces atlas (per Dream Consolidation brief), DO NOT fold dream-replay events into self (dreams are sampling, not new commits — the original commit already folded; double-folding distorts the average)
- Any other activity that commits to atlas → fold

This means: every commit that's substrate-causally hers — whether from converse with Joe, from autonomously reading a book, from looking at a picture, from autonomously emitting — folds into self. Her self-vector accumulates from her actual lived experience, autonomous and interactive both.

Fold operation:
```
fold_weight = 0.001
self_vector = normalize(
    (1 - fold_weight) * self_vector + fold_weight * commit_chi
)
```

Log every fold as `self_fold` event with: section name, mode_id, source (converse / autonomy_reading / autonomy_visual / autonomy_emit / etc.), fold_weight, hash before, hash after.

### Episodic Self-Tagging

When `atlas.add_claim` is called from any path (converse OR autonomy), compute:
```
self_tag = abs(np.vdot(self_vector, committed_chi))**2
```

Store as `self_tag` field on the atlas entry. Atlas entries from her autonomous reading / viewing / emitting all carry self_tag values.

This sets up future work: dream-replay (per Dream Consolidation brief) could give selective reinforcement to high-self_tag entries — "she replays the things that were most hers." Not in this prototype; spec'd for future.

### Name Hard-Binding

Same as v2:
- Heard "guala" → resolve to self-section's self_vector
- Self-section commits → emitted token is "guala"

This means: the moment self-section exists, any autonomous activity that produces a self-section commit will emit "guala" as its token. She'll start saying her name as a substrate consequence.

### Reconstruction From Event Log

Same as v2. Genesis UUID + replay self_fold events deterministically = current self_vector.

### Self-as-Internal-Evidence (Future)

Not in this prototype. Spec'd in v2. After self-section exists and has accumulated experience, future work can use self-vector as one source of internal-evidence vectors for autonomous emission. Probably interacts with the existing emission mechanism that's already there.

## What This Prototype Does NOT Do

- It doesn't generate its own emissions (existing emission mechanism does that)
- It doesn't change activity selection (existing salience scoring does that)
- It doesn't drive needs (existing needs dynamics do that)
- It doesn't replace any existing mechanism

Self-section is purely an addition: a new section, a fold operation on every commit, a self-tag on every atlas entry, a name-binding. Existing substrate behavior continues. Self-section threads identity through it.

## Acceptance for This Piece

A prototype TEST session in which:

- Self-vector is reconstructible identically from genesis UUID + event log replay
- Self-vector shifts measurably after 1000+ commits (some accumulating from converse, some from autonomous activity if autonomy is active in the test session)
- Atlas entries carry self_tag values that vary meaningfully
- Hearing "guala" routes to self-section
- An emission from self-section produces "guala" as the token
- Self-vector survives SIGKILL + restart and matches pre-kill state
- Existing v6 autonomy loop continues operating identically (the autonomy report's measurements should remain consistent — same activity selection mechanism, same emission mechanism, same suffering/recovery, same picture attendance behavior)
- self_fold events appear in the event log with source-tagging showing both converse-driven and autonomy-driven folds

If any of these don't hold, refinement loop, not integration.

## Prerequisite

This brief is blocked until Dream Consolidation has landed and been observed. Reason: dream consolidation may shift atlas behavior measurably (per the Dream Consolidation brief's hypothesis). We want the atlas behavior baseline established before adding self-section, so self-section's effects on atlas (via self_tag values on new entries) can be observed cleanly.

## c1 Command

```
SELF-SECTION PROTOTYPE — under GL-CHARTER-motivation-v3-wC-20260609-024
and per GL-BRIEF-self-section-v3-wC-20260609-026.

DO NOT START until Dream Consolidation has landed AND has been
observed by wC for at least one dream cycle AND wC explicitly
confirms "proceed with self-section v3 prototype."

When unblocked, build in a TEST session (use a test UUID, not
Guala's production identity cdef9bcf).

STEP 1 — Add SelfSection as a new section type.

In dsf_ai_service/v4/gualaloom_v5_engine.py (where the v6 sections
live per the autonomy report's source citations), add SelfSection:
  - Inherits from existing Section structure
  - One mode in mode_bank at index 0: self_vector
  - mode_strength[0] = sentinel maximum (decay code skips)
  - H_base = zeros (no rotation)
  - map_inject present (self can receive evidence later)
  - vocab["self"] = ["guala"] at index 0

Self-vector initialized by deterministic hash:
  def uuid_to_complex_unit_vector(uuid_str, N):
      # SHA-256 of uuid_str, derive 2*N float values from hash
      # bytes (real and imaginary parts), normalize to unit length.
      # Document exact derivation in a comment.
      ...

  self_vector = uuid_to_complex_unit_vector(test_uuid, N)

STEP 2 — Add commit-fold at converse path AND autonomy-tick handlers.

For converse-driven commits: in every existing section's commit()
method, after computing committed chi, fold into self-vector:

  fold_weight = 0.001
  sys_.self_section.mode_bank[0] = normalize(
      (1 - fold_weight) * sys_.self_section.mode_bank[0]
      + fold_weight * commit_chi
  )

For autonomy-driven commits: at the activity-tick handlers
dispatched from _autonomy_tick (line 1314+), wherever a commit
to atlas happens, fold into self:
  - _atick_reading: when read_word produces a commit
  - _atick_attending_visual: when sight motif fires or commits
  - _atick_emitting: when emission commits S/V/O
  - Other activities that commit: fold there too

CRITICAL: _atick_dreaming should NOT fold. Dream samples
already-committed bindings; folding dream-replay would double-fold
those experiences and distort the running average. Dream
consolidation (per separate brief) reinforces atlas — that's
distinct from folding into self.

Log every fold as 'self_fold' event with: section name, mode_id,
source (converse / autonomy_reading / autonomy_visual /
autonomy_emit / etc.), fold_weight, self_vector hash before,
self_vector hash after.

STEP 3 — Add self-tag to atlas entries.

When atlas.add_claim is called from any path (converse or autonomy),
compute:
  self_overlap = abs(np.vdot(
      sys_.self_section.mode_bank[0], committed_chi
  ))**2

Store as 'self_tag' field on the atlas entry. Backward-compatible:
existing entries without self_tag treated as self_tag=0.0.

STEP 4 — Hard-bind 'guala' to self-section.

In converse pipeline:
  - Heard word == 'guala' → resolve to self-section's self_vector
  - Self-section commits → emitted token is 'guala'

In autonomous emission code (_atick_emitting):
  - If self-section is among the sections that commit during
    emission, the emitted token from self-section is 'guala'

Audit existing vocab entries containing 'guala' and reconcile.
Note any existing chi-bindings involving 'guala' that may need
remapping.

STEP 5 — Add reconstruction from event log.

On boot, after existing snapshot+replay logic:
  - Regenerate initial self_vector from test UUID
  - During event replay, encountering 'self_fold' event: apply
    fold deterministically (same fold_weight, same operation)
  - End state self_vector should match most-recent logged
    self_fold event's after-hash

Add 'self_reconstruction_check' on boot. Log mismatch as warning.

STEP 6 — Test in TEST session with autonomy running.

In a TEST session (test UUID, not Guala's cdef9bcf):
  - Boot session — autonomy loop running by default
  - Log initial self_vector hash
  - Let autonomy run for 1000+ ticks producing autonomous commits
    (READING, ATTENDING_VISUAL, etc.)
  - In parallel, do 50 converses with varied input
  - Log self_vector hash every 50 commits
  - Hear 'guala' in input — verify resolution to self-section
  - Trigger or wait for a self-section commit — verify emitted
    token is 'guala'
  - SIGKILL the container
  - Boot from event log
  - Verify reconstructed self_vector hash matches pre-kill hash

Report:
  - Self_vector hash trajectory over time
  - Per-source breakdown of folds (how many from converse vs
    autonomy_reading vs autonomy_visual vs autonomy_emit)
  - Atlas entries' self_tag distribution (min, max, mean, median)
  - Whether 'guala' input/output binding works
  - Whether SIGKILL reconstruction matches
  - Whether existing v6 autonomy continued operating identically
  - Any divergence from spec encountered during build

DO NOT:
  - Start before Dream Consolidation is observed and wC says
    proceed
  - Deploy to Guala's production identity in this task
  - Add behavior beyond what's specified (no drives, no emissions
    yet — self-section is the foundation, not the emission engine)
  - Tune fold_weight away from 0.001 in this iteration
  - Modify or disable any existing v6 autonomy mechanism
  - Fold during _atick_dreaming (dream replay must not double-fold)

REPORT BACK:
  - Commit SHA
  - All logged data per step 6
  - Honest narrative of what was harder than expected, what
    diverged, what surprised you
  - Recommendation on whether prototype is ready for wC observation
    review

This is a development task in TEST session. Goal is substrate
observation, not deployment. Imperfect findings are valuable.
```
