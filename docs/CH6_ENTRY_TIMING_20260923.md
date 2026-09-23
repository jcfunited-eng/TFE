# CH6 — the door is not the problem; the fill is

Joe, 2026-09-23: *"Can you fix this — the door lets in too many stocks
that never fall."* Measured before touching anything. Nothing changed.

## What was already tried on the door (filed, all buried)

| study | verdict |
|---|---|
| shape doors, eight tunings (`ch6_tight_vs_loose`) | all lose $6–15 per $2,500, both halves |
| species-law DOWN finder vs UP-mirror control (`ch6_species_down_finder`) | no beat: derive −$4.38 vs −$3.19; confirm −$5.12 vs **+$13.40** for the control |
| extinction-presence law (`ch6_extinction_presence_law`) | halves disagree (refused class better in derive, worse in confirm); not in force |
| mechanism-family readings | graded at zero |
| first-close cut (`ch6_day1_cut_test`, today) | loses to the shipped ladder; buried |

## The receipt

The live door (≥ 8 % day, ≥ 3× volume, ≥ $5, herd band 0) decides at
the close and fills at the first mark of the next session, and only at
or below the decided close (Joseph 2026-08-20 *"decide tonight, purchase
tomorrow"*; 2026-08-21 *"a stock on the rise is never entered"*).

Live book, 122 closed shorts with a prior close on file:

```
filled BELOW the spike-day close        111 of 122   (91 %)
filled at/above                          11 of 122
fill vs decided close, percent:
   worst -9.19 | 10th pct -2.44 | quarter -1.49 | median -0.72 | mean -1.06 | best 0.00
fills 2 % or more below the decided close  15   (the whole bank target gone before entry)

summed short return, actual                        +15.9 %
summed short return if short AT the decided close  +146.8 %   (same exit prices)
in dollars, ~$2,500 slices                    -$534  vs  +$2,790
wins                                          76/122 vs   89/122
```

The stocks fall. They fall overnight, in the gap between the close that
qualified them and the mark the engine is allowed to sell at. The fill
rule then puts the book short *after* an average 1.06 % of the fall is
gone, against a 2 % bank target. The "never fall" names are mostly names
that fell overnight and then bounced.

This agrees with the filed decade study (`ch6_fast_cash_laws`, 2026-08-19),
which shorted the CURRENT door **at the completed close**:

```
                            derive ≤2023 (n 6,007)   CONFIRM 2024+ (n 7,991)
bank at 2 %, per trade         +1.22 %  (74 % W)        +1.56 %  (74 % W)
on a $2,500 slice              ≈ +$31                   ≈ +$39
```

versus the live book at −$4 per trade. The difference between +$39 and
−$4 is the overnight gap. Same door, same exits, different entry instant.

## What would fix it (NOT done — it changes Joe's law)

Be short at the spike-day close instead of the next morning:

```
decision      ~15:45 ET, on the intraday price and volume so far
              (≥ 8 % on the day, ≥ 3× the trailing-20 mean, ≥ $5, herd band 0)
fill          at the closing print (market-on-close); in the paper book,
              the 19:55 UTC sweep can stage and fill at the close mark exactly
exits         unchanged: 2 % sweep, 5 % arm / 1-point trail, −20 % stop,
              5-session clock, quiet-cut, Joseph's sound-structure cut
```

What this touches that is Joe's, not mine:
- *"decide tonight, purchase tomorrow"* (2026-08-20) — becomes decide at
  15:45, purchase at the close.
- *"a stock on the rise is never entered"* (2026-08-21) — on the spike day
  the stock is, by definition, up. The rule was written against chasing a
  stock higher the next morning; at-close entry is a different instant.

What is knowable at 15:45 that is not identical to the close: the day's
gain and volume are read fifteen minutes early, so a few events near the
8 % / 3× lines will differ from the close-based set. Slippage on a
market-on-close print is not modelled; paper book, no real orders.

Expected, from the filed study: roughly +$30–40 per trade at the same
74 % bank rate, instead of break-even. Grade: 20 fills at the new
instant, declared before the first one; control = the same events'
next-morning marks, logged alongside.

## SHIPPED 2026-09-23 — Joe's word

> "we do find the falls — it's a timing issue — that we could correct and
> see if it works — and the rules you talk about are to help with trade
> and timing so if one of them blocks a sound strategy we don't have to
> enforce it."

```
tools/ch6_fast_harvest.py
   ENTRY_AT_CLOSE = True
   close_entry_door(px, vol_today, prev_close, vol_mean20)   pure; tests/test_ch6_close_entry_door.py 9/9
   _market_snapshot()      one Massive full-market call: price now, volume so far, prior close
   _gate_and_rank(events)  the entry reading + cherry-pick ranking, shared with the nightly hunt
   hunt_at_close()         decide on the day so far, fill at the mark, once per session
   hunt()                  settles as before; stages NOTHING for the next morning
   evaluate_live_marks()   poll records control_next_morning on every at-close position
   close_position()        closed record carries entry_mode + control_next_morning
   commands                close_entry, close_entry_dry
tools/ch6_loop.sh
   19:45-19:54 UTC weekdays: python tools/ch6_fast_harvest.py close_entry
   (before the 19:55 sweep; one stamp per session; a refused pass retries once)
```

What is unchanged: the door's three conditions, herd band 0, unreset
refutations, the entry reading, the cherry-pick cap, sizing ($2,500 /
1 % of a normal day / floor), every exit, the sound-structure cut, the
protective halt file.

What the at-close read does differently, stated:
- gain and volume are read fifteen minutes before the close, so volume
  is ~85–90 % of the day's; the 3× test is slightly stricter than at the
  completed close. Prior close comes from the feed (yesterday's actual
  close), not the store.
- the universe is the store's symbols with 20 completed closes in the
  last 21 sessions (5,029 on 2026-09-23).
- the store must be within 5 sessions of today or the day is refused
  loudly (MINE). Loop hours are fixed UTC and assume EDT, as before.
- dry run 2026-09-23 ~14:10 ET: door 0 (seven names up 8 %+, none on
  3× volume yet) — a quiet day, the chain runs end to end.

GRADE, declared before the first fill: **20 closed at-close entries.**
FAILS if average P&L per closed trade ≤ $0 or fewer than 60 % bank →
`ENTRY_AT_CLOSE = False`, next-morning staging returns, nothing
re-tuned. CONTROL: `control_next_morning` on every position — the next
session's first mark, its gap to the close entry, and whether the old
rule would have filled there.

## Not touched

The watchdog shipped earlier today stands. CH6 remains a paper book;
no real orders.
