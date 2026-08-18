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


function executionMode(value: string | undefined): ExecutionMode {
  if (value === "paper" || value === "live") return value;
  throw new Error("execution_mode_missing_or_invalid");
}


export async function GET() {
  const user = await getCurrentServerUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  if (user.role !== "admin") return NextResponse.json({ error: "Forbidden" }, { status: 403 });

  const pool = resolveRuntimePostgresPool();
  try {
    const [positionResult, modeResult] = await Promise.all([
      pool.query<LedgerOpenPosition>(
        `SELECT id, ticker, signal_class, shares,
                entry_filled_price, dollar_allocation, atr_14,
                spy_dk, s_uf, bar_count, status,
                signal_detected_at, entry_filled_at, alpaca_order_id
         FROM personal_trade_ledger
         WHERE status IN ('submitted', 'filled')
         ORDER BY signal_detected_at DESC`,
      ),
      pool.query<{ value: string }>(
        `SELECT value FROM pee1_execution_config WHERE key = 'execution_mode' LIMIT 1`,
      ),
    ]);
    const mode = executionMode(modeResult.rows[0]?.value);
    const broker = await fetchAlpacaCustody(mode);
    const custody = reconcileCustody(positionResult.rows, broker.positions, broker.openOrders);

    return NextResponse.json({
      positions: custody.positions,
      execution_mode: mode,
      custody: custody.summary,
      broker_status: broker.status,
      broker_position_status: broker.positionsStatus,
      broker_order_status: broker.ordersStatus,
      broker_reasons: broker.reasons,
      as_of: broker.fetchedAt,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (message.includes("does not exist")) {
      return NextResponse.json({ error: "tables_not_initialized" }, { status: 503 });
    }
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
