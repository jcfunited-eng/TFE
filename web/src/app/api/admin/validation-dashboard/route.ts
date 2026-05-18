import { NextResponse } from "next/server";
import { getCurrentServerUser } from "@/lib/server-auth";
import { resolveRuntimePostgresPool } from "@/lib/runtime-db";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Validation start date — clean DSF V3 physics era
const VALIDATION_START = "2026-04-06";

function safeFloat(v: unknown): number | null {
  if (v === null || v === undefined) return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function pct(num: number, denom: number): number | null {
  if (denom === 0) return null;
  return Math.round((num / denom) * 10000) / 100;
}

export async function GET() {
  const user = await getCurrentServerUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  if (user.role !== "admin") return NextResponse.json({ error: "Forbidden" }, { status: 403 });

  const pool = resolveRuntimePostgresPool();

  try {
    // ── Portfolio snapshot ───────────────────────────────────────────────
    const configRes = await pool.query<{ key: string; value: string }>(
      `SELECT key, value FROM pee1_execution_config`
    );
    const config: Record<string, string> = {};
    for (const r of configRes.rows) config[r.key] = r.value;

    // ── Open positions ──────────────────────────────────────────────────
    const openRes = await pool.query(`
      SELECT signal_class, status, COUNT(*) as cnt,
             SUM(CASE WHEN entry_filled_price IS NOT NULL THEN
               (CAST(shares AS NUMERIC) * CAST(entry_filled_price AS NUMERIC)) ELSE 0 END) as invested
      FROM personal_trade_ledger
      WHERE status IN ('submitted', 'filled')
      GROUP BY signal_class, status
    `);

    // ── Closed positions (for expectancy) ───────────────────────────────
    const closedRes = await pool.query(`
      SELECT id, ticker, signal_class, entry_filled_price, exit_filled_price,
             shares, p_l, p_l_pct, exit_reason, exit_filled_at, created_at
      FROM personal_trade_ledger
      WHERE status = 'closed' AND p_l IS NOT NULL
      ORDER BY exit_filled_at DESC
    `);

    const closedTrades = closedRes.rows;

    // Fence CH3 from CH1/CH2 validation — separate tracks
    const closedCh1Ch2 = closedTrades.filter(r => (r.signal_class ?? "CH2") !== "CH3");
    const closedCh3 = closedTrades.filter(r => r.signal_class === "CH3");

    // Administrative closures — excluded from win/loss scoring
    const ADMIN_EXIT_REASONS = ["stale_position_cleanup", "manual_close_stale"];
    const closedStrategy = closedCh1Ch2.filter(r => !ADMIN_EXIT_REASONS.includes(r.exit_reason));
    const adminClosures = closedCh1Ch2.length - closedStrategy.length;

    // Primary validation: CH1/CH2 strategy trades only
    const wins = closedStrategy.filter(r => safeFloat(r.p_l)! > 0);
    const losses = closedStrategy.filter(r => safeFloat(r.p_l)! <= 0);

    const winRate = pct(wins.length, closedStrategy.length);
    const avgWinPct = wins.length > 0
      ? wins.reduce((s, r) => s + (safeFloat(r.p_l_pct) ?? 0), 0) / wins.length
      : 0;
    const avgLossPct = losses.length > 0
      ? Math.abs(losses.reduce((s, r) => s + (safeFloat(r.p_l_pct) ?? 0), 0) / losses.length)
      : 0;

    // Mathematical Expectancy: E = (W × AvgW) - (L × AvgL)
    const winRateDecimal = wins.length / Math.max(closedStrategy.length, 1);
    const lossRateDecimal = losses.length / Math.max(closedStrategy.length, 1);
    const expectancy = (winRateDecimal * avgWinPct / 100) - (lossRateDecimal * avgLossPct / 100);

    const totalRealizedPL = closedCh1Ch2.reduce((s, r) => s + (safeFloat(r.p_l) ?? 0), 0);

    // CH3 separate validation track
    const ch3Wins = closedCh3.filter(r => safeFloat(r.p_l)! > 0);
    const ch3Losses = closedCh3.filter(r => safeFloat(r.p_l)! <= 0);
    const ch3WinRate = pct(ch3Wins.length, closedCh3.length);
    const ch3TotalPL = closedCh3.reduce((s, r) => s + (safeFloat(r.p_l) ?? 0), 0);

    // ── Exit breakdown ──────────────────────────────────────────────────
    const exitRes = await pool.query(`
      SELECT exit_reason, COUNT(*) as cnt,
             SUM(CAST(p_l AS NUMERIC)) as total_pl,
             AVG(CAST(p_l_pct AS NUMERIC)) as avg_pl_pct
      FROM personal_trade_ledger
      WHERE status = 'closed' AND exit_reason IS NOT NULL
        AND (signal_class IS NULL OR signal_class != 'CH3')
      GROUP BY exit_reason
      ORDER BY cnt DESC
    `);

    // ── Signal activity today ───────────────────────────────────────────
    const todaySignals = await pool.query(`
      SELECT signal_class, status, COUNT(*) as cnt
      FROM personal_trade_ledger
      WHERE created_at::date = CURRENT_DATE
      GROUP BY signal_class, status
      ORDER BY signal_class, status
    `);

    // ── Daily equity history (from refresh runs) ────────────────────────
    const dailyRes = await pool.query(`
      SELECT DISTINCT ON (completed_at::date)
        completed_at::date as day,
        report_status
      FROM runtime_refresh_runs
      WHERE report_status = 'ok' AND completed_at >= $1
      ORDER BY completed_at::date DESC, completed_at DESC
      LIMIT 60
    `, [VALIDATION_START]);

    // ── Structural state ────────────────────────────────────────────────
    const spyRes = await pool.query(`
      SELECT snapshot_row_json->>'D_k' as dk,
             snapshot_row_json->>'S_UF' as s_uf,
             snapshot_row_json->>'regime' as regime
      FROM runtime_decisions_latest WHERE ticker = 'SPY' LIMIT 1
    `);
    const spy = spyRes.rows[0] ?? {};

    const decisionDist = await pool.query(`
      SELECT decision_label, COUNT(*) as cnt
      FROM runtime_decisions_latest
      GROUP BY decision_label
      ORDER BY cnt DESC
    `);

    // ── Accumulate count ────────────────────────────────────────────────
    const accCount = await pool.query(`
      SELECT COUNT(*) as cnt FROM runtime_decisions_latest
      WHERE decision_label = 'Accumulate'
    `);

    // ── All positions for daily P&L breakdown ───────────────────────────
    const allPositions = await pool.query(`
      SELECT ticker, signal_class, status, shares,
             entry_filled_price, exit_filled_price,
             p_l, p_l_pct, exit_reason, created_at, exit_filled_at
      FROM personal_trade_ledger
      WHERE created_at >= $1
      ORDER BY created_at DESC
    `, [VALIDATION_START]);

    // ── Refresh history ─────────────────────────────────────────────────
    const refreshHistory = await pool.query(`
      SELECT run_id, trigger_source, report_status,
             started_at, completed_at,
             EXTRACT(EPOCH FROM (completed_at - started_at)) as duration_seconds,
             rows_written
      FROM runtime_refresh_runs
      WHERE started_at >= $1 AND report_status = 'ok'
      ORDER BY started_at DESC
      LIMIT 30
    `, [VALIDATION_START]);

    // ── Circuit breaker history ─────────────────────────────────────────
    const cbRes = await pool.query(`
      SELECT triggered_at, expires_at, cleared_at, trigger_reason,
             drawdown_pct, threshold_pct
      FROM pee1_circuit_breaker
      ORDER BY triggered_at DESC
      LIMIT 10
    `);

    // ── Fundamentals coverage ───────────────────────────────────────────
    const fundCoverage = await pool.query(`
      SELECT
        COUNT(*) FILTER (WHERE r.decision_label = 'Accumulate') as total_accumulate,
        COUNT(*) FILTER (WHERE r.decision_label = 'Accumulate' AND f.gross_profit IS NOT NULL
          AND f.current_ratio IS NOT NULL AND f.free_cash_flow IS NOT NULL
          AND f.gross_margin IS NOT NULL AND f.operating_cash_flow IS NOT NULL
          AND f.revenues IS NOT NULL AND f.sector IS NOT NULL AND f.sector != 'Unknown') as with_fundamentals
      FROM runtime_decisions_latest r
      LEFT JOIN l5_fundamentals_normalized f ON f.ticker = r.ticker
    `);

    // ── Validation day count ────────────────────────────────────────────
    const daysSinceStart = Math.floor(
      (Date.now() - new Date(VALIDATION_START).getTime()) / (1000 * 60 * 60 * 24)
    );

    // ── Compose response ────────────────────────────────────────────────
    const response = {
      generated_at_utc: new Date().toISOString(),
      validation_start: VALIDATION_START,
      validation_day: daysSinceStart,
      milestones: {
        day_10_kinetic_buffer: { target_date: "2026-04-16", days_remaining: Math.max(0, 10 - daysSinceStart) },
        day_30_win_rate: { target_date: "2026-05-06", days_remaining: Math.max(0, 30 - daysSinceStart) },
        day_60_validation_complete: { target_date: "2026-06-05", days_remaining: Math.max(0, 60 - daysSinceStart) },
      },
      structural_state: {
        spy_dk: safeFloat(spy.dk),
        spy_s_uf: safeFloat(spy.s_uf),
        spy_regime: spy.regime ?? "unknown",
        total_accumulate: parseInt(accCount.rows[0]?.cnt ?? "0"),
        decision_distribution: decisionDist.rows.map(r => ({
          label: r.decision_label,
          count: parseInt(r.cnt),
        })),
      },
      portfolio: {
        open_positions: openRes.rows.map(r => ({
          signal_class: r.signal_class,
          status: r.status,
          count: parseInt(r.cnt),
          invested: Math.round(safeFloat(r.invested) ?? 0),
        })),
        total_open: openRes.rows.reduce((s, r) => s + parseInt(r.cnt), 0),
        execution_mode: config.execution_mode ?? "paper",
        auto_tfe: config.auto_tfe_enabled ?? "true",
        risk_per_trade: config.risk_per_trade_pct ?? "1.5",
      },
      expectancy: {
        value: Math.round(expectancy * 100000) / 100000,
        target: 0.052,
        threshold: 0.02,
        status: closedStrategy.length < 10
          ? "insufficient_data"
          : expectancy >= 0.052 ? "exceeds_target"
          : expectancy >= 0.02 ? "above_threshold"
          : expectancy > 0 ? "positive_but_below_threshold"
          : "negative",
        note: "CH1/CH2 strategy trades only — admin closures and CH3 excluded",
        closed_trades: closedStrategy.length,
        admin_closures: adminClosures,
        win_rate: winRate,
        avg_win_pct: Math.round(avgWinPct * 100) / 100,
        avg_loss_pct: Math.round(avgLossPct * 100) / 100,
        total_realized_pl: Math.round(totalRealizedPL * 100) / 100,
        wins: wins.length,
        losses: losses.length,
      },
      ch3_validation: {
        note: "CH3 (Scalp) — separate development track, not part of primary validation",
        closed_trades: closedCh3.length,
        win_rate: ch3WinRate,
        wins: ch3Wins.length,
        losses: ch3Losses.length,
        total_realized_pl: Math.round(ch3TotalPL * 100) / 100,
      },
      exits: exitRes.rows.map(r => ({
        reason: r.exit_reason,
        count: parseInt(r.cnt),
        total_pl: Math.round(safeFloat(r.total_pl) ?? 0),
        avg_pl_pct: Math.round((safeFloat(r.avg_pl_pct) ?? 0) * 100) / 100,
      })),
      signals_today: todaySignals.rows.map(r => ({
        signal_class: r.signal_class,
        status: r.status,
        count: parseInt(r.cnt),
      })),
      positions: allPositions.rows.map(r => ({
        ticker: r.ticker,
        signal_class: r.signal_class,
        status: r.status,
        shares: safeFloat(r.shares),
        entry: safeFloat(r.entry_filled_price),
        exit: safeFloat(r.exit_filled_price),
        p_l: safeFloat(r.p_l),
        p_l_pct: safeFloat(r.p_l_pct),
        exit_reason: r.exit_reason,
        created_at: r.created_at,
        exit_at: r.exit_filled_at,
      })),
      refresh_history: refreshHistory.rows.map(r => ({
        run_id: r.run_id,
        trigger: r.trigger_source,
        status: r.report_status,
        started: r.started_at,
        completed: r.completed_at,
        duration_seconds: Math.round(safeFloat(r.duration_seconds) ?? 0),
        rows: safeFloat(r.rows_written),
      })),
      circuit_breaker_events: cbRes.rows,
      fundamentals: {
        total_accumulate: parseInt(fundCoverage.rows[0]?.total_accumulate ?? "0"),
        with_complete_data: parseInt(fundCoverage.rows[0]?.with_fundamentals ?? "0"),
        coverage_pct: pct(
          parseInt(fundCoverage.rows[0]?.with_fundamentals ?? "0"),
          parseInt(fundCoverage.rows[0]?.total_accumulate ?? "1")
        ),
      },
    };

    return NextResponse.json(response);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
