import { NextResponse } from "next/server";
import { getCurrentServerUser } from "@/lib/server-auth";
import {
  fetchAlpacaCustody,
  reconcileCustody,
  type ExecutionMode,
  type LedgerOpenPosition,
} from "@/lib/alpaca-custody";
import { resolveRuntimePostgresPool } from "@/lib/runtime-db";


export const dynamic = "force-dynamic";


type LedgerSummaryRow = LedgerOpenPosition & {
  exit_filled_price: string | null;
  p_l: string | null;
  p_l_pct: string | null;
  exit_reason: string | null;
  exit_filled_at: string | null;
};


const ADMIN_EXIT_REASONS = new Set([
  "stale_position_cleanup",
  "manual_close_stale",
  "manual_portfolio_reset",
  "manual_profit_take",
]);


function executionMode(value: string | undefined): ExecutionMode {
  if (value === "paper") return value;
  throw new Error(`execution_mode_not_authorized:${value ?? "missing"}`);
}


function numberOrNull(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}


function rounded(value: number | null): number | null {
  return value === null ? null : Math.round(value * 100) / 100;
}


function completeSum(values: Array<number | null>): number | null {
  if (values.some((value) => value === null)) return null;
  return values.reduce<number>((sum, value) => sum + (value ?? 0), 0);
}


export async function GET() {
  const user = await getCurrentServerUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  if (user.role !== "admin") return NextResponse.json({ error: "Forbidden" }, { status: 403 });

  const pool = resolveRuntimePostgresPool();
  try {
    const [configResult, ledgerResult] = await Promise.all([
      pool.query<{ key: string; value: string }>(
        `SELECT key, value FROM pee1_execution_config`,
      ),
      pool.query<LedgerSummaryRow>(
        `SELECT id, ticker, signal_class, shares, status,
                entry_filled_price, entry_filled_at, exit_filled_price,
                dollar_allocation, p_l, p_l_pct, exit_reason,
                signal_detected_at, exit_filled_at, alpaca_order_id,
                atr_14, spy_dk, s_uf, bar_count
         FROM personal_trade_ledger
         ORDER BY signal_detected_at DESC`,
      ),
    ]);
    const config = Object.fromEntries(configResult.rows.map((row) => [row.key, row.value]));
    const mode = executionMode(config.execution_mode);
    const fundedAmount = numberOrNull(config.vault_funded_amount);
    if (fundedAmount === null || fundedAmount <= 0) throw new Error("vault_funded_amount_missing_or_invalid");
    const baseline = numberOrNull(config.pl_reset_baseline) ?? fundedAmount;
    const openLedgerRows = ledgerResult.rows.filter((row) => row.status === "submitted" || row.status === "filled");
    const closedTrades = ledgerResult.rows.filter((row) => row.status === "closed");

    const broker = await fetchAlpacaCustody(mode);
    const custody = reconcileCustody(openLedgerRows, broker.positions, broker.openOrders);
    const accountEquity = broker.account?.equity ?? broker.account?.portfolioValue ?? null;
    const brokerCash = broker.account?.cash ?? null;
    const brokerGrossMarketValue = broker.positions === null
      ? null
      : completeSum(broker.positions.map((position) => position.marketValue === null ? null : Math.abs(position.marketValue)));
    const brokerUnrealized = broker.positions === null
      ? null
      : completeSum(broker.positions.map((position) => position.unrealizedPnl));
    const totalPnl = accountEquity === null || baseline <= 0 ? null : accountEquity - baseline;
    const totalPnlPct = totalPnl === null || baseline <= 0 ? null : 100 * totalPnl / baseline;

    const ledgerRealized = closedTrades.reduce((sum, row) => sum + (numberOrNull(row.p_l) ?? 0), 0);
    const closedCh1Ch2 = closedTrades.filter((row) => row.signal_class !== "CH3");
    const closedStrategy = closedCh1Ch2.filter((row) => !ADMIN_EXIT_REASONS.has(row.exit_reason ?? ""));
    const wins = closedStrategy.filter((row) => (numberOrNull(row.p_l) ?? 0) > 0).length;
    const losses = closedStrategy.filter((row) => (numberOrNull(row.p_l) ?? 0) < 0).length;
    const winRate = wins + losses > 0 ? `${(100 * wins / (wins + losses)).toFixed(1)}%` : "n/a";
    const closedCh3 = closedTrades.filter((row) => row.signal_class === "CH3");
    const realizedCh1Ch2 = closedCh1Ch2.reduce((sum, row) => sum + (numberOrNull(row.p_l) ?? 0), 0);
    const realizedCh3 = closedCh3.reduce((sum, row) => sum + (numberOrNull(row.p_l) ?? 0), 0);

    const exitReasons: Record<string, number> = {};
    for (const trade of closedTrades) {
      if (trade.exit_reason) exitReasons[trade.exit_reason] = (exitReasons[trade.exit_reason] ?? 0) + 1;
    }

    const recentClosedTrades = closedTrades
      .filter((row) => row.exit_filled_price && row.entry_filled_price && row.p_l !== null)
      .sort((left, right) => String(right.exit_filled_at ?? "").localeCompare(String(left.exit_filled_at ?? "")))
      .slice(0, 30)
      .map((row) => ({
        ticker: row.ticker,
        signal_class: row.signal_class ?? "—",
        shares: Number(row.shares),
        entry: numberOrNull(row.entry_filled_price),
        exit: numberOrNull(row.exit_filled_price),
        pnl: rounded(numberOrNull(row.p_l)),
        pnl_pct: rounded(numberOrNull(row.p_l_pct)),
        exit_reason: row.exit_reason ?? "—",
        closed_at: row.exit_filled_at,
      }));

    return NextResponse.json({
      funded_amount: fundedAmount,
      cash_on_hand: rounded(brokerCash),
      total_invested: rounded(brokerGrossMarketValue),
      portfolio_value: rounded(accountEquity),
      total_pl: rounded(totalPnl),
      total_pl_pct: rounded(totalPnlPct),
      pl_baseline: baseline,
      pl_method: "alpaca_equity_minus_recorded_reset_baseline",
      total_realized: null,
      total_realized_status: "unavailable_from_broker_account_endpoint",
      ledger_realized: rounded(ledgerRealized),
      total_realized_ch1ch2: rounded(realizedCh1Ch2),
      total_realized_ch3: rounded(realizedCh3),
      total_unrealized: rounded(brokerUnrealized),
      open_positions: broker.positions?.length ?? null,
      ledger_open_positions: custody.summary.ledgerSymbols,
      open_orders: broker.openOrders?.length ?? null,
      total_trades: ledgerResult.rows.length,
      closed_trades: closedTrades.length,
      closed_trades_ch1ch2: closedCh1Ch2.length,
      closed_trades_ch3: closedCh3.length,
      wins,
      losses,
      win_rate: winRate,
      win_rate_note: "Ledger CH1/CH2 resolved strategy rows only; not broker custody performance.",
      exit_reasons: exitReasons,
      recent_closed_trades: recentClosedTrades,
      execution_mode: mode,
      auto_tfe_enabled: config.auto_tfe_enabled === "true",
      entries_halted:
        process.env.TFE_ENTRIES_HALTED === "1"
        || config.entries_halted === "true"
        || config.auto_tfe_enabled !== "true",
      risk_per_trade_pct: numberOrNull(config.risk_per_trade_pct) ?? 1.5,
      alpaca_equity: rounded(accountEquity),
      alpaca_cash: rounded(brokerCash),
      broker_status: broker.status,
      broker_reasons: broker.reasons,
      broker_as_of: broker.fetchedAt,
      custody: custody.summary,
      custody_positions: custody.positions,
      value_sources: {
        portfolio_value: "Alpaca account equity",
        cash_on_hand: "Alpaca account cash",
        total_invested: "absolute Alpaca position market value",
        total_unrealized: "sum of Alpaca position unrealized P&L; unavailable if any mark is absent",
        total_realized: "not supplied by the Alpaca account endpoint; ledger value is separately labeled",
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (message.includes("does not exist")) {
      return NextResponse.json({ error: "tables_not_initialized" }, { status: 503 });
    }
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
