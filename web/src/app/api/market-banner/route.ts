import { NextResponse } from "next/server";
import { getCurrentServerUser } from "@/lib/server-auth";
import { resolveRuntimePostgresPool, RUNTIME_DECISIONS_TABLE } from "@/lib/runtime-db";

function exactDk(value: unknown): -1 | 0 | 1 {
  const parsed = Number(value);
  if (parsed === -1 || parsed === 0 || parsed === 1) return parsed;
  throw new Error("SPY_D_k_missing_or_invalid");
}

function dkToKey(dk: -1 | 0 | 1): "D_k_minus_1" | "D_k_0" | "D_k_plus_1" {
  if (dk === -1) return "D_k_minus_1";
  if (dk === 1) return "D_k_plus_1";
  return "D_k_0";
}

function validColor(value: string): boolean {
  return /^#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$/.test(value);
}

export async function GET() {
  const user = await getCurrentServerUser();
  if (!user) return NextResponse.json({ error: "Authentication required." }, { status: 401 });

  const pool = resolveRuntimePostgresPool();
  try {
    const spyResult = await pool.query<{ snapshot_row_json: unknown }>(
      `SELECT snapshot_row_json
       FROM ${RUNTIME_DECISIONS_TABLE}
       WHERE ticker = 'SPY'
       LIMIT 1`,
    );
    if (spyResult.rows.length !== 1) throw new Error("SPY_field_row_unavailable");
    const snapshot = spyResult.rows[0].snapshot_row_json;
    if (!snapshot || typeof snapshot !== "object" || Array.isArray(snapshot)) {
      throw new Error("SPY_field_payload_invalid");
    }

    const spyDk = exactDk((snapshot as Record<string, unknown>).D_k);
    const conditionKey = dkToKey(spyDk);
    const bannerResult = await pool.query<{
      background_image_path: string;
      instructional_text: string;
      text_color_hex: string;
    }>(
      `SELECT background_image_path, instructional_text, text_color_hex
       FROM ui_asset_controls
       WHERE condition_key = $1
       LIMIT 1`,
      [conditionKey],
    );
    if (bannerResult.rows.length !== 1) throw new Error(`banner_configuration_missing:${conditionKey}`);
    const row = bannerResult.rows[0];
    if (!validColor(row.text_color_hex)) throw new Error(`banner_text_color_invalid:${conditionKey}`);

    return NextResponse.json({
      conditionKey,
      backgroundImagePath: row.background_image_path,
      instructionalText: row.instructional_text,
      textColorHex: row.text_color_hex,
      spyDk,
      fieldCoverage: "single_observed_D_k",
    });
  } catch (error) {
    return NextResponse.json(
      {
        error: "market_condition_unavailable",
        detail: error instanceof Error ? error.message : String(error),
      },
      { status: 503 },
    );
  }
}
