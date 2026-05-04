/**
 * web/scripts/execution/ch3_scalp_strategist.mjs
 * PEE-1 Chapter 3 — Structural Spike Hunter
 *
 * Selects from the FULL snapshot, NOT from Accumulates.
 * Uses L4 coupled geometry proximity to the profitable center
 * discovered via 500-ticker structural register forensics (Apr 29, 2026).
 *
 * Selection (ALL must be true):
 *   1. L4 distance to profitable center < 0.65 (coupled 7D geometry)
 *   2. B_k <= -0.95         — fully compressed (loaded spring)
 *   3. R_rev_k = 1          — recent reversal (spring just loaded)
 *   4. price < $50           — small/micro cap proxy (moves faster)
 *   5. price >= $1           — not a sub-penny stock
 *   6. bar_count > 20        — established stock
 *   7. No existing position on this ticker (any channel)
 *   8. Not already traded today by CH3
 *   9. Pool has funds remaining
 *  10. Daily loss limit not hit
 *  11. Epoch sector not ADVERSE
 *
 * Exit (enforced by Alpaca bracket order):
 *   STOP LOSS:   entry × 0.95  (-5% hard stop)
 *   TAKE PROFIT: entry × 1.50  (wide ceiling — sentinel trails)
 *
 * Pool rules:
 *   - $5,000 scalp pool
 *   - Max $2,500 per trade
 *   - Daily loss limit: $1,000
 *
 * The L4 tuple is NEVER decomposed. Distance is computed in the
 * full 7D coupled space. The profitable center is a fixed structural
 * constant derived from 13,014 entries across 500 tickers.
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

// ── CH3 Structural Constants ────────────────────────────────────────────
// Profitable center in coupled L4 space (from 500-ticker register forensics)
// Validated across random halves: Half A PF=3.85, Half B PF=3.77
const PROFIT_CENTER = {
  D_k:      0.2875,
  M_k:      0.0196,
  R_rev_k:  0.6649,
  U_star_k: 0.2978,
  C_k:      2.2506,
  P_k:      1.3766,
  B_k:     -0.9771,
};

// Normalization ranges for distance calculation (keeps coupling intact)
const NORMS = {
  D_k:      2.0,
  M_k:      2.0,
  R_rev_k:  1.0,
  U_star_k: 1.0,
  C_k:      3.0,
  P_k:      2.0,
  B_k:      2.0,
};

const L4_FIELDS = ['D_k', 'M_k', 'R_rev_k', 'U_star_k', 'C_k', 'P_k', 'B_k'];

// Selection thresholds
const CH3_MAX_DISTANCE     = 0.65;   // max L4 distance to profitable center
const CH3_B_K_RAIL         = -0.95;  // B_k must be at or below this (loaded spring)
const CH3_MAX_PRICE        = 50;     // small/micro cap proxy
const CH3_MIN_PRICE        = 1;      // no sub-penny
const CH3_BAR_COUNT_MIN    = 21;     // established stocks only

// Pool & risk
const CH3_POOL_TOTAL       = 5000;
const CH3_MAX_PER_TRADE    = 2500;
const CH3_DAILY_LOSS_LIMIT = 1000;

// Exit: -5% hard stop, sentinel grabs on fuel fade
// TP is a safety ceiling — the sentinel exits on fuel, not TP
const CH3_STOP_LOSS_PCT    = 0.05;   // 5% below entry
const CH3_TAKE_PROFIT_PCT  = 0.10;   // 10% ceiling (backstop only — sentinel grabs earlier)

function toFloat(v) {
  const n = parseFloat(v);
  return isFinite(n) ? n : null;
}

/**
 * Compute coupled L4 distance to profitable center.
 * The full 7-value tuple stays coupled — distance is in 7D space.
 */
function computeL4Distance(snap) {
  let sumSq = 0;
  for (const f of L4_FIELDS) {
    const val = toFloat(snap[f]) ?? 0;
    const center = PROFIT_CENTER[f];
    const norm = NORMS[f];
    sumSq += ((val - center) / norm) ** 2;
  }
  return Math.sqrt(sumSq);
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

// ── Candidate selection ─────────────────────────────────────────────────

/**
 * Fetch candidates from the FULL snapshot — not filtered by Accumulate.
 * Selection is purely by L4 coupled geometry proximity.
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
       AND CAST(NULLIF(r.snapshot_row_json->>'bar_count', '') AS INTEGER) > $1
       AND CAST(NULLIF(r.snapshot_row_json->>'R_rev_k', '') AS DOUBLE PRECISION) = 1
       AND CAST(NULLIF(r.snapshot_row_json->>'B_k', '') AS DOUBLE PRECISION) <= $2
       AND CAST(NULLIF(r.snapshot_row_json->>'price', '') AS DOUBLE PRECISION) < $3
       AND CAST(NULLIF(r.snapshot_row_json->>'price', '') AS DOUBLE PRECISION) >= $4
     ORDER BY CAST(NULLIF(r.snapshot_row_json->>'B_k', '') AS DOUBLE PRECISION) ASC
     LIMIT 50`,
    [CH3_BAR_COUNT_MIN - 1, CH3_B_K_RAIL, CH3_MAX_PRICE, CH3_MIN_PRICE]
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
  if (price === null || price < CH3_MIN_PRICE || price >= CH3_MAX_PRICE) return null;

  // Compute coupled L4 distance
  const dist = computeL4Distance(snap);
  if (dist >= CH3_MAX_DISTANCE) return null;

  // G32 epoch sector filter — skip ADVERSE sectors
  let epochStatus = "UNKNOWN";
  try {
    const { readFileSync } = await import("fs");
    const g32Raw = readFileSync("/app/g32_state.json", "utf-8");
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
    console.log(`[CH3-HUNTER]   ${ticker} — skipped (sector ${sector} ADVERSE epoch pressure)`);
    return null;
  }

  return {
    ticker,
    run_id:       runId,
    signal_class: "CH3",
    s_uf:         toFloat(snap.S_UF),
    d_k:          toFloat(snap.D_k),
    b_k:          toFloat(snap.B_k),
    m_k:          toFloat(snap.M_k),
    r_rev_k:      toFloat(snap.R_rev_k),
    u_star_k:     toFloat(snap.U_star_k),
    c_k:          toFloat(snap.C_k),
    p_k:          toFloat(snap.P_k),
    bar_count:    barCount,
    price:        price,
    sector:       sector,
    epoch_status: epochStatus,
    l4_distance:  dist,
    // CH3 bracket prices: -5% stop, +50% ceiling
    ch3_stop_loss_pct:    CH3_STOP_LOSS_PCT,
    ch3_take_profit_pct:  CH3_TAKE_PROFIT_PCT,
  };
}

// ── Main entry point ────────────────────────────────────────────────────

export async function getCh3Signals() {
  console.log(`[CH3-HUNTER] Structural spike hunter scanning...`);

  // Gate 0: market hours check — don't submit orders when market is closed
  const now = new Date();
  const utcHour = now.getUTCHours();
  const utcMinute = now.getUTCMinutes();
  const utcTime = utcHour * 60 + utcMinute;
  // Market hours: 13:30-20:00 UTC (9:30 AM - 4:00 PM ET)
  if (utcTime < 13 * 60 + 30 || utcTime >= 20 * 60) {
    console.log(`[CH3-HUNTER] SKIP — market closed (${utcHour}:${String(utcMinute).padStart(2,'0')} UTC)`);
    return [];
  }

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
    const { readFileSync: readFileSync2 } = await import("fs");
    let g32 = {};
    try { g32 = JSON.parse(readFileSync2("/app/g32_state.json", "utf-8")); } catch {}
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

  console.log(`[CH3-HUNTER] ${rows.length} raw candidates → ${signals.length} passed L4 proximity filter`);

  // Exclude tickers with existing positions or already traded today
  const openTickers = await fetchOpenPositionTickers();
  const todayCh3Tickers = await fetchTodayCh3Tickers();
  const available = signals.filter(s => {
    if (openTickers.has(s.ticker)) return false;
    if (todayCh3Tickers.has(s.ticker)) return false;
    return true;
  });

  if (available.length === 0) {
    console.log(`[CH3-HUNTER] No candidates passed all filters`);
    return [];
  }

  // Sort by L4 distance — closest to center = most loaded
  available.sort((a, b) => a.l4_distance - b.l4_distance);

  // Pool-limited: one position at a time to start
  const perTradeAmount = Math.min(CH3_MAX_PER_TRADE, availablePool);
  const best = available[0];
  best.ch3_trade_amount = perTradeAmount;

  console.log(`[CH3-HUNTER] SIGNAL: ${best.ticker} | dist=${best.l4_distance.toFixed(3)} | D=${best.d_k} M=${best.m_k?.toFixed(4)} Rrev=${best.r_rev_k} U*=${best.u_star_k?.toFixed(3)} C=${best.c_k} P=${best.p_k} B=${best.b_k?.toFixed(4)} | $${perTradeAmount}`);

  return [best];
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
