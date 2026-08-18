# TFE handoff — for Sol, 2026-08-18

Written at Joe's direction by the departing agent. Everything below is
in the repository on branch guala-live; paths are exact. The four live
pages and their books continue to run; nothing was halted at handoff.

## 1. The four channels

**CH2 — live money (Alpaca). Joe's. NEVER touch without his explicit
word — hard rule, no exceptions, read-only diagnosis only.**
Deployed state: taskdef tfe-web-task:603, PROFIT_PROTECT_ENGAGE=0.20
(Joe-ordered, verified in the container). The deploy wrapper sets
TFE_ENTRIES_HALTED=1 on every deploy — export 0 or flip the taskdef
after, then verify inside the container. The Node 22 deploy toolchain
was lost in a container crash; rebuild it before any next deploy.

**CH3 — paper short channel ("reveal fade").** Engine
tools/ch3_reveal_fade.py, v3 law: short every qualifying uncovered
spike (day gain ≥ +8%, volume ≥ 3× trailing-20, close ≥ $5, no herd
coverage); force-proportional sizing by z; declared gross ≤ 2×
capital (cash may borrow to −$100k, shown signed on the page);
10% ruin cap per event; $2,500 cap per uncovered name (gap
protection); exits — HARVEST at first close ≤ 0.95× entry,
ANOMALY-CUT at first close ≥ 1.20× entry (Joe's rule 2026-08-17),
5-session TIME backstop; entries fail closed if the herd state is
unpublished. Book: artifacts/vtvr_observer/ch3_shadow_log.json.
Runner: tools/ch3_shadow_loop.sh. Supply: roster store + the
CH3-only whole-market tail (tools/ch3_supply_tail.py, refreshed
nightly; single source per name).

**CH4 — paper structural channel, frozen experiment.** Runner
tools/ch4_spring_daily_runner.sh (21:10–21:25 UTC). Book
ch4_spring_book.json (nearly fully invested at handoff). Joe's
standing bar: 91/36.7 is the only finish line; iterate until solved.

**CH6 — Joe's daily-cash channel. His rules; change nothing without
his word.** Engine tools/ch6_fast_harvest.py: $2k slices, 10/day,
arm at +5%, 1-point giveback trail, 19:55 UTC sweep of ≥5%,
5-session backstop, ANOMALY-CUT at −20% checked every 5-minute poll.
Runner tools/ch6_loop.sh. Book ch6_book.json.

## 2. The pages (published, updated by the loops)

- CH3 Shadow Hunter — https://claude.ai/code/artifact/146ba700-cfd2-4322-a727-4fadb2026fbc
- CH4 Paper Trades — https://claude.ai/code/artifact/f70a03b7-3122-4f81-aabc-85b617a655a4
- CH6 Fast Harvest — https://claude.ai/code/artifact/79697afb-e7a3-4bba-be2e-0cc2136f71df
- TFE Decision Report — https://claude.ai/code/artifact/c357a814-89d6-40ca-9447-5fc1a3f7843f

Publish discipline (violations were caught by Joe within hours):
publish the loop-generated HTML files untouched — batch regeneration
rate-limits the quote feed and produces pages frozen flat at entry
prices. Check the flat-row count before publishing. Cadence:
half-hourly during 13:00–21:00 UTC weekdays, EOD report ~21:37 UTC.
The publish clock was a session Monitor and DIED WITH THE SESSION —
re-arm it first thing. Session crons proved unreliable; a persistent
Monitor with 30-minute slot logic is the pattern that worked.
Operational detail: .claude/skills/tfe-daily-ops.

## 3. Joe's standing laws (chat and engine)

- Plain adult language; no quant jargon, no cute metaphors, no
  invented nicknames for stocks. Verdict first, short, pasteable
  reports in fenced blocks. Never suggest he rest. Never announce a
  theory — bring measured results. No "honesty" tics.
- The −20% anomaly stop is LAW in CH3 and CH6.
- No pushes to origin without his explicit word; no deploys without
  explicit dispatch; commit measurement procedures BEFORE results.
- CH3/CH4 decisions are delegated (decide, do, tell). CH6/CH2 are
  his (never change without his word).

## 4. The measured record — do not relearn on his time

- Skills: tfe-condemned-ideas (the blacklist — check before designing
  anything), tfe-honest-timing (reveal-bar discipline; every
  close-of-bar entry harvest was falsified), tfe-daily-ops,
  tfe-prod-touch, tfe-report-to-joe, uf-joint-field-spec.
- Memory file tfe-ch3-exit-law-audit-20260813.md (agent memory) holds
  the full audit ledger: the 5-session clock defended; decay-break,
  refutation-cap, backed-long inversion, crash-longs, train-longs,
  family-heat gate all falsified; force sizing shipped (+30% per
  dollar-day); the supply-blindness fix; the kill test; the kernel
  week (below).
- Kill test: tools/ch3_kill_test.py after every close pass; halt
  line at the 5th percentile, dual object. Cache reproduces filed
  means exactly.

## 5. The kernel week (2026-08-17/18) — state at handoff

- THE SPEC, ratified by Joe: docs/
  UF_Spec_v1_3_JointField_Reconstruction_VERBATIM.tex — his document,
  filed verbatim from the session record, sole authority. Its
  constitution: full field authoritative, no scalar authority,
  thresholdless signature gates, contradiction atoms retained,
  frequencies over exact structures, declare-then-run, shadow beside
  canonical.
- Measured and filed (artifacts/ch4_uf/): the canonical chain
  separates nothing (+0.9pp frozen, best feature). The sign-structure
  survivor (sustained all-scale build) was demoted to a forward-only
  hypothesis after an adversarial audit found the first run deviated
  from its declaration (docs/CH3_DEEP_BUILD_FORWARD_REGISTRATION.json;
  no peeking before n=100). A 70-stock whole-life reading taxonomy
  FAILED its blind test under the +20%/5-day clock; under field-scored
  outcomes (declared docs/CH3_BLIND_TEST_SCORING_20260818.md) one
  narrow lead survived: blind readers separate "will not fully
  unwind" about 6:1 — a lead with a second-look caveat, fresh forward
  test required. The decade sweep inverted the live/dead-charge
  claim; the coarse fact that held in both halves: blocked approaches
  (no boundary closures / channel shut) run more (18–20% vs 15.5%
  base), resolving approaches less (11.7–14.1%).
- The price-scar result (stocks with a prior pump-collapse cycle are
  the fade's richest stratum: 3–10× the dollars per 100 trades,
  unwind rates 26–38% vs 17–22%) uses two hand-picked constants and
  is NOT kernel analysis — Joe rejected it as such. A kernel-native
  rerun (tools/ch3_kernel_scar.py) was stopped incomplete.
- tools/ch3_joint_field_full.py implements the COMPLETE tuple chain
  from the verbatim document (typed topology, dyadic custody, L0–L4,
  declared quotients). Committed, never run — Joe stopped the run.
  The math documents beside it: docs/CH3_JOINT_FIELD_MATH_20260817.md,
  docs/CH3_TUPLE_TIME_MATH_20260817.md,
  docs/CH3_PRECEDENT_MATH_20260818.md.
- Joe's final assessment of this agent's kernel work: persistent
  flattening — single-signal reductions wearing kernel vocabulary.
  Treat every finding above with suspicion; re-derive under his
  stated method (the full tuple, dimensionalized across time, whole
  lifetimes, compared to similar shares, with group and system
  energy) before any of it touches an engine. Nothing from the
  kernel week is in any engine.

## 6. First actions for Sol

1. Re-arm the publish clock (Monitor died with the session).
2. Confirm the three runners are alive; restart pattern in
   tfe-daily-ops.
3. Nightly sequence: supply-tail refresh → close pass → kill test →
   EOD report page.
4. Books at handoff (they move daily — the JSON files are the truth):
   CH3 cash −$81,096.14 on margin, realized +$1,107.39 lifetime;
   CH6 cash $65,564.72; CH4 cash $32.28 (fully invested).
5. CH2: nothing pending; rebuild the deploy toolchain before any
   deploy, and touch nothing without Joe's word.
