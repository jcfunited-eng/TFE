import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";
import { UI_PAGE_KEYS, type UiPageKey } from "@/lib/ui-config";
import { getCurrentServerUser } from "@/lib/server-auth";

const ALLOWED_TYPES: Record<string, string> = {
  "image/jpeg": "jpg",
  "image/png": "png",
  "image/webp": "webp",
};

const MAX_BYTES = 8 * 1024 * 1024;

function sanitizeBaseName(name: string): string {
  const withoutExt = name.replace(/\.[^/.]+$/, "");
  const normalized = withoutExt.toLowerCase().replace(/[^a-z0-9\-]+/g, "-").replace(/-+/g, "-").replace(/^-|-$/g, "");
  return normalized || "image";
}

function isUiPageKey(value: string): value is UiPageKey {
  return (UI_PAGE_KEYS as readonly string[]).includes(value);
}

export async function POST(request: Request) {
  const sessionUser = await getCurrentServerUser();
  if (!sessionUser) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  if (sessionUser.role !== "admin") {
    return NextResponse.json({ error: "Admin role required." }, { status: 403 });
  }

  const form = await request.formData();
  const file = form.get("file");
  const pageKeyValue = String(form.get("pageKey") || "home");

  if (!(file instanceof File)) {
    return NextResponse.json({ error: "No file provided." }, { status: 400 });
  }

  if (!isUiPageKey(pageKeyValue)) {
    return NextResponse.json({ error: "Invalid page key." }, { status: 400 });
  }

  if (!ALLOWED_TYPES[file.type]) {
    return NextResponse.json({ error: "Only JPG, PNG, and WEBP are allowed." }, { status: 400 });
  }

  if (file.size <= 0 || file.size > MAX_BYTES) {
    return NextResponse.json({ error: "File size must be between 1 byte and 8 MB." }, { status: 400 });
  }

  const ext = ALLOWED_TYPES[file.type];
  const base = sanitizeBaseName(file.name);
  const fileName = `${Date.now()}-${pageKeyValue}-${base}.${ext}`;

  const publicUploadsDir = path.join(process.cwd(), "public", "uploads");
  const targetPath = path.join(publicUploadsDir, fileName);

  await mkdir(publicUploadsDir, { recursive: true });
  const bytes = Buffer.from(await file.arrayBuffer());
  await writeFile(targetPath, bytes);

  return NextResponse.json({
    path: `/uploads/${fileName}`,
    pageKey: pageKeyValue,
  });
}
