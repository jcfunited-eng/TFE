# Independently implemented temporal geometry

Implemented in `tools/tfe_exact_geometry.py`. This imports no existing kernel and is not yet a replacement seven-field DSF law or a selection mechanism.

For observed points `(t_i, X_i)`, retain every point, coordinate identity and unit. Form each oriented edge `(dt_i, dX_i)` by exact subtraction. Between consecutive edges retain every component of their exterior product:

```
time-coordinate[j] = dt_previous * dX_current[j]
                   - dt_current * dX_previous[j]

coordinate-pair[j,k] = dX_previous[j] * dX_current[k]
                     - dX_previous[k] * dX_current[j]
```

These are exact oriented areas of sampled edges, not instantaneous physical derivatives or an assumed interpolation between samples. They describe temporal bending and joint coordinate relationships. No norm, average, sum across components, normalization, fitted weight, threshold or ranking replaces them. Their original operands remain available. A straight rise has zero bend but nonzero displacement, so zero bend must never be interpreted as no motion or as quiescence.

Unknown values remain unknown through the affected relationships. Inputs are not reordered or filled. Decimal observations are converted to exact rationals; binary floating-point input is refused. A resource bound refuses oversized constructions without truncation. Initial observations do not receive fabricated derivatives.

## Evidence

Fourteen tests passed: exact reconstruction, common rise/fall preservation, causal prefix invariance, irregular timestamps, complete oriented pair retention, missing observations, input refusal, resource refusal and initialization.

Applied independently to the original provider response for AEBI: 306 daily OHLCV observations, five coordinates, 305 edges, 304 turns, and 3,040 coordinate-pair components. Every source coordinate reconstructs exactly from the first point and its successive changes. A separately computed 150-observation prefix agrees exactly with the corresponding prefix of the full computation.

Evidence is in `artifacts/tfe_verification/exact_geometry_20260922/`. Provider timestamps identify daily bars, not when completed bars became knowable. The adjusted historical response is not certified as the data vintage available on historical decision dates. This run establishes geometry preservation, not historical prediction.

## Remaining mathematical boundary

These geometric quantities are not relabelled as resonance, uncertainty, cohesion, pressure or breathing. Their physical definitions and relationships still require an explicit derivation before claiming replacement L0–L4. The further task is to determine which complete evolving configurations justify an anticipatory structural interpretation, and falsify that interpretation against continuation and failure cases. No entry rule, predictive accuracy, WR or SPY-relative lift is claimed here.

The existing kernel, production trading paths and Guala were not modified.
