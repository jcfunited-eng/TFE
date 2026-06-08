/**
 * web/scripts/execution/sentinel_daemon.mjs
 * Continuous sentinel — polls Alpaca every 5 minutes during market hours,
 * syncs fill status to the DB, and runs exit checks on open positions.
 *
 * Runs as a background process started by tfe_startup.sh.
 * Exits cleanly on SIGTERM.
 */

import { runSentinel, closeSentinelPool } from "./sentinel_monitor.mjs";
import { runEntryTimingCheck, closeEntryTimingPool } from "./entry_timing_watcher.mjs";
import { runStrikeZoneCheck, closeStrikeZonePool } from "./ch3_strike_zone_detector.mjs";
import { getCh3Signals, closeCh3StrategistPool } from "./ch3_scalp_strategist.mjs";
import { get3WASignals, closeStrategistPool } from "./3wa_strategist.mjs";
import { getCh2Signals, closeCh2StrategistPool } from "./ch2_strategist.mjs";
import { executeBracketOrder, executeCh2BracketOrder,
         executeCh3MarketOrder } from "./alpaca_bridge.mjs";
import { isTradingDay, getHolidayName } from "./market_calendar.mjs";
import pg from "pg";

const POLL_INTERVAL_MS  = 5 * 60 * 1000;  // 5 minutes

// ── DB pool for execution mode lookup ────────────────────────────────────
const pool = new pg.Pool({
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

/**
 * Fetch available cash from Alpaca account.
 * Returns { cash } — the ground truth for gating orders.
 * Got cash on hand? Trade. Don't? Stop.
 */
async function fetchAvailableCash() {
  let cash = 0;
  try {
    const modeRes = await pool.query(
      `SELECT value FROM pee1_execution_config WHERE key = 'execution_mode' LIMIT 1`
    );
    const mode = modeRes.rows[0]?.value ?? "paper";
    const base = mode === "live"
      ? "https://api.alpaca.markets"
      : "https://paper-api.alpaca.markets";
    const res = await fetch(`${base}/v2/account`, {
      headers: {
        "APCA-API-KEY-ID":     process.env.APCA_API_KEY_ID,
        "APCA-API-SECRET-KEY": process.env.APCA_API_SECRET_KEY,
      },
    });
    const acct = await res.json();
    cash = parseFloat(acct?.cash ?? 0);
  } catch (err) {
    console.error(`[SENTINEL-DAEMON] fetchAvailableCash error: ${err.message}`);
    cash = 0; // fail-safe: no cash = no orders
  }

  return { cash };
}
const MARKET_OPEN_UTC_H  = 13;  // 9:30 ET = 13:30 UTC
const MARKET_OPEN_UTC_M  = 30;
const MARKET_CLOSE_UTC_H = 20;  // 4:00 PM ET = 20:00 UTC

let running = true;

process.on("SIGTERM", () => { running = false; });
process.on("SIGINT",  () => { running = false; });

function isMarketHours() {
  const now = new Date();
  const h = now.getUTCHours();
  const m = now.getUTCMinutes();
  const minuteOfDay = h * 60 + m;
  const open  = MARKET_OPEN_UTC_H  * 60 + MARKET_OPEN_UTC_M;
  const close = MARKET_CLOSE_UTC_H * 60;
  // Run from 30 min before open through 30 min after close to catch fills
  return minuteOfDay >= (open - 30) && minuteOfDay <= (close + 30);
}

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function main() {
  console.log("[SENTINEL-DAEMON] Started. Polling every 5 min during market hours.");

  while (running) {
    if (!isTradingDay()) {
      const holiday = getHolidayName();
      console.log(`[SENTINEL-DAEMON] Market holiday${holiday ? ` (${holiday})` : ""} — no trading today.`);
      // Sleep longer on holidays — no need to check every 5 min
      await sleep(30 * 60 * 1000); // 30 min
      continue;
    }

    if (isMarketHours()) {
      try {
        console.log(`[SENTINEL-DAEMON] Running sentinel check at ${new Date().toISOString()}`);
        await runSentinel();
        console.log(`[SENTINEL-DAEMON] Check complete.`);
      } catch (err) {
        console.error(`[SENTINEL-DAEMON] Error: ${err.message}`);
      }

      // ── HARD KILL SWITCH: skip ALL entry logic when entries are halted ──
      // Reads TFE_ENTRIES_HALTED env var OR pee1_execution_config.entries_halted.
      // Independent of the cash gate — this is the guaranteed stop.
      let entriesHalted = process.env.TFE_ENTRIES_HALTED === "1";
      if (!entriesHalted) {
        try {
          const haltRes = await pool.query(
            `SELECT value FROM pee1_execution_config WHERE key = 'entries_halted' LIMIT 1`
          );
          entriesHalted = haltRes.rows[0]?.value === "true";
        } catch { /* non-fatal — env var is the primary kill */ }
      }
      if (entriesHalted) {
        console.log(`[SENTINEL-DAEMON] ENTRIES HALTED — kill switch active, skipping all entry channels`);
        // Still run sentinel (exits), just skip all entries below
        await sleep(POLL_INTERVAL_MS);
        continue;
      }

      // ── Cash gate: shared across ALL entry channels ────────────────────
      // Fetch once per cycle, decrement locally after each successful order.
      // This prevents burst-ordering: placing N orders in one loop when
      // cash runs out after order M. The funded amount ($100K) is the hard
      // ceiling — invested must never exceed it. Position count is not a
      // constraint; only available cash matters.
      let capacity;
      try {
        capacity = await fetchAvailableCash();
        console.log(`[SENTINEL-DAEMON] Available cash: $${capacity.cash.toFixed(2)}`);
      } catch (err) {
        console.error(`[SENTINEL-DAEMON] Cash fetch failed: ${err.message} — skipping all entries this cycle`);
        capacity = null;
      }

      // ── 3WA + CH2 entry: evaluate and place orders during market hours ──
      // These strategists read runtime_decisions_latest (updated by refresh)
      // and place bracket orders via the bridge. Previously only ran during
      // the overnight refresh (00:17 UTC) — orders couldn't fill because
      // the market was closed. Now runs every sentinel cycle during market hours.
      if (capacity && capacity.cash > 0) {
        try {
          const signals3wa = await get3WASignals();
          for (const signal of signals3wa) {
            if (capacity.cash <= 0) {
              console.log(`[3WA-ENTRY] CASH EXHAUSTED — $${capacity.cash.toFixed(2)} — skipping remaining signals`);
              break;
            }
            try {
              const result = await executeBracketOrder(signal);
              if (result.ok) {
                console.log(`[3WA-ENTRY] ✓ ${signal.ticker} | class=${signal.signal_class} | orderId=${result.orderId}`);
                capacity.cash -= result.dollarAllocation ?? 0;
              } else if (!result.rejected) {
                console.log(`[3WA-ENTRY] ✗ ${signal.ticker} | ${result.reason}`);
              }
            } catch (orderErr) {
              console.error(`[3WA-ENTRY] Order error ${signal.ticker}: ${orderErr.message}`);
            }
          }
        } catch (err) {
          console.error(`[3WA-ENTRY] Error: ${err.message}`);
        }
      }

      if (capacity && capacity.cash > 0) {
        try {
          const signalsCh2 = await getCh2Signals();
          for (const signal of signalsCh2) {
            if (capacity.cash <= 0) {
              console.log(`[CH2-ENTRY] CASH EXHAUSTED — $${capacity.cash.toFixed(2)} — skipping remaining signals`);
              break;
            }
            try {
              const result = await executeCh2BracketOrder(signal);
              if (result.ok) {
                console.log(`[CH2-ENTRY] ✓ ${signal.ticker} | orderId=${result.orderId}`);
                capacity.cash -= result.dollarAllocation ?? 0;
              } else if (!result.rejected) {
                console.log(`[CH2-ENTRY] ✗ ${signal.ticker} | ${result.reason}`);
              }
            } catch (orderErr) {
              console.error(`[CH2-ENTRY] Order error ${signal.ticker}: ${orderErr.message}`);
            }
          }
        } catch (err) {
          console.error(`[CH2-ENTRY] Error: ${err.message}`);
        }
      }

      // Real-time entry timing: check primed tickers for entry opportunities
      // MUST be inside the cash gate — was previously outside, allowing orders
      // to bypass the funded-amount ceiling entirely.
      if (capacity && capacity.cash > 0) {
        try {
          await runEntryTimingCheck();
        } catch (err) {
          console.error(`[ENTRY-TIMING] Error: ${err.message}`);
        }
      }

      // CH3 Strike Zone: phase + swarm + G32 epoch direction
      // MUST be inside the cash gate — same bypass fix as entry timing.
      if (capacity && capacity.cash > 0) {
        try {
          await runStrikeZoneCheck();
        } catch (err) {
          console.error(`[STRIKE-ZONE] Error: ${err.message}`);
        }
      }

      // CH3 intraday scan: check for spike candidates every cycle
      if (capacity && capacity.cash > 0) {
        try {
          const ch3Signals = await getCh3Signals();
          for (const signal of ch3Signals) {
            if (capacity.cash <= 0) {
              console.log(`[CH3-INTRADAY] CASH EXHAUSTED — $${capacity.cash.toFixed(2)} — skipping remaining signals`);
              break;
            }
            try {
              const result = await executeCh3MarketOrder(signal);
              if (result.ok) {
                console.log(`[CH3-INTRADAY] ✓ ${signal.ticker} | orderId=${result.orderId} | shares=${result.shares} | entry≈${result.entryPrice}`);
                capacity.cash -= result.tradeAmount ?? result.dollarAllocation ?? 0;
              } else {
                console.log(`[CH3-INTRADAY] ✗ ${signal.ticker} | rejected: ${result.reason}`);
              }
            } catch (orderErr) {
              console.error(`[CH3-INTRADAY] Order error ${signal.ticker}: ${orderErr.message}`);
            }
          }
        } catch (err) {
          console.error(`[CH3-INTRADAY] Error: ${err.message}`);
        }
      }
    } else {
      console.log(`[SENTINEL-DAEMON] Outside market hours — sleeping.`);
    }

    await sleep(POLL_INTERVAL_MS);
  }

  await closeSentinelPool();
  await closeEntryTimingPool();
  await closeStrikeZonePool();
  await closeCh3StrategistPool();
  await closeStrategistPool();
  await closeCh2StrategistPool();
  await pool.end();
  console.log("[SENTINEL-DAEMON] Stopped.");
}

main().catch(err => {
  console.error("[SENTINEL-DAEMON] Fatal:", err);
  process.exit(1);
});
