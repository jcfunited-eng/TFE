/**
 * web/scripts/execution/stealth_bridge.mjs
 * PEE-1 Stealth Execution Engine V2 — Dynamic Order Slicer
 *
 * Decision logic:
 *   If dollar_allocation < stealth_threshold_dollars (default $5,000):
 *     → delegate straight to alpaca_bridge.executeBracketOrder (no slicing)
 *
 *   If dollar_allocation >= threshold:
 *     → split into N=stealth_agent_count (default 3, range 2–5) independent bracket orders
 *     → Agent 0 fires immediately (limit order at latest trade price)
 *     → Agents 1..N-1 written to pee1_stealth_queue with randomized scheduled_at
 *     → stealth_executor.mjs picks up queued agents on the next pass
 *
 * Order type alternation (per agent_index):
 *   Even indices (0, 2, 4) → limit order at latest trade price
 *   Odd  indices (1, 3)    → midpoint limit order at (bid + ask) / 2
 *
 * Share distribution:
 *   Base = floor(totalShares / N) per agent
 *   Each agent gets base ± up to 10% randomization
 *   Remainder shares given to agent 0 after rounding
 *   Total shares across all agents = totalShares (exact)
 *
 * Full audit trail:
 *   rationale_json on each ledger row records stealth_group_id, agent_index,
 *   total_agents, order_type, and parent_ledger_id.
 */

import pg from "pg";
import { createHash, randomUUID } from "crypto";
import { executeBracketOrder, rejectSignal } from "./alpaca_bridge.mjs";

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
});

// ── Constants ────────────────────────────────────────────────────────────
const ATR_PERIOD       = 14;
const TAKE_PROFIT_MULT = 1.2;
const STOP_LOSS_MULT   = 1.0;
const MIN_SHARE_PRICE  = 5.0;
const ALPACA_DATA_URL  = "https://data.alpaca.markets";

// ── Config helpers ────────────────────────────────────────────────────────
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

async function readExecutionMode() {
  return readConfig("execution_mode", "paper");
}

function alpacaBaseUrl(mode) {
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
  if (!res.ok) throw new Error(`Alpaca GET ${path} → ${res.status}: ${JSON.stringify(body)}`);
  return body;
}

async function alpacaPost(path, payload, base) {
  const res  = await fetch(`${base}${path}`, {
    method:  "POST",
    headers: alpacaHeaders(),
    body:    JSON.stringify(payload),
  });
  const body = await res.json();
  if (!res.ok) throw new Error(`Alpaca POST ${path} → ${res.status}: ${JSON.stringify(body)}`);
  return body;
}

// ── Market data ───────────────────────────────────────────────────────────
async function fetchLatestPrice(ticker) {
  try {
    const t = await alpacaGet(
      `/v2/stocks/${encodeURIComponent(ticker)}/trades/latest?feed=iex`,
      ALPACA_DATA_URL
    );
    const p = parseFloat(t?.trade?.p ?? 0);
    if (isFinite(p) && p > 0) return p;
  } catch { /* fall through */ }

  const bars = await alpacaGet(
    `/v2/stocks/${encodeURIComponent(ticker)}/bars?timeframe=1Day&limit=1&feed=iex`,
    ALPACA_DATA_URL
  );
  const close = parseFloat((bars?.bars ?? [])[0]?.c ?? 0);
  if (!isFinite(close) || close <= 0)
    throw new Error(`fetchLatestPrice: no valid price for ${ticker}`);
  return close;
}

async function fetchMidpointPrice(ticker) {
  try {
    const q = await alpacaGet(
      `/v2/stocks/${encodeURIComponent(ticker)}/quotes/latest?feed=iex`,
      ALPACA_DATA_URL
    );
    const bid = parseFloat(q?.quote?.bp ?? 0);
    const ask = parseFloat(q?.quote?.ap ?? 0);
    if (isFinite(bid) && isFinite(ask) && bid > 0 && ask > 0) {
      return parseFloat(((bid + ask) / 2).toFixed(2));
    }
  } catch { /* fall through */ }
  // Fallback to last trade price if quote unavailable
  return fetchLatestPrice(ticker);
}

async function computeATR(ticker) {
  const bars = await alpacaGet(
    `/v2/stocks/${encodeURIComponent(ticker)}/bars?timeframe=1Day&limit=${ATR_PERIOD + 1}&feed=iex`,
    ALPACA_DATA_URL
  );
  const list = bars?.bars ?? [];
  if (list.length < 2) throw new Error(`ATR: insufficient bars for ${ticker}`);

  let sum = 0;
  for (let i = 1; i < list.length; i++) {
    const high = parseFloat(list[i].h);
    const low  = parseFloat(list[i].l);
    const prev = parseFloat(list[i - 1].c);
    sum += Math.max(high - low, Math.abs(high - prev), Math.abs(low - prev));
  }
  const atr = sum / (list.length - 1);
  if (!isFinite(atr) || atr <= 0) throw new Error(`ATR invalid for ${ticker}: ${atr}`);
  return atr;
}

async function fetchAccountEquity(base) {
  const acct   = await alpacaGet("/v2/account", base);
  const equity = parseFloat(acct?.equity ?? acct?.portfolio_value ?? 0);
  if (!isFinite(equity) || equity <= 0)
    throw new Error("fetchAccountEquity: equity unavailable");
  return equity;
}

// ── Share slice distribution ──────────────────────────────────────────────
/**
 * Split totalShares into N slices with ±10% randomization.
 * Ensures sum === totalShares exactly (remainder to slice 0).
 */
function distributeShares(totalShares, N) {
  if (N <= 1) return [totalShares];
  const base  = Math.floor(totalShares / N);
  const jitter = Math.ceil(base * 0.10);  // ±10%

  const slices = [];
  for (let i = 0; i < N; i++) {
    const delta = Math.floor(Math.random() * (jitter * 2 + 1)) - jitter;
    slices.push(Math.max(1, base + delta));
  }

  // Normalize to match totalShares exactly
  const currentSum = slices.reduce((a, b) => a + b, 0);
  slices[0] += (totalShares - currentSum);
  if (slices[0] < 1) {
    // Edge case: first slice went negative — redistribute
    const shortfall = 1 - slices[0];
    slices[0] = 1;
    for (let i = 1; i < N && shortfall > 0; i++) {
      const give = Math.min(slices[i] - 1, shortfall);
      slices[i] -= give;
    }
  }
  return slices;
}

// ── Scheduled delay for each agent (seconds) ─────────────────────────────
// Agent 0: fires now. Each subsequent agent: 5–20 minutes after the previous.
function buildScheduledTimes(N) {
  const times = [new Date()];
  let base = Date.now();
  for (let i = 1; i < N; i++) {
    const delaySec = 300 + Math.floor(Math.random() * 900); // 5–20 min
    base += delaySec * 1000;
    times.push(new Date(base));
  }
  return times;
}

// ── Ledger helpers ────────────────────────────────────────────────────────
async function ledgerInsert(row) {
  const res = await pool.query(
    `INSERT INTO personal_trade_ledger (
       ticker, run_id, signal_class,
       spy_dk, s_uf, bar_count, f_n,
       vault_equity_at_signal, risk_per_trade_pct, dollar_allocation, shares, atr_14,
       alpaca_order_id, alpaca_take_profit_order_id, alpaca_stop_loss_order_id,
       entry_limit_price, take_profit_price, stop_loss_price,
       status, exit_reason, rationale_json, signal_detected_at
     ) VALUES (
       $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,NOW()
     ) RETURNING id`,
    [
      row.ticker, row.run_id, row.signal_class,
      row.spy_dk ?? null, row.s_uf ?? null, row.bar_count ?? null, row.f_n ?? null,
      row.vault_equity ?? null, row.risk_per_trade_pct ?? 1.5,
      row.dollar_allocation ?? null, row.shares ?? null, row.atr_14 ?? null,
      row.alpaca_order_id ?? null, row.take_profit_order_id ?? null, row.stop_loss_order_id ?? null,
      row.entry_limit_price ?? null, row.take_profit_price ?? null, row.stop_loss_price ?? null,
      row.status, row.exit_reason ?? null,
      JSON.stringify(row.rationale_json ?? {}),
    ]
  );
  return res.rows[0].id;
}

// ── Place a single sliced bracket order ──────────────────────────────────
async function placeAgentOrder({ ticker, shares, orderType, entryPrice, takeProfitPrice, stopLossPrice, BASE }) {
  return alpacaPost("/v2/orders", {
    symbol:        ticker,
    qty:           shares,
    side:          "buy",
    type:          "limit",
    time_in_force: "day",
    limit_price:   entryPrice,
    order_class:   "bracket",
    take_profit: { limit_price: takeProfitPrice },
    stop_loss:   { stop_price:  stopLossPrice   },
  }, BASE);
}

// ── Enqueue future agents to pee1_stealth_queue ───────────────────────────
async function enqueueAgents(agents, signal, groupId, parentLedgerId) {
  for (const agent of agents) {
    await pool.query(
      `INSERT INTO pee1_stealth_queue (
         parent_ledger_id, ticker, signal_json, agent_index, total_agents,
         shares, order_type, entry_limit_price, take_profit_price, stop_loss_price,
         atr_14, vault_equity, scheduled_at
       ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)`,
      [
        parentLedgerId,
        signal.ticker,
        JSON.stringify({ ...signal, stealth_group_id: groupId }),
        agent.agentIndex,
        agent.totalAgents,
        agent.shares,
        agent.orderType,
        agent.entryPrice,
        agent.takeProfitPrice,
        agent.stopLossPrice,
        agent.atr,
        agent.vaultEquity,
        agent.scheduledAt.toISOString(),
      ]
    ).catch(e => console.error(`[STEALTH] Queue insert failed for agent ${agent.agentIndex}:`, e.message));
  }
}

// ── Main entry point ──────────────────────────────────────────────────────
/**
 * Decide whether to slice or delegate, then execute agent 0 + queue the rest.
 *
 * @param {Object} signal — same shape as alpaca_bridge.executeBracketOrder expects
 * @param {Object} [opts] — { riskPct }
 * @returns {Promise<Object>} execution result
 */
export async function executeStealthOrder(signal, opts = {}) {
  const ticker  = String(signal?.ticker ?? "").trim().toUpperCase();
  const riskPct = Math.min(Math.max(parseFloat(opts.riskPct ?? "1.5"), 0.1), 5.0);

  // ── Load stealth config from DB ──────────────────────────────────────
  const [thresholdStr, agentCountStr, executionMode] = await Promise.all([
    readConfig("stealth_threshold_dollars", "5000"),
    readConfig("stealth_agent_count",       "3"),
    readExecutionMode(),
  ]);

  const threshold   = parseFloat(thresholdStr);
  const agentCount  = Math.min(5, Math.max(2, parseInt(agentCountStr, 10)));
  const BASE        = alpacaBaseUrl(executionMode);
  const isPaper     = executionMode !== "live";

  // ── Fetch market data ────────────────────────────────────────────────
  let vaultEquity, currentPrice, atr;
  try {
    [vaultEquity, currentPrice, atr] = await Promise.all([
      fetchAccountEquity(BASE),
      fetchLatestPrice(ticker),
      computeATR(ticker),
    ]);
  } catch (err) {
    return rejectSignal(signal, `stealth_market_data_failed: ${err.message}`);
  }

  if (currentPrice < MIN_SHARE_PRICE) {
    return rejectSignal(signal, `price_below_minimum: ${currentPrice}`);
  }

  // ── Position sizing ──────────────────────────────────────────────────
  const dollarAllocation = vaultEquity * (riskPct / 100);
  const totalShares      = Math.floor(dollarAllocation / currentPrice);

  if (totalShares < 1) {
    return rejectSignal(signal, `shares_below_minimum: allocation=${dollarAllocation.toFixed(2)} price=${currentPrice}`);
  }

  // ── Should we slice? ─────────────────────────────────────────────────
  if (dollarAllocation < threshold || agentCount <= 1) {
    console.log(`[STEALTH] ${ticker} | allocation=$${dollarAllocation.toFixed(2)} < threshold=$${threshold} — delegating to bridge`);
    return executeBracketOrder(signal, opts);
  }

  console.log(`[STEALTH] ${ticker} | allocation=$${dollarAllocation.toFixed(2)} ≥ threshold=$${threshold} — slicing into ${agentCount} agents`);

  // ── Compute bracket prices (shared across all agents) ────────────────
  const entryPrice      = parseFloat(currentPrice.toFixed(2));
  const takeProfitPrice = parseFloat((entryPrice + TAKE_PROFIT_MULT * atr).toFixed(2));
  const stopLossPrice   = parseFloat((entryPrice - STOP_LOSS_MULT   * atr).toFixed(2));

  if (stopLossPrice <= 0) {
    return rejectSignal(signal, `stop_loss_price_invalid: ${stopLossPrice}`);
  }

  // ── Build slice distribution ─────────────────────────────────────────
  const shareSlices    = distributeShares(totalShares, agentCount);
  const scheduledTimes = buildScheduledTimes(agentCount);
  const groupId        = randomUUID();

  console.log(`[STEALTH] Group ${groupId} | slices=${shareSlices.join("+")} | entry=${entryPrice} | TP=${takeProfitPrice} | SL=${stopLossPrice}`);

  // ── Agent 0: fire immediately ────────────────────────────────────────
  const agent0Type  = "limit";  // even index
  const agent0Price = entryPrice;

  let parentLedgerId;
  try {
    parentLedgerId = await ledgerInsert({
      ticker,
      run_id:            signal.run_id ?? groupId,
      signal_class:      signal.signal_class ?? "3WA",
      spy_dk:            signal.spy_dk   ?? null,
      s_uf:              signal.s_uf     ?? null,
      bar_count:         signal.bar_count ?? null,
      f_n:               signal.f_n       ?? null,
      vault_equity:      vaultEquity,
      risk_per_trade_pct: riskPct,
      dollar_allocation: shareSlices[0] * agent0Price,
      shares:            shareSlices[0],
      atr_14:            atr,
      entry_limit_price: agent0Price,
      take_profit_price: takeProfitPrice,
      stop_loss_price:   stopLossPrice,
      status:            "pending",
      rationale_json: {
        stealth:         true,
        stealth_group_id: groupId,
        agent_index:     0,
        total_agents:    agentCount,
        order_type:      agent0Type,
        paper_mode:      isPaper,
        spy_dk:          signal.spy_dk,
        s_uf:            signal.s_uf,
        bar_count:       signal.bar_count,
        run_id:          signal.run_id,
      },
    });
  } catch (dbErr) {
    console.error(`[STEALTH] Ledger pre-insert failed for ${ticker} agent 0:`, dbErr.message);
  }

  let agent0OrderId;
  try {
    const order0 = await placeAgentOrder({
      ticker, shares: shareSlices[0], orderType: agent0Type,
      entryPrice: agent0Price, takeProfitPrice, stopLossPrice, BASE,
    });
    agent0OrderId = order0.id;
    const legIds = (order0.legs ?? []).reduce((acc, l) => {
      if (l.order_class === "take_profit") acc.tp = l.id;
      if (l.order_class === "stop_loss")   acc.sl = l.id;
      return acc;
    }, {});

    if (parentLedgerId != null) {
      await pool.query(
        `UPDATE personal_trade_ledger
         SET alpaca_order_id=$1, alpaca_take_profit_order_id=$2,
             alpaca_stop_loss_order_id=$3, status='submitted'
         WHERE id=$4`,
        [order0.id, legIds.tp ?? null, legIds.sl ?? null, parentLedgerId]
      ).catch(e => console.error("[STEALTH] Ledger update failed:", e.message));
    }
    console.log(`[STEALTH] Agent 0 submitted | ${ticker} | orderId=${order0.id} | shares=${shareSlices[0]}`);
  } catch (err) {
    console.error(`[STEALTH] Agent 0 order FAILED for ${ticker}:`, err.message);
    if (parentLedgerId != null) {
      await pool.query(
        `UPDATE personal_trade_ledger SET status='rejected', exit_reason='order_failed',
         rationale_json = rationale_json || $1::jsonb WHERE id=$2`,
        [JSON.stringify({ agent0_error: err.message }), parentLedgerId]
      ).catch(() => {});
    }
    return { ok: false, reason: `agent0_order_failed: ${err.message}` };
  }

  // ── Agents 1..N-1: determine prices and enqueue ──────────────────────
  const futureAgents = [];
  for (let i = 1; i < agentCount; i++) {
    const orderType = i % 2 === 0 ? "limit" : "midpoint";
    // Midpoint price will be fetched at execution time by stealth_executor.
    // Store the last-known price as a fallback reference.
    futureAgents.push({
      agentIndex:      i,
      totalAgents:     agentCount,
      shares:          shareSlices[i],
      orderType,
      entryPrice:      entryPrice,       // executor re-fetches midpoint/limit live
      takeProfitPrice,
      stopLossPrice,
      atr,
      vaultEquity,
      scheduledAt:     scheduledTimes[i],
    });
    console.log(`[STEALTH] Agent ${i} queued | type=${orderType} | shares=${shareSlices[i]} | scheduledAt=${scheduledTimes[i].toISOString()}`);
  }

  await enqueueAgents(futureAgents, signal, groupId, parentLedgerId ?? null);

  return {
    ok:              true,
    sliced:          true,
    ticker,
    groupId,
    agentCount,
    agent0OrderId,
    parentLedgerId,
    totalShares,
    shareSlices,
    entryPrice,
    takeProfitPrice,
    stopLossPrice,
    atr,
    dollarAllocation,
    paperMode: isPaper,
    queuedAgents: futureAgents.map(a => ({
      agentIndex:  a.agentIndex,
      shares:      a.shares,
      orderType:   a.orderType,
      scheduledAt: a.scheduledAt.toISOString(),
    })),
  };
}

export async function closeStealthPool() {
  await pool.end();
}
