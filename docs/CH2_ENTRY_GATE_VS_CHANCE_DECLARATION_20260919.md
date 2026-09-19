# Does the CH2 entry gate beat chance? — measurement declaration (2026-09-19)

Declared BEFORE any result is computed. Provenance: Joseph's order, after the
holding-length measurement showed the gain came from holding less time rather
than from the gate's choices, and asked the question directly.

## The question

**On tradable names, do stocks the V3 basin entry gate selects outperform
randomly chosen entries in the same stocks over the same window, held the same
length?**

This is an entry-quality question, so every adaptive exit is removed. A
position is opened and held a fixed number of sessions — nothing else. What
remains is the gate's choice and nothing but the gate's choice.

## Population

- Lanes: the production kernel tuple per ticker per session, 2021-09-01 →
  2026-09-19, as exported for the two prior measurements.
- Gate: `computeV3Basin` (verified port) with `decision_argmax ==
  "Accumulate"`, `accumulate_basin >= 0.15`, `break_agreement < 0.20`,
  `bar_count > 20` — the live door's rule.
- Floors, as declared in the holding-length measurement and unchanged: median
  dollar volume over the prior 20 sessions ≥ $5,000,000 and entry close ≥
  $5.00, standing in for the $500 M capitalisation rule that has no history.
- **Every** surviving signal is a position. Signals are not de-overlapped:
  this measures the gate's picks, not a tradable book, and the null carries
  the same overlap by construction.

## Holds (declared once, no sweeps)

5, 10, 20, 30 and 60 sessions. Entry fills at the close of the session after
the signal; the position closes at the close N sessions later.

## Null

Random entries: the same tickers, the same number of positions per ticker,
entry sessions drawn uniformly from that ticker's sessions inside the same
window that also pass both floors, held the same N. **200 seeds.**

## How it is judged

Per-position **mean** return, not a sum — a sum rewards whichever run happens
to hold more positions. Reported with the null's distribution across seeds.
Win rate and median are reported beside it.

## The verdict bar (declared before results)

The gate **beats chance** only if its mean per-position return exceeds the
95th percentile of the null's seed distribution at a majority of the five
holds, **and** does so in both halves of the window (split 2024-03-15).
Anything less is reported as: the gate did not beat chance on this test.

## Costs

Not modeled, and they cancel: gate and null carry identical position counts
and identical holding lengths, so any per-trade cost subtracts equally from
both.

## Known limits, stated before the result

Closes only. One price stream — the independent-rung replication that
honest-timing rule 6 asks for is not available in this export, so a positive
result here would still owe a second stream. Five years, one market regime
split in two. The epoch-pressure block and the capitalisation rule are absent.

## Output

`artifacts/ch4_uf/ch2_entry_gate_vs_chance_20260919.json` plus a result
section here, committed. A negative answer is filed exactly as a positive one
would be.
