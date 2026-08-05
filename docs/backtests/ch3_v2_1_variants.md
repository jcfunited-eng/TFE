# CH3 v2.1 Selectivity Variants — Final Results

**Window:** April 7 - May 4 2026 | **Per-bar kernel on daily_bars** | 10,023 tickers, 20 days

## Comparison Table

| Channel | Signals | WR | Avg Win | Avg Loss | Ratio | Max Conc | CH2 Overlap |
|---------|---------|-----|---------|----------|-------|----------|-------------|
| **CH2 April** | 30 | 50% | +12.34% | -4.81% | **2.57x** | n/a | 100% |
| Orig CH3 (S_UF≥.70) | 4,724 | 50% | +4.03% | -3.15% | 1.28x | 309 | 1% |
| V2 no-SPY | 3,931 | 52% | +6.50% | -4.78% | 1.36x | 255 | 0% |
| **VA self-rel 2x** | 2,539 | 53% | +6.05% | -4.37% | **1.39x** | 185 | 0% |
| **VB acceleration** | 2,516 | 50% | +6.55% | -4.90% | 1.34x | 185 | 0% |

## Acceptance Criteria

| Criterion | VA | VB | Required |
|-----------|-----|-----|----------|
| Max concurrent ≤ 20 | **185 — NO** | **185 — NO** | ≤ 20 |
| Asymmetry ≥ 1.5x (resolved) | **1.40x — NO** | **1.37x — NO** | ≥ 1.5x |
| CH2 overlap ≤ 30% | 0% — YES | 0% — YES | ≤ 30% |

**Neither variant meets acceptance criteria.**

## Findings

1. **Selectivity improved but insufficient.** VA reduced signals from 3,931 to 2,539 (35% reduction) and VB to 2,516 (36%). Max concurrent dropped from 255 to 185 — better but still 9x the 20-signal cap.

2. **Asymmetry stable around 1.35-1.40x across all M_k variants.** The self-relative and acceleration filters don't concentrate the asymmetry — they just reduce noise.

3. **0% CH2 overlap maintained.** The M_k signal is genuinely additive at the ticker level.

4. **CH2 remains dominant at 2.57x.** The M_k channel produces a real but thin edge (~1.4x) that doesn't justify deployment complexity at $100K scale.

## Disposition

Per acceptance criteria: **CH3 v2 archived.** M_k as primary observable produces a real but commercially-marginal channel at $100K resolution. The kernel perceives M_k energy loading but the signal fires too broadly and too weakly to justify a parallel execution pipeline.

Revisit conditions: account size change (more capital to spread across 185+ signals), kernel resolution change (daily → intraday bars producing sharper M_k transitions), or a selectivity gate not yet tested that achieves ≤ 20 concurrent with ≥ 1.5x ratio.
