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
import { executeCh3MarketOrder } from "./alpaca_bridge.mjs";
import { isTradingDay, getHolidayName } from "./market_calendar.mjs";

const POLL_INTERVAL_MS  = 5 * 60 * 1000;  // 5 minutes
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

      // Real-time entry timing: check primed tickers for entry opportunities
      try {
        await runEntryTimingCheck();
      } catch (err) {
        console.error(`[ENTRY-TIMING] Error: ${err.message}`);
      }

      // CH3 Strike Zone: phase + swarm + G32 epoch direction
      try {
        await runStrikeZoneCheck();
      } catch (err) {
        console.error(`[STRIKE-ZONE] Error: ${err.message}`);
      }

      // CH3 intraday scan: check for spike candidates every cycle
      try {
        const ch3Signals = await getCh3Signals();
        for (const signal of ch3Signals) {
          try {
            const result = await executeCh3MarketOrder(signal);
            if (result.ok) {
              console.log(`[CH3-INTRADAY] ✓ ${signal.ticker} | orderId=${result.orderId} | shares=${result.shares} | entry≈${result.entryPrice}`);
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
    } else {
      console.log(`[SENTINEL-DAEMON] Outside market hours — sleeping.`);
    }

    await sleep(POLL_INTERVAL_MS);
  }

  await closeSentinelPool();
  await closeEntryTimingPool();
  await closeStrikeZonePool();
  await closeCh3StrategistPool();
  console.log("[SENTINEL-DAEMON] Stopped.");
}

main().catch(err => {
  console.error("[SENTINEL-DAEMON] Fatal:", err);
  process.exit(1);
});
