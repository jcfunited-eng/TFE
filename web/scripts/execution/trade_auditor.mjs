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
  ssl: { rejectUnauthorized: false },
});

function alpacaHeaders() {
  return {
    "APCA-API-KEY-ID":     process.env.APCA_API_KEY_ID,
    "APCA-API-SECRET-KEY": process.env.APCA_API_SECRET_KEY,
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

async function fetchAlpacaOrder(orderId, base) {
  try {
    const res = await fetch(`${base}/v2/orders/${orderId}`, { headers: alpacaHeaders() });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

// ── Sync fills from Alpaca back into ledger ───────────────────────────────
async function syncFills() {
  const base = await resolveAlpacaBase();
  // Gap 3 fix: also process rows where alpaca_order_id is NULL but a fallback
  // order ID was written to rationale_json by the writeOrderIdsToLedger helper.
  const res = await pool.query(
    `SELECT id, ticker, alpaca_order_id, alpaca_stop_loss_order_id, shares, status,
            rationale_json->>'fallback_alpaca_order_id' AS fallback_order_id
     FROM personal_trade_ledger
     WHERE status IN ('submitted', 'filled')
       AND (
         alpaca_order_id IS NOT NULL
         OR (rationale_json->>'fallback_alpaca_order_id') IS NOT NULL
       )`
  );

  for (const row of res.rows) {
    // Use primary column first; fall back to rationale_json fallback
    const effectiveOrderId = row.alpaca_order_id ?? row.fallback_order_id;
    if (!effectiveOrderId) continue;

    const order = await fetchAlpacaOrder(effectiveOrderId, base);
    if (!order) continue;

    // Promote fallback to primary column so future queries hit the fast path
    if (!row.alpaca_order_id && row.fallback_order_id) {
      await pool.query(
        `UPDATE personal_trade_ledger SET alpaca_order_id=$1 WHERE id=$2`,
        [effectiveOrderId, row.id]
      ).catch(e => console.error(`[TRADE-AUDITOR] Failed to write recovered alpaca_order_id for ledgerId=${row.id}: ${e.message}`));
    }

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

  // Fence CH3 from primary validation — separate track
  const ch1ch2 = rows.filter(r => (r.signal_class ?? "CH2") !== "CH3");
  const ch3 = rows.filter(r => r.signal_class === "CH3");

  // Administrative closures — excluded from win/loss scoring
  const ADMIN_EXIT_REASONS = ["stale_position_cleanup", "manual_close_stale", "manual_portfolio_reset"];
  const isStrategyTrade = r => !ADMIN_EXIT_REASONS.includes(r.exit_reason);

  const closedStrategy = ch1ch2.filter(r => r.status === "closed" && isStrategyTrade(r));
  const closedAdmin = ch1ch2.filter(r => r.status === "closed" && !isStrategyTrade(r));

  const summary = {
    total_signals:   ch1ch2.length,
    executed:        ch1ch2.filter(r => !["rejected"].includes(r.status)).length,
    rejected:        ch1ch2.filter(r => r.status === "rejected").length,
    open:            ch1ch2.filter(r => ["submitted","filled"].includes(r.status)).length,
    closed:          ch1ch2.filter(r => r.status === "closed").length,
    admin_closures:  closedAdmin.length,
    total_pl:        ch1ch2.reduce((s, r) => s + (parseFloat(r.p_l) || 0), 0),
    wins:            closedStrategy.filter(r => parseFloat(r.p_l) > 0).length,
    losses:          closedStrategy.filter(r => parseFloat(r.p_l) < 0).length,
    exit_reasons:    {},
  };

  for (const r of ch1ch2.filter(r => r.exit_reason)) {
    summary.exit_reasons[r.exit_reason] = (summary.exit_reasons[r.exit_reason] ?? 0) + 1;
  }

  const win_rate = summary.wins + summary.losses > 0
    ? ((summary.wins / (summary.wins + summary.losses)) * 100).toFixed(1) + "%"
    : "n/a";

  // CH3 separate summary
  const ch3_closed = ch3.filter(r => r.status === "closed");
  const ch3_wins = ch3_closed.filter(r => parseFloat(r.p_l) > 0).length;
  const ch3_losses = ch3_closed.filter(r => parseFloat(r.p_l) < 0).length;
  const ch3_summary = {
    note: "CH3 (Scalp) — separate development track",
    total_signals: ch3.length,
    open: ch3.filter(r => ["submitted","filled"].includes(r.status)).length,
    closed: ch3_closed.length,
    wins: ch3_wins,
    losses: ch3_losses,
    total_pl: ch3_closed.reduce((s, r) => s + (parseFloat(r.p_l) || 0), 0),
    win_rate: ch3_wins + ch3_losses > 0
      ? ((ch3_wins / (ch3_wins + ch3_losses)) * 100).toFixed(1) + "%"
      : "n/a",
  };

  return { summary: { ...summary, win_rate }, ch3_summary, rows };
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
