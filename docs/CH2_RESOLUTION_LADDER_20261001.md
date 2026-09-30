# CH2 — the standing label, the resolution ladder, and the event-direction test

Joe, 2026-09-30: *"You don't see nearly the same 30 every day as a
problem?"* — then *"Do whatever."* Two declared measurements, both filed
whichever way they fell. Production kernel unmodified throughout.

## 1. The standing label (measured on `runtime_decisions_history`, 181 runs since June)

```
today's 30 basin passers vs   1 run ago 30 same · 5 runs ago 29 · 10 runs 28 · 20 runs (Aug 16) 26
rated "buy" every night since 07-09 (101 consecutive runs):
   AROW BAM BDX BFST DEI DOC HTH LINE MSBI OCFC SNY VALE VRTS
gates per stock at tau_D = 0.20: 4–5 in 1,373 bars (5.5 years)
```

CH2 does not pick a moment. The buy date is set by when cash is free.

## 2. Resolution ladder — `tools/ch2_resolution_ladder.py` (declared before running)

Production adapter on daily closes; only `tau_D` varied, per arm, in the
offline process. 142 operating companies (every 20th with ≥ 1,000
closes; survivorship not handled). EVENT = enter at close t+1 when a gate
forms at t and the live gate passes; LABEL = every 10th session on the
standing reading. 20-session hold, halves ≤ 2023 / 2024+.

```
tau_D    events/stock-year (median)   buys the live gate produced (142 cos, 5.7 y)
0.20     2.5   (87 of 142 under 4/yr)  76 — 67 of them ONE stock (BRO)
                                        LABEL: derive WR 51.4 % ret20 +0.0 %  ·  confirm WR 53.8 % +1.3 %
0.10     21                              2
0.05     87                              0
0.02     196                             0
```

**The V3 basin says "buy" only when the kernel has seen almost nothing.**
Its support inputs are the adapter's lifetime means over gates
(`S_UF = ½(1 − share of gates with D≠0) + ½(1 − share with a reversal)`,
`R_UF` = mean resonance), which are high only for a history with few
events. Give the kernel more events and the basin never says buy again.
"Accumulate" ≈ "quiet history". That is why the list is static, why the
re-bought names came straight back, and why the live record is a coin
flip. **The sensitivity dial cannot be turned with this gate in place.**

## 3. Event direction — `tools/ch2_event_direction.py` (declared before running)

The kernel's own latest-tuple `D_k` (+1 / 0 / −1) at a fresh gate boundary
(knowable at t+1), no averages, no basin; enter at close t+1; 20-session
return; null = coin flip. Same 142 companies. Pass bar: at an arm with
≥ 4 events/yr, `D_k = +1` wins > 50 % in both halves (n ≥ 200) and beats
`D_k = −1` in mean return in both halves.

```
tau_D 0.20   EVENT  derive  up n=1001 WR 42.2 % ret20 −2.5 %   down n=1302 WR 36.6 % −5.5 %   all 38.9 %
                    confirm up n= 844 WR 46.3 %       +0.8 %   down n=1251 WR 43.7 % +0.5 %   all 45.2 %
tau_D 0.10   EVENT  derive  up n=3729 WR 46.6 %       −0.6 %   down n=8449 WR 42.2 % −2.1 %   all 43.5 %
                    confirm up n=2802 WR 50.1 %       +0.8 %   down n=6498 WR 48.2 % +1.5 %   all 48.7 %
tau_D 0.05   EVENT  derive  up n=6973 WR 49.2 %       −0.2 %   down n=29713 WR 46.2 % −0.9 %  all 46.8 %
                    confirm up n=5399 WR 51.3 %       +0.9 %   down n=22973 WR 50.4 % +1.4 %  all 50.5 %
the standing label, same companies, all arms:   derive WR 48.2 % ret20 −0.2 %  ·  confirm WR 51.8 % +1.1 %
```

**Fails at every arm.** Buying when the kernel registers an event and
says "up" wins less than half the time in the first half at all three
settings, and does *worse* than the standing label at all three. The
up-minus-down spread is small and flips sign between halves at 0.10 and
0.05. At daily resolution, one stock's kernel direction at its own event
does not say what the next 20 sessions do.

## What this leaves

- CH2 as deployed selects quiet histories and its record is a coin flip
  plus market drift. The fresh-logic grade (20 closures) is the honest
  measurement of exactly that, and should be expected to land near it.
- Turning the kernel's sensitivity up is not a fix: the gate on top
  stops buying, and the raw direction is null.
- The only construction in this repository with a positive decade record
  is population-level — the species law and herd conditioning
  (`artifacts/ch4_uf/ch4_kgate_herd_K3.json`: 7–8 of 10 years positive,
  $48–60k per decade on $100k a year) — relations between stocks, not a
  per-stock scalar. CH2 has never used it. That is a different CH2, and
  it is Joe's call, not a patch.

## Not done

No change to production. No rule bolted onto the gate. No re-tuning of
either measurement after seeing results.
