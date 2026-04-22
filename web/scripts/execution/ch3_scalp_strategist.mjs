/**
 * web/scripts/execution/ch3_scalp_strategist.mjs
 * PEE-1 Chapter 3 Strategist — "Smash and Grab" Scalp Channel
 *
 * High-conviction, concentrated, fast-exit trades.
 * Uses EXISTING kernel signals (S_UF from runtime_decisions_latest).
 * The kernel is NOT modified — this is a new execution path only.
 *
 * Entry conditions (ALL must be true):
 *   1. S_UF >= 0.70          — high conviction (near acceleration complete)
 *   2. D_k = 1               — directional expansion confirmed
 *   3. bar_count > 20        — established stock
 *   4. Pool has funds remaining (daily pool not depleted)
 *   5. No existing CH3 position open (one at a time)
 *   6. Daily loss limit not hit
 *
 * Exit conditions (evaluated by sentinel_monitor per signal_class='CH3'):
 *   EXIT PROFIT — price >= entry + 1.0%  → market sell (take profit)
 *   EXIT STOP   — price <= entry - 0.5%  → market sell (stop loss)
 *   EXIT TIME   — position age > 4 hours → market sell (time limit)
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

// ── CH3 Scalp thresholds ─────────────────────────────────────────────────
const CH3_S_UF_MIN         = 0.70;    // high conviction entry
const CH3_REQUIRED_DK      = 1;       // directional expansion required
const CH3_BAR_COUNT_MIN    = 21;      // established stocks only
const CH3_POOL_TOTAL       = 5000;    // total scalp pool $
const CH3_MAX_PER_TRADE    = 2500;    // max $ per scalp
const CH3_TAKE_PROFIT_PCT  = 0.01;    // +1.0% take profit
const CH3_STOP_LOSS_PCT    = 0.005;   // -0.5% stop loss
const CH3_TIME_LIMIT_HOURS = 4;       // close after 4 hours
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
 * Fetch all CH3 candidate rows — highest S_UF signals.
 */
async function fetchCandidateRows() {
  const res = await pool.query(
    `SELECT
       ticker,
       run_id,
       decision_label,
       snapshot_row_json
     FROM runtime_decisions_latest
     WHERE decision_label = 'Accumulate'
       AND ticker != 'SPY'
       AND CAST(NULLIF(snapshot_row_json->>'bar_count', '') AS INTEGER) > $1
       AND CAST(NULLIF(snapshot_row_json->>'S_UF', '') AS DOUBLE PRECISION) >= $2
       AND CAST(NULLIF(snapshot_row_json->>'D_k', '') AS INTEGER) = $3
     ORDER BY CAST(NULLIF(snapshot_row_json->>'S_UF', '') AS DOUBLE PRECISION) DESC
     LIMIT 10`,
    [CH3_BAR_COUNT_MIN - 1, CH3_S_UF_MIN, CH3_REQUIRED_DK]
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

  if (!ticker) return null;
  if (sUf === null || sUf < CH3_S_UF_MIN) return null;
  if (dk !== CH3_REQUIRED_DK) return null;
  if (barCount === null || barCount < CH3_BAR_COUNT_MIN) return null;

  return {
    ticker,
    run_id:       runId,
    signal_class: "CH3",
    s_uf:         sUf,
    d_k:          dk,
    bar_count:    barCount,
  };
}

/**
 * Main entry point — returns at most ONE CH3 signal (best candidate).
 */
export async function getCh3Signals() {
  console.log(`[CH3-SCALP] Scanning for high-conviction scalp candidates...`);

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

  // Gate 3: one at a time
  const hasOpen = await hasOpenCh3Position();
  if (hasOpen) {
    console.log(`[CH3-SCALP] SKIP — CH3 position already open`);
    return [];
  }

  // Fetch candidates
  const rows = await fetchCandidateRows();
  const signals = rows.map(parseSignal).filter(Boolean);

  // Exclude tickers with existing positions (any channel)
  const openTickers = await fetchOpenPositionTickers();
  const available = signals.filter(s => {
    if (openTickers.has(s.ticker)) {
      console.log(`[CH3-SCALP]   ${s.ticker} — SKIPPED (position exists in another channel)`);
      return false;
    }
    return true;
  });

  if (available.length === 0) {
    console.log(`[CH3-SCALP] No candidates found (need S_UF >= ${CH3_S_UF_MIN}, D_k = ${CH3_REQUIRED_DK})`);
    return [];
  }

  // Pick the BEST one (highest S_UF)
  const best = available[0];
  const tradeAmount = Math.min(CH3_MAX_PER_TRADE, poolRemaining);

  console.log(`[CH3-SCALP] SIGNAL: ${best.ticker} | S_UF=${best.s_uf} | D_k=${best.d_k} | pool=$${poolRemaining.toFixed(0)} | trade=$${tradeAmount.toFixed(0)}`);

  // Override the sizing — CH3 uses fixed dollar amount, not percentage
  best.ch3_trade_amount = tradeAmount;
  best.ch3_take_profit_pct = CH3_TAKE_PROFIT_PCT;
  best.ch3_stop_loss_pct = CH3_STOP_LOSS_PCT;

  return [best];
}

/**
 * CH3 exit thresholds — exported for sentinel to use.
 */
export const CH3_CONFIG = {
  TAKE_PROFIT_PCT:  CH3_TAKE_PROFIT_PCT,
  STOP_LOSS_PCT:    CH3_STOP_LOSS_PCT,
  TIME_LIMIT_HOURS: CH3_TIME_LIMIT_HOURS,
  DAILY_LOSS_LIMIT: CH3_DAILY_LOSS_LIMIT,
};

export async function closeCh3StrategistPool() {
  await pool.end();
}
