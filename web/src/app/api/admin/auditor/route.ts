/**
 * web/src/app/api/admin/auditor/route.ts
 * PEE-1 Admin Auditor API — Signal Provenance + Execution Trace + Sentinel Log
 *
 * GET /api/admin/auditor
 *   Query params:
 *     status   — filter by status (all | open | closed | rejected)
 *     ticker   — filter by ticker symbol
 *     limit    — max rows to return (default 200)
 *     offset   — pagination offset (default 0)
 *
 * Returns:
 *   - rows: full ledger rows with signal provenance + execution details
 *   - stealth: stealth queue rows (grouped by parent_ledger_id)
 *   - circuitBreaker: current circuit breaker state
 *   - summary: aggregate stats
 *
 * Admin-only endpoint.
 */

import { NextRequest, NextResponse } from "next/server";
import { getCurrentServerUser } from "@/lib/server-auth";
import { resolveRuntimePostgresPool } from "@/lib/runtime-db";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const user = await getCurrentServerUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  if (user.role !== "admin") return NextResponse.json({ error: "Forbidden" }, { status: 403 });

  const { searchParams } = new URL(request.url);
  const statusFilter = searchParams.get("status") ?? "all";
  const tickerFilter = searchParams.get("ticker")?.trim().toUpperCase() ?? "";
  const limit        = Math.min(500, Math.max(1, parseInt(searchParams.get("limit") ?? "200", 10)));
  const offset       = Math.max(0, parseInt(searchParams.get("offset") ?? "0", 10));

  const pool = resolveRuntimePostgresPool();

  try {
    // ── Build WHERE clause ───────────────────────────────────────────────
    const conditions: string[] = [];
    const params: (string | number)[] = [];

    if (statusFilter !== "all") {
      if (statusFilter === "open") {
        conditions.push(`l.status IN ('submitted', 'filled')`);
      } else if (statusFilter === "closed") {
        conditions.push(`l.status = 'closed'`);
      } else if (statusFilter === "rejected") {
        conditions.push(`l.status = 'rejected'`);
      }
    }

    if (tickerFilter) {
      params.push(tickerFilter);
      conditions.push(`l.ticker = $${params.length}`);
    }

    const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(" AND ")}` : "";

    // ── Ledger rows ──────────────────────────────────────────────────────
    params.push(limit, offset);
    const ledgerRes = await pool.query(
      `SELECT
         l.id, l.ticker, l.run_id, l.signal_class, l.status, l.exit_reason,
         l.spy_dk, l.s_uf, l.bar_count, l.f_n,
         l.signal_detected_at, l.entry_filled_at, l.exit_filled_at,
         l.entry_limit_price, l.entry_filled_price,
         l.take_profit_price, l.stop_loss_price,
         l.exit_filled_price, l.shares, l.dollar_allocation,
         l.p_l, l.p_l_pct, l.atr_14,
         l.vault_equity_at_signal, l.risk_per_trade_pct,
         l.alpaca_order_id, l.alpaca_take_profit_order_id, l.alpaca_stop_loss_order_id,
         l.rationale_json, l.created_at
       FROM personal_trade_ledger l
       ${whereClause}
       ORDER BY l.created_at DESC
       LIMIT $${params.length - 1} OFFSET $${params.length}`,
      params
    );

    // ── Total count ──────────────────────────────────────────────────────
    const countParams = params.slice(0, -2);
    const countRes = await pool.query(
      `SELECT COUNT(*) FROM personal_trade_ledger l ${whereClause}`,
      countParams
    );
    const totalRows = parseInt(countRes.rows[0]?.count ?? "0", 10);

    // ── Stealth queue: agents grouped by parent_ledger_id ─────────────
    let stealthRows: Record<string, unknown>[] = [];
    try {
      const sq = await pool.query(
        `SELECT
           sq.id, sq.parent_ledger_id, sq.ticker, sq.agent_index, sq.total_agents,
           sq.shares, sq.order_type, sq.entry_limit_price,
           sq.take_profit_price, sq.stop_loss_price,
           sq.scheduled_at, sq.executed_at, sq.status,
           sq.alpaca_order_id, sq.ledger_id, sq.error
         FROM pee1_stealth_queue sq
         ORDER BY sq.created_at DESC
         LIMIT 500`
      );
      stealthRows = sq.rows;
    } catch {
      // Table may not exist yet — non-fatal
    }

    // ── Circuit breaker state ────────────────────────────────────────────
    let circuitBreaker = null;
    try {
      const cbRes = await pool.query(
        `SELECT id, trigger_reason, triggered_at, expires_at,
                vault_equity_open, vault_equity_low, drawdown_pct, threshold_pct,
                cleared_at
         FROM pee1_circuit_breaker
         ORDER BY triggered_at DESC LIMIT 5`
      );
      circuitBreaker = cbRes.rows;
    } catch {
      circuitBreaker = [];
    }

    // ── Summary ──────────────────────────────────────────────────────────
    const allRes = await pool.query(
      `SELECT status, exit_reason, p_l, signal_class, signal_detected_at
       FROM personal_trade_ledger`
    );
    const all = allRes.rows;

    // Fence CH3 from primary validation — separate track
    const ch1ch2 = all.filter(r => (r.signal_class ?? "CH2") !== "CH3");
    const ch3 = all.filter(r => r.signal_class === "CH3");

    // Administrative closures — excluded from win/loss scoring
    const ADMIN_EXIT_REASONS = ["stale_position_cleanup", "manual_close_stale", "manual_portfolio_reset"];
    const isStrategyTrade = (r: typeof all[0]) => !ADMIN_EXIT_REASONS.includes(r.exit_reason);
    const closedStrategy = ch1ch2.filter(r => r.status === "closed" && isStrategyTrade(r));
    const closedAdmin = ch1ch2.filter(r => r.status === "closed" && !isStrategyTrade(r));

    const summary = {
      note:       "CH1/CH2 only — CH3 reported separately. Admin closures excluded from win/loss.",
      total:      ch1ch2.length,
      open:       ch1ch2.filter(r => ["submitted","filled"].includes(r.status)).length,
      closed:     ch1ch2.filter(r => r.status === "closed").length,
      admin_closures: closedAdmin.length,
      rejected:   ch1ch2.filter(r => r.status === "rejected").length,
      wins:       closedStrategy.filter(r => parseFloat(r.p_l) > 0).length,
      losses:     closedStrategy.filter(r => parseFloat(r.p_l) < 0).length,
      total_pl:   ch1ch2.reduce((s, r) => s + (parseFloat(r.p_l) || 0), 0),
      exit_reasons: {} as Record<string, number>,
      by_signal_class: {} as Record<string, number>,
    };

    for (const r of ch1ch2) {
      if (r.exit_reason) {
        summary.exit_reasons[r.exit_reason] = (summary.exit_reasons[r.exit_reason] ?? 0) + 1;
      }
      if (r.signal_class) {
        summary.by_signal_class[r.signal_class] = (summary.by_signal_class[r.signal_class] ?? 0) + 1;
      }
    }

    const wl = summary.wins + summary.losses;
    const win_rate = wl > 0 ? ((summary.wins / wl) * 100).toFixed(1) + "%" : "n/a";

    // CH3 separate validation track
    const ch3Closed = ch3.filter(r => r.status === "closed");
    const ch3Wins = ch3Closed.filter(r => parseFloat(r.p_l) > 0).length;
    const ch3Losses = ch3Closed.filter(r => parseFloat(r.p_l) < 0).length;
    const ch3WL = ch3Wins + ch3Losses;
    const ch3_summary = {
      note: "CH3 (Scalp) — separate development track",
      total: ch3.length,
      open: ch3.filter(r => ["submitted","filled"].includes(r.status)).length,
      closed: ch3Closed.length,
      wins: ch3Wins,
      losses: ch3Losses,
      total_pl: ch3Closed.reduce((s, r) => s + (parseFloat(r.p_l) || 0), 0),
      win_rate: ch3WL > 0 ? ((ch3Wins / ch3WL) * 100).toFixed(1) + "%" : "n/a",
    };

    return NextResponse.json({
      rows:           ledgerRes.rows,
      totalRows,
      limit,
      offset,
      stealth:        stealthRows,
      circuitBreaker,
      summary:        { ...summary, win_rate },
      ch3_summary,
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    if (msg.includes("does not exist")) {
      return NextResponse.json({ error: "tables_not_initialized" }, { status: 503 });
    }
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
