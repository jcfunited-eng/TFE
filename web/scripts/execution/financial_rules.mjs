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
 * CHANGELOG:
 *   2026-05-19  ENTRY-R1  Red-day filter: 2 consecutive declining closes blocks entry
 *   2026-05-19  ENTRY-R2  Friday block: no new entries Fri/Sat/Sun (weekend gap risk)
 *   2026-05-19  ENTRY-R3  Minimum share price $5 (penny stock filter)
 *   2026-05-19  ENTRY-R4  Minimum 5% bracket width (tight brackets lose at 50%)
 *   2026-05-19  ENTRY-R5  Market cap >= $500M (liquidity floor)
 *   2026-05-19  ENTRY-R6  B_k > -0.80: boundary not deeply compressed (81.1% WR backtest)
 *   2026-05-19  ENTRY-R7  F_n > 1.65: structural energy available (70.1% WR prod-calibrated)
 *   2026-05-19  EXIT-R1   Catastrophic floor: -10% CH2, -1% CH3
 *   2026-05-19  EXIT-R2   Acceleration complete: S_UF >= 0.75
 *   2026-05-19  EXIT-R3   D_k collapse: D_k != 1 after entry
 *   2026-05-19  EXIT-R4   Tau exhaustion: position age > tau_out
 *   2026-05-19  EXIT-R5   Trailing profit: ratcheting floor after 5% gain
 *   2026-05-19  EXIT-R6   Structural harvest: past midpoint with >= 5% gain
 *   2026-05-19  SCORE-R1  Admin closures excluded: stale_position_cleanup,
 *                          manual_close_stale, manual_portfolio_reset
 *   2026-05-19  SIZE-R1   CH2 risk per trade: 2.5% of equity ($2,500 on $100K)
 *   2026-05-19  SIZE-R2   ATR stops killed 13/14 winners — use -10% catastrophic only
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


/**
 * ENTRY-R6: Boundary expansion gate (B_k > -0.80)
 * B_k measures the structural boundary position from the coupled L4 field.
 * B_k is always negative for Accumulate signals (range [-1.0, -0.025]).
 * Closer to zero = more expanded = more structural room to move.
 * Deeply negative = compressed = coin flip territory.
 *
 * Backtest (7658 trades):
 *   B_k > -0.80 + rising: 81.1% WR (2072 trades)
 *   B_k <= -0.80:         50.5% WR (random)
 *   Delta: +30.6% win rate
 *
 * @param {number|null} bk — B_k from snapshot_row_json
 * @returns {{ blocked: boolean, rule: string, reason?: string }}
 */
export function entryR6_BoundaryExpansion(bk) {
  const RULE = "ENTRY-R6";
  const B_K_MIN = -0.80;

  if (bk === null || bk === undefined) {
    return { blocked: false, rule: RULE, reason: "no_bk_data" };
  }

  if (bk <= B_K_MIN) {
    return { blocked: true, rule: RULE, reason: `B_k=${bk.toFixed(4)} <= ${B_K_MIN} (boundary compressed)` };
  }

  return { blocked: false, rule: RULE };
}

/**
 * ENTRY-R7: Structural energy gate (F_n > 1.65, production-calibrated)
 * F_n measures free structural energy from the coupled L4 cognitive kernel.
 *
 * CRITICAL: Production F_n is INVERTED from quarantine F_n.
 * - Quarantine (full history): F_n <= 1.65 was the good zone
 * - Production (252-bar cap): F_n > 1.65 is the good zone
 * The CV-1.0 integrators saturate differently with the bar cap.
 * Higher F_n in production = more surprise = more energy available to harvest.
 *
 * Backtest (580 trades, production kernel):
 *   F_n > 1.65: 70.1% WR (174 trades)
 *   F_n > 1.72: 77.6% WR (116 trades)
 *   F_n <= 1.65: 49.5% WR (random)
 *
 * @param {number|null} fn — F_n from snapshot_row_json
 * @returns {{ blocked: boolean, rule: string, reason?: string }}
 */
export function entryR7_StructuralEnergy(fn) {
  const RULE = "ENTRY-R7";
  const F_N_MIN = 1.65;

  if (fn === null || fn === undefined) {
    return { blocked: false, rule: RULE, reason: "no_fn_data" };
  }

  if (fn <= F_N_MIN) {
    return { blocked: true, rule: RULE, reason: `F_n=${fn.toFixed(3)} <= ${F_N_MIN} (low structural energy)` };
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
