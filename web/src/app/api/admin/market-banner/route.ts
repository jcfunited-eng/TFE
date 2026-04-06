import { NextResponse } from "next/server";
import { getCurrentServerUser } from "@/lib/server-auth";
import { resolveRuntimePostgresPool } from "@/lib/runtime-db";

export type MarketBannerRow = {
  id: number;
  conditionKey: string;
  backgroundImagePath: string;
  instructionalText: string;
  textColorHex: string;
  updatedAt: string;
};

const ALLOWED_KEYS = new Set(["D_k_minus_1", "D_k_0", "D_k_plus_1"]);

async function requireAdmin(request: Request): Promise<NextResponse | null> {
  const user = await getCurrentServerUser();
  if (!user) return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  if (user.role !== "admin") return NextResponse.json({ error: "Admin role required." }, { status: 403 });
  return null;
}

function sanitizeHex(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return /^#[0-9A-Fa-f]{3,6}$/.test(trimmed) ? trimmed : null;
}

function sanitizeImagePath(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  if (trimmed === "") return "";
  return /^\/[a-zA-Z0-9_\-./]+\.(jpg|jpeg|png|webp)$/i.test(trimmed) ? trimmed : null;
}

export async function GET(request: Request) {
  const denied = await requireAdmin(request);
  if (denied) return denied;

  const pool = resolveRuntimePostgresPool();
  const res = await pool.query<{
    id: number;
    condition_key: string;
    background_image_path: string;
    instructional_text: string;
    text_color_hex: string;
    updated_at: Date;
  }>(
    `SELECT id, condition_key, background_image_path, instructional_text, text_color_hex, updated_at
     FROM ui_asset_controls
     ORDER BY id ASC`
  );

  const rows: MarketBannerRow[] = res.rows.map((r) => ({
    id: r.id,
    conditionKey: r.condition_key,
    backgroundImagePath: r.background_image_path,
    instructionalText: r.instructional_text,
    textColorHex: r.text_color_hex,
    updatedAt: r.updated_at.toISOString(),
  }));

  return NextResponse.json({ rows });
}

export async function PATCH(request: Request) {
  const denied = await requireAdmin(request);
  if (denied) return denied;

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON." }, { status: 400 });
  }

  const payload = body as Record<string, unknown>;
  const conditionKey = String(payload.conditionKey ?? "").trim();

  if (!ALLOWED_KEYS.has(conditionKey)) {
    return NextResponse.json({ error: "Invalid conditionKey." }, { status: 400 });
  }

  const updates: string[] = [];
  const values: unknown[] = [conditionKey];
  let idx = 2;

  if ("instructionalText" in payload) {
    if (typeof payload.instructionalText !== "string") {
      return NextResponse.json({ error: "instructionalText must be a string." }, { status: 400 });
    }
    updates.push(`instructional_text = $${idx++}`);
    values.push(payload.instructionalText.trim());
  }

  if ("textColorHex" in payload) {
    const hex = sanitizeHex(payload.textColorHex);
    if (hex === null) {
      return NextResponse.json({ error: "textColorHex must be a valid hex color (e.g. #FFFFFF)." }, { status: 400 });
    }
    updates.push(`text_color_hex = $${idx++}`);
    values.push(hex);
  }

  if ("backgroundImagePath" in payload) {
    const imgPath = sanitizeImagePath(payload.backgroundImagePath);
    if (imgPath === null) {
      return NextResponse.json({ error: "backgroundImagePath is invalid." }, { status: 400 });
    }
    updates.push(`background_image_path = $${idx++}`);
    values.push(imgPath);
  }

  if (updates.length === 0) {
    return NextResponse.json({ error: "No valid fields to update." }, { status: 400 });
  }

  updates.push(`updated_at = NOW()`);

  const pool = resolveRuntimePostgresPool();
  await pool.query(
    `UPDATE ui_asset_controls SET ${updates.join(", ")} WHERE condition_key = $1`,
    values
  );

  return NextResponse.json({ ok: true });
}
