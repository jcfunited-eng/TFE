/**
 * web/scripts/execution/sentinel_daemon.mjs
 * Continuous sentinel — polls Alpaca every 5 minutes during market hours,
 * syncs fill status to the DB, and runs exit checks on open positions.
 *
 * ENTRY CADENCE: Once per trading day, after market open (~13:45 UTC).
 * The daemon loop runs sentinel exits every 5 min. Entry logic runs once
 * daily from settled account state. Cash freed by intraday exits
 * accumulates untouched until the next day's pass.
 *
 * Runs as a background process started by tfe_startup.sh.
 * Exits cleanly on SIGTERM.
 */

import { runSentinel, closeSentinelPool } from "./sentinel_monitor.mjs";
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

// ── Daily entry pass tracking ────────────────────────────────────────────
// Entries run ONCE per trading day. This tracks whether today's pass has run.
let lastEntryPassDate = null;

/**
 * Fetch account state from Alpaca.
 * Returns { cash, invested, funded } for the submitEntry pipeline.
 */
async function fetchAccountState() {
  const modeRes = await pool.query(
    `SELECT value FROM pee1_execution_config WHERE key = 'execution_mode' LIMIT 1`
  );
  const mode = modeRes.rows[0]?.value ?? "paper";
  const base = mode === "live"
    ? "https://api.alpaca.markets"
    : "https://paper-api.alpaca.markets";

  const fundedRes = await pool.query(
    `SELECT value FROM pee1_execution_config WHERE key = 'vault_funded_amount' LIMIT 1`
  );
  const funded = parseFloat(fundedRes.rows[0]?.value ?? "100000");

  const res = await fetch(`${base}/v2/account`, {
    headers: {
      "APCA-API-KEY-ID":     process.env.APCA_API_KEY_ID,
      "APCA-API-SECRET-KEY": process.env.APCA_API_SECRET_KEY,
    },
  });
  const acct = await res.json();
  const cash = parseFloat(acct?.cash ?? 0);
  const invested = parseFloat(acct?.long_market_value ?? 0);

  return { cash, invested, funded };
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

/**
 * Check if it's past the daily entry window (15 min after open).
 * Entries run at ~13:45 UTC (9:45 AM ET) — 15 min after open to let
 * the market settle and ensure account state reflects overnight fills.
 */
function isEntryWindow() {
  const now = new Date();
  const h = now.getUTCHours();
  const m = now.getUTCMinutes();
  const minuteOfDay = h * 60 + m;
  const entryTime = (MARKET_OPEN_UTC_H * 60 + MARKET_OPEN_UTC_M) + 15; // 13:45 UTC
  // Entry window: 13:45 - 14:15 UTC (30 min window)
  return minuteOfDay >= entryTime && minuteOfDay <= entryTime + 30;
}

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * submitEntry — single pipeline for all entry channels.
 * Checks: kill switch → invested cap → cash gate → execute.
 * Returns { ok, reason } or the bridge result.
 */
async function submitEntry(signal, executeFn, channelTag, budget) {
  // Invested cap: projected invested after this order must not exceed funded capital
  const dollarAllocation = signal.ch3_trade_amount ?? budget.perTrade;
  const projectedInvested = budget.invested + dollarAllocation;
  if (projectedInvested > budget.funded) {
    console.log(
      `[${channelTag}] ${signal.ticker} — INVESTED CAP: projected $${projectedInvested.toFixed(0)} ` +
      `> funded $${budget.funded.toFixed(0)} — skipped`
    );
    return { ok: false, reason: "invested_cap" };
  }

  // Cash gate
  if (budget.cashRemaining <= 0) {
    console.log(`[${channelTag}] CASH EXHAUSTED — $${budget.cashRemaining.toFixed(2)} — skipping`);
    return { ok: false, reason: "cash_exhausted" };
  }

  const result = await executeFn(signal);
  if (result.ok) {
    const spent = result.dollarAllocation ?? result.tradeAmount ?? dollarAllocation;
    budget.cashRemaining -= spent;
    budget.invested += spent;
    console.log(`[${channelTag}] ✓ ${signal.ticker} | orderId=${result.orderId} | spent=$${spent.toFixed(0)} | remaining=$${budget.cashRemaining.toFixed(0)}`);
  } else if (!result.rejected) {
    console.log(`[${channelTag}] ✗ ${signal.ticker} | ${result.reason}`);
  }
  return result;
}

/**
 * Daily entry pass — runs ONCE per trading day.
 * Evaluates all channels from settled account state.
 */
async function runDailyEntryPass() {
  console.log(`[DAILY-ENTRY] ═══════════════════════════════════════════════`);
  console.log(`[DAILY-ENTRY] Starting daily entry pass at ${new Date().toISOString()}`);

  // ── Kill switch ──────────────────────────────────────────────────────
  let entriesHalted = process.env.TFE_ENTRIES_HALTED === "1";
  if (!entriesHalted) {
    try {
      const haltRes = await pool.query(
        `SELECT value FROM pee1_execution_config WHERE key = 'entries_halted' LIMIT 1`
      );
      entriesHalted = haltRes.rows[0]?.value === "true";
    } catch { /* non-fatal */ }
  }
  if (entriesHalted) {
    console.log(`[DAILY-ENTRY] KILL SWITCH ACTIVE — no entries today`);
    console.log(`[DAILY-ENTRY] ═══════════════════════════════════════════════`);
    return;
  }

  // ── Fetch settled account state (once, used for entire pass) ─────────
  let acct;
  try {
    acct = await fetchAccountState();
  } catch (err) {
    console.error(`[DAILY-ENTRY] Account fetch failed: ${err.message} — aborting`);
    return;
  }

  console.log(
    `[DAILY-ENTRY] Account: cash=$${acct.cash.toFixed(0)} invested=$${acct.invested.toFixed(0)} ` +
    `funded=$${acct.funded.toFixed(0)} headroom=$${Math.max(0, acct.funded - acct.invested).toFixed(0)}`
  );

  if (acct.cash <= 0) {
    console.log(`[DAILY-ENTRY] No cash on hand — skipping all entries`);
    console.log(`[DAILY-ENTRY] ═══════════════════════════════════════════════`);
    return;
  }

  // ── Build daily budget (snapshot, does not change during this pass) ──
  const riskPct = 2.5;  // matches CH2_RISK_PCT in alpaca_bridge
  const budget = {
    cashRemaining: acct.cash,
    invested: acct.invested,
    funded: acct.funded,
    perTrade: acct.funded * (riskPct / 100),
  };

  let totalEntries = 0;

  // ── Channel 1: 3WA ──────────────────────────────────────────────────
  try {
    const signals3wa = await get3WASignals();
    for (const signal of signals3wa) {
      if (budget.cashRemaining <= 0) break;
      const result = await submitEntry(signal, executeBracketOrder, "3WA-ENTRY", budget);
      if (result.ok) totalEntries++;
    }
  } catch (err) {
    console.error(`[3WA-ENTRY] Error: ${err.message}`);
  }

  // ── Channel 2: CH2 ──────────────────────────────────────────────────
  try {
    const signalsCh2 = await getCh2Signals();
    for (const signal of signalsCh2) {
      if (budget.cashRemaining <= 0) break;
      const result = await submitEntry(signal, executeCh2BracketOrder, "CH2-ENTRY", budget);
      if (result.ok) totalEntries++;
    }
  } catch (err) {
    console.error(`[CH2-ENTRY] Error: ${err.message}`);
  }

  // ── Channel 3: CH3 intraday ─────────────────────────────────────────
  try {
    const ch3Signals = await getCh3Signals();
    for (const signal of ch3Signals) {
      if (budget.cashRemaining <= 0) break;
      const result = await submitEntry(signal, executeCh3MarketOrder, "CH3-ENTRY", budget);
      if (result.ok) totalEntries++;
    }
  } catch (err) {
    console.error(`[CH3-ENTRY] Error: ${err.message}`);
  }

  console.log(
    `[DAILY-ENTRY] Pass complete: ${totalEntries} entries placed | ` +
    `cash remaining=$${budget.cashRemaining.toFixed(0)} | invested=$${budget.invested.toFixed(0)}`
  );
  console.log(`[DAILY-ENTRY] ═══════════════════════════════════════════════`);
}

async function main() {
  console.log("[SENTINEL-DAEMON] Started. Sentinel every 5 min. Entries once daily after open.");

  while (running) {
    if (!isTradingDay()) {
      const holiday = getHolidayName();
      console.log(`[SENTINEL-DAEMON] Market holiday${holiday ? ` (${holiday})` : ""} — no trading today.`);
      await sleep(30 * 60 * 1000);
      continue;
    }

    if (isMarketHours()) {
      // ── Sentinel: runs every 5 min (exits, position management) ─────
      try {
        console.log(`[SENTINEL-DAEMON] Running sentinel check at ${new Date().toISOString()}`);
        await runSentinel();
        console.log(`[SENTINEL-DAEMON] Check complete.`);
      } catch (err) {
        console.error(`[SENTINEL-DAEMON] Error: ${err.message}`);
      }

      // ── Daily entry pass: runs ONCE per trading day ─────────────────
      // Fires in the entry window (13:45-14:15 UTC) if not already run today.
      // Cash freed by intraday exits accumulates until tomorrow's pass.
      const today = new Date().toISOString().slice(0, 10);
      if (isEntryWindow() && lastEntryPassDate !== today) {
        lastEntryPassDate = today;
        try {
          await runDailyEntryPass();
        } catch (err) {
          console.error(`[DAILY-ENTRY] Fatal: ${err.message}`);
        }
      }
    } else {
      console.log(`[SENTINEL-DAEMON] Outside market hours — sleeping.`);
    }

    await sleep(POLL_INTERVAL_MS);
  }

  await closeSentinelPool();
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
