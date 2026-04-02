/**
 * web/scripts/execution/trade_auditor.mjs
 * PEE-1 Trade Auditor — SQA Reporting
 *
 * Reads personal_trade_ledger and produces a structured audit report:
 *   - All signals received (including rejected)
 *   - All executions (submitted, filled)
 *   - All exits and their reasons
 *   - P&L summary
 *
 * Also syncs Alpaca order fill prices back into the ledger for any
 * submitted/filled rows that don't yet have entry_filled_price.
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

function alpacaHeaders() {
  return {
    "APCA-API-KEY-ID":     process.env.ALPACA_API_KEY,
    "APCA-API-SECRET-KEY": process.env.ALPACA_SECRET_KEY,
  };
}
const ALPACA_BASE = process.env.ALPACA_PAPER !== "0"
  ? "https://paper-api.alpaca.markets"
  : "https://api.alpaca.markets";

async function fetchAlpacaOrder(orderId) {
  try {
    const res = await fetch(`${ALPACA_BASE}/v2/orders/${orderId}`, { headers: alpacaHeaders() });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

// ── Sync fills from Alpaca back into ledger ───────────────────────────────
async function syncFills() {
  const res = await pool.query(
    `SELECT id, ticker, alpaca_order_id, alpaca_stop_loss_order_id, shares, status
     FROM personal_trade_ledger
     WHERE status IN ('submitted', 'filled')
       AND alpaca_order_id IS NOT NULL`
  );

  for (const row of res.rows) {
    const order = await fetchAlpacaOrder(row.alpaca_order_id);
    if (!order) continue;

    const fields = {};

    // Entry fill
    if (order.filled_avg_price && !row.entry_filled_price) {
      fields.entry_filled_price = parseFloat(order.filled_avg_price);
      fields.entry_filled_at    = order.filled_at ?? new Date().toISOString();
      fields.status             = "filled";
    }

    // Exit fill (check if stop_loss or take_profit leg resolved)
    if (order.status === "filled" && order.legs) {
      for (const leg of order.legs) {
        if (["take_profit", "stop_loss"].includes(leg.order_class) && leg.filled_avg_price) {
          const exitPrice = parseFloat(leg.filled_avg_price);
          const entryPrice = fields.entry_filled_price ?? parseFloat(order.filled_avg_price ?? "0");
          const pl = (exitPrice - entryPrice) * row.shares;
          const plPct = entryPrice > 0 ? (pl / (entryPrice * row.shares)) * 100 : null;

          fields.exit_filled_price = exitPrice;
          fields.exit_filled_at    = leg.filled_at ?? new Date().toISOString();
          fields.p_l               = pl;
          fields.p_l_pct           = plPct;
          fields.exit_reason       = leg.order_class === "take_profit" ? "take_profit" : "stop_loss";
          fields.status            = "closed";
        }
      }
    }

    if (Object.keys(fields).length === 0) continue;

    const setClauses = Object.keys(fields).map((k, i) => `${k} = $${i + 2}`).join(", ");
    await pool.query(
      `UPDATE personal_trade_ledger SET ${setClauses} WHERE id = $1`,
      [row.id, ...Object.values(fields)]
    ).catch(e => console.error(`[AUDITOR] Fill sync failed for ${row.ticker}:`, e.message));
  }
}

// ── Build audit report ────────────────────────────────────────────────────
async function buildReport() {
  const res = await pool.query(
    `SELECT
       id, ticker, signal_class, status, exit_reason,
       signal_detected_at, entry_filled_at, exit_filled_at,
       entry_filled_price, exit_filled_price, shares,
       dollar_allocation, p_l, p_l_pct,
       spy_dk, s_uf, bar_count, f_n,
       vault_equity_at_signal, atr_14,
       alpaca_order_id, rationale_json
     FROM personal_trade_ledger
     ORDER BY created_at DESC`
  );

  const rows = res.rows;

  const summary = {
    total_signals:   rows.length,
    executed:        rows.filter(r => !["rejected"].includes(r.status)).length,
    rejected:        rows.filter(r => r.status === "rejected").length,
    open:            rows.filter(r => ["submitted","filled"].includes(r.status)).length,
    closed:          rows.filter(r => r.status === "closed").length,
    total_pl:        rows.reduce((s, r) => s + (parseFloat(r.p_l) || 0), 0),
    wins:            rows.filter(r => parseFloat(r.p_l) > 0).length,
    losses:          rows.filter(r => parseFloat(r.p_l) < 0).length,
    exit_reasons:    {},
  };

  for (const r of rows.filter(r => r.exit_reason)) {
    summary.exit_reasons[r.exit_reason] = (summary.exit_reasons[r.exit_reason] ?? 0) + 1;
  }

  const win_rate = summary.wins + summary.losses > 0
    ? ((summary.wins / (summary.wins + summary.losses)) * 100).toFixed(1) + "%"
    : "n/a";

  return { summary: { ...summary, win_rate }, rows };
}

// ── Main ──────────────────────────────────────────────────────────────────
export async function runAudit({ syncFillsFirst = true } = {}) {
  if (syncFillsFirst) {
    console.log("[AUDITOR] Syncing fills from Alpaca...");
    await syncFills();
  }

  const report = await buildReport();
  const { summary } = report;

  console.log("[AUDITOR] ── Trade Audit Report ──────────────────────────");
  console.log(`[AUDITOR]   Total signals   : ${summary.total_signals}`);
  console.log(`[AUDITOR]   Executed        : ${summary.executed}`);
  console.log(`[AUDITOR]   Rejected        : ${summary.rejected}`);
  console.log(`[AUDITOR]   Open            : ${summary.open}`);
  console.log(`[AUDITOR]   Closed          : ${summary.closed}`);
  console.log(`[AUDITOR]   Total P&L       : $${summary.total_pl.toFixed(2)}`);
  console.log(`[AUDITOR]   Win rate        : ${summary.win_rate} (${summary.wins}W / ${summary.losses}L)`);
  console.log(`[AUDITOR]   Exit breakdown  :`, summary.exit_reasons);
  console.log("[AUDITOR] ────────────────────────────────────────────────");

  return report;
}

export async function closeAuditorPool() {
  await pool.end();
}
