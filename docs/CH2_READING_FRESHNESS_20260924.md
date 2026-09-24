# CH2 — the readings behind half the book were a week old

Joe, 2026-09-24, on the open book: *"what of all the other stale losers —
that portfolio looks like a waterloo"* and *"do what you think is best."*
Measured first. Two defects found and fixed; one older pair of positions
explained. Nothing sold by hand.

## The book at 10:00 AM ET

```
2 from July (CWAN, HTBK)    flat, 72 days       readings frozen since April / June
19 bought 09-16/17          8 days old          14 red, 5 green   -$1,158 on $48,540 (-2.4%)
                                                SPY over the same days +1.4%
9 bought today              -0.6% first morning
```

## Defect 1 — the nightly kernel refresh skips 42 % of the universe

The nightly refresh (`?mode=snapshot`, 00:17 UTC) runs the rebuild in
**targeted PFSC** mode. Its selector, from the live report:

```
Include symbol if regime != STABLE OR bar_count < 514 OR tenant-linked OR curated index/crypto
selected_union   6,775        selector_source_rows   11,685
```

The other **4,852 symbols** (STABLE regime, ≥ 514 bars) are cloned from the
previous night's row, with a new run_id and the old `last_bar_timestamp`.
They get a real kernel reading only on the Sunday `universe_snapshot` run.

```
last_bar_timestamp on the 09-24 run:   2026-09-23  6,016   |  2026-09-18  4,642   |  older 1,027
STABLE & >= 514 bars                   4,969   (4,852 of them stale)
```

CH2 positions held on a 09-18 reading on 09-24: BAM, IVZ, MSBI, RBC, SNY,
VALE. IVZ was bought today on it. The kernel is a black box; feeding it a
week-old prefix and calling the output today's reading is not.

Before 09-20 the nightly loop covered ~10,900 names (daily_bars rows per
session 09-14..09-18: 10,953 / 10,931 / 10,904 / 10,932 / 10,915). The
Sunday 09-20 full run re-labelled ~4,900 names STABLE, and from 09-21 the
targeted loop dropped them (6,303 / 6,156 / 6,016). So the week-old
readings began three days before CH2 started buying from the widened pool.

**Fix (MINE):** `web/src/app/api/admin/refresh/route.ts` — the nightly
`snapshot` mode now passes `--refresh-mode full_universe` (still
`--skip-l5-learning`, still the light env, no universe re-pull).
`TFE_SNAPSHOT_REFRESH_MODE=targeted_pfsc` restores the old behaviour.
Cost: the rebuild runs in-process with no kill budget; last night it
recomputed ~6,300 names in 2,018 s, so the full universe is roughly an
hour, done well before the 13:45 UTC entry pass. **No model calls anywhere
in the refresh** (the CH2 reading pass stays OFF per Joseph 09-19).

## Defect 2 — the dead clock counted sync runs, not sessions

Joseph's dead clock (09-15) sells a position that closes > 5 % under entry
and stays there 16 closed sessions with no heal. The sentinel fed it from
`runtime_bars_daily`, whose `bar_date` is **the date the nightly sync ran**
(`barDate = generatedAtUtc.slice(0,10)`), with the quote-cache price at
that moment:

```
MSBI  runtime_bars_daily   09-16 33.67 | 09-17 33.33 | 09-18 33.33 | 09-19 33.33 | 09-20 33.54 | 09-21 33.54 | 09-22 33.55 | 09-23 33.55 | 09-24 32.39
MSBI  true sessions        09-15 33.67 | 09-16 33.33 | 09-17 33.63 | 09-18 33.54 | 09-21 33.55 | 09-22 32.88 | 09-23 32.39
```

Weekend rows, duplicated closes, and two real sessions (09-17, 09-22) that
never appear. The clock counted calendar rows and could miss the very heal
that ends an episode. VRTS showed "below the line since 09-20, 4/16" — the
"09-20" bar is the 09-18 close.

**Fix (MINE):** `sentinel_monitor.mjs` — the clock now reads `daily_bars`
(one row per ticker per trading session, provider bars; the table the
kernel itself is fed from). With Defect 1 fixed it is complete every night
for the whole universe.

## CWAN and HTBK — 72 days, flat, unreadable

Their price histories in `daily_bars` end 2026-04-17 (HTBK) and
2026-06-24 (CWAN). The provider returns no bars after those dates; the
delta fetch comes back empty; the cached bars are reused; the kernel
reading is cloned every night (bar_count 1261 / 1191 unchanged for months,
`last_bar_timestamp` April / June). The dead clock cannot tick on them
either. Only the 90-day wall (Joseph 08-25) can sell them: 2026-10-12.
Not sold by hand; recommendation is to let the wall take them, and to
check why the provider stopped serving these two tickers (rename or
delisting) — separately.

## The losers — nothing sold

Eight days, −2 to −7 %, market +1.4 %. The audit on file says most losers
sold at 0–3 days were winners at 20; the dead clock exists for exactly
this. First clock verdicts on the current worst (VRTS, DEI, LINE, HRB) land
around 2026-10-08 on true sessions. The −20 % brake stands under all of it.

## The nightly "FAILED" stamp — fixed (Joseph's word, same day)

Every nightly refresh since 09-16 ended `report_status=error`,
`failure_code=VALIDATION_GATE_FAILED`. The gate runs 18 checks; 17 pass
every night (tables present, 11,685 rows, joins intact, readings under an
hour old, every decision row well-formed). The 18th,
`ui_filter_behavior_integrity`, is a **website test**: it signs into the
site and checks the screener's sector and minimum-price filters on seven
tabs. It needs `TFE_VALIDATION_BASE_URL/USERNAME/PASSWORD`, which no
container has ever carried, so it sits at `not_run`; the 2026-08-18 rule
counts a check that cannot run as failed; so no nightly run could pass.
It has no bearing on the readings or on trading, which read the tables
directly and never consult the gate.

Joseph: *"do what you think you need to do."* Commit `9ab109a01`: the
check is **advisory** — still run, still recorded with its real status,
no longer part of the verdict (`advisoryValidationCheck` /
`validationReportPassed` in `web/scripts/validation_status.mjs`; tests
extended). The 08-18 rule stands for every blocking check.

## Still open — the activation bypass (not touched)

`web/src/app/api/admin/refresh/route.ts` has four functions stubbed to
constants since 2026-03-13 (Codex, "Bind production deploy tree to git
commit"): `publicationActivationRowIsValid → true`,
`publicationActivationFailureReasons → []`, and both payload/merge
functions returning `validationStatus: "pass"`,
`quoteBindingStatus: "bypass_active"`. The website's "active
publication" pointer is a run from 2026-03-28 marked `pointer_invalid`,
`serving_state=blocked`. The site serves through the stubs. Restoring the
real activation logic blind could block the site's serving path, so it
was left alone tonight; it needs the real logic mapped and a serving
test before removal. Trading is unaffected either way.

## Verification, tonight and tomorrow

```
deploy            after the close (rolling deploy overlaps two containers)
tonight 00:17 UTC [UF-SNAPSHOT] Refresh mode: full_universe ; Processing N/11685
tomorrow          every runtime_decisions_latest row last_bar_timestamp = 2026-09-24
                  [SENTINEL] CH2 <ticker> dead clock lines with true session counts
```
