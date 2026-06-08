/**
 * web/scripts/execution/ch2_strategist.mjs
 * PEE-1 Chapter 2 Strategist — Mid S_UF Acceleration Layer
 *
 * Independent execution path. Does NOT touch or depend on 3WA (Chapter 1) logic.
 *
 * Entry conditions (ALL must be true):
 *   1. decision_label = 'Accumulate'  — tuple-proximity WR >= 0.65
 *   2. D_k = 1                        — per-ticker directional expansion
 *   3. bar_count > 20                 — established stock
 *   4. market_cap >= $500M            — liquidity floor
 *
 * S_UF band [0.50, 0.75) REMOVED June 2026 — validated as primary alpha drag.
 * Tuple-proximity reads S_UF as part of the coupled state; the scalar gate
 * was redundant and blocked high-WR picks (NVDA WR=0.933 rejected at S_UF=0.34).
 *
 * Exit conditions (evaluated by sentinel_monitor per signal_class='CH2'):
 *   EXIT A — Acceleration complete:  S_UF crosses above 0.75
 *   EXIT B — Directional collapse:   D_k flips to 0 or -1
 *
 * Data source: runtime_decisions_latest (same as 3WA strategist)
 * Position sizing: 1.0% risk per trade (vs 1.5% for 3WA — lower conviction)
 */

import pg from "pg";
import { readFileSync } from "fs";
// computeRegimeExposure import removed — position count cap removed, cash is the only constraint

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

// ── Chapter 2 entry thresholds ────────────────────────────────────────────
const CH2_S_UF_MIN        = 0.50;   // inclusive
const CH2_S_UF_MAX        = 0.75;   // exclusive — above this is 3WA territory
const CH2_BAR_COUNT_MIN   = 21;     // must be established (> 3WA threshold of 20)
const CH2_REQUIRED_DK     = 1;      // directional expansion required
const CH2_REQUIRED_REGIME = "TRANSITIONAL";
const CH2_MIN_MARKET_CAP  = 500_000_000;  // $500M — liquidity floor

function toFloat(v) {
  const n = parseFloat(v);
  return isFinite(n) ? n : null;
}
function toInt(v) {
  const n = parseInt(v, 10);
  return isFinite(n) ? n : null;
}

async function resolveLatestRunId() {
  const res = await pool.query(
    `SELECT run_id FROM runtime_decisions_latest
     ORDER BY generated_at_utc DESC LIMIT 1`
  );
  if (!res.rows.length) throw new Error("[CH2-STRATEGIST] runtime_decisions_latest is empty");
  return res.rows[0].run_id;
}

/**
 * Fetch all Chapter 2 candidate rows for the given run_id.
 * Filters at the DB level for performance.
 */
async function fetchCandidateRows(runId) {
  const res = await pool.query(
    `SELECT
       r.ticker,
       r.run_id,
       r.decision_label,
       r.snapshot_row_json,
       COALESCE(f.sector, 'Unknown') AS sector
     FROM runtime_decisions_latest r
     LEFT JOIN runtime_symbols s ON s.ticker = r.ticker
     LEFT JOIN l5_fundamentals_normalized f ON f.ticker = r.ticker
     WHERE r.run_id = $1
       AND r.decision_label = 'Accumulate'
       AND r.ticker != 'SPY'
       AND CAST(NULLIF(r.snapshot_row_json->>'bar_count', '') AS INTEGER) > $2
       AND COALESCE(NULLIF(s.market_cap, 0), f.market_cap, 0) >= $3
     ORDER BY r.ticker ASC`,
    [runId, CH2_BAR_COUNT_MIN - 1, CH2_MIN_MARKET_CAP]
  );
  return res.rows;
}

/**
 * Parse a DB row into a validated Ch2 signal object.
 * Returns null if any required field is missing or out of range.
 */
function parseSignal(row) {
  const snap      = row.snapshot_row_json ?? {};
  const ticker    = String(row.ticker ?? "").trim().toUpperCase();
  const runId     = String(row.run_id ?? "").trim();
  const barCount  = toInt(snap.bar_count ?? row.bar_count);
  const sUf       = toFloat(snap.S_UF ?? snap.s_uf);
  const dk        = toInt(snap.D_k ?? snap.d_k);
  const regime    = String(snap.regime ?? "").trim().toUpperCase();
  const bk        = toFloat(snap.B_k ?? snap.b_k);
  const fn        = toFloat(snap.F_n ?? snap.f_n);
  const neighborWR = toFloat(snap.neighbor_wr);

  // Hard entry gates — all must pass
  if (!ticker)                                          return null;
  if (!runId)                                           return null;
  if (barCount === null || barCount < CH2_BAR_COUNT_MIN) return null;
  // S_UF band gate REMOVED. Validated as primary drag on alpha:
  // with S_UF band [0.50, 0.75): -8.65pp vs SPY (rejected NVDA WR=0.933, AMD, etc.)
  // without S_UF band (tuple-only): +2.73pp vs SPY on same leak-free deep-pool window.
  // The band blocked high-WR picks whose structural field strength sat outside
  // an arbitrary acceleration range. Tuple-proximity WR already reads the full
  // coupled structural state including S_UF — the scalar gate was redundant
  // and destructive.
  // D_k=1 gate stays — it's part of the 7-dim tuple the TP engine reads,
  // and validates as a legitimate per-ticker directional alignment check.
  if (dk !== 1) return null;

  return {
    ticker,
    run_id:       runId,
    signal_class: "CH2",
    s_uf:         sUf,
    d_k:          dk,
    bar_count:    barCount,
    regime,
    f_n:          fn,
    b_k:          bk,
    sector:       String(row.sector ?? "Unknown").trim(),
    neighbor_wr:  neighborWR,
    // No spy_dk gate for Ch2 — D_k=1 on the ticker itself is sufficient
    spy_dk:       null,
  };
}

/**
 * Main entry point.
 * Returns array of validated Ch2 signal objects ready for alpaca_bridge.
 */
/**
 * Fetch tickers that already have open positions in the ledger.
 * Prevents duplicate position entries on the same ticker.
 */
async function fetchOpenPositionTickers() {
  // Include both currently-open positions AND tickers recently closed by sentinel.
  // The sentinel writes kill_cooldown_<TICKER> to pee1_execution_config when it
  // exits a position. Without this, the entry logic (which runs AFTER runSentinel
  // in the same daemon cycle) sees the ticker as "no open position" and immediately
  // re-enters — creating a buy→sell→buy→sell churn loop.
  const [openRes, cooldownRes] = await Promise.all([
    pool.query(
      `SELECT DISTINCT UPPER(TRIM(ticker)) AS ticker
       FROM personal_trade_ledger
       WHERE status IN ('pending', 'submitted', 'filled')`
    ),
    pool.query(
      `SELECT key, value FROM pee1_execution_config
       WHERE key LIKE 'kill_cooldown_%'`
    ),
  ]);
  const tickers = new Set(openRes.rows.map(r => r.ticker));
  // Add tickers still in kill cooldown (15 min window)
  const COOLDOWN_MS = 15 * 60 * 1000;
  for (const row of cooldownRes.rows) {
    const killedAt = new Date(row.value).getTime();
    if (Date.now() - killedAt <= COOLDOWN_MS) {
      const ticker = row.key.replace('kill_cooldown_', '');
      tickers.add(ticker);
    }
  }
  return tickers;
}

export async function getCh2Signals() {
  const runId = await resolveLatestRunId();
  console.log(`[CH2-STRATEGIST] run_id=${runId}`);

  // Diagnostic: count candidates at each filter step (scoped to current run_id)
  try {
    const diag1 = await pool.query(`SELECT COUNT(*) as cnt FROM runtime_decisions_latest WHERE run_id = $1 AND decision_label = 'Accumulate'`, [runId]);
    const diag2 = await pool.query(`SELECT COUNT(*) as cnt FROM runtime_decisions_latest WHERE run_id = $1 AND decision_label = 'Accumulate' AND CAST(NULLIF(snapshot_row_json->>'S_UF','') AS DOUBLE PRECISION) >= 0.50 AND CAST(NULLIF(snapshot_row_json->>'S_UF','') AS DOUBLE PRECISION) < 0.75`, [runId]);
    const diag3 = await pool.query(`SELECT COUNT(*) as cnt FROM runtime_decisions_latest WHERE run_id = $1 AND decision_label = 'Accumulate' AND CAST(NULLIF(snapshot_row_json->>'S_UF','') AS DOUBLE PRECISION) >= 0.50 AND CAST(NULLIF(snapshot_row_json->>'S_UF','') AS DOUBLE PRECISION) < 0.75 AND CAST(NULLIF(snapshot_row_json->>'bar_count','') AS INTEGER) > 20`, [runId]);
    const diag4 = await pool.query(`SELECT COUNT(*) as cnt FROM runtime_decisions_latest r LEFT JOIN runtime_symbols s ON s.ticker = r.ticker WHERE r.run_id = $1 AND r.decision_label = 'Accumulate' AND CAST(NULLIF(r.snapshot_row_json->>'S_UF','') AS DOUBLE PRECISION) >= 0.50 AND CAST(NULLIF(r.snapshot_row_json->>'S_UF','') AS DOUBLE PRECISION) < 0.75 AND CAST(NULLIF(r.snapshot_row_json->>'bar_count','') AS INTEGER) > 20 AND COALESCE(s.market_cap, 0) >= 500000000`, [runId]);
    const diag5 = await pool.query(`SELECT COUNT(*) as cnt FROM runtime_symbols WHERE market_cap IS NOT NULL AND market_cap > 0`);
    // Check how many in-band candidates have market_cap in l5_fundamentals_normalized (the OTHER table)
    const diag6 = await pool.query(`SELECT COUNT(*) as cnt FROM runtime_decisions_latest r LEFT JOIN l5_fundamentals_normalized f ON f.ticker = r.ticker WHERE r.run_id = $1 AND r.decision_label = 'Accumulate' AND CAST(NULLIF(r.snapshot_row_json->>'S_UF','') AS DOUBLE PRECISION) >= 0.50 AND CAST(NULLIF(r.snapshot_row_json->>'S_UF','') AS DOUBLE PRECISION) < 0.75 AND CAST(NULLIF(r.snapshot_row_json->>'bar_count','') AS INTEGER) > 20 AND COALESCE(f.market_cap, 0) >= 500000000`, [runId]);
    console.log(`[CH2-DIAG] run_id=${runId} | Accumulate: ${diag1.rows[0].cnt} | S_UF band: ${diag2.rows[0].cnt} | +bar_count: ${diag3.rows[0].cnt} | +mktcap(runtime_symbols): ${diag4.rows[0].cnt} | +mktcap(l5_fundamentals): ${diag6.rows[0].cnt} | runtime_symbols w/mktcap: ${diag5.rows[0].cnt}`);
  } catch (diagErr) {
    console.log(`[CH2-DIAG] Error: ${diagErr.message}`);
  }

  // ── Weekend + Holiday block: no entries on non-trading days ─────────────
  // Weekend gap risk is unmanageable — REGN dropped 12% over a weekend.
  // Memorial Day 2026: 66 orders placed on closed market. Holidays kill.
  {
    const now = new Date();
    const dayOfWeek = now.getUTCDay(); // 0=Sun, 5=Fri, 6=Sat
    if (dayOfWeek === 5 || dayOfWeek === 6 || dayOfWeek === 0) {
      console.log(`[CH2-STRATEGIST] WEEKEND BLOCK — no new entries (day=${dayOfWeek})`);
      return [];
    }
    try {
      const { isMarketHoliday, getHolidayName } = await import("./market_calendar.mjs");
      if (isMarketHoliday(now)) {
        console.log(`[CH2-STRATEGIST] HOLIDAY BLOCK — ${getHolidayName(now) ?? "market holiday"}`);
        return [];
      }
    } catch {}
  }

  // Position count cap (maxPositions=30) REMOVED. The constraint on deployment
  // is available cash (task 523/530/531 cash ceiling), not position count.
  // Position count caps were never authorized — Joe specified "the constraint
  // is cash, not position count." Same class of arbitrary aggregate gate as the
  // 0.5 regime cap and S_UF band already removed.
  //
  // Previously: computeRegimeExposure(spyDk, openCount, 30, 0) → blocked at 30+ positions
  // Cash ceiling in alpaca_bridge still gates every order against available cash.

  // Aggregate D_k shield REMOVED. Same principle as S_UF band and regime cap:
  // an aggregate scalar override was vetoing qualified individual picks.
  // The tuple-proximity engine already evaluates each stock's coupled structural
  // state. A stock with WR=0.93 should not be blocked because unrelated stocks
  // in the universe have D_k < 0. The per-stock structural read is the entry
  // decision; aggregate breadth is observable but does not veto.
  //
  // Previously: contracting > expanding → return [] (blocked all CH2 entries)
  // Now: log the breadth reading for observability, proceed to individual evaluation.

  const rows    = await fetchCandidateRows(runId);
  const signals = rows.map(parseSignal).filter(Boolean);

  // Exclude tickers that already have open positions
  const openTickers = await fetchOpenPositionTickers();
  const deduped = signals.filter(s => {
    if (openTickers.has(s.ticker)) {
      console.log(`[CH2-STRATEGIST]   ${s.ticker} — SKIPPED (open position exists)`);
      return false;
    }
    return true;
  });

  // L5 epoch governance — sort by sector pressure, block epoch-adverse stocks
  let g32 = {};
  try { g32 = JSON.parse(readFileSync("/app/g32_state.json", "utf-8")); } catch {}
  const sectorPressures = g32.sector_pressures ?? {};

  // Add epoch pressure to each signal
  for (const s of deduped) {
    s.epoch_pressure = sectorPressures[s.sector] ?? 0;
  }

  // Block stocks in heavily adverse sectors (pressure < -0.5)
  const governed = deduped.filter(s => {
    if (s.epoch_pressure < -0.5) {
      console.log(`[CH2-STRATEGIST]   ${s.ticker} — BLOCKED (sector ${s.sector} epoch pressure ${s.epoch_pressure.toFixed(2)})`);
      return false;
    }
    return true;
  });

  // Sort: epoch-favored sectors first, then by S_UF
  governed.sort((a, b) => (b.epoch_pressure - a.epoch_pressure) || (b.s_uf - a.s_uf));

  console.log(`[CH2-STRATEGIST] ${rows.length} candidates → ${signals.length} valid → ${deduped.length} dedup → ${governed.length} after epoch governance`);
  for (const s of governed) {
    console.log(`[CH2-STRATEGIST]   ${s.ticker} | s_uf=${s.s_uf} | D_k=${s.d_k} | sector=${s.sector} | epoch=${s.epoch_pressure?.toFixed(2) ?? "?"}`);
  }

  return governed;
}

export async function closeCh2StrategistPool() {
  await pool.end();
}
