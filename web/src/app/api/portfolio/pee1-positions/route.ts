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

async function fetchCurrentPrices(tickers: string[], executionMode: string): Promise<Record<string, number>> {
  if (!tickers.length) return {};
  const base = executionMode === "live"
    ? "https://api.alpaca.markets"
    : "https://paper-api.alpaca.markets";
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
    // Suppress unused variable warning
    void base;
    return prices;
  } catch {
    return {};
  }
}

async function getExecutionMode(pool: ReturnType<typeof resolveRuntimePostgresPool>): Promise<string> {
  try {
    const res = await pool.query<{ value: string }>(
      `SELECT value FROM pee1_execution_config WHERE key = 'execution_mode' LIMIT 1`
    );
    return res.rows[0]?.value ?? "paper";
  } catch {
    return "paper";
  }
}

export async function GET(request: NextRequest) {
  const user = await readSessionUserFromRequest(request);
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const pool = resolveRuntimePostgresPool();
  try {
    const [posRes, executionMode] = await Promise.all([
      pool.query<{
        id: number;
        ticker: string;
        signal_class: string;
        shares: number;
        entry_filled_price: string | null;
        dollar_allocation: string | null;
        atr_14: string | null;
        spy_dk: number | null;
        s_uf: string | null;
        bar_count: number | null;
        status: string;
        signal_detected_at: string;
        entry_filled_at: string | null;
        alpaca_order_id: string | null;
      }>(
        `SELECT id, ticker, signal_class, shares,
                entry_filled_price, dollar_allocation, atr_14,
                spy_dk, s_uf, bar_count, status,
                signal_detected_at, entry_filled_at, alpaca_order_id
         FROM personal_trade_ledger
         WHERE status IN ('submitted', 'filled')
         ORDER BY signal_detected_at DESC`
      ),
      getExecutionMode(pool),
    ]);

    const tickers = [...new Set(posRes.rows.map(r => r.ticker))];
    const prices = await fetchCurrentPrices(tickers, executionMode);

    const positions = posRes.rows.map(row => {
      const entryPrice = parseFloat(row.entry_filled_price ?? "0") || null;
      const currentPrice = prices[row.ticker] ?? null;
      const shares = Number(row.shares) || 0;
      const unrealizedPl = entryPrice && currentPrice ? (currentPrice - entryPrice) * shares : null;
      const unrealizedPlPct = entryPrice && unrealizedPl !== null ? (unrealizedPl / (entryPrice * shares)) * 100 : null;
      return {
        id: row.id,
        ticker: row.ticker,
        signal_class: row.signal_class ?? "manual",
        shares,
        entry_price: entryPrice,
        current_price: currentPrice,
        dollar_allocation: parseFloat(row.dollar_allocation ?? "0") || null,
        unrealized_pl: unrealizedPl !== null ? Math.round(unrealizedPl * 100) / 100 : null,
        unrealized_pl_pct: unrealizedPlPct !== null ? Math.round(unrealizedPlPct * 100) / 100 : null,
        status: row.status,
        spy_dk: row.spy_dk,
        s_uf: parseFloat(row.s_uf ?? "0") || null,
        bar_count: row.bar_count,
        signal_detected_at: row.signal_detected_at,
        entry_filled_at: row.entry_filled_at,
        alpaca_order_id: row.alpaca_order_id,
      };
    });

    return NextResponse.json({ positions, execution_mode: executionMode });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    if (msg.includes("does not exist")) {
      return NextResponse.json({ positions: [], execution_mode: "paper", error: "tables_not_initialized" });
    }
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
