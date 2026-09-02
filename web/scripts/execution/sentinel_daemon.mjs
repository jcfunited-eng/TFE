/**
 * web/scripts/execution/sentinel_daemon.mjs
 * Continuous sentinel — polls Alpaca every 5 minutes during market hours,
 * syncs fill status to the DB, and runs exit checks on open positions.
 *
 * ENTRY CADENCE: Once per trading day, after market open (09:45 ET).
 * The daemon loop runs sentinel exits every 5 min. Entry logic runs once
 * daily from settled account state. Cash freed by intraday exits
 * accumulates untouched until the next day's pass.
 *
 * CH3 EXCEPTION: the scalp channel re-arms every 15 min after the entry
 * window until 14:00 ET — an intraday channel whose entries
 * cancel unfilled deserves more than one shot per day. 3WA/CH2 remain
 * strictly once-daily.
 *
 * Runs as a background process started by tfe_startup.sh.
 * Exits cleanly on SIGTERM.
 */

import { runSentinel, closeSentinelPool } from "./sentinel_monitor.mjs";
import { S3Client, GetObjectCommand } from "@aws-sdk/client-s3";
import { SNSClient, PublishCommand } from "@aws-sdk/client-sns";

// ── Machinery pulse alerts (Joseph, 2026-08-31) ───────────────────────
// The local research machine's loops died in a weekend restart and
// trading stopped silently for two days. The local side publishes a
// pulse sheet beside the channel books every minute; production — the
// only piece with real uptime — checks it every cycle, around the
// clock, and emails when any pulse has been silent 3x its expected
// interval. One email per pulse per 12 hours.
const PULSE_BUCKET = "tfe-codebuild-src-418384447921-us-east-1";
const PULSE_KEY = "runtime-refresh-checkpoints/channel-books/heartbeats.json";
const PULSE_TOPIC = "arn:aws:sns:us-east-1:418384447921:tfe-machinery-alerts";
const pulseAlertLast = new Map();

async function checkMachineryPulse() {
  const now = Date.now();
  let body = null;
  try {
    const s3 = new S3Client({ region: "us-east-1" });
    const res = await s3.send(new GetObjectCommand({ Bucket: PULSE_BUCKET, Key: PULSE_KEY }));
    body = JSON.parse(await res.Body.transformToString());
  } catch {
    body = null;
  }
  const stale = [];
  const genAt = body ? new Date(body.generated_at ?? 0).getTime() : NaN;
  if (!Number.isFinite(genAt) || now - genAt > 30 * 60 * 1000) {
    stale.push(["publisher", "pulse sheet itself", Number.isFinite(genAt) ? Math.round((now - genAt) / 60000) : null]);
  }
  for (const [key, p] of Object.entries(body?.pulses ?? {})) {
    const t = p?.last ? new Date(p.last).getTime() : NaN;
    const expect = Number(p?.expect_minutes ?? 60);
    const ageMin = Number.isFinite(t) ? (now - t) / 60000 : null;
    if (ageMin === null || ageMin > 3 * expect) {
      stale.push([key, String(p?.label ?? key), ageMin === null ? null : Math.round(ageMin)]);
    }
  }
  if (!stale.length) return;
  const fresh = stale.filter(([key]) => (now - (pulseAlertLast.get(key) ?? 0)) > 12 * 60 * 60 * 1000);
  if (!fresh.length) return;
  const lines = fresh.map(([, label, age]) =>
    `- ${label}: ${age === null ? "no signal at all" : `silent for ${age >= 120 ? Math.round(age / 60) + " hours" : age + " minutes"}`}`);
  try {
    const sns = new SNSClient({ region: "us-east-1" });
    await sns.send(new PublishCommand({
      TopicArn: PULSE_TOPIC,
      Subject: "TFE machinery alert: " + fresh.map(([, l]) => l).join(", "),
      Message: "The following TFE programs have gone silent:\n\n" + lines.join("\n") +
        "\n\nThe research machine's loops may need restarting. Checked " + new Date(now).toISOString(),
    }));
    for (const [key] of fresh) pulseAlertLast.set(key, now);
    console.log(`[PULSE-ALERT] emailed: ${fresh.map(([, l]) => l).join(", ")}`);
  } catch (err) {
    console.error(`[PULSE-ALERT] publish failed: ${err.message}`);
  }
}
import { getCh3Signals, closeCh3StrategistPool } from "./ch3_scalp_strategist.mjs";
import { get3WASignals, closeStrategistPool } from "./3wa_strategist.mjs";
import { getCh2Signals, closeCh2StrategistPool } from "./ch2_strategist.mjs";
import { executeBracketOrder, executeCh2BracketOrder,
         executeCh3MarketOrder, CH1_REDUCED_ALLOCATION_PCT } from "./alpaca_bridge.mjs";
import { isTradingDay, getHolidayName } from "./market_calendar.mjs";
import {
  isCh3RearmWindowEastern,
  isDaemonMarketWindow,
  isDailyEntryWindow,
  marketDateEastern,
} from "./market_clock.mjs";
import { fetchPaperEntryCustody } from "./broker_entry_custody.mjs";
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
// Persisted to DB so daemon restarts during market hours don't re-fire.
// In-memory variable is loaded from DB at startup in main().
let lastEntryPassDate = null;

async function loadEntryPassDate() {
  const r = await pool.query(
    `SELECT value FROM pee1_execution_config WHERE key = 'lastEntryPassDate' LIMIT 1`
  );
  lastEntryPassDate = r.rows[0]?.value ?? null;
  if (lastEntryPassDate) {
    console.log(`[SENTINEL-DAEMON] Entry pass already ran: ${lastEntryPassDate}`);
  }
}

async function persistEntryPassDate(date) {
  await pool.query(
    `INSERT INTO pee1_execution_config (key, value) VALUES ('lastEntryPassDate', $1)
     ON CONFLICT (key) DO UPDATE SET value = $1`,
    [date]
  );
}

/**
 * Fetch account state from Alpaca.
 * Returns { cash, invested, funded } for the submitEntry pipeline.
 */
async function fetchAccountState() {
  const configRes = await pool.query(
    `SELECT key, value
     FROM pee1_execution_config
     WHERE key IN ('execution_mode', 'vault_funded_amount')`
  );
  const config = new Map(configRes.rows.map(row => [row.key, row.value]));
  return fetchPaperEntryCustody({
    executionMode: config.get("execution_mode"),
    fundedCapital: config.get("vault_funded_amount"),
  });
}

let running = true;

process.on("SIGTERM", () => { running = false; });
process.on("SIGINT",  () => { running = false; });

function isMarketHours() {
  return isDaemonMarketWindow();
}

/**
 * Check if it's past the daily entry window (15 min after open).
 * Entries run at 09:45 ET — 15 min after open to let
 * the market settle and ensure account state reflects overnight fills.
 */
function isEntryWindow() {
  return isDailyEntryWindow();
}

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * submitEntry — single pipeline for all entry channels.
 * Checks: same-day exit → invested cap → cash gate → execute.
 * Returns { ok, reason } or the bridge result.
 */
async function submitEntry(signal, executeFn, channelTag, budget, sameDayExitTickers) {
  // Same-day exit exclusion: no entry on a ticker the sentinel exited today
  const ticker = String(signal?.ticker ?? "").trim().toUpperCase();
  if (sameDayExitTickers && sameDayExitTickers.has(ticker)) {
    console.log(`[DAILY-ENTRY] ${ticker} excluded: same-day exit`);
    return { ok: false, reason: "same_day_exit" };
  }

  // ── The entry door gets a memory (Joseph 2026-09-02) ─────────────
  // Receipt: RAL bought three times in three weeks — once on top of
  // an open lot (broker 79 vs ledger 40, custody mismatch), twice
  // within days of a losing stop-out. CH2 scope only.
  if (String(channelTag ?? "").toUpperCase().includes("CH2")) {
    // one position per stock, ever — the ledger is built one lot per
    // ticker; a second lot breaks custody by construction
    const held = await pool.query(
      `SELECT id FROM personal_trade_ledger
       WHERE UPPER(TRIM(ticker)) = $1 AND signal_class = 'CH2'
         AND status IN ('submitted','filled') LIMIT 1`, [ticker]);
    if (held.rows.length > 0) {
      console.log(`[DAILY-ENTRY] ${ticker} excluded: already held (one position per stock)`);
      return { ok: false, reason: "already_held" };
    }
    // cooling-off: a stock that stopped us out at a loss is not
    // re-entered on the same class of signal for 14 calendar days
    // (~10 sessions) — no more averaging down into our own rejects
    const cooled = await pool.query(
      `SELECT id FROM personal_trade_ledger
       WHERE UPPER(TRIM(ticker)) = $1 AND signal_class = 'CH2'
         AND exit_filled_at >= NOW() - INTERVAL '14 days'
         AND exit_filled_price IS NOT NULL AND entry_filled_price IS NOT NULL
         AND exit_filled_price < entry_filled_price LIMIT 1`, [ticker]);
    if (cooled.rows.length > 0) {
      console.log(`[DAILY-ENTRY] ${ticker} excluded: cooling off after a losing exit (14 days)`);
      return { ok: false, reason: "cooling_off" };
    }
  }

  // Invested cap: projected invested after this order must not exceed funded capital
  const dollarAllocation = signal.ch3_trade_amount ?? budget.perTrade;
  if (!Number.isFinite(dollarAllocation) || dollarAllocation <= 0) {
    console.error(`[${channelTag}] ${signal.ticker} — invalid allocation ${dollarAllocation}; skipped`);
    return { ok: false, reason: "invalid_allocation" };
  }
  const projectedInvested = budget.invested + dollarAllocation;
  if (projectedInvested > budget.funded) {
    console.log(
      `[${channelTag}] ${signal.ticker} — INVESTED CAP: projected $${projectedInvested.toFixed(0)} ` +
      `> funded $${budget.funded.toFixed(0)} — skipped`
    );
    return { ok: false, reason: "invested_cap" };
  }

  // Cash gate
  if (budget.cashRemaining < dollarAllocation) {
    console.log(
      `[${channelTag}] CASH GATE — allocation $${dollarAllocation.toFixed(2)} exceeds ` +
      `available $${budget.cashRemaining.toFixed(2)} — skipping`
    );
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
 * CH3-only kill switch — env var or config row halts CH3 entries ONLY.
 * CH2 and every other channel are untouched by this flag. Added
 * 2026-07-30 after the CH3 diagnosis (19% WR, -$449 since 07-07):
 * entries halt, exits/brackets stay fully active so open scalps unwind.
 */
async function checkCh3EntriesHalted() {
  let halted = process.env.CH3_ENTRIES_HALTED === "1";
  if (!halted) {
    try {
      const res = await pool.query(
        `SELECT value FROM pee1_execution_config WHERE key = 'ch3_entries_halted' LIMIT 1`
      );
      halted = res.rows[0]?.value === "true";
    } catch { /* non-fatal */ }
  }
  return halted;
}

/**
 * Kill switch — env var or config row halts all entries.
 */
async function checkEntriesHalted() {
  if (process.env.TFE_ENTRIES_HALTED === "1") return true;
  try {
    const configRes = await pool.query(
      `SELECT key, value
       FROM pee1_execution_config
       WHERE key IN ('entries_halted', 'auto_tfe_enabled')`
    );
    const config = new Map(configRes.rows.map(row => [row.key, row.value]));
    if (config.get("auto_tfe_enabled") !== "true") return true;
    return config.get("entries_halted") === "true";
  } catch (error) {
    console.error(`[ENTRY-GATE] Configuration unavailable — entries fail closed (${error.message})`);
    return true;
  }
}

/**
 * Same-day exit exclusion set (brief point 4): tickers closed in the ledger
 * today plus tickers with open sell orders on Alpaca right now. Prevents
 * buy+sell collision (May 27 BELFB/LPLA/NVT incident). Throws on failure —
 * callers FAIL CLOSED and skip their pass.
 */
async function buildSameDayExitTickers(openOrders) {
  // 1. Tickers closed in the ledger today
  const exitRes = await pool.query(
    `SELECT DISTINCT UPPER(TRIM(ticker)) AS ticker
     FROM personal_trade_ledger
     WHERE status = 'closed'
       AND exit_filled_at >= CURRENT_DATE`
  );
  const sameDayExitTickers = new Set(exitRes.rows.map(r => r.ticker));

  // 2. Tickers with open/unfilled sell orders in the same verified custody
  // snapshot used for exposure accounting.
  if (!Array.isArray(openOrders)) throw new Error("alpaca_open_orders_invalid");
  for (const order of openOrders) {
    if (String(order?.side ?? "").toLowerCase() !== "sell") continue;
    const ticker = String(order?.symbol ?? "").trim().toUpperCase();
    if (!ticker) throw new Error("alpaca_open_sell_symbol_missing");
    sameDayExitTickers.add(ticker);
  }
  return sameDayExitTickers;
}

/**
 * Daily entry pass — runs ONCE per trading day.
 * Evaluates all channels from settled account state.
 */
async function runDailyEntryPass() {
  console.log(`[DAILY-ENTRY] ═══════════════════════════════════════════════`);
  console.log(`[DAILY-ENTRY] Starting daily entry pass at ${new Date().toISOString()}`);

  // ── Kill switch ──────────────────────────────────────────────────────
  if (await checkEntriesHalted()) {
    console.log(`[DAILY-ENTRY] KILL SWITCH ACTIVE — no entries today`);
    console.log(`[DAILY-ENTRY] ═══════════════════════════════════════════════`);
    return true;
  }

  // ── Fetch settled account state (once, used for entire pass) ─────────
  let acct;
  try {
    acct = await fetchAccountState();
  } catch (err) {
    console.error(`[DAILY-ENTRY] Account fetch failed: ${err.message} — aborting`);
    return false;
  }

  console.log(
    `[DAILY-ENTRY] Account: cash=$${acct.cash.toFixed(0)} invested=$${acct.invested.toFixed(0)} ` +
    `funded=$${acct.funded.toFixed(0)} headroom=$${Math.max(0, acct.funded - acct.invested).toFixed(0)}`
  );

  if (acct.cash <= 0) {
    console.log(`[DAILY-ENTRY] No cash on hand — skipping all entries`);
    console.log(`[DAILY-ENTRY] ═══════════════════════════════════════════════`);
    return true;
  }

  // ── Build daily budget (snapshot, does not change during this pass) ──
  const riskPct = Math.max(2.5, CH1_REDUCED_ALLOCATION_PCT);
  const budget = {
    cashRemaining: acct.cash,
    invested: acct.invested,
    funded: acct.funded,
    perTrade: acct.funded * (riskPct / 100),
  };

  // ── Same-day exit exclusion (brief point 4) ────────────────────────
  // FAIL CLOSED: if either query fails, abort the entire pass for today.
  let sameDayExitTickers;
  try {
    sameDayExitTickers = await buildSameDayExitTickers(acct.openOrders);
    if (sameDayExitTickers.size > 0) {
      console.log(`[DAILY-ENTRY] Same-day exit exclusions: ${[...sameDayExitTickers].sort().join(', ')}`);
    }
  } catch (err) {
    console.error(`[DAILY-ENTRY] Exclusion data unavailable — pass aborted, no entries today (${err.message})`);
    console.log(`[DAILY-ENTRY] ═══════════════════════════════════════════════`);
    return false;
  }

  let totalEntries = 0;

  // ── Channel 1: 3WA ──────────────────────────────────────────────────
  try {
    const signals3wa = await get3WASignals();
    for (const signal of signals3wa) {
      if (budget.cashRemaining <= 0) break;
      const result = await submitEntry(signal, executeBracketOrder, "3WA-ENTRY", budget, sameDayExitTickers);
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
      const result = await submitEntry(signal, executeCh2BracketOrder, "CH2-ENTRY", budget, sameDayExitTickers);
      if (result.ok) totalEntries++;
    }
  } catch (err) {
    console.error(`[CH2-ENTRY] Error: ${err.message}`);
  }

  // ── Channel 3: CH3 intraday ─────────────────────────────────────────
  try {
    if (await checkCh3EntriesHalted()) {
      console.log("[CH3-ENTRY] CH3 entries halted by switch — skipping (exits unaffected)");
    } else {
      const ch3Signals = await getCh3Signals();
      for (const signal of ch3Signals) {
        if (budget.cashRemaining <= 0) break;
        const result = await submitEntry(signal, executeCh3MarketOrder, "CH3-ENTRY", budget, sameDayExitTickers);
        if (result.ok) totalEntries++;
      }
    }
  } catch (err) {
    console.error(`[CH3-ENTRY] Error: ${err.message}`);
  }

  console.log(
    `[DAILY-ENTRY] Pass complete: ${totalEntries} entries placed | ` +
    `cash remaining=$${budget.cashRemaining.toFixed(0)} | invested=$${budget.invested.toFixed(0)}`
  );
  console.log(`[DAILY-ENTRY] ═══════════════════════════════════════════════`);
  return true;
}

// ── CH3 intraday re-arm ──────────────────────────────────────────────────
// The daily pass gives CH3 one shot at 09:45 ET. When that entry never
// fills (stale-entry cancel, 4-for-4 on 7/24–7/27) or nothing is HOT yet,
// the slots sit idle all day while the strategist's own gates (pool
// dollars, already-traded-today, recent losers, daily loss limit) would
// happily authorize a later attempt. Re-arm: after the entry window
// closes, re-run the CH3 hunter every 15 min until the cutoff. CH3 only —
// 3WA/CH2 stay strictly once-daily. Every strategist and bridge gate
// still applies on each pass.
const CH3_REARM_INTERVAL_MS   = 15 * 60 * 1000;
let lastCh3RearmAt = 0;

export function isCh3RearmWindow(now = new Date()) {
  return isCh3RearmWindowEastern(now);
}

async function runCh3RearmPass() {
  if (await checkEntriesHalted()) {
    console.log(`[CH3-REARM] Kill switch active — skipping`);
    return;
  }
  if (await checkCh3EntriesHalted()) {
    console.log(`[CH3-REARM] CH3 entries halted by switch — skipping (exits unaffected)`);
    return;
  }

  let acct;
  try {
    acct = await fetchAccountState();
  } catch (err) {
    console.error(`[CH3-REARM] Account fetch failed: ${err.message} — skipping`);
    return;
  }
  if (acct.cash <= 0) return;

  // FAIL CLOSED on exclusion data, same as the daily pass.
  let sameDayExitTickers;
  try {
    sameDayExitTickers = await buildSameDayExitTickers(acct.openOrders);
  } catch (err) {
    console.error(`[CH3-REARM] Exclusion data unavailable — skipping (${err.message})`);
    return;
  }

  const budget = {
    cashRemaining: acct.cash,
    invested: acct.invested,
    funded: acct.funded,
    perTrade: acct.funded * (2.5 / 100),
  };

  const ch3Signals = await getCh3Signals();
  if (!ch3Signals.length) return;

  console.log(`[CH3-REARM] ${ch3Signals.length} signal(s) on re-arm pass`);
  for (const signal of ch3Signals) {
    if (budget.cashRemaining <= 0) break;
    await submitEntry(signal, executeCh3MarketOrder, "CH3-REARM", budget, sameDayExitTickers);
  }
}

async function main() {
  console.log("[SENTINEL-DAEMON] Started. Sentinel every 5 min. Entries once daily after open.");
  await loadEntryPassDate();

  while (running) {
    await checkMachineryPulse().catch(() => {});

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
      // Fires in the entry window (09:45-10:15 ET) if not already run today.
      // Cash freed by intraday exits accumulates until tomorrow's pass.
      const today = marketDateEastern();
      if (isEntryWindow() && lastEntryPassDate !== today) {
        try {
          const completed = await runDailyEntryPass();
          if (completed) {
            await persistEntryPassDate(today);
            lastEntryPassDate = today;
          } else {
            console.error(`[DAILY-ENTRY] Pass did not complete; date remains unmarked so the entry window may retry.`);
          }
        } catch (err) {
          console.error(`[DAILY-ENTRY] Fatal: ${err.message}`);
        }
      }

      // ── CH3 re-arm: every 15 min after the entry window, until cutoff ─
      if (isCh3RearmWindow() && Date.now() - lastCh3RearmAt >= CH3_REARM_INTERVAL_MS) {
        lastCh3RearmAt = Date.now();
        try {
          await runCh3RearmPass();
        } catch (err) {
          console.error(`[CH3-REARM] Fatal: ${err.message}`);
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
