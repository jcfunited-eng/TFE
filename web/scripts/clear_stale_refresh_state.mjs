/**
 * clear_stale_refresh_state.mjs
 *
 * Run on container startup. If the admin refresh state in Postgres
 * shows running=true (left over from the previous container), mark it
 * as failed so the admin UI shows a clean error instead of permanently
 * showing "running" or the stale-process error on every page load.
 */

import { Pool } from "pg";

const TABLE = "tfe_admin_refresh_persist";
const STATUS_KEY = "status_record_v1";

const pool = new Pool({
  host: process.env.PGHOST,
  database: process.env.PGDATABASE,
  user: process.env.PGUSER,
  password: process.env.PGPASSWORD,
  port: Number(process.env.PGPORT ?? 5432),
  max: 2,
  connectionTimeoutMillis: 8000,
  ssl: { rejectUnauthorized: false },
});

async function run() {
  try {
    // Table may not exist yet on fresh deployments — that's fine.
    const exists = await pool.query(
      `SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=$1`,
      [TABLE],
    );
    if (exists.rows.length === 0) {
      console.log("[STARTUP] tfe_admin_refresh_persist table not yet created — nothing to clear.");
      return;
    }

    const result = await pool.query(
      `SELECT payload FROM ${TABLE} WHERE key = $1 LIMIT 1`,
      [STATUS_KEY],
    );

    if (result.rows.length === 0) {
      console.log("[STARTUP] No refresh state found in DB — nothing to clear.");
      return;
    }

    const payload = result.rows[0].payload;
    if (!payload?.running) {
      console.log("[STARTUP] Refresh state is already not running — nothing to clear.");
      return;
    }

    const updated = {
      ...payload,
      running: false,
      completion_status: "error",
      last_error: "Container was restarted or redeployed while a refresh was in progress. Start a new refresh from the admin page.",
      completed_at: new Date().toISOString(),
    };

    await pool.query(
      `UPDATE ${TABLE} SET payload = $1::jsonb, updated_at = NOW() WHERE key = $2`,
      [JSON.stringify(updated), STATUS_KEY],
    );

    console.log("[STARTUP] Cleared stale running=true refresh state from previous container.");
  } catch (err) {
    // Non-fatal — never block container startup.
    console.error("[STARTUP] Could not clear stale refresh state:", err.message);
  } finally {
    await pool.end().catch(() => {});
  }
}

run();
