# CH2 — why no entries since 2026-09-17, and the fix

Short record with receipts. Operational state before this is in
`CH2_STATE_20260921.md`.

## The finding

CH2 placed no new entries after 2026-09-17 with $49,740 of cash idle.
The kernel gate was not the reason. The entry pre-filter was.

`fetchCandidateRows` in `web/scripts/execution/ch2_strategist.mjs` required

```
COALESCE(NULLIF(runtime_symbols.market_cap, 0), l5_fundamentals_normalized.market_cap, 0) >= 500000000
```

Measured against the live database on 2026-09-23 (run `578df27a`):

```
runtime_decisions_latest                 11,685 tickers
runtime_symbols.market_cap > 0               53 tickers   (54 on every run since 2026-03)
l5_fundamentals_normalized.market_cap > 0 1,985 of 5,056 rows, MIXED UNITS:
    AAPL   3,712,713,494,600     dollars
    MSFT   2,755,205,412,359     dollars
    BFST   944.4                 millions  (Business First Bancshares, ~$944M)
    STAK   1000.0                millions?
    HBCP   557,500,000,000,000   garbage (5.6e14)
    ACB    134,840,000,000,000   garbage
    125 rows < 1e6 | 652 rows 1e6..1e9 | 1,206 rows 1e9..1e13 | 2 rows > 1e13

coverage of the pre-filter:   big 1,389 | small 621 | NO CAP ON FILE 9,675   (83%)
```

So 83 % of the universe was dropped for having **no market cap on file**,
not for being small. The pool CH2 could trade from was 1,389 tickers, and
it has been that size since the rule went in on 2026-05-04
(`cb8f2a138`, Codex: *"$500M floor via runtime_symbols.market_cap JOIN
removes worst offenders"*). The 428 live trades at 57.4 % all came from
that pool.

Live funnel on 2026-09-23, from the container log:

```
[CH2-DIAG] pre-basin candidates: 1389
[CH2-STRATEGIST] 1389 candidates → 20 passed V3 basin → 1 dedup → 1 after epoch governance
[DAILY-ENTRY] CRVL excluded: cooling off after the law sold it (ch2_reading_dead_exit, 14 days)
```

Every basin passer inside the 1,389 pool was already held. Over the whole
universe the full gate (Accumulate, basin ≥ 0.15, break < 0.20,
B_k > −0.50, bar_count ≥ 21) passed **47** tickers: 19 held, 28 not
held. 27 of the 28 were invisible to CH2 because of the cap column.

## Whose rule

ENTRY-R5 is **Codex's rule** (2026-05-04), recorded in
`financial_rules.mjs` under the 2026-05-19 changelog. It is not Joe's.
Its stated purpose is liquidity: *"tiny-caps have fill problems and wide
spreads."* The purpose stands. The measurement it used does not exist for
most of the universe.

## The fix (MINE — Claude, 2026-09-23)

Same purpose, measured directly, on data that exists for every ticker:

```
price × runtime_metrics_latest.avg_volume  >=  $2,000,000 a day
```

- `runtime_metrics_latest` has 11,685 rows, one per ticker, rebuilt with
  the same run as the readings (same `run_id`, same timestamp
  2026-09-23T00:17:31Z). `avg_volume > 0` on 11,506 of 11,513 tickers with
  bar_count > 20.
- $2M a day against a ~$2,500 order (SIZE-R1) is about 0.1 % of one day's
  trade. The number is mine; nothing was measured to pick $2M over $1M or
  $5M. Counts at each: $1M 6,588 | $2M 5,620 | $5M 4,480 | $10M 3,639.
- New pre-basin count on the live run: **5,620** (was 1,389). With the
  $5 price floor the bridge applies (ENTRY-R3): 5,104.
- `runtime_symbols` and the cap column are no longer read by CH2.
  `l5_fundamentals_normalized` is still joined for `sector` only.

Of the 28 un-held passers, the ones the new floor lets through today
(dollar volume, $M/day): DOC 93.9, IVZ 116.5, PRKS 21.5, RECS 19.0,
FBRT 17.1, OCFC 17.0, CRVL 13.9 (in cooldown), AVO 8.9, HEWJ 7.2,
BFST 6.3, CFFI 5.6, SIND 2.6, AVBH 2.1. Still blocked: FNRN 1.8,
FLJH 1.7, FTHF 1.3, AEMS 1.2 (also under $5), KBA 1.2, AIVC 1.0,
NORW 0.9, QTUP 0.8, XOVL 0.3, ASHS 0.3, SGU 0.2, REKT 0.14,
BITK 0.05, MRA 0.04, COIO 0.01.

## ENTRY-R11 — stocks only (JOE's rule, 2026-09-23)

Funds never had a market cap, so the old filter kept them out by
accident; the dollar-volume floor would have let them in. Joe, on
reading the first version of this record: *"I think funds should come
out."* So:

```
LOWER(TRIM(snapshot_row_json->>'asset_type')) = 'stock'
```

Labels on the live run: stock 5,986 | etf 5,664 | crypto 25 | index 10.
Of the 47 basin passers, 15 were funds (HEWJ, RECS, NORW, FLJH, FTHF,
AIVC, KBA, XOVL, ASHS, QTUP, REKT, BITK, COIO, MRA, AEMS). 32 stocks
remain.

Pre-basin count, live run, both rules: **3,765** (old 1,389; dollar
volume alone 5,620).

## What was changed

```
web/scripts/execution/ch2_strategist.mjs
    CH2_MIN_MARKET_CAP removed
    CH2_MIN_AVG_DOLLAR_VOLUME = 2_000_000 (exported)            MINE
    CH2_ENTRY_ASSET_TYPE = "stock" (exported)                   JOE
    liquidityFloorPasses(price, avgVolume) (exported, pure)
    entryAssetTypeAllowed(assetType) (exported, pure)
    fetchCandidateRows: JOIN runtime_metrics_latest, dollar-volume + asset_type conditions
    [CH2-DIAG] query: same conditions
web/scripts/execution/financial_rules.mjs
    ENTRY-R5 changelog entry + entryR5_LiquidityFloor (record copy)
    ENTRY-R11 changelog entry
web/scripts/execution/tests/ch2_liquidity_floor_test.mjs
    24 tests on real rows and labels from the 2026-09-23 run — 24/24 pass
    sentinel_bugs_test.mjs still 29/29
```

## Deploy timing

The ECS service rolls with minimumHealthyPercent 100 / maximumPercent
200, so two containers overlap for a few minutes, and the daemon has no
instance lock. Both earlier deploys this week ran outside market hours
for that reason. The entry pass runs once a day at 09:45 ET and is
recorded in `pee1_execution_config.lastEntryPassDate` (= 2026-09-23
already), so a mid-day deploy would not produce entries today anyway.

Deploy after the 20:00 UTC close. First entry pass on the new pool:
2026-09-24 13:45 UTC.

After deploy, verify all three toggles: env `TFE_ENTRIES_HALTED=0`,
DB `auto_tfe_enabled=true`, DB `entries_halted=false`.

## What this does not change

- The grading bar in `CH2_STATE_20260921.md` stands: 20 closures opened
  after 2026-09-21; ENTRY-R10 comes out at or below 57.4 %.
- Nothing inside the kernel. Nothing in the basin gate. Nothing in exits.
- The two cap columns are still wrong in the database. Not repaired;
  CH2 no longer depends on them.
