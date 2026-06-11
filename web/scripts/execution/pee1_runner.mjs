/**
 * web/scripts/execution/pee1_runner.mjs
 * PEE-1 — Personal Execution Engine, Audit-Only Runner
 *
 * ORDER SUBMISSION REMOVED — GL-BRIEF-039 single-engine brief.
 * Orders are placed exclusively by the daily entry pass in sentinel_daemon.mjs.
 * This file retains the audit phase only (trade_auditor fill sync + report).
 *
 * Previously spawned by run_refresh_with_l5_learning.py after each nightly
 * refresh. That spawn has also been removed. If this file is invoked manually,
 * it runs the audit and exits — no orders are placed.
 */

import pg from "pg";
import { runAudit, closeAuditorPool } from "./trade_auditor.mjs";

const configPool = new pg.Pool({
  host:     process.env.PGHOST,
  port:     parseInt(process.env.PGPORT ?? "5432", 10),
  database: process.env.PGDATABASE,
  user:     process.env.PGUSER,
  password: process.env.PGPASSWORD,
  max: 2,
  idleTimeoutMillis: 30_000,
  connectionTimeoutMillis: 5_000,
  ssl: { rejectUnauthorized: false },
});

async function main() {
  console.log("═══════════════════════════════════════════════════");
  console.log("  PEE-1 Audit-Only Runner (orders removed — GL-BRIEF-039)");
  console.log(`  Time: ${new Date().toISOString()}`);
  console.log("═══════════════════════════════════════════════════");

  // Order submission removed. Daily entry pass in sentinel_daemon.mjs is
  // the single authorized order pipeline. This runner retains audit only.
  console.log("[RUNNER] Order submission removed. Use sentinel_daemon daily pass.");

  // ── Audit report (read-only: syncs fill status, prints portfolio) ────
  console.log("\n[RUNNER] Running trade audit...");
  try {
    await runAudit({ syncFillsFirst: true });
  } catch (err) {
    console.error("[RUNNER] Auditor failed:", err.message);
  }

  console.log("\n[RUNNER] Done.");
}

main()
  .catch(err => {
    console.error("[RUNNER] FATAL:", err.message);
    process.exit(1);
  })
  .finally(async () => {
    await Promise.allSettled([
      configPool.end(),
      closeAuditorPool(),
    ]);
  });
