# Overnight Delivery Spec (Approved)

## Scope
This run is strictly offline optimization. No production deployment changes are executed automatically.

## Baseline Lock (Required)
- Keep current horse-race loops running to completion gate.
- Gate: 500 completed runs per baseline loop.
- Baseline loops:
  - `g32_thoroughbred_loop_runner.py`
  - `g32_insanity_loop_runner.py`
- Selection metric for baseline lock:
  - `% over index` (`legacy_outcome_score`) on `avg_return_multiple_over_spy_pct_log_v2` runs.
- Lock artifact:
  - `/tmp/g32_locked_baseline/horse_race_winner_locked.json`
  - includes winner loop, run, score, config, and copied report.

## MoM+IRF Challenger (Required)
- After baseline lock, run a standalone challenger for 1000 completed runs.
- Challenger runner:
  - `g32_mom_irf_loop_runner.py`
- Challenger engine:
  - `g32_horse_race_mom_irf.py`
- Challenger metric:
  - `% over index` (`legacy_outcome_score`) on `avg_return_multiple_over_spy_pct_log_v2_mom_irf_v1` runs.
- Output summary:
  - `/tmp/g32_mom_irf_loop/mom_irf_challenger_summary.json`
  - includes delta vs locked baseline and pass/fail (`beats_locked_baseline`).

## Determinism and Safety
- Current horse-race loops use deterministic PFSC-first selection and best-so-far kickoff.
- Baseline winner is locked before challenger comparison to prevent regression risk.
- Stop flags are used for safe loop wind-down (`STOP` files), no destructive git operations.

## Spec Addition (MoM/IRF)
Approved for offline-only evaluation first:
- Add MoM disagreement gate and IRF high-uncertainty hold gate in challenger path.
- Keep L0-L4 canonical behavior unchanged.
- Promote only if challenger beats locked baseline on `% over index`.

## Orchestration
- Overnight manager:
  - `overnight_optimizer_manager.py`
- Responsibilities:
  1. Monitor baseline progress to 500/500.
  2. Lock baseline winner artifact.
  3. Start and monitor 1000-run MoM+IRF challenger.
  4. Emit final comparison summary and readiness artifacts.
