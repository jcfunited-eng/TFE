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
