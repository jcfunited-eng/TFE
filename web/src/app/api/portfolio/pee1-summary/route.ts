import { NextRequest, NextResponse } from "next/server";
import { getCurrentServerUser } from "@/lib/server-auth";
import { resolveRuntimePostgresPool } from "@/lib/runtime-db";

export const dynamic = "force-dynamic";

function alpacaHeaders() {
  return {
    "APCA-API-KEY-ID": process.env.APCA_API_KEY_ID ?? process.env.ALPACA_API_KEY ?? "",
    "APCA-API-SECRET-KEY": process.env.APCA_API_SECRET_KEY ?? process.env.ALPACA_SECRET_KEY ?? "",
  };
}

async function fetchAlpacaAccount(executionMode: string): Promise<{ equity: number; cash: number } | null> {
  const base = executionMode === "live"
    ? "https://api.alpaca.markets"
    : "https://paper-api.alpaca.markets";
  try {
    const res = await fetch(`${base}/v2/account`, { headers: alpacaHeaders() });
    if (!res.ok) return null;
    const data = await res.json() as { equity?: string; cash?: string };
    return {
      equity: parseFloat(data.equity ?? "0") || 0,
      cash: parseFloat(data.cash ?? "0") || 0,
    };
  } catch {
    return null;
  }
}

async function fetchCurrentPrices(tickers: string[]): Promise<Record<string, number>> {
  if (!tickers.length) return {};
  try {
    const symbolList = tickers.map(t => encodeURIComponent(t)).join(",");
    const res = await fetch(`https://data.alpaca.markets/v2/stocks/snapshots?symbols=${symbolList}&feed=iex`, {
      headers: alpacaHeaders(),
    });
    if (!res.ok) return {};
    const data = await res.json() as Record<string, { latestTrade?: { p: number }; latestQuote?: { ap: number } }>;
    const prices: Record<string, number> = {};
    for (const [ticker, snap] of Object.entries(data)) {
      const price = snap?.latestTrade?.p ?? snap?.latestQuote?.ap ?? null;
      if (price && price > 0) prices[ticker] = price;
    }
    return prices;
  } catch {
    return {};
  }
}

export async function GET(request: NextRequest) {
  const user = await getCurrentServerUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  if (user.role !== "admin") return NextResponse.json({ error: "Forbidden" }, { status: 403 });

  const pool = resolveRuntimePostgresPool();
  try {
    const [configRes, ledgerRes] = await Promise.all([
      pool.query<{ key: string; value: string }>(
        `SELECT key, value FROM pee1_execution_config`
      ),
      pool.query<{
        id: number;
        ticker: string;
        shares: number;
        status: string;
        signal_class: string | null;
        entry_filled_price: string | null;
        exit_filled_price: string | null;
        dollar_allocation: string | null;
        p_l: string | null;
        p_l_pct: string | null;
        exit_reason: string | null;
        signal_detected_at: string;
      }>(
        `SELECT id, ticker, shares, status, signal_class,
                entry_filled_price, exit_filled_price, dollar_allocation,
                p_l, p_l_pct, exit_reason, signal_detected_at
         FROM personal_trade_ledger
         ORDER BY signal_detected_at DESC`
      ),
    ]);

    const configMap: Record<string, string> = {};
    for (const row of configRes.rows) configMap[row.key] = row.value;

    const fundedAmount = parseFloat(configMap.vault_funded_amount ?? "0") || 0;
    const executionMode = configMap.execution_mode ?? "paper";

    const openTrades = ledgerRes.rows.filter(r => ["submitted", "filled"].includes(r.status));
    const filledTrades = ledgerRes.rows.filter(r => r.status === "filled" && r.entry_filled_price);
    const closedTrades = ledgerRes.rows.filter(r => r.status === "closed");

    // Fetch current prices for filled (active) positions only
    const filledTickers = [...new Set(filledTrades.map(r => r.ticker))];
    const prices = await fetchCurrentPrices(filledTickers);

    // Unrealized P&L from filled positions only (submitted = pending, no fill yet)
    let totalUnrealized = 0;
    let totalInvested = 0;
    for (const trade of filledTrades) {
      const entry = parseFloat(trade.entry_filled_price ?? "0") || 0;
      const shares = Number(trade.shares) || 0;
      const current = prices[trade.ticker] ?? entry;
      totalUnrealized += (current - entry) * shares;
      totalInvested += entry * shares;
    }

    // Realized P&L from all closed trades (for per-trade breakdown)
    const totalRealized = closedTrades.reduce((sum, r) => sum + (parseFloat(r.p_l ?? "0") || 0), 0);

    // Win rate: fence CH3 and admin closures from primary validation
    const ADMIN_EXIT_REASONS = ["stale_position_cleanup", "manual_close_stale", "manual_portfolio_reset"];
    const closedCh1Ch2 = closedTrades.filter(r => r.signal_class !== "CH3");
    const closedStrategy = closedCh1Ch2.filter(r => !ADMIN_EXIT_REASONS.includes(r.exit_reason ?? ""));
    const wins = closedStrategy.filter(r => (parseFloat(r.p_l ?? "0") || 0) > 0).length;
    const losses = closedStrategy.filter(r => (parseFloat(r.p_l ?? "0") || 0) < 0).length;
    const winRate = wins + losses > 0 ? ((wins / (wins + losses)) * 100).toFixed(1) + "%" : "n/a";

    const exitReasons: Record<string, number> = {};
    for (const t of closedTrades) {
      if (t.exit_reason) exitReasons[t.exit_reason] = (exitReasons[t.exit_reason] ?? 0) + 1;
    }

    const cashOnHand = fundedAmount - totalInvested;

    // Try to get Alpaca account equity — use as ground truth for portfolio value and P&L.
    // The DB-calculated P&L has gaps (null exit prices on bracket exits, delisted tickers).
    // Alpaca equity is the actual dollar amount in the account right now.
    const alpacaAccount = await fetchAlpacaAccount(executionMode);

    const portfolioValue = alpacaAccount?.equity
      ?? Math.round((cashOnHand + totalInvested + totalUnrealized) * 100) / 100;
    const totalPl = alpacaAccount
      ? alpacaAccount.equity - fundedAmount
      : totalRealized + totalUnrealized;
    const totalPlPct = fundedAmount > 0 ? (totalPl / fundedAmount) * 100 : null;

    // Realized P&L split: CH1/CH2 vs CH3
    const realizedCh1Ch2 = closedCh1Ch2.reduce((sum, r) => sum + (parseFloat(r.p_l ?? "0") || 0), 0);
    const closedCh3 = closedTrades.filter(r => r.signal_class === "CH3");
    const realizedCh3 = closedCh3.reduce((sum, r) => sum + (parseFloat(r.p_l ?? "0") || 0), 0);

    const recentClosedTrades = closedTrades
      .filter(r => r.exit_filled_price && r.entry_filled_price && r.p_l !== null)
      .sort((a, b) => (b.signal_detected_at > a.signal_detected_at ? 1 : -1))
      .slice(0, 30)
      .map(r => ({
        ticker: r.ticker,
        signal_class: r.signal_class ?? "—",
        shares: Number(r.shares),
        entry: parseFloat(r.entry_filled_price ?? "0"),
        exit: parseFloat(r.exit_filled_price ?? "0"),
        pnl: Math.round(parseFloat(r.p_l ?? "0") * 100) / 100,
        pnl_pct: r.p_l_pct ? Math.round(parseFloat(r.p_l_pct) * 100) / 100 : null,
        exit_reason: r.exit_reason ?? "—",
        closed_at: r.signal_detected_at,
      }));

    return NextResponse.json({
      funded_amount: fundedAmount,
      cash_on_hand: Math.round(cashOnHand * 100) / 100,
      total_invested: Math.round(totalInvested * 100) / 100,
      portfolio_value: Math.round(portfolioValue * 100) / 100,
      total_pl: Math.round(totalPl * 100) / 100,
      total_pl_pct: totalPlPct !== null ? Math.round(totalPlPct * 100) / 100 : null,
      total_realized: Math.round(totalRealized * 100) / 100,
      total_realized_ch1ch2: Math.round(realizedCh1Ch2 * 100) / 100,
      total_realized_ch3: Math.round(realizedCh3 * 100) / 100,
      total_unrealized: Math.round(totalUnrealized * 100) / 100,
      open_positions: openTrades.length,
      total_trades: ledgerRes.rows.length,
      closed_trades: closedTrades.length,
      closed_trades_ch1ch2: closedCh1Ch2.length,
      closed_trades_ch3: closedCh3.length,
      wins,
      losses,
      win_rate: winRate,
      win_rate_note: "CH1/CH2 only — CH3 on separate track",
      exit_reasons: exitReasons,
      recent_closed_trades: recentClosedTrades,
      execution_mode: executionMode,
      auto_tfe_enabled: configMap.auto_tfe_enabled === "true",
      entries_halted: process.env.TFE_ENTRIES_HALTED === "1" || configMap.entries_halted === "true",
      risk_per_trade_pct: parseFloat(configMap.risk_per_trade_pct ?? "1.5") || 1.5,
      alpaca_equity: alpacaAccount?.equity ?? null,
      alpaca_cash: alpacaAccount?.cash ?? null,
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    if (msg.includes("does not exist")) {
      return NextResponse.json({ error: "tables_not_initialized" }, { status: 503 });
    }
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
