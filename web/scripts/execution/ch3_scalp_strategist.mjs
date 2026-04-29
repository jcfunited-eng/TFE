/**
 * web/scripts/execution/ch3_scalp_strategist.mjs
 * PEE-1 Chapter 3 Strategist — "Smash and Grab" Scalp Channel
 *
 * High-conviction, concentrated, fast-exit trades.
 * Uses EXISTING kernel signals (S_UF from runtime_decisions_latest).
 * The kernel is NOT modified — this is a new execution path only.
 *
 * Entry conditions (ALL must be true):
 *   1. S_UF >= 0.70          — high conviction (all market regimes)
 *   2. bar_count > 20        — established stock
 *   3. Pool has funds remaining (daily pool not depleted)
 *   4. No existing CH3 position open (one at a time)
 *   5. Daily loss limit not hit
 *
 * Exit conditions (evaluated by sentinel_monitor per signal_class='CH3'):
 *   EXIT PROFIT — price >= entry + 1.0 × ATR-14  → market sell (take profit)
 *   EXIT STOP   — price <= entry - 0.5 × ATR-14  → market sell (stop loss)
 *   EXIT TIME   — position age > 4 hours          → market sell (time limit)
 *
 * Pool rules:
 *   - $5,000 scalp pool (configurable)
 *   - Max $2,500 per scalp position
 *   - Daily loss limit: $1,000 (stop trading for the day)
 *   - Wins sweep to cash immediately (pool stays fixed)
 *   - Pool depletes on losses; refilled manually or from CH2 profits
 *
 * Position sizing:
 *   - $2,500 per trade OR pool remainder, whichever is less
 *   - shares = floor(trade_amount / current_price)
 */

import pg from "pg";

const pool = new pg.Pool({
  host:     process.env.PGHOST,
  port:     parseInt(process.env.PGPORT ?? "5432", 10),
  database: process.env.PGDATABASE,
  user:     process.env.PGUSER,
  password: process.env.PGPASSWORD,
  max: 3,
  idleTimeoutMillis: 30_000,
  connectionTimeoutMillis: 5_000,
  ssl: { rejectUnauthorized: false },
});

// ── CH3 thresholds ───────────────────────────────────────────────────────
const CH3_S_UF_MIN         = 0.70;    // high conviction entry
const CH3_REQUIRED_DK      = null;    // ANY D_k — works in all regimes
const CH3_BAR_COUNT_MIN    = 21;      // established stocks only
const CH3_POOL_TOTAL       = 5000;    // total CH3 pool $
const CH3_MAX_PER_TRADE    = 2500;    // max $ per trade
// Stops are ATR-based, computed per-trade in alpaca_bridge:
//   Take profit: entry + 1.0 × ATR-14
//   Stop loss:   entry - 0.5 × ATR-14
// NO TIME LIMIT — hold until bracket resolves (TP or SL).
// The structural move plays out on its own timeline.
// One position at a time — don't stack until current resolves.
const CH3_TIME_LIMIT_HOURS = null;    // REMOVED — bracket decides, not a clock
const CH3_DAILY_LOSS_LIMIT = 1000;    // stop after $1K daily loss

function toFloat(v) {
  const n = parseFloat(v);
  return isFinite(n) ? n : null;
}
function toInt(v) {
  const n = parseInt(v, 10);
  return isFinite(n) ? n : null;
}

/**
 * Get today's CH3 P&L — sum of all closed CH3 trades today.
 * Used to enforce daily loss limit.
 */
async function getTodayCh3PL() {
  const res = await pool.query(
    `SELECT COALESCE(SUM(p_l), 0) AS total_pl
     FROM personal_trade_ledger
     WHERE signal_class = 'CH3'
       AND status = 'closed'
       AND exit_filled_at >= CURRENT_DATE`
  );
  return parseFloat(res.rows[0]?.total_pl ?? "0");
}

/**
 * Get remaining CH3 pool — total pool minus unrealized losses on closed CH3 trades.
 */
async function getCh3PoolRemaining() {
  const res = await pool.query(
    `SELECT COALESCE(SUM(CASE WHEN p_l < 0 THEN p_l ELSE 0 END), 0) AS total_losses
     FROM personal_trade_ledger
     WHERE signal_class = 'CH3'
       AND status = 'closed'`
  );
  const totalLosses = Math.abs(parseFloat(res.rows[0]?.total_losses ?? "0"));
  return Math.max(0, CH3_POOL_TOTAL - totalLosses);
}

/**
 * Check if there's already an open CH3 position (one at a time).
 */
async function hasOpenCh3Position() {
  const res = await pool.query(
    `SELECT COUNT(*) AS cnt FROM personal_trade_ledger
     WHERE signal_class = 'CH3' AND status IN ('submitted', 'filled')`
  );
  return parseInt(res.rows[0]?.cnt ?? "0", 10) > 0;
}

/**
 * Fetch tickers that already have open positions (any channel).
 */
async function fetchOpenPositionTickers() {
  const res = await pool.query(
    `SELECT DISTINCT UPPER(TRIM(ticker)) AS ticker
     FROM personal_trade_ledger
     WHERE status IN ('submitted', 'filled')`
  );
  return new Set(res.rows.map(r => r.ticker));
}

/**
 * Fetch tickers that CH3 already traded today (win or loss).
 * No same-day re-entry — avoid chasing the same stock twice.
 */
async function fetchTodayCh3Tickers() {
  const res = await pool.query(
    `SELECT DISTINCT UPPER(TRIM(ticker)) AS ticker
     FROM personal_trade_ledger
     WHERE signal_class = 'CH3'
       AND signal_detected_at >= CURRENT_DATE`
  );
  return new Set(res.rows.map(r => r.ticker));
}

/**
 * Fetch all CH3 candidate rows — highest S_UF signals.
 */
async function fetchCandidateRows() {
  // Full structural selection: high conviction, expanding, no reversal, free to move
  const res = await pool.query(
    `SELECT
       r.ticker,
       r.run_id,
       r.decision_label,
       r.snapshot_row_json,
       COALESCE(f.sector, 'Unknown') AS sector
     FROM runtime_decisions_latest r
     LEFT JOIN l5_fundamentals_normalized f ON f.ticker = r.ticker
     WHERE r.decision_label = 'Accumulate'
       AND r.ticker != 'SPY'
       AND CAST(NULLIF(r.snapshot_row_json->>'bar_count', '') AS INTEGER) > $1
       AND CAST(NULLIF(r.snapshot_row_json->>'S_UF', '') AS DOUBLE PRECISION) >= $2
       AND CAST(NULLIF(r.snapshot_row_json->>'D_k', '') AS DOUBLE PRECISION) = 1
       AND CAST(NULLIF(r.snapshot_row_json->>'R_rev_k', '') AS DOUBLE PRECISION) = 0
       AND ABS(CAST(NULLIF(r.snapshot_row_json->>'B_k', '') AS DOUBLE PRECISION)) < 0.8
     ORDER BY CAST(NULLIF(r.snapshot_row_json->>'S_UF', '') AS DOUBLE PRECISION) DESC
     LIMIT 20`,
    [CH3_BAR_COUNT_MIN - 1, CH3_S_UF_MIN]
  );
  return res.rows;
}

/**
 * Parse a candidate row into a CH3 signal.
 */
function parseSignal(row) {
  const snap     = row.snapshot_row_json ?? {};
  const ticker   = String(row.ticker ?? "").trim().toUpperCase();
  const runId    = String(row.run_id ?? "").trim();
  const barCount = toInt(snap.bar_count);
  const sUf      = toFloat(snap.S_UF ?? snap.s_uf);
  const dk       = toInt(snap.D_k ?? snap.d_k);
  const bk       = toFloat(snap.B_k ?? snap.b_k);
  const mk       = toFloat(snap.M_k ?? snap.m_k);
  const sector   = String(row.sector ?? "").trim();

  if (!ticker) return null;
  if (sUf === null || sUf < CH3_S_UF_MIN) return null;
  if (dk !== 1) return null;  // must be expanding
  if (barCount === null || barCount < CH3_BAR_COUNT_MIN) return null;

  // G32 epoch sector filter — skip ADVERSE sectors
  let epochStatus = "UNKNOWN";
  try {
    const fs = require("fs");
    const g32Raw = fs.readFileSync("/app/g32_state.json", "utf-8");
    const g32 = JSON.parse(g32Raw);
    if (g32?.xi && sector) {
      const COUPLING = {
        "Energy": {RATES_PRESSURE:0,CONSUMER_STRESS:-0.2,WAR_GEOPOLITICS:0.9,ENERGY_COMMODITY:0.9,TECH_CYCLE:0,CURRENCY_FX:0.3,FISCAL_INFRA:0.2,VOLATILITY_REGIME:0.1},
        "Technology": {RATES_PRESSURE:-0.4,CONSUMER_STRESS:-0.3,WAR_GEOPOLITICS:0,ENERGY_COMMODITY:-0.1,TECH_CYCLE:-0.5,CURRENCY_FX:-0.2,FISCAL_INFRA:0.1,VOLATILITY_REGIME:-0.3},
        "Financial Services": {RATES_PRESSURE:0.2,CONSUMER_STRESS:-0.5,WAR_GEOPOLITICS:-0.2,ENERGY_COMMODITY:0,TECH_CYCLE:-0.1,CURRENCY_FX:0.1,FISCAL_INFRA:0.1,VOLATILITY_REGIME:-0.4},
        "Healthcare": {RATES_PRESSURE:0,CONSUMER_STRESS:0.3,WAR_GEOPOLITICS:0.1,ENERGY_COMMODITY:-0.1,TECH_CYCLE:0.1,CURRENCY_FX:-0.1,FISCAL_INFRA:0.1,VOLATILITY_REGIME:0.1},
        "Real Estate": {RATES_PRESSURE:-1.0,CONSUMER_STRESS:-0.5,WAR_GEOPOLITICS:0,ENERGY_COMMODITY:-0.1,TECH_CYCLE:0,CURRENCY_FX:-0.1,FISCAL_INFRA:0.1,VOLATILITY_REGIME:-0.3},
        "Consumer Discretionary": {RATES_PRESSURE:-0.5,CONSUMER_STRESS:-1.0,WAR_GEOPOLITICS:-0.2,ENERGY_COMMODITY:-0.4,TECH_CYCLE:-0.1,CURRENCY_FX:-0.2,FISCAL_INFRA:0.1,VOLATILITY_REGIME:-0.5},
      };
      const c = COUPLING[sector];
      if (c) {
        let pressure = 0;
        for (const [ch, w] of Object.entries(c)) pressure += (g32.xi[ch] ?? 0) * w;
        epochStatus = pressure <= -0.5 ? "ADVERSE" : pressure > 0.3 ? "TAILWIND" : "NEUTRAL";
      }
    }
  } catch {}

  if (epochStatus === "ADVERSE") {
    console.log(`[CH3-SCALP]   ${ticker} — skipped (sector ${sector} ADVERSE epoch pressure)`);
    return null;
  }

  return {
    ticker,
    run_id:       runId,
    signal_class: "CH3",
    s_uf:         sUf,
    d_k:          dk,
    b_k:          bk,
    m_k:          mk,
    bar_count:    barCount,
    sector:       sector,
    epoch_status: epochStatus,
  };
}

/**
 * Main entry point — returns at most ONE CH3 signal (best candidate).
 */
export async function getCh3Signals() {
  console.log(`[CH3-SCALP] Structural hunter scanning...`);

  // Gate 1: daily loss limit
  const todayPL = await getTodayCh3PL();
  if (todayPL <= -CH3_DAILY_LOSS_LIMIT) {
    console.log(`[CH3-SCALP] HALTED — daily loss limit hit ($${todayPL.toFixed(2)} today)`);
    return [];
  }

  // Gate 2: pool remaining
  const poolRemaining = await getCh3PoolRemaining();
  if (poolRemaining <= 0) {
    console.log(`[CH3-SCALP] HALTED — scalp pool depleted ($${poolRemaining.toFixed(2)} remaining)`);
    return [];
  }

  // Gate 3: check invested amount in open CH3 positions
  const ch3InvestedRes = await pool.query(`
    SELECT COALESCE(SUM(CAST(dollar_allocation AS NUMERIC)), 0) AS invested
    FROM personal_trade_ledger
    WHERE signal_class = 'CH3' AND status IN ('submitted', 'filled')
  `);
  const ch3Invested = parseFloat(ch3InvestedRes.rows[0]?.invested ?? "0");
  const availablePool = Math.max(0, poolRemaining - ch3Invested);

  if (availablePool < 500) {
    console.log(`[CH3-SCALP] SKIP — pool fully allocated ($${availablePool.toFixed(0)} available, $${ch3Invested.toFixed(0)} invested)`);
    return [];
  }

  // Fetch candidates
  const rows = await fetchCandidateRows();
  const signals = rows.map(parseSignal).filter(Boolean);

  // Exclude tickers with existing positions (any channel) or already traded today by CH3
  const openTickers = await fetchOpenPositionTickers();
  const todayCh3Tickers = await fetchTodayCh3Tickers();
  const available = signals.filter(s => {
    if (openTickers.has(s.ticker)) {
      return false;
    }
    if (todayCh3Tickers.has(s.ticker)) {
      return false;
    }
    return true;
  });

  if (available.length === 0) {
    console.log(`[CH3-SCALP] No candidates found (need S_UF >= ${CH3_S_UF_MIN})`);
    return [];
  }

  // Pool-limited multi-position: divide available pool among candidates
  // Max per trade caps each position, pool caps total exposure
  const maxPositions = Math.floor(availablePool / 500);  // minimum $500 per position
  const candidates = available.slice(0, Math.min(available.length, maxPositions));
  const perTradeAmount = Math.min(CH3_MAX_PER_TRADE, Math.floor(availablePool / candidates.length));

  console.log(`[CH3-SCALP] ${candidates.length} candidate(s) | pool=$${availablePool.toFixed(0)} | per_trade=$${perTradeAmount}`);

  for (const sig of candidates) {
    sig.ch3_trade_amount = perTradeAmount;
    console.log(`[CH3-SCALP] SIGNAL: ${sig.ticker} | S_UF=${sig.s_uf} | D_k=${sig.d_k} | $${perTradeAmount}`);
  }

  // Return all candidates (PEE-1 runner will execute each)
  const best = candidates[0];
  best.ch3_trade_amount = perTradeAmount;

  return [best];
}

/**
 * CH3 config — exported for sentinel to use.
 */
export const CH3_CONFIG = {
  TIME_LIMIT_HOURS: null,  // no time limit — bracket decides
  DAILY_LOSS_LIMIT: CH3_DAILY_LOSS_LIMIT,
};

export async function closeCh3StrategistPool() {
  await pool.end();
}
