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

---

## Result (2026-09-19) — the exit rules are close to neutral, and my earlier reading was wrong

10,612 positions from the same gate and floors. Port check inside the run:
2,000 tuples, 0 decision mismatches.

**Horizon 30 sessions — blind hold +1.70 % per position**

| rule | run mean | delta vs blind | fired | median session | realised on fired | if held on fired | timing null | worse than arbitrary exit |
|---|---:|---:|---:|---:|---:|---:|---:|:--:|
| brake | +1.65 % | −0.05 | 583 | 18 | −22.33 % | −21.42 % | +1.59 % | no |
| dead clock | +1.67 % | −0.03 | 1,008 | 24 | −15.25 % | −14.93 % | +1.65 % | no |
| ratchet | +1.64 % | −0.06 | 253 | 23 | +15.33 % | +17.88 % | +1.63 % | no |
| wall | +1.70 % | +0.00 | 0 | — | — | — | +1.70 % | no |
| **full law** | **+1.59 %** | **−0.11** | 1,424 | 22 | −10.62 % | −9.80 % | +1.50 % | no |

**Horizon 60 sessions — blind hold +2.51 % per position**

| rule | run mean | delta vs blind | fired | median session | realised on fired | if held on fired | timing null | worse than arbitrary exit |
|---|---:|---:|---:|---:|---:|---:|---:|:--:|
| brake | +2.44 % | −0.06 | 1,171 | 31 | −22.27 % | −21.85 % | +2.08 % | no |
| dead clock | +2.42 % | −0.09 | 2,347 | 34 | −14.80 % | −14.52 % | +1.80 % | no |
| ratchet | +2.29 % | −0.22 | 1,043 | 41 | +16.25 % | +17.88 % | +2.18 % | no |
| wall | +2.52 % | +0.01 | 304 | 60 | −4.47 % | −4.67 % | +2.52 % | no |
| **full law** | **+2.16 %** | **−0.35** | 3,575 | 36 | −5.27 % | −4.51 % | +0.91 % | no |

### What this says

1. **No rule is a destroyer.** The whole law costs 0.11 points per position at
   a 30-session horizon and 0.35 at 60. The wall is free, the brake and the
   dead clock sell losers within a point of what holding them would have
   returned, and the ratchet gives up about 2.5 points on the winners it sells
   (+15.33 % against +17.88 % held) but touches few positions.
2. **None is worse than arbitrary exiting** at the same count and timing.
3. The dead clock does what it was built to do: it ends 1,008 positions
   averaging −15.25 %, at almost exactly what holding them would have paid.

### Correction to what I told Joseph

After the entry-gate measurement I said the exit law converts the gate's
positive expectancy into a negative one. **That was wrong, and this
measurement is the reason I know.** The −0.44 % figure came from the
holding-length run's control, which is a different population: a *book* that
holds one position per ticker at a time (1,588 positions). This run measures
every signal (10,197). On one population, with the exits isolated, they cost
almost nothing. The gap between +1.70 % and −0.44 % is therefore not the exit
rules — it is the difference between the signal population and the book that
takes one position per stock at a time, and possibly the longer holds that
book runs.

### What would drain it

Run the de-overlapped book — the live "one position per stock at a time" door
— against the all-signals population **at the same fixed horizons**. If the
gap survives at equal holding length, the cost is in the one-at-a-time rule
(live since 2026-09-02) and not in holding length; if it closes, the earlier
control's 48-session holds explain it. Declared and measured the same way,
before any claim. Nothing about CH2 changes on this result.
