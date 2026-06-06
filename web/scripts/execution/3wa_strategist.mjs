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
 * Wave 1 conditions (validated at 84.6% on n=371):
 *   1. decision_label = 'Accumulate'
 *   2. bar_count <= 20  (structural ground state)
 *   3. s_uf > 0         (structural entropy order parameter present)
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
 * Fetch all Accumulate rows for the given run_id.
 * Wave 1 bar_count filtering happens in parseSignal (tagging, not exclusion).
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
     ORDER BY ticker ASC`,
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
 */
function parseSignal(row, spyDk, speciesMap) {
  const snap     = row.snapshot_row_json ?? {};
  const ticker   = String(row.ticker ?? "").trim().toUpperCase();
  const runId    = String(row.run_id ?? "").trim();
  const barCount = toInt(snap.bar_count ?? row.bar_count);
  const sUf      = toFloat(snap.S_UF ?? snap.s_uf);
  const dk       = toInt(snap.D_k ?? snap.d_k);
  const fn       = toFloat(snap.F_n ?? snap.f_n);
  const bk       = toFloat(snap.B_k ?? snap.b_k);
  const neighborWR = toFloat(snap.neighbor_wr);

  if (!ticker)  return null;
  if (!runId)   return null;
  if (spyDk !== 1) return null;  // Wave 3 not active — no signals at all

  // Wave 1 conditions (validated set — do not modify)
  const wave1 = barCount !== null && barCount >= 1 && barCount <= NEW_LISTING_BAR_THRESHOLD
             && sUf !== null && sUf > 0;

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
    run_id:       runId,
    signal_class: signalClass,
    species,
    spy_dk:       spyDk,
    s_uf:         sUf,
    bar_count:    barCount,
    d_k:          dk,
    f_n:          fn,
    b_k:          bk,
    neighbor_wr:  neighborWR,
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
    console.log(`[STRATEGIST]   ${s.ticker} | signal_class=${s.signal_class} | species=${s.species} | bar_count=${s.bar_count} | s_uf=${s.s_uf}`);
  }

  return deduped;
}

export async function closeStrategistPool() {
  await pool.end();
}
