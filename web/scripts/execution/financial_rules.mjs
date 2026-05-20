/**
 * web/scripts/execution/financial_rules.mjs
 * TFE Financial Rules Library — Deterministic Entry/Exit Governance
 *
 * All trading rules in one place. No ML. No heuristics. No smoothing.
 * Each rule is a pure function: data in, boolean + reason out.
 *
 * Rules are referenced by ID (e.g. ENTRY-R1) in logs and audit trails.
 * When a rule blocks or allows a trade, the ID is recorded in the ledger
 * rationale_json so every decision is traceable.
 *
 * ═══════════════════════════════════════════════════════════════════════
 * L5 CANONICAL BASELINE — PROVEN WIN RATES
 * ═══════════════════════════════════════════════════════════════════════
 *
 * Source: L5_CANONICAL_BASELINE.md (locked 2026-03-25)
 * Data: quarantine_12k_l5_trades.csv (7,658 Accumulate signals)
 * Universe: 11,884 symbols, 10,162,966 OHLCV rows, 2021-2026
 *
 * Quarantine backtest (20-day forward hold, no exit logic):
 *   Baseline (Accumulate only):     57.1% WR | 7,290 signals
 *   + Close >= $5:                  57.7% WR | 6,556 signals
 *   + Rising 5d (not falling):      75.0% WR | 3,674 signals
 *   + B_k > -0.80:                  81.1% WR | 2,072 signals
 *   + B_k > -0.50:                  81.4% WR | 2,016 signals
 *
 * L5 Canonical Baseline Layers (from L5_CANONICAL_BASELINE.md):
 *   Layer 1 — Primitive Geometric Eye:
 *     D_k >= 0, Rev_k == 0, B_k > prev_B_k, M_k >= 0
 *   Layer 2 — Common Sense Reality:
 *     Close >= $5, Gate_Count >= 10
 *   Layer 3 — Cognitive Restraint:
 *     raw_x_m <= 0.50, F_n <= 1.65
 *   Result: 3,587 signals, 64.66% WR, 1.25% avg 20d return
 *
 * B_k quartile analysis (7,658 trades):
 *   Q1 [-1.0, -0.998] (compressed): 51.3% WR — coin flip
 *   Q2 [-0.998, -0.671]:            49.6% WR — coin flip
 *   Q3 [-0.671, -0.047]:            63.5% WR — real edge
 *   Q4 [-0.047, -0.025] (expanded): 64.0% WR — real edge
 *
 * ═══════════════════════════════════════════════════════════════════════
 * PRODUCTION VERIFICATION (May 19, 2026)
 * ═══════════════════════════════════════════════════════════════════════
 *
 * 428 real trades verified against Alpaca order API + Polygon historical.
 *
 * CRITICAL FINDING: Entry selection is NOT the problem. Exit timing IS.
 *   Trades held >0 days: 57.4% WR, +$1,280 P&L (matches quarantine 57%)
 *   Day-0 exits:         24.2% WR, -$1,545 P&L (system destroys wins)
 *   175 day-0 losers checked against Polygon 20-day forward:
 *     68% would have been winners. $5,510 left on the table.
 *
 * Day-0 root causes (every sell order verified via Alpaca API):
 *   Sentinel market sells: 113 trades, -$1,512 (SPY flip mass liquidation)
 *   Bracket SL same-day:    61 trades, -$946 (1×ATR too tight for intraday)
 *
 * After EXIT-R7 (day-0 loss protection):
 *   Projected: 67.2% WR, +$5,245 P&L (from -$265)
 *
 * WHY B_k/F_n ENTRY GATES DON'T WORK IN PRODUCTION:
 *   Tested on 428 production trades — every gate made things WORSE.
 *   Rejected pool had HIGHER win rate (48.1%) than passed pool.
 *   Root cause: production CP-2 uses 252-bar cap → F_n inverted,
 *   raw_x_m saturates to 1.0, thresholds from quarantine don't transfer.
 *   The quarantine 81% is real but requires 20-day hold (no exit logic).
 *   Production exits early → the entry filter doesn't matter if exits
 *   are killing positions before they reach 20 days.
 *
 * ═══════════════════════════════════════════════════════════════════════
 *
 * CHANGELOG:
 *   2026-05-19  ENTRY-R1  Red-day filter: 2 consecutive declining closes blocks entry
 *   2026-05-19  ENTRY-R2  Friday block: no new entries Fri/Sat/Sun (weekend gap risk)
 *   2026-05-19  ENTRY-R3  Minimum share price $5 (penny stock filter)
 *   2026-05-19  ENTRY-R4  Minimum 5% bracket width (tight brackets lose at 50%)
 *   2026-05-19  ENTRY-R5  Market cap >= $500M (liquidity floor)
 *   2026-05-19  EXIT-R1   Catastrophic floor: -10% CH2, -1% CH3
 *   2026-05-19  EXIT-R2   Acceleration complete: S_UF >= 0.75
 *   2026-05-19  EXIT-R3   D_k collapse: D_k != 1 after entry
 *   2026-05-19  EXIT-R4   Tau exhaustion: position age > tau_out
 *   2026-05-19  EXIT-R5   Trailing profit: ratcheting floor after 5% gain
 *   2026-05-19  EXIT-R6   Structural harvest: past midpoint with >= 5% gain
 *   2026-05-19  EXIT-R7   Day-0 loss protection: no losing exit on day 0 (67.2% WR recovery)
 *   2026-05-19  SCORE-R1  Admin closures excluded: stale_position_cleanup,
 *                          manual_close_stale, manual_portfolio_reset
 *   2026-05-19  SIZE-R1   CH2 risk per trade: 2.5% of equity ($2,500 on $100K)
 *   2026-05-19  SIZE-R2   ATR stops killed 13/14 winners — use -10% catastrophic only
 *   2026-05-19  SIZE-R3   3WA bracket SL widened from 1×ATR to -10% (matching CH2)
 *   2026-05-20  EXIT-R8   Market hours guard on EXIT-F: stale overnight prices triggered
 *                          false catastrophic exits (BELFB -33.6% phantom, MYE -18.4% phantom)
 *   2026-05-20  SYNC-R1   Orphan adoption cooldown: 15-min kill cooldown prevents
 *                          adopt→kill→adopt loop (AM/BCPC/FOXA each killed 5x)
 *   2026-05-20  SYNC-R2   Phantom cleanup grace: 30-min grace period before declaring
 *                          unfilled orders as phantom (GENB killed at 5min, filled at 43min)
 *   2026-05-20  EXIT-R9   7-day minimum hold: no losing exits before 7 calendar days.
 *                          Supersedes EXIT-R7 (day-0 only). Production data: 85% of D_k
 *                          collapse exits recovered at 10-20 days. 73% of early losers
 *                          (0-3d) were winners at 20d. Projected WR: 67.1%.
 *                          Winning exits (EXIT-A, EXIT-H) always fire. -10% always active.
 */

// ═══════════════════════════════════════════════════════════════════════════
// ENTRY RULES
// ═══════════════════════════════════════════════════════════════════════════

/**
 * ENTRY-R1: Red-day filter
 * If the stock closed lower than the prior day's close for 2 consecutive
 * days, the move is reversing — don't buy into a falling knife.
 *
 * Backtest (28 positions, May 19 2026):
 *   Precision: 90% (9/10 blocks were correct — all losers)
 *   Winners preserved: 86% (6/7 winners allowed through)
 *   Key saves: BELFA -5.1%, DHI -4.6%, PHM -3.5%, DEI -3.4%
 *
 * @param {Array} bars — daily bars, oldest first, must have at least 3
 * @returns {{ blocked: boolean, rule: string, reason?: string }}
 */
export function entryR1_RedDayFilter(bars) {
  const RULE = "ENTRY-R1";

  if (!Array.isArray(bars) || bars.length < 3) {
    return { blocked: false, rule: RULE, reason: "insufficient_bars" };
  }

  const recent = bars.slice(-3);
  const close0 = parseFloat(recent[0].c);
  const close1 = parseFloat(recent[1].c);
  const close2 = parseFloat(recent[2].c);

  if (close1 < close0 && close2 < close1) {
    return {
      blocked: true,
      rule: RULE,
      reason: `2 consecutive declining closes: ${close0}→${close1}→${close2}`,
    };
  }

  return { blocked: false, rule: RULE };
}

/**
 * ENTRY-R2: Friday block
 * No new entries on Friday, Saturday, or Sunday.
 * Weekend gaps are unmanageable — REGN lost 12% over a weekend.
 *
 * @returns {{ blocked: boolean, rule: string, reason?: string }}
 */
export function entryR2_FridayBlock() {
  const RULE = "ENTRY-R2";
  const day = new Date().getUTCDay(); // 0=Sun, 5=Fri, 6=Sat

  if (day === 5 || day === 6 || day === 0) {
    return { blocked: true, rule: RULE, reason: `day=${day} (Fri/Sat/Sun)` };
  }

  return { blocked: false, rule: RULE };
}

/**
 * ENTRY-R3: Minimum share price
 * Reject penny stocks. Below $5 = too volatile, wide spreads.
 *
 * @param {number} price — current share price
 * @returns {{ blocked: boolean, rule: string, reason?: string }}
 */
export function entryR3_MinSharePrice(price) {
  const RULE = "ENTRY-R3";
  const MIN_PRICE = 5.0;

  if (price < MIN_PRICE) {
    return { blocked: true, rule: RULE, reason: `${price} < ${MIN_PRICE}` };
  }

  return { blocked: false, rule: RULE };
}

/**
 * ENTRY-R4: Minimum bracket width
 * TP must be at least 5% above entry. Tight brackets on cheap stocks
 * get stopped out prematurely.
 *
 * Backtest: <5% brackets won at 50%, 5-15% brackets won at 80%.
 *
 * @param {number} entryPrice
 * @param {number} takeProfitPrice
 * @returns {{ blocked: boolean, rule: string, reason?: string }}
 */
export function entryR4_MinBracketWidth(entryPrice, takeProfitPrice) {
  const RULE = "ENTRY-R4";
  const MIN_PCT = 0.05;
  const bracketPct = (takeProfitPrice - entryPrice) / entryPrice;

  if (bracketPct < MIN_PCT) {
    return {
      blocked: true,
      rule: RULE,
      reason: `bracket ${(bracketPct * 100).toFixed(1)}% < ${MIN_PCT * 100}% minimum`,
    };
  }

  return { blocked: false, rule: RULE };
}

/**
 * ENTRY-R5: Market cap floor
 * $500M minimum — illiquid stocks get wide spreads and phantom fills.
 *
 * @param {number} marketCap
 * @returns {{ blocked: boolean, rule: string, reason?: string }}
 */
export function entryR5_MarketCapFloor(marketCap) {
  const RULE = "ENTRY-R5";
  const MIN_CAP = 500_000_000;

  if (marketCap < MIN_CAP) {
    return { blocked: true, rule: RULE, reason: `${marketCap} < $500M` };
  }

  return { blocked: false, rule: RULE };
}


// ═══════════════════════════════════════════════════════════════════════════
// EXIT RULES
// ═══════════════════════════════════════════════════════════════════════════

/**
 * EXIT-R1: Catastrophic floor
 * Hard stop at -10% for CH2, -1% for CH3. Not noise — only disaster.
 * ATR-based stops killed 13/14 winners. This is insurance, not strategy.
 *
 * @param {number} entryPrice
 * @param {number} currentPrice
 * @param {string} signalClass — "CH2" or "CH3"
 * @returns {{ triggered: boolean, rule: string, lossPct?: number }}
 */
export function exitR1_CatastrophicFloor(entryPrice, currentPrice, signalClass) {
  const RULE = "EXIT-R1";
  const threshold = signalClass === "CH3" ? -0.01 : -0.10;
  const lossPct = (currentPrice - entryPrice) / entryPrice;

  if (lossPct <= threshold) {
    return { triggered: true, rule: RULE, lossPct };
  }

  return { triggered: false, rule: RULE, lossPct };
}


/**
 * EXIT-R7: Day-0 loss protection
 * No LOSING exit on day 0. The structural thesis needs at least 1 full
 * trading day to manifest. Intraday noise kills winners.
 *
 * Production backtest (428 trades, Polygon verified):
 *   175 day-0 losses → 68% would have been winners at 20 days.
 *   Blocking day-0 losses recovers $5,510 and raises WR from 39.5% to 67.2%.
 *
 * What's BLOCKED on day 0:
 *   - Sentinel structural exits (D_k collapse, SPY flip) if position is underwater
 *   - Bracket SL legs (3WA SL widened to -10% to prevent same-day triggers)
 *
 * What's ALLOWED on day 0:
 *   - Winning exits (take-profit, acceleration complete, energy harvest)
 *   - -10% catastrophic floor (disaster insurance, always active)
 *   - CH3 harvest (scalp channel — profit is the signal to exit)
 *
 * Implementation: sentinel_monitor.mjs checks posAge and currentPnlPct
 * before each structural exit. If posAge < 1 day AND P&L < 0, exit is
 * deferred to day 1+.
 *
 * @param {number} posAgeDays — days since entry fill
 * @param {number} currentPnlPct — current P&L percentage
 * @param {boolean} isWinningExit — is this a take-profit / harvest exit?
 * @returns {{ blocked: boolean, rule: string, reason?: string }}
 */
export function exitR7_Day0LossProtection(posAgeDays, currentPnlPct, isWinningExit = false) {
  const RULE = "EXIT-R7";

  // Winning exits always allowed
  if (isWinningExit || currentPnlPct >= 0) {
    return { blocked: false, rule: RULE };
  }

  // Day 0 + underwater = blocked
  if (posAgeDays < 1 && currentPnlPct < 0) {
    return {
      blocked: true,
      rule: RULE,
      reason: `day-0 loss guard: age=${posAgeDays}d P&L=${currentPnlPct.toFixed(1)}%`,
    };
  }

  return { blocked: false, rule: RULE };
}


// ═══════════════════════════════════════════════════════════════════════════
// SCORING RULES
// ═══════════════════════════════════════════════════════════════════════════

/**
 * SCORE-R1: Admin closure exclusion
 * These exit reasons are administrative, not strategy outcomes.
 * Excluded from win/loss rate and expectancy calculations.
 */
export const ADMIN_EXIT_REASONS = [
  "stale_position_cleanup",
  "manual_close_stale",
  "manual_portfolio_reset",
];

/**
 * Check if an exit reason is an admin closure (excluded from scoring).
 *
 * @param {string} exitReason
 * @returns {boolean}
 */
export function isAdminClosure(exitReason) {
  return ADMIN_EXIT_REASONS.includes(exitReason);
}


// ═══════════════════════════════════════════════════════════════════════════
// SIZING RULES
// ═══════════════════════════════════════════════════════════════════════════

/**
 * SIZE-R1: CH2 position sizing
 * 2.5% of vault equity per trade.
 * Backtest (85 trades): win/loss ratio 1.91:1.
 * At 2.5% same trades produce $4,413 P&L vs $1,633 at 0.917%.
 */
export const CH2_RISK_PCT = 2.5;

/**
 * SIZE-R2: Stop loss method
 * -10% catastrophic only. ATR stops killed 13/14 winners.
 * The bracket SL is insurance against disaster, not a trading strategy.
 * Structural exits (acceleration, D_k collapse, tau, harvest) handle
 * normal profit-taking and loss-cutting.
 */
export const CH2_STOP_LOSS_PCT = 0.10;
