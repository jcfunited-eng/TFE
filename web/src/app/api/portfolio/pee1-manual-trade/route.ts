import { NextRequest, NextResponse } from "next/server";
import { readSessionUserFromRequest } from "@/lib/auth-session";
import { resolveRuntimePostgresPool } from "@/lib/runtime-db";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  const user = await readSessionUserFromRequest(request);
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  let body: { ticker?: string; shares?: number; entry_price?: number; notes?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const ticker = String(body.ticker ?? "").trim().toUpperCase();
  const shares = Number(body.shares);
  const entryPrice = Number(body.entry_price);

  if (!ticker) return NextResponse.json({ error: "ticker required" }, { status: 400 });
  if (!shares || shares <= 0) return NextResponse.json({ error: "shares must be > 0" }, { status: 400 });
  if (!entryPrice || entryPrice <= 0) return NextResponse.json({ error: "entry_price must be > 0" }, { status: 400 });

  const dollarAllocation = shares * entryPrice;
  const notes = String(body.notes ?? "").trim() || null;

  const pool = resolveRuntimePostgresPool();
  try {
    const res = await pool.query<{ id: number }>(
      `INSERT INTO personal_trade_ledger
         (ticker, signal_class, status, shares, entry_filled_price,
          dollar_allocation, signal_detected_at, entry_filled_at,
          rationale_json)
       VALUES ($1, 'manual', 'filled', $2, $3, $4, NOW(), NOW(), $5)
       RETURNING id`,
      [
        ticker,
        shares,
        entryPrice,
        dollarAllocation,
        JSON.stringify({ source: "manual_entry", notes, entered_by: user.username ?? "user" }),
      ]
    );
    return NextResponse.json({ ok: true, id: res.rows[0].id });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    if (msg.includes("does not exist")) {
      return NextResponse.json({ error: "tables_not_initialized" }, { status: 503 });
    }
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
