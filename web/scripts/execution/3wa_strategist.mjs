/**
 * web/scripts/execution/3wa_strategist.mjs
 * PEE-1 Three-Wave Alignment Strategist
 *
 * Queries runtime_decisions_latest for the current run_id.
 * Returns only signals where ALL of the following are true:
 *   1. decision_label = 'Accumulate'
 *   2. bar_count <= 20  (Wave 1: structural ground state)
 *   3. SPY D_k = 1      (Wave 3: market structural expansion)
 *   4. s_uf > 0         (structural entropy order parameter present)
 *
 * Any missing field → signal is excluded. No fallbacks.
 *
 * Also queries SPY's row to confirm Wave 3 is active before returning
 * any signals. If SPY is not in structural expansion → returns [].
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
});

const NEW_LISTING_BAR_THRESHOLD = 20;

function toFloat(v) {
  const n = parseFloat(v);
  return isFinite(n) ? n : null;
}
function toInt(v) {
  const n = parseInt(v, 10);
  return isFinite(n) ? n : null;
}

/**
 * Resolve the latest run_id from runtime_decisions_latest.
 */
async function resolveLatestRunId() {
  const res = await pool.query(
    `SELECT run_id FROM runtime_decisions_latest
     ORDER BY generated_at_utc DESC LIMIT 1`
  );
  if (!res.rows.length) throw new Error("[STRATEGIST] runtime_decisions_latest is empty");
  return res.rows[0].run_id;
}

/**
 * Fetch SPY's snapshot row for the given run_id.
 * Returns null if SPY not present.
 */
async function fetchSpyRow(runId) {
  const res = await pool.query(
    `SELECT snapshot_row_json FROM runtime_decisions_latest
     WHERE ticker = 'SPY' AND run_id = $1 LIMIT 1`,
    [runId]
  );
  if (!res.rows.length) return null;
  const snap = res.rows[0].snapshot_row_json ?? {};
  return {
    d_k:      toInt(snap.D_k ?? snap.d_k),
    decision: String(snap.decision_label ?? res.rows[0].decision_label ?? "").trim(),
  };
}

/**
 * Fetch all Accumulate rows for the given run_id with bar_count <= 20.
 */
async function fetchCandidateRows(runId) {
  const res = await pool.query(
    `SELECT
       ticker,
       run_id,
       decision_label,
       bar_count,
       snapshot_row_json
     FROM runtime_decisions_latest
     WHERE run_id = $1
       AND decision_label = 'Accumulate'
       AND CAST(NULLIF(snapshot_row_json->>'bar_count', '') AS INTEGER) <= $2
       AND ticker != 'SPY'
     ORDER BY ticker ASC`,
    [runId, NEW_LISTING_BAR_THRESHOLD]
  );
  return res.rows;
}

/**
 * Parse a DB row into a validated signal object.
 * Returns null if any required field is missing or invalid.
 */
function parseSignal(row, spyDk) {
  const snap     = row.snapshot_row_json ?? {};
  const ticker   = String(row.ticker ?? "").trim().toUpperCase();
  const runId    = String(row.run_id ?? "").trim();
  const barCount = toInt(snap.bar_count ?? row.bar_count);
  const sUf      = toFloat(snap.S_UF ?? snap.s_uf);
  const dk       = toInt(snap.D_k ?? snap.d_k);
  const fn       = toFloat(snap.F_n ?? snap.f_n);
  const bk       = toFloat(snap.B_k ?? snap.b_k);

  // Binary checks — all must pass
  if (!ticker)                                return null;
  if (!runId)                                 return null;
  if (barCount === null || barCount < 1 || barCount > NEW_LISTING_BAR_THRESHOLD) return null;
  if (sUf === null || sUf <= 0)              return null;
  if (spyDk !== 1)                            return null;  // Wave 3 not active

  return {
    ticker,
    run_id:       runId,
    signal_class: "3WA",
    spy_dk:       spyDk,
    s_uf:         sUf,
    bar_count:    barCount,
    d_k:          dk,
    f_n:          fn,
    b_k:          bk,
  };
}

/**
 * Main entry point.
 * Returns array of validated 3WA signal objects ready for alpaca_bridge.
 * Returns [] if Wave 3 (SPY D_k) is not active.
 */
export async function get3WASignals() {
  const runId = await resolveLatestRunId();
  console.log(`[STRATEGIST] run_id=${runId}`);

  // Wave 3 gate — check SPY first
  const spy = await fetchSpyRow(runId);
  if (!spy) {
    console.log("[STRATEGIST] SPY not found in runtime_decisions_latest — Wave 3 INACTIVE");
    return [];
  }

  const spyDk = spy.d_k;
  if (spyDk !== 1) {
    console.log(`[STRATEGIST] SPY D_k=${spyDk} — Wave 3 INACTIVE — no signals emitted`);
    return [];
  }

  console.log(`[STRATEGIST] SPY D_k=1 — Wave 3 ACTIVE`);

  // Fetch and parse candidates
  const rows    = await fetchCandidateRows(runId);
  const signals = rows.map(r => parseSignal(r, spyDk)).filter(Boolean);

  console.log(`[STRATEGIST] ${rows.length} candidates → ${signals.length} valid 3WA signals`);
  for (const s of signals) {
    console.log(`[STRATEGIST]   ${s.ticker} | bar_count=${s.bar_count} | s_uf=${s.s_uf} | D_k=${s.d_k}`);
  }

  return signals;
}

export async function closeStrategistPool() {
  await pool.end();
}
