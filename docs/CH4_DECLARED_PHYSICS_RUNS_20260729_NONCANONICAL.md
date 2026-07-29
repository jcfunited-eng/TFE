# CH4 Declared Physics Runs — 2026-07-29 (NON-CANONICAL)

Session context: prior CH4 session ended 18:33 UTC in suspected
behavioral corruption (Joe's report; corruption artifacts confined to
that chat session — nothing corrupted found on file in this lane).
Its three final experiment programs were recovered, vetted line-by-line
(no look-ahead, trailing-only conditions, declared constants, declared
nulls, deterministic seeding), committed at `f53fec93`, and executed
unmodified. Results below are raw. Nothing was tuned, re-run, or
selected. All runs: closed bars only, forming bar excluded.

---

## 1. `vtvr_ch4_physics_gate.py` — engine candidate v3 (six slow-state conditions + zombie eligibility)

Declared acceptance bar (in-file, pre-run): precision must RISE as
conditions stack; flat curve = dead, by the standard that executed the
prior engines.

### Cohort A (home field, 30 names, 1503 bars 2020-07-27..2026-07-29)

| conditions | firings/yr | WR@20 | avg@20 | WR@60 | avg@60 | WR@90 | avg@90 |
|---|---|---|---|---|---|---|---|
| 0 | 286.3 | 51.3 | +0.49 | 52.1 | +2.34 | 53.1 | +3.91 |
| 1 | 1336.8 | 54.8 | +1.10 | 56.5 | +2.93 | 57.6 | +4.65 |
| 2 | 2649.1 | 54.7 | +1.03 | 57.5 | +2.87 | 57.9 | +4.37 |
| 3 | 2358.9 | 53.7 | +0.91 | 57.6 | +3.06 | 58.0 | +4.47 |
| 4 | 830.5 | 55.1 | +1.17 | 60.5 | +3.76 | 60.5 | +4.91 |
| 5 | 96.2 | 58.0 | +1.63 | 62.1 | +4.57 | 57.8 | +5.77 |
| 6 | 2.1 | 45.5 | −0.06 | 63.6 | +3.79 | 36.4 | +3.44 |

Universe base @60: WR 57.5%, mean +2.34%→+3.04%. Full-gate firings:
11 in ~5.2yr. **@60 the curve rises monotonically 52.1→63.6 — the
demanded signature — but k=6 has n=11 and the 20/90 horizons do not
confirm (k=6 @20 below base; @90 collapses).**

### Cohort B (virgin, 30 names, 1506 bars)

| conditions | firings/yr | WR@60 | avg@60 | WR@90 | avg@90 |
|---|---|---|---|---|---|
| 0 | 299.5 | 52.8 | +3.14 | 53.9 | +3.89 |
| 1 | 1379.3 | 54.6 | +2.83 | 54.0 | +4.24 |
| 2 | 2640.8 | 54.8 | +2.85 | 55.5 | +4.38 |
| 3 | 2321.1 | 55.0 | +2.62 | 55.3 | +4.22 |
| 4 | 815.0 | 55.7 | +2.82 | 55.8 | +4.25 |
| 5 | 103.1 | 56.0 | +2.91 | 58.1 | +4.77 |
| 6 | 1.2 | 66.7 | +0.57 | 66.7 | +1.92 |

Universe base @60: WR 54.9%, mean +2.78%. **Nearly flat: home-field
+4.6pp over base at k=5 shrinks to +1.1pp on virgin names; avg@60 at
base. Weak monotonicity in WR only. By the standard that voided the
prior engines: NOT CONFIRMED on virgin data.**

### 300-name pooled (FULL300 — 10 cohorts of 30, all succeeded)

| conditions | firings/yr | WR@20 | avg@20 | WR@60 | avg@60 | WR@90 | avg@90 |
|---|---|---|---|---|---|---|---|
| 0 | 321.3 | 52.8 | +1.12 | 56.5 | +4.46 | 57.7 | +6.96 |
| 1 | 1364.7 | 54.3 | +1.52 | 57.6 | +4.86 | 59.1 | +7.56 |
| 2 | 2468.7 | 54.2 | +1.36 | 56.8 | +4.32 | 58.5 | +6.82 |
| 3 | 2165.1 | 54.3 | +1.27 | 57.8 | +4.46 | 59.3 | +6.80 |
| 4 | 730.8 | 53.8 | +1.25 | 57.6 | +4.02 | 59.4 | +6.35 |
| 5 | 94.5 | 54.2 | +1.57 | 55.6 | +3.91 | 59.1 | +6.13 |
| 6 | 1.0 | 66.0 | +2.44 | 51.1 | −1.82 | 48.9 | +1.44 |

Universe base @60: WR 57.3%, mean +4.44%. Full-gate firings: 47.

**FLAT — DEAD by the declared standard.** At full scale the curve does
not rise at any horizon; k=5 sits below base @60, and the full gate
(k=6, n=47 — a real sample now) is 51.1% WR with negative mean @60.
The cohort-A monotone rise was home-field idiosyncrasy. Engine
candidate v3 is executed by the same standard that executed v1/v2.

## 2. `vtvr_whole_history_physics.py` — windowless lifetime-integral state (LIFE/SAT/DRAIN)

Declared one-shot prediction (in-file, pre-run): alive (LIFE≥0.9),
lifetime-saturation-deep (SAT≤0.2), lifetime-drained (DRAIN≤0.2)
vertices gain structural share over the next 60–90 bars vs field.

Cohort A result:

```
+60 bars: share ROSE in 48.0% of qualifying configurations (n=11283)
          vs 48.2% baseline (n=34800); mean Δshare −8.03e−05 vs ~0
+90 bars: 46.0% vs 46.9% baseline; mean Δshare −2.19e−04 vs ~0
L5 line:  price @60 57.2%/+2.46% vs baseline 56.2%/+2.75% — nothing
```

**FALSIFIED — clean NULL.** Qualifying configurations do no better
(marginally worse) than the field. Note: the three conditions are
strongly correlated (32% of vertex-days qualify, not the ~2% naive
independence would give) — the "drained extreme" is not a rare state
under these lifetime definitions.

## 3. `vtvr_field_dynamics.py` — conserved-field linear-response dynamics (P1–P4)

Cohort A, 1502 closed bars, conservation verified to 4.4e−16.

- **P1 operator stability:** real era-to-era similarity mean +0.153 vs
  shuffled null mean +0.011 (p95 +0.213). Above the null mean, below
  the declared p95 bar → **dynamics NOT distinguishable from noise.**
- **P2 relaxation spectrum:** slow modes at ~1131/363/159 bars —
  descriptive only given P1.
- **P3 irreversibility:** 33 of 435 edges show persistent currents
  beyond the time-reversal null (~22 expected at 5% false-positive) —
  mild excess; strongest currents HD→CAT, BDX→DE/CAT/LIN, PEP→CAT.
- **P4 virgin-era forecast (the falsifiable core):** mean corr
  (predicted Δρ, realized Δρ) = +0.0267 over 501 steps, SE 0.0137,
  shuffled-operator null +0.0141 → fails both declared bars →
  **dynamics NOT captured by this operator.**

## Standing after today

- Four declared shots, four honest misses (gate on virgin cohort: not
  confirmed; gate at 300-name full scale: flat/dead; lifetime-drain:
  falsified; linear dynamics: not captured).
- The paper book keeps trading the (edge-unproven, stamped) bands_v1
  rule as the forward evidence channel; runner alive, tonight's bar
  processes at 21:10 UTC.
- Nothing was wired into the book. Engine replacement still requires a
  candidate that survives its own declared tests on virgin data first.
