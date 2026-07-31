# CH4/CH3 Live-Timing Audit — 2026-07-31

Standing doctrine: no bench victories. Every number below is causal,
declared before measurement, misses included. This audit was triggered
by porting the CH3 shadow hunter into a decade replay and asking, at
every step, "at which bar close is this fact actually knowable?"

## The central finding (the reveal-bar theorem)

The v2 gate boundary at bar t requires bar t's data
(`D(t)=‖SEV(t)−SEV(t−1)‖`; `boundary(t) ⟺ D(t)² > mean(D²) ∨ N-flip`).
A gate ending at bar `tb−1` is therefore first KNOWN at the close of
bar `tb` (the reveal bar). Every previously filed harvest number used
entry/exit at `closes[tb−1]` — one bar of hindsight at both ends of
every trade.

Under live-true timing (fills at reveal closes, species records strictly
as-of-issue via a two-stream ledger):

1. **The species law survives, at every rung.** Bigram band ≥ 0.75
   causal predictions of the next gate's displacement sign:
   - daily (12k-universe ext store): 60.0–69.4 % every year 2016–2026
   - hourly (5,016 symbols, full-depth store): 60.7–67.3 % every year
   - 15-min (60-name watchlist store): 57.9–64.8 % (mature years)
   Structural perception is real, rung-invariant, and live-reproducible.

2. **Every money construction dies.** Fresh $100k/yr, 10 % slices,
   max-10, both polarities, live-true fills:
   - per-gate step: WR collapses 62 % → ~48 %, mean/trade ≈ 0 at all
     three rungs (hourly book −34 %…+24 %/yr noise; daily −25 %…+35 %)
   - cycle read (exit on first opposing majority): noise at all rungs
   - morphology read (causal per-species median gates-to-peak): noise
     at all rungs (daily total +$21.8k/11 yr, 5/11 years positive)

3. **The proof of why.** Redefining the schema-memory completion object
   as the TRADABLE displacement (reveal close → reveal close) and
   rerunning the whole field: the consistency spectrum equals the
   binomial null at every rung — zero excess species. The predictable
   component of a gate's displacement lives ENTIRELY inside the reveal
   bar. What the law predicts, a close-of-bar actor can no longer buy.

## Status of previously filed numbers

The harvest-ladder book figures (next-gate +671 % 5y, cycle +208 %,
morphology +503–630 %/decade, BOTH-t75 +97–123 %) were measured at
`closes[tb−1]` and are unsound as money claims — they monetize the
reveal bar retroactively. The LAW figures (65.9 % daily etc.) stand;
today's strict re-measurement confirms and extends them to three rungs.
WRC91's live-forward result (predicted 91.6 vs realized 92.3 WR, but
only +2.2 % total money) was the early tell: sign-consistency survives
live timing; the dollars never did.

## Also falsified today (filed raw in artifacts/ch4_uf)

- The daily spring frame transposed intraday: every year negative at
  the hourly rung and at the native 15-min rung (ch3_m15_replay.json).
  Conditioning on decline+quiet+flip is ANTI-selective intraday.
- Hourly rung cannot even resolve same-session flare species (finds
  collapse to noise under a same-session yield record).
- A real defect in the live CH3 shadow hunter was found and fixed
  before its first sweep (8cefa573): the energy condition read the
  confirmation bounce instead of the stored decline.

## Open paths (physics-true, not band-mining)

1. **Act inside the reveal bar.** The structure rung and the sampling
   rung need not be equal: an hourly-gate boundary can be provisionally
   detected from 15-min partials up to 45 min before the hourly close.
   Capturing part of the reveal bar is the only place the proven edge
   physically exists. This is CH3-shaped work (its 15-min cadence).
2. **Different completion objects / terrain.** These alphabets carry no
   post-reveal structure; others (longer horizons, cross-symbol herd
   completions, magnitude-conditioned objects) remain unmeasured.

## Reproduction

`tools/ch3_hourly_law.py` (CH3_RUNG=daily|hour|m15, CH3_TRADE_DISP=1
for the null proof, sharded via CH3_OBS_SHARD/CH3_OBS_MERGE),
`tools/ch3_hourly_harvest.py`, `tools/ch3_cycle_harvest.py`
(CH3_MORPH=1), `tools/ch3_hourly_replay.py`, stores
`ch4_hourly_universe_full.parquet` (5,016 syms, 2016–2026-03, hourly),
`ch3_m15_watchlist.parquet` (60 syms, 2016–2026-07, 15-min). Results in
`artifacts/ch4_uf/ch3_*.json`.
