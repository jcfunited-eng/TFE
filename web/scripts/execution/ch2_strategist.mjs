/**
 * web/scripts/execution/ch2_strategist.mjs
 * PEE-1 Chapter 2 Strategist — FIELD-R1 (the field governs exposure; the
 * particle's reporting cycle governs selection). Claude's law, 2026-09-30,
 * on Joe's word: "as long as it's a positive move go for it." One system:
 * this replaces the V3 basin as the entry decision. Receipt:
 * docs/CH2_CANON_KERNEL_FULL_BAR_20260930.md (book: every year positive
 * 2022–2026, +$54k–$68k on $100k, one day in four in the market).
 *
 * Entry conditions (ALL must be true):
 *   1. FIELD-R1: today's field state (ch2_field_state, written nightly by
 *      tools/ch2_field_nightly_db.py from the pool's own bars) says
 *      field_long — an epic window, a field-wide down-release, or a
 *      charging & quiet field, never while the field's 20-day release
 *      polarity is UP, and in a bear regime only the epic window.
 *   2. the name is in today's ch2_field_eligible: tradeable by the
 *      field job's filters and 61–95 days into its reporting cycle
 *      (not a late filer, not 0–3 days after a report).
 *   3. bar_count > 20  — established stock
 *   4. avg dollar volume >= $2M  — liquidity floor (ENTRY-R5, re-based 2026-09-23)
 *   5. asset_type = 'stock'  — no funds, no crypto, no indexes (ENTRY-R11, Joe 2026-09-23)
 *   6. ENTRY-R12: the reading's last bar is the run's session
 *   Order: the field's priority (epic 0 > down-release 1 > charging 2),
 *   then the name closest to its report first.
 *   The V3 basin is still computed and recorded on each signal for the
 *   ledger; it no longer decides.
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
// ENTRY-R5 liquidity floor, re-based 2026-09-23. Claude's rule, not Joe's.
// Codex wrote it 2026-05-04 as market_cap >= $500M "because tiny-caps have
// fill problems and wide spreads". Receipt (docs/CH2_ENTRY_POOL_20260923.md):
//   runtime_symbols.market_cap             54 of 11,685 tickers, every run since March
//   l5_fundamentals_normalized.market_cap  1,985 of 5,056 rows, MIXED UNITS
//       (AAPL 3.71e12 dollars, BFST 944.4 millions, HBCP 5.6e14 garbage)
//   => 9,675 of 11,685 tickers (83%) were dropped for having NO cap on file,
//      not for being small. The pool was 1,389. On 2026-09-23 every basin
//      passer inside that pool was already held and $49,740 sat idle.
// Average dollar volume (price x runtime_metrics_latest.avg_volume) measures
// the same thing directly and exists for 11,506 of 11,513 tickers. $2M a day
// against a ~$2,500 order is about 0.1% of one day's trade. Passes 5,620.
export const CH2_MIN_AVG_DOLLAR_VOLUME = 2_000_000;
// ENTRY-R11, Joe's rule 2026-09-23: "funds should come out". The cap filter
// had excluded funds by accident (funds have no market cap). Now explicit.
// snapshot asset_type on the 2026-09-23 run: stock 5,986 | etf 5,664 |
// crypto 25 | index 10. Only 'stock' enters.
export const CH2_ENTRY_ASSET_TYPE = "stock";
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

// ENTRY-R5 as one pure check, so it can be tested without a database. The
// SQL in fetchCandidateRows applies the same arithmetic.
export function liquidityFloorPasses(price, avgVolume, minDollarVolume = CH2_MIN_AVG_DOLLAR_VOLUME) {
  const p = toFloat(price);
  const v = toFloat(avgVolume);
  if (p === null || v === null) return false;
  return p * v >= minDollarVolume;
}

// ENTRY-R12 as one pure check: a reading is current when its last bar is on
// or after the run's session date. Missing or unparseable dates are stale.
export function readingIsCurrent(lastBarTimestamp, sessionDate) {
  const bar = String(lastBarTimestamp ?? "").slice(0, 10);
  const session = String(sessionDate ?? "").slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(bar) || !/^\d{4}-\d{2}-\d{2}$/.test(session)) return false;
  return bar >= session;
}

// The run's session = the most common last-bar date across the whole run.
async function resolveSessionDate(runId) {
  const res = await pool.query(
    `SELECT LEFT(snapshot_row_json->>'last_bar_timestamp', 10) AS d, COUNT(*) AS n
       FROM runtime_decisions_latest
      WHERE run_id = $1 AND snapshot_row_json->>'last_bar_timestamp' IS NOT NULL
      GROUP BY 1 ORDER BY n DESC, d DESC LIMIT 1`,
    [runId]
  );
  return res.rows[0]?.d ?? null;
}

// ENTRY-R11 as one pure check. The SQL in fetchCandidateRows applies the same test.
export function entryAssetTypeAllowed(assetType) {
  return String(assetType ?? "").trim().toLowerCase() === CH2_ENTRY_ASSET_TYPE;
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
// ── FIELD-R1: today's field state and eligible names ───────────────────────
// Written by tools/ch2_field_nightly_db.py after the close. The state is as
// of the last closed session; the entry pass the next morning reads it. If
// it is older than the readings' session by more than 3 calendar days the
// field is unknown and nothing is bought (safe default).
export const CH2_FIELD_MAX_LAG_DAYS = 3;

export function fieldStateIsCurrent(asOf, sessionDate, maxLagDays = CH2_FIELD_MAX_LAG_DAYS) {
  if (!asOf || !sessionDate) return false;
  const a = new Date(String(asOf).slice(0, 10) + "T00:00:00Z").getTime();
  const b = new Date(String(sessionDate).slice(0, 10) + "T00:00:00Z").getTime();
  if (!Number.isFinite(a) || !Number.isFinite(b)) return false;
  return (b - a) / 864e5 <= maxLagDays;
}

async function fetchFieldState() {
  const res = await pool.query(`SELECT as_of::text AS as_of, state FROM ch2_field_state ORDER BY as_of DESC LIMIT 1`);
  if (!res.rows.length) return null;
  const row = res.rows[0];
  const state = typeof row.state === "string" ? JSON.parse(row.state) : row.state;
  return { as_of: row.as_of, ...state };
}

async function fetchFieldEligible(asOf) {
  const res = await pool.query(`SELECT ticker, dsl, age, priority FROM ch2_field_eligible WHERE as_of = $1::date`, [asOf]);
  const out = new Map();
  for (const r of res.rows) out.set(String(r.ticker).trim().toUpperCase(), { dsl: toInt(r.dsl), age: toInt(r.age), priority: toInt(r.priority) });
  return out;
}

// One filer, one slot (FIELD-R1, 2026-10-02): LEN and LEN.B are one company
// reporting once; the reporting cycle is the filer's, not the share class's.
// The filer key is the company name when the symbol table has it, else the
// ticker's root before a share-class suffix (LEN.B → LEN, BRK-B → BRK).
export function filerKey(ticker, companyName) {
  const name = String(companyName ?? "").trim().toUpperCase().replace(/[^A-Z0-9]+/g, " ").trim();
  if (name) return "name:" + name;
  return "root:" + String(ticker ?? "").trim().toUpperCase().split(/[.\-]/)[0];
}

// The signal a FIELD-R1 entry carries: the tuple fields for the ledger
// (recorded, not decided on), the field state, and the name's cycle position.
function parseFieldSignal(row, elig, field) {
  const snap     = row.snapshot_row_json ?? {};
  const ticker   = String(row.ticker ?? "").trim().toUpperCase();
  const runId    = String(row.run_id ?? "").trim();
  const barCount = toInt(snap.bar_count ?? row.bar_count);
  if (!ticker || !runId)                                 return null;
  if (barCount === null || barCount < CH2_BAR_COUNT_MIN) return null;
  const basin = computeV3Basin({
    S_UF: toFloat(snap.S_UF ?? snap.s_uf), R_UF: toFloat(snap.R_UF ?? snap.r_uf), D_k: toFloat(snap.D_k ?? snap.d_k),
    M_k: toFloat(snap.M_k ?? snap.m_k), R_rev_k: toFloat(snap.R_rev_k ?? snap.r_rev_k), U_star_k: toFloat(snap.U_star_k ?? snap.u_star_k),
    C_k: toFloat(snap.C_k ?? snap.c_k), P_k: toFloat(snap.P_k ?? snap.p_k), B_k: toFloat(snap.B_k ?? snap.b_k),
  });
  return {
    ticker, run_id: runId, signal_class: "CH2",
    s_uf: toFloat(snap.S_UF ?? snap.s_uf), d_k: toFloat(snap.D_k ?? snap.d_k), bar_count: barCount,
    b_k: toFloat(snap.B_k ?? snap.b_k), f_n: toFloat(snap.F_n ?? snap.f_n),
    sector: String(row.sector ?? "Unknown").trim(), spy_dk: null,
    filer: filerKey(ticker, row.company_name),
    v3_basin: basin,
    entry_law: "FIELD-R1",
    field: { as_of: field.as_of, priority: field.priority, rules: field.rules, bear: field.bear, phase: field.phase, polarity20: field.polarity20,
             slow120: field.slow120, temperature: field.temperature, releasing: field.releasing },
    cycle: { dsl: elig.dsl, age: elig.age },
    priority: elig.priority,
  };
}

async function fetchCandidateRows(runId) {
  const res = await pool.query(
    `SELECT
       r.ticker,
       r.run_id,
       r.snapshot_row_json,
       COALESCE(f.sector, 'Unknown') AS sector,
       COALESCE(s.company_name, '') AS company_name
     FROM runtime_decisions_latest r
     LEFT JOIN runtime_metrics_latest m ON m.ticker = r.ticker
     LEFT JOIN l5_fundamentals_normalized f ON f.ticker = r.ticker
     LEFT JOIN runtime_symbols s ON s.ticker = r.ticker
     WHERE r.run_id = $1
       AND r.ticker != 'SPY'
       AND CAST(NULLIF(r.snapshot_row_json->>'bar_count', '') AS INTEGER) > $2
       AND CAST(NULLIF(r.snapshot_row_json->>'price', '') AS DOUBLE PRECISION)
           * COALESCE(m.avg_volume, 0) >= $3
       AND LOWER(TRIM(COALESCE(r.snapshot_row_json->>'asset_type', ''))) = $4
     ORDER BY r.ticker ASC`,
    [runId, CH2_BAR_COUNT_MIN - 1, CH2_MIN_AVG_DOLLAR_VOLUME, CH2_ENTRY_ASSET_TYPE]
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
       LEFT JOIN runtime_metrics_latest m ON m.ticker = r.ticker
       WHERE r.run_id = $1 AND r.ticker != 'SPY'
         AND CAST(NULLIF(r.snapshot_row_json->>'bar_count','') AS INTEGER) > $2
         AND CAST(NULLIF(r.snapshot_row_json->>'price','') AS DOUBLE PRECISION)
             * COALESCE(m.avg_volume, 0) >= $3
         AND LOWER(TRIM(COALESCE(r.snapshot_row_json->>'asset_type',''))) = $4`,
      [runId, CH2_BAR_COUNT_MIN - 1, CH2_MIN_AVG_DOLLAR_VOLUME, CH2_ENTRY_ASSET_TYPE]
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

  const allRows = await fetchCandidateRows(runId);

  // ── ENTRY-R12 (Claude 2026-09-29): never buy on a reading whose last bar
  // is older than the run's session. The nightly refresh swallows provider
  // errors and silently reuses cached bars, so a name can carry today's
  // run_id on last week's prices: on the 09-29 run 9,652 names were read on
  // the 09-28 bar and 1,220 on 09-25 or older (FNRN and SIND among the
  // holdings). The session is the run's own most common last-bar date — no
  // calendar needed. A stale reading is not a basis for a buy.
  const sessionDate = await resolveSessionDate(runId);
  const rows = allRows.filter(row => {
    const lbt = row.snapshot_row_json?.last_bar_timestamp;
    if (readingIsCurrent(lbt, sessionDate)) return true;
    console.log(`[CH2-STRATEGIST]   ${row.ticker} — REJECT stale reading: last bar ${String(lbt ?? "none").slice(0, 10)} < session ${sessionDate} (ENTRY-R12)`);
    return false;
  });
  console.log(`[CH2-DIAG] session=${sessionDate} | current readings: ${rows.length} of ${allRows.length} candidates`);

  // ── FIELD-R1: the field governs exposure ─────────────────────────────
  let field = null;
  try { field = await fetchFieldState(); } catch (e) { console.log(`[CH2-FIELD] state unavailable: ${e.message}`); }
  if (!field) { console.log("[CH2-FIELD] NO FIELD STATE — no entries (the nightly field job has not written ch2_field_state)"); return []; }
  if (!fieldStateIsCurrent(field.as_of, sessionDate)) {
    console.log(`[CH2-FIELD] FIELD STATE STALE — as_of ${field.as_of} vs session ${sessionDate} (> ${CH2_FIELD_MAX_LAG_DAYS}d) — no entries`);
    return [];
  }
  console.log(`[CH2-FIELD] as_of=${field.as_of} | field_long=${field.field_long} | priority=${field.priority} | bear=${field.bear} | slow120=${field.slow120} | phase=${field.phase} | polarity20=${field.polarity20} | releasing=${field.releasing} (${field.releasing_band}) | temperature=${field.temperature} | epic_window=${field.epic_window} | rules=${JSON.stringify(field.rules)} | eligible=${field.eligible_names}`);
  if (!field.field_long) { console.log("[CH2-FIELD] FIELD NOT LONG — no entries today"); return []; }

  const eligible = await fetchFieldEligible(field.as_of);
  const signals = [];
  for (const row of rows) {
    const t = String(row.ticker ?? "").trim().toUpperCase();
    const e = eligible.get(t);
    if (!e) continue;
    const sig = parseFieldSignal(row, e, field);
    if (sig) signals.push(sig);
  }

  // Exclude tickers that already have open positions
  const openTickers = await fetchOpenPositionTickers();
  const openFilerNames = new Map();
  try {
    const q = await pool.query(`SELECT ticker, company_name FROM runtime_symbols WHERE ticker = ANY($1)`, [[...openTickers]]);
    for (const r of q.rows) openFilerNames.set(String(r.ticker).trim().toUpperCase(), r.company_name);
  } catch {}
  const deduped = signals.filter(s => {
    if (openTickers.has(s.ticker)) {
      console.log(`[CH2-STRATEGIST]   ${s.ticker} — SKIPPED (open position exists)`);
      return false;
    }
    return true;
  });

  // Order: the field's priority first (epic 0 > down-release 1 > charging 2),
  // then the name closest to its report. The epoch/sector governance that
  // sorted the old basin list is retired with it (FIELD-R1 is the governance).
  deduped.sort((a, b) => (a.priority - b.priority) || ((b.cycle?.dsl ?? 0) - (a.cycle?.dsl ?? 0)));

  // One filer, one slot: the first (best-ordered) share class of a company wins;
  // a company already held under another class is not bought again.
  const heldFilers = new Set();
  for (const t of openTickers) heldFilers.add(filerKey(t, openFilerNames.get(t)));
  const oneFiler = [];
  for (const s of deduped) {
    if (heldFilers.has(s.filer)) { console.log(`[CH2-STRATEGIST]   ${s.ticker} — SKIPPED (same filer as a held or earlier pick: ${s.filer})`); continue; }
    heldFilers.add(s.filer); oneFiler.push(s);
  }

  console.log(`[CH2-STRATEGIST] ${rows.length} candidates → ${signals.length} in the field's eligible list → ${deduped.length} after dedup → ${oneFiler.length} one-filer-one-slot (FIELD-R1, priority ${field.priority})`);
  for (const s of oneFiler) {
    console.log(`[CH2-STRATEGIST]   ${s.ticker} | dsl=${s.cycle.dsl} | age=${s.cycle.age} | priority=${s.priority} | acc(recorded)=${s.v3_basin ? s.v3_basin.accumulate_basin.toFixed(4) : "n/a"} | sector=${s.sector}`);
  }
  return oneFiler;
}

export async function closeCh2StrategistPool() {
  await pool.end();
}
