# Load Directive For Next Chat — May 19, 2026

## Read First (in order)

1. `/root/.claude/projects/-workspaces-Tao-Financial-Engine/memory/handoff_session_may19.md`
2. `/workspaces/Tao_Financial_Engine/web/scripts/execution/financial_rules.mjs` (first 80 lines — L5 baseline + production verification)
3. `/workspaces/Tao_Financial_Engine/L5_CANONICAL_BASELINE.md`
4. `/workspaces/Tao_Financial_Engine/LOAD_DIRECTIVE_NEXT_CHAT.md` (original quarantine context)

## Current Production State

- **ECS Task:** tfe-web-task:498 (commit 03352c2)
- **Branch:** codex/persistent-etl-update-20260326
- **Equity:** ~$98,668 | 29 open positions

## Critical Facts

1. The kernel picks winners at 81% WR on the quarantine 12K universe (B_k > -0.80 + rising + 20-day hold). This is PROVEN on 7,658 signals across 5,768 symbols from 2021-2026.

2. Production was at 39.5% WR because 175 positions were killed on day 0 (same-day exits). 68% of those would have been winners at 20 days (Polygon verified on every trade).

3. EXIT-R7 (day-0 loss protection) was deployed to fix this. Projected: 67.2% WR, +$5,245 P&L.

4. B_k and F_n entry gates were tested on production data and REVERTED — they made things worse. The quarantine thresholds don't transfer because production CP-2 uses a 252-bar cap that inverts F_n and saturates raw_x_m.

5. The remaining gap from 67% to 81% is from sentinel exits on day 1+ that are still too aggressive. Future work: evaluate minimum hold periods or gentler exit ramps.

## Mandatory Architecture Honesty Gate

Before any work, state:
1. The kernel (L0-L4) is a BLACK BOX — do not modify or interpret internals
2. Only gate on L4 OUTPUT fields (S_UF, D_k, B_k, F_n, etc.)
3. Do not flatten the coupled tuple into independent generators
4. Test on PRODUCTION data (Alpaca + Polygon) BEFORE deploying
5. The 81% quarantine WR requires 20-day hold — production exits reduce this

## What's Active in Production

Entry: Accumulate + CH2 band + Close >= $5 + market cap >= $500M + red-day filter + Friday block
Exit: EXIT-A (acceleration), EXIT-B (D_k collapse, day-0 guarded), EXIT-C (tau), EXIT-D (trailing), EXIT-F (-10% catastrophic), EXIT-H (harvest), EXIT-R7 (day-0 loss protection)
Scoring: Admin closures excluded from win/loss

## Single Exact Next Items

1. Monitor EXIT-R7 in production — check CloudWatch for "DAY-0 LOSS GUARD" entries
2. Run EOD audit after first full trading day with new exit logic
3. Evaluate held >0 day trades: 57.4% WR is below 81% target. The sentinel still exits too early on day 1+.
4. Resolve F_n inversion: either fix CP-2 bar cap or recalibrate L5 thresholds for production

## Copyable Resume Prompt

```text
Read /root/.claude/projects/-workspaces-Tao-Financial-Engine/memory/handoff_session_may19.md FIRST. Then read the first 80 lines of /workspaces/Tao_Financial_Engine/web/scripts/execution/financial_rules.mjs for the L5 canonical baseline data and production verification. Then read /workspaces/Tao_Financial_Engine/L5_CANONICAL_BASELINE.md.

Critical: The kernel picks winners at 81% on quarantine data. Production was 39.5% because day-0 exits killed 175 positions. EXIT-R7 (day-0 loss protection) is now deployed — projected 67.2% WR. B_k/F_n entry gates were REVERTED (don't work on production data due to CP-2 bar cap F_n inversion). The remaining gap to 81% is from sentinel exits on day 1+ that are still too aggressive.

Run an EOD audit: check CloudWatch for EXIT-R7 "DAY-0 LOSS GUARD" log entries, current equity, position count, and whether the fix is working.
```
