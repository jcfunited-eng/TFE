import { NextResponse } from "next/server";
import { getDurableUiAsset } from "@/lib/ui-asset-storage";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(_request: Request, context: { params: Promise<{ fileName: string }> }) {
  const { fileName } = await context.params;
  const asset = await getDurableUiAsset(fileName);
  if (!asset) return NextResponse.json({ error: "Asset not found." }, { status: 404 });
  return new NextResponse(Buffer.from(asset.bytes), {
    status: 200,
    headers: {
      "Content-Type": asset.contentType,
      "Content-Length": String(asset.bytes.byteLength),
      "Cache-Control": "public, max-age=31536000, immutable",
      ETag: `"${asset.digest}"`,
      "X-Content-Type-Options": "nosniff",
    },
  });
}
