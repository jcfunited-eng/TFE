# CH2 — profit-take on Joseph's order, 2026-09-25

Joseph, 11:16 ET: *"in ch2 sell anything that is before 9/24 that is at a
profit."* His order; executed as given.

## Rule applied

Ledger rows with `signal_class='CH2'`, `status='filled'`,
`created_at < 2026-09-24`, and a positive unrealized P&L at the broker at
run time. 21 rows qualified on date; 5 were in profit. Dry run first
(list only), then live. Script: `ch2_take_profits.js` (session
scratchpad), run as `node` inside the serving container — sells at
market, then closes the ledger row exactly as `sentinel_monitor.ledgerClose`
does, then sets `kill_cooldown_<ticker>` exactly as `markRecentlyKilled`
does. `exit_reason = manual_profit_take_joseph_20260925` — it does not
start with `manual_reset`, so the daemon's 14-day re-entry cooling-off
applies to these five (MINE; stated so Joseph can override).

## Sold (all filled 11:20–11:21 ET, market orders)

```
AZZ   18 sh   134.39 -> 136.92    +$45.54    +1.88 %   (opened 09-17)
HDB  108 sh    22.69 ->  22.95    +$28.08    +1.15 %   (opened 09-16)
MTD    1 sh  1357.57 -> 1506.57  +$149.00   +10.98 %   (opened 09-16)
RAL   36 sh    67.83 ->  69.55    +$61.92    +2.54 %   (opened 09-16)
RBC    5 sh   484.18 -> 504.21   +$100.15    +4.14 %   (opened 09-16)
                                 +$384.69 realized
```

## Not sold, and why

```
14 pre-09-24 positions under water (AEBI -7.0 % … HTH -0.8 %)   not at a profit
HTBK   0.00 %                                                    not at a profit
CWAN   +0.9 % but exit_blocked: broker reports the asset inactive
       and refuses orders (same since the 09-15 reset)
9 bought 09-24                                                    outside the order
```

## Account after

```
equity $96,978   cash $39,490   open 25   unrealized -$1,686
```

## Also on the record today

The deploy of the 09-24 fixes (full nightly refresh, dead clock on true
sessions, advisory screener check) **did not run** on 09-24: the queued
job was killed when that session ended before 20:05 UTC. Production is
still `tfe-web-task:636`. Last night's refresh therefore ran the old
targeted mode. Re-queued for 20:05 UTC today, guarded on HEAD carrying
both fixes.
