/**
 * web/scripts/execution/ch2_strategist.mjs
 * PEE-1 Chapter 2 Strategist — Mid S_UF Acceleration Layer
 *
 * Independent execution path. Does NOT touch or depend on 3WA (Chapter 1) logic.
 *
 * Entry conditions (ALL must be true):
 *   1. decision_label = 'Accumulate'
 *   2. regime = 'TRANSITIONAL'
 *   3. S_UF ∈ [0.5, 0.75)  — mid-conviction acceleration band
 *   4. D_k = 1              — directional expansion confirmed
 *   5. bar_count > 20       — established stock (not a new listing / 3WA candidate)
 *
 * Exit conditions (evaluated by sentinel_monitor per signal_class='CH2'):
 *   EXIT A — Acceleration complete:  S_UF crosses above 0.75
 *   EXIT B — Directional collapse:   D_k flips to 0 or -1
 *
 * Data source: runtime_decisions_latest (same as 3WA strategist)
 * Position sizing: 1.0% risk per trade (vs 1.5% for 3WA — lower conviction)
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

// ── Chapter 2 entry thresholds ────────────────────────────────────────────
const CH2_S_UF_MIN        = 0.50;   // inclusive
const CH2_S_UF_MAX        = 0.75;   // exclusive — above this is 3WA territory
const CH2_BAR_COUNT_MIN   = 21;     // must be established (> 3WA threshold of 20)
const CH2_REQUIRED_DK     = 1;      // directional expansion required
const CH2_REQUIRED_REGIME = "TRANSITIONAL";

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
       ticker,
       run_id,
       decision_label,
       snapshot_row_json
     FROM runtime_decisions_latest
     WHERE run_id = $1
       AND decision_label = 'Accumulate'
       AND ticker != 'SPY'
       AND CAST(NULLIF(snapshot_row_json->>'bar_count', '') AS INTEGER) > $2
       AND CAST(NULLIF(snapshot_row_json->>'S_UF', '') AS DOUBLE PRECISION) >= $3
       AND CAST(NULLIF(snapshot_row_json->>'S_UF', '') AS DOUBLE PRECISION) <  $4
     ORDER BY ticker ASC`,
    [runId, CH2_BAR_COUNT_MIN - 1, CH2_S_UF_MIN, CH2_S_UF_MAX]
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

  // Hard entry gates — all must pass
  if (!ticker)                                          return null;
  if (!runId)                                           return null;
  if (barCount === null || barCount < CH2_BAR_COUNT_MIN) return null;
  if (sUf === null || sUf < CH2_S_UF_MIN || sUf >= CH2_S_UF_MAX) return null;
  if (dk !== CH2_REQUIRED_DK)                          return null;
  if (regime !== CH2_REQUIRED_REGIME)                  return null;

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
    // No spy_dk gate for Ch2 — D_k=1 on the ticker itself is sufficient
    spy_dk:       null,
  };
}

/**
 * Main entry point.
 * Returns array of validated Ch2 signal objects ready for alpaca_bridge.
 */
export async function getCh2Signals() {
  const runId = await resolveLatestRunId();
  console.log(`[CH2-STRATEGIST] run_id=${runId}`);

  const rows    = await fetchCandidateRows(runId);
  const signals = rows.map(parseSignal).filter(Boolean);

  console.log(`[CH2-STRATEGIST] ${rows.length} candidates → ${signals.length} valid Ch2 signals`);
  for (const s of signals) {
    console.log(`[CH2-STRATEGIST]   ${s.ticker} | bar_count=${s.bar_count} | s_uf=${s.s_uf} | D_k=${s.d_k} | regime=${s.regime}`);
  }

  return signals;
}

export async function closeCh2StrategistPool() {
  await pool.end();
}
