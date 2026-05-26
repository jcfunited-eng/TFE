/**
 * web/scripts/execution/ch3_scalp_strategist.mjs
 * PEE-1 Chapter 3 — Accumulate Quick Grab
 *
 * Rapid in-and-out cash grabs on Accumulate stocks.
 * The kernel's coupled decision IS the filter — no individual field gates.
 * Grab 3%, stop 1.5%. Rapid fire, all day, every day.
 *
 * Selection (ALL must be true):
 *   1. decision_label = 'Accumulate'  — kernel says good stock
 *   2. bar_count > 20                 — established stock
 *   3. No existing position on this ticker (any channel)
 *   4. Not already traded today by CH3
 *   5. No loss on this ticker in last 7 days
 *   6. Pool has funds remaining
 *   7. Daily loss limit not hit
 *   8. Epoch sector not ADVERSE
 *
 * Exit:
 *   TAKE PROFIT: entry × 1.03  (+3% grab)
 *   STOP LOSS:   entry × 0.985 (-1.5% cut fast, EXIT-F backs this up)
 *
 * Pool: $5K total, $2.5K per trade, $1K daily loss limit
 */

import pg from "pg";
import { readFileSync } from "fs";

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

// ── CH3 Selection & Exit Constants ──────────────────────────────────────
const CH3_BAR_COUNT_MIN    = 21;     // established stocks only

// Pool & risk
const CH3_POOL_TOTAL       = 5000;
const CH3_MAX_PER_TRADE    = 2500;
const CH3_DAILY_LOSS_LIMIT = 1000;

// Exit: +3% grab, -1.5% cut. Asymmetric — wins are 2x losses.
// Backtested PF=2.31 on Accumulate D_k=-1 entries.
const CH3_STOP_LOSS_PCT    = 0.01;   // 1% below entry — cut fast
const CH3_TAKE_PROFIT_PCT  = 0.015;  // 1.5% above entry — matches actual daily range

function toFloat(v) {
  const n = parseFloat(v);
  return isFinite(n) ? n : null;
}


// ── Pool & risk management ──────────────────────────────────────────────

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

async function fetchOpenPositionTickers() {
  const res = await pool.query(
    `SELECT DISTINCT UPPER(TRIM(ticker)) AS ticker
     FROM personal_trade_ledger
     WHERE status IN ('submitted', 'filled')`
  );
  return new Set(res.rows.map(r => r.ticker));
}

async function fetchTodayCh3Tickers() {
  const res = await pool.query(
    `SELECT DISTINCT UPPER(TRIM(ticker)) AS ticker
     FROM personal_trade_ledger
     WHERE signal_class = 'CH3'
       AND signal_detected_at >= CURRENT_DATE`
  );
  return new Set(res.rows.map(r => r.ticker));
}

async function fetchRecentCh3Losers() {
  const res = await pool.query(
    `SELECT DISTINCT UPPER(TRIM(ticker)) AS ticker
     FROM personal_trade_ledger
     WHERE signal_class = 'CH3'
       AND status = 'closed'
       AND COALESCE(p_l, 0) < 0
       AND updated_at >= NOW() - INTERVAL '7 days'`
  );
  return new Set(res.rows.map(r => r.ticker));
}

// ── Candidate selection ─────────────────────────────────────────────────

/**
 * Fetch all Accumulate stocks with structural history.
 * The kernel's coupled decision is the filter. No D_k gate.
 * Sorted by S_UF so highest structural stability picks first.
 */
async function fetchCandidateRows() {
  const res = await pool.query(
    `SELECT
       r.ticker,
       r.run_id,
       r.decision_label,
       r.snapshot_row_json,
       COALESCE(f.sector, 'Unknown') AS sector
     FROM runtime_decisions_latest r
     LEFT JOIN l5_fundamentals_normalized f ON f.ticker = r.ticker
     WHERE r.ticker != 'SPY'
       AND r.ticker NOT LIKE 'I:%'
       AND r.ticker NOT LIKE 'X:%'
       AND r.decision_label = 'Accumulate'
       AND CAST(NULLIF(r.snapshot_row_json->>'bar_count', '') AS INTEGER) > $1
     ORDER BY CAST(NULLIF(r.snapshot_row_json->>'S_UF', '') AS DOUBLE PRECISION) DESC
     LIMIT 50`,
    [CH3_BAR_COUNT_MIN - 1]
  );
  return res.rows;
}

/**
 * Parse and score a candidate row.
 */
function parseSignal(row) {
  const snap     = row.snapshot_row_json ?? {};
  const ticker   = String(row.ticker ?? "").trim().toUpperCase();
  const runId    = String(row.run_id ?? "").trim();
  const barCount = parseInt(snap.bar_count, 10);
  const price    = toFloat(snap.price);
  const sector   = String(row.sector ?? "").trim();

  if (!ticker || !runId) return null;
  if (!isFinite(barCount) || barCount < CH3_BAR_COUNT_MIN) return null;
  if (price === null || price < 1) return null;

  // L5 epoch governance — use pre-computed sector pressures from G32
  let epochPressure = 0;
  let epochStatus = "NEUTRAL";
  try {
    const g32Raw = readFileSync("/app/g32_state.json", "utf-8");
    const g32 = JSON.parse(g32Raw);
    const sectorPressures = g32.sector_pressures ?? {};
    epochPressure = sectorPressures[sector] ?? 0;
    epochStatus = epochPressure <= -0.5 ? "ADVERSE" : epochPressure > 0.3 ? "TAILWIND" : "NEUTRAL";
  } catch {}

  if (epochStatus === "ADVERSE") {
    console.log(`[CH3-HUNTER]   ${ticker} — skipped (sector ${sector} ADVERSE pressure=${epochPressure.toFixed(2)})`);
    return null;
  }

  return {
    ticker,
    run_id:       runId,
    signal_class: "CH3",
    s_uf:         toFloat(snap.S_UF),
    d_k:          toFloat(snap.D_k),
    b_k:          toFloat(snap.B_k),
    bar_count:    barCount,
    price:        price,
    sector:       sector,
    epoch_status: epochStatus,
    epoch_pressure: epochPressure,
    ch3_stop_loss_pct:    CH3_STOP_LOSS_PCT,
    ch3_take_profit_pct:  CH3_TAKE_PROFIT_PCT,
  };
}

// ── Main entry point ────────────────────────────────────────────────────

export async function getCh3Signals() {
  console.log(`[CH3-HUNTER] Structural spike hunter scanning...`);

  // Gate 0: market hours + holiday check — don't submit orders when market is closed
  const now = new Date();
  const utcHour = now.getUTCHours();
  const utcMinute = now.getUTCMinutes();
  const utcTime = utcHour * 60 + utcMinute;
  // Market hours: 13:30-20:00 UTC (9:30 AM - 4:00 PM ET)
  if (utcTime < 13 * 60 + 30 || utcTime >= 20 * 60) {
    console.log(`[CH3-HUNTER] SKIP — market closed (${utcHour}:${String(utcMinute).padStart(2,'0')} UTC)`);
    return [];
  }
  // Holiday check — computed, works for any year
  try {
    const { isMarketHoliday, getHolidayName } = await import("./market_calendar.mjs");
    if (isMarketHoliday(now)) {
      console.log(`[CH3-HUNTER] SKIP — ${getHolidayName(now) ?? "market holiday"}`);
      return [];
    }
  } catch {}

  // Gate 1: daily loss limit
  const todayPL = await getTodayCh3PL();
  if (todayPL <= -CH3_DAILY_LOSS_LIMIT) {
    console.log(`[CH3-HUNTER] HALTED — daily loss limit hit ($${todayPL.toFixed(2)} today)`);
    return [];
  }

  // Gate 2: pool remaining
  const poolRemaining = await getCh3PoolRemaining();
  if (poolRemaining <= 0) {
    console.log(`[CH3-HUNTER] HALTED — scalp pool depleted`);
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
    console.log(`[CH3-HUNTER] SKIP — pool fully allocated ($${availablePool.toFixed(0)} available)`);
    return [];
  }

  // Gate 4: Epoch Resonance Shield — block entries in hostile macro environments
  // Reads G32 mosaic + SPY structural state as a coupled assessment.
  // In hostile epochs, even structurally attractive setups get crushed.
  try {
    let g32 = {};
    try { g32 = JSON.parse(readFileSync("/app/g32_state.json", "utf-8")); } catch {}
    const xi = g32.xi ?? {};

    // Stress aggregate: sum of active adverse pressure channels
    // Aggregate D_k shield — macro signal from structurally rich tickers
    const dkRes = await pool.query(`
      SELECT
        COUNT(*) FILTER (WHERE CAST(NULLIF(snapshot_row_json->>'D_k','') AS DOUBLE PRECISION) > 0) AS expanding,
        COUNT(*) FILTER (WHERE CAST(NULLIF(snapshot_row_json->>'D_k','') AS DOUBLE PRECISION) < 0) AS contracting
      FROM runtime_decisions_latest
      WHERE decision_label = 'Accumulate'
        AND ticker != 'SPY'
        AND CAST(NULLIF(snapshot_row_json->>'bar_count','') AS INTEGER) > 20
    `);
    const expanding = parseInt(dkRes.rows[0]?.expanding ?? "0", 10);
    const contracting = parseInt(dkRes.rows[0]?.contracting ?? "0", 10);
    const total = expanding + contracting;

    if (total >= 5 && contracting > expanding) {
      console.log(`[CH3-HUNTER] SHIELD BLOCK — majority contracting (expanding=${expanding} contracting=${contracting})`);
      return [];
    }
    console.log(`[CH3-HUNTER] Shield: CLEAR (expanding=${expanding} contracting=${contracting})`);
  } catch (shieldErr) {
    console.log(`[CH3-HUNTER] Shield check failed: ${shieldErr.message} — proceeding`);
  }

  // Fetch candidates from full snapshot (not Accumulate-only)
  const rows = await fetchCandidateRows();
  const signals = rows.map(parseSignal).filter(Boolean);

  console.log(`[CH3-HUNTER] ${rows.length} Accumulate candidates → ${signals.length} passed filters`);

  // Exclude tickers with existing positions, already traded today, or recent losers
  const openTickers = await fetchOpenPositionTickers();
  const todayCh3Tickers = await fetchTodayCh3Tickers();
  const recentLosers = await fetchRecentCh3Losers();
  const available = [];
  for (const s of signals) {
    if (openTickers.has(s.ticker)) {
      console.log(`[CH3-HUNTER]   ${s.ticker} — skipped (open position exists)`);
      continue;
    }
    if (todayCh3Tickers.has(s.ticker)) {
      console.log(`[CH3-HUNTER]   ${s.ticker} — skipped (already traded today)`);
      continue;
    }
    if (recentLosers.has(s.ticker)) {
      console.log(`[CH3-HUNTER]   ${s.ticker} — skipped (lost money in last 7 days)`);
      continue;
    }
    available.push(s);
  }

  if (available.length === 0) {
    console.log(`[CH3-HUNTER] No candidates passed all filters`);
    return [];
  }

  // Sort by epoch pressure first (favored sectors), then S_UF
  available.sort((a, b) => (b.epoch_pressure ?? 0) - (a.epoch_pressure ?? 0) || (b.s_uf ?? 0) - (a.s_uf ?? 0));

  // Pool-limited: up to 3 signals per run, constrained by available capital
  const maxSignals = 3;
  const results = [];
  let remainingPool = availablePool;

  for (const candidate of available.slice(0, maxSignals)) {
    if (remainingPool < 500) break;
    const perTradeAmount = Math.min(CH3_MAX_PER_TRADE, remainingPool);
    candidate.ch3_trade_amount = perTradeAmount;
    remainingPool -= perTradeAmount;

    console.log(`[CH3-HUNTER] SIGNAL: ${candidate.ticker} | D_k=${candidate.d_k} B_k=${candidate.b_k?.toFixed(3)} S_UF=${candidate.s_uf?.toFixed(2)} | sector=${candidate.sector} epoch=${candidate.epoch_pressure?.toFixed(2)} | $${perTradeAmount}`);
    results.push(candidate);
  }

  return results;
}

export const CH3_CONFIG = {
  TIME_LIMIT_HOURS: null,
  DAILY_LOSS_LIMIT: CH3_DAILY_LOSS_LIMIT,
  STOP_LOSS_PCT: CH3_STOP_LOSS_PCT,
  TAKE_PROFIT_PCT: CH3_TAKE_PROFIT_PCT,
};

export async function closeCh3StrategistPool() {
  await pool.end();
}
