/**
 * web/scripts/execution/sentinel_monitor.mjs
 * PEE-1 Sentinel Monitor — Live Position Audit + Kill Switches
 *
 * Runs after each market day against all open positions in personal_trade_ledger.
 *
 * Three kill conditions (all result in immediate market sell):
 *   1. ZOMBIE:   position age > tau_in_max bars (default 10) with no exit
 *   2. CALAMITY: R_rev_k > 0 (reversion factor triggered)
 *   3. SPY FLIP: SPY D_k flipped to 0 or -1 — Wave 3 gone, full liquidation
 *
 * For each kill: places a market sell via Alpaca, updates ledger with exit reason.
 * If a kill cannot be placed (Alpaca error) → logs CRITICAL and continues to next.
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
    "APCA-API-KEY-ID":     process.env.ALPACA_API_KEY,
    "APCA-API-SECRET-KEY": process.env.ALPACA_SECRET_KEY,
    "Content-Type":        "application/json",
  };
}
const ALPACA_BASE = process.env.ALPACA_PAPER !== "0"
  ? "https://paper-api.alpaca.markets"
  : "https://api.alpaca.markets";
const ALPACA_DATA = "https://data.alpaca.markets";

async function alpacaGet(path, base = ALPACA_BASE) {
  const res = await fetch(`${base}${path}`, { headers: alpacaHeaders() });
  const body = await res.json();
  if (!res.ok) throw new Error(`Alpaca GET ${path} → ${res.status}: ${JSON.stringify(body)}`);
  return body;
}

async function alpacaPost(path, payload) {
  const res = await fetch(`${ALPACA_BASE}${path}`, {
    method: "POST",
    headers: alpacaHeaders(),
    body: JSON.stringify(payload),
  });
  const body = await res.json();
  if (!res.ok) throw new Error(`Alpaca POST ${path} → ${res.status}: ${JSON.stringify(body)}`);
  return body;
}

// ── Cancel open bracket legs before liquidating ──────────────────────────
async function cancelOrder(orderId) {
  try {
    await fetch(`${ALPACA_BASE}/v2/orders/${orderId}`, {
      method: "DELETE",
      headers: alpacaHeaders(),
    });
  } catch (e) {
    console.warn(`[SENTINEL] Could not cancel order ${orderId}: ${e.message}`);
  }
}

// ── Market sell ───────────────────────────────────────────────────────────
async function marketSell(ticker, qty) {
  return alpacaPost("/v2/orders", {
    symbol:        ticker,
    qty,
    side:          "sell",
    type:          "market",
    time_in_force: "day",
  });
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
async function killPosition(pos, exitReason) {
  const { ticker, shares, alpaca_take_profit_order_id, alpaca_stop_loss_order_id } = pos;
  console.log(`[SENTINEL] KILL ${ticker} | reason=${exitReason} | shares=${shares}`);

  // Cancel pending bracket legs so market sell doesn't conflict
  if (alpaca_take_profit_order_id) await cancelOrder(alpaca_take_profit_order_id);
  if (alpaca_stop_loss_order_id)   await cancelOrder(alpaca_stop_loss_order_id);

  let exitOrderId = null;
  try {
    const sellOrder = await marketSell(ticker, shares);
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

// ── Main ──────────────────────────────────────────────────────────────────
export async function runSentinel() {
  console.log("[SENTINEL] Starting position audit...");

  const [positions, spyDk] = await Promise.all([
    fetchOpenPositions(),
    fetchSpyDk(),
  ]);

  console.log(`[SENTINEL] Open positions: ${positions.length} | SPY D_k: ${spyDk ?? "unknown"}`);

  // Wave 3 flip — liquidate ALL positions if SPY D_k is no longer 1
  const spyFlip = spyDk !== null && spyDk !== 1;
  if (spyFlip) {
    console.log(`[SENTINEL] SPY D_k=${spyDk} — Wave 3 GONE — liquidating all positions`);
    for (const pos of positions) {
      await killPosition(pos, "sentinel_spy_flip");
    }
    return;
  }

  // Per-position checks
  for (const pos of positions) {
    const fields = await fetchStructuralFields(pos.ticker);

    // Calamity check: R_rev_k > 0
    if (isFinite(fields.r_rev_k) && fields.r_rev_k > 0) {
      await killPosition(pos, "sentinel_calamity");
      continue;
    }

    // Zombie check: position older than tau_in_max bars
    const barCount = isFinite(fields.bar_count) ? fields.bar_count : null;
    if (barCount !== null && barCount > ZOMBIE_BAR_THRESHOLD) {
      await killPosition(pos, "sentinel_zombie");
      continue;
    }

    console.log(`[SENTINEL] ${pos.ticker} CLEAR | R_rev_k=${fields.r_rev_k ?? "n/a"} | bar_count=${barCount ?? "n/a"}`);
  }

  console.log("[SENTINEL] Audit complete.");
}

export async function closeSentinelPool() {
  await pool.end();
}
