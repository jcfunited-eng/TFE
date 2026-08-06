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

## Addendum (same day): the reveal is TWO bars

`kappa(t) = |F(t+1) − 2F(t) + F(t−1)|` — the boundary flag at t is only
final once bar t+1 exists (the kernel's own finalization comment).
True knowability is therefore the close of bar t+2's open… i.e. one bar
later than even this audit's strict fills assumed. Every falsification
above is thus CONSERVATIVE (real capturable is smaller still); the law
is unaffected (completion signs do not depend on when they are
learned). Corollary for path 1: during the true reveal bar, all
quantities of the closing gate are final EXCEPT the single provisional
kappa/N term — the species prediction is computable BEFORE the boundary
confirms, and provisional detection from finer sub-bars is an O(1)
update per sub-bar.

## Addendum 2: early capture measured and closed

Provisional detection from 15-min partials is ~100% precise AND ~100%
complete at the FIRST 15-min close of the reveal bar (302,853/302,862
fires confirmed; 9 missed; ch3_early_reveal.json) — the boundary
decision is dominated by terms final at the gate close; the provisional
kappa/N term almost never flips it. The earliest honest fill therefore
exists 15 minutes into the reveal bar. Measured on the 60-name m15
store: the species spectrum on the early-capturable window (first
15-min close of reveal bar → same instant of the next gate) is at the
binomial null with marginal excess; the declared book is ±1%/yr noise
(ch3_early_capture.json). Conclusion: at these alphabets the payout
concentrates in the first 15 minutes of the reveal bar — ahead of any
honest fill at 15-min sampling. Capturing it would require sub-15-min
sampling (1-min partials), which remains the one unmeasured corner of
path 1.

## Addendum 3 (2026-08-01): multi-gate horizons, unconditioned — a whisper

K-gate tradable displacement (enter at event i's reveal-slipped issue
close, exit at event i+K's; K=3/5/10; daily stream, strict as-of-issue):
spectra ~= null with a small consistent extreme-tail excess (K=5: 7
species vs 1.3 expected at 0.85–0.90); post-2016 band years wobble
42–63%; declared books +$15k–$70k per decade, 7–9 of 11 years positive.
Real but far below deployable. Next (and last standing) candidate from
the campaign's own measurements: HERD-conditioned objects (the 73.6%
completion-sign tier) applied to the K-gate tradable displacement —
being built next. (ch4_kgate_law_K*.json)

## Addendum 4 (2026-08-01): herd conditioning — first replicated positive

Herd-conditioned K-gate tradable displacement (species x herd energy x
greed at issue, strict as-of-issue, reveal-slipped, prior-day herd
state for intraday causality):
- daily K=3 HG: 10/11 years positive (+$47.8k/decade, 2022 -3.5% only)
- hourly (independent rung, blind application): conditioning improves
  the unconditioned book at K=3 (-$9.7k -> +$23k HG / +$41k H) and
  K=5 (+$36k -> +$58k HG); 7-8/11 years positive.
The herd effect REPLICATES across rungs under fully honest timing —
the first surviving positive of this audit. Magnitude is modest
(~+2-5%/yr, worst years -3..-8%): real, not yet deployable dollars.
Open refinement (declared): the harvest cycle on this object —
species-quantile targets + adverse stops evaluated at gate-reveal
closes, replacing the blind K-gate exit. (ch4_kgate_herd*.json)

## Addendum 5 (2026-08-01): harvest shapes rarely mature; edge is real but small

The declared quantile-shape harvest barely activates: HG species are too
fine to earn 10 completed harvests (daily exits ~100% at the K=3
baseline). Hourly improves modestly (9/11 years, +$43k vs +$23k blind).
Critically, the daily book flips 10/11 -> 6/11 between two
near-identical ledger implementations of the same trades — the herd
K-gate edge is REAL in direction (replicates across rungs and
conditionings) but small enough that implementation details move the
book. Honest scale: low single digits per year. DECISION: wire the
simplest replicated form (K=3, bigram_HG entries, K=3 exit,
herd state at issue) into the CH4 paper channel as engine
herd_kgate_v1 for LIVE-FORWARD measurement — the paper book is the
instrument for exactly this. Expectation stated in advance: ~+2-6%/yr
scale, not yet the goal; live-forward divergence from that range is
itself information. (ch4_kgate_harvest_*.json)


## Addendum 6 (2026-08-04): the law is the PHYSICS — canonical confirmation

Run freely chosen during the granted hour. Species law rebuilt on the
CANONICAL uf_core kernel (production v1.4.0: quiet-interval gates,
pinned tau_D=0.20, log-normalized field), 5,219 symbols, 172,433
observations, strict as-of-issue, reveal=+2 bars:
**58.6-77.9% direction accuracy EVERY year 2016-2026 (11/11).**
Fourth independent gate construction to carry the law (divergent daily,
hourly, m15, now canonical). The law is a property of the physics.

Canonical gates are COARSE (~40/symbol/decade, weeks-months long) —
the ownership timescale, where the reveal tax amortizes to ~nothing.
The naive ride-to-next-gate money read is NOT yet positive (magnitude
asymmetry; 2020 crisis clustering whips the short side). Next
construction: polarity-aware harvest governance (species-quantile
targets/stops — the read that fixed this at the daily rung) on
canonical gates + herd conditioning + DSF gating. (ch4_canon_law.json)

## Reproduction

`tools/ch3_hourly_law.py` (CH3_RUNG=daily|hour|m15, CH3_TRADE_DISP=1
for the null proof, sharded via CH3_OBS_SHARD/CH3_OBS_MERGE),
`tools/ch3_hourly_harvest.py`, `tools/ch3_cycle_harvest.py`
(CH3_MORPH=1), `tools/ch3_hourly_replay.py`, stores
`ch4_hourly_universe_full.parquet` (5,016 syms, 2016–2026-03, hourly),
`ch3_m15_watchlist.parquet` (60 syms, 2016–2026-07, 15-min). Results in
`artifacts/ch4_uf/ch3_*.json`.

## Addendum 7 (2026-08-06): Mirror-world probe — the engine commutes with price inversion

Joe's probe: invert every price series and see what the decisions look
like. Construction: per symbol c_inv[t] = c[0]^2 / c[t] (exactly
negates every log-return, keeps prices positive and volumes unchanged),
rebuild the herd state on the inverted store, replay the UNTOUCHED
herd_kgate_v1 engine full-history (baseline=0). Declared expectations
in advance: structure-carried decisions should mirror (counts similar,
long/short flipped); drift-carried decisions should collapse; the herd
layer should mirror least (fear/greed asymmetry).

Results (real vs mirror):
- events 2,763,885 vs 2,621,798 (95% of gate events survive inversion)
- entries 7,604 vs 6,984 (92%)
- side mix 93.9% LONG vs 93.3% SHORT (flips to within 0.6pp)
- band mean 0.7856 vs 0.7858 (identical conviction distribution)

Entry-level rift map: 1,873 stock-days fire in BOTH universes and
100% of them flip direction exactly (zero same-side anomalies — the
decision logic has no sign leak). The other ~75% of entries exist in
only one universe; real-only entries concentrate in slow-grind rally
years (2017/2018 lose ~25% of entries in the mirror; choppy 2016
gains). Reading: the ENSEMBLE is the invariant (counts, side ratio,
conviction all mirror); individual entry membership is path/threshold
sensitive, and the herd conditioning reads an emotional asymmetry
(slow rallies vs fast crashes) that a mirrored universe cannot
reproduce.

Calibration in flight: 1bp-noise control (same pipeline, deterministic
seed) to measure baseline entry-set churn under ANY tiny perturbation —
the 75% membership divergence is only "asymmetry" if it clears that
floor. Scripts: session scratchpad build_inverted_store.py /
build_noise_store.py / mirror_driver{,2}.py; results
mirror_results.json / real_results.json / rift_map.json /
noise_floor.json (scratchpad; headline filed here).

Noise-floor result (same pipeline, deterministic 1bp gaussian on every
close, seed 0): 7,473 entries, only 49.1% shared with the real run —
half the entry list churns under an imperceptible perturbation. Side
agreement on shared entries: 3,734/3,734 (100%).

Final reading of the probe pair:
1. ENTRY MEMBERSHIP IS NOT A ROBUST OBJECT. The band>=0.75 threshold
   is knife-edged and cascades through path-dependent records: 1bp of
   noise rebuilds half the portfolio. CH4 must be evaluated on
   ensembles (counts, side mix, band distribution, aggregate P&L),
   never on individual picks. Two near-identical worlds pick different
   stocks of the same character.
2. DIRECTION IS THE ROBUST QUANTITY. 100% side agreement under noise,
   100% side flip under mirror, zero anomalies anywhere. The sign of
   conviction has no sensitivity at all.
3. The mirror churns membership ~2x the noise floor (24.6% vs 49.1%
   overlap), so a genuine asymmetry signal exists beyond sensitivity,
   concentrated in the herd layer and slow-rally years (Addendum 7
   rift map) — the fear/greed arrow markets actually have.
