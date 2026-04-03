/**
 * web/scripts/execution/circuit_breaker.mjs
 * PEE-1 Standalone Circuit Breaker — 3% Portfolio Drawdown Fuse
 *
 * Runs independently of pee1_runner.mjs. Designed to be invoked frequently
 * (every 5–10 min via EventBridge during market hours) as an intraday fuse.
 *
 * Behavior:
 *   1. Fetch current Alpaca equity
 *   2. Compare to session-open equity (earliest vault_equity_at_signal today)
 *   3. If drawdown >= circuit_breaker_threshold_pct (default 3%):
 *      a. Cancel ALL pending stealth queue rows
 *      b. Market-sell ALL open positions via sentinel_monitor.killPosition logic
 *      c. Insert row into pee1_circuit_breaker with reason='standalone_3pct_fuse'
 *   4. If circuit breaker already active: log and return — no double-trigger
 *
 * Config keys read from pee1_execution_config:
 *   circuit_breaker_threshold_pct  — default 3.0
 *   circuit_breaker_hours          — default 24
 *   execution_mode                 — paper | live
 */

import pg from "pg";

const pool = new pg.Pool({
  host:     process.env.PGHOST,
  port:     parseInt(process.env.PGPORT ?? "5432", 10),
  database: process.env.PGDATABASE,
  user:     process.env.PGUSER,
  password: process.env.PGPASSWORD,
  max: 3,
  idleTimeoutMillis: 30_000,
  connectionTimeoutMillis: 5_000,
});

// ── Config ────────────────────────────────────────────────────────────────
async function readConfig(key, fallback) {
  try {
    const res = await pool.query(
      `SELECT value FROM pee1_execution_config WHERE key = $1 LIMIT 1`, [key]
    );
    return res.rows[0]?.value ?? fallback;
  } catch {
    return fallback;
  }
}

async function resolveAlpacaBase() {
  const mode = await readConfig("execution_mode", "paper");
  return mode === "live"
    ? "https://api.alpaca.markets"
    : "https://paper-api.alpaca.markets";
}

// ── Alpaca helpers ────────────────────────────────────────────────────────
function alpacaHeaders() {
  return {
    "APCA-API-KEY-ID":     process.env.APCA_API_KEY_ID,
    "APCA-API-SECRET-KEY": process.env.APCA_API_SECRET_KEY,
    "Content-Type":        "application/json",
  };
}

async function alpacaGet(path, base) {
  const res  = await fetch(`${base}${path}`, { headers: alpacaHeaders() });
  const body = await res.json();
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}: ${JSON.stringify(body)}`);
  return body;
}

async function alpacaPost(path, payload, base) {
  const res  = await fetch(`${base}${path}`, {
    method:  "POST",
    headers: alpacaHeaders(),
    body:    JSON.stringify(payload),
  });
  const body = await res.json();
  if (!res.ok) throw new Error(`POST ${path} → ${res.status}: ${JSON.stringify(body)}`);
  return body;
}

async function alpacaDelete(path, base) {
  try {
    await fetch(`${base}${path}`, { method: "DELETE", headers: alpacaHeaders() });
  } catch (e) {
    console.warn(`[CB] DELETE ${path} failed: ${e.message}`);
  }
}

// ── Circuit breaker state ─────────────────────────────────────────────────
async function isCircuitBreakerActive() {
  const res = await pool.query(
    `SELECT id, trigger_reason, expires_at FROM pee1_circuit_breaker
     WHERE cleared_at IS NULL AND expires_at > NOW()
     ORDER BY triggered_at DESC LIMIT 1`
  );
  return res.rows[0] ?? null;
}

async function triggerCircuitBreaker({ equityOpen, equityNow, drawdownPct, thresholdPct, hours, reason }) {
  const expiresAt = new Date(Date.now() + hours * 60 * 60 * 1000).toISOString();
  await pool.query(
    `INSERT INTO pee1_circuit_breaker
       (trigger_reason, expires_at, vault_equity_open, vault_equity_low, drawdown_pct, threshold_pct)
     VALUES ($1, $2, $3, $4, $5, $6)`,
    [reason, expiresAt, equityOpen, equityNow, drawdownPct, thresholdPct]
  );
  console.log(`[CB] ⚡ CIRCUIT BREAKER TRIGGERED | reason=${reason} | drawdown=${drawdownPct.toFixed(2)}% | halt until ${expiresAt}`);
}

// ── Cancel all pending stealth queue rows ────────────────────────────────
async function cancelStealthQueue(base) {
  const pending = await pool.query(
    `SELECT id, alpaca_order_id FROM pee1_stealth_queue WHERE status = 'pending'`
  );
  for (const row of pending.rows) {
    if (row.alpaca_order_id) await alpacaDelete(`/v2/orders/${row.alpaca_order_id}`, base);
    await pool.query(
      `UPDATE pee1_stealth_queue SET status='cancelled' WHERE id=$1`, [row.id]
    ).catch(() => {});
  }
  console.log(`[CB] Cancelled ${pending.rows.length} pending stealth queue row(s)`);
}

// ── Market-sell all open positions ────────────────────────────────────────
async function liquidateAllPositions(base) {
  const positions = await pool.query(
    `SELECT id, ticker, shares, alpaca_take_profit_order_id, alpaca_stop_loss_order_id
     FROM personal_trade_ledger
     WHERE status IN ('submitted', 'filled')`
  );

  for (const pos of positions.rows) {
    try {
      // Cancel bracket legs first
      if (pos.alpaca_take_profit_order_id)
        await alpacaDelete(`/v2/orders/${pos.alpaca_take_profit_order_id}`, base);
      if (pos.alpaca_stop_loss_order_id)
        await alpacaDelete(`/v2/orders/${pos.alpaca_stop_loss_order_id}`, base);

      const sellOrder = await alpacaPost("/v2/orders", {
        symbol:        pos.ticker,
        qty:           pos.shares,
        side:          "sell",
        type:          "market",
        time_in_force: "day",
      }, base);

      await pool.query(
        `UPDATE personal_trade_ledger
         SET status='closed', exit_reason='circuit_breaker_3pct',
             rationale_json = rationale_json || $1::jsonb,
             exit_filled_at = NOW()
         WHERE id=$2`,
        [JSON.stringify({ cb_exit_order_id: sellOrder.id, cb_reason: "standalone_3pct_fuse" }), pos.id]
      ).catch(e => console.error(`[CB] Ledger close failed for ${pos.ticker}:`, e.message));

      console.log(`[CB] Liquidated ${pos.ticker} | shares=${pos.shares} | sellOrderId=${sellOrder.id}`);
    } catch (err) {
      console.error(`[CB] CRITICAL: liquidation FAILED for ${pos.ticker}: ${err.message}`);
      await pool.query(
        `UPDATE personal_trade_ledger
         SET rationale_json = rationale_json || $1::jsonb
         WHERE id=$2`,
        [JSON.stringify({ cb_liquidation_failed: err.message }), pos.id]
      ).catch(() => {});
    }
  }
  return positions.rows.length;
}

// ── Main ──────────────────────────────────────────────────────────────────
export async function runCircuitBreaker() {
  console.log("[CB] Standalone circuit breaker check...");

  // ── Already active? ──────────────────────────────────────────────────
  const existing = await isCircuitBreakerActive().catch(() => null);
  if (existing) {
    console.log(`[CB] ⚡ Already active (${existing.trigger_reason}) — expires ${existing.expires_at}. No action.`);
    return { halted: true, reason: existing.trigger_reason, expires: existing.expires_at };
  }

  const BASE = await resolveAlpacaBase();
  const [accountRaw, thresholdStr, hoursStr] = await Promise.all([
    alpacaGet("/v2/account", BASE).catch(() => null),
    readConfig("circuit_breaker_threshold_pct", "3.0"),
    readConfig("circuit_breaker_hours", "24"),
  ]);

  const equityNow    = parseFloat(accountRaw?.equity ?? "0");
  const thresholdPct = parseFloat(thresholdStr);
  const hours        = parseInt(hoursStr, 10);

  if (equityNow <= 0) {
    console.log("[CB] Equity unavailable — skipping check");
    return { skipped: true };
  }

  // ── Session open equity ──────────────────────────────────────────────
  const sessionRes = await pool.query(
    `SELECT vault_equity_at_signal FROM personal_trade_ledger
     WHERE DATE(signal_detected_at) = CURRENT_DATE
     ORDER BY signal_detected_at ASC LIMIT 1`
  );
  const equityOpen = parseFloat(sessionRes.rows[0]?.vault_equity_at_signal ?? equityNow);

  const drawdownPct = ((equityOpen - equityNow) / equityOpen) * 100;
  console.log(`[CB] Drawdown check: ${drawdownPct.toFixed(2)}% / ${thresholdPct}% threshold | equityOpen=$${equityOpen.toFixed(2)} equityNow=$${equityNow.toFixed(2)}`);

  if (drawdownPct < thresholdPct) {
    console.log("[CB] Drawdown within limits. No action.");
    return { triggered: false, drawdownPct, thresholdPct };
  }

  // ── Fuse triggered ───────────────────────────────────────────────────
  await triggerCircuitBreaker({
    equityOpen, equityNow, drawdownPct, thresholdPct, hours,
    reason: "standalone_3pct_fuse",
  });

  await cancelStealthQueue(BASE);
  const liquidated = await liquidateAllPositions(BASE);

  console.log(`[CB] ⚡ FUSE BLOWN | liquidated ${liquidated} position(s) | halt for ${hours}h`);

  return {
    triggered:   true,
    drawdownPct,
    thresholdPct,
    liquidated,
    haltHours:   hours,
  };
}

export async function closeCircuitBreakerPool() {
  await pool.end();
}

// ── Direct execution ──────────────────────────────────────────────────────
if (process.argv[1]?.endsWith("circuit_breaker.mjs")) {
  runCircuitBreaker()
    .then(r => { console.log("[CB] Result:", JSON.stringify(r, null, 2)); process.exit(0); })
    .catch(e => { console.error("[CB] FATAL:", e.message); process.exit(1); })
    .finally(() => pool.end());
}
