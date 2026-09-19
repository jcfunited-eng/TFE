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

---

## Result (2026-09-19)

10,612 gate signals survived the floors across 1,065 tickers; every one is a
position. Port check inside the run: 2,000 tuples, 0 decision mismatches.

Mean return per position, gate against the 95th percentile of 200
random-entry seeds:

| hold | gate (all) | null p95 | gate H1 | null H1 p95 | gate H2 | null H2 p95 | win rate |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 | +0.33 % | +0.20 % | +0.03 % | +0.18 % | +0.45 % | +0.28 % | 51.7 % |
| 10 | +0.63 % | +0.36 % | +0.15 % | +0.28 % | +0.83 % | +0.51 % | 52.0 % |
| 20 | +1.09 % | +0.64 % | +0.24 % | +0.41 % | +1.44 % | +0.97 % | 53.4 % |
| 30 | +1.70 % | +1.01 % | +0.50 % | +0.63 % | +2.21 % | +1.55 % | 54.7 % |
| 60 | +2.51 % | +1.77 % | +0.57 % | +0.72 % | +3.79 % | +3.07 % | 54.5 % |

(H1: 3,070 positions, 2021-09 → 2024-03. H2: 4,656–7,442 positions,
2024-03 → 2026-09.)

### Verdict against the declared bar: **the gate did not beat chance**

Five holds of five beat the null over the whole window, and five of five beat
it in the second half. **Zero of five beat it in the first half** — the gate's
mean is positive there at every hold but stays inside the random draw's
spread. The bar required both halves. It is not met, and it is not
reinterpreted after the fact.

### What the numbers say, stated exactly

1. Over the whole window the gate's edge is consistent and ordered: it beats
   the null at every hold, and both the edge and the gap over the null grow
   with holding length (+0.13 points at 5 sessions, +0.74 at 60).
2. That edge is **concentrated in the second half**. In the first half — which
   contains the 2022 decline — the gate picked better than the average random
   draw at four of five holds but never beyond its noise.
3. Win rate rises with hold length (51.7 % → 54.7 %), the shape of a small
   positive edge rather than a lottery.

### Read together with the two earlier measurements

- Held blindly for 30 sessions with no exits at all: **+1.70 %** per position.
- The same 30-session cap with today's exit law layered on: **+1.00 %**.
- Today's law alone, holding 48 sessions on average: **−0.44 %**.

On this population the entry gate produces a positive expectancy that the
current exit law converts into a negative one. The damage is in the exits, not
in the picks — the opposite of where the reading pass was pointed.

### Limits

Closes only; no costs (they cancel between gate and null, but not against the
live channel's slippage). One price stream: the independent-rung replication
honest-timing rule 6 requires is still owed and would be the first thing to
break a positive claim. Five years, one regime split. The epoch-pressure block
and the capitalisation rule are absent; liquidity and price floors stand in.

### What would drain it

Two things, each its own declaration. First, replicate on an independent
stream (hourly or m15 lanes) — a gate edge that does not survive a second rung
is an implementation artefact. Second, measure the exits directly against
holding blind: if the law subtracts 2.1 points per position at 30 sessions,
which rule does the subtracting, and does removing it survive its own null?
Neither is started, and nothing about CH2 changes on this result alone.
