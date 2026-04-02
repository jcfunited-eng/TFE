/**
 * web/scripts/execution/sentinel_monitor.mjs
 * PEE-1 Sentinel Monitor — Live Position Audit + Kill Switches
 *
 * Runs after each market day against all open positions in personal_trade_ledger.
 *
 * Four kill conditions:
 *   1. CIRCUIT BREAKER: portfolio dropped > max_drawdown_pct in session
 *      → liquidate ALL positions, halt new trades for circuit_breaker_hours
 *   2. SPY FLIP: SPY D_k flipped to 0/-1 → liquidate ALL positions
 *   3. CALAMITY: R_rev_k > 0 on individual position → market sell that position
 *   4. ZOMBIE:   position age > tau_in_max bars → market sell that position
 *
 * Circuit breaker state is written to pee1_circuit_breaker table.
 * pee1_runner checks this table before executing any new orders.
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

const ZOMBIE_BAR_THRESHOLD = parseInt(process.env.SENTINEL_ZOMBIE_BARS ?? "10", 10);

// ── Alpaca helpers (duplicated intentionally — sentinel is independent) ───
function alpacaHeaders() {
  return {
    "APCA-API-KEY-ID":     process.env.APCA_API_KEY_ID,
    "APCA-API-SECRET-KEY": process.env.APCA_API_SECRET_KEY,
    "Content-Type":        "application/json",
  };
}

async function resolveAlpacaBase() {
  try {
    const res = await pool.query(
      `SELECT value FROM pee1_execution_config WHERE key = 'execution_mode' LIMIT 1`
    );
    return (res.rows[0]?.value ?? "paper") === "live"
      ? "https://api.alpaca.markets"
      : "https://paper-api.alpaca.markets";
  } catch {
    return "https://paper-api.alpaca.markets";
  }
}

const ALPACA_DATA = "https://data.alpaca.markets";

async function alpacaGet(path, base) {
  const res = await fetch(`${base}${path}`, { headers: alpacaHeaders() });
  const body = await res.json();
  if (!res.ok) throw new Error(`Alpaca GET ${path} → ${res.status}: ${JSON.stringify(body)}`);
  return body;
}

async function alpacaPost(path, payload, base) {
  const res = await fetch(`${base}${path}`, {
    method: "POST",
    headers: alpacaHeaders(),
    body: JSON.stringify(payload),
  });
  const body = await res.json();
  if (!res.ok) throw new Error(`Alpaca POST ${path} → ${res.status}: ${JSON.stringify(body)}`);
  return body;
}

// ── Cancel open bracket legs before liquidating ──────────────────────────
async function cancelOrder(orderId, base) {
  try {
    await fetch(`${base}/v2/orders/${orderId}`, {
      method: "DELETE",
      headers: alpacaHeaders(),
    });
  } catch (e) {
    console.warn(`[SENTINEL] Could not cancel order ${orderId}: ${e.message}`);
  }
}

// ── Market sell ───────────────────────────────────────────────────────────
async function marketSell(ticker, qty, base) {
  return alpacaPost("/v2/orders", {
    symbol:        ticker,
    qty,
    side:          "sell",
    type:          "market",
    time_in_force: "day",
  }, base);
}

// ── Current SPY D_k ──────────────────────────────────────────────────────
async function fetchSpyDk() {
  try {
    const res = await pool.query(
      `SELECT snapshot_row_json FROM runtime_decisions_latest
       WHERE ticker = 'SPY' ORDER BY generated_at_utc DESC LIMIT 1`
    );
    if (!res.rows.length) return null;
    const snap = res.rows[0].snapshot_row_json ?? {};
    const dk = parseInt(snap.D_k ?? snap.d_k ?? "", 10);
    return isFinite(dk) ? dk : null;
  } catch {
    return null;
  }
}

// ── Current R_rev_k and bar age for a ticker ─────────────────────────────
async function fetchStructuralFields(ticker) {
  try {
    const res = await pool.query(
      `SELECT snapshot_row_json FROM runtime_decisions_latest
       WHERE ticker = $1 ORDER BY generated_at_utc DESC LIMIT 1`,
      [ticker]
    );
    if (!res.rows.length) return {};
    const snap = res.rows[0].snapshot_row_json ?? {};
    return {
      r_rev_k:   parseFloat(snap.R_rev_k ?? snap.r_rev_k ?? "NaN"),
      bar_count: parseInt(snap.bar_count ?? "", 10),
    };
  } catch {
    return {};
  }
}

// ── Open positions from ledger ────────────────────────────────────────────
async function fetchOpenPositions() {
  const res = await pool.query(
    `SELECT id, ticker, shares, alpaca_order_id,
            alpaca_take_profit_order_id, alpaca_stop_loss_order_id,
            entry_filled_at, signal_detected_at
     FROM personal_trade_ledger
     WHERE status IN ('submitted', 'filled')
     ORDER BY created_at ASC`
  );
  return res.rows;
}

// ── Ledger: mark closed ───────────────────────────────────────────────────
async function ledgerClose(id, exitReason, exitOrderId) {
  await pool.query(
    `UPDATE personal_trade_ledger
     SET status='closed', exit_reason=$1,
         rationale_json = rationale_json || $2::jsonb,
         exit_filled_at = NOW()
     WHERE id=$3`,
    [exitReason, JSON.stringify({ sentinel_exit_order_id: exitOrderId ?? null }), id]
  );
}

// ── Kill a single position ────────────────────────────────────────────────
async function killPosition(pos, exitReason, base) {
  const { ticker, shares, alpaca_take_profit_order_id, alpaca_stop_loss_order_id } = pos;
  console.log(`[SENTINEL] KILL ${ticker} | reason=${exitReason} | shares=${shares}`);

  // Cancel pending bracket legs so market sell doesn't conflict
  if (alpaca_take_profit_order_id) await cancelOrder(alpaca_take_profit_order_id, base);
  if (alpaca_stop_loss_order_id)   await cancelOrder(alpaca_stop_loss_order_id, base);

  let exitOrderId = null;
  try {
    const sellOrder = await marketSell(ticker, shares, base);
    exitOrderId = sellOrder.id;
    console.log(`[SENTINEL] Market sell placed | ${ticker} | orderId=${exitOrderId}`);
  } catch (err) {
    console.error(`[SENTINEL] CRITICAL: market sell FAILED for ${ticker}: ${err.message}`);
    // Still update ledger so the position is flagged — operator must intervene
    await pool.query(
      `UPDATE personal_trade_ledger
       SET rationale_json = rationale_json || $1::jsonb
       WHERE id=$2`,
      [JSON.stringify({ sentinel_kill_failed: err.message, kill_reason: exitReason }), pos.id]
    ).catch(() => {});
    return;
  }

  await ledgerClose(pos.id, exitReason, exitOrderId).catch(e => {
    console.error(`[SENTINEL] Ledger close failed for ${ticker}:`, e.message);
  });
}

// ── Circuit breaker ───────────────────────────────────────────────────────
async function fetchConfig(key) {
  const res = await pool.query(
    `SELECT value FROM pee1_execution_config WHERE key = $1`, [key]
  );
  return res.rows[0]?.value ?? null;
}

async function isCircuitBreakerActive() {
  const res = await pool.query(
    `SELECT id, trigger_reason, expires_at FROM pee1_circuit_breaker
     WHERE cleared_at IS NULL AND expires_at > NOW()
     ORDER BY triggered_at DESC LIMIT 1`
  );
  if (!res.rows.length) return null;
  return res.rows[0];
}

async function triggerCircuitBreaker({ equityOpen, equityNow, drawdownPct, thresholdPct, hours }) {
  const expiresAt = new Date(Date.now() + hours * 60 * 60 * 1000).toISOString();
  await pool.query(
    `INSERT INTO pee1_circuit_breaker
       (trigger_reason, expires_at, vault_equity_open, vault_equity_low, drawdown_pct, threshold_pct)
     VALUES ('max_drawdown', $1, $2, $3, $4, $5)`,
    [expiresAt, equityOpen, equityNow, drawdownPct, thresholdPct]
  );
  console.log(`[SENTINEL] ⚡ CIRCUIT BREAKER TRIGGERED | drawdown=${drawdownPct.toFixed(2)}% > ${thresholdPct}% | halt until ${expiresAt}`);
}

async function checkMaxDrawdown(equityNow) {
  // Session open equity = equity at the earliest 'submitted' trade today, or current
  const res = await pool.query(
    `SELECT vault_equity_at_signal FROM personal_trade_ledger
     WHERE DATE(signal_detected_at) = CURRENT_DATE
     ORDER BY signal_detected_at ASC LIMIT 1`
  );
  const equityOpen = parseFloat(res.rows[0]?.vault_equity_at_signal ?? equityNow);
  if (equityOpen <= 0) return null;

  const drawdownPct = ((equityOpen - equityNow) / equityOpen) * 100;
  const thresholdPct = parseFloat(await fetchConfig("max_drawdown_pct") ?? "5.0");
  const hours = parseInt(await fetchConfig("circuit_breaker_hours") ?? "24", 10);

  if (drawdownPct >= thresholdPct) {
    await triggerCircuitBreaker({ equityOpen, equityNow, drawdownPct, thresholdPct, hours });
    return { triggered: true, drawdownPct, thresholdPct };
  }
  return { triggered: false, drawdownPct, thresholdPct };
}

// ── Main ──────────────────────────────────────────────────────────────────
export async function runSentinel() {
  console.log("[SENTINEL] Starting position audit...");

  // Circuit breaker: check if already halted
  const existingHalt = await isCircuitBreakerActive().catch(() => null);
  if (existingHalt) {
    console.log(`[SENTINEL] ⚡ Circuit breaker ACTIVE (${existingHalt.trigger_reason}) — expires ${existingHalt.expires_at}. No new actions.`);
    return { halted: true, reason: existingHalt.trigger_reason, expires: existingHalt.expires_at };
  }

  const ALPACA_BASE = await resolveAlpacaBase();
  console.log(`[SENTINEL] Alpaca base: ${ALPACA_BASE}`);

  const [positions, spyDk, accountRaw] = await Promise.all([
    fetchOpenPositions(),
    fetchSpyDk(),
    alpacaGet("/v2/account", ALPACA_BASE).catch(() => null),
  ]);

  const equityNow = parseFloat(accountRaw?.equity ?? "0");
  console.log(`[SENTINEL] Open positions: ${positions.length} | SPY D_k: ${spyDk ?? "unknown"} | Equity: $${equityNow.toFixed(2)}`);

  // Max drawdown circuit breaker check (runs before any per-position logic)
  if (equityNow > 0) {
    const ddCheck = await checkMaxDrawdown(equityNow).catch(e => {
      console.error("[SENTINEL] Drawdown check failed:", e.message);
      return null;
    });
    if (ddCheck?.triggered) {
      console.log(`[SENTINEL] ⚡ MAX DRAWDOWN — liquidating all ${positions.length} positions`);
      for (const pos of positions) {
        await killPosition(pos, "sentinel_max_drawdown", ALPACA_BASE);
      }
      return { halted: true, reason: "max_drawdown", drawdownPct: ddCheck.drawdownPct };
    } else if (ddCheck) {
      console.log(`[SENTINEL] Drawdown check: ${ddCheck.drawdownPct.toFixed(2)}% / ${ddCheck.thresholdPct}% threshold — OK`);
    }
  }

  console.log(`[SENTINEL] Open positions: ${positions.length} | SPY D_k: ${spyDk ?? "unknown"}`);

  // Wave 3 flip — liquidate ALL positions if SPY D_k is no longer 1
  const spyFlip = spyDk !== null && spyDk !== 1;
  if (spyFlip) {
    console.log(`[SENTINEL] SPY D_k=${spyDk} — Wave 3 GONE — liquidating all positions`);
    for (const pos of positions) {
      await killPosition(pos, "sentinel_spy_flip", ALPACA_BASE);
    }
    return;
  }

  // Per-position checks
  for (const pos of positions) {
    const fields = await fetchStructuralFields(pos.ticker);

    // Calamity check: R_rev_k > 0
    if (isFinite(fields.r_rev_k) && fields.r_rev_k > 0) {
      await killPosition(pos, "sentinel_calamity", ALPACA_BASE);
      continue;
    }

    // Zombie check: position older than tau_in_max bars
    const barCount = isFinite(fields.bar_count) ? fields.bar_count : null;
    if (barCount !== null && barCount > ZOMBIE_BAR_THRESHOLD) {
      await killPosition(pos, "sentinel_zombie", ALPACA_BASE);
      continue;
    }

    console.log(`[SENTINEL] ${pos.ticker} CLEAR | R_rev_k=${fields.r_rev_k ?? "n/a"} | bar_count=${barCount ?? "n/a"}`);
  }

  console.log("[SENTINEL] Audit complete.");
}

export async function closeSentinelPool() {
  await pool.end();
}
