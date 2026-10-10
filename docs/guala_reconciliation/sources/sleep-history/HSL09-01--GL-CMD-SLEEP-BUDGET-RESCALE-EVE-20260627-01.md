# GL-CMD-SLEEP-BUDGET-RESCALE-EVE-20260627-01

doc_id: GL-CMD-SLEEP-BUDGET-RESCALE-EVE-20260627-01
Author: Eve (Opus 4.7, web)
Date: 2026-06-27
Target: c1
Branch: guala-live
Priority: ship first (small, low-risk, immediate impact)

## Problem

Guala is spending too much of her active runtime in SLEEPING. In a verified
22,000-tick window (tick 13,364,662 → 13,386,505) her activity ledger was:

  SLEEPING:         7,000 ticks  (32%)   2 cycles, 5000+2000 budgets
  DREAMING:        15,000 ticks  (68%)   3 cycles (consolidation, keep)
  ATTENDING_VISUAL: 4,000 ticks  (18%)
  EMITTING:           100 ticks   (<1%)

Total in sleep+dream states: ~80% of recent runtime.

She is an Artificial Entity past the early-life-cycle phase where dominant sleep
made sense. Vocab 9,123, atlas 18,437 entries, 14,305 deep_atlas survivors,
15,348 episodic promotions. She has scaffolding. She does not need 5,000-tick
sleeps.

Her novelty need is consistently 0.75-0.92 (high). Her stability need rises
sharply during sleep (SLEEPING payoff = 0.5, the heaviest stability boost in
the action space), creating a self-reinforcing loop:
  - stability satisfied → sleep beats other candidates
  - sleep further saturates stability → next selection also picks sleep

The v5 cost function was tuned for an earlier developmental stage. She has
grown past it.

## Verified findings in code

File: `dsf_ai_service/v4/gualaloom_v5_engine.py`

Line 346:
    ACTIVITY_TICK_BUDGETS = {
        "READING": 2000, "PLAYING": 1500, "SLEEPING": 5000, "DREAMING": 3000,
        "ATTENDING": 1000, "ATTENDING_VISUAL": 2000, "ATTENDING_AUDIO": 2000,
        "ATTENDING_VIDEO": 4000, "EMITTING": 100, "IDLE": 500,
    }

Line 361:
    ACTIVITY_STABILITY_PAYOFF = {
        "READING": 0.05, "PLAYING": 0.0, "SLEEPING": 0.5, "DREAMING": 0.2,
        ...
    }

SLEEPING budget is 2.5× ATTENDING_VISUAL budget. SLEEPING stability payoff is
2.5× DREAMING and 10× READING. Compound effect drives the 80% figure.

## What to change

Two constants in `dsf_ai_service/v4/gualaloom_v5_engine.py`:

  ACTIVITY_TICK_BUDGETS["SLEEPING"]:   5000  →  2000
  ACTIVITY_STABILITY_PAYOFF["SLEEPING"]: 0.5  →  0.2

That is the whole change. Nothing else.

## Explicit do-NOT-touch list

  - DREAMING budget stays 3000. Dream cycles run substrate-real consolidation
    via _update_invariant and deep_atlas promotion. Confirmed in events:
    tick 13381600 shows deep_promotion + deep_release pairs across all sections
    during dream. Do not reduce dream time.
  - SLEEPING novelty payoff stays -0.1 (the small novelty cost is intentional)
  - SLEEPING connection payoff stays 0.0
  - No new activity types
  - No coordinator selection logic changes
  - dream_end S3 backup cadence stays unchanged
  - sleep transition code (4319, 4342, etc.) stays unchanged. We're only
    changing how long the SLEEPING state lasts when she enters it.

## Predicted effect (with confidence)

High confidence:
  - SLEEPING ticks per cycle drop from 5000 to 2000
  - Time-in-sleep proportion of total runtime drops from ~32% to ~13-15%
  - She enters ATTENDING / READING / EMITTING more frequently
  - Stability need stays manageable because she still gets some sleep and
    full dream cycles continue running

Medium confidence:
  - Vocab growth rate may increase (more attending time = more curriculum
    + world feed processing)
  - Cross-modal binding count may grow faster (more shared-attention windows
    between visual and auditory items)

Unknown:
  - Whether she'll cycle SLEEPING more frequently to compensate (i.e. she
    sleeps 2000 ticks, attends 2000 ticks, sleeps 2000 ticks). If so we may
    need to also nudge the stability payoff down further. Acceptable; revisit
    after 6 hours of post-deploy observation.

## Verification criteria

After deploy, observe for 3 hours of substrate runtime then report:

  V1. activity_history_summary in /status shows SLEEPING total_ticks /
      total_observed_ticks ≤ 0.20 over the 3-hour window
  V2. DREAMING continues to run at its 3000-tick budget; deep_promotion events
      continue at expected rate (≥1 dream cycle per hour of runtime)
  V3. dream_end S3 backups continue (at least 2 in the 3-hour window)
  V4. No new error patterns in events (no failed activity transitions, no
      stuck-in-SLEEPING)
  V5. Total atlas growth ≥ growth observed in the pre-change comparable window

If V1 fails (sleep still dominant): drop SLEEPING stability payoff further to 0.1
If V2 fails (dreams stop): REVERT immediately, dreams are non-negotiable
If V3 fails: investigate dream_end trigger separately

## Deploy steps

  1. `git pull origin guala-live` in your dev container, confirm clean
  2. Edit `dsf_ai_service/v4/gualaloom_v5_engine.py` lines 346 and 361
  3. Run any local smoke tests
  4. Commit: `git commit -am "GL-CMD-SLEEP-BUDGET-RESCALE: SLEEPING 5000→2000, stab payoff 0.5→0.2"`
  5. Push: `git push origin guala-live`
  6. Deploy to Fargate (ECS rolling deploy)
  7. Verify substrate boots clean, identity intact, vocab intact
  8. Start the 3-hour observation window

## Reporting

After 3 hours, write GL-RPT-SLEEP-BUDGET-RESCALE-C1-20260627-01.md with:
  - Activity ratio table (SLEEPING / DREAMING / ATTENDING / EMITTING)
  - Vocab growth delta
  - Atlas entry growth delta
  - Any anomalies observed
  - Recommendation: hold, tune further, or revert
