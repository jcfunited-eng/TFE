/**
 * web/scripts/execution/pee1_runner.mjs
 * PEE-1 — Personal Execution Engine, Main Runner
 *
 * This is the only file you ever need to run. It does everything in order:
 *   1. Sentinel: audit open positions, apply kill switches
 *   2. Strategist: find 3WA signals from latest TFE run
 *   3. Bridge: place bracket orders for each validated signal
 *   4. Auditor: sync fills and print the trade report
 *
 * Run once after market open (after TFE daily refresh completes):
 *   node pee1_runner.mjs
 *
 * Required environment variables (set before running):
 *   APCA_API_KEY_ID    — your Alpaca key ID
 *   APCA_API_SECRET_KEY — your Alpaca secret key
 *   ALPACA_PAPER       — '1' = paper (safe default), '0' = live real money
 *   PGHOST / PGPORT / PGDATABASE / PGUSER / PGPASSWORD — TFE database
 */

import pg from "pg";
import { runSentinel, closeSentinelPool }                        from "./sentinel_monitor.mjs";
import { get3WASignals, closeStrategistPool }                    from "./3wa_strategist.mjs";
import { getCh2Signals, closeCh2StrategistPool }                 from "./ch2_strategist.mjs";
import { executeBracketOrder, executeCh2BracketOrder,
         closeBridgePool }                                       from "./alpaca_bridge.mjs";
import { runAudit, closeAuditorPool }                            from "./trade_auditor.mjs";

const IS_PAPER = process.env.ALPACA_PAPER !== "0";

const configPool = new pg.Pool({
  host:     process.env.PGHOST,
  port:     parseInt(process.env.PGPORT ?? "5432", 10),
  database: process.env.PGDATABASE,
  user:     process.env.PGUSER,
  password: process.env.PGPASSWORD,
  max: 2,
  idleTimeoutMillis: 10_000,
  connectionTimeoutMillis: 5_000,
  ssl: { rejectUnauthorized: false },
});

async function readConfig(key) {
  try {
    const res = await configPool.query(
      `SELECT value FROM pee1_execution_config WHERE key = $1`, [key]
    );
    return res.rows[0]?.value ?? null;
  } catch {
    return null;
  }
}

async function main() {
  console.log("═══════════════════════════════════════════════════");
  console.log("  PEE-1 Personal Execution Engine");
  console.log(`  Mode: ${IS_PAPER ? "PAPER (safe)" : "⚠️  LIVE REAL MONEY"}`);
  console.log(`  Time: ${new Date().toISOString()}`);
  console.log("═══════════════════════════════════════════════════");

  // ── Read DB config ────────────────────────────────────────────────────
  const [autoTFEValue, executionMode] = await Promise.all([
    readConfig("auto_tfe_enabled"),
    readConfig("execution_mode"),
  ]);
  const autoTFEEnabled = autoTFEValue !== "false";  // default true if missing
  console.log(`[RUNNER] Auto-TFE: ${autoTFEEnabled ? "ON" : "OFF"} | Execution mode: ${executionMode ?? "paper"}`);

  // ── Auto-TFE gate ─────────────────────────────────────────────────────
  if (!autoTFEEnabled) {
    console.log("\n[RUNNER] Auto-TFE is OFF — sentinel will still run, but no new orders will be placed.");
  }

  // ── Phase 1: Sentinel audit ──────────────────────────────────────────
  console.log("\n[RUNNER] Phase 1: Sentinel position audit");
  let sentinelResult = null;
  try {
    sentinelResult = await runSentinel();
  } catch (err) {
    console.error("[RUNNER] Sentinel failed:", err.message);
  }

  // ── Circuit breaker gate ─────────────────────────────────────────────
  const sentinelHalted = typeof sentinelResult === "object" && sentinelResult?.halted;
  if (sentinelHalted) {
    console.log(`\n[RUNNER] ⚡ CIRCUIT BREAKER ACTIVE (${sentinelResult.reason}) — skipping signals and execution`);
    console.log("[RUNNER] Audit will still run to show current portfolio state.");
  }

  // Skip signals + execution if circuit breaker OR auto-TFE is off
  const skipExecution = sentinelHalted || !autoTFEEnabled;

  // ── Phase 2a: Chapter 1 — 3WA signal detection ──────────────────────
  console.log("\n[RUNNER] Phase 2a: Chapter 1 — 3WA signal detection");
  let signals = [];
  try {
    signals = await get3WASignals();
  } catch (err) {
    console.error("[RUNNER] 3WA Strategist failed:", err.message);
    signals = [];
  }

  if (signals.length === 0) {
    console.log("[RUNNER] No 3WA signals today.");
  } else if (!autoTFEEnabled) {
    console.log(`[RUNNER] ${signals.length} 3WA signal(s) found but Auto-TFE is OFF — not placing orders.`);
    for (const s of signals) {
      console.log(`[RUNNER]   (dry-run) ${s.ticker} | bar_count=${s.bar_count} | s_uf=${s.s_uf}`);
    }
  }

  // ── Phase 2b: Chapter 2 — Mid S_UF Acceleration signal detection ─────
  console.log("\n[RUNNER] Phase 2b: Chapter 2 — Mid S_UF Acceleration signal detection");
  let ch2Signals = [];
  try {
    ch2Signals = await getCh2Signals();
  } catch (err) {
    console.error("[RUNNER] Ch2 Strategist failed:", err.message);
    ch2Signals = [];
  }

  if (ch2Signals.length === 0) {
    console.log("[RUNNER] No Ch2 signals today.");
  } else if (!autoTFEEnabled) {
    console.log(`[RUNNER] ${ch2Signals.length} Ch2 signal(s) found but Auto-TFE is OFF — not placing orders.`);
    for (const s of ch2Signals) {
      console.log(`[RUNNER]   (dry-run) ${s.ticker} | bar_count=${s.bar_count} | s_uf=${s.s_uf} | D_k=${s.d_k}`);
    }
  }

  // ── Phase 3: Execute orders ──────────────────────────────────────────
  if (!skipExecution) {
    // 3WA orders
    if (signals.length > 0) {
      console.log(`\n[RUNNER] Phase 3a: Executing ${signals.length} 3WA signal(s)`);
      for (const signal of signals) {
        try {
          const result = await executeBracketOrder(signal);
          if (result.ok) {
            console.log(`[RUNNER] ✓ 3WA ${signal.ticker} | orderId=${result.orderId} | shares=${result.shares} | entry=${result.entryPrice}`);
          } else {
            console.log(`[RUNNER] ✗ 3WA ${signal.ticker} | rejected: ${result.reason}`);
          }
        } catch (err) {
          console.error(`[RUNNER] Order error for ${signal.ticker}:`, err.message);
        }
      }
    }

    // Ch2 orders
    if (ch2Signals.length > 0) {
      console.log(`\n[RUNNER] Phase 3b: Executing ${ch2Signals.length} Ch2 signal(s)`);
      for (const signal of ch2Signals) {
        try {
          const result = await executeCh2BracketOrder(signal);
          if (result.ok) {
            console.log(`[RUNNER] ✓ CH2 ${signal.ticker} | orderId=${result.orderId} | shares=${result.shares} | entry=${result.entryPrice}`);
          } else {
            console.log(`[RUNNER] ✗ CH2 ${signal.ticker} | rejected: ${result.reason}`);
          }
        } catch (err) {
          console.error(`[RUNNER] Ch2 order error for ${signal.ticker}:`, err.message);
        }
      }
    }

    if (signals.length === 0 && ch2Signals.length === 0) {
      console.log("[RUNNER] No signals today. Nothing to execute.");
    }
  }

  // ── Phase 4: Audit report ────────────────────────────────────────────
  console.log("\n[RUNNER] Phase 4: Trade audit");
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
      closeSentinelPool(),
      closeStrategistPool(),
      closeCh2StrategistPool(),
      closeBridgePool(),
      closeAuditorPool(),
    ]);
  });
