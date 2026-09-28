# CH2 — old batch cleared, fresh-logic baseline set — 2026-09-28

Joseph, 09-25: *"I am just trying to clear out past tickers so we can
evaluate fresh logic."* 09-28, on the recommendation to sell the 14 left
from 09-16: *"proceed."*

## Sold — 14 positions opened 2026-09-16, all at market, all filled 12:31–12:33 ET

```
HRB   -$257.05  -10.60 %      VRTS  -$125.97   -5.40 %
AEBI  -$248.88  -10.14 %      SNY    -$95.76   -3.92 %
DEI   -$192.70   -7.85 %      BAM    -$94.87   -3.88 %
LINE  -$175.77   -7.23 %      AROW   -$77.21   -3.16 %
FIZZ  -$166.92   -6.82 %      HTH    -$46.62   -1.90 %
VALE  -$141.10   -5.74 %      MSBI   -$44.53   -1.81 %
AGNC  -$129.85   -5.28 %      BDX    -$38.35   -1.59 %
                                     -$1,835.58 realized
```

Same mechanism as 09-25 (`ch2_clear_old_batch.js`, run as `node` inside
the serving container: market sell, ledger close as `ledgerClose` does,
kill-cooldown key as `markRecentlyKilled` does). `exit_reason =
manual_reset_joseph_20260928` — Joseph's reset convention, the same prefix
as the 09-15 reset, so the daemon's 14-day cooling-off does **not** apply:
the new logic may pick any of these again on its own reading.

The whole 09-16 batch, for the record: 19 bought; 5 sold 09-25 at a profit
(+$384.69); 14 sold 09-28 at a loss (−$1,835.58); net −$1,450.89 over
8–12 days while SPY rose about 1.4 %. They were bought from the 1,389-name
pool (cap filter) and the six STABLE names among them were held on
week-old readings. They are evidence about neither the kernel nor the
fresh logic.

Not sold: CWAN, HTBK — the broker reports both assets inactive and refuses
orders; the 90-day wall date is 2026-10-12 but it cannot sell them either.
Only a paper-account reset removes them.

## Fresh-logic baseline — 2026-09-28 12:33 ET

```
equity            $96,512.07
cash              $66,931.76
open              13  =  11 fresh-logic  +  CWAN, HTBK (unsellable, $3,357 at cost)
fresh cohort      09-24: AVO BFST CFFI DOC FBRT IVZ OCFC PRKS SIND
                  09-28: EMBJ FNRN
unrealized        -$317
SPY               764.68
```

What "fresh logic" is, exactly — everything live in `tfe-web-task:637`:

```
pool       avg dollar volume >= $2M/day (MINE) · stocks only (JOE)     ~3,750 names
gate       V3 basin Accumulate, basin >= 0.15, break < 0.20 · B_k > -0.50 (ENTRY-R10)
readings   every name through the kernel every night (full_universe)
exits      7-day no-loss-sale hold (EXIT-R9) · dead clock on true sessions ·
           -20 % brake · 90-day wall · profit protection
```

## Grading bar — unchanged, restated on the clean book

```
GRADE AT     20 closures of positions opened 2026-09-24 or later
FAILS IF     win rate at or below 57.4 %  ->  ENTRY-R10 comes out, not re-baselined
LIFT         account return from $96,512.07 minus SPY's return from 764.68,
             same dates (the spec's definition; not mean trade excess)
NOT COUNTED  the two manual sells above, the 09-15 reset, CWAN, HTBK
```

The page's "Ledger Strategy Win Rate" (35.9 %, 14W/25L before today) counts
every ledger closure including the resets; after today it will read lower.
It is not the fresh cohort's number. The fresh cohort has zero closures.
