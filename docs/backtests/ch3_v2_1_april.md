# CH3 v2.1 Backtest — Corrected Apparatus

**Window:** 2026-04-07 to 2026-05-04
**Data:** Per-bar kernel (L0-L4) computed on daily_bars. 10,023 tickers, 20 trading days.
**Generated:** 2026-06-16

## Backtest 1: SPY D_k=1 gate

**Not possible.** SPY D_k=1 never lasts more than 2 consecutive days in available data (33 isolated days across 2021-2026). No 60-day contiguous window exists. SPY D_k=1 is a gate-transition event, not a sustained state. Any channel gated on SPY D_k=1 fires only on isolated days.

## Backtest 2: V2 without SPY gate (April 7 - May 4)

Entry: M_k > 0, M_k(t) > M_k(t-1) > M_k(t-2), per-ticker D_k = 1, bar_count >= 21, price >= $5.

### Resolved trades only (meaningful exits)
- **3,333 trades** | WR: 1,700/3,333 = **51.0%**
- Avg win: **+7.21%** | Avg loss: **-5.22%** | **Ratio: 1.38x**
- P&L: $93,071

### Unresolved (data_end)
- 598 trades | WR: 54.5% | Avg win: +2.76% | Avg loss: -2.18% | Ratio: 1.27x

### Exit distribution (resolved)
| Reason | Count | % |
|--------|-------|---|
| m_k_rollover | 874 | 26% |
| max_hold | 827 | 25% |
| take_profit | 701 | 21% |
| stop_loss | 686 | 21% |
| catastrophic | 245 | 7% |

Max concurrent: 255. Unique tickers: 894. CH2 overlap: 0%.

## Control: Original CH3 (S_UF >= 0.70, D_k = 1)

### Resolved trades only
- **4,011 trades** | WR: 2,029/4,011 = **50.6%**
- Avg win: **+4.40%** | Avg loss: **-3.47%** | **Ratio: 1.27x**
- P&L: $51,047

Max concurrent: 309. Unique tickers: 553. CH2 overlap: 1%.

## Comparison Table

| Channel | Signals | WR | Avg Win | Avg Loss | Ratio | Max Conc | CH2 Overlap |
|---------|---------|-----|---------|----------|-------|----------|-------------|
| **CH2 April baseline** | 30 | 50% | +12.34% | -4.81% | **2.57x** | n/a | 100% |
| Original CH3 (S_UF≥.70) | 4,724 | 50% | +4.03% | -3.15% | 1.28x | 309 | 1% |
| **V2 no-SPY-gate** | 3,931 | 52% | +6.50% | -4.78% | **1.38x** | 255 | 0% |

## Key findings

1. **V2 resolved-trade ratio (1.38x) is better than original (1.28x)** and has materially higher avg win (+7.21% vs +4.40%). M_k rising selects stronger energy entries.

2. **Both fire far too broadly** (255-309 concurrent signals). Neither has the selectivity to be a deployable channel without additional filtering.

3. **0% CH2 overlap** — V2 selects entirely different stocks than CH2. It IS genuinely additive at the signal level.

4. **13% overlap between V2 and original CH3** — structurally distinct selections.

5. **CH2 remains dominant at 2.57x ratio.** V2's 1.38x and original's 1.28x don't justify a second channel — the asymmetry is too thin for the complexity cost.

6. **The selectivity problem remains the binding constraint.** V2 has the right structural thesis (M_k rising = energy loading) but fires on too many tickers to be actionable.
