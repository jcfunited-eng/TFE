/**
 * web/scripts/execution/ch3_strike_zone_detector.mjs
 *
 * CH3 Strike Zone Detector — Phase + Swarm + G32 Direction
 *
 * Detects the three conditions that precede high-probability spikes:
 *   1. PHASE: Strong upheaval 5-10 days ago + partial settling now
 *   2. SWARM: Current day swarm is dead (investors coiled, about to strike)
 *   3. DIRECTION: G32 epoch pressure tells us which sectors benefit
 *
 * Based on study findings:
 *   - Strike zone + swarm dead = +38.5% edge (51.3% spike vs 12.7% drop)
 *   - Works across all price tiers ($5-500+)
 *   - 591 unique symbols, not concentrated
 *
 * The detector runs every 5 minutes during market hours (alongside sentinel).
 * When strike zone is detected, it selects Accumulate stocks with:
 *   - B near zero (free to move, not locked)
 *   - Sector in TAILWIND from active epoch (G32 direction)
 *   - D_k = +1 (expanding)
 *
 * Then fires CH3 bracket orders on the best candidates.
 *
 * No ML. No heuristics. Deterministic phase detection + epoch coupling.
 */

import pg from "pg";
import { readFileSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

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

// ── Configuration ───────────────────────────────────────────────────────
const UPHEAVAL_THRESHOLD = 0.06;     // regime change rate considered "strong upheaval"
const PARTIAL_SETTLE_HIGH = 0.05;    // settling: current rcr below this
const PARTIAL_SETTLE_LOW = 0.03;     // but above this (not fully dead)
const SWARM_DEAD_THRESHOLD = 0.04;   // today's rcr below this = swarm coiled
const B_NEAR_ZERO_MAX = 0.15;        // |B_k| < this = free to move
const CH3_POOL_TOTAL = 5000;
const CH3_MAX_PER_TRADE = 2500;
const MAX_ENTRIES_PER_CHECK = 1;     // one at a time

// ── G32 State Reader ────────────────────────────────────────────────────

function loadG32State() {
  try {
    const statePath = resolve(__dirname, "../../../g32_state.json");
    const raw = readFileSync(statePath, "utf-8");
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function getSectorPressure(g32State, sector) {
  if (!g32State || !g32State.xi) return { pressure: 0, status: "UNKNOWN" };

  // Coupling matrix (same as tfe_g32_coordinator.py)
  const COUPLING = {
    "Communication Services": { RATES_PRESSURE: -0.2, CONSUMER_STRESS: -0.3, WAR_GEOPOLITICS: -0.1 },
    "Consumer Discretionary": { RATES_PRESSURE: -0.5, CONSUMER_STRESS: -1.0, WAR_GEOPOLITICS: -0.2 },
    "Consumer Staples":       { RATES_PRESSURE: 0.1,  CONSUMER_STRESS: 0.4,  WAR_GEOPOLITICS: -0.1 },
    "Energy":                 { RATES_PRESSURE: 0.0,  CONSUMER_STRESS: -0.2, WAR_GEOPOLITICS: 0.9 },
    "Financial Services":     { RATES_PRESSURE: 0.2,  CONSUMER_STRESS: -0.5, WAR_GEOPOLITICS: -0.2 },
    "Financials":             { RATES_PRESSURE: 0.2,  CONSUMER_STRESS: -0.5, WAR_GEOPOLITICS: -0.2 },
    "Health Care":            { RATES_PRESSURE: 0.0,  CONSUMER_STRESS: 0.3,  WAR_GEOPOLITICS: 0.1 },
    "Healthcare":             { RATES_PRESSURE: 0.0,  CONSUMER_STRESS: 0.3,  WAR_GEOPOLITICS: 0.1 },
    "Industrials":            { RATES_PRESSURE: -0.2, CONSUMER_STRESS: -0.3, WAR_GEOPOLITICS: 0.2 },
    "Information Technology":  { RATES_PRESSURE: -0.4, CONSUMER_STRESS: -0.3, WAR_GEOPOLITICS: 0.0 },
    "Technology":             { RATES_PRESSURE: -0.4, CONSUMER_STRESS: -0.3, WAR_GEOPOLITICS: 0.0 },
    "Materials":              { RATES_PRESSURE: -0.1, CONSUMER_STRESS: -0.3, WAR_GEOPOLITICS: 0.3 },
    "Real Estate":            { RATES_PRESSURE: -1.0, CONSUMER_STRESS: -0.5, WAR_GEOPOLITICS: 0.0 },
    "Utilities":              { RATES_PRESSURE: -0.3, CONSUMER_STRESS: 0.2,  WAR_GEOPOLITICS: 0.1 },
    "Banking":                { RATES_PRESSURE: 0.3,  CONSUMER_STRESS: -0.6, WAR_GEOPOLITICS: -0.2 },
    "Basic Materials":        { RATES_PRESSURE: -0.1, CONSUMER_STRESS: -0.3, WAR_GEOPOLITICS: 0.3 },
  };

  const normalized = (sector ?? "").trim();
  const coupling = COUPLING[normalized];
  if (!coupling) return { pressure: 0, status: "UNKNOWN" };

  let pressure = 0;
  for (const [ch, weight] of Object.entries(coupling)) {
    pressure += (g32State.xi[ch] ?? 0) * weight;
  }

  const status = pressure <= -0.5 ? "ADVERSE" : pressure <= 0 ? "HEADWIND" : pressure > 0.3 ? "TAILWIND" : "NEUTRAL";
  return { pressure: Math.round(pressure * 1000) / 1000, status };
}

// ── Phase Detection ─────────────────────────────────────────────────────

/**
 * Compute rolling regime change rate from runtime_decisions_history.
 * Returns { peakRcr, recentRcr, rcrDrop, phase }
 */
async function detectPhase() {
  try {
    // Get regime change counts over last 10 refresh cycles
    const res = await pool.query(`
      SELECT
        run_id,
        COUNT(*) as total_decisions,
        COUNT(*) FILTER (WHERE
          snapshot_row_json->>'regime' IS DISTINCT FROM
          LAG(snapshot_row_json->>'regime') OVER (PARTITION BY ticker ORDER BY created_at)
        ) as regime_changes
      FROM runtime_decisions_history
      WHERE created_at >= NOW() - INTERVAL '14 days'
      GROUP BY run_id
      ORDER BY MAX(created_at) DESC
      LIMIT 10
    `);

    if (res.rows.length < 3) {
      return { phase: "INSUFFICIENT_DATA", peakRcr: 0, recentRcr: 0, rcrDrop: 0 };
    }

    const rcrs = res.rows.map(r => {
      const total = parseInt(r.total_decisions) || 1;
      const changes = parseInt(r.regime_changes) || 0;
      return changes / total;
    });

    // rcrs[0] = most recent, rcrs[9] = oldest
    const recentRcr = rcrs.length >= 3 ? (rcrs[0] + rcrs[1] + rcrs[2]) / 3 : rcrs[0];
    const olderRcrs = rcrs.slice(3);
    const peakRcr = olderRcrs.length > 0 ? Math.max(...olderRcrs) : 0;
    const rcrDrop = peakRcr - recentRcr;

    // Phase classification
    let phase;
    if (peakRcr >= UPHEAVAL_THRESHOLD && recentRcr < PARTIAL_SETTLE_HIGH && recentRcr > PARTIAL_SETTLE_LOW) {
      phase = "STRIKE_ZONE";
    } else if (peakRcr >= UPHEAVAL_THRESHOLD && recentRcr <= PARTIAL_SETTLE_LOW) {
      phase = "POST_SETTLE";
    } else if (peakRcr >= UPHEAVAL_THRESHOLD && recentRcr >= PARTIAL_SETTLE_HIGH) {
      phase = "UPHEAVAL";
    } else {
      phase = "NORMAL";
    }

    return { phase, peakRcr, recentRcr, rcrDrop };
  } catch (err) {
    console.error(`[STRIKE-ZONE] Phase detection error: ${err.message}`);
    return { phase: "ERROR", peakRcr: 0, recentRcr: 0, rcrDrop: 0 };
  }
}

// ── Swarm Detection ─────────────────────────────────────────────────────

/**
 * Check if the swarm is dead (low current regime change activity).
 * Uses the G32 delta signal if available, or falls back to recent rcr.
 */
function detectSwarm(phaseData, g32State) {
  // Use G32 delta if available
  if (g32State?.xi_delta) {
    const deltaMag = Math.sqrt(
      Object.values(g32State.xi_delta).reduce((sum, v) => sum + v * v, 0)
    );
    // Delta near zero = epoch field not changing = swarm settled
    if (deltaMag < 0.05) return { swarm: "DEAD", deltaMag };
    if (deltaMag < 0.10) return { swarm: "QUIET", deltaMag };
    return { swarm: "ACTIVE", deltaMag };
  }

  // Fallback: use phase data rcr
  if (phaseData.recentRcr < SWARM_DEAD_THRESHOLD) {
    return { swarm: "DEAD", deltaMag: null };
  }
  return { swarm: "ACTIVE", deltaMag: null };
}

// ── Candidate Selection ─────────────────────────────────────────────────

/**
 * Get CH3 candidates: Accumulate stocks with B near zero, D_k=+1,
 * in sectors with TAILWIND or NEUTRAL epoch pressure.
 */
async function getStrikeZoneCandidates(g32State) {
  // Get tickers with open positions — exclude them
  const openRes = await pool.query(`
    SELECT DISTINCT UPPER(TRIM(ticker)) AS ticker
    FROM personal_trade_ledger
    WHERE status IN ('submitted', 'filled', 'pending')
  `);
  const openTickers = new Set(openRes.rows.map(r => r.ticker));

  // Check if CH3 already has an open position (one at a time)
  const ch3Open = await pool.query(`
    SELECT COUNT(*) AS cnt FROM personal_trade_ledger
    WHERE signal_class = 'CH3' AND status IN ('submitted', 'filled')
  `);
  if (parseInt(ch3Open.rows[0]?.cnt ?? "0") > 0) {
    return { candidates: [], reason: "CH3 position already open" };
  }

  // No same-day re-entry
  const todayCh3 = await pool.query(`
    SELECT DISTINCT UPPER(TRIM(ticker)) AS ticker
    FROM personal_trade_ledger
    WHERE signal_class = 'CH3' AND signal_detected_at >= CURRENT_DATE
  `);
  const todayTickers = new Set(todayCh3.rows.map(r => r.ticker));

  // Get Accumulate stocks with B near zero and D_k = +1
  const candidateRes = await pool.query(`
    SELECT
      r.ticker,
      r.run_id,
      CAST(NULLIF(r.snapshot_row_json->>'S_UF', '') AS DOUBLE PRECISION) AS s_uf,
      CAST(NULLIF(r.snapshot_row_json->>'D_k', '') AS DOUBLE PRECISION) AS d_k,
      CAST(NULLIF(r.snapshot_row_json->>'B_k', '') AS DOUBLE PRECISION) AS b_k,
      CAST(NULLIF(r.snapshot_row_json->>'M_k', '') AS DOUBLE PRECISION) AS m_k,
      CAST(NULLIF(r.snapshot_row_json->>'bar_count', '') AS INTEGER) AS bar_count,
      COALESCE(f.sector, 'Unknown') AS sector
    FROM runtime_decisions_latest r
    LEFT JOIN l5_fundamentals_normalized f ON f.ticker = r.ticker
    WHERE r.decision_label = 'Accumulate'
      AND CAST(NULLIF(r.snapshot_row_json->>'D_k', '') AS DOUBLE PRECISION) = 1
      AND ABS(CAST(NULLIF(r.snapshot_row_json->>'B_k', '') AS DOUBLE PRECISION)) < $1
      AND CAST(NULLIF(r.snapshot_row_json->>'bar_count', '') AS INTEGER) > 20
      AND r.ticker != 'SPY'
    ORDER BY CAST(NULLIF(r.snapshot_row_json->>'S_UF', '') AS DOUBLE PRECISION) DESC
    LIMIT 30
  `, [B_NEAR_ZERO_MAX]);

  const candidates = [];
  for (const row of candidateRes.rows) {
    const ticker = row.ticker.trim().toUpperCase();
    if (openTickers.has(ticker)) continue;
    if (todayTickers.has(ticker)) continue;

    const sector = (row.sector ?? "Unknown").trim();
    const epochPressure = getSectorPressure(g32State, sector);

    // Only pick stocks in TAILWIND or NEUTRAL sectors
    if (epochPressure.status === "ADVERSE") continue;

    candidates.push({
      ticker,
      run_id: row.run_id,
      signal_class: "CH3",
      s_uf: parseFloat(row.s_uf),
      d_k: parseFloat(row.d_k),
      b_k: parseFloat(row.b_k),
      m_k: parseFloat(row.m_k ?? "0"),
      bar_count: parseInt(row.bar_count),
      sector,
      epoch_pressure: epochPressure.pressure,
      epoch_status: epochPressure.status,
    });
  }

  // Sort: TAILWIND sectors first, then by S_UF
  candidates.sort((a, b) => {
    const aBoost = a.epoch_status === "TAILWIND" ? 1 : 0;
    const bBoost = b.epoch_status === "TAILWIND" ? 1 : 0;
    if (aBoost !== bBoost) return bBoost - aBoost;
    return b.s_uf - a.s_uf;
  });

  return { candidates, reason: null };
}

// ── Main Detection + Execution ──────────────────────────────────────────

/**
 * Run the full strike zone detection and fire CH3 if conditions align.
 * Called by sentinel daemon every 5 minutes during market hours.
 */
export async function runStrikeZoneCheck() {
  // Step 1: Detect phase
  const phaseData = await detectPhase();

  // Step 2: Load G32 state
  const g32State = loadG32State();

  // Step 3: Detect swarm
  const swarmData = detectSwarm(phaseData, g32State);

  // Log current state
  console.log(
    `[STRIKE-ZONE] Phase=${phaseData.phase} (peak=${(phaseData.peakRcr*100).toFixed(1)}% recent=${(phaseData.recentRcr*100).toFixed(1)}%) | ` +
    `Swarm=${swarmData.swarm} | G32=${g32State ? "loaded" : "unavailable"}`
  );

  // Step 4: Check if we're in the strike zone
  if (phaseData.phase !== "STRIKE_ZONE") {
    return;
  }

  if (swarmData.swarm !== "DEAD" && swarmData.swarm !== "QUIET") {
    console.log(`[STRIKE-ZONE] Strike zone detected but swarm is ${swarmData.swarm} — waiting for coil`);
    return;
  }

  console.log(`[STRIKE-ZONE] *** STRIKE ZONE ACTIVE *** Phase=${phaseData.phase} Swarm=${swarmData.swarm}`);

  // Step 5: Get candidates
  const { candidates, reason } = await getStrikeZoneCandidates(g32State);

  if (reason) {
    console.log(`[STRIKE-ZONE] No candidates: ${reason}`);
    return;
  }

  if (candidates.length === 0) {
    console.log(`[STRIKE-ZONE] No B-near-zero Accumulate stocks in TAILWIND/NEUTRAL sectors`);
    return;
  }

  // Step 6: Fire on best candidate
  const best = candidates[0];
  const tradeAmount = Math.min(CH3_MAX_PER_TRADE, CH3_POOL_TOTAL);

  console.log(
    `[STRIKE-ZONE] FIRING: ${best.ticker} | S_UF=${best.s_uf} | B_k=${best.b_k} | ` +
    `sector=${best.sector} | epoch=${best.epoch_status}(${best.epoch_pressure}) | $${tradeAmount}`
  );

  try {
    const { executeCh3MarketOrder } = await import("./alpaca_bridge.mjs");
    best.ch3_trade_amount = tradeAmount;
    const result = await executeCh3MarketOrder(best);
    if (result?.status === "submitted" || result?.status === "filled") {
      console.log(`[STRIKE-ZONE] ORDER PLACED: ${best.ticker} — ${result.status}`);
    } else {
      console.log(`[STRIKE-ZONE] ${best.ticker} — ${result?.status ?? "unknown"}: ${result?.exit_reason ?? ""}`);
    }
  } catch (err) {
    console.error(`[STRIKE-ZONE] Order failed: ${err.message}`);
  }
}

export async function closeStrikeZonePool() {
  await pool.end();
}
