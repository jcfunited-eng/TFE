/**
 * Public (authenticated-user) endpoint that returns the active market banner
 * for the current SPY D_k state. Used by MarketConditionBanner on the
 * Recommendations page.
 *
 * Returns:
 *   { conditionKey, backgroundImagePath, instructionalText, textColorHex, spyDk, isMarketLocked }
 */
import { NextResponse } from "next/server";
import { readSessionUserFromRequest } from "@/lib/auth-session";
import { resolveRuntimePostgresPool, RUNTIME_DECISIONS_TABLE } from "@/lib/runtime-db";

function safeFloat(val: unknown): number | null {
  if (val === null || val === undefined) return null;
  const f = typeof val === "number" ? val : parseFloat(String(val));
  return isFinite(f) ? f : null;
}

function dkToKey(dk: number | null): string {
  if (dk === null) return "D_k_minus_1"; // default to caution when unknown
  if (dk >= 1) return "D_k_plus_1";
  if (dk <= -1) return "D_k_minus_1";
  return "D_k_0";
}

export async function GET(request: Request) {
  const user = await readSessionUserFromRequest(request);
  if (!user) return NextResponse.json({ error: "Authentication required." }, { status: 401 });

  const pool = resolveRuntimePostgresPool();

  // Resolve SPY D_k
  let spyDk: number | null = null;
  try {
    const spyRes = await pool.query<{ snapshot_row_json: unknown; decision_label: string | null }>(
      `SELECT snapshot_row_json, decision_label FROM ${RUNTIME_DECISIONS_TABLE} WHERE ticker = 'SPY' LIMIT 1`
    );
    if (spyRes.rows.length > 0) {
      const snap =
        spyRes.rows[0].snapshot_row_json &&
        typeof spyRes.rows[0].snapshot_row_json === "object" &&
        !Array.isArray(spyRes.rows[0].snapshot_row_json)
          ? (spyRes.rows[0].snapshot_row_json as Record<string, unknown>)
          : {};
      spyDk = safeFloat(snap["D_k"]);
    }
  } catch {
    // Leave spyDk null — will map to D_k_minus_1 (cautious default)
  }

  const conditionKey = dkToKey(spyDk);
  const isMarketLocked = conditionKey === "D_k_minus_1";

  // Fetch banner row
  try {
    const bannerRes = await pool.query<{
      background_image_path: string;
      instructional_text: string;
      text_color_hex: string;
    }>(
      `SELECT background_image_path, instructional_text, text_color_hex
       FROM ui_asset_controls
       WHERE condition_key = $1
       LIMIT 1`,
      [conditionKey]
    );

    const row = bannerRes.rows[0];

    return NextResponse.json({
      conditionKey,
      backgroundImagePath: row?.background_image_path ?? "",
      instructionalText: row?.instructional_text ?? "",
      textColorHex: row?.text_color_hex ?? "#FFFFFF",
      spyDk,
      isMarketLocked,
    });
  } catch {
    // If table doesn't exist yet (before migration), return safe defaults
    return NextResponse.json({
      conditionKey,
      backgroundImagePath: "",
      instructionalText: "",
      textColorHex: "#FFFFFF",
      spyDk,
      isMarketLocked,
    });
  }
}
