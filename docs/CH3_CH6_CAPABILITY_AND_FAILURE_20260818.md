# CH3 / CH6 Capability and Failure Report — 2026-08-18

## Architecture honesty gate

1. **Requested architecture:** deterministic TFE decisions that preserve the explicit joint field and refuse decisions when required evidence is absent.
2. **Current code reality:** CH3 and CH6 are paper-only short experiments driven by a reduced event projection: completed-close gain, relative volume, price, and herd `gband`.
3. **Conflict with requested architecture:** **yes.** Neither channel evaluates the full joint field and neither should be represented as full DSF decision authority.
4. **Mechanisms not extended:** the former “large spike implies short,” missing-herd-means-calm behavior; the invalid same-bar re-entry behavior; CH1; CH2; L0–L4; and any real-order path.
5. **Single exact repaired item:** CH3/CH6 entry and anomaly-refutation custody, including their read-only pages and paper-book reconciliation.
6. **Full field or reduced approximation:** **reduced approximation.**
7. **Lost field structure:** explicit reversal phase, uncertainty, cohesion, pressure, breathing, multiscale relationships, and the joint topology among `D_k`, `M_k`, `R_rev_k`, `U_star_k`, `C_k`, `P_k`, and `B_k`.

The Completed Joint-Field Reconstruction is treated here as a strong working document requiring further proof, not as canonical authority.

## Verdict

CH3 and CH6 are not bad on most selections. They are dangerously asymmetric.

The current-regime record through the completed 2026-08-17 book is:

| Channel | Resolved trades | Wins | Realized P&L | Realized P&L excluding WETO |
|---|---:|---:|---:|---:|
| CH3 current regime | 10 | 8 | +$2,585.70 | +$5,665.95 |
| CH6 | 12 | 10 | -$733.00 | +$1,514.75 |

One WETO loss removed $3,080.25 from CH3 and $2,247.75 from CH6. CH6 therefore lost money despite winning 10 of 12 resolved trades. Win rate is not sufficient evidence of sound physics when loss magnitude is unbounded relative to ordinary harvest magnitude.

CH3 shows that post-event fading is a measurable population tendency. CH6 shows that the early part of that fade can often be harvested quickly. Neither channel establishes that an individual event has reached structural exhaustion.

## What happened in WETO

- Both channels shorted WETO at the completed 2026-08-14 close of $8.22.
- At the first observed anomaly action on 2026-08-17, the available live mark was $17.47. That was 112.53% against the short, not a 20% realized loss.
- The completed 2026-08-17 close was $24.59.
- Both channels then opened a new WETO short on that same completed bar, even though the earlier short thesis had already been refuted that day.
- WETO had also completed a 1-for-100 reverse split on 2026-08-03. This was an explicit corporate-action and extreme-tail environment, not an ordinary fade event. [Nasdaq corporate-action notice](https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2026-538)

The 20% law was implemented as an observation trigger. It could not guarantee a 20% realized-loss ceiling across a weekend gap or between observations. Describing it as a hard loss cap was false.

## Why the spike was shorted instead of bought

The entry projection treated a large up-move with elevated volume and low recorded herd state as a fade candidate. It did not determine whether upward structural motion was exhausted or accelerating.

The existing ten-year train test does not support simply reversing these events into long positions:

| Historical construction | Count | Mean result | Win rate | 1st percentile |
|---|---:|---:|---:|---:|
| Short high-prerun train events | 1,282 | +2.095% | 71.4% | -90.33% |
| Buy those same train events | 1,282 | -2.239% | 48.5% | -65.06% |

The population tends to fade, so “buy every extreme spike” was falsified. The short distribution nevertheless contains a catastrophic left tail. The correct conclusion is not to reverse the sign. It is that gain and volume alone do not identify exhaustion.

## Defects found in the channel mechanics

1. **Missing evidence was converted into favorable evidence.** A symbol with no herd row was treated as “no herd backing.” No observation is not a calm observation.
2. **An anomaly did not create persistent refutation.** The same symbol could be cut and then re-entered on the same bar.
3. **The 20% trigger was presented like a cap.** A trigger observed after a gap cannot manufacture a fill at the threshold.
4. **CH6 anomaly custody depended too heavily on its five-minute loop.** The completed-close settlement path did not independently enforce the anomaly action.
5. **Legacy pages could conceal missing marks.** CH3's old static renderer replaced a missing quote with entry price, visually manufacturing a flat position.
6. **The pages overstated the physics.** They did not disclose that the entry law is a reduced projection rather than full joint-field evaluation.

## Repairs completed

- CH3 and CH6 now require explicit same-day `gband=0`; missing herd coverage is refused.
- An anomaly cut now keeps the symbol refuted until a later completed daily close returns to or below the original entry. The candidate bar cannot reset its own refutation.
- CH6 checks anomaly custody both during live polling and during completed-close settlement.
- Book writes are atomic.
- The invalid 2026-08-17 WETO re-entries were voided without deleting history or creating fictional P&L:
  - CH3: cash restored to -$79,596.15; 35 valid open positions remain.
  - CH6: cash restored to $67,556.51; 16 valid open positions remain.
- Linked and legacy channel pages now disclose the reduced projection, missing-evidence refusal, refutation reset, and trigger/gap distinction.
- A missing mark now makes aggregate equity and unrealized P&L unavailable instead of silently substituting entry price.
- Voided records remain visible but do not affect win rate or realized P&L.

## What this repair does not prove

This repair establishes deterministic evidence custody around the existing paper experiments. It does not elevate CH3 or CH6 to full-field L5, prove that their entry projection is canonical, model borrow availability or fees, guarantee stop execution, or authorize real trading.

The recommended architectural next step for these channels is a separate proof that maps explicit joint-field relationships to exhaustion versus continuation. The current event projection should remain labeled reduced until that proof exists.
