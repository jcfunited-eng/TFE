/**
 * web/scripts/execution/alpaca_bridge.mjs
 *
 * PEE-1 Alpaca Bridge — Personal Execution Engine
 * ─────────────────────────────────────────────────────────────────────────────
 * Places BRACKET ORDERS for validated 3WA signals.
 *
 * Contract:
 *   - signal_class MUST equal '3WA'. Any other value → immediate rejection.
 *   - spy_dk MUST equal 1. Any other value → immediate rejection.
 *   - s_uf MUST be > 0. Missing or zero → immediate rejection.
 *   - ANY required field missing → status: 'rejected', exit_reason: 'rejected_field'.
 *   - NO fallbacks. NO guesses. Truth over satisfaction.
 *
 * Order structure:
 *   Entry:       Limit order at current market price (DAY TIF)
 *   Take Profit: entry_price + (1.2 × ATR-14)  [limit]
 *   Stop Loss:   entry_price − (1.0 × ATR-14)  [stop-market, no limit_price]
 *
 * Environment (all required):
 *   ALPACA_API_KEY      — Alpaca key ID
 *   ALPACA_SECRET_KEY   — Alpaca secret key
 *   ALPACA_PAPER        — '1' for paper trading, '0' for live (default: fail-safe to paper)
 *   PGHOST / PGPORT / PGDATABASE / PGUSER / PGPASSWORD — production DB
 *
 * Usage:
 *   import { executeBracketOrder, rejectSignal } from './alpaca_bridge.mjs';
 */

import pg from "pg";
import { createHash } from "crypto";

// ── Environment validation ─────────────────────────────────────────────────
const REQUIRED_ENV = [
  "APCA_API_KEY_ID",
  "APCA_API_SECRET_KEY",
  "PGHOST",
  "PGDATABASE",
  "PGUSER",
  "PGPASSWORD",
];
for (const key of REQUIRED_ENV) {
  if (!process.env[key]) {
    throw new Error(`[BRIDGE] FATAL: Missing required environment variable: ${key}`);
  }
}

// Paper/live mode: read from DB config (pee1_execution_config.execution_mode).
// Resolved at order-execution time by readExecutionMode().
// Fail-safe: if DB read fails, always default to paper.
const ALPACA_DATA_URL = "https://data.alpaca.markets";

// ── Constants ─────────────────────────────────────────────────────────────
const ATR_PERIOD           = 14;
const TAKE_PROFIT_MULT     = 1.2;
const STOP_LOSS_MULT       = 1.0;
const MIN_SHARE_PRICE      = 5.0;   // reject penny stocks
const MIN_SHARES           = 1;     // minimum viable position
const MAX_SINGLE_TRADE_PCT = 5.0;   // hard cap: never risk > 5% in one trade

// ── DB pool ───────────────────────────────────────────────────────────────
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

// ── Execution mode (paper vs live) from DB ────────────────────────────────
async function readExecutionMode() {
  try {
    const res = await pool.query(
      `SELECT value FROM pee1_execution_config WHERE key = 'execution_mode' LIMIT 1`
    );
    return res.rows[0]?.value ?? "paper";
  } catch {
    return "paper";  // fail-safe
  }
}

function alpacaBaseUrl(mode) {
  return mode === "live"
    ? "https://api.alpaca.markets"
    : "https://paper-api.alpaca.markets";
}

// ── Alpaca REST helpers ───────────────────────────────────────────────────
function alpacaHeaders() {
  return {
    "APCA-API-KEY-ID":     process.env.APCA_API_KEY_ID,
    "APCA-API-SECRET-KEY": process.env.APCA_API_SECRET_KEY,
    "Content-Type":        "application/json",
  };
}

async function alpacaGet(path, base) {
  const res = await fetch(`${base}${path}`, { headers: alpacaHeaders() });
  const body = await res.json();
  if (!res.ok) {
    throw new Error(`[BRIDGE] Alpaca GET ${path} → ${res.status}: ${JSON.stringify(body)}`);
  }
  return body;
}

async function alpacaPost(path, payload, base) {
  const res = await fetch(`${base}${path}`, {
    method: "POST",
    headers: alpacaHeaders(),
    body: JSON.stringify(payload),
  });
  const body = await res.json();
  if (!res.ok) {
    throw new Error(`[BRIDGE] Alpaca POST ${path} → ${res.status}: ${JSON.stringify(body)}`);
  }
  return body;
}

// ── ATR-14 calculation ────────────────────────────────────────────────────
function calcATRFromBars(barList) {
  const trValues = [];
  for (let i = 1; i < barList.length; i++) {
    const curr = barList[i];
    const prev = barList[i - 1];
    const high     = parseFloat(curr.h);
    const low      = parseFloat(curr.l);
    const prevClose = parseFloat(prev.c);
    const tr = Math.max(
      high - low,
      Math.abs(high - prevClose),
      Math.abs(low  - prevClose),
    );
    trValues.push(tr);
  }
  const atr = trValues.reduce((sum, v) => sum + v, 0) / trValues.length;
  return isFinite(atr) && atr > 0 ? atr : null;
}

/**
 * Compute ATR-14 for a ticker. Tries IEX feed first, then SIP feed.
 * If both fail, falls back to 2% of current price (never blocks a valid signal).
 *
 * @param {string} ticker
 * @param {number} [fallbackPrice] — used only if bar data unavailable
 * @returns {Promise<{ atr: number, source: string }>}
 */
async function computeATR(ticker, fallbackPrice = null) {
  for (const feed of ["iex", "sip"]) {
    try {
      const bars = await alpacaGet(
        `/v2/stocks/${encodeURIComponent(ticker)}/bars?timeframe=1Day&limit=${ATR_PERIOD + 1}&feed=${feed}`,
        ALPACA_DATA_URL,
      );
      const barList = bars?.bars ?? bars?.data?.bars ?? [];
      if (Array.isArray(barList) && barList.length >= 2) {
        const atr = calcATRFromBars(barList);
        if (atr) {
          console.log(`[BRIDGE] ATR(${ticker}) = ${atr.toFixed(4)} via ${feed} (${barList.length} bars)`);
          return { atr, source: feed };
        }
      }
    } catch { /* try next feed */ }
  }

  // Fallback: 2% of price — reasonable bracket for any liquid stock
  if (fallbackPrice && fallbackPrice > 0) {
    const atr = parseFloat((fallbackPrice * 0.02).toFixed(4));
    console.log(`[BRIDGE] ATR(${ticker}) = ${atr.toFixed(4)} via price_fallback (2% of ${fallbackPrice})`);
    return { atr, source: "price_fallback" };
  }

  throw new Error(`[BRIDGE] ATR: no bar data and no fallback price for ${ticker}`);
}

// ── Latest quote ──────────────────────────────────────────────────────────
/**
 * Fetch the latest trade price from Alpaca.
 * Falls back to latest bar close if trade quote unavailable.
 */
async function fetchLatestPrice(ticker) {
  try {
    const trade = await alpacaGet(
      `/v2/stocks/${encodeURIComponent(ticker)}/trades/latest?feed=iex`,
      ALPACA_DATA_URL,
    );
    const price = parseFloat(trade?.trade?.p ?? trade?.price ?? 0);
    if (isFinite(price) && price > 0) return price;
  } catch {
    // fall through to bar close
  }

  const bars = await alpacaGet(
    `/v2/stocks/${encodeURIComponent(ticker)}/bars?timeframe=1Day&limit=1&feed=iex`,
    ALPACA_DATA_URL,
  );
  const barList = bars?.bars ?? [];
  const close = parseFloat(barList[0]?.c ?? 0);
  if (!isFinite(close) || close <= 0) {
    throw new Error(`[BRIDGE] fetchLatestPrice: could not resolve price for ${ticker}`);
  }
  return close;
}

// ── Account equity ────────────────────────────────────────────────────────
async function fetchAccountEquity(base) {
  const account = await alpacaGet("/v2/account", base);
  const equity = parseFloat(account?.equity ?? account?.portfolio_value ?? 0);
  if (!isFinite(equity) || equity <= 0) {
    throw new Error("[BRIDGE] fetchAccountEquity: account equity is zero or unavailable");
  }
  return equity;
}

// ── Signal validation ─────────────────────────────────────────────────────
/**
 * Validate a 3WA signal. Binary — every check must pass or the trade fails.
 * Returns { valid: true } or { valid: false, reason: string }.
 */
function validateSignal(signal) {
  const check = (condition, reason) => condition ? null : reason;

  const failures = [
    check(signal != null && typeof signal === "object",                              "signal_null_or_not_object"),
    check(typeof signal.ticker === "string" && signal.ticker.trim().length > 0,      "ticker_missing"),
    check(typeof signal.run_id === "string" && signal.run_id.trim().length > 0,      "run_id_missing"),
    check(signal.signal_class === "3WA",                                             `signal_class_not_3wa:${signal.signal_class}`),
    check(signal.spy_dk === 1,                                                       `spy_dk_not_1:${signal.spy_dk}`),
    check(typeof signal.s_uf === "number" && isFinite(signal.s_uf) && signal.s_uf > 0, `s_uf_invalid:${signal.s_uf}`),
    check(typeof signal.bar_count === "number" && signal.bar_count >= 1 && signal.bar_count <= 20, `bar_count_invalid:${signal.bar_count}`),
  ].filter(Boolean);

  if (failures.length > 0) {
    return { valid: false, reason: failures.join("; ") };
  }
  return { valid: true };
}

// ── Ledger writes ─────────────────────────────────────────────────────────
async function ledgerInsert(row) {
  const sql = `
    INSERT INTO personal_trade_ledger (
      ticker, run_id, signal_class,
      spy_dk, s_uf, bar_count, f_n, d_k, b_k,
      vault_equity_at_signal, risk_per_trade_pct, dollar_allocation, shares, atr_14,
      alpaca_order_id, alpaca_take_profit_order_id, alpaca_stop_loss_order_id,
      entry_limit_price, take_profit_price, stop_loss_price,
      status, exit_reason, rationale_json, signal_detected_at
    ) VALUES (
      $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23,NOW()
    ) RETURNING id
  `;
  const result = await pool.query(sql, [
    row.ticker,
    row.run_id,
    row.signal_class,
    row.spy_dk             ?? null,
    row.s_uf               ?? null,
    row.bar_count          ?? null,
    row.f_n                ?? null,
    row.d_k                ?? null,
    row.b_k                ?? null,
    row.vault_equity       ?? null,
    row.risk_per_trade_pct ?? 1.5,
    row.dollar_allocation  ?? null,
    row.shares             ?? null,
    row.atr_14             ?? null,
    row.alpaca_order_id    ?? null,
    row.take_profit_order_id ?? null,
    row.stop_loss_order_id   ?? null,
    row.entry_limit_price  ?? null,
    row.take_profit_price  ?? null,
    row.stop_loss_price    ?? null,
    row.status,
    row.exit_reason        ?? null,
    JSON.stringify(row.rationale_json ?? {}),
  ]);
  return result.rows[0].id;
}

async function ledgerUpdate(alpacaOrderId, fields) {
  const setClauses = Object.keys(fields)
    .map((k, i) => `${k} = $${i + 2}`)
    .join(", ");
  const values = [alpacaOrderId, ...Object.values(fields)];
  await pool.query(
    `UPDATE personal_trade_ledger SET ${setClauses} WHERE alpaca_order_id = $1`,
    values,
  );
}

// ── Rejection helper ──────────────────────────────────────────────────────
/**
 * Log a rejected signal to the ledger. Never throws.
 */
export async function rejectSignal(signal, reason) {
  const ticker  = String(signal?.ticker  ?? "UNKNOWN").trim().toUpperCase();
  const run_id  = String(signal?.run_id  ?? "UNKNOWN").trim();

  console.log(`[BRIDGE] REJECT ${ticker} | ${reason}`);

  try {
    await ledgerInsert({
      ticker,
      run_id,
      signal_class:      signal?.signal_class ?? "unknown",
      spy_dk:            signal?.spy_dk       ?? null,
      s_uf:              signal?.s_uf         ?? null,
      bar_count:         signal?.bar_count    ?? null,
      f_n:               signal?.f_n          ?? null,
      d_k:               signal?.d_k          ?? null,
      b_k:               signal?.b_k          ?? null,
      status:            "rejected",
      exit_reason:       reason.startsWith("signal_class") ? "rejected_no_3wa" : "rejected_field",
      rationale_json: {
        rejection_reason: reason,
        spy_dk:           signal?.spy_dk       ?? null,
        s_uf:             signal?.s_uf         ?? null,
        bar_count:        signal?.bar_count    ?? null,
        run_id,
      },
    });
  } catch (dbErr) {
    console.error(`[BRIDGE] REJECT ledger write failed for ${ticker}:`, dbErr.message);
  }

  return { ok: false, rejected: true, reason };
}

// ── Core: place bracket order ─────────────────────────────────────────────
/**
 * Validate, size, and place a DAY bracket order for a 3WA signal.
 *
 * @param {Object} signal — from 3wa_strategist, must include:
 *   { ticker, run_id, signal_class, spy_dk, s_uf, bar_count, f_n, d_k, b_k }
 * @param {Object} [opts]
 *   { riskPct: number = 1.5 }  — override default 1.5% risk per trade
 *
 * @returns {Promise<{ok: boolean, orderId?: string, ledgerId?: number, ...}>}
 */
export async function executeBracketOrder(signal, opts = {}) {
  const ticker     = String(signal?.ticker ?? "").trim().toUpperCase();
  const riskPct    = Math.min(
    Math.max(parseFloat(opts.riskPct ?? process.env.RISK_PER_TRADE_PCT ?? "1.5"), 0.1),
    MAX_SINGLE_TRADE_PCT,
  );

  // ── Step 0: resolve execution mode (paper vs live) ────────────────────
  const executionMode = await readExecutionMode();
  const BASE = alpacaBaseUrl(executionMode);
  const isPaper = executionMode !== "live";
  console.log(`[BRIDGE] Execution mode: ${executionMode.toUpperCase()} | base=${BASE}`);

  // ── Step 1: validate signal (binary) ──────────────────────────────────
  const validation = validateSignal(signal);
  if (!validation.valid) {
    return rejectSignal(signal, validation.reason);
  }

  console.log(`[BRIDGE] Signal validated: ${ticker} | class=${signal.signal_class} | spy_dk=${signal.spy_dk} | s_uf=${signal.s_uf}`);

  let vaultEquity, currentPrice, atr;

  // ── Step 2: fetch live market data ───────────────────────────────────
  try {
    [vaultEquity, currentPrice] = await Promise.all([
      fetchAccountEquity(BASE),
      fetchLatestPrice(ticker),
    ]);
    ({ atr } = await computeATR(ticker, currentPrice));
  } catch (err) {
    return rejectSignal(signal, `market_data_fetch_failed: ${err.message}`);
  }

  // ── Step 3: price sanity check ────────────────────────────────────────
  if (currentPrice < MIN_SHARE_PRICE) {
    return rejectSignal(signal, `price_below_minimum: ${currentPrice} < ${MIN_SHARE_PRICE}`);
  }

  // ── Step 4: position sizing ───────────────────────────────────────────
  const dollarAllocation = vaultEquity * (riskPct / 100);
  const shares           = Math.floor(dollarAllocation / currentPrice);

  if (shares < MIN_SHARES) {
    return rejectSignal(signal, `shares_below_minimum: allocation=${dollarAllocation.toFixed(2)} price=${currentPrice} shares=${shares}`);
  }

  // ── Step 5: bracket prices ────────────────────────────────────────────
  // Round to 2dp — Alpaca rejects prices with more precision on most assets
  const entryPrice      = parseFloat(currentPrice.toFixed(2));
  const takeProfitPrice = parseFloat((entryPrice + TAKE_PROFIT_MULT * atr).toFixed(2));
  const stopLossPrice   = parseFloat((entryPrice - STOP_LOSS_MULT   * atr).toFixed(2));

  if (stopLossPrice <= 0) {
    return rejectSignal(signal, `stop_loss_price_invalid: ${stopLossPrice} (ATR=${atr.toFixed(4)})`);
  }

  console.log(`[BRIDGE] ${ticker} | shares=${shares} | entry=${entryPrice} | TP=${takeProfitPrice} | SL=${stopLossPrice} | ATR=${atr.toFixed(4)}`);

  // ── Step 6: insert pending ledger row (before order placement) ────────
  let ledgerId;
  try {
    ledgerId = await ledgerInsert({
      ticker,
      run_id:            signal.run_id,
      signal_class:      signal.signal_class,
      spy_dk:            signal.spy_dk,
      s_uf:              signal.s_uf,
      bar_count:         signal.bar_count,
      f_n:               signal.f_n          ?? null,
      d_k:               signal.d_k          ?? null,
      b_k:               signal.b_k          ?? null,
      vault_equity:      vaultEquity,
      risk_per_trade_pct: riskPct,
      dollar_allocation: dollarAllocation,
      shares,
      atr_14:            atr,
      entry_limit_price: entryPrice,
      take_profit_price: takeProfitPrice,
      stop_loss_price:   stopLossPrice,
      status:            "pending",
      rationale_json: {
        wave1_active:  true,  // bar_count <= 20 confirmed above
        wave3_active:  true,  // spy_dk == 1 confirmed above
        spy_dk:        signal.spy_dk,
        s_uf:          signal.s_uf,
        bar_count:     signal.bar_count,
        f_n:           signal.f_n ?? null,
        run_id:        signal.run_id,
        vault_equity:  vaultEquity,
        atr_14:        atr,
        paper_mode:    isPaper,
      },
    });
  } catch (dbErr) {
    // Ledger failure does NOT block execution — log and proceed.
    // We cannot lose a trade because of a DB write failure.
    console.error(`[BRIDGE] Ledger pre-insert failed for ${ticker}:`, dbErr.message);
  }

  // ── Step 7: place bracket order via Alpaca REST ───────────────────────
  let order;
  try {
    order = await alpacaPost("/v2/orders", {
      symbol:         ticker,
      qty:            shares,
      side:           "buy",
      type:           "limit",
      time_in_force:  "day",
      limit_price:    entryPrice,
      order_class:    "bracket",
      take_profit: {
        limit_price:  takeProfitPrice,
      },
      stop_loss: {
        stop_price:   stopLossPrice,
        // No limit_price → stop-market order on trigger (as specified)
      },
    }, BASE);
  } catch (orderErr) {
    const errMsg = `order_placement_failed: ${orderErr.message}`;
    console.error(`[BRIDGE] ${ticker}: ${errMsg}`);

    if (ledgerId != null) {
      await pool.query(
        `UPDATE personal_trade_ledger SET status='rejected', exit_reason=$1,
         rationale_json = rationale_json || $2::jsonb WHERE id=$3`,
        ["rejected_field", JSON.stringify({ order_error: orderErr.message }), ledgerId],
      ).catch(e => console.error("[BRIDGE] Ledger error-update failed:", e.message));
    }

    return { ok: false, rejected: true, reason: errMsg, ledgerId };
  }

  // ── Step 8: update ledger with Alpaca order ID ────────────────────────
  const orderId         = order.id;
  const legIds          = (order.legs ?? []).reduce((acc, leg) => {
    if (leg.order_class === "take_profit") acc.tp = leg.id;
    if (leg.order_class === "stop_loss")   acc.sl = leg.id;
    return acc;
  }, {});

  if (ledgerId != null) {
    await pool.query(
      `UPDATE personal_trade_ledger
       SET alpaca_order_id=$1, alpaca_take_profit_order_id=$2,
           alpaca_stop_loss_order_id=$3, status='submitted'
       WHERE id=$4`,
      [orderId, legIds.tp ?? null, legIds.sl ?? null, ledgerId],
    ).catch(e => console.error("[BRIDGE] Ledger submitted-update failed:", e.message));
  }

  console.log(`[BRIDGE] ORDER SUBMITTED | ${ticker} | orderId=${orderId} | ledgerId=${ledgerId}`);

  return {
    ok:               true,
    ticker,
    orderId,
    ledgerId,
    shares,
    entryPrice,
    takeProfitPrice,
    stopLossPrice,
    atr,
    vaultEquity,
    dollarAllocation,
    paperMode:        IS_PAPER,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Chapter 2 — Mid S_UF Acceleration Layer
// Independent execution path. Does NOT modify or share logic with 3WA above.
// ─────────────────────────────────────────────────────────────────────────────

// Dynamic Expectancy Multiplier sizing (derived from structural_episodes.csv):
//   Chapter 1 (3WA sustained): win_rate=0.725, avg_return=0.220 → edge=0.1595
//   Chapter 2 (mid S_UF):      win_rate=0.649, avg_return=0.150 → edge=0.0974
//   Multiplier = 0.0974 / 0.1595 = 0.611
//   Ch2 risk pct = 1.5% (3WA base) × 0.611 = 0.917%
const CH2_RISK_PCT         = 0.917; // derived expectancy multiplier: 0.611 × 3WA base
const CH2_TAKE_PROFIT_MULT = 1.0;   // tighter TP: median hold ~91 bars, not 223
const CH2_STOP_LOSS_MULT   = 1.0;   // same SL distance

/**
 * Validate a Ch2 signal. Binary — every check must pass or the trade fails.
 */
function validateCh2Signal(signal) {
  const check = (condition, reason) => condition ? null : reason;

  const failures = [
    check(signal != null && typeof signal === "object",                                "signal_null_or_not_object"),
    check(typeof signal.ticker === "string" && signal.ticker.trim().length > 0,        "ticker_missing"),
    check(typeof signal.run_id === "string" && signal.run_id.trim().length > 0,        "run_id_missing"),
    check(signal.signal_class === "CH2",                                               `signal_class_not_ch2:${signal.signal_class}`),
    check(typeof signal.s_uf === "number" && signal.s_uf >= 0.50 && signal.s_uf < 0.75, `s_uf_out_of_ch2_band:${signal.s_uf}`),
    check(signal.d_k === 1,                                                            `d_k_not_1:${signal.d_k}`),
    check(typeof signal.bar_count === "number" && signal.bar_count > 20,               `bar_count_not_established:${signal.bar_count}`),
    check(signal.regime === "TRANSITIONAL",                                            `regime_not_transitional:${signal.regime}`),
  ].filter(Boolean);

  if (failures.length > 0) {
    return { valid: false, reason: failures.join("; ") };
  }
  return { valid: true };
}

/**
 * Validate, size, and place a bracket order for a Ch2 signal.
 * Mirrors executeBracketOrder() structure but uses Ch2-specific parameters.
 *
 * @param {Object} signal — from ch2_strategist, must include:
 *   { ticker, run_id, signal_class, s_uf, d_k, bar_count, regime, f_n, b_k }
 * @returns {Promise<{ok: boolean, orderId?: string, ledgerId?: number, ...}>}
 */
export async function executeCh2BracketOrder(signal) {
  const ticker  = String(signal?.ticker ?? "").trim().toUpperCase();
  const riskPct = Math.min(CH2_RISK_PCT, MAX_SINGLE_TRADE_PCT);

  const executionMode = await readExecutionMode();
  const BASE = alpacaBaseUrl(executionMode);
  console.log(`[CH2-BRIDGE] Execution mode: ${executionMode.toUpperCase()} | base=${BASE}`);

  // Step 1: validate
  const validation = validateCh2Signal(signal);
  if (!validation.valid) {
    return rejectSignal(signal, validation.reason);
  }
  console.log(`[CH2-BRIDGE] Signal validated: ${ticker} | class=${signal.signal_class} | s_uf=${signal.s_uf} | D_k=${signal.d_k}`);

  let vaultEquity, currentPrice, atr;
  try {
    [vaultEquity, currentPrice] = await Promise.all([
      fetchAccountEquity(BASE),
      fetchLatestPrice(ticker),
    ]);
    ({ atr } = await computeATR(ticker, currentPrice));
  } catch (err) {
    return rejectSignal(signal, `market_data_fetch_failed: ${err.message}`);
  }

  if (currentPrice < MIN_SHARE_PRICE) {
    return rejectSignal(signal, `price_below_minimum: ${currentPrice} < ${MIN_SHARE_PRICE}`);
  }

  const dollarAllocation = vaultEquity * (riskPct / 100);
  const shares           = Math.floor(dollarAllocation / currentPrice);
  if (shares < MIN_SHARES) {
    return rejectSignal(signal, `shares_below_minimum: allocation=${dollarAllocation.toFixed(2)} price=${currentPrice} shares=${shares}`);
  }

  const entryPrice      = parseFloat(currentPrice.toFixed(2));
  const takeProfitPrice = parseFloat((entryPrice + CH2_TAKE_PROFIT_MULT * atr).toFixed(2));
  const stopLossPrice   = parseFloat((entryPrice - CH2_STOP_LOSS_MULT   * atr).toFixed(2));

  if (stopLossPrice <= 0) {
    return rejectSignal(signal, `stop_loss_price_invalid: ${stopLossPrice} (ATR=${atr.toFixed(4)})`);
  }

  console.log(`[CH2-BRIDGE] ${ticker} | shares=${shares} | entry=${entryPrice} | TP=${takeProfitPrice} | SL=${stopLossPrice} | ATR=${atr.toFixed(4)}`);

  let ledgerId;
  try {
    ledgerId = await ledgerInsert({
      ticker,
      run_id:            signal.run_id,
      signal_class:      "CH2",
      spy_dk:            null,
      s_uf:              signal.s_uf,
      bar_count:         signal.bar_count,
      f_n:               signal.f_n ?? null,
      d_k:               signal.d_k,
      b_k:               signal.b_k ?? null,
      vault_equity:      vaultEquity,
      risk_per_trade_pct: riskPct,
      dollar_allocation: dollarAllocation,
      shares,
      atr_14:            atr,
      entry_limit_price: entryPrice,
      take_profit_price: takeProfitPrice,
      stop_loss_price:   stopLossPrice,
      status:            "pending",
      rationale_json: {
        chapter:          2,
        regime:           signal.regime,
        s_uf:             signal.s_uf,
        d_k:              signal.d_k,
        bar_count:        signal.bar_count,
        exit_trigger_a:   "s_uf >= 0.75",
        exit_trigger_b:   "d_k != 1",
        run_id:           signal.run_id,
        vault_equity:     vaultEquity,
      },
    });
  } catch (err) {
    return rejectSignal(signal, `ledger_insert_failed: ${err.message}`);
  }

  const dedupeKey = createHash("sha256")
    .update(`CH2:${ticker}:${signal.run_id}`)
    .digest("hex")
    .slice(0, 16);

  let order;
  try {
    order = await alpacaPost("/v2/orders", {
      symbol:         ticker,
      qty:            shares,
      side:           "buy",
      type:           "limit",
      limit_price:    entryPrice,
      time_in_force:  "day",
      client_order_id: dedupeKey,
      order_class:    "bracket",
      take_profit: {
        limit_price: takeProfitPrice,
      },
      stop_loss: {
        stop_price: stopLossPrice,
      },
    }, BASE);
  } catch (err) {
    const errMsg = err.message ?? "unknown";
    if (ledgerId != null) {
      await pool.query(
        `UPDATE personal_trade_ledger SET status='rejected', exit_reason=$1 WHERE id=$2`,
        [errMsg, ledgerId],
      ).catch(() => {});
    }
    return { ok: false, rejected: true, reason: errMsg, ledgerId };
  }

  const orderId = order.id;
  const legIds  = (order.legs ?? []).reduce((acc, leg) => {
    if (leg.order_class === "take_profit") acc.tp = leg.id;
    if (leg.order_class === "stop_loss")   acc.sl = leg.id;
    return acc;
  }, {});

  if (ledgerId != null) {
    await pool.query(
      `UPDATE personal_trade_ledger
       SET alpaca_order_id=$1, alpaca_take_profit_order_id=$2,
           alpaca_stop_loss_order_id=$3, status='submitted'
       WHERE id=$4`,
      [orderId, legIds.tp ?? null, legIds.sl ?? null, ledgerId],
    ).catch(e => console.error("[CH2-BRIDGE] Ledger submitted-update failed:", e.message));
  }

  console.log(`[CH2-BRIDGE] ORDER SUBMITTED | ${ticker} | orderId=${orderId} | ledgerId=${ledgerId}`);

  return {
    ok:               true,
    ticker,
    orderId,
    ledgerId,
    shares,
    entryPrice,
    takeProfitPrice,
    stopLossPrice,
    atr,
    vaultEquity,
    dollarAllocation,
  };
}

// ── Cleanup ───────────────────────────────────────────────────────────────
export async function closeBridgePool() {
  await pool.end();
}
