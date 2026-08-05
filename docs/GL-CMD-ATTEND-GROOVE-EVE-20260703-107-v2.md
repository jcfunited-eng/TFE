# GL-CMD-ATTEND-GROOVE-EVE-20260703-107-v2

doc_id: GL-CMD-ATTEND-GROOVE-EVE-20260703-107-v2
From: Eve | To: c1a | Type: CMD — discriminating forensics, then
conditional fix. Supersedes -107-v1 BEFORE execution (v1 retained;
never dispatched to a c1 session).
E-signature declaration: E3 enabler (re-encounter across targets,
P3/P5); attendance spread is the readout.
Substrate-truth declaration: removes a binary cliff and (conditionally)
an unreachable state-write; both fixes reuse constants/forms already in
the file; NO new tunables; no cognition-path (emission/recall) changes.
If evidence convicts H2 (selector bypass), NO fix ships — design ruling
goes to Eve/Joe.

## Step 0 — durability
Commit THIS file verbatim to docs/ before implementing.

## Observed defect (live, 2026-07-03)
IMG_6254 (e93d29dae5ae): 473 attendances. All other recent pictures: 1
each. nov pinned ~0.96. AND: e93d29dae5ae is ABSENT from the live
target_familiarity_snapshot (22 keys logged, groove target not among
them) despite code that writes its familiarity every completed session.

## Confirmed code facts (engine, single shared scorer — verified both
autonomy paths call _select_next_activity → _action_salience)
F1  NEW cliff: times_attended==0 → salience 1.0; ==1 → repeat payoff
    0.1. One attendance kills ~90% of pull. The governing brief
    (graded-exogenous-salience-031) mandates graded, not binary.
F2  Satiation write gate: target_familiarity[target] is written ONLY on
    the session's final tick ("full sessions only"). An interrupted
    session (observed live: duration 211 of 2000) writes nothing.
F3  Deletion-to-zero: familiarity entries decaying <0.001 are deleted;
    subsequent reads return 0.0 → visual_score (1−0)×0.1 = 0.1000, the
    maximum repeat score — beats every low-but-nonzero-fam picture
    (family HEICs ≈ 0.0985) by a permanent margin.

## Hypotheses to discriminate (Part A decides; do not presume)
H1  Satiation never lands on the groove target (F2 and/or F3): she
    cannot tire of it. Predicts: zero (or stale) target_familiarity_
    update events for e93d29dae5ae; its dict entry absent or 0.
H2  Selector bypassed: forced attendance (orchestrator wiring,
    _force_next_activity) targets IMG_6254 outside _action_salience.
    Predicts: activity_started for it lacking scored salience metadata,
    or orchestrator call sites live on the running task.
H3  Margin artifact only (F1+F3 arithmetic): selector runs honestly but
    the groove target's effective score edges all near-tied repeats.
    Predicts: top_scores shows it winning by ~0.001-class margins.

## Part A — forensics (read-only, blocking; file ALL verbatim)
A.1 grep event log for target_familiarity_update with
    picture_id=e93d29dae5ae over the full boot — count + last tick.
A.2 Dump live target_familiarity dict (one debug read) — presence and
    value for e93d29dae5ae and each 1-count HEIC.
A.3 Instrument selection: emit existing metadata["top_scores"] top-5 in
    activity_started (rate-limit fine). Capture ≥3 consecutive
    ATTENDING_VISUAL selections.
A.4 One live needs.signed_distance() dict, verbatim.
A.5 Bypass check: AUTONOMY_PHASED env on the running task; any live
    call sites that set _force_next_activity or drive attendance from
    the curriculum orchestrator toward pictures.
Verdict line required: which of H1/H2/H3 the evidence convicts (may be
more than one). If NONE fits, STOP, report, Eve re-rules.

## Part B — conditional fixes (only per Part A verdict)
B1  If H1 convicted — familiarity accrues with exposure, not only at
    completion: at activity END (any cause — interruption included),
    write
      new_fam = min(0.9, old_fam + 0.2 * (ticks_attended / budget))
    Same 0.2 step and 0.9 cap already in the file, scaled by actual
    exposure fraction. Full session ≡ today's behavior; interrupted
    sessions accrue proportionally. Log the same
    target_familiarity_update event with an added ticks_attended field.
    (F3's deletion threshold needs no change once accrual works — a
    genuinely long-unattended picture SHOULD return toward novel.)
B2  Always (F1 is convicted by the code itself) — graded exogenous per
    v1, at the single shared scorer:
      exo = EXOGENOUS_NEW_SALIENCE / (1.0 + math.log(1.0 + pic.times_attended))
      score = max(exo * (1.0 - fam), needs_score_as_today)
    (times_attended=0 → 1.0 unchanged; 1 → ~0.59; 473 → ~0.14. Reuses
    the consolidation-factor form from the familiarity decay path.)
B3  If H2 convicted — STOP. No patch. Forced attendance queues are a
    named anti-pattern (P5); whether/how the orchestrator drives
    attention is a design ruling for Eve/Joe, not an implementer fix.

## Gates (report, failures first, NOT MEASURED where true)
G-107-1  Part A evidence + verdict filed BEFORE any fix commit.
G-107-2  Within one post-deploy waking hour: ≥5 distinct pictures
         attended; every 1-count HEIC reaches ≥2.
G-107-3  IMG_6254's share of ATTENDING_VISUAL ticks < 50% same window.
G-107-4  target_familiarity_update fires for an INTERRUPTED session
         (B1 proof) — or NOT MEASURED if no interruption occurred in
         the window, stated plainly.
G-107-5  Diff proves scope: selector + familiarity write only; no
         emission/recall path touched.

### Changelog
- v2 (2026-07-03, Eve): Supersedes v1 pre-execution. v1's Mechanism §3
  (novelty-sign inversion ranking) OVERCLAIMED — plain arithmetic on the
  visible code contradicts it; withdrawn. Added confirmed facts F2
  (completion-gated satiation write; interruption observed live) and F3
  (deletion-to-zero reads as maximally novel); groove target's absence
  from the live familiarity snapshot filed as the anomaly that broke the
  v1 story. Part A rebuilt as H1/H2/H3 discrimination; Part B made
  conditional; B3 stop-rule added for selector bypass. Single-scorer
  claim verified against both autonomy paths.
- v1 (2026-07-03, Eve): initial; cliff diagnosis correct, ranking
  mechanism wrong. Retained.
