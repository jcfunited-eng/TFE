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
import { computeSizing, checkEpochGovernance } from "../l5_unified_shadow.mjs";

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

// CH3 entry slippage cap. A market entry into a fast mover fills above the
// submit-time quote while the brackets stay anchored to it — 2026-07-16 AMAL
// filled +1.27% over quote, compressing the +1.5% take-profit to +0.23%
// against a -2.24% effective stop. Entry is therefore a marketable limit at
// quote×(1+cap), and brackets anchor to that worst-case fill so the designed
// TP/SL distances survive any fill the order can legally receive.
const CH3_ENTRY_SLIPPAGE_CAP = 0.003;

export function computeCh3EntryPrices(quote, tpPct, slPct) {
  const limitPrice      = parseFloat((quote * (1 + CH3_ENTRY_SLIPPAGE_CAP)).toFixed(2));
  const takeProfitPrice = parseFloat((limitPrice * (1 + tpPct)).toFixed(2));
  const stopLossPrice   = parseFloat((limitPrice * (1 - slPct)).toFixed(2));
  return { limitPrice, takeProfitPrice, stopLossPrice };
}

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
 * @returns {Promise<{ atr: number, source: string, bars: Array }>}
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
          return { atr, source: feed, bars: barList };
        }
      }
    } catch { /* try next feed */ }
  }

  // Fallback: 2% of price — reasonable bracket for any liquid stock
  if (fallbackPrice && fallbackPrice > 0) {
    const atr = parseFloat((fallbackPrice * 0.02).toFixed(4));
    console.log(`[BRIDGE] ATR(${ticker}) = ${atr.toFixed(4)} via price_fallback (2% of ${fallbackPrice})`);
    return { atr, source: "price_fallback", bars: [] };
  }

  throw new Error(`[BRIDGE] ATR: no bar data and no fallback price for ${ticker}`);
}

// ── Red-day filter: reject entries on stocks falling 2+ consecutive days ──
// If the last 2 daily closes are both lower than the prior day's close,
// the stock is in active decline — don't buy into a falling knife.
// Backtest on 28 positions: 90% precision (9/10 blocks correct, 1 winner missed).
function checkRedDayFilter(ticker, bars) {
  if (!Array.isArray(bars) || bars.length < 3) return { blocked: false, reason: "insufficient_bars" };

  const recent = bars.slice(-3); // last 3 bars
  const close0 = parseFloat(recent[0].c); // 3 days ago
  const close1 = parseFloat(recent[1].c); // 2 days ago
  const close2 = parseFloat(recent[2].c); // yesterday

  const decline1 = close1 < close0; // day before yesterday closed lower
  const decline2 = close2 < close1; // yesterday closed lower

  if (decline1 && decline2) {
    console.log(
      `[BRIDGE] RED-DAY BLOCK ${ticker} | ` +
      `${recent[0].t?.slice(0,10)} C=${close0} → ${recent[1].t?.slice(0,10)} C=${close1} → ${recent[2].t?.slice(0,10)} C=${close2} | ` +
      `2 consecutive declining closes — skipping entry`
    );
    return { blocked: true, reason: `red_day_filter: 2 consecutive declines (${close0}→${close1}→${close2})` };
  }

  return { blocked: false };
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
async function fetchAccountState(base) {
  const account = await alpacaGet("/v2/account", base);
  const equity = parseFloat(account?.equity ?? account?.portfolio_value ?? 0);
  const cash = parseFloat(account?.cash ?? 0);
  if (!isFinite(equity) || equity <= 0) {
    throw new Error("[BRIDGE] fetchAccountState: account equity is zero or unavailable");
  }
  return { equity, cash };
}

// Backward-compatible wrapper (used by callers that only need equity)
async function fetchAccountEquity(base) {
  const { equity } = await fetchAccountState(base);
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

// ── Robust order-ID ledger write (Gap 1 fix) ─────────────────────────────
// The primary UPDATE writes alpaca_order_id to the column. If the DB write
// fails (connection drop, lock timeout), retries up to 2× with 500ms backoff.
// If all retries fail, the order IDs are persisted to rationale_json so the
// zombie check and trade_auditor can recover them via the fallback path.
// If BOTH the column update and the rationale fallback fail, logs at ERROR
// level with full order IDs so the row is manually recoverable from logs.
async function writeOrderIdsToLedger(ledgerId, ticker, orderId, tpId, slId, logPrefix) {
  const primary = async () => pool.query(
    `UPDATE personal_trade_ledger
       SET alpaca_order_id=$1, alpaca_take_profit_order_id=$2,
           alpaca_stop_loss_order_id=$3, status='submitted'
     WHERE id=$4`,
    [orderId, tpId ?? null, slId ?? null, ledgerId],
  );

  // Try primary — up to 3 attempts with 500ms backoff
  let lastErr;
  for (let attempt = 1; attempt <= 3; attempt++) {
    try {
      await primary();
      return; // success
    } catch (e) {
      lastErr = e;
      if (attempt < 3) await new Promise(r => setTimeout(r, 500));
    }
  }

  // Primary failed — write fallback into rationale_json
  console.error(`[${logPrefix}] PRIMARY order-ID write failed after 3 attempts for ${ticker} ledgerId=${ledgerId}: ${lastErr.message}. Writing fallback to rationale_json.`);
  try {
    await pool.query(
      `UPDATE personal_trade_ledger
         SET rationale_json = rationale_json || jsonb_build_object(
               'fallback_alpaca_order_id',    $1::text,
               'fallback_alpaca_tp_order_id', $2::text,
               'fallback_alpaca_sl_order_id', $3::text,
               'fallback_write_reason',       'primary_column_update_failed',
               'fallback_write_at',           to_char(now() at time zone 'utc',
                                                'YYYY-MM-DD"T"HH24:MI:SS"Z"')
             )
       WHERE id=$4`,
      [orderId, tpId ?? null, slId ?? null, ledgerId],
    );
    console.error(`[${logPrefix}] Fallback order IDs written to rationale_json for ${ticker} ledgerId=${ledgerId} orderId=${orderId}`);
  } catch (fbErr) {
    // Both paths failed — log everything so the row is manually recoverable
    console.error(
      `[${logPrefix}] CRITICAL: both primary and fallback order-ID writes failed for ` +
      `${ticker} ledgerId=${ledgerId} orderId=${orderId} tpId=${tpId ?? "null"} slId=${slId ?? "null"} ` +
      `primary_err=${lastErr.message} fallback_err=${fbErr.message}`
    );
  }
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

  let vaultEquity, vaultCash, currentPrice, atr, bars;

  // ── Step 2: fetch live market data ───────────────────────────────────
  try {
    [{ equity: vaultEquity, cash: vaultCash }, currentPrice] = await Promise.all([
      fetchAccountState(BASE),
      fetchLatestPrice(ticker),
    ]);
    ({ atr, bars } = await computeATR(ticker, currentPrice));
  } catch (err) {
    return rejectSignal(signal, `market_data_fetch_failed: ${err.message}`);
  }

  // ── Step 2b: red-day filter — don't buy falling knives ────────────────
  const redDay = checkRedDayFilter(ticker, bars);
  if (redDay.blocked) {
    return rejectSignal(signal, redDay.reason);
  }

  // ── Step 3: price sanity check ────────────────────────────────────────
  if (currentPrice < MIN_SHARE_PRICE) {
    return rejectSignal(signal, `price_below_minimum: ${currentPrice} < ${MIN_SHARE_PRICE}`);
  }

  // ── Step 4: position sizing (L5 computeSizing) ────────────────────────
  const entryLayer = signal.signal_class === "3WA" ? "3WA"
                   : signal.signal_class === "1+3" ? "1+3" : "TP";
  const confidence = signal.signal_class === "3WA" ? "HIGH" : "MEDIUM";
  const signalWR = signal.neighbor_wr ?? null;
  const epochState = checkEpochGovernance(signal.sector ?? "Unknown");
  const l5Sizing = computeSizing(entryLayer, confidence, signalWR, epochState.phase);
  const effectiveRiskPct = l5Sizing.sizePct * 100;  // computeSizing returns fraction, bridge uses percentage
  console.log(`[BRIDGE] L5 sizing: ${l5Sizing.reason} → ${effectiveRiskPct.toFixed(2)}% | neighbor_wr=${signalWR?.toFixed(3) ?? "null"} (was fixed ${riskPct}%)`);

  const dollarAllocation = vaultEquity * (effectiveRiskPct / 100);
  const shares           = Math.floor(dollarAllocation / currentPrice);

  if (shares < MIN_SHARES) {
    return rejectSignal(signal, `shares_below_minimum: allocation=${dollarAllocation.toFixed(2)} price=${currentPrice} shares=${shares}`);
  }

  // ── Step 4b: cash ceiling — position cost must not exceed available cash ──
  const positionCost = shares * currentPrice;
  if (positionCost > vaultCash) {
    return rejectSignal(signal, `insufficient_cash: cost=$${positionCost.toFixed(2)} cash=$${vaultCash.toFixed(2)} (equity=$${vaultEquity.toFixed(2)})`);
  }

  // ── Step 5: bracket prices ────────────────────────────────────────────
  // Kinetic buffer: 0.1% above current price to catch accelerating entries.
  // 0.99x discount tested May 19 — killed 4/12 fills (33% loss rate).
  // Fill volume matters more than entry price at $2,500 sizing.
  // Reverted to 1.001x. Solve peak-entry problem differently (intraday timing).
  const KINETIC_BUFFER = 1.001;
  const entryPrice      = parseFloat((currentPrice * KINETIC_BUFFER).toFixed(2));
  const takeProfitPrice = parseFloat((entryPrice + TAKE_PROFIT_MULT * atr).toFixed(2));
  // 1×ATR bracket SL restored — April's validated exit width (-1.7% avg).
  // May 19 commit 03352c2 changed to -10% based on a memory-file observation
  // (not a repo artifact). Destruction registry: "survivorship reframing."
  const stopLossPrice   = parseFloat((entryPrice - STOP_LOSS_MULT * atr).toFixed(2));

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
      risk_per_trade_pct: effectiveRiskPct,
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
    await writeOrderIdsToLedger(ledgerId, ticker, orderId, legIds.tp, legIds.sl, "BRIDGE");
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
    paperMode:        isPaper,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Chapter 2 — Mid S_UF Acceleration Layer
// Independent execution path. Does NOT modify or share logic with 3WA above.
// ─────────────────────────────────────────────────────────────────────────────

// Position sizing: 2.5% risk per trade.
// Backtest (85 trades): win/loss ratio 1.91:1. At 2.5% same trades produce
// $4,413 P&L vs $1,633 at 0.917%. Utilization ~60% vs ~23%.
const CH2_RISK_PCT         = 2.5;
// Brackets are disaster backstops only — spec exit is EXIT-B (ticker D_k collapse).
// 1×ATR SL fires on normal daily noise and kills valid positions before the
// basin can release. 3×ATR gives the position room to breathe through intraday
// volatility while still catching real structural failures.
// TP bracket removed — sentinel EXIT-B handles upside when the wave releases.
const CH2_STOP_LOSS_MULT   = 3.0;   // 3×ATR — backstop only, not primary exit
const CH2_MIN_SL_PCT       = 0.05;  // minimum 5% stop regardless of ATR

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
    // D_k gate REMOVED — kernel's Accumulate decision is the filter. D_k stays as EXIT-B.
    check(typeof signal.bar_count === "number" && signal.bar_count > 20,               `bar_count_not_established:${signal.bar_count}`),
    // Regime check REMOVED — validation finding: TRANSITIONAL-only was too restrictive
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

  let vaultEquity, vaultCash, currentPrice, atr, bars;
  try {
    [{ equity: vaultEquity, cash: vaultCash }, currentPrice] = await Promise.all([
      fetchAccountState(BASE),
      fetchLatestPrice(ticker),
    ]);
    ({ atr, bars } = await computeATR(ticker, currentPrice));
  } catch (err) {
    return rejectSignal(signal, `market_data_fetch_failed: ${err.message}`);
  }

  // Red-day filter — don't buy falling knives
  const redDay = checkRedDayFilter(ticker, bars);
  if (redDay.blocked) {
    return rejectSignal(signal, redDay.reason);
  }

  if (currentPrice < MIN_SHARE_PRICE) {
    return rejectSignal(signal, `price_below_minimum: ${currentPrice} < ${MIN_SHARE_PRICE}`);
  }

  // Fixed 2.5% sizing — V3 basin is the selection gate; graduated WR sizer is
  // redundant here and was silently halving allocation (null neighbor_wr → TP_MED
  // 1.5% → UPHEAVAL halved → 0.75%). Use CH2_RISK_PCT directly.
  console.log(`[CH2-BRIDGE] Sizing: fixed ${riskPct}% (CH2_RISK_PCT)`);

  const dollarAllocation = vaultEquity * (riskPct / 100);
  const shares           = Math.floor(dollarAllocation / currentPrice);
  if (shares < MIN_SHARES) {
    return rejectSignal(signal, `shares_below_minimum: allocation=${dollarAllocation.toFixed(2)} price=${currentPrice} shares=${shares}`);
  }

  // Cash ceiling — position cost must not exceed available cash
  const ch2PositionCost = shares * currentPrice;
  if (ch2PositionCost > vaultCash) {
    return rejectSignal(signal, `insufficient_cash: cost=$${ch2PositionCost.toFixed(2)} cash=$${vaultCash.toFixed(2)} (equity=$${vaultEquity.toFixed(2)})`);
  }

  // Kinetic buffer: 0.1% above current price to catch accelerating entries.
  // 0.99x discount tested May 19 — killed 4/12 fills. Reverted.
  const KINETIC_BUFFER = 1.001;
  const entryPrice     = parseFloat((currentPrice * KINETIC_BUFFER).toFixed(2));
  // SL: 3×ATR below entry, minimum 5% — backstop only. Primary exit is EXIT-B (D_k collapse).
  const atrSlDistance  = CH2_STOP_LOSS_MULT * atr;
  const minSlDistance  = entryPrice * CH2_MIN_SL_PCT;
  const stopLossPrice  = parseFloat((entryPrice - Math.max(atrSlDistance, minSlDistance)).toFixed(2));
  // No TP bracket — let winners ride to EXIT-B.
  const takeProfitPrice = null;

  if (stopLossPrice <= 0) {
    return rejectSignal(signal, `stop_loss_price_invalid: ${stopLossPrice} (ATR=${atr.toFixed(4)})`);
  }

  console.log(`[CH2-BRIDGE] ${ticker} | shares=${shares} | entry=${entryPrice} | SL=${stopLossPrice} (3xATR=${(atrSlDistance).toFixed(2)} min5%=${(minSlDistance).toFixed(2)}) | no TP`);

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
        // The WHY of the trade, permanently: entry-time coupled read.
        // Pass logs age out in ~7 days; without this, outcomes have no
        // recorded cause and edge attribution is impossible (the UTZ
        // unicorn forensics had to reconstruct these from history tables).
        v3_basin:         signal.v3_basin ?? null,
        epoch_pressure:   signal.epoch_pressure ?? null,
      },
    });
  } catch (err) {
    return rejectSignal(signal, `ledger_insert_failed: ${err.message}`);
  }

  // Unique order ID per attempt. The old sha256(CH2:ticker:run_id) was constant
  // across the entire refresh cycle, so re-evaluations within the same run_id
  // all got the same client_order_id → Alpaca rejected 186 orders as duplicates.
  // Use timestamp + random to ensure uniqueness per attempt. Duplicate-entry
  // prevention is handled by the open-position check in the strategist, not
  // by Alpaca's client_order_id.
  const dedupeKey = createHash("sha256")
    .update(`CH2:${ticker}:${signal.run_id}:${Date.now()}:${Math.random()}`)
    .digest("hex")
    .slice(0, 16);

  let order;
  try {
    // oto (one-triggers-other) with stop-loss only — no TP bracket.
    // Primary exit is sentinel EXIT-B (ticker D_k collapse).
    order = await alpacaPost("/v2/orders", {
      symbol:          ticker,
      qty:             shares,
      side:            "buy",
      type:            "limit",
      limit_price:     entryPrice,
      time_in_force:   "day",
      client_order_id: dedupeKey,
      order_class:     "oto",
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
    await writeOrderIdsToLedger(ledgerId, ticker, orderId, legIds.tp, legIds.sl, "CH2-BRIDGE");
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

// ── Chapter 3 — Scalp "Smash and Grab" market buy ─────────────────────────
/**
 * CH3 uses a MARKET BUY (not bracket) — exits are managed by sentinel.
 * Fixed dollar amount per trade, not percentage of equity.
 */
export async function executeCh3MarketOrder(signal) {
  const ticker      = String(signal?.ticker ?? "").trim().toUpperCase();
  const tradeAmount = signal.ch3_trade_amount ?? 2500;

  const executionMode = await readExecutionMode();
  const BASE = alpacaBaseUrl(executionMode);
  console.log(`[CH3-BRIDGE] Execution mode: ${executionMode.toUpperCase()} | base=${BASE}`);

  if (!ticker || signal.signal_class !== "CH3") {
    return rejectSignal(signal, "invalid_ch3_signal");
  }

  let currentPrice, atr, ch3Cash;
  try {
    [{ cash: ch3Cash }, currentPrice] = await Promise.all([
      fetchAccountState(BASE),
      fetchLatestPrice(ticker),
    ]);
  } catch (err) {
    return rejectSignal(signal, `market_data_fetch_failed: ${err.message}`);
  }

  if (currentPrice < MIN_SHARE_PRICE) {
    return rejectSignal(signal, `price_below_minimum: ${currentPrice} < ${MIN_SHARE_PRICE}`);
  }

  // Compute ATR for price-scaled stops
  try {
    ({ atr } = await computeATR(ticker, currentPrice));
  } catch (err) {
    return rejectSignal(signal, `atr_fetch_failed: ${err.message}`);
  }

  const entryQuote = parseFloat(currentPrice.toFixed(2));
  // Percentage-based exits from structural register forensics:
  //   Stop: -5% hard stop (profit factor 3.81 across 1832 trades)
  //   TP: +50% wide ceiling (sentinel manages trailing)
  const slPct = signal.ch3_stop_loss_pct ?? 0.05;
  const tpPct = signal.ch3_take_profit_pct ?? 0.50;
  const { limitPrice, takeProfitPrice, stopLossPrice } = computeCh3EntryPrices(entryQuote, tpPct, slPct);

  // Shares and cash ceiling sized against the worst-case fill (the limit)
  const shares = Math.floor(tradeAmount / limitPrice);
  if (shares < MIN_SHARES) {
    return rejectSignal(signal, `shares_below_minimum: amount=${tradeAmount} price=${limitPrice} shares=${shares}`);
  }

  const ch3PositionCost = shares * limitPrice;
  if (ch3PositionCost > ch3Cash) {
    return rejectSignal(signal, `insufficient_cash: cost=$${ch3PositionCost.toFixed(2)} cash=$${ch3Cash.toFixed(2)}`);
  }

  if (stopLossPrice <= 0) {
    return rejectSignal(signal, `stop_loss_price_invalid: ${stopLossPrice} (ATR=${atr.toFixed(4)})`);
  }

  console.log(`[CH3-BRIDGE] ${ticker} | shares=${shares} | quote=${entryQuote} limit=${limitPrice} | TP=${takeProfitPrice} | SL=${stopLossPrice} | ATR=${atr.toFixed(4)} | amount=$${tradeAmount}`);

  let ledgerId;
  try {
    ledgerId = await ledgerInsert({
      ticker,
      run_id:            signal.run_id,
      signal_class:      "CH3",
      spy_dk:            null,
      s_uf:              signal.s_uf,
      bar_count:         signal.bar_count,
      f_n:               null,
      d_k:               signal.d_k,
      b_k:               null,
      vault_equity:      tradeAmount,
      risk_per_trade_pct: (tradeAmount / 100000) * 100,
      dollar_allocation: tradeAmount,
      shares,
      atr_14:            atr,
      entry_limit_price: limitPrice,
      take_profit_price: takeProfitPrice,
      stop_loss_price:   stopLossPrice,
      status:            "pending",
      rationale_json: {
        chapter:           3,
        scalp:             true,
        s_uf:              signal.s_uf,
        d_k:               signal.d_k,
        bar_count:         signal.bar_count,
        trade_amount:      tradeAmount,
        atr_14:            atr,
        take_profit_price: takeProfitPrice,
        stop_loss_price:   stopLossPrice,
        run_id:            signal.run_id,
      },
    });
  } catch (err) {
    return rejectSignal(signal, `ledger_insert_failed: ${err.message}`);
  }

  const dedupeKey = createHash("sha256")
    .update(`CH3:${ticker}:${signal.run_id}:${Date.now()}:${Math.random()}`)
    .digest("hex")
    .slice(0, 16);

  let order;
  try {
    // Bracket order: marketable-limit buy (slippage-capped) + TP/SL enforced
    // by Alpaca in real-time. If price runs past the cap before we fill, the
    // day order rests at the cap — chasing a runaway open is exactly the fill
    // this cap exists to refuse. A resting order can only ever fill at ≤ the
    // cap (brackets stay valid), and the CH3 EOD close still flattens it.
    order = await alpacaPost("/v2/orders", {
      symbol:          ticker,
      qty:             shares,
      side:            "buy",
      type:            "limit",
      limit_price:     limitPrice,
      time_in_force:   "day",
      client_order_id: dedupeKey,
      order_class:     "bracket",
      take_profit: {
        limit_price:   takeProfitPrice,
      },
      stop_loss: {
        stop_price:    stopLossPrice,
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

  // Extract bracket leg order IDs for sentinel tracking
  const legs = order.legs ?? [];
  const tpOrderId = legs.find(l => l.type === "limit")?.id ?? null;
  const slOrderId = legs.find(l => l.type === "stop")?.id ?? null;

  if (ledgerId != null) {
    await writeOrderIdsToLedger(ledgerId, ticker, orderId, tpOrderId, slOrderId, "CH3-BRIDGE");
  }

  console.log(`[CH3-BRIDGE] BRACKET ORDER SUBMITTED | ${ticker} | orderId=${orderId} | TP_id=${tpOrderId} | SL_id=${slOrderId} | shares=${shares} | ledgerId=${ledgerId}`);

  return {
    ok:          true,
    ticker,
    orderId,
    ledgerId,
    shares,
    entryPrice:  entryQuote,
    limitPrice,
    takeProfitPrice,
    stopLossPrice,
    tradeAmount,
  };
}

// ── Cleanup ───────────────────────────────────────────────────────────────
export async function closeBridgePool() {
  await pool.end();
}
