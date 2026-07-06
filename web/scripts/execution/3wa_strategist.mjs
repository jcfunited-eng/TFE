/**
 * web/scripts/execution/3wa_strategist.mjs
 * PEE-1 Three-Wave Alignment Strategist
 *
 * Queries runtime_decisions_latest for the current run_id.
 * Joins species_profiles to classify signals:
 *
 *   signal_class = '3WA'      — Wave 1 + Wave 3 + calm species
 *   signal_class = '1+3'      — Wave 1 + Wave 3 without calm
 *   signal_class = 'standard' — Wave 3 active but Wave 1 conditions not met
 *
 * Wave 1 conditions — canonical Structure A (D2 / SHA 9de8471):
 *   1. bar_count ∈ [1, 20]           (structural ground state)
 *   2. s_n       ∈ [0.954, 0.969]    (ordered structural regime)
 *   3. |Δs_n|    ∈ [0.67,  0.72]     (crystallisation magnitude)
 *   4. D_k(t-1) = 0  AND  D_k(t) = 1 (first accumulate trigger)
 *   Validated: 372 signals, WR_20d=92.2%, Wilson 95% CI [89.0%, 94.5%]
 *
 * Wave 3: SPY D_k = 1 (market structural expansion)
 * Wave 2: species = 'calm' from species_profiles table
 *
 * If SPY is not in structural expansion → returns [].
 */

import pg from "pg";
import { computeRegimeExposure } from "../l5_unified_shadow.mjs";

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

const NEW_LISTING_BAR_THRESHOLD = 20;
const W1_S_N_MIN       = 0.954;
const W1_S_N_MAX       = 0.969;
const W1_DELTA_S_N_MIN = 0.67;
const W1_DELTA_S_N_MAX = 0.72;

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
 * Fetch all Accumulate rows for the given run_id, plus the previous
 * snapshot row per ticker for Wave 1 Δs_n and D_k(t-1) evaluation.
 *
 * Uses a LATERAL join against runtime_decisions_history to retrieve
 * the most recent prior snapshot per ticker. s_n is a top-level column
 * (indexed by idx_rdh_ticker_date) so no JSON parsing is needed for the
 * previous s_n. D_k(t-1) comes from prev_snapshot_row_json.
 *
 * Option A chosen over Option B (JS-side pairing) for two reasons:
 *   1. Single query round-trip vs two fetches.
 *   2. Top-level s_n column in runtime_decisions_history avoids JSON
 *      extraction overhead; the idx_rdh_ticker_date index makes the
 *      LATERAL subquery O(log N) per ticker.
 */
async function fetchCandidateRows(runId) {
  const res = await pool.query(
    `SELECT
       rdl.ticker,
       rdl.run_id,
       rdl.decision_label,
       rdl.snapshot_row_json,
       rdh_prev.s_n                AS prev_s_n,
       rdh_prev.snapshot_row_json  AS prev_snapshot_row_json
     FROM runtime_decisions_latest rdl
     LEFT JOIN LATERAL (
       SELECT s_n, snapshot_row_json
       FROM runtime_decisions_history
       WHERE ticker = rdl.ticker
         AND generated_at_utc < rdl.generated_at_utc
       ORDER BY generated_at_utc DESC
       LIMIT 1
     ) rdh_prev ON true
     WHERE rdl.run_id = $1
       AND rdl.decision_label = 'Accumulate'
       AND rdl.ticker != 'SPY'
     ORDER BY rdl.ticker ASC`,
    [runId]
  );
  return res.rows;
}

/**
 * Fetch species classifications from species_profiles table.
 * Returns a Map of ticker → classification ('calm', 'normal', 'volatile').
 */
async function fetchSpeciesProfiles() {
  const res = await pool.query(
    `SELECT ticker, classification FROM species_profiles`
  );
  const map = new Map();
  for (const row of res.rows) {
    map.set(String(row.ticker).trim().toUpperCase(), row.classification);
  }
  return map;
}

/**
 * Parse a DB row into a validated signal object.
 * Returns null if decision_label is not Accumulate or required fields missing.
 * Tags signal_class based on Wave 1/2/3 alignment.
 *
 * Wave 1 uses canonical Structure A condition (D2):
 *   bar_count ∈ [1,20], s_n ∈ [0.954,0.969], |Δs_n| ∈ [0.67,0.72],
 *   D_k(t-1)=0, D_k(t)=1
 * prev_s_n and prev_snapshot_row_json come from the LATERAL join in
 * fetchCandidateRows (runtime_decisions_history, most recent prior row).
 */
function parseSignal(row, spyDk, speciesMap) {
  const snap     = row.snapshot_row_json      ?? {};
  const prevSnap = row.prev_snapshot_row_json ?? {};
  const ticker   = String(row.ticker ?? "").trim().toUpperCase();
  const runId    = String(row.run_id  ?? "").trim();
  const barCount = toInt(snap.bar_count   ?? row.bar_count);
  const sUf      = toFloat(snap.S_UF     ?? snap.s_uf);
  const dk       = toInt(snap.D_k        ?? snap.d_k);
  const fn       = toFloat(snap.F_n      ?? snap.f_n);
  const bk       = toFloat(snap.B_k      ?? snap.b_k);
  const neighborWR = toFloat(snap.neighbor_wr);
  const sN       = toFloat(snap.s_n);
  const snPrev   = toFloat(row.prev_s_n  ?? prevSnap.s_n);
  const dKPrev   = toInt(prevSnap.D_k    ?? prevSnap.d_k);
  const absDeltaSN = (sN !== null && snPrev !== null) ? Math.abs(sN - snPrev) : null;

  if (!ticker)  return null;
  if (!runId)   return null;

  // Wave 1: canonical Structure A (D2 / structural_wave_alignment_spec.tex Definition 1)
  // Close >= $5 is guaranteed upstream by decision_label='Accumulate' (tfe_l5_baseline.py MIN_PRICE)
  const wave1 =
       barCount   !== null && barCount   >= 1               && barCount   <= NEW_LISTING_BAR_THRESHOLD
    && sN         !== null && sN         >= W1_S_N_MIN       && sN         <= W1_S_N_MAX
    && absDeltaSN !== null && absDeltaSN >= W1_DELTA_S_N_MIN && absDeltaSN <= W1_DELTA_S_N_MAX
    && dk         === 1
    && dKPrev     === 0;

  // Wave 2: species classification
  const species = speciesMap.get(ticker) ?? "unknown";
  const wave2 = species === "calm";

  // Classify signal
  let signalClass;
  if (wave1 && wave2) {
    signalClass = "3WA";
  } else if (wave1) {
    signalClass = "1+3";
  } else {
    signalClass = "standard";
  }

  return {
    ticker,
    run_id:        runId,
    signal_class:  signalClass,
    species,
    spy_dk:        spyDk,
    s_uf:          sUf,
    s_n:           sN,
    abs_delta_s_n: absDeltaSN,
    bar_count:     barCount,
    d_k:           dk,
    d_k_prev:      dKPrev,
    f_n:           fn,
    b_k:           bk,
    neighbor_wr:   neighborWR,
  };
}

/**
 * Main entry point.
 * Returns array of validated 3WA signal objects ready for alpaca_bridge.
 * Returns [] if Wave 3 (SPY D_k) is not active.
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

export async function get3WASignals() {
  const runId = await resolveLatestRunId();
  console.log(`[STRATEGIST] run_id=${runId}`);

  // SPY D_k is informational, NOT a Wave 1 selection gate.
  // Design doc §4 defines Wave 1 gate on individual ticker transition
  // (D_k(t-1)=0 → D_k(t)=+1), s_n bands, |Δs_n| bands, bar_count.
  // Design doc §15/line 128: "W3 is not used as a v1.0 selection condition."
  // Backtest C13 = 0: 92% WR population never overlapped with SPY D_k=+1.
  const spy = await fetchSpyRow(runId);
  const spyDk = spy?.d_k ?? null;
  console.log(`[STRATEGIST] SPY D_k=${spyDk ?? "unknown"} (informational — not a Wave 1 gate)`);

  // ── Regime exposure gate (position capacity check) ──────────────────
  {
    const openRes = await pool.query(
      `SELECT COUNT(*) AS cnt FROM personal_trade_ledger WHERE status IN ('submitted', 'filled')`
    );
    const openCount = parseInt(openRes.rows[0]?.cnt ?? "0", 10);

    const regime = computeRegimeExposure(spyDk, openCount, 30, 0);
    console.log(`[STRATEGIST] Regime: ${regime.reason} | openPositions=${openCount}`);

    if (!regime.newEntriesAllowed) {
      console.log(`[STRATEGIST] REGIME BLOCK — ${regime.reason}`);
      return [];
    }
  }

  // Fetch species profiles and candidates
  let speciesMap = new Map();
  let rows;
  try {
    [speciesMap, rows] = await Promise.all([
      fetchSpeciesProfiles(),
      fetchCandidateRows(runId),
    ]);
    console.log(`[STRATEGIST] species_profiles loaded: ${speciesMap.size} tickers`);
  } catch (speciesErr) {
    // species_profiles table missing or query failed — degrade gracefully.
    // Signals tag as '1+3' or 'standard' instead of '3WA'. No sizing change
    // upward, no additional trades. The only effect is down-tagging: signals
    // that would be '3WA' (3.5% sizing) become '1+3' (2.5% sizing).
    console.warn(`[STRATEGIST] species_profiles unavailable: ${speciesErr.message} — degrading to empty species map`);
    speciesMap = new Map();
    rows = rows ?? await fetchCandidateRows(runId);
  }

  const signals = rows.map(r => parseSignal(r, spyDk, speciesMap)).filter(Boolean);

  // Exclude tickers that already have open positions
  const openTickers = await fetchOpenPositionTickers();
  const deduped = signals.filter(s => {
    if (openTickers.has(s.ticker)) {
      console.log(`[STRATEGIST]   ${s.ticker} — SKIPPED (open position exists)`);
      return false;
    }
    return true;
  });

  // Report signal_class distribution
  const classCounts = { "3WA": 0, "1+3": 0, "standard": 0 };
  for (const s of deduped) {
    classCounts[s.signal_class] = (classCounts[s.signal_class] || 0) + 1;
  }
  console.log(`[STRATEGIST] ${rows.length} candidates → ${signals.length} valid → ${deduped.length} after dedup`);
  console.log(`[STRATEGIST] signal_class distribution: 3WA=${classCounts["3WA"]} | 1+3=${classCounts["1+3"]} | standard=${classCounts["standard"]}`);
  for (const s of deduped) {
    console.log(`[STRATEGIST]   ${s.ticker} | signal_class=${s.signal_class} | species=${s.species} | bar_count=${s.bar_count} | s_n=${s.s_n} | |Δs_n|=${s.abs_delta_s_n}`);
  }

  return deduped;
}

export async function closeStrategistPool() {
  await pool.end();
}
