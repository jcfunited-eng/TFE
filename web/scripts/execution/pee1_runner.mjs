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
 *   ALPACA_API_KEY     — your Alpaca key ID
 *   ALPACA_SECRET_KEY  — your Alpaca secret key
 *   ALPACA_PAPER       — '1' = paper (safe default), '0' = live real money
 *   PGHOST / PGPORT / PGDATABASE / PGUSER / PGPASSWORD — TFE database
 */

import { runSentinel, closeSentinelPool }       from "./sentinel_monitor.mjs";
import { get3WASignals, closeStrategistPool }    from "./3wa_strategist.mjs";
import { executeBracketOrder, closeBridgePool }  from "./alpaca_bridge.mjs";
import { runAudit, closeAuditorPool }            from "./trade_auditor.mjs";

const IS_PAPER = process.env.ALPACA_PAPER !== "0";

async function main() {
  console.log("═══════════════════════════════════════════════════");
  console.log("  PEE-1 Personal Execution Engine");
  console.log(`  Mode: ${IS_PAPER ? "PAPER (safe)" : "⚠️  LIVE REAL MONEY"}`);
  console.log(`  Time: ${new Date().toISOString()}`);
  console.log("═══════════════════════════════════════════════════");

  // ── Phase 1: Sentinel audit ──────────────────────────────────────────
  console.log("\n[RUNNER] Phase 1: Sentinel position audit");
  try {
    await runSentinel();
  } catch (err) {
    console.error("[RUNNER] Sentinel failed:", err.message);
    // Sentinel failure does not stop new signal processing
  }

  // ── Phase 2: 3WA signal detection ───────────────────────────────────
  console.log("\n[RUNNER] Phase 2: 3WA signal detection");
  let signals = [];
  try {
    signals = await get3WASignals();
  } catch (err) {
    console.error("[RUNNER] Strategist failed:", err.message);
    signals = [];
  }

  if (signals.length === 0) {
    console.log("[RUNNER] No 3WA signals today. Nothing to execute.");
  }

  // ── Phase 3: Execute orders ──────────────────────────────────────────
  if (signals.length > 0) {
    console.log(`\n[RUNNER] Phase 3: Executing ${signals.length} signal(s)`);
    for (const signal of signals) {
      try {
        const result = await executeBracketOrder(signal);
        if (result.ok) {
          console.log(`[RUNNER] ✓ ${signal.ticker} | orderId=${result.orderId} | shares=${result.shares} | entry=${result.entryPrice}`);
        } else {
          console.log(`[RUNNER] ✗ ${signal.ticker} | rejected: ${result.reason}`);
        }
      } catch (err) {
        console.error(`[RUNNER] Order error for ${signal.ticker}:`, err.message);
      }
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
      closeSentinelPool(),
      closeStrategistPool(),
      closeBridgePool(),
      closeAuditorPool(),
    ]);
  });
