import { NextResponse } from "next/server";
import { evaluateRuntimeHealth } from "@/lib/runtime-health";

export const dynamic = "force-dynamic";

export async function GET() {
  const result = await evaluateRuntimeHealth();
  return NextResponse.json(
    {
      status: result.healthy ? "healthy" : "unhealthy",
      checked_at_utc: result.checkedAtUtc,
      generation_id: result.generationId,
      checks: {
        process_heartbeat: result.checks.processHeartbeat,
        database: result.checks.database,
        snapshot_receipts: result.checks.snapshotReceipts,
      },
    },
    {
      status: result.healthy ? 200 : 503,
      headers: { "Cache-Control": "no-store" },
    },
  );
}
