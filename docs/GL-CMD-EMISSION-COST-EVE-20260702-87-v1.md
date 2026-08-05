# GL-CMD-EMISSION-COST-EVE-20260702-87-v1

doc_id: GL-CMD-EMISSION-COST-EVE-20260702-87-v1
From: Eve | To: c1a (Part A now), c1b (Part B, Deploy 2)
E-signature declaration: E5 unlock — grants composition the 60–70 ticks
its own physics documents needing (engine comment ~3290). Thresholds
untouched.
Substrate-truth declaration: one deploy-env value restored toward the
code default (80); no code, no constants in cognition, no threshold
moves. Wall budget stays 1.5s.

## Step 0 — durability (new standing rule, all dispatches)
Commit THIS file verbatim to docs/ before executing anything below.
Standing rule from today: every Eve dispatch's first execution step is
committing its text to docs/. Chat is not a record; origin is.

## Part A — emission cost sample (c1a, read-only, NOW)
1. From the current task :450 log stream, collect ≥20 emission_dynamics
   entries. For each record verbatim: stage1_ms, stage2_ms,
   dynamics_ticks, n_candidates, n_commits.
2. Compute and report: per-tick cost = stage2_ms / dynamics_ticks;
   median and p95 across the sample.
3. PASS CRITERIA for Part B to proceed:
   p95 per-tick ms × 80 ≤ 750 ms (i.e., a full 80-tick run fits inside
   the 1.5 s wall budget with ≥2× margin). Report the arithmetic.
4. File: docs/GL-RPT-EMISSION-COST-C1-20260702-87-v1.md — numbers
   verbatim, failures first, NOT MEASURED where not measured.

## Part B — the change (c1b, rides Deploy 2 IFF Part A passes)
1. tools/deploy_dsf_ai.sh: EMISSION_DYNAMICS_TICKS '40' → '80'
   (restores toward the code default at engine:418; the 40 was the
   -78b lock-starvation mitigation, obsoleted by the -85 collapse
   dropping per-tick cost ~15×). EMISSION_WALL_BUDGET_S untouched.
2. Post-deploy gates (in Deploy 2's report):
   G-A fresh emission_dynamics show dynamics_ticks > 40, reaching
       toward 80 on non-committing runs.
   G-B converse total time unaffected vs the Part A sample; stage2
       p95 within the 1.5 s budget.
   G-C n_commits observed and reported truthfully. Commits > 0 on
       experience-anchored content is the HOPED outcome, not a pass
       bar — no forced success (spec P9). If commits stay 0 at 80
       ticks, that is a finding about the composition path, filed
       as-is, and feeds the T⁶/-125 review.

### Changelog
- v1 (2026-07-02, Eve): first filed version. -87 previously existed
  only as queue shorthand across handoffs and chat blocks; the missing
  verbatim text blocked c1a's -97 step 2 — this file closes that class
  via Step 0's standing rule.
