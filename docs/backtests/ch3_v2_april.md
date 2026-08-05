# CH3 v2 Backtest Report
**Window:** 2026-04-07 to 2026-05-05
**Position size:** $2,500
**Data source:** runtime_decisions_history (validation DB)
**Generated:** 2026-06-16T20:25:52Z

**NOTE:** SPY D_k computed from price proxy (close vs prev_close), not kernel. This is an approximation.

### CH3 v2: M_k-driven energy grabber

**Signals admitted:** 442
**Win rate:** 227/442 = 51.4%
**Avg win:** +4.10%
**Avg loss:** -3.70%
**Asymmetry ratio:** 1.11x
**Total P&L:** $3,380

**Exit reason distribution:**

| Reason | Count | % |
|--------|-------|---|
| data_end | 272 | 62% |
| stop_loss | 83 | 19% |
| take_profit | 64 | 14% |
| catastrophic_floor | 23 | 5% |

**Max concurrent signals (single day):** 345

**Sample trades (top 10 by P&L):**

| Ticker | Entry | Exit | P&L% | Exit Reason | Bars |
|--------|-------|------|------|-------------|------|
| MB | $6.15 | $7.38 | +19.98% | take_profit | 1 |
| MXL | $60.32 | $71.89 | +19.17% | take_profit | 1 |
| BAND | $23.44 | $27.73 | +18.30% | take_profit | 1 |
| USAR | $22.66 | $26.11 | +15.20% | take_profit | 1 |
| RMAX | $7.07 | $8.14 | +15.16% | take_profit | 1 |
| PRCH | $7.58 | $8.63 | +13.98% | take_profit | 1 |
| IHRT | $5.42 | $6.15 | +13.38% | take_profit | 1 |
| DNA | $7.73 | $8.75 | +13.20% | take_profit | 1 |
| RLYB | $8.78 | $9.85 | +12.23% | take_profit | 1 |
| FTRE | $9.8 | $10.86 | +10.80% | take_profit | 1 |

### Control: Original CH3 (S_UF >= 0.70, D_k = 1)

**Signals admitted:** 81
**Win rate:** 42/81 = 51.9%
**Avg win:** +2.26%
**Avg loss:** -2.54%
**Asymmetry ratio:** 0.89x
**Total P&L:** $-35

**Exit reason distribution:**

| Reason | Count | % |
|--------|-------|---|
| data_end | 56 | 69% |
| stop_loss | 12 | 15% |
| take_profit | 10 | 12% |
| catastrophic_floor | 3 | 4% |

**Max concurrent signals (single day):** 70

**Sample trades (top 10 by P&L):**

| Ticker | Entry | Exit | P&L% | Exit Reason | Bars |
|--------|-------|------|------|-------------|------|
| ALRM | $44.14 | $46.24 | +4.76% | take_profit | 1 |
| ALH | $24.37 | $25.48 | +4.55% | data_end | 1 |
| PRKS | $33.8 | $35.27 | +4.35% | data_end | 1 |
| MAN | $29.28 | $30.52 | +4.23% | data_end | 1 |
| SSNC | $66.28 | $69.07 | +4.21% | take_profit | 1 |
| ACM | $79.7 | $83.0 | +4.14% | take_profit | 1 |
| CCI | $85.13 | $88.59 | +4.07% | take_profit | 1 |
| VRSK | $177.51 | $184.46 | +3.92% | data_end | 1 |
| MSM | $97.84 | $101.51 | +3.75% | take_profit | 1 |
| COLM | $60.26 | $62.35 | +3.47% | data_end | 1 |

### Overlap Analysis

- CH3 v2 unique tickers: 442
- Original CH3 unique tickers: 81
- Overlap: 14 tickers (3% of v2)
- Overlapping: AMZN, BFST, CFR, DEI, DMLP, FIZZ, HBCP, HTH, KN, NPKI, OCFC, PFIS, PRKS, RBC