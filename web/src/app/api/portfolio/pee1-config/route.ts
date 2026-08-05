import { NextRequest, NextResponse } from "next/server";
import { getCurrentServerUser } from "@/lib/server-auth";
import { resolveRuntimePostgresPool } from "@/lib/runtime-db";

export const dynamic = "force-dynamic";

const ALLOWED_KEYS = ["execution_mode", "auto_tfe_enabled", "vault_funded_amount", "risk_per_trade_pct"] as const;
type ConfigKey = (typeof ALLOWED_KEYS)[number];

async function requireAdminUser(request: NextRequest) {
  const user = await getCurrentServerUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  if (user.role !== "admin") return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  return null;
}

export async function GET(request: NextRequest) {
  const authError = await requireAdminUser(request);
  if (authError) return authError;

  const pool = resolveRuntimePostgresPool();
  try {
    const res = await pool.query<{ key: string; value: string }>(
      `SELECT key, value FROM pee1_execution_config WHERE key = ANY($1)`,
      [ALLOWED_KEYS]
    );
    const config: Record<string, string | boolean | number> = {
      execution_mode: "paper",
      auto_tfe_enabled: true,
      vault_funded_amount: 0,
      risk_per_trade_pct: 1.5,
    };
    for (const row of res.rows) {
      if (row.key === "auto_tfe_enabled") {
        config[row.key] = row.value === "true";
      } else if (row.key === "vault_funded_amount" || row.key === "risk_per_trade_pct") {
        config[row.key] = parseFloat(row.value) || 0;
      } else {
        config[row.key] = row.value;
      }
    }
    return NextResponse.json(config);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    if (msg.includes("does not exist")) {
      return NextResponse.json({ error: "tables_not_initialized" }, { status: 503 });
    }
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  const authError = await requireAdminUser(request);
  if (authError) return authError;

  let body: Partial<Record<ConfigKey, string | boolean | number>>;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const pool = resolveRuntimePostgresPool();
  try {
    for (const key of ALLOWED_KEYS) {
      if (!(key in body)) continue;
      const raw = body[key];
      const value = String(raw ?? "");
      await pool.query(
        `INSERT INTO pee1_execution_config (key, value, updated_by)
         VALUES ($1, $2, 'ui')
         ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_by = 'ui'`,
        [key, value]
      );
    }
    return NextResponse.json({ ok: true });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
