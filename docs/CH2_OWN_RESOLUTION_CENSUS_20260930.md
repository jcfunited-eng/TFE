# CH2 — the tuples over time at each stock's own resolution, on the tradable pool

Joe, 2026-09-30: *"the resolution was daily — and there are the prefilters
for the Non tradables so it's not fair to make you look at them all — and
there is a 'resolution' consideration for D_k for tickers at market cap and
price points that alter what volatility looks like i.e. the Smooth Glass
conundrum."* Earlier the same day: *"there will be a pattern for when the
price goes up and the price goes down."*

All three corrections applied. Production untouched. Every number below is
the production chain's own output on daily closes; nothing was tuned after
seeing a result.

## 1. The Smooth Glass conundrum, measured

One fixed `tau_D = 0.20` on the 3,755-name tradable pool (HIS prefilters:
asset_type stock, price × avg volume ≥ $2M; pulled from production
2026-09-30, `artifacts/ch2_life/universe_tradable_20260930.csv`):

```
boundaries per year at tau_D = 0.20
  SNY 0.37   BRO 0.65   MTD 0.75   AAPL 0.84   PPG 0.93     smooth glass
  APLS 15.3  NCMI 13.9  TLYS 13.7  LAC 19.5   XPEV 21.6     storm
```

A 50× spread from one number. Market cap is present in the database for
39 of the 3,755 names, so size could not be read from it.

**HIS:** the resolution must be set per ticker by its size and price.
**MINE (the setting):** `tau_D(ticker) = 3.77 × median daily deviation
D(t) = |ΔF| + σ + κ` of that ticker. 3.77 is what puts MTD at 0.10, the
resolution its phases were first read at. Result: SNY 7.9 boundaries/yr,
MTD 7, HRB 11.6, LAC 8.2 — comparable. `tools/ch2_tuples_over_time.py`
prints any life at its own resolution.

## 2. What the kernel can and cannot carry (read from the code)

`uf_core/layer0.py`: the boundary operator uses `|ΔF|`, `σ`, `κ` (all
unsigned). `uf_core/layer1.py`: `V_k = Σ(|ΔF| + σ + κ)`; the one signed
value, the gate mean of `ΔF`, enters only as `‖μ_k − μ_{k−1}‖` (a norm) in
`U_k`. `layer2`–`layer4`: `w, ψ, S, U, C, R, D_k, M_k, B_k` are all built
from those. **No sign of price reaches any tuple field.** `D_k` is the
direction of resonance, not of price. LAC's two large falls (−32 %, −54 %)
carry `D_k = −1` and `D_k = +1`.

Also: `g_k = 0` is not damage. It is `Hyst_k = 1` (resonance moved more than
0.20 from the previous gate), i.e. the first gate after a shock. SNY k67
(+6.1 %) and HRB k115 (+6.9 %) are `g = 0` gates that rose.

## 3. Four lives read at their own resolution (MTD, HRB, SNY, LAC)

```
SHOCK   1-bar VOLATILE gate, w > 0.2: the jump day. Direction is in the price.
RIDE    the long gate after a shock carries the big move, both ways:
        LAC k48 −42 % (109 bars), k50 +21 % (114), k68 −32 % (130);
        HRB k104 −26 % (151), k117 +19 % (46); MTD +31 % (171).
TOP     a sharp rise in a short gate, or shocks stacked at a high, then a fall
        (LAC k47 +26 %/9 bars → −42 %; 17 shock days Sep 23–Oct 16 → −32 %, −54 %;
        HRB k103 +25 %/27 bars → −26 %).
BOTTOM  shocks at a low after a long fall, then a rise (SNY k65–66; HRB k107–108).
```

## 4. The count — `tools/ch2_gate_transition_census.py` (declared before running)

2,887 tradable names with ≥ 1,000 bars, own resolution, every gate the
chain draws (265,762 gates), on the trader's clock: a boundary at bar `i`
is knowable at close `i+1` (κ[i] uses close[i+1]); enter at close `i+1`,
exit at the close after the next boundary. Halves: gate start < 2024
(seen) / ≥ 2024 (confirm).

```
what came before the gate         seen: n      up   ride   | confirm: n     up   ride
all gates                             199,095  51.3%  +1.8%  |  66,667  51.2%  +2.6%
previous gate was a SHOCK              72,292  51.0%  +1.7%  |  19,816  54.1%  +3.8%
previous gate SHORT (≤20 bars)         74,456  53.1%  +2.2%  |  24,062  49.7%  +2.0%
previous gate MID (21–60)              29,789  50.3%  +1.7%  |  13,052  51.3%  +2.5%
previous gate LONG (>60)               22,558  47.5%  +1.0%  |   9,737  49.1%  +1.7%
jump into the gate UP >3% (any prev)   ~70k    50–54%         |  ~26k   46–53%
jump DOWN <−3%                         ~72k    47–56%         |  ~25k   50–55%
previous move SHARP_UP >15%            14,043  49.3%  +1.8%  |   6,192  51.7%  +2.6%
previous move SHARP_DOWN <−15%          9,572  48.5%  +1.7%  |   4,027  48.3%  +4.8%
2+ shocks in a row                     35,294  46–53%         |   5,823  45–57%
previous gate g = 0                    11,903  51.1%  +1.2%  |   5,465  52.2%  +3.5%
previous regime DEGENERATE              3,452  43.6%  −0.5%  |   1,441  48.2%  +2.2%
```

**Nothing that comes before a gate says which way price goes across it.**
Every context sits within a few points of the 51 % base in both halves;
the ones that look different in one half flip in the other. The TOP and
BOTTOM shapes seen in four lives do not exist across 2,887.

What does hold, in both halves, is **concurrent**: a gate's own finished
tuple and its own move —

```
gate length     seen: rose   big up   big down  | confirm: rose  big up  big down
2–5 bars         48.5%   1.5%    1.0%           |  48.8%   2.1%    1.4%
6–20             51.0%   7.6%    6.0%           |  52.3%   7.3%    5.7%
21–60            54.3%  14.6%   11.4%           |  52.2%  14.9%   11.4%
> 60             59.0%  28.3%   16.2%           |  60.8%  31.2%   16.5%
DEGENERATE (ψ high, median 216 bars)  62.7% rose, +10.4 % mean  |  60.4%, +11.3 %
```

Long undisturbed gates are the big moves and lean up 60/40; the gate after
a long gate is flat (47–49 %). That is the exhaustion shape — but a gate is
long only in hindsight.

## 5. The causal version — `tools/ch2_gate_age_census.py` (declared before running)

Day by day, 3,809,293 stock-days 2021→, causal per-ticker resolution
(`3.77 × trailing-252-bar median of D`, boundary known at `i+1`). Reading
on day `t`: the age of the current gate (days since the last known
boundary) and the price since its start. Outcomes: 20 sessions ahead, and
the ride to the close after the next boundary.

```
age of gate / price since start   seen: 20d up   ride up  | confirm: 20d up  ride up
1–5   DOWN / UP                    51.8% / 50.8%  50 / 46  |  54.3% / 52.2%   54 / 50
6–20  DOWN / UP                    48.9% / 48.3%  48 / 46  |  51.8% / 50.7%   51 / 51
21–60 DOWN / UP                    51.2% / 47.5%  49 / 46  |  52.0% / 53.7%   51 / 54
> 60  DOWN / UP                    51.7% / 51.1%  51 / 51  |  49.6% / 52.6%   50 / 53
all                                50.2%          49       |  52.2%           52
```

**Coin flip plus drift in every cell, both halves.** Being 60 days into an
undisturbed rising gate does not say the rise continues.

## What this leaves

- The three corrections were right and are now in the tools: daily bars,
  the live prefilters, one resolution per ticker.
- At that resolution, on that pool, the kernel's gate structure over time
  does not carry the sign of the next move. It cannot: no signed quantity
  reaches the tuple. The kernel sees how much and how long — never which
  way.
- A pattern "for when the price goes up and when it goes down" must
  therefore be read from the tuples **and** the price tape together, or
  from a signed quantity the kernel does not currently keep. Which of
  those is Joe's call.

## Not done

No change to production. No rule declared or tested beyond the two
counts. No re-tuning after results. Survivorship not handled (names in the
store today); costs not modelled; close-only.
