# Load Directive For Next Chat

Generated UTC: 2026-03-26T02:05:00Z
Workspace: `/workspaces/Tao_Financial_Engine`

## Read First

Read these files before doing any work:

1. `/workspaces/Tao_Financial_Engine/AGENTS.md`
2. `/workspaces/Tao_Financial_Engine/PRODUCTION_EVALUATION_CONTRACT.md`
3. `/workspaces/Tao_Financial_Engine/LOAD_DIRECTIVE_NEXT_CHAT.md`
4. `/workspaces/Tao_Financial_Engine/L5_CANONICAL_BASELINE.md`
5. `/workspaces/Tao_Financial_Engine/tfe_l5_baseline.py`
6. `/workspaces/Tao_Financial_Engine/tfe_fundamental_fetcher.py`
7. `/workspaces/Tao_Financial_Engine/quarantine_historical_kernel.py`
8. `/workspaces/Tao_Financial_Engine/quarantine_backtester.py`
9. `/workspaces/Tao_Financial_Engine/quarantine_sequential_filter.py`
10. `/workspaces/Tao_Financial_Engine/quarantine_governance_sweeper.py`
11. `/workspaces/Tao_Financial_Engine/quarantine_bottleneck_diagnostic.py`
12. `/workspaces/Tao_Financial_Engine/quarantine_base_pool_truth.py`
13. `/workspaces/Tao_Financial_Engine/quarantine_primitive_governance_join.py`
14. `/workspaces/Tao_Financial_Engine/DSF_PRIMITIVE_FULL_FIELD_SORTABLE_V3_RATIONALIZED.md`
15. `/workspaces/Tao_Financial_Engine/DSF_GOVERNANCE_HANDOFF_FROM_FROZEN_PRIMITIVE.md`

## Mandatory Architecture Honesty Gate

Before any substantial work, the next chat must explicitly state:

1. `requested architecture`
2. `current code reality`
3. `conflict with requested architecture: yes or no`
4. `what exact mechanism or files will not be extended`
5. `the single exact next item`

For any L5 or DSF-related work, the next chat must also explicitly state:

6. `am I evaluating the full field or a reduced approximation?`
7. `if reduced, what exact field structure is being lost?`

## Permanent Carry-Forward Contracts

These remain active:

1. the user is not a developer
2. do not guess structure, behavior, or intent
3. no masking, smoothing, or false reassurance
4. if current code conflicts with requested architecture, say so before any edit
5. do not extend wrong architecture just because it already exists
6. do not flatten DSF into a reduced proxy when explicit DSF fields are available unless explicitly approved
7. if only a reduced approximation is being evaluated, say that plainly
8. Slack ping is required on completion or when blocked, and the result must be checked in `/workspaces/Tao_Financial_Engine/backups/runtime/codex-notify.log`

## Files That Must Not Be Extended Without Explicit Approval

1. `/workspaces/Tao_Financial_Engine/web/src/lib/uf-dynamic-decision.ts`
2. `/workspaces/Tao_Financial_Engine/web/src/lib/uf-dynamic-decision-pressure-test.ts`
3. `/workspaces/Tao_Financial_Engine/DSF_PRIMITIVE_LAW_SKETCH.md`
4. `/workspaces/Tao_Financial_Engine/DSF_PRIMITIVE_INTERPRETATION_RECOVERY.md`
5. `/workspaces/Tao_Financial_Engine/DSF_PRIMITIVE_FULL_FIELD_SORTABLE_V3_RATIONALIZED.md`

## Current Honest Status

There are now two parallel lines of truth in this workspace:

1. frozen DSF primitive line
2. quarantine research line

The frozen DSF primitive line is documented and frozen:

1. `/workspaces/Tao_Financial_Engine/DSF_PRIMITIVE_FULL_FIELD_SORTABLE_V3_RATIONALIZED.md`
2. `/workspaces/Tao_Financial_Engine/DSF_GOVERNANCE_HANDOFF_FROM_FROZEN_PRIMITIVE.md`

Important frozen primitive facts:

1. fixed-snapshot counts:
   - `Accumulate = 133`
   - `Hold = 1132`
   - `Avoid = 4148`
2. anchors:
   - `9 / 9`
3. adjudicated sample metrics:
   - `rational_match = 90.52924791086329%`
   - `conservative_but_plausible = 5.849582172701926%`
   - `suspicious_mismatch = 3.6211699164345257%`
   - `zero_basin_fallback = 0.0%`
   - `plausible_total = 96.37883008356522%`
4. that primitive is frozen for governance work

The quarantine research line is the most current active research surface in this chat.

## Quarantine Data Lake

Critical input/data artifacts:

1. `/workspaces/Tao_Financial_Engine/quarantine_12k_universe.parquet`
2. `/workspaces/Tao_Financial_Engine/quarantine_12k_historical_states.parquet`
3. `/workspaces/Tao_Financial_Engine/quarantine_12k_governed_states.parquet`
4. `/workspaces/Tao_Financial_Engine/quarantine_12k_l5_trades.csv`
5. `/workspaces/Tao_Financial_Engine/quarantine_12k_governed_l5_trades.csv`
6. `/workspaces/Tao_Financial_Engine/quarantine_5yr_universe.parquet`
7. `/workspaces/Tao_Financial_Engine/quarantine_historical_states.parquet`
8. `/workspaces/Tao_Financial_Engine/quarantine_l5_trades.csv`

Important quarantine facts:

1. 12k ingest succeeded with:
   - `11884` symbols saved
   - `10162966` OHLCV rows
2. 12k historical kernel succeeded with:
   - `11884` symbols processed
   - `8343139` state rows
3. primitive-only 12k backtest on `quarantine_12k_historical_states.parquet`:
   - `Total Signals = 7658`
   - `5d avg = 1.2571%`
   - `5d win = 54.08%`
   - `10d avg = 1.4729%`
   - `10d win = 55.71%`
   - `20d avg = 2.7036%`
   - `20d win = 57.13%`

## Governed Quarantine Findings

Critical governed scripts:

1. `/workspaces/Tao_Financial_Engine/quarantine_historical_kernel.py`
2. `/workspaces/Tao_Financial_Engine/quarantine_backtester.py`
3. `/workspaces/Tao_Financial_Engine/quarantine_governance_sweeper.py`
4. `/workspaces/Tao_Financial_Engine/quarantine_bottleneck_diagnostic.py`
5. `/workspaces/Tao_Financial_Engine/quarantine_base_pool_truth.py`
6. `/workspaces/Tao_Financial_Engine/quarantine_primitive_governance_join.py`
7. `/workspaces/Tao_Financial_Engine/quarantine_sequential_filter.py`

Important governed findings:

1. CV-1.0 governed backtest on `quarantine_12k_governed_states.parquet`:
   - `Total Signals = 0`
   - `20d avg = 0.0000%`
   - `20d win = 0.00%`
2. bottleneck diagnostic on the base pool:
   - `Base Pool Rows = 3583`
   - `chi_n = 1.0` for all base-pool rows
   - `raw_x_m` median = `1.000000`
   - `F_n` min = `1.143867`
   - `F_n` median = `1.643044`
   - prior governance caps were below the actual `F_n` floor
3. primitive-governance cross-join on the exact `7658` primitive trades:
   - winners = `4165`
   - losers = `3094`
   - winners had lower `F_n` than losers
   - `chi_n` was `1.0` for both winners and losers
   - current governance variables do not cleanly separate winners
4. base-pool truth without Layer 3 governance:
   - `Total Signals = 3583`
   - `20d avg = -0.1151%`
   - `20d win = 50.09%`
   - high `F_n` quartile was less bad than low quartiles, but still negative
5. calibrated governance sweep:
   - best reported positive-average top-5 candidate was weak
   - no strong governance-only rescue was found
6. sequential cognitive filtering on the original `7658` primitive trades:
   - Filter A: `Close >= 5.0`
   - Filter B: `raw_x_m <= 0.50`
   - Filter C: `F_n <= 1.65`
   - result:
     - `Total Signals = 3587`
     - `5d avg = 0.5605%`, `5d win = 60.92%`
     - `10d avg = 0.6947%`, `10d win = 63.47%`
     - `20d avg = 1.2524%`, `20d win = 64.66%`
7. current honest recommendation from the quarantine line:
   - the sequential filter is the first governance-assisted filter that materially improved the primitive trade set

## Fundamental Reality Check Module

Critical new module:

1. `/workspaces/Tao_Financial_Engine/tfe_fundamental_fetcher.py`

What it does:

1. standalone `FundamentalCorpora` class
2. requires `POLYGON_API_KEY`
3. uses `/vX/reference/financials`
4. evaluates three equity domains:
   - Survival via Current Ratio
   - Energy via Free Cash Flow
   - Margin via Gross Margin
5. crypto path explicitly bypasses SEC-style checks
6. missing required metric fails closed

Live smoke truth:

1. syntax check passed
2. `AAPL` failed closed because the live endpoint response did not include `capital_expenditure`
3. crypto pass path worked

Important warning:

1. if deployment work depends on this module, the next chat must explicitly decide whether missing `capital_expenditure` from the Polygon response should remain a hard fail or be mapped from another approved endpoint
2. do not silently weaken that failure rule

## Current Incomplete Tasks

These are the real incomplete items from this chat:

1. deployment integration work on top of `/workspaces/Tao_Financial_Engine/tfe_l5_baseline.py` has not been done yet
2. `tfe_fundamental_fetcher.py` exists, but no approved production integration path has been chosen
3. no approved decision has been made about whether the sequential quarantine filter should become:
   - a research-only lane
   - a candidate deployment lane
   - or only a diagnostic result
4. no symbol-level concentration audit has been done yet on the improved sequential-filter result beyond the simple top-10 frequency table

## Recommended Single Exact Next Item

Recommended option:

1. decide the integration role of the sequential filter before touching deployment code

Reason:

1. the sequential filter is the only governance-assisted result that materially improved the primitive trade set in this chat
2. the standalone fundamental reality-check module now exists, but its production fail-closed behavior must be explicitly accepted before wiring it into baseline or deployment logic

## Copyable Resume Prompt For The Next Chat

Paste this into the next chat:

```text
Read `/workspaces/Tao_Financial_Engine/AGENTS.md`, `/workspaces/Tao_Financial_Engine/PRODUCTION_EVALUATION_CONTRACT.md`, `/workspaces/Tao_Financial_Engine/LOAD_DIRECTIVE_NEXT_CHAT.md`, `/workspaces/Tao_Financial_Engine/L5_CANONICAL_BASELINE.md`, `/workspaces/Tao_Financial_Engine/tfe_l5_baseline.py`, `/workspaces/Tao_Financial_Engine/tfe_fundamental_fetcher.py`, `/workspaces/Tao_Financial_Engine/quarantine_historical_kernel.py`, `/workspaces/Tao_Financial_Engine/quarantine_backtester.py`, `/workspaces/Tao_Financial_Engine/quarantine_sequential_filter.py`, `/workspaces/Tao_Financial_Engine/quarantine_governance_sweeper.py`, `/workspaces/Tao_Financial_Engine/quarantine_bottleneck_diagnostic.py`, `/workspaces/Tao_Financial_Engine/quarantine_base_pool_truth.py`, and `/workspaces/Tao_Financial_Engine/quarantine_primitive_governance_join.py` first. Then continue from the current honest state. Critical facts: the frozen DSF primitive remains documented and frozen; the quarantine 12k primitive-only backtest produced `7658` signals with `20d avg 2.7036%` and `20d win 57.13%`; the governed CV-1.0 backtest produced `0` signals; the best result in this chat came from the sequential filter on the original primitive trades using `Close >= 5.0`, `raw_x_m <= 0.50`, and `F_n <= 1.65`, which produced `3587` signals with `20d avg 1.2524%` and `20d win 64.66%`; `tfe_fundamental_fetcher.py` was created as a standalone module using `POLYGON_API_KEY`, but live `AAPL` failed closed on missing `capital_expenditure`; the single exact next item is to decide whether the sequential filter is only a research lane or a candidate deployment lane before touching baseline/deployment integration code.
```
