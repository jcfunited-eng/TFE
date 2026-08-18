import { NextResponse } from "next/server";
import { getCurrentServerUser } from "@/lib/server-auth";

export const dynamic = "force-dynamic";

/**
 * Manual broker submission is deliberately unavailable.
 *
 * The former implementation could create a broker order before its custody
 * record existed, had no idempotency boundary, and bypassed the supervised
 * entry halt. Only sentinel_daemon.mjs may originate TFE orders until a
 * transactional broker/ledger command architecture is implemented.
 */
export async function POST() {
  const user = await getCurrentServerUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  if (user.role !== "admin") return NextResponse.json({ error: "Forbidden" }, { status: 403 });

  return NextResponse.json(
    {
      error: "manual_order_execution_disabled",
      message: "Manual broker orders are disabled. The supervised automatic paper pipeline is the only authorized order origin.",
    },
    { status: 409 },
  );
}
