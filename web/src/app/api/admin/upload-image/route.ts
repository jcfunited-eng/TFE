import { NextResponse } from "next/server";
import { getCurrentServerUser } from "@/lib/server-auth";
import { putDurableUiAsset } from "@/lib/ui-asset-storage";
import { UI_PAGE_KEYS, type UiPageKey } from "@/lib/ui-config";

const ALLOWED_TYPES: Record<string, string> = {
  "image/jpeg": "jpg",
  "image/png": "png",
  "image/webp": "webp",
};
const MAX_BYTES = 8 * 1024 * 1024;

function isUiPageKey(value: string): value is UiPageKey {
  return (UI_PAGE_KEYS as readonly string[]).includes(value);
}

export async function POST(request: Request) {
  const user = await getCurrentServerUser();
  if (!user) return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  if (user.role !== "admin") return NextResponse.json({ error: "Admin role required." }, { status: 403 });

  const form = await request.formData();
  const file = form.get("file");
  const pageKey = String(form.get("pageKey") || "home");
  if (!(file instanceof File)) return NextResponse.json({ error: "No file provided." }, { status: 400 });
  if (!isUiPageKey(pageKey)) return NextResponse.json({ error: "Invalid page key." }, { status: 400 });
  const extension = ALLOWED_TYPES[file.type];
  if (!extension) return NextResponse.json({ error: "Only JPG, PNG, and WEBP are allowed." }, { status: 400 });
  if (file.size <= 0 || file.size > MAX_BYTES) {
    return NextResponse.json({ error: "File size must be between 1 byte and 8 MB." }, { status: 400 });
  }

  const bytes = new Uint8Array(await file.arrayBuffer());
  const assetPath = await putDurableUiAsset(bytes, file.type, extension);
  return NextResponse.json({ path: assetPath, pageKey, storage: "s3_immutable" });
}
