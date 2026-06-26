# Gate D1 Bit-Equivalence Amendment Note

**Ref:** TFE-CMD-GATE-D1-S_N-EMISSION-WC-20260625-AMEND-1
**Original FAIL SHA:** 8ecfdaf
**Corrected test SHA:** this dispatch (see commit)

---

## What failed

Both the original test (8ecfdaf) and the cohort-segmented test (this
dispatch) fail to achieve bit-equivalence between the quarantine kernel's
s_n and the production path's s_n.

**Original failure (full sample, 8ecfdaf):**
- max abs_diff = 1.66 on 42,036 rows
- Cause: quarantine kernel uses full history; production uses 252-bar
  rolling window. Integrators diverge after 252 bars. Expected.

**Amendment failure (Cohort_W1, this dispatch):**
- 38,123 Cohort_W1 rows found in early-bar window (2020-04-01 → 2020-05-31)
- max abs_diff = 1.35 on Cohort_W1 rows
- Cause: described below. Unexpected.

---

## Root cause of Cohort_W1 divergence

The amendment's invariance premise was:

> "When bar_count ≤ 20 < 252 (max_bars cap), both kernels process identical
> raw bars from the same zero integrator state."

This premise is FALSE. `compute_quarantine_s_n` in the test runs
`build_state_rows` on the **full bar history** (all 1,562 bars for GLP).
The test then filters the output to early-bar dates for the Cohort_W1 
comparison.

The quarantine kernel's `compute_l0_sev` computes:
```
kappa_t = |F[t+1] - 2*F[t] + F[t-1]|  for 0 < t < n-1
kappa_t = 0.0                            for t == n-1 (last bar)
```

When running on 1,562 bars, bar at index t=11 is NOT the last bar. It has
access to F[12] (from 2020-04-20, the next trading day). So kappa_11 = 0.43.

When running on only 12 bars (as the production path does, since bar_count=12
means only 12 bars have been observed), t=11 IS the last bar. kappa_11 = 0.0.

Verification (GLP, 2020-04-17, bar_count=12):
```
kappa at t=11 (full history run):  0.430000  ← F[12] = 2020-04-20 close used
kappa at t=11 (12-bar run):        0.000000  ← last bar, kappa = 0 (correct)

s_n from quarantine (full run):   0.131645   ← leaks future bar
s_n from production  (12-bar):    1.483684   ← no future leakage
```

The s_n difference (1.352) is not a bug in the s_n port. It is a consequence
of the quarantine kernel's kappa computation "leaking" future bar data when
run on the full history.

---

## What this means for Gate D1

Gate D1 (s_n emission in production) cannot be validated by comparing to the
quarantine kernel's s_n values as produced by `build_state_rows` on the full
history.

The production snapshot path (`compute_cognitive_scalars`) processes a
252-bar rolling window — it does NOT have access to future bars. The quarantine
kernel, when run on full history to extract historical s_n values, produces
kappa values at intermediate bars that are contaminated by future data. These
are NOT the same computation.

**The s_n emission code change in 8ecfdaf is correct** — it faithfully ports
the `surprise = ||nu_core - z_n||` formula from the quarantine kernel. The
disagreement is in the TEST DESIGN, not in the implementation.

---

## Options for Joe + wC

**(a) Validate s_n using a different reference.**
Run `compute_cognitive_scalars` with the SAME bars and SAME window as the
quarantine kernel, by passing each date's bar slice explicitly. This would
test that the s_n formula in `compute_cognitive_scalars` matches the quarantine
kernel's formula for the SAME inputs.

**(b) Accept the architectural difference as documented.**
Define "production s_n" explicitly as the output of `compute_cognitive_scalars`
with the 252-bar rolling window. Validate it against a numerical formula
check (e.g., hand-verify the s_n formula on 5 randomly-selected bars), not
against the quarantine kernel's full-history output.

**(c) Modify the quarantine kernel test helper to run per-window.**
Add a test-only function to quarantine_historical_kernel.py that takes a
bar slice (not the full history) and returns the gate s_n for that slice.
This would match the production path's semantics. (Requires modifying the
quarantine kernel — needs authorization.)

---

## Status

Gate D1: s_n emission code is committed and correct (8ecfdaf).
Gate D1: bit-equivalence test cannot PASS in the current test design.
Gate D1: **BUILT, NOT-TESTED** — code correct, test methodology unresolved.

Three-key sign-off (Joe + wC + c1) required to resolve test methodology
before Gate D1 can be marked BUILT-AND-TESTED.
