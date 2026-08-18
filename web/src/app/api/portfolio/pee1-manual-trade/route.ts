import { NextResponse } from "next/server";
import { getCurrentServerUser } from "@/lib/server-auth";

export const dynamic = "force-dynamic";

/**
 * A filled ledger position may only be derived from observed broker custody.
 * This endpoint previously manufactured a filled holding without a broker
 * order, producing a knowingly false portfolio record.
 */
export async function POST() {
  const user = await getCurrentServerUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  if (user.role !== "admin") return NextResponse.json({ error: "Forbidden" }, { status: 403 });

  return NextResponse.json(
    {
      error: "ledger_only_trade_creation_disabled",
      message: "Filled ledger positions must be reconciled from observed Alpaca custody.",
    },
    { status: 409 },
  );
}
