import { NextRequest, NextResponse } from "next/server";
import { getCurrentServerUser } from "@/lib/server-auth";
import { resolveRuntimePostgresPool } from "@/lib/runtime-db";

export const dynamic = "force-dynamic";

const READ_KEYS = ["execution_mode", "auto_tfe_enabled", "vault_funded_amount", "risk_per_trade_pct"] as const;
const WRITE_KEYS = ["execution_mode", "auto_tfe_enabled", "vault_funded_amount"] as const;
type WriteKey = (typeof WRITE_KEYS)[number];

async function requireAdminUser() {
  const user = await getCurrentServerUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  if (user.role !== "admin") return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  return null;
}

function finitePositive(value: unknown, field: string): number {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) throw new Error(`${field}_must_be_positive`);
  return parsed;
}

export async function GET() {
  const authError = await requireAdminUser();
  if (authError) return authError;

  const pool = resolveRuntimePostgresPool();
  try {
    const result = await pool.query<{ key: string; value: string }>(
      `SELECT key, value FROM pee1_execution_config WHERE key = ANY($1)`,
      [READ_KEYS],
    );
    const values = new Map(result.rows.map((row) => [row.key, row.value]));
    const missing = READ_KEYS.filter((key) => !values.has(key));
    if (missing.length > 0) {
      return NextResponse.json({ error: "execution_config_incomplete", missing }, { status: 503 });
    }

    const executionMode = values.get("execution_mode");
    if (executionMode !== "paper") {
      return NextResponse.json(
        { error: "execution_mode_not_authorized", observed: executionMode },
        { status: 503 },
      );
    }
    const autoValue = values.get("auto_tfe_enabled");
    if (autoValue !== "true" && autoValue !== "false") {
      return NextResponse.json({ error: "auto_tfe_enabled_invalid" }, { status: 503 });
    }

    return NextResponse.json({
      execution_mode: "paper",
      auto_tfe_enabled: autoValue === "true",
      vault_funded_amount: finitePositive(values.get("vault_funded_amount"), "vault_funded_amount"),
      risk_per_trade_pct: finitePositive(values.get("risk_per_trade_pct"), "risk_per_trade_pct"),
      live_execution_authorized: false,
      risk_policy: "channel_owned_read_only",
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (message.includes("does not exist")) {
      return NextResponse.json({ error: "tables_not_initialized" }, { status: 503 });
    }
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  const authError = await requireAdminUser();
  if (authError) return authError;

  let body: Record<string, unknown>;
  try {
    body = await request.json() as Record<string, unknown>;
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const keys = Object.keys(body);
  const unsupported = keys.filter((key) => !WRITE_KEYS.includes(key as WriteKey));
  if (unsupported.length > 0) {
    return NextResponse.json(
      { error: "execution_config_key_not_editable", keys: unsupported },
      { status: 400 },
    );
  }
  if (keys.length === 0) return NextResponse.json({ error: "no_config_values" }, { status: 400 });

  const updates: Array<[WriteKey, string]> = [];
  try {
    if ("execution_mode" in body) {
      if (body.execution_mode !== "paper") {
        return NextResponse.json(
          { error: "live_execution_not_authorized", message: "TFE execution is restricted to Alpaca paper custody." },
          { status: 409 },
        );
      }
      updates.push(["execution_mode", "paper"]);
    }
    if ("auto_tfe_enabled" in body) {
      if (typeof body.auto_tfe_enabled !== "boolean") throw new Error("auto_tfe_enabled_must_be_boolean");
      updates.push(["auto_tfe_enabled", String(body.auto_tfe_enabled)]);
    }
    if ("vault_funded_amount" in body) {
      updates.push(["vault_funded_amount", String(finitePositive(body.vault_funded_amount, "vault_funded_amount"))]);
    }
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : String(error) },
      { status: 400 },
    );
  }

  const pool = resolveRuntimePostgresPool();
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    for (const [key, value] of updates) {
      await client.query(
        `INSERT INTO pee1_execution_config (key, value, updated_by)
         VALUES ($1, $2, 'ui')
         ON CONFLICT (key) DO UPDATE
         SET value = EXCLUDED.value, updated_by = EXCLUDED.updated_by`,
        [key, value],
      );
    }
    await client.query("COMMIT");
    return NextResponse.json({ ok: true });
  } catch (error) {
    await client.query("ROLLBACK");
    return NextResponse.json(
      { error: error instanceof Error ? error.message : String(error) },
      { status: 500 },
    );
  } finally {
    client.release();
  }
}
