# Which CH2 exit rule subtracts? — measurement declaration (2026-09-19)

Declared BEFORE any result is computed. Provenance: Joseph's word to continue,
after the entry-gate measurement showed the gate's blind-hold expectancy
(+1.70 % per position at 30 sessions) becoming −0.44 % under the live exit law.

## The question

**Rule by rule, what does each seller in the current law cost or earn against
simply holding to the horizon?**

## Population, timing, prices

Identical to the entry-gate measurement and unchanged: the live gate on the
production kernel lanes 2021-09-01 → 2026-09-19, liquidity floor $5 M median
dollar volume over 20 sessions, price floor $5.00, every surviving signal a
position, fills at the close after the signal, closes only, no costs.

## Baseline

**Hold blind to the horizon.** Horizons declared once: **30 and 60 sessions.**
No exits at all. This is the number every rule is measured against.

## Runs

At each horizon, the baseline plus exactly one rule, then the whole law:

- **brake** — a close at or below entry × 0.80.
- **dead_clock** — more than 16 closed sessions at or below entry × 0.95 with
  no close back above that line.
- **ratchet** — after a peak close ≥ entry × 1.20, a close at or below
  entry + (peak − entry) × 2/3.
- **wall** — 90 calendar days (reported even where it rarely binds).
- **full_law** — all four together, as production runs them.

## The sharp number

For each rule, besides the run mean, the **fired set**: the positions where
that rule ended the trade, comparing what the rule realised with what those
same positions would have made held to the horizon. That difference, summed
and per position, is what the rule cost or saved. A rule can lower the average
and still be worth keeping if it cuts a tail; the fired-set distribution is
reported so that is visible rather than assumed.

## Null

For each rule, an exit-timing null: the same number of positions, drawn at
random from those the rule did **not** fire on, exited after the rule's own
median firing session. If a rule's cost matches arbitrary exits of the same
timing and count, the rule is not the cause — the exiting is. 200 seeds.

## Replication

Both halves of the window, split 2024-03-15, for every run.

## What this measurement may conclude

It reports costs. It ships nothing and changes nothing in CH2. Any rule change
would need its own declaration, its own null, and Joseph's word.

## Output

`artifacts/ch4_uf/ch2_exit_rule_cost_20260919.json` plus a result section
here, committed. A result that vindicates the current law is filed exactly as
one that condemns it.
