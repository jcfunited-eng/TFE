# CH3 v2.1 Selectivity Backtest Report
**Window:** 2026-04-07 to 2026-05-05
**Position size:** $2,500
**Data source:** runtime_decisions_history (validation DB)
**Generated:** 2026-06-16T20:53:42Z

**NOTE:** SPY D_k computed from price proxy. 62% data_end exits due to sparse validation DB.

**CH2 tickers in window:** 30
**Original CH3 tickers in window:** 83

### Variant A: Universe-relative (top decile M_k)

**Signals admitted:** 42
**Win rate:** 21/42 = 50.0%
**Avg win:** +2.81%
**Avg loss:** -2.08%
**Asymmetry ratio:** 1.35x
**Total P&L:** $423
**Max concurrent signals:** 34
**Unique tickers:** 49

**Exit reason distribution:**

| Reason | Count | % |
|--------|-------|---|
| data_end | 33 | 79% |
| stop_loss | 7 | 17% |
| take_profit | 2 | 5% |

**CH2 overlap:** 0/49 = 0%
**Original CH3 overlap:** 0/49 = 0%

**Acceptance criteria:**

| Criterion | Value | Pass? |
|-----------|-------|-------|
| Max concurrent <= 20 | 34 | NO |
| Asymmetry >= 1.5x | 1.35x | NO |
| CH2 overlap <= 30% | 0% | YES |
| Original CH3 overlap <= 10% | 0% | YES |

**Overall: CRITERIA NOT MET**

**Top 10 trades:**

| Ticker | Entry | Exit | P&L% | M_k | Exit Reason | Bars |
|--------|-------|------|------|-----|-------------|------|
| PUBM | $9.62 | $10.23 | +6.34% | 0.7724 | data_end | 1 |
| EGAN | $7.31 | $7.74 | +5.88% | 0.9012 | data_end | 1 |
| TNK | $74.52 | $78.62 | +5.51% | 0.8079 | take_profit | 1 |
| HOG | $23.19 | $24.27 | +4.64% | 0.8858 | data_end | 1 |
| LAD | $275.38 | $286.84 | +4.16% | 0.9088 | data_end | 1 |
| BX | $121.65 | $126.35 | +3.86% | 0.795 | data_end | 1 |
| HXL | $89.39 | $92.23 | +3.18% | 1.0811 | data_end | 1 |
| GNK | $23.54 | $24.25 | +3.02% | 0.7812 | data_end | 1 |
| JKHY | $149.36 | $153.86 | +3.01% | 0.9434 | take_profit | 1 |
| AROW | $36.06 | $37.14 | +3.00% | 1.0096 | data_end | 1 |

### Variant B: Self-relative (M_k >= 2x stdev)

**Signals admitted:** 350
**Win rate:** 185/350 = 52.9%
**Avg win:** +3.68%
**Avg loss:** -3.15%
**Asymmetry ratio:** 1.17x
**Total P&L:** $4,034
**Max concurrent signals:** 278
**Unique tickers:** 390

**Exit reason distribution:**

| Reason | Count | % |
|--------|-------|---|
| data_end | 224 | 64% |
| stop_loss | 68 | 19% |
| take_profit | 49 | 14% |
| catastrophic_floor | 9 | 3% |

**CH2 overlap:** 8/390 = 2%
  Tickers: BELFA, BELFB, PWR, RRX, SOHU, SONO, WCC, WOR
**Original CH3 overlap:** 13/390 = 3%
  Tickers: AMZN, BFST, DEI, DMLP, FIZZ, HBCP, HTH, KN, NPKI, OCFC, PFIS, PRKS, RBC

**Acceptance criteria:**

| Criterion | Value | Pass? |
|-----------|-------|-------|
| Max concurrent <= 20 | 278 | NO |
| Asymmetry >= 1.5x | 1.17x | NO |
| CH2 overlap <= 30% | 2% | YES |
| Original CH3 overlap <= 10% | 3% | YES |

**Overall: CRITERIA NOT MET**

**Top 10 trades:**

| Ticker | Entry | Exit | P&L% | M_k | Exit Reason | Bars |
|--------|-------|------|------|-----|-------------|------|
| MXL | $60.32 | $71.89 | +19.17% | 0.6858 | take_profit | 1 |
| BAND | $23.44 | $27.73 | +18.30% | 0.099 | take_profit | 1 |
| RMAX | $7.07 | $8.14 | +15.16% | 0.1022 | take_profit | 1 |
| PRCH | $7.58 | $8.63 | +13.98% | 0.2743 | take_profit | 1 |
| JOBY | $8.42 | $9.31 | +10.58% | 0.5855 | take_profit | 1 |
| CEVA | $28.1 | $31.02 | +10.38% | 0.6833 | take_profit | 1 |
| CRNC | $8.29 | $9.15 | +10.36% | 0.219 | take_profit | 1 |
| TDOC | $5.75 | $6.29 | +9.43% | 0.0347 | take_profit | 1 |
| TRDA | $12.96 | $14.07 | +8.54% | 0.1629 | take_profit | 1 |
| PAL | $6.96 | $7.54 | +8.39% | 0.6925 | take_profit | 1 |

### Cross-Variant Overlap

- Variant A tickers: 49
- Variant B tickers: 390
- A ∩ B overlap: 46 (12%)