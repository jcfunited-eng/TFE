# Does "one position per stock at a time" cost the book? — declaration (2026-09-19)

Declared BEFORE any result. Provenance: Joseph's word to continue, after the
exit-rule measurement showed the exits are near neutral and located the open
gap in the difference between the signal population and the live book.

## The question

The live door has taken **one position per stock at a time** since 2026-09-02.
At equal holding length, does that discipline change what the book earns, and
if so, is it because it takes *fewer* signals or because it takes the *first*
signal of each cluster?

## Population, timing, prices

Unchanged: the live gate on the production kernel lanes 2021-09-01 →
2026-09-19, liquidity floor $5 M median dollar volume over 20 sessions, price
floor $5.00, fills at the close after the signal, closes only, no costs. No
adaptive exits at all — every position is held a fixed number of sessions, so
nothing but the choice of entries differs between the runs.

## Horizons

**30 and 60 sessions**, declared once.

## The three runs

- **all_signals** — every surviving signal is a position (the population used
  in the entry-gate and exit-rule measurements).
- **first_of_cluster** — the live rule: take a signal only if no position in
  that stock is open; hold the horizon; the next eligible signal may then be
  taken. This is what production does.
- **random_of_cluster** — the same number of positions per stock as
  `first_of_cluster`, chosen at random among that stock's signals under the
  same no-overlap constraint. **200 seeds.**

The third run is the point of the measurement. If `first_of_cluster` matches
it, the live rule costs nothing beyond taking fewer positions. If
`first_of_cluster` falls below its spread, taking the *first* signal of a
cluster is specifically worse than taking any other one.

## How it is judged

Mean return per position, with win rate and median beside it, in both halves
(split 2024-03-15) as well as over the whole window. Counts are reported
because they differ by construction; the comparison is per position.

## What this may conclude

It reports. It ships nothing and changes nothing in CH2. A change to the live
door would need its own declaration, its own null, and Joseph's word.

## Output

`artifacts/ch4_uf/ch2_one_at_a_time_20260919.json` plus a result section here,
committed. Either answer is filed the same way.

---

## Result (2026-09-19) — the rule does not pick badly; discarding the repeats is what costs

1,065 tickers, 9,078 signals (fills falling on the same session deduplicated).
Port check inside the run: 2,000 tuples, 0 decision mismatches.

| horizon | all signals | live first-of-cluster | random within cluster (200 seeds) |
|---|---|---|---|
| 30 sessions | n 8,766, **+1.43 %** | n 1,844, **+1.11 %** | n ≈1,667, +1.07 % (p05 +0.88, p95 +1.30) |
| 60 sessions | n 7,013, **+2.02 %** | n 793, **−0.05 %** | n ≈695, −0.20 % (p05 −0.73, p95 +0.26) |

### What this says

1. **The live rule is not choosing the wrong signal.** At both horizons its
   result sits inside the spread of picking a different signal at random from
   the same cluster (+1.11 % against +1.07 % ±; −0.05 % against −0.20 % ±).
   Taking the *first* signal of a run is neither better nor worse than taking
   any other one.
2. **Discarding the repeats is what costs.** Every way of taking one position
   per cluster lands well below taking every signal, and the gap widens with
   the hold: 0.3 points at 30 sessions, **2.1 points at 60**. A stock that
   keeps signalling is where the gate's edge lives; a book that takes one
   position per stock and holds through the rest of the cluster throws that
   weighting away.
3. This is the mechanism behind the gap that prompted the measurement. It is
   an entry-side effect, not an exit-side one.

### What this does not establish

That the live book should take repeat positions. Three things stand between
this result and that change: the book's capital can hold roughly forty
positions at a time, so it cannot take 8,766 over five years; repeat-signal
weighting may be a trend artefact rather than an edge, which is exactly what
the first half of the entry-gate measurement could not confirm; and the
re-entry cooling-off exists because of a real custody failure (RAL, three buys
in three weeks). Any change would need its own declaration, a capacity-bounded
book simulation rather than a per-position mean, its own null, and Joseph's
word.

### The chain so far, in one place

- Gate picks beat chance over the window, all five holds, but not in the first
  half → `CH2_ENTRY_GATE_VS_CHANCE_DECLARATION_20260919.md`.
- The exit law costs 0.11–0.35 points per position; no rule is a destroyer →
  `CH2_EXIT_RULE_COST_DECLARATION_20260919.md`.
- No structural winner-side exit and no holding cap cleared its null →
  `CH2_WINNER_EXIT_MEASUREMENT_DECLARATION_20260919.md`,
  `CH2_HOLDING_LENGTH_MEASUREMENT_DECLARATION_20260919.md`.
- One position per stock at a time costs up to 2.1 points per position at
  longer holds, through discarded repeats rather than bad choice — here.
