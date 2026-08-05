# Canonical L6 exact integer boundary — 2026-07-27

## Decision

Canonical L6 now evaluates

\[
n_{\mathrm{eff}} < \frac{n_{\mathrm{start}}}{e}
\]

without binary floating-point arithmetic. The lock inequality and all L6
inputs and outputs are unchanged. Canonical L0–L4 is unchanged.

## Defect removed

The former implementation used
`ceil(dimensions / math.e)`. That is not the stated integer-exact law.
For

\[
n_{\mathrm{start}}=2^{63}-1,
\]

the binary-float calculation returned
`3393088950634442752`; the exact knee is
`3393088950634442637`.

## Exact law

Let

\[
A_r=\sum_{j=0}^{r}\frac{(-1)^j}{j!}.
\]

For every even \(m\), the alternating factorial series gives strict bounds

\[
A_{m+1}<\frac{1}{e}<A_m.
\]

The implementation advances these adjacent bounds using integer numerators
and factorial denominators. It multiplies both bounds by
\(n_{\mathrm{start}}\) and stops when their floors are equal. That common
integer is exactly
\(\lfloor n_{\mathrm{start}}/e\rfloor\). Because \(e\) is irrational and
\(n_{\mathrm{start}}>0\),

\[
\left\lceil\frac{n_{\mathrm{start}}}{e}\right\rceil
=
\left\lfloor\frac{n_{\mathrm{start}}}{e}\right\rfloor+1.
\]

The interval width tends to zero factorially, so the calculation terminates
without an epsilon, precision setting, iteration cap, or tuned threshold.

## Authority and validation

- Canonical implementation:
  `dsf_ai_service/substrate/canonical_l6.py`
- The duplicate language-strand implementation was removed; that module now
  delegates to the same canonical function.
- Exact regression and independent positive-series certificate:
  `tests/test_canonical_l6_exact_knee.py`
- Focused result after final input validation:
  `39 passed in 0.94s`
- Boolean, floating-point, negative, and otherwise noninteger dimension
  counts fail closed.

No production deployment or live-hearing claim is made by this correction.
