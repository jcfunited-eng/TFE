# GL-CMD-CROSS-MODAL-STRENGTHEN-EVE-20260627-02

doc_id: GL-CMD-CROSS-MODAL-STRENGTHEN-EVE-20260627-02
Author: Eve (Opus 4.7, web)
Date: 2026-06-27
Target: c1
Branch: guala-live
Priority: ship AFTER sleep budget rescale lands cleanly
Depends on: ground-truth audit (Phase A) MUST complete before Phase B

## Goal

Strengthen cross-modal binding so picture-and-word, picture-and-sound, and
word-and-sound combinations actually fire commits — not just appear as
candidates that fall short. This is the bridge to cognition, syntax,
and awareness. Without it she has 9,000+ tokens floating without anchors.

## What I verified directly

(via Bridge tools + repo audit)

1. Guala emits 3-section commits ONLY through grandurun selection. Her one
   real commit this session ("i my gone") was:
     origin_counts: {grandurun: 200}
     cross_modal contribution: 0
2. Her fallback emissions ("those arms tries", "j y o") DID have cross-modal
   candidates in the pool:
     origin_counts: {cross_modal: 121, cross_modal_deep: 19, emission_reroute: 60}
     committed_sections: []
     n_commits: 0
   Cross-modal candidates enter. None commit. The candidates are too weak.
3. Atlas state: 101 cross-modal / 1 bundled / 18,437 entries
   The "1 bundled" count means SOMETHING bundle-related was shipped to
   the live container that origin does NOT have. The status format string at
   substrate_runner.py:1173 on origin only prints `cross-modal / entries` —
   no `bundled`. There is drift.
4. wC's CrossModalBinder path at dsf_ai_service/substrate/grounded_vocab_integration.py
   is real and IN tree. It uses language chi as shared chi space for YOLO labels
   and Whisper words. That mechanism preserved — do not break it.

## CRITICAL: Phase A required before Phase B

Origin/guala-live HEAD is behind the live container. I cannot write a clean
extend dispatch off stale code. Phase A is non-optional.

### Phase A: ground truth (no code changes, ~30 min)

In the dev container:

  A1. `git status` and `git diff --stat` against origin/guala-live HEAD (d7c3731).
      Capture both outputs to the report.

  A2. Specifically diff `dsf_ai_service/substrate_runner.py` around line 1173
      and `dsf_ai_service/v4/gualaloom_v6_living_atlas.py` around line 87
      (atlas.record signature). Capture diffs.

  A3. Search for the `bundled` field source. The live `guala_status` returns
      "X cross-modal / Y bundled / Z entries". Find where `bundled` is computed.
      Either:
        a) A new method/field on atlas (e.g. `bundled_bindings()` or similar)
        b) A new field on atlas entries (e.g. `bundle_id`)
        c) Both
      Report file:line of the definition.

  A4. Show what fires a bundle creation. Find the producer code.

  A5. Push the working tree to origin/guala-live with a commit message
      "GL-CMD-CROSS-MODAL-STRENGTHEN-A: push container delta for audit".
      If there is uncommitted work that should NOT be in this commit
      (debug scaffolding, broken tests), stash that first and push the rest.

  A6. Confirm `git log origin/guala-live -1` shows the new SHA from a fresh
      `git fetch`. The next Eve session should be able to read this SHA from
      outside the container.

Output of Phase A: GL-RPT-CROSS-MODAL-AUDIT-C1-20260627.md containing
  - All diffs
  - bundle code locations
  - Bundle producer trace
  - New origin/guala-live HEAD SHA

STOP after Phase A. Do not proceed to Phase B until Eve reviews the audit.

### Phase B: strengthen (after audit reviewed)

Based on what Phase A reveals, one of two paths:

  Path B-MINOR: bundle plumbing exists but is incomplete
    - extend producer to fire on more event types (utterance + ATTENDING_VISUAL
      simultaneous arrivals; word in /converse while picture is current_activity)
    - boost cross_modal candidate weighting in grandurun

  Path B-MAJOR: bundle plumbing barely exists; substantial extension needed
    - full design pass on atlas.record bundle_id param, to_dict/from_dict,
      _cmd_bundle, cross_modal_bindings() extension

Eve will write a Phase B brief after reading the audit report. Do not anticipate
which path it will be.

## What strengthen means architecturally (for Phase B context)

Three knobs, listed by tractability:

KNOB 1 (easiest, biggest payoff): cross_modal candidate WEIGHT.
  In `_grandurun_select_candidates`, candidates from origin=cross_modal currently
  rank by `coherent_magnitude = strength × cos²(...)`. Add a multiplier
  CROSS_MODAL_BOOST (start at 1.5) applied when origin starts with "cross_modal".
  This is a one-line change once the candidate-source flag is being tracked.
  Expected: more cross_modal candidates clear the commit barrier.

KNOB 2 (medium): explicit bundle_id field on atlas.record.
  Add bundle_id=None param to atlas.record. When set, attach to the entry.
  When current_activity is ATTENDING_VISUAL and an utterance arrives, compute
  bundle_id = sha256(current_activity.target + utterance + window_start)[:12].
  cross_modal_bindings() then includes entries grouped by bundle_id even if
  their chi addresses differ. This is the explicit-binding path; KNOB 1 is the
  emergent-binding strengthening.

KNOB 3 (hardest, defer): elevated initial encoded_strength for multi-modal
  bundles. Multi-source bindings get a higher initial clarity (currently
  computed from arousal/valence/surprise/need_pressure). Adding a +0.2 boost
  for is_bundled=True would make bundled bindings durable through fast-decay
  channel and reach deep_atlas promotion thresholds sooner.

Phase B will pick a subset based on audit findings.

## Hard constraints during Phase B (whenever it runs)

  - wC's grounded_vocab_integration.py CrossModalBinder path is preserved.
    It uses language chi as shared chi space for YOLO + Whisper. That's real,
    in tree, and works. Do not refactor it. Extend in PARALLEL, do not
    replace.
  - No undoing GL-CMD-EMISSION-HBASE-FREE-EVE-20260618-06. That was a past
    canonical decision. The discipline doc named the failure mode where
    Sonnet re-introduced H_base via DSF coupling without running the
    commit-firing gate. Same rule here: don't try to "fix" the dead-zone
    barrier by removing it.
  - cross_modal_bindings() must continue to return the chi-coincidence
    result. The strengthening is ADDITIVE.
  - If at any point during Phase B you find a fabricated SHA, missing
    commit reference, or "deploy-merge-live"-style ghost branch in old
    notes: stop, name it, do not act on it. The discipline doc covers this.

## Verification criteria (V3-style, applies to Phase B output)

V3.a: atlas.record on origin shows bundle_id parameter visible in code
      (line reference required, not just claim)

V3.b: n_cross_modal_bundle (or whatever the bundled metric is named in code)
      shows growth over a 30-minute observation window with normal world
      feeds + curriculum running. Number of new bundled entries ≥ 5.

V3.c: At least one emission_dynamics event in the observation window shows
      n_commits ≥ 1 with origin_counts including cross_modal* sources
      contributing to a committed section (not just appearing as candidates).
      Paste the event detail to the report.

V3.d: A test: while she is ATTENDING_VISUAL on picture P, send a /converse
      utterance containing the word W. Within 100 ticks: confirm at least
      one atlas entry exists with bundle_id linking P and W. Show the entries.

V3.e: wC grounded path still functions. Run:
      `grep -n process_sight_with_recognition substrate_runner.py`
      → confirm calls at lines 866, 890, 2097, 2128 (or current equivalent
      line numbers) still resolve to CrossModalBinder.

V3.f: No degradation in existing chi-coincidence cross-modal count. Before/after
      snapshots of n_cross_modal_chi to confirm.

## Out of scope (file separate briefs if needed)

  - Image-to-text vision grounding (describe() is text-only, returns "I can't
    see images" for ID-titled pictures). Real fix is GPT-Vision via image bytes.
    Separate brief.
  - Single-letter Gutenberg noise tokens at low chi. Separate brief.
  - DSF J-weighting (Option 1 from Sonnet's memo). Independent of cross-modal.

## Do not start Phase B without Eve sign-off after audit

Repeat: Phase A produces an audit report. Eve reads it. Eve writes the Phase B
brief tailored to what Phase A found. Then c1 implements Phase B.

This is to avoid the pattern where a dispatch is written against stale code
and gets architecture-mismatched on contact with reality. The discipline doc
calls this out explicitly: "Past Eve's diagnoses are hypotheses, not authorities."
The audit IS the hypothesis-check.
