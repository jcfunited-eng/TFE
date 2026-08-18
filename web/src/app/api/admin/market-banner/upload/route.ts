import { NextResponse } from "next/server";
import { getCurrentServerUser } from "@/lib/server-auth";
import { resolveRuntimePostgresPool } from "@/lib/runtime-db";
import { putDurableUiAsset } from "@/lib/ui-asset-storage";

const ALLOWED_TYPES: Record<string, string> = {
  "image/jpeg": "jpg",
  "image/png": "png",
  "image/webp": "webp",
};
const MAX_BYTES = 8 * 1024 * 1024;
const ALLOWED_KEYS = new Set(["D_k_minus_1", "D_k_0", "D_k_plus_1"]);

export async function POST(request: Request) {
  const user = await getCurrentServerUser();
  if (!user) return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  if (user.role !== "admin") return NextResponse.json({ error: "Admin role required." }, { status: 403 });

  const form = await request.formData();
  const file = form.get("file");
  const conditionKey = String(form.get("conditionKey") || "").trim();
  if (!(file instanceof File)) return NextResponse.json({ error: "No file provided." }, { status: 400 });
  if (!ALLOWED_KEYS.has(conditionKey)) return NextResponse.json({ error: "Invalid conditionKey." }, { status: 400 });
  const extension = ALLOWED_TYPES[file.type];
  if (!extension) return NextResponse.json({ error: "Only JPG, PNG, and WEBP are allowed." }, { status: 400 });
  if (file.size <= 0 || file.size > MAX_BYTES) {
    return NextResponse.json({ error: "File size must be between 1 byte and 8 MB." }, { status: 400 });
  }

  const assetPath = await putDurableUiAsset(new Uint8Array(await file.arrayBuffer()), file.type, extension);
  const pool = resolveRuntimePostgresPool();
  const updated = await pool.query(
    `UPDATE ui_asset_controls
     SET background_image_path = $1, updated_at = NOW()
     WHERE condition_key = $2
     RETURNING condition_key`,
    [assetPath, conditionKey],
  );
  if (updated.rowCount !== 1) {
    return NextResponse.json({ error: "Market banner control row is missing." }, { status: 503 });
  }
  return NextResponse.json({ ok: true, path: assetPath, storage: "s3_immutable" });
}
