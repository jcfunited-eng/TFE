/**
 * clear_stale_refresh_state.mjs
 *
 * Run on container startup. Clears stale refresh state left over from the
 * previous container so the admin UI shows a clean error instead of
 * permanently showing "running" or the stale-process error on every page load.
 *
 * Clears TWO persistence layers:
 *  1. tfe_admin_refresh_persist   — main UI refresh status record
 *  2. runtime_refresh_runs +
 *     runtime_refresh_run_phases  — phase-level truth tables used by the
 *                                   publication-critical phase-truth check
 */

import { Pool } from "pg";

const PERSIST_TABLE = "tfe_admin_refresh_persist";
const STATUS_KEY    = "status_record_v1";
const RUNS_TABLE    = "runtime_refresh_runs";
const PHASES_TABLE  = "runtime_refresh_run_phases";

const pool = new Pool({
  host:     process.env.PGHOST,
  database: process.env.PGDATABASE,
  user:     process.env.PGUSER,
  password: process.env.PGPASSWORD,
  port:     Number(process.env.PGPORT ?? 5432),
  max: 2,
  connectionTimeoutMillis: 8000,
  ssl: { rejectUnauthorized: false },
});

// ── 1. Clear tfe_admin_refresh_persist ────────────────────────────────────────

async function clearAdminPersist() {
  const exists = await pool.query(
    `SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=$1`,
    [PERSIST_TABLE],
  );
  if (exists.rows.length === 0) {
    console.log(`[STARTUP] ${PERSIST_TABLE} table not yet created — skipping.`);
    return;
  }

  const result = await pool.query(
    `SELECT payload FROM ${PERSIST_TABLE} WHERE key = $1 LIMIT 1`,
    [STATUS_KEY],
  );

  if (result.rows.length === 0) {
    console.log("[STARTUP] No refresh state found in tfe_admin_refresh_persist — nothing to clear.");
    return;
  }

  const payload = result.rows[0].payload;
  if (!payload?.running) {
    console.log("[STARTUP] tfe_admin_refresh_persist is already not running — nothing to clear.");
    return;
  }

  const updated = {
    ...payload,
    running:           false,
    completion_status: "error",
    last_error:        "Container was restarted or redeployed while a refresh was in progress. Start a new refresh from the admin page.",
    completed_at:      new Date().toISOString(),
  };

  await pool.query(
    `UPDATE ${PERSIST_TABLE} SET payload = $1::jsonb, updated_at = NOW() WHERE key = $2`,
    [JSON.stringify(updated), STATUS_KEY],
  );

  console.log("[STARTUP] Cleared stale running=true state from tfe_admin_refresh_persist.");
}

// ── 2. Clear runtime_refresh_runs / runtime_refresh_run_phases ────────────────

async function clearRunPhases() {
  // Check both tables exist
  const runsExists = await pool.query(
    `SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=$1`,
    [RUNS_TABLE],
  );
  if (runsExists.rows.length === 0) {
    console.log(`[STARTUP] ${RUNS_TABLE} table not yet created — skipping phase truth cleanup.`);
    return;
  }

  const phasesExists = await pool.query(
    `SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=$1`,
    [PHASES_TABLE],
  );
  if (phasesExists.rows.length === 0) {
    console.log(`[STARTUP] ${PHASES_TABLE} table not yet created — skipping phase truth cleanup.`);
    return;
  }

  // Mark any incomplete runs (no completed_at) as aborted
  const staleRuns = await pool.query(
    `UPDATE ${RUNS_TABLE}
     SET report_status  = 'aborted',
         epoch_library_status = 'aborted_by_admin',
         failure_code   = 'container_restart',
         failure_detail = 'Container restarted — run abandoned',
         completed_at   = NOW()
     WHERE completed_at IS NULL
     RETURNING run_id`,
  );

  if (staleRuns.rowCount === 0) {
    console.log("[STARTUP] No incomplete runs in runtime_refresh_runs — nothing to clear.");
  } else {
    const ids = staleRuns.rows.map(r => r.run_id).join(", ");
    console.log(`[STARTUP] Marked ${staleRuns.rowCount} stale run(s) as aborted: ${ids}`);
  }

  // Mark any non-terminal phases as failed
  const stalePhases = await pool.query(
    `UPDATE ${PHASES_TABLE}
     SET process_status = 'failed',
         failure_code   = 'container_restart',
         failure_detail = 'Container restarted — phase abandoned',
         completed_at   = NOW()
     WHERE process_status NOT IN ('completed', 'failed', 'cancelled', 'skipped')
     RETURNING phase_name`,
  );

  if (stalePhases.rowCount === 0) {
    console.log("[STARTUP] No stale phases in runtime_refresh_run_phases — nothing to clear.");
  } else {
    const names = stalePhases.rows.map(r => r.phase_name).join(", ");
    console.log(`[STARTUP] Marked ${stalePhases.rowCount} stale phase(s) as failed: ${names}`);
  }
}

// ── Main ──────────────────────────────────────────────────────────────────────

async function run() {
  try {
    await clearAdminPersist();
  } catch (err) {
    console.error("[STARTUP] clearAdminPersist error (non-fatal):", err instanceof Error ? err.message : err);
  }

  try {
    await clearRunPhases();
  } catch (err) {
    console.error("[STARTUP] clearRunPhases error (non-fatal):", err instanceof Error ? err.message : err);
  }

  await pool.end().catch(() => {});
}

run();
