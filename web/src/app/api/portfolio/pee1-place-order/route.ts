import { NextRequest, NextResponse } from "next/server";
import { getCurrentServerUser } from "@/lib/server-auth";
import { resolveRuntimePostgresPool } from "@/lib/runtime-db";

export const dynamic = "force-dynamic";

type OrderSide = "buy" | "sell";
type OrderType = "market" | "limit";

interface PlaceOrderBody {
  ticker?: string;
  side?: OrderSide;
  shares?: number;
  order_type?: OrderType;
  limit_price?: number;
  notes?: string;
}

interface AlpacaOrderPayload {
  symbol: string;
  qty: string;
  side: OrderSide;
  type: OrderType;
  time_in_force: string;
  limit_price?: string;
}

function alpacaHeaders() {
  return {
    "APCA-API-KEY-ID": process.env.ALPACA_API_KEY ?? process.env.APCA_API_KEY_ID ?? "",
    "APCA-API-SECRET-KEY": process.env.ALPACA_SECRET_KEY ?? process.env.APCA_API_SECRET_KEY ?? "",
    "Content-Type": "application/json",
  };
}

async function getExecutionMode(pool: ReturnType<typeof resolveRuntimePostgresPool>): Promise<string> {
  try {
    const res = await pool.query<{ value: string }>(
      `SELECT value FROM pee1_execution_config WHERE key = 'execution_mode' LIMIT 1`
    );
    return res.rows[0]?.value ?? "paper";
  } catch {
    return "paper"; // fail-safe
  }
}

async function getCurrentPrice(ticker: string): Promise<number | null> {
  try {
    const res = await fetch(
      `https://data.alpaca.markets/v2/stocks/snapshots?symbols=${encodeURIComponent(ticker)}&feed=iex`,
      { headers: alpacaHeaders() }
    );
    if (!res.ok) return null;
    const data = await res.json() as Record<string, { latestTrade?: { p: number }; latestQuote?: { ap: number } }>;
    const snap = data[ticker];
    return snap?.latestTrade?.p ?? snap?.latestQuote?.ap ?? null;
  } catch {
    return null;
  }
}

export async function POST(request: NextRequest) {
  const user = await getCurrentServerUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  if (user.role !== "admin") return NextResponse.json({ error: "Forbidden" }, { status: 403 });

  let body: PlaceOrderBody;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const ticker = String(body.ticker ?? "").trim().toUpperCase();
  const side = body.side;
  const shares = Number(body.shares);
  const orderType: OrderType = body.order_type === "limit" ? "limit" : "market";
  const limitPrice = body.limit_price ? Number(body.limit_price) : undefined;
  const notes = String(body.notes ?? "").trim() || null;

  if (!ticker) return NextResponse.json({ error: "ticker required" }, { status: 400 });
  if (side !== "buy" && side !== "sell") return NextResponse.json({ error: "side must be 'buy' or 'sell'" }, { status: 400 });
  if (!shares || shares <= 0 || !Number.isFinite(shares)) return NextResponse.json({ error: "shares must be a positive number" }, { status: 400 });
  if (orderType === "limit" && (!limitPrice || limitPrice <= 0)) return NextResponse.json({ error: "limit_price required for limit orders" }, { status: 400 });

  const pool = resolveRuntimePostgresPool();
  const executionMode = await getExecutionMode(pool);
  const alpacaBase = executionMode === "live"
    ? "https://api.alpaca.markets"
    : "https://paper-api.alpaca.markets";

  // Build Alpaca order payload
  const alpacaPayload: AlpacaOrderPayload = {
    symbol: ticker,
    qty: String(shares % 1 === 0 ? Math.round(shares) : shares),
    side,
    type: orderType,
    time_in_force: "day",
  };
  if (orderType === "limit" && limitPrice) {
    alpacaPayload.limit_price = String(limitPrice.toFixed(2));
  }

  // Place order via Alpaca API
  let alpacaOrder: Record<string, unknown>;
  try {
    const alpacaRes = await fetch(`${alpacaBase}/v2/orders`, {
      method: "POST",
      headers: alpacaHeaders(),
      body: JSON.stringify(alpacaPayload),
    });

    const alpacaData = await alpacaRes.json() as Record<string, unknown>;

    if (!alpacaRes.ok) {
      const errMsg = (alpacaData.message as string) ?? (alpacaData.code as string) ?? `Alpaca error ${alpacaRes.status}`;
      return NextResponse.json({ error: errMsg }, { status: 422 });
    }

    alpacaOrder = alpacaData;
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: `Failed to reach Alpaca: ${msg}` }, { status: 502 });
  }

  // Determine entry price for the ledger
  const filledPrice = alpacaOrder.filled_avg_price
    ? Number(alpacaOrder.filled_avg_price)
    : (orderType === "limit" && limitPrice ? limitPrice : null);

  const priceForLedger = filledPrice ?? (await getCurrentPrice(ticker)) ?? 0;
  const dollarAllocation = side === "buy" ? shares * priceForLedger : -(shares * priceForLedger);

  // Write to personal_trade_ledger
  try {
    const status = alpacaOrder.status === "filled" ? "filled" : "submitted";

    await pool.query(
      `INSERT INTO personal_trade_ledger
         (ticker, signal_class, status, shares, entry_filled_price,
          dollar_allocation, alpaca_order_id, signal_detected_at, entry_filled_at,
          rationale_json)
       VALUES ($1, 'manual', $2, $3, $4, $5, $6, NOW(), NOW(), $7)`,
      [
        ticker,
        status,
        side === "sell" ? -Math.abs(shares) : shares,
        priceForLedger > 0 ? priceForLedger : null,
        side === "buy" ? Math.abs(dollarAllocation) : -Math.abs(dollarAllocation),
        String(alpacaOrder.id ?? ""),
        JSON.stringify({
          source: "manual_order",
          side,
          order_type: orderType,
          execution_mode: executionMode,
          alpaca_order_id: alpacaOrder.id ?? null,
          notes,
          entered_by: user.username ?? "user",
        }),
      ]
    );
  } catch (err) {
    // Order was placed but ledger write failed — log and still return success
    console.error("[PLACE-ORDER] Ledger write failed:", err instanceof Error ? err.message : err);
    return NextResponse.json({
      ok: true,
      warning: "Order placed on Alpaca but ledger write failed — refresh the portfolio page.",
      alpaca_order_id: String(alpacaOrder.id ?? ""),
      alpaca_status: String(alpacaOrder.status ?? ""),
    });
  }

  return NextResponse.json({
    ok: true,
    alpaca_order_id: String(alpacaOrder.id ?? ""),
    alpaca_status: String(alpacaOrder.status ?? ""),
    execution_mode: executionMode,
  });
}
