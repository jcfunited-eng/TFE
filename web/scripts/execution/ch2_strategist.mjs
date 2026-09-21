/**
 * web/scripts/execution/ch2_strategist.mjs
 * PEE-1 Chapter 2 Strategist — V3 Basin Gate
 *
 * Entry conditions (ALL must be true):
 *   1. computeV3Basin → decision_argmax = 'Accumulate'
 *   2. accumulate_basin >= 0.15
 *   3. bar_count > 20  — established stock
 *   4. market_cap >= $500M  — liquidity floor
 *
 * Replaces TFE-CMD-V3-BASIN-DETERMINISTIC-WC-20260707-v1: tuple-proximity
 * decision_label gate and D_k=1 scalar gate removed. V3 basin coupled math
 * is the sole entry criterion. D_k directionality is already embedded in the
 * basin via D_nonadverse/D_adverse terms.
 *
 * Exit conditions (evaluated by sentinel_monitor per signal_class='CH2'):
 *   EXIT-BASIN-BREAK — break_agreement >= 0.20
 *   EXIT-CALENDAR-CAP — age >= 25 days
 *
 * Data source: runtime_decisions_latest
 * Position sizing: 1.0% risk per trade
 */

import pg from "pg";
import { readFileSync } from "fs";
import { computeV3Basin } from "./v3_basin.mjs";

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
const CH2_BAR_COUNT_MIN    = 21;
const CH2_MIN_MARKET_CAP   = 500_000_000;
const ACCUMULATE_BASIN_MIN = 0.15;
// ENTRY-R10 carry governance. Fixed constant, from L5_CANONICAL_BASELINE's
// B_k rung measured WITHOUT its forward-looking "Rising 5d" filter.
export const CH2_CARRY_MIN = -0.50;
const BREAK_AGREEMENT_MAX  = 0.20;  // V3 spec exit threshold — reject entry if already in exit territory

function toFloat(v) {
  const n = parseFloat(v);
  return isFinite(n) ? n : null;
}
function toInt(v) {
  const n = parseInt(v, 10);
  return isFinite(n) ? n : null;
}

// Readings older than this are not a basis for a buy. The nightly rebuild
// runs every weekday close; four days covers a weekend plus a holiday.
// Receipt: from 2026-08-18 to 2026-09-15 the table never advanced and the
// entry door kept buying the same frozen list (Aug 27, Aug 31), re-buying
// three names the reading had just sold. Joseph's restart 2026-09-15: a stale
// table means no entries, said out loud in the log.
const CH2_READINGS_MAX_AGE_MS = 4 * 24 * 60 * 60 * 1000;

async function resolveLatestRun() {
  const res = await pool.query(
    `SELECT run_id, generated_at_utc FROM runtime_decisions_latest
     ORDER BY generated_at_utc DESC LIMIT 1`
  );
  if (!res.rows.length) throw new Error("[CH2-STRATEGIST] runtime_decisions_latest is empty");
  const generatedAt = res.rows[0].generated_at_utc ? new Date(res.rows[0].generated_at_utc) : null;
  const ageMs = generatedAt && Number.isFinite(generatedAt.getTime()) ? Date.now() - generatedAt.getTime() : null;
  return { runId: res.rows[0].run_id, generatedAt, ageMs };
}

export function readingsAreStale(ageMs, maxAgeMs = CH2_READINGS_MAX_AGE_MS) {
  return !Number.isFinite(ageMs) || ageMs < 0 || ageMs > maxAgeMs;
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
       r.snapshot_row_json,
       COALESCE(f.sector, 'Unknown') AS sector
     FROM runtime_decisions_latest r
     LEFT JOIN runtime_symbols s ON s.ticker = r.ticker
     LEFT JOIN l5_fundamentals_normalized f ON f.ticker = r.ticker
     WHERE r.run_id = $1
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
  const snap     = row.snapshot_row_json ?? {};
  const ticker   = String(row.ticker ?? "").trim().toUpperCase();
  const runId    = String(row.run_id ?? "").trim();
  const barCount = toInt(snap.bar_count ?? row.bar_count);

  if (!ticker)                                           return null;
  if (!runId)                                            return null;
  if (barCount === null || barCount < CH2_BAR_COUNT_MIN) return null;

  const basin = computeV3Basin({
    S_UF:    toFloat(snap.S_UF    ?? snap.s_uf),
    R_UF:    toFloat(snap.R_UF    ?? snap.r_uf),
    D_k:     toFloat(snap.D_k     ?? snap.d_k),
    M_k:     toFloat(snap.M_k     ?? snap.m_k),
    R_rev_k: toFloat(snap.R_rev_k ?? snap.r_rev_k),
    U_star_k:toFloat(snap.U_star_k?? snap.u_star_k),
    C_k:     toFloat(snap.C_k     ?? snap.c_k),
    P_k:     toFloat(snap.P_k     ?? snap.p_k),
    B_k:     toFloat(snap.B_k     ?? snap.b_k),
  });

  if (basin === null)                                          { console.log(`[CH2-STRATEGIST]   ${ticker} — REJECT tuple incomplete`); return null; }
  if (basin.decision_argmax !== "Accumulate")                  { console.log(`[CH2-STRATEGIST]   ${ticker} — REJECT argmax=${basin.decision_argmax}`); return null; }
  if (basin.accumulate_basin < ACCUMULATE_BASIN_MIN)           { console.log(`[CH2-STRATEGIST]   ${ticker} — REJECT acc=${basin.accumulate_basin.toFixed(4)} < ${ACCUMULATE_BASIN_MIN}`); return null; }
  if (basin.break_agreement >= BREAK_AGREEMENT_MAX)            { console.log(`[CH2-STRATEGIST]   ${ticker} — REJECT break=${basin.break_agreement.toFixed(4)} >= ${BREAK_AGREEMENT_MAX} (already in exit territory)`); return null; }

  // ── ENTRY-R10: carry governance (2026-09-21) ────────────────────────
  // The V3 basin does NOT read B_k on an Accumulate decision: carry_break is
  // multiplied by R_rev_k, and accumulate_basin by (1 - R_rev_k), so B_k
  // cancels algebraically on every buy. Carry has to be governed separately.
  //
  // Measured on quarantine_12k_l5_trades.csv (7,658 Accumulate signals,
  // 20-day forward hold), with NO forward-looking filter:
  //   Accumulate only                     57.1% WR | 7,290 signals
  //   + Close >= $5 + B_k > -0.50         62.9% WR | 3,359 signals
  //
  // The +5.8pp is real. The 81.4% in the L5_CANONICAL_BASELINE ladder is NOT:
  // that rung adds "Rising 5d", which is Return_5d > 0, and Return_5d is the
  // FORWARD five-day return (verified 400/400 against the raw bars). It
  // cannot be known at entry and is worth +17.6pp of pure lookahead.
  //
  // Threshold transfers: B_k > -0.50 passes 59.1% of production rows
  // (uf_core path, 2.65M rows) against 49.0% of the quarantine signals.
  const bkEntry = toFloat(snap.B_k ?? snap.b_k);
  if (!Number.isFinite(bkEntry))                               { console.log(`[CH2-STRATEGIST]   ${ticker} — REJECT B_k missing (ENTRY-R10 needs carry)`); return null; }
  if (bkEntry <= CH2_CARRY_MIN)                                { console.log(`[CH2-STRATEGIST]   ${ticker} — REJECT B_k=${bkEntry.toFixed(4)} <= ${CH2_CARRY_MIN} (ENTRY-R10 carry governance)`); return null; }

  return {
    ticker,
    run_id:       runId,
    signal_class: "CH2",
    s_uf:         toFloat(snap.S_UF ?? snap.s_uf),
    d_k:          toFloat(snap.D_k  ?? snap.d_k),
    bar_count:    barCount,
    b_k:          toFloat(snap.B_k  ?? snap.b_k),
    f_n:          toFloat(snap.F_n  ?? snap.f_n),
    sector:       String(row.sector ?? "Unknown").trim(),
    spy_dk:       null,
    v3_basin:     basin,
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
  const { runId, generatedAt, ageMs } = await resolveLatestRun();
  console.log(`[CH2-STRATEGIST] run_id=${runId} | readings generated ${generatedAt?.toISOString() ?? "unknown"} | age_h=${Number.isFinite(ageMs) ? (ageMs / 3.6e6).toFixed(1) : "n/a"}`);
  if (readingsAreStale(ageMs)) {
    console.log(`[CH2-STRATEGIST] READINGS STALE — table not rebuilt within ${CH2_READINGS_MAX_AGE_MS / 864e5} days; no entries on old physics`);
    return [];
  }

  // Diagnostic: candidate pool before V3 basin filter
  try {
    const diag = await pool.query(
      `SELECT COUNT(*) AS cnt FROM runtime_decisions_latest r
       LEFT JOIN runtime_symbols s ON s.ticker = r.ticker
       LEFT JOIN l5_fundamentals_normalized f ON f.ticker = r.ticker
       WHERE r.run_id = $1 AND r.ticker != 'SPY'
         AND CAST(NULLIF(r.snapshot_row_json->>'bar_count','') AS INTEGER) > $2
         AND COALESCE(NULLIF(s.market_cap,0), f.market_cap, 0) >= $3`,
      [runId, CH2_BAR_COUNT_MIN - 1, CH2_MIN_MARKET_CAP]
    );
    console.log(`[CH2-DIAG] run_id=${runId} | pre-basin candidates: ${diag.rows[0].cnt}`);
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

  // Sort: epoch-favored sectors first, then by accumulate_basin DESC
  governed.sort((a, b) => (b.epoch_pressure - a.epoch_pressure) || (b.v3_basin.accumulate_basin - a.v3_basin.accumulate_basin));

  console.log(`[CH2-STRATEGIST] ${rows.length} candidates → ${signals.length} passed V3 basin → ${deduped.length} dedup → ${governed.length} after epoch governance`);
  for (const s of governed) {
    console.log(`[CH2-STRATEGIST]   ${s.ticker} | acc=${s.v3_basin.accumulate_basin.toFixed(4)} | break=${s.v3_basin.break_agreement.toFixed(4)} | sector=${s.sector} | epoch=${s.epoch_pressure?.toFixed(2) ?? "?"}`);
  }

  return governed;
}

export async function closeCh2StrategistPool() {
  await pool.end();
}
