/**
 * web/scripts/execution/circuit_breaker.mjs
 * PEE-1 Standalone Circuit Breaker — 3% Portfolio Drawdown Fuse
 *
 * Runs independently of pee1_runner.mjs. Designed to be invoked frequently
 * (every 5–10 min via EventBridge during market hours) as an intraday fuse.
 *
 * Behavior:
 *   1. Fetch current Alpaca equity
 *   2. Compare to session-open equity (Alpaca last_equity — previous close)
 *   3. If drawdown >= max_drawdown_pct (default 5%):
 *      a. Cancel ALL pending stealth queue rows
 *      b. Market-sell ALL open positions via sentinel_monitor.killPosition logic
 *      c. Insert row into pee1_circuit_breaker with reason='standalone_drawdown_fuse'
 *   4. If circuit breaker already active: log and return — no double-trigger
 *
 * Config keys read from pee1_execution_config:
 *   max_drawdown_pct               — default 5.0 (unified with sentinel_monitor)
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
  ssl: { rejectUnauthorized: false },
});

// ── Numeric config validation ─────────────────────────────────────────────
// parseFloat can return NaN silently; NaN comparisons return false so the
// breaker never fires. Validate and fall back to spec default on invalid.
function parseThresholdSafe(rawValue, defaultVal, key, logPrefix) {
  const parsed = parseFloat(rawValue);
  if (!Number.isFinite(parsed) || parsed < 0) {
    console.warn(`[${logPrefix}] Invalid ${key}='${rawValue}' — falling back to spec default ${defaultVal}`);
    return defaultVal;
  }
  return parsed;
}

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
  try {
    await pool.query(
      `INSERT INTO pee1_circuit_breaker
         (trigger_reason, expires_at, vault_equity_open, vault_equity_low, drawdown_pct, threshold_pct)
       VALUES ($1, $2, $3, $4, $5, $6)`,
      [reason, expiresAt, equityOpen, equityNow, drawdownPct, thresholdPct]
    );
    console.log(`[CB] ⚡ CIRCUIT BREAKER TRIGGERED | reason=${reason} | drawdown=${drawdownPct.toFixed(2)}% | halt until ${expiresAt}`);
    return { fired: true };
  } catch (e) {
    // CB-3: partial unique index (migration 010) enforces at-most-one
    // uncleared row. If a concurrent runCircuitBreaker invocation fired
    // first, our INSERT hits unique_violation (SQLSTATE 23505). Treat as
    // no-op — the other invocation already logged and initiated liquidation.
    if (e.code === "23505") {
      console.log(`[CB] Concurrent trigger detected — another invocation fired first (unique_violation). Skipping duplicate.`);
      return { fired: false, raced: true };
    }
    throw e;
  }
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
    ).catch(e => console.error(`[CB] Stealth queue cancel UPDATE failed for id=${row.id}: ${e.message}`));
  }
  console.log(`[CB] Cancelled ${pending.rows.length} pending stealth queue row(s)`);
}

// ── Ledger write helper (D4.5 pattern) ───────────────────────────────────
// Retry primary UPDATE up to 3 times with 500ms backoff. On all-fail,
// append recovery breadcrumbs to rationale_json so trade_auditor and
// zombie check can reconcile the position as closed. On both-fail,
// CRITICAL log with all IDs for manual CloudWatch recovery.
async function closePositionInLedgerWithRetry(ledgerId, ticker, sellOrderId) {
  const primary = async () => pool.query(
    `UPDATE personal_trade_ledger
       SET status='closed',
           exit_reason='circuit_breaker_3pct',
           rationale_json = rationale_json || $1::jsonb,
           exit_filled_at = NOW()
     WHERE id=$2`,
    [JSON.stringify({ cb_exit_order_id: sellOrderId, cb_reason: "standalone_drawdown_fuse" }), ledgerId],
  );

  let lastErr;
  for (let attempt = 1; attempt <= 3; attempt++) {
    try {
      await primary();
      return;
    } catch (e) {
      lastErr = e;
      if (attempt < 3) await new Promise(r => setTimeout(r, 500));
    }
  }

  console.error(`[CB] PRIMARY liquidation write failed after 3 attempts for ${ticker} ledgerId=${ledgerId}: ${lastErr.message}. Writing fallback to rationale_json.`);
  try {
    await pool.query(
      `UPDATE personal_trade_ledger
         SET rationale_json = rationale_json || jsonb_build_object(
               'cb_fallback_sell_order_id', $1::text,
               'cb_fallback_reason',        'primary_close_update_failed',
               'cb_fallback_write_at',      to_char(now() at time zone 'utc',
                                              'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
               'cb_fallback_primary_err',   $2::text
             )
       WHERE id=$3`,
      [sellOrderId, lastErr.message, ledgerId],
    );
    console.error(`[CB] Fallback recovery breadcrumbs written for ${ticker} ledgerId=${ledgerId} sellOrderId=${sellOrderId}`);
  } catch (fbErr) {
    console.error(
      `[CB] CRITICAL: both primary and fallback liquidation writes failed for ` +
      `${ticker} ledgerId=${ledgerId} sellOrderId=${sellOrderId} ` +
      `primary_err=${lastErr.message} fallback_err=${fbErr.message}`
    );
  }
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

      await closePositionInLedgerWithRetry(pos.id, pos.ticker, sellOrder.id);

      console.log(`[CB] Liquidated ${pos.ticker} | shares=${pos.shares} | sellOrderId=${sellOrder.id}`);
    } catch (err) {
      console.error(`[CB] CRITICAL: liquidation FAILED for ${pos.ticker} ledgerId=${pos.id}: ${err.message}`);
      try {
        await pool.query(
          `UPDATE personal_trade_ledger
           SET rationale_json = rationale_json || $1::jsonb
           WHERE id=$2`,
          [JSON.stringify({ cb_liquidation_failed: err.message, cb_liquidation_failed_at: new Date().toISOString() }), pos.id]
        );
      } catch (fbErr) {
        console.error(`[CB] CRITICAL: liquidation-failure breadcrumb write also failed for ${pos.ticker} ledgerId=${pos.id}: ${fbErr.message}`);
      }
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
    readConfig("max_drawdown_pct", "5.0"),
    readConfig("circuit_breaker_hours", "24"),
  ]);

  const equityNow    = parseFloat(accountRaw?.equity ?? "0");
  const thresholdPct = parseThresholdSafe(thresholdStr, 5.0, "max_drawdown_pct", "CB");
  const hoursRaw     = parseInt(hoursStr, 10);
  const hours        = Number.isFinite(hoursRaw) && hoursRaw > 0 ? hoursRaw : 24;

  if (equityNow <= 0) {
    console.log("[CB] Equity unavailable — skipping check");
    return { skipped: true };
  }

  // ── Session open equity ──────────────────────────────────────────────
  // Use Alpaca last_equity (previous close) as session-open reference.
  // The old fallback (earliest signal today) yielded equityNow on quiet
  // days (zero signals), collapsing drawdown to 0 and silently disabling
  // the breaker. Wave 1 canonical selection produces quiet days by design.
  const equityOpen = parseFloat(accountRaw?.last_equity ?? "0");
  if (equityOpen <= 0) {
    console.warn(`[CB] Alpaca last_equity unavailable or non-positive (${accountRaw?.last_equity}) — skipping drawdown check`);
    return { skipped: true, reason: "no_last_equity" };
  }

  const drawdownPct = ((equityOpen - equityNow) / equityOpen) * 100;
  console.log(`[CB] Drawdown check: ${drawdownPct.toFixed(2)}% / ${thresholdPct}% threshold | equityOpen(last_equity)=$${equityOpen.toFixed(2)} equityNow=$${equityNow.toFixed(2)}`);

  if (drawdownPct < thresholdPct) {
    console.log("[CB] Drawdown within limits. No action.");
    return { triggered: false, drawdownPct, thresholdPct };
  }

  // ── Fuse triggered ───────────────────────────────────────────────────
  const triggerResult = await triggerCircuitBreaker({
    equityOpen, equityNow, drawdownPct, thresholdPct, hours,
    reason: "standalone_drawdown_fuse",
  });

  if (triggerResult.raced) {
    console.log(`[CB] Skipping cancel/liquidate — another invocation is handling it.`);
    return { triggered: false, raced: true, drawdownPct, thresholdPct };
  }

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
