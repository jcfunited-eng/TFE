import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";
import { readSessionUserFromRequest } from "@/lib/auth-session";
import { resolveRuntimePostgresPool } from "@/lib/runtime-db";

const ALLOWED_TYPES: Record<string, string> = {
  "image/jpeg": "jpg",
  "image/png": "png",
  "image/webp": "webp",
};
const MAX_BYTES = 8 * 1024 * 1024;
const ALLOWED_KEYS = new Set(["D_k_minus_1", "D_k_0", "D_k_plus_1"]);

export async function POST(request: Request) {
  const user = await readSessionUserFromRequest(request);
  if (!user) return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  if (user.role !== "admin") return NextResponse.json({ error: "Admin role required." }, { status: 403 });

  const form = await request.formData();
  const file = form.get("file");
  const conditionKey = String(form.get("conditionKey") || "").trim();

  if (!(file instanceof File)) {
    return NextResponse.json({ error: "No file provided." }, { status: 400 });
  }
  if (!ALLOWED_KEYS.has(conditionKey)) {
    return NextResponse.json({ error: "Invalid conditionKey." }, { status: 400 });
  }
  if (!ALLOWED_TYPES[file.type]) {
    return NextResponse.json({ error: "Only JPG, PNG, and WEBP are allowed." }, { status: 400 });
  }
  if (file.size > MAX_BYTES) {
    return NextResponse.json({ error: "File exceeds 8 MB limit." }, { status: 400 });
  }

  const ext = ALLOWED_TYPES[file.type];
  const ts = Date.now();
  const fileName = `${ts}-banner-${conditionKey}.${ext}`;
  const uploadsDir = path.join(process.cwd(), "public", "uploads");
  await mkdir(uploadsDir, { recursive: true });
  const filePath = path.join(uploadsDir, fileName);
  const bytes = await file.arrayBuffer();
  await writeFile(filePath, Buffer.from(bytes));

  const publicPath = `/uploads/${fileName}`;

  // Persist path into the DB row
  const pool = resolveRuntimePostgresPool();
  await pool.query(
    `UPDATE ui_asset_controls
     SET background_image_path = $1, updated_at = NOW()
     WHERE condition_key = $2`,
    [publicPath, conditionKey]
  );

  return NextResponse.json({ ok: true, path: publicPath });
}
