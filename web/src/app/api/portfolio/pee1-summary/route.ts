import { NextRequest, NextResponse } from "next/server";
import { readSessionUserFromRequest } from "@/lib/auth-session";
import { resolveRuntimePostgresPool } from "@/lib/runtime-db";

export const dynamic = "force-dynamic";

function alpacaHeaders() {
  return {
    "APCA-API-KEY-ID": process.env.ALPACA_API_KEY ?? "",
    "APCA-API-SECRET-KEY": process.env.ALPACA_SECRET_KEY ?? "",
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
    const params = tickers.map(t => `symbols=${encodeURIComponent(t)}`).join("&");
    const res = await fetch(`https://data.alpaca.markets/v2/stocks/snapshots?${params}&feed=iex`, {
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
  const user = await readSessionUserFromRequest(request);
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
        entry_filled_price: string | null;
        exit_filled_price: string | null;
        dollar_allocation: string | null;
        p_l: string | null;
        p_l_pct: string | null;
        exit_reason: string | null;
        signal_detected_at: string;
      }>(
        `SELECT id, ticker, shares, status,
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
    const closedTrades = ledgerRes.rows.filter(r => r.status === "closed");

    // Fetch current prices for open positions
    const openTickers = [...new Set(openTrades.map(r => r.ticker))];
    const prices = await fetchCurrentPrices(openTickers);

    // Unrealized P&L from open positions
    let totalUnrealized = 0;
    let totalInvested = 0;
    for (const trade of openTrades) {
      const entry = parseFloat(trade.entry_filled_price ?? "0") || 0;
      const shares = Number(trade.shares) || 0;
      const current = prices[trade.ticker] ?? entry;
      totalUnrealized += (current - entry) * shares;
      totalInvested += entry * shares;
    }

    // Realized P&L from closed trades
    const totalRealized = closedTrades.reduce((sum, r) => sum + (parseFloat(r.p_l ?? "0") || 0), 0);
    const totalPl = totalRealized + totalUnrealized;

    const wins = closedTrades.filter(r => (parseFloat(r.p_l ?? "0") || 0) > 0).length;
    const losses = closedTrades.filter(r => (parseFloat(r.p_l ?? "0") || 0) < 0).length;
    const winRate = wins + losses > 0 ? ((wins / (wins + losses)) * 100).toFixed(1) + "%" : "n/a";

    const exitReasons: Record<string, number> = {};
    for (const t of closedTrades) {
      if (t.exit_reason) exitReasons[t.exit_reason] = (exitReasons[t.exit_reason] ?? 0) + 1;
    }

    const cashOnHand = fundedAmount - totalInvested;
    const portfolioValue = cashOnHand + totalInvested + totalUnrealized;
    const totalPlPct = fundedAmount > 0 ? (totalPl / fundedAmount) * 100 : null;

    // Try to get Alpaca account equity for validation
    const alpacaAccount = await fetchAlpacaAccount(executionMode);

    return NextResponse.json({
      funded_amount: fundedAmount,
      cash_on_hand: Math.round(cashOnHand * 100) / 100,
      total_invested: Math.round(totalInvested * 100) / 100,
      portfolio_value: Math.round(portfolioValue * 100) / 100,
      total_pl: Math.round(totalPl * 100) / 100,
      total_pl_pct: totalPlPct !== null ? Math.round(totalPlPct * 100) / 100 : null,
      total_realized: Math.round(totalRealized * 100) / 100,
      total_unrealized: Math.round(totalUnrealized * 100) / 100,
      open_positions: openTrades.length,
      total_trades: ledgerRes.rows.length,
      closed_trades: closedTrades.length,
      wins,
      losses,
      win_rate: winRate,
      exit_reasons: exitReasons,
      execution_mode: executionMode,
      auto_tfe_enabled: configMap.auto_tfe_enabled === "true",
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
