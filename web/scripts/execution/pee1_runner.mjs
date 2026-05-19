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
import { getCh3Signals, closeCh3StrategistPool }                 from "./ch3_scalp_strategist.mjs";
import { executeBracketOrder, executeCh2BracketOrder,
         executeCh3MarketOrder, closeBridgePool }                from "./alpaca_bridge.mjs";
import { runAudit, closeAuditorPool }                            from "./trade_auditor.mjs";

const IS_PAPER = process.env.ALPACA_PAPER !== "0";
const POLYGON_KEY = process.env.MASSIVE_API_KEY ?? process.env.POLYGON_API_KEY ?? "";
const TAU_CACHE_PATH = "/app/tau_backfill_days.json";

/**
 * Compute τ_in (compression days) for a ticker by fetching Polygon bars
 * and running the L0-L4 kernel. Updates the backfill cache file.
 *
 * This runs at entry time for new CH2 positions so the sentinel has
 * day-level τ_out data from the start — no cold start problem.
 */
async function computeAndCacheTauIn(ticker) {
  if (!POLYGON_KEY) {
    console.log(`[RUNNER] τ_in: no Polygon key — skipping ${ticker}`);
    return;
  }

  // Fetch 400 days of bars
  const endDate = new Date().toISOString().slice(0, 10);
  const startDate = new Date(Date.now() - 400 * 86400000).toISOString().slice(0, 10);
  const url = `https://api.polygon.io/v2/aggs/ticker/${ticker}/range/1/day/${startDate}/${endDate}?adjusted=true&sort=asc&limit=50000&apiKey=${POLYGON_KEY}`;

  const resp = await fetch(url);
  const data = await resp.json();
  const bars = data?.results ?? [];

  if (bars.length < 30) {
    console.log(`[RUNNER] τ_in: ${ticker} only ${bars.length} bars — skipping`);
    return;
  }

  // Run the kernel via Python subprocess (the kernel is Python, runner is Node)
  const { execSync } = await import("child_process");
  const pythonScript = `
import sys, json
sys.path.insert(0, '/app')
import pandas as pd
from uf_core.layer0 import compute_sev_series
from uf_core.layer1 import segment_gates
from uf_core.layer2 import interpret_gates
from uf_core.layer3 import compute_resonance
from uf_core.layer4 import compute_directional_signal, compute_dsf

bars = json.loads(sys.stdin.read())
closes = pd.Series([b['c'] for b in bars], index=[pd.Timestamp(b['t'], unit='ms') for b in bars]).sort_index()
frame = pd.DataFrame({"Close": closes})
sev = compute_sev_series(frame, field_col="Close")
gates = segment_gates(sev)
interps = interpret_gates(sev, gates)
resonance = compute_resonance(interps)
decisions = compute_directional_signal(resonance)
dsf_list = compute_dsf(decisions)

# Count compression days (bar-level, not gate-level)
gate_spans = [{'D_k': d.D_k, 'start': d.gate.start_idx, 'end': d.gate.end_idx, 'days': d.gate.end_idx - d.gate.start_idx + 1} for d in dsf_list]

# Find current expansion, then count compression before it
expansion_days = 0
idx = len(gate_spans) - 1
while idx >= 0 and gate_spans[idx]['D_k'] > 0:
    expansion_days += gate_spans[idx]['days']
    idx -= 1

tau_in_days = 0
while idx >= 0 and gate_spans[idx]['D_k'] <= 0:
    tau_in_days += gate_spans[idx]['days']
    idx -= 1

print(json.dumps({'tau_in_days': tau_in_days, 'tau_out_days': tau_in_days // 3, 'expansion_days': expansion_days, 'total_gates': len(dsf_list), 'total_bars': len(bars), 'current_dk': dsf_list[-1].D_k if dsf_list else 0}))
`;

  try {
    const result = execSync(`echo '${JSON.stringify(bars).replace(/'/g, "\\'")}' | python3 -c "${pythonScript.replace(/"/g, '\\"')}"`, {
      timeout: 30000,
      maxBuffer: 10 * 1024 * 1024,
    });
    const tauData = JSON.parse(result.toString().trim());
    tauData.status = tauData.expansion_days > tauData.tau_out_days ? "EXPIRED" : `${tauData.tau_out_days - tauData.expansion_days}d left`;

    // Update cache file
    const fs = await import("fs");
    let cache = {};
    try { cache = JSON.parse(fs.readFileSync(TAU_CACHE_PATH, "utf-8")); } catch {}
    cache[ticker] = tauData;
    fs.writeFileSync(TAU_CACHE_PATH, JSON.stringify(cache, null, 2));

    console.log(`[RUNNER] τ_in: ${ticker} compressed=${tauData.tau_in_days}d budget=${tauData.tau_out_days}d expansion=${tauData.expansion_days}d → ${tauData.status}`);
    return tauData;
  } catch (kernelErr) {
    console.warn(`[RUNNER] τ_in kernel failed for ${ticker}: ${kernelErr.message?.slice(0, 100)}`);
    return null;
  }
}

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

    // Ch2 orders — with energy gate: compute τ BEFORE order, reject if energy spent
    if (ch2Signals.length > 0) {
      console.log(`\n[RUNNER] Phase 3b: Executing ${ch2Signals.length} Ch2 signal(s) (energy gate enabled)`);
      for (const signal of ch2Signals) {
        try {
          // ENTRY-R6: Energy gate — compute τ BEFORE order placement.
          // If the stock has already used >70% of its expansion budget,
          // the move is nearly over — don't enter a spent position.
          // This is what separates "stock on its way up" from "stock at the top."
          const MAX_ENERGY_SPENT = 0.70;
          let tauData = null;
          try {
            tauData = await computeAndCacheTauIn(signal.ticker);
          } catch (tauErr) {
            console.warn(`[RUNNER] τ_in compute failed for ${signal.ticker}: ${tauErr.message} — proceeding without energy gate`);
          }

          if (tauData && tauData.tau_out_days > 0) {
            const energySpent = tauData.expansion_days / tauData.tau_out_days;
            const energyRemaining = Math.max(0, 1 - energySpent);
            console.log(
              `[RUNNER] ENTRY-R6 ${signal.ticker} | τ_in=${tauData.tau_in_days}d τ_out=${tauData.tau_out_days}d ` +
              `expansion=${tauData.expansion_days}d | energy=${(energyRemaining * 100).toFixed(0)}% remaining`
            );
            if (energySpent > MAX_ENERGY_SPENT) {
              console.log(
                `[RUNNER] ✗ CH2 ${signal.ticker} | ENTRY-R6 BLOCKED — ` +
                `${(energySpent * 100).toFixed(0)}% energy spent (>${(MAX_ENERGY_SPENT * 100).toFixed(0)}% threshold). ` +
                `Move is nearly over.`
              );
              continue;
            }
          }

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

    // Ch3 scalp orders
    console.log(`\n[RUNNER] Phase 2c/3c: Chapter 3 — Scalp "Smash and Grab"`);
    let ch3Signals = [];
    try {
      ch3Signals = await getCh3Signals();
    } catch (err) {
      console.error("[RUNNER] Ch3 Strategist failed:", err.message);
      ch3Signals = [];
    }

    if (ch3Signals.length > 0) {
      for (const signal of ch3Signals) {
        try {
          const result = await executeCh3MarketOrder(signal);
          if (result.ok) {
            console.log(`[RUNNER] ✓ CH3 ${signal.ticker} | orderId=${result.orderId} | shares=${result.shares} | entry≈${result.entryPrice} | TP=${result.takeProfitPrice} | SL=${result.stopLossPrice}`);
          } else {
            console.log(`[RUNNER] ✗ CH3 ${signal.ticker} | rejected: ${result.reason}`);
          }
        } catch (err) {
          console.error(`[RUNNER] Ch3 order error for ${signal.ticker}:`, err.message);
        }
      }
    } else {
      console.log("[RUNNER] No Ch3 scalp signals.");
    }

    if (signals.length === 0 && ch2Signals.length === 0 && ch3Signals.length === 0) {
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
      closeCh3StrategistPool(),
      closeBridgePool(),
      closeAuditorPool(),
    ]);
  });
