/**
 * web/scripts/execution/stealth_executor.mjs
 * PEE-1 Stealth Executor — Fires queued stealth agents whose scheduled_at has arrived.
 *
 * Run this on a tight interval (every 5–10 min) during market hours via EventBridge,
 * or call runStealthExecutor() from pee1_runner.mjs if you prefer a unified process.
 *
 * For each pee1_stealth_queue row where:
 *   status = 'pending' AND scheduled_at <= NOW()
 *
 * → Re-fetch live price (limit or midpoint per order_type)
 * → Place bracket order on Alpaca
 * → Write ledger row
 * → Mark queue row as executed
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

const ALPACA_DATA_URL = "https://data.alpaca.markets";
const TAKE_PROFIT_MULT = 1.2;
const STOP_LOSS_MULT   = 1.0;

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

async function fetchLimitPrice(ticker) {
  try {
    const t = await alpacaGet(
      `/v2/stocks/${encodeURIComponent(ticker)}/trades/latest?feed=iex`,
      ALPACA_DATA_URL
    );
    const p = parseFloat(t?.trade?.p ?? 0);
    if (isFinite(p) && p > 0) return parseFloat(p.toFixed(2));
  } catch { /* fall through */ }
  const bars = await alpacaGet(
    `/v2/stocks/${encodeURIComponent(ticker)}/bars?timeframe=1Day&limit=1&feed=iex`,
    ALPACA_DATA_URL
  );
  const c = parseFloat((bars?.bars ?? [])[0]?.c ?? 0);
  if (!isFinite(c) || c <= 0) throw new Error(`No valid price for ${ticker}`);
  return parseFloat(c.toFixed(2));
}

async function fetchMidpointPrice(ticker) {
  try {
    const q = await alpacaGet(
      `/v2/stocks/${encodeURIComponent(ticker)}/quotes/latest?feed=iex`,
      ALPACA_DATA_URL
    );
    const bid = parseFloat(q?.quote?.bp ?? 0);
    const ask = parseFloat(q?.quote?.ap ?? 0);
    if (bid > 0 && ask > 0) return parseFloat(((bid + ask) / 2).toFixed(2));
  } catch { /* fall through */ }
  return fetchLimitPrice(ticker);
}

async function ledgerInsert(queueRow, orderId, legIds, liveEntryPrice, BASE) {
  const sig = queueRow.signal_json ?? {};
  const res = await pool.query(
    `INSERT INTO personal_trade_ledger (
       ticker, run_id, signal_class,
       spy_dk, s_uf, bar_count, f_n,
       vault_equity_at_signal, risk_per_trade_pct, dollar_allocation, shares, atr_14,
       alpaca_order_id, alpaca_take_profit_order_id, alpaca_stop_loss_order_id,
       entry_limit_price, take_profit_price, stop_loss_price,
       status, rationale_json, signal_detected_at
     ) VALUES (
       $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,NOW()
     ) RETURNING id`,
    [
      queueRow.ticker,
      sig.run_id ?? queueRow.ticker,
      sig.signal_class ?? "3WA",
      sig.spy_dk   ?? null,
      sig.s_uf     ?? null,
      sig.bar_count ?? null,
      sig.f_n       ?? null,
      queueRow.vault_equity   ?? null,
      1.5,
      queueRow.shares * liveEntryPrice,
      queueRow.shares,
      queueRow.atr_14 ?? null,
      orderId,
      legIds.tp ?? null,
      legIds.sl ?? null,
      liveEntryPrice,
      queueRow.take_profit_price ?? null,
      queueRow.stop_loss_price   ?? null,
      "submitted",
      JSON.stringify({
        stealth:          true,
        stealth_group_id: sig.stealth_group_id,
        agent_index:      queueRow.agent_index,
        total_agents:     queueRow.total_agents,
        order_type:       queueRow.order_type,
        parent_ledger_id: queueRow.parent_ledger_id,
        queue_id:         queueRow.id,
      }),
    ]
  );
  return res.rows[0].id;
}

export async function runStealthExecutor() {
  console.log("[STEALTH-EXEC] Checking pee1_stealth_queue for due agents...");
  const BASE = await resolveAlpacaBase();

  const due = await pool.query(
    `SELECT * FROM pee1_stealth_queue
     WHERE status = 'pending' AND scheduled_at <= NOW()
     ORDER BY agent_index ASC`
  );

  if (due.rows.length === 0) {
    console.log("[STEALTH-EXEC] No agents due. Done.");
    return { processed: 0 };
  }

  console.log(`[STEALTH-EXEC] ${due.rows.length} agent(s) due for execution`);
  let executed = 0, failed = 0;

  for (const row of due.rows) {
    const { ticker, shares, order_type, take_profit_price, stop_loss_price } = row;
    console.log(`[STEALTH-EXEC] Processing agent ${row.agent_index}/${row.total_agents - 1} | ${ticker} | type=${order_type} | shares=${shares}`);

    try {
      // Re-fetch live entry price
      const entryPrice = order_type === "midpoint"
        ? await fetchMidpointPrice(ticker)
        : await fetchLimitPrice(ticker);

      const order = await alpacaPost("/v2/orders", {
        symbol:        ticker,
        qty:           shares,
        side:          "buy",
        type:          "limit",
        time_in_force: "day",
        limit_price:   entryPrice,
        order_class:   "bracket",
        take_profit: { limit_price: parseFloat(take_profit_price) },
        stop_loss:   { stop_price:  parseFloat(stop_loss_price)   },
      }, BASE);

      const legIds = (order.legs ?? []).reduce((acc, l) => {
        if (l.order_class === "take_profit") acc.tp = l.id;
        if (l.order_class === "stop_loss")   acc.sl = l.id;
        return acc;
      }, {});

      const ledgerId = await ledgerInsert(row, order.id, legIds, entryPrice, BASE)
        .catch(e => { console.error("[STEALTH-EXEC] Ledger insert failed:", e.message); return null; });

      await pool.query(
        `UPDATE pee1_stealth_queue
         SET status='executed', executed_at=NOW(), alpaca_order_id=$1, ledger_id=$2
         WHERE id=$3`,
        [order.id, ledgerId, row.id]
      );

      console.log(`[STEALTH-EXEC] ✓ Agent ${row.agent_index} | ${ticker} | orderId=${order.id} | entry=${entryPrice}`);
      executed++;
    } catch (err) {
      console.error(`[STEALTH-EXEC] ✗ Agent ${row.agent_index} | ${ticker} | ${err.message}`);
      await pool.query(
        `UPDATE pee1_stealth_queue SET status='failed', error=$1 WHERE id=$2`,
        [err.message, row.id]
      ).catch(() => {});
      failed++;
    }
  }

  console.log(`[STEALTH-EXEC] Done. executed=${executed} failed=${failed}`);
  return { processed: due.rows.length, executed, failed };
}

export async function closeStealthExecutorPool() {
  await pool.end();
}

// ── Direct execution ──────────────────────────────────────────────────────
if (process.argv[1]?.endsWith("stealth_executor.mjs")) {
  runStealthExecutor()
    .then(r => { console.log("[STEALTH-EXEC] Result:", r); process.exit(0); })
    .catch(e => { console.error("[STEALTH-EXEC] FATAL:", e.message); process.exit(1); })
    .finally(() => pool.end());
}
