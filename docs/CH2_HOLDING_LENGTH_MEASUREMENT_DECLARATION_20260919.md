# CH2 holding length — measurement declaration (2026-09-19)

Declared BEFORE any result is computed. Provenance: Joseph's order to drain
the failure filed in `CH2_WINNER_EXIT_MEASUREMENT_DECLARATION_20260919.md`,
where duration-matched random exits beat the current law in every case while
holding far less than its 47.8-session average.

## The question

**Does capping how long a CH2 position is held beat the current exit law, on a
population the live door could actually buy?**

## Population (fixed before measurement)

Same entry reconstruction as the winner-exit measurement — the live gate
(`computeV3Basin` port, verified) on the production kernel lanes,
2021-09-01 → 2026-09-19 — with two filters added, standing in for the
$500 M market-cap floor that has no historical series:

- **Liquidity floor**: median dollar volume (close × volume) over the 20
  sessions before the entry signal ≥ **$5,000,000**.
- **Price floor**: entry close ≥ **$5.00** (the live channel buys whole
  shares in ~$2,459 slices).

Both are declared once, here. They are proxies for tradable size, not the
capitalisation rule itself, and they are applied identically to the control,
every candidate and every null. The control is re-measured on this filtered
population; the earlier unfiltered control is not the comparison.

## Timing, prices, costs

Unchanged from the winner-exit declaration: decisions on a closed session,
fills at the next session's close, price stops at their trigger close, closes
only (no intraday range in the store), no costs or slippage modeled.

## Control

The current law, verbatim: dead clock (>16 closed sessions at or below entry
× 0.95 with no close back above), 90-day wall, −20 % brake, +20 % ratchet
floor, window end.

## Candidates (each measured alone)

A holding cap added to the control — the position closes at the next session's
close once it has been held N sessions, if nothing else has ended it first:

- **H10** — N = 10
- **H20** — N = 20
- **H30** — N = 30
- **H45** — N = 45 (an anchor beside the control's own average hold)

No other constants, no sweeps, no stacking with the structural candidates
already falsified.

## Null test

A duration null is meaningless for a rule that *is* a duration, so the null
here asks the other question: **is the advantage in CH2's entries, or in the
period itself?** For each candidate, 20 seeds of random-entry positions —
same tickers, same number of positions per ticker, entry sessions drawn at
random from that ticker's history, same holding cap, same control rules. A
candidate whose result is matched by random entries held the same length has
found nothing about CH2's picks.

## Replication

Both halves of the window (split 2024-03-15). A candidate must beat the
control in both.

## The bar to ship

A candidate ships only if it beats the control on total return over the whole
window **and** in both halves **and** exceeds the 95th percentile of its
random-entry null. Otherwise nothing ships, and the failure is filed with what
would drain it.

## Output

`artifacts/ch4_uf/ch2_holding_length_measurement_20260919.json` plus a result
section here, committed. Failures are filed exactly as wins are.

---

## Result (2026-09-19) — nothing ships, and the finding is about the entries

Run: `tools/ch2_holding_length_measure.py`. Port check inside the run: 2,000
tuples, 0 decision mismatches. 23,417 raw entry signals → 10,612 survive the
liquidity and price floors (12,075 dropped) → 1,588 control positions.

| run | n | total | mean | win | hold | first half | second half |
|---|---:|---:|---:|---:|---:|---:|---:|
| control (today's law) | 1,588 | −700.4 % | −0.44 % | 45.5 % | 48.0 | −409.2 % | −291.2 % |
| H10 | 3,004 | +570.6 % | +0.19 % | 49.7 % | 9.9 | −71.9 % | +642.5 % |
| H20 | 2,226 | +1,010.8 % | +0.45 % | 51.2 % | 19.4 | −84.3 % | +1,095.1 % |
| H30 | 1,908 | **+1,913.1 %** | +1.00 % | 56.0 % | 28.2 | −232.0 % | +2,145.1 % |
| H45 | 1,690 | +862.8 % | +0.51 % | 51.2 % | 39.9 | −397.7 % | +1,260.5 % |

Random-entry nulls, count-matched per ticker and drawn from the same window
(20 seeds): H10 mean +658.9 % (p95 +1,606.6), H20 +953.3 % (p95 +1,677.0),
H30 +1,085.8 % (p95 +1,918.0), H45 +774.0 % (p95 +1,418.9).

**Verdict against the declared bar: none ships.** Every cap beats the current
law by a wide margin and H30 beats it in both halves — but no cap clears the
95th percentile of random entries held the same length. H30 misses by 4.9
points of return (1,913.1 against 1,918.0); it is not rounded up.

### What this measured, stated exactly

1. The current law loses on this population in **both** halves (−409 %,
   −291 %; −0.44 % per position, 45.5 % wins, 48-session average hold).
2. Capping the hold is worth hundreds of points against it, consistently
   across all four caps.
3. Random entries in the same stocks, same window, same count, held the same
   length, do as well or better. **The gain is in holding less time, not in
   which stocks the V3 basin gate chose.** On this test the entry gate did not
   beat chance.

### Corrected before reporting

The first pass of this measurement drew null entries from the whole bar store
(2016 onward) and did not match position counts, producing nulls six times
larger than the candidates. Those numbers were never reported as a result;
the null was rebuilt to the same window with matched counts, and that is the
table above. Implementation sensitivity is exactly what honest-timing rule 6
warns about.

### Limits of this result

Closes only, no costs and no slippage modeled — and the caps trade roughly
twice as often as the control, so costs would bite them hardest. The
population uses a $5 M median dollar-volume and $5 price floor as proxies for
the $500 M capitalisation rule, and omits the epoch-pressure block. One
window, five years, one stream.

### What would drain it

The question this exposed is not an exit question. It is: **does the V3 basin
entry gate beat chance at all, on tradable names?** That deserves its own
declaration — CH2 entries against count-matched random entries at several
fixed holds, judged on per-position mean with an interval rather than a sum,
replicated on an independent stream (hourly or m15 lanes exist), with costs
modeled. Not started; not assumed. Until it is answered, no exit rule changes
on the strength of these numbers.
