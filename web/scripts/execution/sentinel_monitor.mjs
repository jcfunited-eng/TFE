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
// assessExit import removed — EXIT-S removed (arbitrary thresholds, no backtest)

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

const ZOMBIE_BAR_THRESHOLD = parseInt(process.env.SENTINEL_ZOMBIE_BARS ?? "10", 10);

// ── Recently-killed tracking (prevents orphan re-adoption loop) ──────────
// When sentinel kills a position, Alpaca may still show it for 1-2 cycles
// while the sell settles. Without this, orphan sync re-adopts the position,
// EXIT-A re-kills it, generating 5+ duplicate sell orders per ticker.
// Entries expire after 15 minutes (well past settlement).
//
// CRITICAL: Uses DB, not in-memory Map, because the PEE-1 Runner and
// Sentinel Daemon are SEPARATE PROCESSES with separate module state.
// Runner killed UTZ at 13:33:47, Daemon adopted it at 13:33:53 because
// the in-memory Map existed only in the Runner's process.
export const recentlyKilledTickers = new Map(); // in-memory fallback
const KILL_COOLDOWN_MS = 15 * 60 * 1000; // 15 minutes

export async function markRecentlyKilled(ticker) {
  const key = ticker.trim().toUpperCase();
  recentlyKilledTickers.set(key, Date.now());
  // Persist to DB so other processes (Runner vs Daemon) see the kill
  try {
    await pool.query(
      `INSERT INTO pee1_execution_config (key, value)
       VALUES ($1, $2)
       ON CONFLICT (key) DO UPDATE SET value = $2`,
      [`kill_cooldown_${key}`, new Date().toISOString()]
    );
  } catch { /* non-fatal — in-memory fallback still works within same process */ }
}

export async function isRecentlyKilled(ticker) {
  const key = ticker.trim().toUpperCase();
  // Check in-memory first (same process)
  const killedAt = recentlyKilledTickers.get(key);
  if (killedAt && Date.now() - killedAt <= KILL_COOLDOWN_MS) return true;
  if (killedAt && Date.now() - killedAt > KILL_COOLDOWN_MS) {
    recentlyKilledTickers.delete(key);
  }
  // Check DB (cross-process)
  try {
    const res = await pool.query(
      `SELECT value FROM pee1_execution_config WHERE key = $1`,
      [`kill_cooldown_${key}`]
    );
    if (res.rows.length > 0) {
      const dbTime = new Date(res.rows[0].value).getTime();
      if (Date.now() - dbTime <= KILL_COOLDOWN_MS) return true;
      // Expired — clean up
      await pool.query(`DELETE FROM pee1_execution_config WHERE key = $1`, [`kill_cooldown_${key}`]);
    }
  } catch { /* non-fatal */ }
  return false;
}

// ── Market hours check for EXIT-F (prevents stale overnight price exits) ─
// Paper API returns unreliable prices outside market hours. BELFB showed
// $170 overnight (actual $252), triggering a false -33.6% catastrophic exit.
// EXIT-F must only fire during real market hours.
export function isMarketHoursForExitF(now = new Date()) {
  const h = now.getUTCHours();
  const m = now.getUTCMinutes();
  const minuteOfDay = h * 60 + m;
  const open  = 13 * 60 + 30;  // 13:30 UTC = 9:30 AM ET
  const close = 20 * 60;       // 20:00 UTC = 4:00 PM ET
  return minuteOfDay >= open && minuteOfDay <= close;
}

// ── Phantom cleanup grace period (prevents killing orders still filling) ──
// GENB was submitted at 13:34, zombie check at 13:39 (5 min) declared it
// phantom because Alpaca hadn't filled yet. Grace period: 30 minutes.
const PHANTOM_GRACE_MS = 30 * 60 * 1000; // 30 minutes

// ── 7-day minimum hold (prevents premature losing exits) ─────────────
// Production data (201 matched positions, Polygon verified):
//   45 positions killed within 1 hour: 4.4% WR
//   85% of D_k collapse exits recovered at 10-20 days
//   73% of early losers (0-3d) were winners at 20 days
//   Optimal: 7 days → projected 67.1% WR (from 41.3%)
// Winning exits (EXIT-A, EXIT-H) always fire. -10% catastrophic always fires.
// Only LOSING exits (EXIT-B D_k collapse, EXIT-C tau, SPY flip) are held.
export const MIN_HOLD_DAYS = 7;

export function shouldPhantomCleanup(pos) {
  if (pos.entry_filled_at) return false; // filled = never phantom
  const createdAt = pos.created_at ?? pos.signal_detected_at;
  if (!createdAt) return true; // no timestamp = stale, clean up
  const age = Date.now() - new Date(createdAt).getTime();
  return age > PHANTOM_GRACE_MS;
}

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

// ── Current R_rev_k, bar age, S_UF, D_k for a ticker ────────────────────
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
      r_rev_k:     parseFloat(snap.R_rev_k ?? snap.r_rev_k ?? "NaN"),
      bar_count:   parseInt(snap.bar_count ?? "", 10),
      s_uf:        parseFloat(snap.S_UF ?? snap.s_uf ?? "NaN"),
      d_k:         parseInt(snap.D_k ?? snap.d_k ?? "NaN", 10),
      neighbor_wr: parseFloat(snap.neighbor_wr ?? "NaN"),
    };
  } catch {
    return {};
  }
}

// ── Open positions from ledger ────────────────────────────────────────────
async function fetchOpenPositions() {
  const res = await pool.query(
    `SELECT id, ticker, shares, signal_class, alpaca_order_id,
            alpaca_take_profit_order_id, alpaca_stop_loss_order_id,
            entry_filled_at, entry_filled_price, signal_detected_at, created_at,
            take_profit_price, stop_loss_price, status
     FROM personal_trade_ledger
     WHERE status IN ('pending', 'submitted', 'filled')
       AND (signal_class IS NULL OR signal_class != 'manual')
     ORDER BY created_at ASC`
  );
  return res.rows;
}

// ── Ledger: mark closed, compute P&L if exit price known ─────────────────
async function ledgerClose(id, exitReason, exitOrderId, exitFilledPrice = null) {
  // Fetch entry data to compute P&L
  let pl = null;
  let plPct = null;
  if (exitFilledPrice != null) {
    try {
      const posRes = await pool.query(
        `SELECT entry_filled_price, shares FROM personal_trade_ledger WHERE id=$1`, [id]
      );
      const pos = posRes.rows[0];
      const entry = parseFloat(pos?.entry_filled_price ?? "0");
      const shares = parseFloat(pos?.shares ?? "0");
      if (entry > 0 && shares > 0) {
        pl = (exitFilledPrice - entry) * shares;
        plPct = ((exitFilledPrice - entry) / entry) * 100;
      }
    } catch { /* non-fatal */ }
  }
  await pool.query(
    `UPDATE personal_trade_ledger
     SET status='closed', exit_reason=$1,
         rationale_json = rationale_json || $2::jsonb,
         exit_filled_at = NOW(),
         exit_filled_price = COALESCE($4, exit_filled_price),
         p_l = COALESCE($5, p_l),
         p_l_pct = COALESCE($6, p_l_pct)
     WHERE id=$3`,
    [exitReason, JSON.stringify({ sentinel_exit_order_id: exitOrderId ?? null }), id,
     exitFilledPrice, pl, plPct]
  );
}

// ── Kill a single position ────────────────────────────────────────────────
async function killPosition(pos, exitReason, base) {
  const { id, ticker, shares, alpaca_order_id, alpaca_take_profit_order_id, alpaca_stop_loss_order_id } = pos;

  // ── Exit-blocked check: don't retry positions that can't be sold ──────
  // Delisted/inactive assets get marked exit_blocked. Don't spam Alpaca.
  try {
    const blockedCheck = await pool.query(
      `SELECT rationale_json->>'exit_blocked' AS blocked FROM personal_trade_ledger WHERE id=$1`, [id]
    );
    if (blockedCheck.rows[0]?.blocked === "true") {
      return; // Silently skip — already logged when blocked was set
    }
  } catch { /* non-fatal */ }

  // ── Market-hours gate: defer sells to next open-market cycle ──────
  if (!isMarketHoursForExitF()) {
    console.log(`[SENTINEL] KILL DEFERRED ${ticker} | reason=${exitReason} — market closed, will retry next open cycle`);
    return;
  }

  console.log(`[SENTINEL] KILL ${ticker} | reason=${exitReason} | shares=${shares}`);

  // Track this kill so orphan sync won't re-adopt while Alpaca settles
  await markRecentlyKilled(ticker);

  // Cancel ALL open orders for this ticker — not just the bracket legs.
  // Previous kill attempts may have left pending sell orders that hold shares.
  try {
    const openOrders = await alpacaGet(`/v2/orders?status=open&symbols=${encodeURIComponent(ticker)}`, base).catch(() => []);
    if (Array.isArray(openOrders)) {
      for (const o of openOrders) {
        await cancelOrder(o.id, base);
      }
      if (openOrders.length > 0) {
        console.log(`[SENTINEL] ${ticker} — cancelled ${openOrders.length} open order(s) before sell`);
      }
    }
  } catch { /* non-fatal — fall through to bracket cancels */ }

  // Also cancel known bracket legs (may already be cancelled above, but safe to retry)
  if (alpaca_order_id)             await cancelOrder(alpaca_order_id, base);
  if (alpaca_take_profit_order_id) await cancelOrder(alpaca_take_profit_order_id, base);
  if (alpaca_stop_loss_order_id)   await cancelOrder(alpaca_stop_loss_order_id, base);

  // Delay to let Alpaca process all cancellations before selling
  await new Promise(r => setTimeout(r, 1500));

  // Verify position still exists in Alpaca — bracket TP/SL may have already closed it
  let sellQty = shares;  // default to DB value, override with Alpaca actual
  try {
    const alpacaPos = await alpacaGet(`/v2/positions/${encodeURIComponent(ticker)}`, base);
    const alpacaQty = parseFloat(alpacaPos?.qty ?? "0");
    if (alpacaQty <= 0) {
      // Short or zero — don't sell, just close DB record
      console.log(`[SENTINEL] ${ticker} — Alpaca qty=${alpacaQty} (already closed or short). Marking DB closed without sell.`);
      await ledgerClose(id, `${exitReason}_bracket_exit`, null).catch(e => {
        console.error(`[SENTINEL] Ledger close failed for ${ticker}:`, e.message);
      });
      return;
    }
    // Use Alpaca's actual qty — DB may be stale (e.g. partial fill on entry)
    if (alpacaQty !== shares) {
      console.log(`[SENTINEL] ${ticker} — qty mismatch: DB=${shares}, Alpaca=${alpacaQty}. Using Alpaca qty.`);
    }
    sellQty = alpacaQty;
  } catch (e) {
    const msg = String(e.message);
    if (msg.includes("40410000") || msg.toLowerCase().includes("position does not exist")) {
      // Bracket already closed the position (TP or SL fired) — try to get exit price from legs
      let bracketExitPrice = null;
      if (alpaca_order_id) {
        try {
          const parentOrder = await alpacaGet(`/v2/orders/${alpaca_order_id}`, base);
          for (const leg of (parentOrder?.legs ?? [])) {
            if (leg.filled_avg_price && leg.side === "sell") {
              bracketExitPrice = parseFloat(leg.filled_avg_price);
              break;
            }
          }
        } catch { /* non-fatal */ }
      }
      console.log(`[SENTINEL] ${ticker} — position already closed in Alpaca (bracket exit @ $${bracketExitPrice ?? "unknown"}). Marking DB closed.`);
      await ledgerClose(id, `${exitReason}_bracket_exit`, null, bracketExitPrice).catch(ex => {
        console.error(`[SENTINEL] Ledger close failed for ${ticker}:`, ex.message);
      });
      return;
    }
    // Other error — log but continue and attempt sell anyway
    console.warn(`[SENTINEL] ${ticker} — position existence check error: ${msg}. Attempting sell anyway.`);
  }

  // ── Idempotent kill: check if this position already has a pending exit ───
  // If a prior cycle submitted a sell but the fill wasn't confirmed, don't
  // re-submit. Instead, poll the existing order for fill status.
  try {
    const pendingCheck = await pool.query(
      `SELECT rationale_json->>'sentinel_exit_order_id' AS order_id
       FROM personal_trade_ledger WHERE id=$1`, [id]
    );
    const pendingOrderId = pendingCheck.rows[0]?.order_id;
    if (pendingOrderId && pendingOrderId !== "null") {
      // Prior sell exists — check its status instead of re-submitting
      try {
        const orderStatus = await alpacaGet(`/v2/orders/${pendingOrderId}`, base);
        if (orderStatus?.filled_avg_price) {
          const fillPrice = parseFloat(orderStatus.filled_avg_price);
          console.log(`[SENTINEL] Pending sell confirmed filled: ${ticker} @ $${fillPrice} (order ${pendingOrderId})`);
          await ledgerClose(id, exitReason, pendingOrderId, fillPrice).catch(e => {
            console.error(`[SENTINEL] Ledger close failed for ${ticker}:`, e.message);
          });
          return;
        }
        if (orderStatus?.status === "canceled" || orderStatus?.status === "cancelled" || orderStatus?.status === "expired") {
          console.log(`[SENTINEL] Pending sell ${orderStatus.status}: ${ticker} — clearing, will retry`);
          // Clear the pending order so next cycle can retry
          await pool.query(
            `UPDATE personal_trade_ledger SET rationale_json = rationale_json - 'sentinel_exit_order_id' WHERE id=$1`, [id]
          ).catch(() => {});
        } else {
          console.log(`[SENTINEL] Pending sell still open: ${ticker} status=${orderStatus?.status} — waiting`);
          return; // Don't re-submit while order is pending
        }
      } catch { /* order lookup failed — fall through to re-submit */ }
    }
  } catch { /* non-fatal */ }

  let exitOrderId = null;
  let exitFilledPrice = null;
  try {
    const sellOrder = await marketSell(ticker, sellQty, base);
    exitOrderId = sellOrder.id;
    console.log(`[SENTINEL] Market sell placed | ${ticker} | orderId=${exitOrderId}`);
  } catch (err) {
    const errMsg = String(err.message);
    // "not active" / 40010001: before permanently blocking, check whether Alpaca
    // still holds the position. If it's gone (404), it closed silently (bracket
    // TP/SL, merger, expiry) — reconcile the ledger rather than block. Only set
    // exit_blocked when Alpaca confirms the asset is genuinely untradeable.
    if (errMsg.includes("not active") || errMsg.includes("40010001")) {
      let alpacaHasPos = true;
      try {
        const alpacaPos = await alpacaGet(`/v2/positions/${encodeURIComponent(ticker)}`, base).catch(() => null);
        alpacaHasPos = alpacaPos !== null && parseFloat(alpacaPos?.qty ?? "0") > 0;
      } catch { /* non-fatal */ }

      if (!alpacaHasPos) {
        // Position already gone on Alpaca — closed silently without ledger update.
        console.log(`[SENTINEL] ${ticker} — "not active" but Alpaca has no position. Reconciling as alpaca_silent_close.`);
        await ledgerClose(id, `${exitReason}_alpaca_silent_close`, null).catch(e => {
          console.error(`[SENTINEL] ${ticker} — ledgerClose after silent reconcile failed: ${e.message}`);
        });
        return;
      }

      // Asset is on Alpaca but genuinely untradeable — block future attempts.
      console.error(`[SENTINEL] ASSET INACTIVE: ${ticker} — position exists but cannot sell, marking exit_blocked`);
      await pool.query(
        `UPDATE personal_trade_ledger
         SET rationale_json = rationale_json || $1::jsonb
         WHERE id=$2`,
        [JSON.stringify({ exit_blocked: true, exit_blocked_reason: "asset_not_active", kill_reason: exitReason }), id]
      ).catch(() => {});
      return;
    }
    console.error(`[SENTINEL] CRITICAL: market sell FAILED for ${ticker}: ${errMsg}`);
    await pool.query(
      `UPDATE personal_trade_ledger
       SET rationale_json = rationale_json || $1::jsonb
       WHERE id=$2`,
      [JSON.stringify({ sentinel_kill_failed: errMsg, kill_reason: exitReason }), id]
    ).catch(() => {});
    return;
  }

  // Store exit order ID immediately so idempotent check works on next cycle
  if (exitOrderId) {
    await pool.query(
      `UPDATE personal_trade_ledger
       SET rationale_json = rationale_json || $1::jsonb
       WHERE id=$2`,
      [JSON.stringify({ sentinel_exit_order_id: exitOrderId }), id]
    ).catch(() => {});
  }

  // Brief wait for market order to fill, then capture exit price for P&L
  if (exitOrderId) {
    await new Promise(r => setTimeout(r, 2000));
    try {
      const fillCheck = await alpacaGet(`/v2/orders/${exitOrderId}`, base);
      if (fillCheck?.filled_avg_price) {
        exitFilledPrice = parseFloat(fillCheck.filled_avg_price);
        console.log(`[SENTINEL] Exit fill: ${ticker} @ $${exitFilledPrice}`);
      }
    } catch { /* non-fatal — p_l will be null */ }
  }

  // Only mark ledger closed if the sell actually filled.
  // An unfilled order (null fill price) means the position is still open —
  // closing the ledger on an unfilled sell creates ledger/broker divergence.
  if (exitFilledPrice != null) {
    await ledgerClose(id, exitReason, exitOrderId, exitFilledPrice).catch(e => {
      console.error(`[SENTINEL] Ledger close failed for ${ticker}:`, e.message);
    });
  } else {
    console.warn(
      `[SENTINEL] SELL UNFILLED ${ticker} | orderId=${exitOrderId} | reason=${exitReason} — ` +
      `ledger NOT closed (position still open). Will retry next cycle.`
    );
  }
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

async function checkMaxDrawdown(equityNow, lastEquity) {
  // Session open equity = Alpaca last_equity (previous close).
  // The old fallback (earliest signal today) yielded equityNow on quiet
  // days (zero signals), collapsing drawdown to 0 and silently disabling
  // the breaker. Wave 1 canonical selection produces quiet days by design.
  const equityOpen = parseFloat(lastEquity ?? "0");
  if (equityOpen <= 0) {
    console.warn(`[SENTINEL] Alpaca last_equity unavailable or non-positive (${lastEquity}) — skipping drawdown check`);
    return null;
  }

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

  // ── Orphan sync: adopt Alpaca positions missing from the ledger ────────
  // Runs every cycle. Finds real positions on Alpaca that have no ledger row
  // and inserts them so exit logic can manage them. Any post-submission
  // ledger UPDATE failure (see D4.5 bracket order-ID write-path fix) can
  // leave a filled Alpaca position invisible to sentinel; this catches it.
  {
    try {
      const alpacaPositions = await alpacaGet("/v2/positions", ALPACA_BASE).catch(() => []);
      if (Array.isArray(alpacaPositions) && alpacaPositions.length > 0) {
        const ledgerTickers = new Set(positions.map(p => String(p.ticker).trim().toUpperCase()));
        // Filter orphans — exclude recently killed (cross-process DB check)
        const orphans = [];
        for (const ap of alpacaPositions) {
          const sym = ap.symbol.trim().toUpperCase();
          if (ledgerTickers.has(sym)) continue;
          if (await isRecentlyKilled(sym)) {
            console.log(`[SENTINEL] Orphan skip: ${sym} — recently killed, Alpaca still settling`);
            continue;
          }
          orphans.push(ap);
        }
        if (orphans.length > 0) {
          console.log(`[SENTINEL] Orphan sync: ${orphans.length} Alpaca positions not in ledger — adopting.`);
          for (const ap of orphans) {
            const ticker = ap.symbol.trim().toUpperCase();
            const qty = parseInt(ap.qty, 10);
            const entryPrice = parseFloat(ap.avg_entry_price);
            try {
              // Check if already in ledger (any open row for this ticker)
              const existing = await pool.query(
                `SELECT id FROM personal_trade_ledger
                 WHERE UPPER(TRIM(ticker)) = $1 AND status IN ('submitted','filled')
                 LIMIT 1`, [ticker]
              );
              if (existing.rows.length > 0) continue;
              // Recover real entry date: check for the most recent closed row
              // for this ticker to carry the original entry_filled_at forward.
              // Never use NOW() — that resets hold timers off phantom timestamps.
              let realEntryAt = null;
              try {
                const prev = await pool.query(
                  `SELECT entry_filled_at FROM personal_trade_ledger
                   WHERE UPPER(TRIM(ticker)) = $1 AND status = 'closed'
                     AND entry_filled_at IS NOT NULL
                   ORDER BY entry_filled_at DESC LIMIT 1`, [ticker]
                );
                if (prev.rows.length > 0) {
                  realEntryAt = prev.rows[0].entry_filled_at;
                }
              } catch { /* non-fatal — fall back to NOW */ }
              const entryAt = realEntryAt ?? new Date().toISOString();
              await pool.query(
                `INSERT INTO personal_trade_ledger
                   (ticker, run_id, signal_class, shares, status,
                    entry_filled_price, entry_filled_at, signal_detected_at)
                 VALUES ($1, 'orphan_sync', 'CH2', $2, 'filled', $3, $4, $4)`,
                [ticker, qty, entryPrice, entryAt]
              );
              console.log(`[SENTINEL] Adopted orphan: ${ticker} qty=${qty} entry=$${entryPrice.toFixed(2)} entryAt=${entryAt}${realEntryAt ? ' (recovered)' : ' (no prior row)'}`);
            } catch (e) {
              console.warn(`[SENTINEL] Orphan insert failed for ${ticker}: ${e.message}`);
            }
          }
          // Re-fetch positions to include the newly adopted ones
          const refreshed = await fetchOpenPositions();
          positions.length = 0;
          positions.push(...refreshed);
          console.log(`[SENTINEL] Open positions after orphan sync: ${positions.length}`);
        }
      }
    } catch (orphanErr) {
      console.warn(`[SENTINEL] Orphan sync error: ${orphanErr.message}`);
    }
  }

  // Max drawdown circuit breaker check (runs before any per-position logic)
  if (equityNow > 0) {
    const ddCheck = await checkMaxDrawdown(equityNow, accountRaw?.last_equity).catch(e => {
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

  // Wave 3 flip — liquidate Ch1 (3WA) positions only if SPY D_k is no longer 1
  // Ch2 positions use their own per-ticker D_k exit (Exit B) — SPY flip does not apply
  const spyFlip = spyDk !== null && spyDk !== 1;
  if (spyFlip) {
    const exemptClasses = new Set(["CH2", "CH3"]);
    const ch1Positions = positions.filter(p => !exemptClasses.has(String(p.signal_class ?? "").trim().toUpperCase()));
    if (ch1Positions.length > 0) {
      console.log(`[SENTINEL] SPY D_k=${spyDk} — Wave 3 GONE — checking ${ch1Positions.length} Ch1 position(s)`);
      for (const pos of ch1Positions) {
        // EXIT-R9: 7-day minimum hold — don't liquidate young positions at a loss
        const spyEntryTime = pos.entry_filled_at ?? pos.signal_detected_at ?? pos.created_at;
        const spyPosAge = spyEntryTime
          ? Math.floor((Date.now() - new Date(spyEntryTime).getTime()) / (1000 * 60 * 60 * 24))
          : 999;
        if (spyPosAge < 7) {
          console.log(`[SENTINEL] SPY flip: ${pos.ticker} — MIN HOLD GUARD: skipping (age=${spyPosAge}d, need 7d)`);
          continue;
        }
        await killPosition(pos, "sentinel_spy_flip", ALPACA_BASE);
      }
    } else {
      console.log(`[SENTINEL] SPY D_k=${spyDk} — Wave 3 GONE — no Ch1 positions to liquidate (Ch2 positions use ticker-level D_k exit)`);
    }
  }

  // ── Sync fill/cancel status from Alpaca → ledger ─────────────────────────
  const submittedPositions = positions.filter(p => p.status === "submitted" || !p.entry_filled_at);
  if (submittedPositions.length > 0) {
    console.log(`[SENTINEL] Syncing fill status for ${submittedPositions.length} submitted positions...`);
    for (const pos of submittedPositions) {
      if (!pos.alpaca_order_id) continue;
      try {
        const order = await alpacaGet(`/v2/orders/${pos.alpaca_order_id}`, ALPACA_BASE);
        if (order?.status === "filled" || order?.status === "partially_filled") {
          const filledPrice = parseFloat(order.filled_avg_price ?? "0");
          const filledAt = order.filled_at ?? new Date().toISOString();
          if (filledPrice > 0) {
            await pool.query(
              `UPDATE personal_trade_ledger
               SET status='filled', entry_filled_price=$1, entry_filled_at=$2
               WHERE id=$3 AND status='submitted'`,
              [filledPrice, filledAt, pos.id]
            );
            console.log(`[SENTINEL] Fill synced: ${pos.ticker} @ $${filledPrice}`);
            pos.status = "filled"; // update in-memory so exit checks work
          }
        } else if ((order?.status === "canceled" || order?.status === "expired") && parseFloat(order.filled_qty ?? "0") === 0) {
          // Order was cancelled or expired before filling — mark ledger record as cancelled
          // REGN was stuck as "submitted" for 8 days because "expired" wasn't handled.
          await pool.query(
            `UPDATE personal_trade_ledger SET status='cancelled' WHERE id=$1 AND status='submitted'`,
            [pos.id]
          );
          console.log(`[SENTINEL] Cancel synced: ${pos.ticker} — order ${order.status}, never filled`);
          pos.status = "cancelled"; // skip exit checks below
        }
      } catch (e) {
        console.warn(`[SENTINEL] Fill sync failed for ${pos.ticker}: ${e.message}`);
      }
    }
  }

  // ── Sync ALL open positions against Alpaca (zombie detection) ─────────
  // Checks both 'filled' AND 'submitted' positions. If Alpaca has no
  // position for a ticker, the DB record is stale (bracket exit, cancelled
  // order, or phantom entry). This was missing before May 6 2026 — caused
  // 27 zombie positions to persist for weeks across deploys.
  // Debug: log first position's status to diagnose filtering
  if (positions.length > 0) {
    const p0 = positions[0];
    console.log(`[SENTINEL] Zombie debug: pos[0].ticker=${p0.ticker} pos[0].status='${p0.status}' type=${typeof p0.status} keys=${Object.keys(p0).slice(0,15).join(',')}`);
  }
  const openPositions = positions.filter(p => p.status === "filled" || p.status === "submitted" || p.status === "pending");
  console.log(`[SENTINEL] Zombie check: ${openPositions.length} open positions to verify against Alpaca (total=${positions.length})`);
  for (const pos of openPositions) {
    try {
      await alpacaGet(`/v2/positions/${encodeURIComponent(pos.ticker)}`, ALPACA_BASE);
      // Position still open on Alpaca — no action needed
    } catch (e) {
      const msg = String(e.message);
      console.log(`[SENTINEL] Zombie check ${pos.ticker}: Alpaca error — ${msg.slice(0, 150)}`);
      // Only act on definitive "not found" — not network errors
      if (!msg.includes("40410000") && !msg.toLowerCase().includes("position does not exist") && !msg.includes("404")) {
        continue; // transient error, skip
      }

      if ((pos.status === "submitted" || pos.status === "pending") && !pos.entry_filled_at) {
        // Phantom entry — never filled on Alpaca.
        // Grace period: wait 30 min before declaring phantom.
        // GENB was submitted at 13:34, zombie check at 13:39 (5 min) declared
        // it phantom because Alpaca hadn't filled yet. It filled at 14:17.
        if (!shouldPhantomCleanup(pos)) {
          console.log(`[SENTINEL] Phantom grace: ${pos.ticker} — ${pos.status}, Alpaca 404, but within 30min grace period. Waiting.`);
          continue;
        }
        await pool.query(
          `UPDATE personal_trade_ledger SET status='cancelled' WHERE id=$1`,
          [pos.id]
        );
        console.log(`[SENTINEL] Phantom cleanup: ${pos.ticker} — ${pos.status} but never existed on Alpaca after 30min. Marked cancelled.`);
        pos.status = "cancelled";
        continue;
      }

      // Filled position no longer on Alpaca — bracket TP/SL closed it.
      // Recovery chain (Gap 2 fix):
      //   1. Primary: use alpaca_order_id column to fetch parent order legs
      //   2. Fallback: use rationale_json.fallback_alpaca_order_id if column is null
      //   3. Last-resort: search Alpaca closed orders for ticker within 24h of entry
      let bracketExitPrice = null;
      let recoveredOrderId = null;

      const lookupOrderId = pos.alpaca_order_id
        ?? (pos.rationale_json?.fallback_alpaca_order_id ?? null);

      if (lookupOrderId) {
        try {
          const parentOrder = await alpacaGet(`/v2/orders/${lookupOrderId}`, ALPACA_BASE);
          for (const leg of (parentOrder?.legs ?? [])) {
            if (leg.filled_avg_price && leg.side === "sell") {
              bracketExitPrice = parseFloat(leg.filled_avg_price);
              recoveredOrderId = lookupOrderId;
              break;
            }
          }
        } catch { /* non-fatal */ }
      }

      // Last-resort: search Alpaca closed orders for this ticker within 24h of entry
      if (bracketExitPrice === null) {
        try {
          const entryTime = pos.entry_filled_at ?? pos.created_at;
          if (entryTime) {
            const after  = new Date(new Date(entryTime).getTime() - 86400_000).toISOString();
            const until  = new Date(Date.now() + 60_000).toISOString();
            const closed = await alpacaGet(
              `/v2/orders?status=closed&symbols=${encodeURIComponent(pos.ticker)}&after=${after}&until=${until}&limit=50&direction=desc`,
              ALPACA_BASE
            );
            if (Array.isArray(closed)) {
              for (const o of closed) {
                if (o.side === "sell" && o.filled_avg_price &&
                    parseFloat(o.qty ?? "0") === pos.shares) {
                  bracketExitPrice = parseFloat(o.filled_avg_price);
                  recoveredOrderId = o.id;
                  break;
                }
              }
            }
          }
        } catch { /* non-fatal */ }
      }

      // If we recovered an order ID via fallback, promote it to the column
      if (recoveredOrderId && !pos.alpaca_order_id) {
        await pool.query(
          `UPDATE personal_trade_ledger SET alpaca_order_id=$1 WHERE id=$2`,
          [recoveredOrderId, pos.id]
        ).catch(() => {});
      }

      const exitTag = bracketExitPrice !== null
        ? "bracket_tp_sl_exit"
        : "bracket_tp_sl_exit_unrecovered";
      console.log(`[SENTINEL] Bracket exit detected: ${pos.ticker} @ $${bracketExitPrice ?? "unknown"} (${exitTag}) — marking DB closed.`);
      await ledgerClose(pos.id, exitTag, null, bracketExitPrice).catch(ex => {
        console.error(`[SENTINEL] Ledger close failed for ${pos.ticker}:`, ex.message);
      });
      pos.status = "closed";
    }
  }

  // Per-position checks (skip cancelled or already-closed records)
  for (const pos of positions) {
    if (pos.status === "cancelled" || pos.status === "closed") continue;

    // ── EXIT-F: Catastrophic Floor ─────────────────────────────────────
    // Runs FIRST, before any structural check. Insurance against price
    // collapse when structural fields still say "fine."
    // Bracket orders use DAY TIF and expire after day 1 — this is the
    // permanent replacement. Does not depend on τ, D_k, S_UF, or any
    // structural field. Pure price-based disaster protection.
    //
    // GUARD: Only run during market hours. Paper API returns stale prices
    // overnight — BELFB showed $170 (actual $252) causing false -33.6% exit.
    // MYE showed $18.06 (actual $21.04) causing false -18.4% exit.
    try {
      if (!isMarketHoursForExitF()) {
        // Skip EXIT-F outside market hours — prices unreliable
      } else {
      const signalClassRaw = String(pos.signal_class ?? "").trim().toUpperCase();
      const catastrophicPct = signalClassRaw === "CH3" ? -0.01 : -0.10;
      const catastrophicLabel = signalClassRaw === "CH3"
        ? "ch3_catastrophic_floor" : "ch2_catastrophic_floor";

      // Skip same-day entries — give thesis at least 1 day
      const entryTime = pos.entry_filled_at ?? pos.signal_detected_at ?? pos.created_at;
      const entryDate = entryTime ? new Date(entryTime) : null;
      const posAgeDays = entryDate
        ? Math.floor((Date.now() - entryDate.getTime()) / (1000 * 60 * 60 * 24))
        : 999; // unknown age → don't skip

      if (posAgeDays >= 1) {
        const alpacaFloorPos = await alpacaGet(
          `/v2/positions/${encodeURIComponent(pos.ticker)}`, ALPACA_BASE
        ).catch(() => null);

        if (alpacaFloorPos) {
          const floorEntry = parseFloat(
            alpacaFloorPos.avg_entry_price ?? pos.entry_filled_price ?? "0"
          );
          const floorCurrent = parseFloat(alpacaFloorPos.current_price ?? "0");

          if (floorEntry > 0 && floorCurrent > 0) {
            const floorLoss = (floorCurrent - floorEntry) / floorEntry;

            if (floorLoss <= catastrophicPct) {
              console.log(
                `[SENTINEL] EXIT-F ${pos.ticker} | catastrophic floor ` +
                `(loss=${(floorLoss * 100).toFixed(1)}% threshold=${(catastrophicPct * 100).toFixed(1)}% ` +
                `entry=$${floorEntry.toFixed(2)} current=$${floorCurrent.toFixed(2)} age=${posAgeDays}d)`
              );
              await killPosition(pos, catastrophicLabel, ALPACA_BASE);
              continue;
            }
          }
        }
      }
      } // close else (market hours guard)
    } catch (floorErr) {
      // Non-fatal — continue to structural checks. Log so we know if
      // the floor check itself is failing.
      console.warn(`[SENTINEL] EXIT-F error for ${pos.ticker}: ${floorErr.message}`);
    }

    const fields = await fetchStructuralFields(pos.ticker);
    const signalClass = String(pos.signal_class ?? "").trim().toUpperCase();

    // ── EXIT-R9: 7-Day Minimum Hold (supersedes EXIT-R7 day-0 guard) ────
    // Production data (201 matched positions, Polygon forward-verified):
    //   45 positions killed within 1 hour: 4.4% WR
    //   85% of D_k collapse exits (EXIT-B) recovered at 10-20 days
    //   73% of early losers (0-3d hold) were winners at 20 days
    //   Optimal hold: 7 days → projected 67.1% WR (from 41.3%)
    //
    // Rule: No LOSING exit before 7 calendar days. Winning exits always
    //   allowed (EXIT-A acceleration, EXIT-H harvest, take-profit).
    //   -10% catastrophic floor always active (above).
    //   D_k collapse on day 0-6 is transient noise, not structural failure.
    const posEntryTime = pos.entry_filled_at ?? pos.signal_detected_at ?? pos.created_at;
    const posEntryDate = posEntryTime ? new Date(posEntryTime) : null;
    const posAge = posEntryDate
      ? Math.floor((Date.now() - posEntryDate.getTime()) / (1000 * 60 * 60 * 24))
      : 999;
    const isYoung = posAge < MIN_HOLD_DAYS;

    // Pre-check current P&L (used by minimum hold guard AND structural exit assessment)
    let currentPnlPct = null;
    try {
      const alpacaPosCheck = await alpacaGet(
        `/v2/positions/${encodeURIComponent(pos.ticker)}`, ALPACA_BASE
      ).catch(() => null);
      if (alpacaPosCheck) {
        const checkEntry = parseFloat(alpacaPosCheck.avg_entry_price ?? "0");
        const checkCurrent = parseFloat(alpacaPosCheck.current_price ?? "0");
        if (checkEntry > 0 && checkCurrent > 0) {
          currentPnlPct = ((checkCurrent - checkEntry) / checkEntry) * 100;
        }
      }
    } catch { /* non-fatal */ }

    // EXIT-S REMOVED. assessExit used arbitrary thresholds (EXIT_CUT_WR=0.50,
    // EXIT_HOLD_WR=0.55) described in the commit as "coin-flip intuition, not
    // backtested." It cut positions in the -2% to -10% zone based on neighbor WR,
    // but the thresholds had no derivation. EXIT-F (-10% catastrophic) and EXIT-B
    // (D_k collapse) remain as the structural exits.

    // ── Chapter 2 exit logic (independent path) ─────────────────────────
    if (signalClass === "CH2") {
      const currentSUf = isFinite(fields.s_uf) ? fields.s_uf : null;
      const currentDk  = isFinite(fields.d_k)  ? fields.d_k  : null;

      // EXIT-A REMOVED. S_UF >= 0.75 trigger had no derivation. Capped winners
      // at +3.25% avg / 4.4 days vs April's +12.34% / 23-30 days. Same class
      // as EXIT-D/H/S: structural-costume story, no backtest, winner-capping.
      // Destruction-pattern registry entry: GL-BRIEF-039.

      // ── EXIT-TIME: 20-Day Default Close ──────────────────────────────────
      // Fires for ALL positions regardless of P&L. No EXIT-R9 guard — this is
      // a time-based close, not a loss exit. EXIT-F already captured any -10%
      // catastrophe above. EXIT-TIME is the outer boundary for Wave 1 (the
      // 92.2% WR finding was measured over a 20-bar forward window).
      if (posAge >= 20) {
        const pnlStr = currentPnlPct !== null ? `${currentPnlPct.toFixed(1)}%` : "n/a";
        console.log(
          `[SENTINEL] CH2 EXIT-TIME ${pos.ticker} | age=${posAge}d — 20-day default exit (P&L=${pnlStr})`
        );
        await killPosition(pos, "ch2_exit_time", ALPACA_BASE);
        continue;
      }

      // Exit B — Directional collapse: D_k no longer 1
      // 7-day minimum hold: D_k collapse on day 0-6 is transient noise.
      // Production data: 85% of D_k collapse exits recovered at 10-20 days.
      // Only allow losing D_k exits after 7 days. Winning exits always allowed.
      if (currentDk !== null && currentDk !== 1) {
        if (isYoung && currentPnlPct !== null && currentPnlPct < 0) {
          console.log(`[SENTINEL] CH2 EXIT-B ${pos.ticker} | D_k=${currentDk} — MIN HOLD GUARD: holding (P&L=${currentPnlPct.toFixed(1)}%, age=${posAge}d, need ${MIN_HOLD_DAYS}d)`);
        } else {
          console.log(`[SENTINEL] CH2 EXIT-B ${pos.ticker} | D_k=${currentDk} — directional collapse, exiting (age=${posAge}d)`);
          await killPosition(pos, "ch2_exit_dk_collapse", ALPACA_BASE);
          continue;
        }
      }

      // ── Pre-fetch τ data from DB (used by EXIT-C τ exhaustion) ────────
      if (!global._tauCache) global._tauCache = {};
      if (!global._tauCache[pos.ticker]) {
        try {
          const histRes = await pool.query(
            `SELECT generated_at_utc::date AS day,
                    CAST(NULLIF(snapshot_row_json->>'D_k','') AS DOUBLE PRECISION) AS d_k
             FROM runtime_decisions_history
             WHERE ticker = $1
             ORDER BY generated_at_utc DESC
             LIMIT 400`,
            [pos.ticker]
          );
          const rows = histRes.rows;
          if (rows.length > 1) {
            const byDay = [];
            const seen = new Set();
            for (const r of rows) {
              const d = String(r.day);
              if (!seen.has(d)) { seen.add(d); byDay.push(r); }
            }
            let compressionDays = 0;
            let phase = "expansion";
            for (const r of byDay) {
              if (phase === "expansion") {
                if (r.d_k !== 1) { phase = "compression"; compressionDays++; }
              } else {
                if (r.d_k !== 1) { compressionDays++; }
                else { break; }
              }
            }
            const tauIn = compressionDays;
            const tauOut = Math.floor(tauIn / 3);
            global._tauCache[pos.ticker] = { tau_in_days: tauIn, tau_out_days: tauOut };
          }
        } catch { /* non-fatal */ }
      }

      // EXIT-D REMOVED. Trailing profit ratchet capped winners at first pullback
      // past +5%. April-May winners averaged +12.34% by riding full structural
      // moves. EXIT-D mechanically reduced avg win to +2.21% by selling on the
      // first dip after +5%. The ratchet constants (cushion, trailPct) had no
      // derivation. Winners now ride until EXIT-B (D_k collapse), EXIT-C
      // (τ exhaustion), or EXIT-F (-10% catastrophic).

      // EXIT-H REMOVED. Structural harvest sold at +5% gain when position
      // reached τ_out midpoint. This was the primary cap on winner magnitude.
      // A position that would have run to +25% over 30 days got sold at +5%
      // on day 15. The +5% threshold was hardcoded with no derivation.
      // EXIT-C (full τ exhaustion) remains as the structural-energy-based exit.

      // Exit C — Exhaustion Timer (τ_out)
      // τ already computed in pre-fetch above.
      try {
        const cached = (global._tauCache ?? {})[pos.ticker];
        if (cached && cached.tau_out_days > 0) {
          const tauIn = cached.tau_in_days;
          const tauOut = cached.tau_out_days;

          const entryDate = pos.signal_detected_at ?? pos.created_at;
          let positionAge = 0;
          if (entryDate) {
            positionAge = Math.floor((Date.now() - new Date(entryDate).getTime()) / (1000*60*60*24));
          }

          if (positionAge > tauOut) {
            // 7-day minimum hold: if tau says exit but position is young and losing, wait
            if (isYoung && currentPnlPct !== null && currentPnlPct < 0) {
              console.log(
                `[SENTINEL] CH2 EXIT-C ${pos.ticker} | τ_in=${tauIn}d τ_out=${tauOut}d age=${positionAge}d — ` +
                `MIN HOLD GUARD: τ spent but P&L=${currentPnlPct.toFixed(1)}%, holding until ${MIN_HOLD_DAYS}d`
              );
            } else {
              console.log(
                `[SENTINEL] CH2 EXIT-C ${pos.ticker} | τ_in=${tauIn}d τ_out=${tauOut}d age=${positionAge}d — ` +
                `structural energy spent, exiting`
              );
              await killPosition(pos, "ch2_exit_tau_exhaustion", ALPACA_BASE);
              continue;
            }
          }

          const remaining = tauOut - positionAge;
          console.log(
            `[SENTINEL] CH2 ${pos.ticker} CLEAR | S_UF=${currentSUf ?? "n/a"} | D_k=${currentDk ?? "n/a"} | ` +
            `τ_in=${tauIn}d τ_out=${tauOut}d age=${positionAge}d (${remaining}d remaining)`
          );
        } else {
          console.log(`[SENTINEL] CH2 ${pos.ticker} CLEAR | S_UF=${currentSUf ?? "n/a"} | D_k=${currentDk ?? "n/a"} | no τ data`);
        }
      } catch (tauErr) {
        console.log(`[SENTINEL] CH2 ${pos.ticker} CLEAR | S_UF=${currentSUf ?? "n/a"} | D_k=${currentDk ?? "n/a"} | τ error: ${tauErr.message}`);
      }
      continue;
    }

    // ── Chapter 3 — fuel gauge exit logic ────────────────────────────────
    if (signalClass === "CH3") {
      // CH3 exits: bracket (TP/SL) as safety net, fuel gauge as primary.
      // Fuel gauge: monitor real-time volume flow. When fuel runs out, exit.
      try {
        // Check if bracket already closed this position
        const alpacaPos = await alpacaGet(`/v2/positions/${encodeURIComponent(pos.ticker)}`, ALPACA_BASE).catch(() => null);
        if (!alpacaPos) {
          console.log(`[SENTINEL] CH3 ${pos.ticker} — position closed by bracket (TP/SL). Marking DB closed.`);
          await ledgerClose(pos.id, "ch3_bracket_exit", null).catch(e => {
            console.error(`[SENTINEL] CH3 ledger close failed for ${pos.ticker}:`, e.message);
          });
          continue;
        }

        const currentPrice = parseFloat(alpacaPos?.current_price ?? "0");
        const entryPrice   = parseFloat(alpacaPos?.avg_entry_price ?? "0");
        const plPct        = entryPrice > 0 ? (currentPrice - entryPrice) / entryPrice : 0;
        const tpPrice = parseFloat(pos.take_profit_price ?? "0");
        const slPrice = parseFloat(pos.stop_loss_price ?? "0");

        // ── Fuel Gauge: check real-time volume vs previous day ──────────
        // Volume is the fuel. When it dries up, the move is over.
        let fuelStatus = "UNKNOWN";
        let volumeRatio = null;
        try {
          const POLYGON_KEY = process.env.MASSIVE_API_KEY ?? process.env.POLYGON_API_KEY ?? "";
          if (POLYGON_KEY) {
            const snapResp = await fetch(
              `https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers/${pos.ticker}?apiKey=${POLYGON_KEY}`
            );
            if (snapResp.ok) {
              const snapData = await snapResp.json();
              const snap = snapData?.ticker;
              if (snap) {
                const todayVol  = snap.day?.v ?? 0;
                const prevDayVol = snap.prevDay?.v ?? 0;

                // Normalize by time of day (early = low volume is normal)
                const now = new Date();
                const marketMins = (now.getUTCHours() - 13) * 60 + (now.getUTCMinutes() - 30);
                const tradingMinutes = Math.max(1, Math.min(390, marketMins));
                const expectedRatio = tradingMinutes / 390;

                volumeRatio = prevDayVol > 0
                  ? todayVol / (prevDayVol * expectedRatio)
                  : 1.0;

                // Fuel classification
                if (volumeRatio >= 1.5)      fuelStatus = "SURGING";
                else if (volumeRatio >= 1.0)  fuelStatus = "FLOWING";
                else if (volumeRatio >= 0.7)  fuelStatus = "THINNING";
                else                          fuelStatus = "EXHAUSTED";
              }
            }
          }
        } catch (volErr) {
          // Volume check is best-effort
        }

        // ── CH3 exit: brackets are primary, sentinel is backstop ────────
        // The 3%/1.5% brackets on Alpaca handle normal exits.
        // Sentinel only intervenes for positions stuck past day 1
        // (brackets use DAY TIF and expire — EXIT-F catches the downside,
        // this catches stale positions that are slightly profitable but
        // the bracket TP never hit and expired).
        const ch3EntryTime = pos.entry_filled_at ?? pos.signal_detected_at ?? pos.created_at;
        const ch3AgeDays = ch3EntryTime
          ? Math.floor((Date.now() - new Date(ch3EntryTime).getTime()) / (1000*60*60*24))
          : 0;

        // Day 1: let the brackets work. Don't interfere.
        // Day 2+: brackets expired. If profitable, grab it. If losing, EXIT-F handles it.
        if (ch3AgeDays >= 1 && plPct > 0.005) {
          console.log(
            `[SENTINEL] CH3 ${pos.ticker} STALE GRAB | P&L=${(plPct*100).toFixed(2)}% | ` +
            `age=${ch3AgeDays}d | brackets expired, taking profit`
          );
          await killPosition(pos, "ch3_stale_grab", ALPACA_BASE);
          continue;
        }

        // Backstop: fuel fully exhausted AND position old — exit even at tiny loss
        if (fuelStatus === "EXHAUSTED" && ch3AgeDays >= 1 && plPct > -0.01) {
          console.log(
            `[SENTINEL] CH3 ${pos.ticker} FUEL OUT | P&L=${(plPct*100).toFixed(2)}% | ` +
            `Grabbing remaining profit`
          );
          await killPosition(pos, "ch3_fuel_exhausted", ALPACA_BASE);
          delete global._ch3FuelHistory[pos.ticker];
          continue;
        }

        console.log(
          `[SENTINEL] CH3 ${pos.ticker} HOLD | P&L=${(plPct*100).toFixed(2)}% | ` +
          `entry=${entryPrice} | current=${currentPrice} | TP=${tpPrice} | SL=${slPrice} | ` +
          `fuel=${fuelStatus}${volumeRatio ? `(${volumeRatio.toFixed(2)}x)` : ""}`
        );
      } catch (e) {
        console.warn(`[SENTINEL] CH3 ${pos.ticker} — position check error: ${e.message}`);
      }
      continue;
    }

    // ── Chapter 1 (3WA) and legacy exit logic ───────────────────────────

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
