# GL-CMD-ATTEND-GROOVE-EVE-20260703-107-v1

doc_id: GL-CMD-ATTEND-GROOVE-EVE-20260703-107-v1
From: Eve | To: c1a | Type: CMD — diagnose-then-fix, one deploy vehicle
E-signature declaration: E3 enabler (re-encounter across targets, P3/P5);
  no direct signature claim — post-deploy attendance spread is the readout.
Substrate-truth declaration: REMOVES a binary cliff (times_attended 0→1)
  that violates GL-BRIEF-graded-exogenous-salience-wC-20260610-031's own
  stated principle ("decays with familiarity, not binary"). Fix reuses the
  consolidation-factor form already present in the familiarity decay path.
  NO new tunable constants. No cognition-path (emission/recall) changes.

## Step 0 — durability
Commit THIS file verbatim to docs/ before implementing.

## Observed defect (live, 2026-07-03, tick ~14.46M)
IMG_6254 (e93d29dae5ae): 473 attendances and climbing. Every other
recently-added picture — Guala Family.HEIC, IMG_1962/2121/2161/2216,
snapshot, Bell.png — exactly 1 attendance each. ATTENDING_VISUAL this
boot: 27 blocks, ~54,000 ticks, effectively one target. nov pinned 0.961.
She is grooved on one image while 27 sit unseen.

## Mechanism (from source, engine `_action_salience` ~L4173)
1. `times_attended == 0` → return EXOGENOUS_NEW_SALIENCE = 1.0.
2. `times_attended >= 1` → base_payoff = ATTENDING_VISUAL_REPEAT = 0.1.
   One attendance drops pull by ~90%. Binary cliff; the governing brief
   mandates graded decay.
3. With novelty ABOVE target (0.961 vs 0.7), sd["novelty"] suppresses all
   novelty-payoff scores; the residual ranking then favors the most
   familiar basin. Combined with (2), once-attended pictures can never
   outcompete the 473-basin.

## Part A — evidence BEFORE fix (read-only, blocking)
A.1 Instrument `activity_started` (or a new `selection_scored` event,
    rate-limited ≥1/2000 ticks) to include the existing
    `metadata["top_scores"]` top-5 (already computed in
    `_select_next_activity`; currently dropped from the event).
A.2 Capture one live `needs.signed_distance()` dict verbatim at a
    selection moment.
A.3 File both verbatim in the report. If the evidence CONTRADICTS the
    mechanism above (e.g. family HEICs absent from candidates entirely),
    STOP after Part A, report, no fix — Eve re-rules.

## Part B — the fix (gated on A confirming)
Replace the binary branch for ATTENDING_VISUAL pictures with graded
exogenous salience using the consolidation form already in this file
(familiarity decay path, `1.0 / (1.0 + log(1.0 + n_attends))`):

    exo = EXOGENOUS_NEW_SALIENCE / (1.0 + math.log(1.0 + pic.times_attended))
    score = max(exo * (1.0 - fam), needs_score_as_today)

Properties: times_attended=0 → 1.0 (unchanged); =1 → ~0.59; =5 → ~0.36;
=473 → ~0.14. Smooth, monotone, no new constants, the 473-basin keeps a
floor (it is genuinely hers) but stops beating every near-new picture.
Nothing else in _action_salience, payoff tables, or Needs is touched.

## Gates (report, failures first, NOT MEASURED where true)
G-107-1  Part A evidence filed verbatim BEFORE any fix commit.
G-107-2  Within one post-deploy waking hour: ≥5 distinct pictures
         attended; every 1-count HEIC reaches ≥2 attendances.
G-107-3  IMG_6254's share of ATTENDING_VISUAL ticks < 50% over the same
         window (it may remain her favorite; it must stop being her only).
G-107-4  No change in emission/recall paths — diff proves scope.

### Changelog
- v1 (2026-07-03, Eve): initial. From live groove evidence + source read.
