# CH2 — the kernel on the whole bar: what the numbers look like

Joe, 2026-09-30, in order: "Something is wrong — the kernel never does that"
(the production L2 subtracts the mean over all gates) · "there should be
Date Open High Low Close Volume" · "no wonder it is flat" · "run what-if
scenarios at your pleasure" · "the remaining pieces are the L5 governance
layer and filters for zombies, pump and dumps, too few bars, and other non
tradeable — so start there and see what the numbers start looking like."

## What was wrong (three things, all in production `uf_core`)
1. The field was one number a day (the close). The canon writes norms
   (‖dF‖, ‖F − F̄‖², ‖F(t+1) − 2F(t) + F(t−1)‖): the field is the bar.
2. `layer0.py:132` replaces F by log(F + 1e-8). Not in the canon. It is why
   a $40 stock got three boundaries a year and the tuple sat still for
   months (the flat lines on the page).
3. `layer2.py:47-50,177` takes the L2 contrast against the mean TVR of all
   gates in the history. The canon uses the gate's own mean. Every downstream
   value inherited that average. The literal file in the repo
   (`standalone_truth_kernel.py`) uses the gate's own mean but stubs L2.

## The kernel used from here: `tools/canon_kernel_causal.py`
L0/L1 from the literal file on the 5-vector (O, H, L, C, V); L2 with the
gate's own mean and the canon formulas as `uf_core/layer2.py` has them;
L3/L4 from `uf_core` unchanged. r(t) = 1. No log, no scaling, no
history-wide mean. One causal pass with running maxima, verified exact
(0.0 difference on every field) against re-running the chain day by day.
The reading on day t describes bar t−1 with everything known at close t.

## Data: `tools/fetch_ohlcv_pool.py` → `artifacts/ch2_life/ohlcv_pool.parquet`
The live CH2 entry pool (stock, price × avg volume ≥ $2M) with ≥ 1,000
bars: 2,887 names, 6,856,095 adjusted daily bars 2016-01-04 → 2026-09-29.

## Three constants are in field units
`tau_D = 0.20`, the lattice steps `(1, 2, 4)`, the negative-space floors
`1e-6`. On dollars and shares volume makes every bar a boundary, `V_k` is
far past the lattice steps so `C_k = 3` always, `B_k` drains to −1 and
stays, `IAS = 0`, regime `VOLATILE` on 99.7% of days. Four of the seven
DSF fields are constants on the pool. The unit the constants were written
for is not in the repository; it is Joe's to state. (This is the Smooth
Glass conundrum in concrete form.)

## Censuses — `tools/ch2_canon_census.py` (declared; results in artifacts/ch4_uf/ch2_canon_census_*.json)
Reading on every day since 2021, 20-session outcome, halves < 2024 / ≥ 2024.

```
field / tau_D                 stock-days   up20 all     D=-1  D=0  D=+1     largest single-field spread (quintiles)
O,H,L,C,V / 0.20 (canon)      4,099,221    49.2 / 52.1  49.6 47.6 49.5      w_k 46.9 → 50.6 (seen) ; 50.8 → 52.5 (confirm)
O,H,L,C,V / own 3.77× (MINE)    689,290    49.1 / 51.5  48.7 49.1 49.4      psi_k 46.8 → 50.1
O,H,L,C / 0.20                4,051,257    49.2 / 52.1  49.4 46.9 49.5      psi_k 46.4 → 50.5 ; 49.9 → 53.7
O,H,L,C / own                   293,003    47.4 / 50.9  47.0 45.2 48.1      S_k 47.8 → 52.0
C,V / own                       689,456    49.1 / 51.5  48.7 49.1 49.4      (= the bar; volume dominates the norms)
```
Every field's values before a RISE (+8 % in 20) and before a FALL (−8 %),
pooled: the same to the third decimal. `D_k` carries nothing in any run.

SPY (Joe's screenshot object), raw bar, 2,699 readings: 20-day up share by
`w_k` quintile 61.5 → 64.4 → 67.3 → 76.1 → 74.1 (base 68.8). On the index
the busy-day lean is 13 points; on single stocks 3–4.

## Filters — MINE, causal, in `ch2_canon_census.py::tradeable_flags`
```
too few bars     < 252 bars of history                      2.6 % of stock-days out
non-tradeable    close < $5 ; 20-day median $ volume < $2M ;  8.5 % ; 14.3 %
                 > 3 zero-volume days in 60                   0.0 %
pump and dump    doubled within 20 sessions, or a |move| > 30 % in 60,
                 or volume > 8× its 60-day median with |move| > 15 %,
                 blocked 60 sessions after                    7.4 %
zombie           60-day (high − low)/close < 5 %              0.6 %
kept                                                          75.6 % (3,100,558 stock-days)
```
Filtered pool: up20 50.2 / 52.4; by `R_k` quintile 48.1 → 52.4 / 51.4 → 53.4;
by `w_k` 48.0 → 52.3 / 51.4 → 53.1; `D_k` −1/0/+1 50.6 48.8 50.4 / 52.4 51.7 52.8.

## L5 governance — `tools/ch2_l5_governance_test.py` (declared before running)
Three resolutions (tau_D 0.20; 3.77× and 8× the ticker's trailing median
D), ACTIVE = `R_k` ≥ the 80th percentile of that resolution's seen-half
readings (0.2387 / 0.3420 / 0.4480, fixed, applied unchanged to the confirm
half), quorum Q of 3, persistence P days, tradeable only, enter at close,
hold 20, one position per name. Pass bar: ≥ +3 points over the null in
both halves, n ≥ 2,000 each.

```
arm          seen: trades   WR     lift   mean20    confirm: trades  WR     lift   mean20
null           1,544,495   50.21%   —     +0.38%    1,507,798      52.44%   —     +1.14%
Q≥1 P≥1          43,172    51.01%  +0.80  +0.53%      39,275       53.44%  +1.00  +1.35%
Q≥2 P≥1          16,979    51.97%  +1.76  +0.64%      13,980       54.06%  +1.62  +1.52%
Q≥2 P≥3          12,810    51.71%  +1.50  +0.68%      10,527       53.79%  +1.35  +1.29%
Q≥2 P≥5          11,356    51.68%  +1.47  +0.65%       9,394       53.76%  +1.32  +1.32%
Q≥3 P≥3           2,475    52.48%  +2.27  +0.90%       2,137       52.50%  +0.06  +1.13%
Q≥3 P≥5           2,018    53.02%  +2.81  +0.89%       1,778       53.43%  +0.99  +1.34%
```
**No arm passes.** The quorum of two resolutions is the one consistent
lift: +1.8 / +1.6 points and +0.26 / +0.38 % per trade over the null, in
both halves. Persistence adds nothing. Three-of-three is thin and flips.

## Not done
Production unchanged (it still runs the log/global-mean kernel on closes).
No re-tuning after results. Units of the kernel's constants: Joe's call.
Page with the readings: https://claude.ai/artifact/Hp3rBbpbabMKF3exVsZ39F
