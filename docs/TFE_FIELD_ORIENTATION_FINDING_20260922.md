# Executed field and orientation checks — 2026-09-22

## Scope correction

The reflection controls demonstrate an orientation invariance of the inspected kernel path. They do not establish that structural selection is impossible, that L4 should equal price direction, or that the kernel must be changed before any L5 evaluation. My earlier description of restoring orientation as the necessary next correction overstated the result. Financial interpretation belongs to L5; whether its available inputs suffice must be checked against the actual proposed decision law.

## Executed measurements

103 retained as-of observations were aligned to subsequent closes: AGNC and SPY each have 20 observations, AEBI has 63. Raw-prefix hashes, source hashes, unchanged earlier prices and consecutive prefix lengths were checked. All final delivered D_k values are +1; the 100 subsequent close changes include 39 rises, 59 falls and two unchanged closes. These are outcome annotations, not fills, win rate or a tested prediction rule.

The complete seven fields and existing S_UF/R_UF context remain in `artifacts/tfe_verification/field_price_alignment_20260922/observations.csv`. The accompanying plot shows every coordinate separately. Peak/valley labels use subsequent observations and are explicitly retrospective. Source fidelity, original adjusted-price vintage and listing completeness remain unresolved; artifact integrity does not settle them.

## Reflection control

The unchanged kernel was executed on each final supplied history and its log reflection:

`F_mirror(t) = (F(0) + epsilon)^2 / (F(t) + epsilon) - epsilon`

Epsilon is the existing L0 offset, 1e-8. All mirrored inputs remained positive.

| Symbol | Bars | Original price change | Reflected price change | Largest absolute L4 difference across all corresponding segments and fields |
|---|---:|---:|---:|---:|
| AGNC | 2693 | -44.27% | +79.43% | 1.55e-15 |
| SPY | 2693 | +278.91% | -73.61% | 3.77e-15 |
| AEBI | 306 | +7.25% | -6.76% | 4.44e-16 |

Segment boundaries match throughout. D_k, reversal, cohesion and pressure match exactly. Other numeric differences are reported, not silently equated.

The source explains the invariance: L0 retains signed dF. L1 uses absolute dF in deviation and TVR variation, then takes the norm of differences between gate means. Its exported GateL1State does not retain a signed coordinate. A separate interface control reflected retained L0 signed coordinates and obtained exactly equal complete L1 records for all 12 AGNC, six SPY and seven AEBI segments. This interface control is distinct from the raw-input runs.

An L5 interpretation cannot obtain raw orientation from exactly identical inputs alone. This does not rule out useful orientation-independent structural detection, nor establish that all domain context is unavailable. No new orientation shortcut or selection rule was introduced.

## Existing governance evaluated subsequently

`artifacts/tfe_verification/existing_governance_20260922/run.py` executes the actual JavaScript V3 module on all 103 retained tuples and checks agreement with the existing Python port. Decisions agree for all inputs; numeric differences are recorded. Results are in the adjacent `result.json`.

This is execution of the existing decision calculation, not a full strategist or portfolio replay. It does not certify its constants, satisfy the requested full temporal evaluation, or establish WR/lift improvement. No kernel, trading behavior or Guala process was changed.

The next work belongs at the existing L5 selection/replay boundary: establish and measure the decision mechanism under the requested constraints, instead of treating a diagnostic invariance as a prerequisite to invent another kernel.
